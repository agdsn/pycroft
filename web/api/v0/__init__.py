import typing as t
from decimal import Decimal
from datetime import timedelta, datetime, date
from functools import wraps
from ipaddress import IPv4Address, IPv6Address

from flask import jsonify, current_app, Response
from flask.typing import ResponseReturnValue
from flask_restful import Api, Resource as FlaskRestfulResource, abort
from packaging.utils import InvalidName
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload, undefer, with_polymorphic
from sqlalchemy.orm.interfaces import ORMOption
from webargs import fields
from webargs.flaskparser import use_kwargs

from pycroft.helpers import utc
from pycroft.helpers.i18n import Message
from pycroft.lib.finance import estimate_balance, get_last_import_date
from pycroft.lib.mpsk_client import mpsk_edit, mpsk_client_create, mpsk_delete
from pycroft.lib.host import change_mac, host_create, interface_create, host_edit
from pycroft.lib.net import SubnetFullException
from pycroft.lib.swdd import get_swdd_person_id, get_relevant_tenancies, \
    get_first_tenancy_with_room
from pycroft.lib.task import cancel_task
from pycroft.lib.user import (
    encode_type2_user_id,
    edit_email,
    change_password,
    status,
    traffic_history as func_traffic_history,
    scheduled_membership_end,
    move_out,
    membership_ending_task,
    reset_wifi_password,
    create_member_request,
    NoTenancyForRoomException,
    UserExistsException,
    UserExistsInRoomException,
    EmailTakenException,
    LoginTakenException,
    MoveInDateInvalidException,
    check_similar_user_in_room,
    get_name_from_first_last,
    confirm_mail_address,
    get_user_by_swdd_person_id,
    scheduled_membership_start,
    send_confirmation_email,
    get_user_by_id_or_login,
    send_password_reset_mail,
    change_password_from_token,
)
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.finance import Account, Split
from pycroft.model.host import IP, Interface, Host
from pycroft.model.session import current_timestamp
from pycroft.model.task import Task
from pycroft.model.types import IPAddress, InvalidMACAddressException
from pycroft.model.user import User, IllegalEmailError, IllegalLoginError
from web.blueprints.mpskclient import get_mpsk_client_or_404

api = Api()


def parse_authorization_header(value: str | None) -> str | None:
    if not value:
        return None

    try:
        auth_type, api_key = value.split(maxsplit=1)
        return api_key if auth_type.lower() == 'apikey' else None
    except ValueError:
        return None


_P = t.ParamSpec("_P")
_TF = t.Callable[_P, ResponseReturnValue]


def authenticate(func: _TF) -> _TF:
    @t.cast(t.Callable[[_TF], _TF], wraps(func))
    @use_kwargs(
        {
            "auth": fields.Str(required=True, data_key="authorization"),
        },
        location="headers",
    )
    def wrapper(auth: str, *args: _P.args, **kwargs: _P.kwargs) -> ResponseReturnValue:
        api_key = parse_authorization_header(auth)

        if api_key is None:
            abort(401, message="Missing API key.")

        if current_app.config['PYCROFT_API_KEY'] != api_key:
            abort(401, message="Invalid API key.")

        return func(*args, **kwargs)

    return wrapper


class Resource(FlaskRestfulResource):
    method_decorators = [authenticate]


def get_user_or_404(user_id: int, options: t.Sequence[ORMOption] | None = None) -> User:
    user = session.session.get(User, user_id, options=options)
    if user is None:
        abort(404, message=f"User {user_id} does not exist")
    return user


def get_authenticated_user(user_id: int, password: str) -> User:
    user = get_user_or_404(user_id)
    if user is None or not user.check_password(password):
        abort(401, message=f"Authentication of user {user_id} failed")
    return user


def get_interface_or_404(interface_id: int) -> Interface:
    interface = session.session.get(Interface, interface_id)
    if interface is None:
        abort(404, message=f"Interface {interface_id} does not exist")
    return interface


def generate_user_data(user: User) -> Response:
    props = {prop.property_name for prop in user.current_properties}
    user_status = status(user)

    interval = timedelta(days=7)
    step = timedelta(days=1)
    traffic_history = func_traffic_history(
        user.id,
        current_timestamp() - interval + step,
        current_timestamp(),
    )

    class _Entry(t.TypedDict):
        valid_on: date
        amount: int | Decimal
        description: str

    finance_history: list[_Entry] = [
        {
            "valid_on": split.transaction.valid_on,
            # Invert amount, to display it from the user's point of view
            "amount": -split.amount,
            "description": Message.from_json(split.transaction.description).localize(),
        }
        for split in user.account.splits
    ]

    finance_history = sorted(finance_history, key=lambda e: e['valid_on'], reverse=True)

    last_import_ts = get_last_import_date(session.session)
    last_finance_update = last_import_ts and last_import_ts.date() or None

    wifi_password = user.wifi_password

    med = scheduled_membership_end(user)
    mbd = scheduled_membership_start(user)

    interface_info = [{
        'id': i.id,
        'mac': str(i.mac),
        'ips': [str(ip.address) for ip in i.ips]
    } for h in user.hosts for i in h.interfaces]

    return jsonify(
        id=user.id,
        user_id=encode_type2_user_id(user.id),
        name=user.name,
        login=user.login,
        status={
            'member': user_status.member,
            'traffic_exceeded': user_status.traffic_exceeded,
            'network_access': user_status.network_access,
            'account_balanced': user_status.account_balanced,
            'violation': user_status.violation
        },
        room=user.room.short_name if user.room is not None else None,
        interfaces=interface_info,
        mail=user.email,
        mail_forwarded=user.email_forwarded,
        mail_confirmed=user.email_confirmed,
        cache='cache_access' in props,
        # TODO: make `has_property` use `current_property`
        properties=list(props),
        traffic_history=[e.__dict__ for e in traffic_history],
        # TODO: think about better way for credit
        finance_balance=-user.account.balance,
        finance_history=finance_history,
        last_finance_update=last_finance_update.isoformat() if last_finance_update else None,
        membership_end_date=med.isoformat() if med else None,
        membership_begin_date=mbd.isoformat() if mbd else None,
        wifi_password=wifi_password,
        birthdate=user.birthdate.isoformat() if user.birthdate else None,
    )


class UserResource(Resource):
    def get(self, user_id: int) -> Response:
        user = get_user_or_404(
            user_id,
            options=[
                joinedload(User.room).joinedload(Room.building),
                joinedload(User.hosts)
                .joinedload(Host.interfaces)
                .joinedload(Interface.ips),
                undefer(User.wifi_passwd_hash),
                joinedload(User.account)
                .selectinload(Account.splits)
                .joinedload(Split.transaction),
                selectinload(User.tasks.of_type(with_polymorphic(Task, "*"))),
                selectinload(User.current_properties),
            ],
        )
        return generate_user_data(user)


api.add_resource(UserResource, '/user/<int:user_id>')


class ChangeEmailResource(Resource):
    @use_kwargs(
        {
            "password": fields.Str(required=True),
            "new_email": fields.Str(required=True),
            "forwarded": fields.Bool(required=False, load_default=True),
        },
        location="form",
    )
    def post(
        self,
        user_id: int,
        password: str,
        new_email: str,
        forwarded: bool | None = None,
    ) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, password)
        try:
            edit_email(user, new_email, forwarded, processor=user)
            session.session.commit()
        except IllegalEmailError:
            abort(400, message='Invalid email address.')
        return "Email has been changed."


api.add_resource(ChangeEmailResource, '/user/<int:user_id>/change-email')


class ChangePasswordResource(Resource):
    @use_kwargs(
        {
            "old_password": fields.Str(required=True, data_key="password"),
            "new_password": fields.Str(required=True),
        },
        location="form",
    )
    def post(
        self, user_id: int, old_password: str, new_password: str
    ) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, old_password)
        change_password(user, new_password)
        session.session.commit()
        return "Password has been changed."


api.add_resource(ChangePasswordResource, '/user/<int:user_id>/change-password')


class FinanceHistoryResource(Resource):
    def get(self, user_id: int) -> ResponseReturnValue:
        user = get_user_or_404(user_id)
        return jsonify([
            {'valid_on': s.transaction.valid_on.isoformat(), 'amount': s.amount}
            for s in
            sorted(user.account.splits, key=lambda s: s.transaction.valid_on)
        ])


api.add_resource(FinanceHistoryResource, '/user/<int:user_id>/finance-history')


class AuthenticationResource(Resource):
    @use_kwargs(
        {
            "login": fields.Str(required=True),
            "password": fields.Str(required=True),
        },
        location="form",
    )
    def post(self, login: str, password: str) -> ResponseReturnValue:
        user = User.verify_and_get(login=login, plaintext_password=password)
        if user is None:
            abort(401, message="Authentication failed")
        return {'id': user.id}


api.add_resource(AuthenticationResource, '/user/authenticate')


class UserByIPResource(Resource):
    @use_kwargs(
        {
            "ipv4": fields.IP(required=True, data_key="ip"),  # type: ignore[no-untyped-call]
        },
        location="query",
    )
    def get(self, ipv4: IPv4Address | IPv6Address) -> ResponseReturnValue:
        user = session.session.scalars(
            select(User)
            .join(Host)
            .join(Interface)
            .join(IP)
            .where(IP.address == ipv4)
            .options(
                # multi-valued, but effectively one-valued:
                # a user has only one IP (except in rare cases) → joinedload
                joinedload(User.hosts, innerjoin=True)
                    .joinedload(Host.interfaces, innerjoin=True)
                    .joinedload(Interface.ips, innerjoin=True),
                # single-valued → joinedload
                joinedload(User.room, innerjoin=True)
                    .joinedload(Room.building, innerjoin=True),
                # 1 account, but many splits
                joinedload(User.account, innerjoin=True)
                    # many splits → load afterwards with `select/where/in`
                    .selectinload(Account.splits)
                    .joinedload(Split.transaction, innerjoin=True),
                # many properties
                selectinload(User.current_properties),
            )
        ).unique().one_or_none()

        if user is None:
            abort(404, message=f"IP {ipv4} is not related to a user")
        return generate_user_data(user)


api.add_resource(UserByIPResource, '/user/from-ip')

class MPSKSClientAddResource(Resource):
    @use_kwargs(
        {
            "password": fields.Str(required=True),
            "mac": fields.Str(required=True),
            "name": fields.Str(required=True),
        },
        location="form",
    )
    def post(self, user_id: int, password: str, mac: str, name: str) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, password)
        # checks rather the user has all settable mpsks clients created
        if len(user.mpsk_clients) >= current_app.config.get("MAX_MPSKS", 30):
            abort(400, message="User has the maximum count of mpsk clients.")

        if not user.wifi_password:
            abort(412, message="Please generate a wifi password first")

        try:
            mpsk_client = mpsk_client_create(
                session.session, owner=user, mac=mac, name=name, processor=user
            )
            session.session.commit()
        except InvalidMACAddressException as e:
            abort(422, message=f"Invalid MAC address: {e}")
        except IntegrityError as e:
            abort(409, message=f"Mac address is already in use: {e}")
        except InvalidName:
            abort(400, message="No proper name was provided.")
        return jsonify(
            {
                "name": mpsk_client.name,
                "id": mpsk_client.id,
                "mac": mpsk_client.mac,
            }
        )


api.add_resource(MPSKSClientAddResource, "/user/<int:user_id>/add-mpsk")


class MPSKSClientDeleteResource(Resource):
    @use_kwargs(
        {
            "password": fields.Str(required=True),
        },
        location="form",
    )
    def post(self, user_id: int, mpsk_id: int, password: str) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, password)
        mpsk = get_mpsk_client_or_404(mpsk_id)

        if not user == mpsk.owner:
            abort(401, message="You are not the owner of the mpsk.")

        mpsk_delete(session.session, mpsk_client=mpsk, processor=user)
        session.session.commit()

        return "mpsk client was deleted"


api.add_resource(MPSKSClientDeleteResource, "/user/<int:user_id>/delete-mpsk/<int:mpsk_id>")


class MPSKSClientChangeResource(Resource):
    @use_kwargs(
        {
            "password": fields.Str(required=True),
            "mac": fields.Str(required=True),
            "name": fields.Str(required=True),
        },
        location="form",
    )
    def post(
        self, user_id: int, mpsks_id: int, password: str, mac: str, name: str
    ) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, password)
        mpsk = get_mpsk_client_or_404(mpsks_id)

        if user != mpsk.owner:
            abort(
                404, message=f"User {user_id} does not own the mpsk client with the id {mpsks_id}"
            )

        try:
            mpsk_edit(session.session, client=mpsk, owner=user, name=name, mac=mac, processor=user)
            session.session.commit()
        except InvalidMACAddressException:
            abort(400, message="Invalid MAC address.")
        except IntegrityError:
            abort(400, message="Mac address is already in use.")
        except InvalidName:
            abort(400, message="No proper name was provided.")
        return "mpsk has been changed."


api.add_resource(MPSKSClientChangeResource, "/user/<int:user_id>/change-mpsk/<int:mpsk_id>")


class UserInterfaceResource(Resource):
    @use_kwargs(
        {
            "password": fields.Str(required=True),
            "mac": fields.Str(required=True),
            "host_name": fields.Str(required=False),
        },
        location="form",
    )
    def post(
        self,
        user_id: int,
        interface_id: int,
        password: str,
        mac: str,
        host_name: str | None = None,
    ) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, password)
        interface = get_interface_or_404(interface_id)
        if interface.host.owner != user:
            abort(
                404,
                message=f"User {user_id} does not have a host with interface {interface_id}"
            )

        try:
            if host_name:
                host_edit(
                    interface.host,
                    interface.host.owner,
                    interface.host.room,
                    host_name,
                    user,
                )
            change_mac(interface, mac, user)
            session.session.add(interface)
            session.session.commit()
        except InvalidMACAddressException:
            abort(400, message='Invalid mac address.')
        except IntegrityError:
            abort(400, message='Mac address is already in use.')
        return "Mac address has been changed."


api.add_resource(UserInterfaceResource,
                 '/user/<int:user_id>/change-mac/<int:interface_id>')


class ActivateNetworkAccessResource(Resource):
    @use_kwargs(
        {
            "password": fields.Str(required=True),
            "birthdate": fields.Date(required=True),
            "mac": fields.Str(required=True),
            "host_name": fields.Str(required=False),
        },
        location="form",
    )
    def post(
        self,
        user_id: int,
        password: str,
        birthdate: date,
        mac: str,
        host_name: str | None = None,
    ) -> ResponseReturnValue:
        user = get_authenticated_user(user_id, password)

        if user.room is None:
            abort(424, message="User is not living in a dormitory.")

        if not user.has_property('network_access'):
            abort(403, message="User has no network access.")

        interfaces = Interface.q.join(Host).filter(Host.owner_id == user.id).all()
        if len(interfaces) > 0:
            abort(412, message="User already has a host with interface.")

        user.birthdate = birthdate

        host = Host.q.filter_by(owner_id=user.id).one_or_none()

        try:
            if host is None:
                host = host_create(user, user.room, host_name, user)
            else:
                host_edit(host, host.owner, user.room, host_name, user)

            interface_create(host, None, mac, None, user)

            session.session.commit()
        except InvalidMACAddressException:
            abort(400, message='Invalid mac address.')
        except IntegrityError:
            abort(400, message='Mac address is already in use.')
        except SubnetFullException:
            abort(422, message='Subnet full.')

        return jsonify({'success': True})


api.add_resource(ActivateNetworkAccessResource,
                 '/user/<int:user_id>/activate-network-access')


class TerminateMembershipResource(Resource):
    @use_kwargs(
        {
            "end_date": fields.Date(required=True),
        },
        location="query",
    )
    def get(self, user_id: int, end_date: date) -> ResponseReturnValue:
        """
        :param user_id: The ID of the user
        :return: The estimated balance of the given end_date
        """

        user = get_user_or_404(user_id)

        estimated_balance = estimate_balance(session.session, user, end_date)

        return jsonify(estimated_balance=estimated_balance)

    @use_kwargs(
        {
            "end_date": fields.Date(required=True),
            "comment": fields.Str(required=False),
        },
        location="form",
    )
    def post(
        self, user_id: int, end_date: date, comment: str | None = None
    ) -> ResponseReturnValue:
        """
        Terminate the membership on the given date

        :param user_id: The ID of the user
        :return:
        """

        user = get_user_or_404(user_id)

        if membership_ending_task(user) is not None:
            abort(400, message="The termination of the membership has already"
                               " been scheduled.")

        if not user.has_property('member'):
            abort(400, message="User is not a member.")

        move_out(
            user=user,
            comment=comment if comment is not None else "Move-out over API",
            processor=user,
            when=utc.with_min_time(end_date),
            end_membership=True,
        )

        session.session.commit()

        return "Membership termination scheduled."

    def delete(self, user_id: int) -> ResponseReturnValue:
        """
        Cancel termination of a membership

        :param user_id: The ID of the user
        :return:
        """

        user = get_user_or_404(user_id)

        task = membership_ending_task(user)

        if task is None:
            abort(400, message="There is no termination scheduled")

        if not user.has_property('member'):
            abort(400, message="User is not a member.")

        cancel_task(task, user)

        session.session.commit()

        return "Membership termination cancelled."


api.add_resource(TerminateMembershipResource,
                 '/user/<int:user_id>/terminate-membership')


class ResetWifiPasswordResource(Resource):
    def patch(self, user_id: int) -> ResponseReturnValue:
        """
        Reset the wifi password

        :return: new password
        """

        user = get_user_or_404(user_id)

        new_password = reset_wifi_password(user, user)

        session.session.commit()

        return new_password


api.add_resource(ResetWifiPasswordResource,
                 '/user/<int:user_id>/reset-wifi-password')


class RegistrationResource(Resource):
    @use_kwargs(
        {
            "first_name": fields.Str(required=True),
            "last_name": fields.Str(required=True),
            "birthdate": fields.Date(required=True),
            "person_id": fields.Int(required=True),
            "previous_dorm": fields.Str(required=False),
        },
        location="query",
    )
    def get(
        self,
        first_name: str,
        last_name: str,
        birthdate: date,
        person_id: int,
        previous_dorm: str | None = None,
    ) -> ResponseReturnValue:
        """
        Get the newest tenancy for the supplied user data, or an error 404 if not found.

        Error codes
            no_tenancies
                No tenancies could be found for the supplied data
            no_relevant_tenancies
                 active or future tenancies could be found
            no_room_for_tenancies
                ere are tenancies but none of them are connected to a pycroft room
            user_exists
                user with this person_id already exists
            similar_user_exists
                similar user already lives in the room
        """

        swdd_person_id = get_swdd_person_id(first_name, last_name, birthdate)

        # some tenants have an additional semicolon added to their last names
        if swdd_person_id is None:
            swdd_person_id = get_swdd_person_id(first_name, last_name + ";", birthdate)

        if swdd_person_id is None or swdd_person_id != person_id:
            abort(404, message="No tenancies found for this data",
                  code="no_tenancies")

        tenancies = get_relevant_tenancies(swdd_person_id)

        if not tenancies:
            abort(404, message="No active or future tenancies found",
                  code="no_relevant_tenancies")

        newest_tenancy = get_first_tenancy_with_room(tenancies)

        if newest_tenancy is None:
            abort(404, message="Cannot associate a room with any tenancy",
                  code="no_room_for_tenancies")

        if previous_dorm is None:
            if get_user_by_swdd_person_id(swdd_person_id) is not None:
                abort(400, message="User already exists", code="user_exists")

        try:
            name = get_name_from_first_last(first_name, last_name)

            check_similar_user_in_room(name, newest_tenancy.room)
        except UserExistsInRoomException:
            abort(400, message="A user with a similar name already lives in this room",
                  code="similar_user_exists")

        return jsonify({
            'id': newest_tenancy.persvv_id,
            'vo_suchname': newest_tenancy.vo_suchname,
            'begin': newest_tenancy.mietbeginn.isoformat(),
            'end': newest_tenancy.mietende.isoformat(),
            'room_id': newest_tenancy.room.id,
            'building': newest_tenancy.room.building.street_and_number,
            'room': newest_tenancy.room.level_and_number
        })

    @use_kwargs(
        {
            "first_name": fields.Str(required=True),
            "last_name": fields.Str(required=False),
            "birthdate": fields.Date(required=True),
            "email": fields.Str(required=True),
            "password": fields.Str(required=True),
            "login": fields.Str(required=True),
            "person_id": fields.Int(required=False),
            "room_id": fields.Int(required=False),
            "move_in_date": fields.Date(required=False),
            "previous_dorm": fields.Str(required=False),
        },
        location="form",
    )
    def post(
        self,
        first_name: str,
        birthdate: date,
        email: str,
        password: str,
        login: str,
        last_name: str | None = None,
        person_id: int | None = None,
        room_id: int | None = None,
        move_in_date: date | None = None,
        previous_dorm: str | None = None,
    ) -> int:
        """
        Create a member request
        """

        room = None
        swdd_person_id = None

        if room_id is not None:
            room = session.session.get(Room, room_id)

            if room is None:
                abort(404, message="Invalid room", code="invalid_room")

        if person_id is not None:
            swdd_person_id = get_swdd_person_id(first_name, last_name, birthdate)

            # some tenants have an additional semicolon added to their last names
            if swdd_person_id is None:
                swdd_person_id = get_swdd_person_id(
                    first_name, last_name + ";", birthdate
                )

            if swdd_person_id != person_id:
                abort(400, message="Person id does not match", code="person_id_mismatch")

        name = get_name_from_first_last(first_name, last_name)

        try:
            mr = create_member_request(
                name,
                email,
                password,
                login,
                birthdate,
                swdd_person_id,
                room,
                move_in_date,
                previous_dorm,
            )
        except UserExistsException:
            abort(400, message="User already exists", code="user_exists")
        except UserExistsInRoomException:
            abort(400, message="A user with a similar name already lives in this room",
                  code="similar_user_exists")
        except EmailTakenException:
            abort(400, message="E-Mail address already in use", code="email_taken")
        except LoginTakenException:
            abort(400, message="Login already in use", code="login_taken")
        except IllegalEmailError:
            abort(400, message="Illegal E-Mail address", code="email_illegal")
        except IllegalLoginError:
            abort(400, message="Illegal login", code="login_illegal")
        except NoTenancyForRoomException:
            abort(400, message="The given person has no tenancy for the room",
                  code="no_tenancy_in_room")
        except MoveInDateInvalidException:
            abort(400, message="The move-in date is invalid", code="move_in_date_invalid")
        else:
            session.session.commit()
            return mr.id
        raise AssertionError(
            "unreachable"
        )  # the `abort`s from `flask_restful` don't return `NoReturn`


api.add_resource(RegistrationResource,
                 '/register')


class EmailConfirmResource(Resource):
    @use_kwargs(
        {
            "user_id": fields.Int(required=True),
        },
        location="query",
    )
    def get(self, user_id: int) -> ResponseReturnValue:
        user = session.session.get(User, user_id)

        if user is None:
            abort(404, message='User not found')

        send_confirmation_email(user)

        session.session.commit()

        return jsonify({'success': True})

    @use_kwargs(
        {
            "key": fields.Str(required=True),
        },
        location="form",
    )
    def post(self, key: str) -> ResponseReturnValue:
        try:
            user_type, reg_result = confirm_mail_address(key)
        except ValueError:
            abort(400, message="Bad key", code="bad_key")

        session.session.commit()

        return jsonify({'type': user_type, 'reg_result': reg_result})


api.add_resource(EmailConfirmResource,  '/register/confirm')


class ResetPasswordResource(Resource):
    @use_kwargs(
        {
            "ident": fields.Str(required=True),
            "email": fields.Str(required=True),
        },
        location="form",
    )
    def post(self, ident: str, email: str) -> ResponseReturnValue:
        user = get_user_by_id_or_login(ident, email)

        if user is None or not user.has_property('sipa_login'):
            abort(404, message="Not found", code="not_found")

        if not send_password_reset_mail(user):
            abort(412, message="No contact email", code="no_contact")

        session.session.commit()

        return {
            'success': True
        }

    @use_kwargs(
        {
            "token": fields.Str(required=True),
            "password": fields.Str(required=True),
        },
        location="form",
    )
    def patch(self, token: str, password: str) -> ResponseReturnValue:
        if not change_password_from_token(token, password):
            abort(403, message="Invalid token", code="invalid_token")

        session.session.commit()

        return {
            'success': True
        }


api.add_resource(ResetPasswordResource, '/user/reset-password')

from datetime import timedelta, datetime
from functools import wraps

from flask import jsonify, request, current_app
from flask_restful import Api, Resource as FlaskRestfulResource, abort, \
    reqparse, inputs
from ipaddr import IPAddress
from pycroft.helpers import utc
from sqlalchemy.exc import IntegrityError

from pycroft import config
from pycroft.lib.finance import build_transactions_query, estimate_balance
from pycroft.lib.host import change_mac, host_create, interface_create, \
    host_edit
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.swdd import get_swdd_person_id, get_relevant_tenancies, \
    get_first_tenancy_with_room
from pycroft.lib.task import cancel_task
from pycroft.lib.user import encode_type2_user_id, edit_email, change_password, \
    status, traffic_history as func_traffic_history, membership_end_date, \
    move_out, membership_ending_task, reset_wifi_password, create_member_request, \
    NoTenancyForRoomException, UserExistsException, UserExistsInRoomException, EmailTakenException, \
    LoginTakenException, MoveInDateInvalidException, check_similar_user_in_room, \
    get_name_from_first_last, confirm_mail_address, get_user_by_swdd_person_id
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.host import IP, Interface, Host
from pycroft.model.types import IPAddress, InvalidMACAddressException
from pycroft.model.user import User, IllegalEmailError, IllegalLoginError
from web.api.v0.helpers import parse_iso_date

api = Api()


def parse_authorization_header(value):
    if not value:
        return None

    try:
        auth_type, api_key = value.split(maxsplit=1)
        return api_key if auth_type.lower() == 'apikey' else None
    except ValueError:
        return None


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('authorization')
        api_key = parse_authorization_header(auth)

        if api_key is None:
            abort(401, message="Missing API key.")

        if current_app.config['PYCROFT_API_KEY'] != api_key:
            abort(401, message="Invalid API key.")

        return func(*args, **kwargs)

    return wrapper


class Resource(FlaskRestfulResource):
    method_decorators = [authenticate]


def get_user_or_404(user_id):
    user = User.q.get(user_id)
    if user is None:
        abort(404, message="User {} does not exist".format(user_id))
    return user


def get_authenticated_user(user_id, password):
    user = get_user_or_404(user_id)
    if user is None or not user.check_password(password):
        abort(401, message="Authentication failed")
    return user


def get_interface_or_404(interface_id):
    interface = Interface.q.get(interface_id)
    if interface is None:
        abort(404, message="Interface {} does not exist".format(interface_id))
    return interface


def generate_user_data(user):
    props = {prop.property_name for prop in user.current_properties}
    user_status = status(user)

    interval = timedelta(days=7)
    step = timedelta(days=1)
    traffic_history = func_traffic_history(user.id,
                                           session.utcnow() - interval + step,
                                           session.utcnow())

    finance_history = [{
        'valid_on': split.transaction.valid_on,
        # Invert amount, to display it from the user's point of view
        'amount': -split.amount,
        'description': split.transaction.description
    } for split in build_transactions_query(user.account, eagerload=True)]
    last_finance_update = finance_history[-1]['valid_on'] if finance_history \
        else None

    try:
        wifi_password = user.wifi_password
    except ValueError:
        wifi_password = None

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
        interfaces=[
            {'id': i.id, 'mac': str(i.mac),
             'ips': [str(ip.address) for ip in i.ips]}
            for h in user.hosts for i in h.interfaces
        ],
        mail=user.email,
        cache='cache_access' in props,
        # TODO: make `has_property` use `current_property`
        properties=list(props),
        traffic_history=[e.__dict__ for e in traffic_history],
        # TODO: think about better way for credit
        finance_balance=-user.account.balance,
        finance_history=finance_history,
        last_finance_update=last_finance_update,
        membership_end_date=membership_end_date(user),
        wifi_password=wifi_password,
    )


class UserResource(Resource):
    def get(self, user_id):
        user = get_user_or_404(user_id)
        return generate_user_data(user)


api.add_resource(UserResource, '/user/<int:user_id>')


class ChangeEmailResource(Resource):
    def post(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('password', dest='password', required=True)
        parser.add_argument('new_email', dest='new_email', required=False)
        args = parser.parse_args()

        user = get_authenticated_user(user_id, args.password)
        try:
            edit_email(user, args.new_email, user)
            session.session.commit()
        except IllegalEmailError as e:
            abort(400, message='Invalid email address.')
        return "Email has been changed."


api.add_resource(ChangeEmailResource, '/user/<int:user_id>/change-email')


class ChangePasswordResource(Resource):
    def post(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('password', dest='old_password', required=True)
        parser.add_argument('new_password', dest='new_password', required=True)
        args = parser.parse_args()

        user = get_authenticated_user(user_id, args.old_password)
        change_password(user, args.new_password)
        session.session.commit()
        return "Password has been changed."


api.add_resource(ChangePasswordResource, '/user/<int:user_id>/change-password')


class ChangeCacheUsageResource(Resource):
    def post(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('use_cache', dest='use_cache', type=inputs.boolean,
                            required=True)
        args = parser.parse_args()

        user = get_user_or_404(user_id)
        if args.use_cache != user.member_of(config.cache_group):
            if args.use_cache:
                make_member_of(user, config.cache_group, user)
            else:
                remove_member_of(user, config.cache_group, user)
        session.session.commit()
        return "Cache usage has been changed."


api.add_resource(ChangeCacheUsageResource,
                 '/user/<int:user_id>/change-cache-usage')


class FinanceHistoryResource(Resource):
    def get(self, user_id):
        user = get_user_or_404(user_id)
        return jsonify([
            {'valid_on': s.transaction.valid_on.isoformat(), 'amount': s.amount}
            for s in
            sorted(user.account.splits, key=lambda s: s.transaction.valid_on)
        ])


api.add_resource(FinanceHistoryResource, '/user/<int:user_id>/finance-history')


class AuthenticationResource(Resource):
    def post(self):
        auth_parser = reqparse.RequestParser()
        auth_parser.add_argument('login', dest='login', required=True)
        auth_parser.add_argument('password', dest='password', required=True)
        args = auth_parser.parse_args()

        user = User.verify_and_get(login=args.login,
                                   plaintext_password=args.password)
        if user is None:
            abort(401, message="Authentication failed")
        return {'id': user.id}


api.add_resource(AuthenticationResource, '/user/authenticate')


class UserByIPResource(Resource):
    def get(self):
        ipv4 = request.args.get('ip', IPAddress)
        ip = IP.q.filter_by(address=ipv4).one_or_none()
        if ip is None:
            abort(404, message="IP {} is not related to a user".format(ipv4))
        return generate_user_data(ip.interface.host.owner)


api.add_resource(UserByIPResource, '/user/from-ip')


class UserInterfaceResource(Resource):
    def post(self, user_id, interface_id):
        parser = reqparse.RequestParser()
        parser.add_argument('password', dest='password', required=True)
        parser.add_argument('mac', dest='mac', required=True)
        parser.add_argument('host_name', dest='host_name', required=False)
        args = parser.parse_args()

        user = get_authenticated_user(user_id, args.password)
        interface = get_interface_or_404(interface_id)
        if interface.host.owner != user:
            abort(404, message="User {} does not have a host with interface {}"
                  .format(user_id, interface_id))

        try:
            if args.host_name:
                host_edit(interface.host, interface.host.owner, interface.host.room,
                          args.host_name, user)
            change_mac(interface, args.mac, user)
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
    def post(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('password', dest='password', required=True)
        parser.add_argument('birthdate', dest='birthdate', required=True)
        parser.add_argument('mac', dest='mac', required=True)
        parser.add_argument('host_name', dest='host_name', required=False)
        args = parser.parse_args()

        user = get_authenticated_user(user_id, args.password)

        if user.room is None:
            abort(424, message="User is not living in a dormitory.")

        if not user.has_property('network_access'):
            abort(403, message="User has no network access.")

        interfaces = Interface.q.join(Host).filter(Host.owner_id == user.id).all()
        if len(interfaces) > 0:
            abort(412, message="User already has a host with interface.")

        user.birthdate = args.birthdate

        host = Host.q.filter_by(owner_id=user.id).one_or_none()

        try:
            host_name = args.host_name if args.host_name else None

            if host is None:
                host = host_create(user, user.room, host_name, user)
            else:
                host_edit(host, host.owner, user.room, host_name, user)

            interface_create(host, None, args.mac, None, user)

            session.session.commit()
        except InvalidMACAddressException:
            abort(400, message='Invalid mac address.')
        except IntegrityError:
            abort(400, message='Mac address is already in use.')
        return "Network access has been activated."


api.add_resource(ActivateNetworkAccessResource,
                 '/user/<int:user_id>/activate-network-access')


class TerminateMembershipResource(Resource):
    def get(self, user_id):
        """
        :param user_id: The ID of the user
        :return: The estimated balance of the given end_date
        """

        parser = reqparse.RequestParser()
        parser.add_argument('end_date',
                            dest='end_date',
                            required=True,
                            type=parse_iso_date)
        args = parser.parse_args()

        user = get_user_or_404(user_id)

        estimated_balance = estimate_balance(user, args.end_date)

        return jsonify(estimated_balance=estimated_balance)

    def post(self, user_id):
        """
        Terminate the membership on the given date

        :param user_id: The ID of the user
        :return:
        """

        parser = reqparse.RequestParser()
        parser.add_argument('end_date',
                            dest='end_date',
                            required=True,
                            type=lambda x: datetime.strptime(x, '%Y-%m-%d').date())
        parser.add_argument('comment', dest='comment', required=False)
        args = parser.parse_args()

        user = get_user_or_404(user_id)

        if membership_ending_task(user) is not None:
            abort(400, message="The termination of the membership has already"
                               " been scheduled.")

        if not user.has_property('member'):
            abort(400, message="User is not a member.")

        move_out(user=user,
                 comment=args.comment if args.comment is not None else "Move-out over API",
                 processor=user,
                 when=datetime.combine(args.end_date, utc.time_min()),
                 end_membership=True)

        session.session.commit()

        return "Membership termination scheduled."

    def delete(self, user_id):
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
    def patch(self, user_id):
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
    def get(self):
        """
        Get the newest tenancy for the supplied user data, or an error 404 if not found.

        Error codes:
        no_tenancies: No tenancies could be found for the supplied data
        no_relevant_tenancies: No active or future tenancies could be found
        no_room_for_tenancies: There are tenancies but none of them are connected to a pycroft room
        user_exists: A user with this person_id already exists
        similar_user_exists: A similar user already lives in the room
        """

        parser = reqparse.RequestParser()
        parser.add_argument('first_name', required=True, type=str)
        parser.add_argument('last_name', required=True, type=str)
        parser.add_argument('birthdate', required=True, type=parse_iso_date)
        parser.add_argument('person_id', required=True, type=int)
        args = parser.parse_args()

        person_id = get_swdd_person_id(args.first_name, args.last_name, args.birthdate)

        if person_id is None:
            abort(404, message="No tenancies found for this data",
                  code="no_tenancies")

        tenancies = get_relevant_tenancies(person_id)

        if not tenancies:
            abort(404, message="No active or future tenancies found",
                  code="no_relevant_tenancies")

        newest_tenancy = get_first_tenancy_with_room(tenancies)

        if newest_tenancy is None:
            abort(404, message="Cannot associate a room with any tenancy",
                  code="no_room_for_tenancies")

        if get_user_by_swdd_person_id(person_id) is not None:
            abort(400, message="User already exists", code="user_exists")

        try:
            name = get_name_from_first_last(args.first_name, args.last_name)

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

    def post(self):
        """
        Create a member request
        """

        parser = reqparse.RequestParser()
        parser.add_argument('first_name', required=True, type=str)
        parser.add_argument('last_name', required=False, type=str)
        parser.add_argument('birthdate', required=True, type=parse_iso_date)
        parser.add_argument('email', required=True, type=str)
        parser.add_argument('password', required=True, type=str)
        parser.add_argument('login', required=True, type=str)
        parser.add_argument('person_id', required=False, type=int)
        parser.add_argument('room_id', required=False, type=int)
        parser.add_argument('move_in_date', required=False, type=parse_iso_date)
        parser.add_argument('previous_dorm', required=False, type=str)
        args = parser.parse_args()

        room = None
        swdd_person_id = None

        if args.room_id is not None:
            room = Room.q.get(args.room_id)

            if room is None:
                abort(404, message="Invalid room", code="invalid_room")

        if args.person_id is not None:
            swdd_person_id = get_swdd_person_id(args.first_name, args.last_name, args.birthdate)

            if swdd_person_id != args.person_id:
                abort(400, message="Person id does not match", code="person_id_mismatch")

        name = get_name_from_first_last(args.first_name, args.last_name)

        try:
            mr = create_member_request(name, args.email, args.password, args.login, swdd_person_id,
                                       room, args.move_in_date, args.previous_dorm)
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


api.add_resource(RegistrationResource,
                 '/register')


class EmailConfirmResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('key', required=True, type=str)
        args = parser.parse_args()

        try:
            confirm_mail_address(args.key)
        except ValueError:
            abort(400, message="Bad key", code="bad_key")

        session.session.commit()

        return


api.add_resource(EmailConfirmResource,  '/register/confirm')

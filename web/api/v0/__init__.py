from datetime import timedelta
from functools import wraps

from flask import jsonify, request, current_app
from flask_restful import Api, Resource as FlaskRestfulResource, abort, \
    reqparse, inputs
from ipaddr import IPAddress
from sqlalchemy.exc import IntegrityError

from pycroft import config
from pycroft.lib.finance import build_transactions_query
from pycroft.lib.host import change_mac, host_create, interface_create, \
    host_edit
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.traffic import effective_traffic_group, NoTrafficGroup
from pycroft.lib.user import encode_type2_user_id, edit_email, change_password, \
    status, traffic_history as func_traffic_history
from pycroft.model import session
from pycroft.model.host import IP, Interface, Host
from pycroft.model.types import IPAddress, InvalidMACAddressException
from pycroft.model.user import User, IllegalEmailError

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
    try:
        traffic_maxmium = effective_traffic_group(user).credit_limit
    except NoTrafficGroup:
        traffic_maxmium = None

    props = {prop.property_name for prop in user.current_properties}
    user_status = status(user)

    interval = timedelta(days=7)
    step = timedelta(days=1)
    traffic_history = func_traffic_history(user.id,
                                          session.utcnow() - interval + step,
                                          interval, step)

    finance_history = [{
        'valid_on': split.transaction.valid_on,
        # Invert amount, to display it from the user's point of view
        'amount': -split.amount,
        'description': split.transaction.description
    } for split in build_transactions_query(user.account, eagerload=True)]
    last_finance_update = finance_history[-1]['valid_on'] if finance_history \
        else None

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
        room=str(user.room),
        interfaces=[
            {'id': i.id, 'mac': str(i.mac),
             'ips': [str(ip.address) for ip in i.ips]}
            for h in user.hosts for i in h.interfaces
        ],
        mail=user.email,
        cache='cache_access' in props,
        # TODO: make `has_property` use `current_property`
        properties=list(props),
        traffic_balance=user.current_credit,
        traffic_maximum=traffic_maxmium,
        traffic_history=[e.__dict__ for e in traffic_history],
        # TODO: think about better way for credit
        finance_balance=-user.account.balance,
        finance_history=finance_history,
        last_finance_update=last_finance_update
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


# todo: traffic history

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
            if args.host_name is not None:
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

        interfaces = Interface.q.join(Host).filter(Host.owner_id == user.id).all()
        if len(interfaces) > 0:
            abort(412, message="User {} already has a host with interface.")

        user.birthdate = args.birthdate

        host = Host.q.filter_by(owner_id=user.id).one_or_none()

        try:
            if host is None:
                host = host_create(user, user.room, args.host_name, user)
            else:
                host.room = user.room

            interface_create(host, args.mac, None, user)

            session.session.commit()
        except InvalidMACAddressException:
            abort(400, message='Invalid mac address.')
        except IntegrityError:
            abort(400, message='Mac address is already in use.')
        return "Network access has been activated."


api.add_resource(ActivateNetworkAccessResource,
                 '/user/<int:user_id>/activate-network-access')


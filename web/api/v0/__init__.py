from operator import attrgetter

from flask import Blueprint, jsonify, request
from flask_restful import Api, Resource, abort, reqparse
from ipaddr import IPAddress
from sqlalchemy.exc import OperationalError

from pycroft.lib.traffic import effective_traffic_group
from pycroft.lib.user import encode_type2_user_id
from pycroft.model import session
from pycroft.model.host import IP, Interface
from pycroft.model.types import IPAddress
from pycroft.model.user import User

api = Api()


def get_user_or_404(user_id):
    user = User.q.get(user_id)
    if user is None:
        abort(404, message="User {} does not exist".format(user_id))
    return user

def get_interface_or_404(interface_id):
    interface = Interface.q.get(interface_id)
    if interface is None:
        abort(404, message="Interface {} does not exist".format(interface_id))
    return interface


class UserResource(Resource):
    def get(self, user_id):
        user = get_user_or_404(user_id)

        props = {prop.property_name for prop in user.current_properties}
        return jsonify(
            user_id=encode_type2_user_id(user_id),
            name=user.name,
            login=user.login,
            status="TBD",  # TODO: fix
            room=str(user.room),
            interfaces=[
                {'mac': str(i.mac), 'ips': [str(ip.address) for ip in i.ips]}
                for h in user.hosts for i in h.interfaces
            ],
            mail=user.email,
            cache='cache_access' in props,  # TODO: make `has_property` use `current_property`
            properties=list(props),
            traffic_balance=user.current_credit,
            traffic_maximum=effective_traffic_group(user).credit_limit,
            # TODO: think about better way for credit
            finance_balance=-user.account.balance,
            # TODO: add `last_finance_update` to library
        )

    def post(self):
        pass

    def change_email(self, email):
        # todo
        pass

    def change_password(self, plain_password):
        # todo
        pass

    def change_cache(self, use_cache):
        # todo
        pass

api.add_resource(UserResource, '/user/<int:user_id>')

class FinanceHistoryResource(Resource):
    def get(self, user_id):
        user = get_user_or_404(user_id)
        return jsonify([
            {'valid_on': s.transaction.valid_on.isoformat(), 'amount': s.amount}
            for s in sorted(user.account.splits, key=lambda s: s.transaction.valid_on)
        ])

api.add_resource(FinanceHistoryResource, '/user/<int:user_id>/finance-history')

# todo: traffic history

class AuthenticationResource(Resource):
    def post(self):
        auth_parser = reqparse.RequestParser()
        auth_parser.add_argument('login', dest='login', required=True)
        auth_parser.add_argument('password', dest='password', required=True)
        args = auth_parser.parse_args()

        user = User.verify_and_get(login=args.login, plaintext_password=args.password)
        if user is None:
            abort(401, msg="Authentication failed")
        return {'id': user.id}

api.add_resource(AuthenticationResource, '/user/authenticate')


class UserByIPResource(Resource):
    def get(self):
        ipv4 = request.args.get('ip', IPAddress)
        ip = IP.q.filter_by(address=ipv4).one()
        if ip is None:
            abort(404, msg="IP {} is not related to a user".format(ipv4))
        return {'id': ip.interface.host.owner.id}

api.add_resource(UserByIPResource, '/user/from-ip')


class UserInterfaceResource(Resource):
    def post(self, user_id, interface_id):
        user = get_user_or_404(user_id)
        interface = get_interface_or_404(interface_id)
        if interface.host.owner != user:
            abort(404, msg="User {} does not have a host with interface {}"
                  .format(user_id, interface_id))
        parser = reqparse.RequestParser()
        parser.add_argument('mac', dest='mac', required=True)
        args = parser.parse_args()

        interface.mac = args.mac
        session.session.add(interface)
        try:
            session.session.commit()
            # TODO: check what can go wrong if e.g. bad mac is supplied
            # or unique constraint is violated
        except OperationalError:
            session.session.rollback()
            raise

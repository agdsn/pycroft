# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from flask import url_for
from flask_wtf import FlaskForm as Form
from markupsafe import escape
from wtforms import Field
from wtforms.validators import (
    Regexp, ValidationError, DataRequired, Email, Optional)
from wtforms.widgets import HTMLString
from wtforms_widgets.fields.core import (
    TextField,
    TextAreaField,
    BooleanField,
    QuerySelectField,
    FormField,
    QuerySelectMultipleField,
    DateField,
    IntegerField,
    TimeField,
    DateTimeField,
)
from wtforms_widgets.fields.custom import MacField
from wtforms_widgets.fields.filters import empty_to_none, to_lowercase
from wtforms_widgets.fields.validators import OptionalIf, MacAddress

from pycroft.helpers import utc
from pycroft.lib.user import find_similar_users
from pycroft.model.address import Address
from pycroft.model.facilities import Room
from pycroft.model.host import Host
from pycroft.model.user import PropertyGroup, User
from web.blueprints.facilities.forms import building_query, SelectRoomForm, \
    CreateAddressForm
from web.blueprints.helpers.host import UniqueMac
from web.blueprints.properties.forms import property_group_query, \
    property_group_user_create_query
from web.form.widgets import UserIDField
from ..helpers.form import confirmable_div, ConfirmCheckboxField, \
    iter_prefixed_field_names


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


def validate_unique_login(form, field):
    if User.q.filter_by(login=field.data).first():
        raise ValidationError("Nutzerlogin schon vergeben!")


class UniqueName:
    """Checks whether the name of a user in a given building is unique.

    If the form misses one of the fields ``room_number``, ``level``, ``building``,
    this validator is effectively disabled.

    :param force_field: The name of the “do it anyway” checkbox field
    """
    def __init__(self, force_field: str | None = 'force'):
        self.force_field = force_field
        self.building_field = 'building'
        self.level_field = 'level'
        self.room_number_field = 'room_number'
        self.ratio = 0.6

    def force_set(self, form: Form) -> bool:
        return self.force_field \
               and hasattr(form, self.force_field)\
               and getattr(form, self.force_field).data

    def try_get_room(self, form: Form) -> Room | None:
        try:
            number = getattr(form, self.room_number_field).data
            level = getattr(form, self.level_field).data
            building = getattr(form, self.building_field).data
        except AttributeError:
            return

        return Room.q.filter_by(number=number, level=level, building=building).one_or_none()

    def __call__(self, form: Form, field: Field):
        if self.force_set(form):
            return
        if (room := self.try_get_room(form)) is None:
            return
        if not (conflicting_inhabitants := find_similar_users(name=field.data, room=room,
                                                              ratio=self.ratio)):
            return

        user_links = ", ".join(
            f"""<a target="_blank" href="{url_for('user.user_show', user_id=user.id)}"/>
                  {escape(user.name)}
                </a>""" for user in conflicting_inhabitants
        )
        raise ValidationError(HTMLString(
            f'{confirmable_div(self.force_field)}'
            f'* Ähnliche Benutzer existieren bereits in diesem Zimmer:'
            f'<br/>Nutzer: {user_links}</div>'
        ))


class UniqueEmail:
    """Checks whether a given email is unique, i.e. already assigned to some user.

    :param force_field: The name of the “do it anyway” checkbox field
    """
    def __init__(self, force_field: str | None = 'force'):
        self.force_field = force_field

    def force_set(self, form: Form) -> bool:
        return self.force_field \
               and hasattr(form, self.force_field)\
               and getattr(form, self.force_field).data

    @staticmethod
    def get_conflicting_users(email: str) -> list[User]:
        return User.q.filter_by(email=email).all()

    def __call__(self, form: Form, field: Field):
        if self.force_set(form):
            return
        if not (conflicting_users := self.get_conflicting_users(field.data)):
            return

        user_links = ", ".join(
            f"""<a target="_blank" href="{url_for('user.user_show', user_id=user.id)}"/>
                {escape(user.name)}</a>""" for user in conflicting_users
        )
        raise ValidationError(HTMLString(
            f"{confirmable_div(self.force_field)}* E-Mail bereits in Verwendung!"
            f"<br/>Nutzer:{user_links}</div>"
        ))


class UserSearchForm(Form):
    id = TextField("Nutzer-ID")
    name = TextField("Name")
    login = TextField("Unix-Login")
    mac = MacField("MAC-Adresse")
    ip_address = TextField("IP-Adresse")
    property_group_id = QuerySelectField("Eigenschaftsgruppe",
                                get_label='name',
                                query_factory=property_group_query,
                                allow_blank=True,
                                blank_text="<Eigenschaftsgruppe>")
    building_id = QuerySelectField("Wohnheim",
                                get_label='short_name',
                                query_factory=building_query,
                                allow_blank=True,
                                blank_text="<Wohnheim>")
    email = TextField("E-Mail")
    person_id = TextField("Debitorennummer")


class UserResetPasswordForm(Form):
    pass


class UserEditForm(Form):
    name = TextField("Name", [DataRequired(message="Name wird benötigt!")])
    email = TextField("E-Mail",
                      [Optional(), Email("E-Mail-Adresse ist ungültig!")])
    email_forwarded = BooleanField("E-Mail Weiterleitung", default=True)
    birthdate = DateField("Geburtsdatum", [Optional()])
    person_id = IntegerField("Debitorennummer", [Optional()],
                             filters=[empty_to_none])


class UserEditAddressForm(CreateAddressForm):
    def set_defaults_from_adress(self, address: Address):
        self.address_street.data = address.street
        self.address_number.data = address.number
        self.address_zip_code.data = address.zip_code
        self.address_city.data = address.city
        self.address_state.data = address.state
        self.address_country.data = address.country


class UserMoveForm(SelectRoomForm):
    comment = TextAreaField("Kommentar", description='Wenn gegeben Referenz zum Ticket',
                            render_kw={'placeholder': 'ticket#<TicketNr> / <TicketNr> / ticket:<ticketId>'})
    now = BooleanField("Sofort", default=False)
    when = DateTimeField(
        "Umzug am",
        [OptionalIf("now")],
        render_kw={"placeholder": "YYYY-MM-DDThh:mm:ssZ"},
    )


class UserBaseDataForm(Form):
    name = TextField("Name", [DataRequired(message="Name wird benötigt!"),
                               UniqueName()])

    login = TextField("Login", [
        DataRequired(message="Login wird benötigt!"),
        Regexp(regex=User.login_regex_ci, message="Login ist ungültig!"),
        validate_unique_login
    ], filters=[to_lowercase])
    email = TextField("E-Mail", [Email(message="E-Mail ist ungueltig!"),
                                  Optional()], filters=[empty_to_none])


class UserCreateForm(UserBaseDataForm, SelectRoomForm):
    birthdate = DateField("Geburtsdatum",
                          [OptionalIf('mac', invert=True)])
    mac = MacField("MAC",
                   [Optional(), MacAddress(message="MAC ist ungültig!"), UniqueMac()])
    property_groups = QuerySelectMultipleField("Gruppen",
                                      get_label='name',
                                      query_factory=property_group_user_create_query)
    annex = ConfirmCheckboxField("Host annektieren")
    force = ConfirmCheckboxField("* Hinweise ignorieren")

    _order = ("name", "building", "level", "room_number")


class NonResidentUserCreateForm(UserBaseDataForm, CreateAddressForm):
    """User creation form for non-resident folks.

    Does not contain mac, since created hosts would not have a room set, anyway.
    If necessary, a device can be created afterwards.
    """
    birthdate = DateField("Geburtsdatum")
    property_groups = QuerySelectMultipleField("Gruppen",
                                      get_label='name',
                                      query_factory=property_group_user_create_query)

    _order = (
        'name', 'login',
        *iter_prefixed_field_names(CreateAddressForm, 'address_'),
        'email', 'birthdate', 'property_groups'
    )


class PreMemberEditForm(UserBaseDataForm, SelectRoomForm):
    # overrides `email` from UserBaseDataForm
    email = TextField("E-Mail", [DataRequired("Mitgliedschaftsanfragen benötigen E-Mail"),
                                 Email(message="E-Mail ist ungueltig!")], filters=[empty_to_none])
    birthdate = DateField("Geburtsdatum", [DataRequired("Das Geburtsdatum wird benötigt!")])
    move_in_date = DateField("Einzugsdatum", [Optional()])
    person_id = IntegerField("Debitorennummer", [Optional()], filters=[empty_to_none])

    force = ConfirmCheckboxField("* Hinweise ignorieren")

    _order = ("name", "building", "level", "room_number")


class PreMemberDenyForm(Form):
    reason = TextAreaField("Begründung", [Optional()], filters=[empty_to_none])
    inform_user = BooleanField("Nutzer per E-Mail informieren", [Optional()], default=True)


class PreMemberMergeForm(Form):
    user_id = UserIDField("User-ID", [DataRequired("Nutzer-ID erforderlich!")])


class PreMemberMergeConfirmForm(Form):
    merge_name = BooleanField("Name", [Optional()], default=True)
    merge_email = BooleanField("E-Mail", [Optional()], default=True)
    merge_person_id = BooleanField("Debitorennummer", [Optional()], default=True)
    merge_room = BooleanField("Einzug/Umzug", [Optional()], default=True)
    merge_password = BooleanField("Passwort aus der Registrierung", [Optional()], default=False)
    merge_birthdate = BooleanField("Geburtsdatum", [Optional()], default=False)


class UserMoveInForm(UserMoveForm):
    now = BooleanField("Sofort", default=False)
    when = DateField("Einzug am", [OptionalIf("now")])
    birthdate = DateField("Geburtsdatum", [OptionalIf('mac', invert=True)])
    mac = MacField("MAC", [Optional()])
    begin_membership = BooleanField("Mitgliedschaft beginnen", [Optional()])


class UserLogEntry(Form):
    message = TextAreaField("", [DataRequired()])


class OptionallyDirectBeginDateForm(Form):
    now = BooleanField("Sofort", default=False)
    date = DateField("Beginn", [OptionalIf("now")])


class OptionallyUnlimitedEndDateForm(Form):
    unlimited = BooleanField("Unbegrenzte Dauer", default=False)
    date = DateField("Ende", [OptionalIf("unlimited")])


class UserAddGroupMembership(Form):
    group = QuerySelectField("Gruppe", get_label='name',
                             query_factory=group_query)
    begins_at = FormField(OptionallyDirectBeginDateForm)
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserEditGroupMembership(Form):
    begins_at = DateField("Beginn", [DataRequired()])
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserSuspendForm(Form):
    ends_at = FormField(OptionallyUnlimitedEndDateForm)
    reason = TextAreaField("Grund", [DataRequired()])
    violation = BooleanField("Verstoß")


class UserMoveOutForm(Form):
    now = BooleanField("Sofort", default=False)
    when = DateField("Auszug am", [OptionalIf("now")])
    comment = TextAreaField("Kommentar")
    end_membership = BooleanField("Mitgliedschaft/Extern beenden", [Optional()])


class GroupMailForm(Form):
    group = QuerySelectField("Gruppe", [DataRequired()], get_label='name', query_factory=group_query)
    subject = TextField("Betreff", [DataRequired()])
    body_plain = TextAreaField("E-Mail (plaintext)", [DataRequired()],
                               description="Verfügbar: {name}, {login}, {id}, {email}, "
                                           "{email_internal}, {room_short}, {swdd_person_id}")
    confirm = BooleanField("Bestätigung", [DataRequired()], default=False)

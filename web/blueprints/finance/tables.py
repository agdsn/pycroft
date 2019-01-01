from flask import url_for
from flask_babel import gettext
from flask_login import current_user

from web.blueprints.helpers.lazy_join import lazy_join

from web.blueprints.helpers.table import BootstrapTable, Column, SplittedTable, \
    BtnColumn, LinkColumn, button_toolbar, DateColumn, MultiBtnColumn
from web.template_filters import money_filter


class FinanceTable(BootstrapTable):
    class Meta:
        table_args = {
            'data-side-pagination': 'server',
            # 'data-search': 'true',
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }
        enforced_url_params = {
            'style': 'inverted',
        }

    def __init__(self, *a, saldo=None, user_id=None, inverted=False, **kw):
        """Init

        :param int user_id: An optional user_id.  If set, this causes
            a “details” button to be rendered in the toolbar
            referencing the user.
        :param bool inverted: An optional switch adding
            `style=inverted` to the given `data_url`
        """
        super().__init__(*a, **kw)

        if inverted:
            self.saldo = -saldo
        else:
            self.saldo = saldo

        self.user_id = user_id
        self.table_footer_offset = 3

    posted_at = Column("Erstellt um")
    valid_on = Column("Gültig am")
    description = LinkColumn("Beschreibung")
    amount = Column("Wert",
                    formatter='table.coloredFormatter',
                    cell_style='table.tdRelativeCellStyle')

    @property
    def toolbar(self):
        """Generate a toolbar with a details button

        If a user_id was passed in the constructor, this renders a
        “details” button reaching the finance overview of the user's account.
        """
        if self.user_id is None:
            return
        href = url_for("user.user_account", user_id=self.user_id)
        return button_toolbar("Details", href, icon="glyphicon-stats")

    @property
    @lazy_join
    def table_footer(self):
        yield "<tfoot>"
        yield "<tr>"

        yield f"<td colspan=\"{self.table_footer_offset}\" class=\"text-right\">"
        yield "<strong>Saldo:</strong>"
        yield "</td>"

        yield "<td>"
        yield "{}".format(money_filter(self.saldo)
                          if self.saldo is not None else "-")
        yield "</td>"

        yield "</tr>"
        yield "</tfoot>"


class FinanceTableSplitted(FinanceTable, SplittedTable):
    class Meta:
        table_args = {
            'data-row-style': False,
            'data-sort-name': False,  # the "valid_on" col doesn't exist here
        }
        enforced_url_params = {'splitted': True}

    splits = (('soll', "Soll"), ('haben', "Haben"))

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.table_footer_offset = 7


def no_finance_change():
    return not current_user.has_property('finance_change')


class MembershipFeeTable(BootstrapTable):
    """A table for displaying the current membership fees"""
    name = Column("Name")
    regular_fee = Column("Regulär")
    payment_deadline = Column("Frist")
    payment_deadline_final = Column("Endgültige Frist")
    begins_on = DateColumn("Beginn")
    ends_on = DateColumn("Ende")
    finance_link = BtnColumn("Finanzen")
    book_link = BtnColumn("Buchen", hide_if=no_finance_change)
    edit_link = BtnColumn("Bearbeiten", hide_if=no_finance_change)

    @property
    def toolbar(self):
        """An “add fee” button"""
        href = url_for(".membership_fee_create")
        return button_toolbar(gettext("Beitrag erstellen"), href)


class UsersDueTable(BootstrapTable):
    """A table for displaying the users that """
    user_id = Column("Nutzer-ID")
    user = LinkColumn("Name")
    valid_on = Column("Gültig am")
    description = Column("Beschreibung")
    amount = Column("Betrag', formatter='table.coloredFormatter")


class BankAccountTable(BootstrapTable):
    """A table for displaying bank accounts

    :param bool create_account: An optional switch adding
        a “create bank account” button to the toolbar
    """
    name = Column("Name")
    bank = Column("Bank")
    ktonr = Column("Kontonummer")
    blz = Column("Bankleitzahl")
    iban = Column("IBAN")
    bic = Column("SWIFT-BIC")
    kto = BtnColumn("Konto")
    last_imported_at = Column("Zuletzt importiert")

    def __init__(self, *a, create_account=False, **kw):
        self.create_account = create_account
        super().__init__(*a, **kw)

    @property
    def toolbar(self):
        """A “create bank account” button"""
        if not self.create_account:
            return
        href = url_for(".bank_accounts_create")
        return button_toolbar(gettext("Neues Bankkonto anlegen"), href)


class BankAccountActivityTable(BootstrapTable):
    """A table for displaying bank account activities """
    bank_account = Column("Bankkonto")
    name = Column("Name")
    valid_on = DateColumn("Gültig am")
    imported_at = DateColumn("Importiert am")
    reference = Column("Verwendungszweck")
    iban = Column("IBAN")
    amount = Column("Betrag")
    actions = MultiBtnColumn("Aktionen")

    class Meta:
        table_args = {
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }


class TransactionTable(BootstrapTable):
    """A table for displaying bank account activities """
    account = LinkColumn("Konto")
    amount = Column("Wert")

    class Meta:
        table_args = {
            'data-row-style': 'table.financeRowFormatter',
        }


class ImportErrorTable(BootstrapTable):
    """A table for displaying buggy mt940 imports"""
    name = Column("Bankkonto")
    imported_at = Column("Importiert am")
    fix = BtnColumn("Importieren")

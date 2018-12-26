from flask import url_for
from flask_babel import gettext
from wtforms.widgets.core import html_params

from web.blueprints.helpers.table import BootstrapTable, Column, SplittedTable
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

    posted_at = Column("Erstellt um")
    valid_on = Column("Gültig am")
    description = Column("Beschreibung", formatter='table.linkFormatter')
    amount = Column("Wert",
                    formatter='table.coloredFormatter',
                    cell_style='table.tdRelativeCellStyle')

    def generate_toolbar(self):
        """Generate a toolbar with a details button

        If a user_id was passed in the constructor, this renders a
        “details” button reaching the finance overview of the user's account.
        """
        if self.user_id is None:
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for("user.user_account", user_id=self.user_id)
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-stats\"></span>"
        yield "Details"
        yield "</a>"

    def generate_table_footer(self, offset=3):
        yield "<tfoot>"
        yield "<tr>"

        yield "<td colspan=\"{}\" class=\"text-right\">".format(offset)
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

    def generate_table_footer(self, offset=7):
        return super().generate_table_footer(offset=offset)


class MembershipFeeTable(BootstrapTable):
    """A table for displaying the current membership fees"""
    name = Column("Name")
    regular_fee = Column("Regulär")
    payment_deadline = Column("Frist")
    payment_deadline_final = Column("Endgültige Frist")
    begins_on = Column("Beginn", formatter='table.dateFormatter')
    ends_on = Column("Ende", formatter='table.dateFormatter')
    finance_link = Column("Finanzen", formatter='table.btnFormatter')
    book_link = Column("Buchen", formatter='table.btnFormatter')
    edit_link = Column("Bearbeiten", formatter='table.btnFormatter')

    def generate_toolbar(self):
        """An “add fee” button"""
        args = {
            'class': "btn btn-primary",
            'href': url_for(".membership_fee_create")
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield gettext("Beitrag erstellen")
        yield "</a>"


class UsersDueTable(BootstrapTable):
    """A table for displaying the users that """
    user_id = Column("Nutzer-ID")
    user = Column("Name', formatter='table.linkFormatter")
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
    kto = Column("Konto", formatter='table.btnFormatter')
    last_imported_at = Column("Zuletzt importiert")

    def __init__(self, *a, create_account=False, **kw):
        self.create_account = create_account
        super().__init__(*a, **kw)

    def generate_toolbar(self):
        """A “create bank account” button"""
        if self.create_account:
            args = {
                'class': "btn btn-primary",
                'href': url_for(".bank_accounts_create")
            }
            yield "<a {}>".format(html_params(**args))
            yield "<span class=\"glyphicon glyphicon-plus\"></span>"
            yield gettext("Neues Bankkonto anlegen")
            yield "</a>"


class BankAccountActivityTable(BootstrapTable):
    """A table for displaying bank account activities """
    bank_account = Column("Bankkonto")
    name = Column("Name")
    valid_on = Column("Gültig am", formatter='table.dateFormatter')
    imported_at = Column("Importiert am", formatter='table.dateFormatter')
    reference = Column("Verwendungszweck")
    iban = Column("IBAN")
    amount = Column("Betrag")
    actions = Column("Aktionen", formatter='table.multiBtnFormatter')

    class Meta:
        table_args = {
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }


class TransactionTable(BootstrapTable):
    """A table for displaying bank account activities """
    account = Column("Konto", formatter='table.linkFormatter')
    amount = Column("Wert")

    class Meta:
        table_args = {
            'data-row-style': 'table.financeRowFormatter',
        }


class ImportErrorTable(BootstrapTable):
    """A table for displaying buggy mt940 imports"""
    name = Column("Bankkonto")
    imported_at = Column("Importiert am")
    fix = Column("Importieren", formatter='table.btnFormatter')

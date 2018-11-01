from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from flask import url_for
from flask_babel import gettext
from wtforms.widgets.core import html_params

from web.blueprints.helpers.table import BootstrapTable, Column, SplittedTable
from web.template_filters import money_filter


def enforce_url_params(url, params):
    """Safely enforce query values in an url

    :param str url: The url to patch
    :param dict params: The parameters to enforce in the URL query
        part
    """
    # we need to use a list because of mutability
    url_parts = list(urlparse(url))
    query_parts = dict(parse_qsl(url_parts[4]))
    query_parts.update(params)
    url_parts[4] = urlencode(query_parts)
    return urlunparse(url_parts)


class FinanceTable(BootstrapTable):
    def __init__(self, *a, saldo=None, user_id=None, inverted=False, **kw):
        """Init

        :param int user_id: An optional user_id.  If set, this causes
            a “details” button to be rendered in the toolbar
            referencing the user.
        :param bool inverted: An optional switch adding
            `style=inverted` to the given `data_url`
        """
        table_args = {
            'data-side-pagination': 'server',
            # 'data-search': 'true',
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }
        original_table_args = kw.pop('table_args', {})
        table_args.update(original_table_args)

        if 'data_url' in kw and inverted:
            kw['data_url'] = enforce_url_params(kw['data_url'],
                                                params={'style': 'inverted'})

        super().__init__(*a, columns=[
            Column(name='posted_at', title='Erstellt um'),
            Column(name='valid_on', title='Gültig am'),
            Column(name='description', title='Beschreibung',
                   formatter='table.linkFormatter'),
            Column(name='amount', title='Wert',
                   formatter='table.coloredFormatter',
                   cell_style='table.tdRelativeCellStyle'),
        ], table_args=table_args, **kw)

        if inverted:
            self.saldo = -saldo
        else:
            self.saldo = saldo

        self.user_id = user_id

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
    def __init__(self, *a, **kw):
        splits = (('soll', "Soll"), ('haben', "Haben"))
        table_args = {
            'data-row-style': False,
            'data-sort-name': False,  # the "valid_on" col doesn't exist here
        }
        table_args.update(kw.pop('table_args', {}))
        if 'data_url' in kw:
            kw['data_url'] = enforce_url_params(kw['data_url'],
                                                params={'splitted': True})
        super().__init__(*a, splits=splits, table_args=table_args, **kw)

    def generate_table_footer(self, offset=7):
        return super().generate_table_footer(offset=offset)


class MembershipFeeTable(BootstrapTable):
    """A table for displaying the current membership fees"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column(name='name', title='Name'),
            Column(name='regular_fee', title='Regulär'),
            Column(name='payment_deadline', title='Frist'),
            Column(name='payment_deadline_final', title='Endgültige Frist'),
            Column(name='begins_on', title='Beginn', formatter='table.dateFormatter'),
            Column(name='ends_on', title='Ende', formatter='table.dateFormatter'),
            Column(name='finance_link', title='Finanzen', formatter='table.btnFormatter'),
            Column(name='book_link', title='Buchen', formatter='table.btnFormatter'),
            Column(name='edit_link', title='Bearbeiten', formatter='table.btnFormatter'),
        ], **kw)

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
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column(name='user_id', title='Nutzer-ID'),
            Column(name='user', title='Name', formatter='table.linkFormatter'),
            Column(name='valid_on', title='Gültig am'),
            Column(name='description', title='Beschreibung'),
            Column(name='amount', title='Betrag', formatter='table.coloredFormatter'),
        ], **kw)

class BankAccountTable(BootstrapTable):
    """A table for displaying bank accounts

    :param bool create_account: An optional switch adding
        a “create bank account” button to the toolbar
    """
    def __init__(self, *a, create_account=False, **kw):
        self.create_account = create_account
        super().__init__(*a, columns=[
            Column(name='name', title='Name'),
            Column(name='bank', title='Bank'),
            Column(name='ktonr', title='Kontonummer'),
            Column(name='blz', title='Bankleitzahl'),
            Column(name='iban', title='IBAN'),
            Column(name='bic', title='SWIFT-BIC'),
            Column(name='kto', title='Konto', formatter='table.btnFormatter'),
            Column(name='last_imported_at', title='Zuletzt importiert'),
        ], **kw)

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
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column(name='bank_account', title='Bankkonto'),
            Column(name='name', title='Name'),
            Column(name='valid_on', title='Gültig am', formatter='table.dateFormatter'),
            Column(name='imported_at', title='Importiert am', formatter='table.dateFormatter'),
            Column(name='reference', title='Verwendungszweck'),
            Column(name='iban', title='IBAN'),
            Column(name='amount', title='Betrag'),
            Column(name='actions', title='Aktionen', formatter='table.multiBtnFormatter'),
        ], table_args = {
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }, **kw)


class TransactionTable(BootstrapTable):
    """A table for displaying bank account activities """
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column(name='account', title='Konto', formatter='table.linkFormatter'),
            Column(name='amount', title='Wert'),
        ], table_args = {
            'data-row-style': 'table.financeRowFormatter',
        }, **kw)

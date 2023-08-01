import typing
from decimal import Decimal

from flask import url_for
from flask_babel import gettext
from flask_login import current_user
from pydantic import BaseModel

from web.table.table import (
    lazy_join,
    DictValueMixin,
    custom_formatter_column,
    IbanColumn,
    DateColResponse,
    BtnColResponse,
    TableResponse,
    LinkColResponse,
)

from web.table.table import BootstrapTable, Column, SplittedTable, \
    BtnColumn, LinkColumn, button_toolbar, DateColumn, MultiBtnColumn
from web.template_filters import money_filter


@custom_formatter_column('table.coloredFormatter')
class ColoredColumn(DictValueMixin, Column):
    if typing.TYPE_CHECKING:
        @classmethod
        def value(cls, value: str, is_positive: bool) -> dict:  # type: ignore[override]
            ...


class ColoredColResponse(BaseModel):
    value: str
    is_positive: bool


class FinanceTable(BootstrapTable):
    class Meta:
        table_args = {
            'data-side-pagination': 'server',
            # 'data-search': 'true',
            'data-sort-order': 'desc',
            # 'data-sort-name': 'valid_on',
            'data-page-list': '[5, 10, 25, 50, 100]'
        }

    def __init__(self, *a, saldo=None, user_id=None, inverted=False, **kw):
        """Init

        :param int user_id: An optional user_id.  If set, this causes
            a “details” button to be rendered in the toolbar
            referencing the user.
        :param bool inverted: An optional switch adding
            `style=inverted` to the given `data_url`
        """

        self.saldo = saldo

        if inverted:
            self._enforced_url_params = frozenset(
                {('style', 'inverted')}
                .union(self._enforced_url_params)
            )
            self.saldo = -saldo

        super().__init__(*a, **kw)


        self.user_id = user_id
        self.table_footer_offset = 3

    posted_at = Column("Erstellt um")
    valid_on = Column("Gültig am")
    description = LinkColumn("Beschreibung")
    amount = ColoredColumn("Wert", cell_style='table.tdRelativeCellStyle')

    @property
    def toolbar(self):
        """Generate a toolbar with a details button

        If a user_id was passed in the constructor, this renders a
        “details” button reaching the finance overview of the user's account.
        """
        if self.user_id is None:
            return
        href = url_for("user.user_account", user_id=self.user_id)
        return button_toolbar("Details", href, icon="fa-chart-area")

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


class FinanceRow(BaseModel):
    posted_at: str
    valid_on: str
    description: LinkColResponse
    amount: ColoredColResponse
    row_positive: bool


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
    actions = MultiBtnColumn("Aktionen")

    @property
    def toolbar(self):
        """An “add fee” button"""
        href = url_for(".membership_fee_create")
        return button_toolbar(gettext("Beitrag erstellen"), href)


class MembershipFeeRow(BaseModel):
    name: str
    regular_fee: str
    payment_deadline: int
    payment_deadline_final: int
    begins_on: DateColResponse
    ends_on: DateColResponse
    actions: list[BtnColResponse]


class UsersDueTable(BootstrapTable):
    """A table for displaying the users that """
    user_id = Column("Nutzer-ID")
    user = LinkColumn("Name")
    valid_on = Column("Gültig am")
    description = Column("Beschreibung")
    fee_account_id = LinkColumn("Beitragskonto")
    amount = Column("Betrag", formatter="table.coloredFormatter")


class UsersDueRow(BaseModel):
    user_id: int
    user: LinkColResponse
    valid_on: str
    description: str
    fee_account_id: LinkColResponse
    amount: ColoredColResponse


class BankAccountTable(BootstrapTable):
    """A table for displaying bank accounts

    :param bool create_account: An optional switch adding
        a “create bank account” button to the toolbar
    """
    name = Column("Name")
    bank = Column("Bank")
    iban = IbanColumn("IBAN")
    bic = Column("SWIFT-BIC")
    balance = Column("Saldo")
    last_imported_at = Column("Zuletzt importiert")
    kto = BtnColumn("Konto")

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


class BankAccountRow(BaseModel):
    name: str
    bank: str
    iban: str
    bic: str
    kto: BtnColResponse
    balance: str
    last_imported_at: str  # TODO perhaps date


class BankAccountActivityTable(BootstrapTable):
    """A table for displaying bank account activities"""

    bank_account = Column("Bankkonto", width=1)
    name = Column("Name", width=2)
    valid_on = DateColumn("Gültig am", width=1)
    imported_at = DateColumn("Importiert am", hide_if=lambda: True)
    reference = Column("Verwendungszweck")
    iban = Column("IBAN", hide_if=lambda: True)
    amount = Column("Betrag", width=1, formatter="table.euroFormatter")
    actions = MultiBtnColumn("Aktionen", width=1)

    def __init__(self, *a, **kw):
        table_args = kw.pop('table_args', {})
        table_args.setdefault('data-detail-view', "true")
        table_args.setdefault('data-row-style', "table.financeRowFormatter")
        table_args.setdefault('data-detail-formatter', "table.bankAccountActivitiesDetailFormatter")
        kw['table_args'] = table_args

        super().__init__(*a, **kw)

    class Meta:
        table_args = {
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }


class BankAccountActivityRow(BaseModel):
    bank_account: str
    name: str
    valid_on: DateColResponse
    imported_at: DateColResponse
    reference: str
    iban: str
    amount: Decimal
    actions: list[BtnColResponse]
    row_positive: bool


class TransactionTable(BootstrapTable):
    """A table for displaying bank account activities """
    account = LinkColumn("Konto")
    amount = Column("Wert")

    class Meta:
        table_args = {
            'data-row-style': 'table.financeRowFormatter',
        }


class TransactionSplitRow(BaseModel):
    account: LinkColResponse
    amount: str
    row_positive: bool


class TransactionSplitResponse(TableResponse[TransactionSplitRow]):
    description: str


class UnconfirmedTransactionsTable(BootstrapTable):
    """A table for displaying unconfirmed transactions """
    selection = Column("Checkbox", col_args={"data-checkbox": "true"})
    id = Column("id")
    description = LinkColumn("Beschreibung")
    user = LinkColumn("Nutzer")
    room = Column("Wohnort")
    date = DateColumn("Datum")
    amount = Column("Wert")
    author = LinkColumn("Ersteller")
    actions = MultiBtnColumn("Aktionen")


class UnconfirmedTransactionsRow(BaseModel):
    id: str | int
    description: LinkColResponse
    user: LinkColResponse | None
    room: str | None
    date: DateColResponse
    amount: str
    author: LinkColResponse
    actions: list[BtnColResponse]


class ImportErrorTable(BootstrapTable):
    """A table for displaying buggy mt940 imports"""
    name = Column("Bankkonto")
    imported_at = Column("Importiert am")
    fix = BtnColumn("Importieren")


class ImportErrorRow(BaseModel):
    name: str
    imported_at: str
    fix: BtnColResponse

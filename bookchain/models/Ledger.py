from __future__ import annotations
from .Account import Account, AccountType
from .LedgerType import LedgerType
from sqloquent import (
    HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol,
)


class Ledger(HashedModel):
    connection_info: str = ''
    table: str = 'ledgers'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'type', 'identity_id', 'currency_id', 'description'
    )
    columns_excluded_from_hash: tuple[str] = ('description',)
    id: str
    name: str
    type: str
    identity_id: str
    currency_id: str
    description: str|None
    owner: RelatedModel
    currency: RelatedModel
    accounts: RelatedCollection
    transactions: RelatedCollection
    archived_transactions: RelatedCollection
    rollups: RelatedCollection

    @property
    def type(self) -> LedgerType:
        """The LedgerType of the Ledger."""
        return LedgerType(self.data['type'])
    @type.setter
    def type(self, val: LedgerType):
        if isinstance(val, LedgerType):
            self.data['type'] = val.value

    @classmethod
    def _encode(cls, data: dict) -> dict:
        """Encode Ledger data without modifying the original dict."""
        if not isinstance(data, dict):
            return data
        data = {**data}
        if isinstance(data.get('type', None), LedgerType):
            data['type'] = data['type'].value
        return data

    @classmethod
    def insert(cls, data: dict) -> Ledger | None:
        """Ensure data is encoded before inserting."""
        return super().insert(cls._encode(data))

    @classmethod
    def insert_many(cls, items: list[dict], /, *, suppress_events: bool = False) -> int:
        """Ensure items are encoded before inserting."""
        items = [cls._encode(item) for item in items]
        return super().insert_many(items, suppress_events=suppress_events)

    def update(self, updates: dict, /, *, suppress_events: bool = False) -> Ledger:
        """Ensure updates are encoded before updating."""
        return super().update(self._encode(updates), suppress_events=suppress_events)

    @classmethod
    def query(cls, conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:
        """Ensure conditions are encoded before querying."""
        return super().query(cls._encode(conditions), connection_info)

    def balances(self, reload: bool = False) -> dict[str, tuple[int, AccountType]]:
        """Return a dict mapping account ids to their balances. Accounts
            with sub-accounts will not include the sub-account balances;
            the sub-account balances will be returned separately.
        """
        balances = {}
        if reload:
            self.accounts().reload()
        for account in self.accounts:
            balances[account.id] = (account.balance(False), account.type)
        return balances

    def setup_basic_accounts(self) -> list[Account]:
        """Creates and returns a list of 3 unsaved Accounts covering the
            3 basic categories: Asset, Liability, Equity.
        """
        asset = Account({
            'name': f'General Asset ({self.owner.name})',
            'type': AccountType.ASSET,
            'ledger_id': self.id,
            'code': '1xx'
        })
        liability = Account({
            'name': f'General Liability ({self.owner.name})',
            'type': AccountType.LIABILITY,
            'ledger_id': self.id,
            'code': '2xx'
        })
        equity = Account({
            'name': f'General Equity ({self.owner.name})',
            'type': AccountType.EQUITY,
            'ledger_id': self.id,
            'code': '28x'
        })
        return [asset, liability, equity]

from __future__ import annotations
from .Account import Account, AccountType
from .LedgerType import LedgerType
from sqloquent.asyncql import AsyncHashedModel, AsyncRelatedModel, AsyncRelatedCollection


class Ledger(AsyncHashedModel):
    connection_info: str = ''
    table: str = 'ledgers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'type', 'identity_id', 'currency_id')
    id: str
    name: str
    type: str
    identity_id: str
    currency_id: str
    owner: AsyncRelatedModel
    currency: AsyncRelatedModel
    accounts: AsyncRelatedCollection
    transactions: AsyncRelatedCollection

    @property
    def type(self) -> LedgerType:
        return LedgerType(self.data['type'])
    @type.setter
    def type(self, val: LedgerType):
        if isinstance(val, LedgerType):
            self.data['type'] = val.value

    async def balances(self, reload: bool = False) -> dict[str, tuple[int, AccountType]]:
        """Return a dict mapping account ids to their balances. Accounts
            with sub-accounts will not include the sub-account balances;
            the sub-account balances will be returned separately.
        """
        balances = {}
        if reload:
            await self.accounts().reload()
        for account in self.accounts:
            balances[account.id] = (await account.balance(False), account.type)
        return balances

    @classmethod
    async def insert(cls, data: dict) -> Ledger | None:
        if 'type' in data and isinstance(data['type'], LedgerType):
            data['type'] = data['type'].value
        return await super().insert(data)

    @classmethod
    async def insert_many(cls, items: list[dict], /, *, suppress_events: bool = False) -> int:
        for item in items:
            if 'type' in item and isinstance(item['type'], LedgerType):
                item['type'] = item['type'].value
        return await super().insert_many(items, suppress_events=suppress_events)

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

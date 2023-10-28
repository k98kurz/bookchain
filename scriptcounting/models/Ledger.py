from __future__ import annotations
from .AccountType import AccountType
from sqloquent import HashedModel, RelatedModel, RelatedCollection


class Ledger(HashedModel):
    connection_info: str = ''
    table: str = 'ledgers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'identity_id', 'currency_id')
    id: str
    name: str
    identity_id: str
    currency_id: str
    owner: RelatedModel
    currency: RelatedModel
    accounts: RelatedCollection
    transactions: RelatedCollection

    def balances(self, reload: bool = False) -> dict[str, tuple[int, AccountType]]:
        """Return a dict mapping account ids to their balances."""
        balances = {}
        if reload:
            self.accounts().reload()
        for account in self.accounts:
            balances[account.id] = (account.balance(reload), account.type)
        return balances

    @classmethod
    def find(cls, id: str) -> Ledger:
        # """For better type hints."""
        return super().find(id)

    @classmethod
    def insert(cls, data: dict) -> Ledger | None:
        # """For better type hints."""
        return super().insert(data)

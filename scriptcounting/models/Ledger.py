from __future__ import annotations
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

    def balances(self) -> dict:
        ...

    @classmethod
    def find(cls, id: str) -> Ledger:
        # """For better type hints."""
        return super().find(id)

    @classmethod
    def insert(cls, data: dict) -> Ledger | None:
        # """For better type hints."""
        return super().insert(data)

from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol
from .AccountType import AccountType


class Account(HashedModel):
    connection_info: str = ''
    table: str = 'accounts'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'type', 'ledger_id', 'locking_script', 'details')
    id: str
    name: str
    type: str
    ledger_id: str
    locking_script: bytes
    details: str|None
    ledger: RelatedModel
    entries: RelatedCollection

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is dict and 'type' in data and type(data['type']) is AccountType:
            data['type'] = data['type'].value
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is dict and 'type' in data and type(data['type']) is str:
            data['type'] = AccountType(data['type'])
        return data

    @staticmethod
    def parse(models: Account|list[Account]) -> Account|list[Account]:
        if type(models) is list:
            for model in models:
                model.data = Account._parse(model.data)
        else:
            models.data = Account._parse(models.data)
        return models

    @classmethod
    def insert(cls, data: dict) -> Account | None:
        result = super().insert(cls._encode(data))
        if result is not None:
            result.data = cls._parse(result.data)
        return result

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        return super().query(cls._encode(conditions))

    @classmethod
    def find(cls, id: str) -> Account | None:
        """For better type hinting."""
        return super().find(id)

    def balance(self) -> int:
        ...

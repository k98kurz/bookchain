from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol
from tapescript import run_auth_script
from .AccountType import AccountType
from .EntryType import EntryType


class Account(HashedModel):
    connection_info: str = ''
    table: str = 'accounts'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'type', 'ledger_id', 'locking_script', 'details')
    id: str
    name: str
    type: str
    ledger_id: str
    locking_script: bytes|None
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
        """Tally all entries for this account."""
        totals = {
            EntryType.CREDIT.value: 0,
            EntryType.DEBIT.value: 0,
        }
        for entries in self.entries().query().chunk(500):
            for entry in entries:
                totals[entry.type] += entry.amount

        if self.type in (
            AccountType.ASSET, AccountType.DEBIT_BALANCE,
            AccountType.CONTRA_LIABILITY, AccountType.CONTRA_EQUITY
        ):
            return totals[EntryType.DEBIT.value] - totals[EntryType.CREDIT.value]

        return totals[EntryType.CREDIT.value] - totals[EntryType.DEBIT.value]

    def validate_script(self, auth_script: bytes, data: dict = {}) -> bool:
        """Checks if the auth_script validates against the account
            locking_script. Returns True if it does and False if it does
            not (or if it errors).
        """
        cache = data.get('cache', {})
        contracts = data.get('contracts', {})
        locking_script = self.locking_script or b''
        return run_auth_script(auth_script + locking_script, cache, contracts)

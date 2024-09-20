from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol
from tapescript import run_auth_script, Script
from .AccountType import AccountType
from .EntryType import EntryType
import packify


class Account(HashedModel):
    connection_info: str = ''
    table: str = 'accounts'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'type', 'ledger_id', 'locking_script', 'details',
        'lock_entry_types',
    )
    id: str
    name: str
    type: str
    ledger_id: str
    locking_script: bytes|None
    lock_entry_types: bytes
    details: bytes|None
    ledger: RelatedModel
    entries: RelatedCollection

    @property
    def Type(self) -> AccountType:
        return AccountType(self.type)
    @Type.setter
    def Type(self, val: AccountType):
        if type(val) is AccountType:
            self.type = val.value

    @property
    def LockEntryTypes(self) -> list[EntryType]:
        return [
            EntryType(et)
            for et in packify.unpack(self.data.get('lock_entry_types', b'l\x00\x00\x00\x00'))
        ]
    @LockEntryTypes.setter
    def LockEntryTypes(self, vals: list[EntryType]):
        if type(vals) is list and all([type(et) is EntryType for et in vals]):
            self.lock_entry_types = packify.pack([et.value for et in vals])

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is not dict:
            return data
        if type(data.get('type', None)) is AccountType:
            data['type'] = data['type'].value
        if type(data.get('lock_entry_types', None)) is list:
            if all([type(et) is not EntryType for et in data['lock_entry_types']]):
                data['lock_entry_types'] = [EntryType(et) for et in data['lock_entry_types']]
            data['lock_entry_types'] = packify.pack([
                let.value for let in data['lock_entry_types']
            ])
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is not dict:
            return data
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
            EntryType.CREDIT: 0,
            EntryType.DEBIT: 0,
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

    def validate_script(self, auth_script: bytes|Script, tapescript_runtime: dict = {}) -> bool:
        """Checks if the auth_script validates against the account
            locking_script. Returns True if it does and False if it does
            not (or if it errors).
        """
        cache = tapescript_runtime.get('cache', {})
        contracts = tapescript_runtime.get('contracts', {})
        locking_script = self.locking_script or b''
        if type(auth_script) is Script:
            locking_script = Script.from_bytes(locking_script)
        return run_auth_script(auth_script + locking_script, cache, contracts)

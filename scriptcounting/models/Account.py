from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol
from tapescript import run_auth_script, Script
from .AccountType import AccountType
from .Entry import Entry
from .EntryType import EntryType
import packify


class Account(HashedModel):
    connection_info: str = ''
    table: str = 'accounts'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'type', 'ledger_id', 'code',
        'locking_scripts', 'details',
    )
    id: str
    name: str
    type: str
    ledger_id: str
    code: str|None
    locking_scripts: bytes|None
    details: bytes|None
    ledger: RelatedModel
    entries: RelatedCollection

    # override automatic property
    @property
    def type(self) -> AccountType:
        return AccountType(self.data['type'])
    @type.setter
    def type(self, val: AccountType):
        if type(val) is AccountType:
            self.data['type'] = val.value

    # override automatic property
    @property
    def locking_scripts(self) -> dict[EntryType, bytes]:
        return {
            EntryType(k): v
            for k,v in packify.unpack(
                self.data.get('locking_scripts', None) or b'd\x00\x00\x00\x00'
            ).items()
        }
    @locking_scripts.setter
    def locking_scripts(self, vals: dict[EntryType, bytes]):
        if type(vals) is dict and all([type(k) is EntryType for k, _ in vals.items()]) \
            and all([type(v) is bytes for k,v in vals.items()]):
            self.data['locking_scripts'] = packify.pack({
                k.value: v
                for k,v in vals.items()
            })

    # override automatic property
    @property
    def details(self) -> packify.SerializableType:
        return packify.unpack(self.data.get('details', None) or b'n\x00\x00\x00\x00')
    @details.setter
    def details(self, val: packify.SerializableType):
        if isinstance(val, packify.SerializableType):
            self.data['details'] = packify.pack(val)

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
            entry: Entry
            for entry in entries:
                totals[entry.type] += entry.amount

        if self.type in (
            AccountType.ASSET, AccountType.DEBIT_BALANCE,
            AccountType.CONTRA_LIABILITY, AccountType.CONTRA_EQUITY
        ):
            return totals[EntryType.DEBIT] - totals[EntryType.CREDIT]

        return totals[EntryType.CREDIT] - totals[EntryType.DEBIT]

    def validate_script(self, entry_type: EntryType, auth_script: bytes|Script,
                        tapescript_runtime: dict = {}) -> bool:
        """Checks if the auth_script validates against the correct
            locking_script for the EntryType. Returns True if it does
            and False if it does not (or if it errors).
        """
        cache = tapescript_runtime.get('cache', {})
        contracts = tapescript_runtime.get('contracts', {})
        locking_script = self.locking_scripts.get(entry_type, b'')
        if type(auth_script) is Script:
            auth_script = auth_script.bytes
        return run_auth_script(auth_script + locking_script, cache, contracts)

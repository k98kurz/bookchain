from __future__ import annotations
from sqloquent.asyncql import (
    AsyncHashedModel, AsyncRelatedModel, AsyncRelatedCollection,
    AsyncQueryBuilderProtocol,
)
from tapescript import run_auth_script, Script
from .AccountType import AccountType
from .Entry import Entry
from .EntryType import EntryType
import packify


class Account(AsyncHashedModel):
    connection_info: str = ''
    table: str = 'accounts'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'type', 'ledger_id', 'parent_id', 'code',
        'locking_scripts', 'category', 'details'
    )
    id: str
    name: str
    type: str
    ledger_id: str
    parent_id: str
    code: str|None
    locking_scripts: bytes|None
    category: str|None
    details: bytes|None
    ledger: AsyncRelatedModel
    parent: AsyncRelatedModel
    children: AsyncRelatedCollection
    entries: AsyncRelatedCollection

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
    async def insert(cls, data: dict) -> Account | None:
        result = await super().insert(cls._encode(data))
        if result is not None:
            result.data = cls._parse(result.data)
        return result

    @classmethod
    def query(cls, conditions: dict = None) -> AsyncQueryBuilderProtocol:
        return super().query(cls._encode(conditions))

    @classmethod
    async def find(cls, id: str) -> Account | None:
        """For better type hinting."""
        return await super().find(id)

    async def balance(self, include_sub_accounts: bool = True) -> int:
        """Tally all entries for this account and all sub-accounts."""
        totals = {
            EntryType.CREDIT: 0,
            EntryType.DEBIT: 0,
            'subaccounts': 0,
        }
        async for entries in self.entries().query().chunk(500):
            entry: Entry
            for entry in entries:
                totals[entry.type] += entry.amount

        if include_sub_accounts:
            for acct in self.children:
                acct: Account
                totals['subaccounts'] += await acct.balance(include_sub_accounts=True)

        if self.type in (
            AccountType.ASSET, AccountType.DEBIT_BALANCE,
            AccountType.CONTRA_LIABILITY, AccountType.CONTRA_EQUITY,
            AccountType.NOSTRO_ASSET
        ):
            return totals[EntryType.DEBIT] - totals[EntryType.CREDIT] + totals['subaccounts']

        return totals[EntryType.CREDIT] - totals[EntryType.DEBIT] + totals['subaccounts']

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
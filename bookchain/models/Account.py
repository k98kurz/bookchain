from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection
from sqloquent.interfaces import QueryBuilderProtocol
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
        'id', 'name', 'type', 'ledger_id', 'parent_id', 'code',
        'locking_scripts', 'category_id', 'details'
    )
    id: str
    name: str
    type: str
    ledger_id: str
    parent_id: str
    code: str|None
    locking_scripts: bytes|None
    category_id: str|None
    details: bytes|None
    ledger: RelatedModel
    parent: RelatedModel
    category: RelatedModel
    children: RelatedCollection
    entries: RelatedCollection

    # override automatic property
    @property
    def type(self) -> AccountType:
        """The AccountType of the Account."""
        return AccountType(self.data['type'])
    @type.setter
    def type(self, val: AccountType):
        if type(val) is AccountType:
            self.data['type'] = val.value

    # override automatic property
    @property
    def locking_scripts(self) -> dict[EntryType, bytes]:
        """The dict mapping EntryType to tapescript locking script bytes."""
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
        """A packify.SerializableType stored in the database as a blob."""
        return packify.unpack(self.data.get('details', None) or b'n\x00\x00\x00\x00')
    @details.setter
    def details(self, val: packify.SerializableType):
        if isinstance(val, packify.SerializableType):
            self.data['details'] = packify.pack(val)

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        """Encode Account data without modifying the original dict."""
        if type(data) is not dict:
            return data
        data = {**data}
        if type(data.get('type', None)) is AccountType:
            data['type'] = data['type'].value
        return data

    @classmethod
    def insert(cls, data: dict) -> Account | None:
        """Ensure data is encoded before inserting."""
        result = super().insert(cls._encode(data))
        return result

    @classmethod
    def insert_many(cls, items: list[dict], /, *, suppress_events: bool = False) -> int:
        """Ensure items are encoded before inserting."""
        items = [cls._encode(item) for item in items]
        return super().insert_many(items, suppress_events=suppress_events)

    def update(self, updates: dict, /, *, suppress_events: bool = False) -> Account:
        """Ensure updates are encoded before updating."""
        updates = self._encode(updates)
        return super().update(updates, suppress_events=suppress_events)

    @classmethod
    def query(cls, conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:
        """Ensure conditions are encoded before querying."""
        if conditions and type(conditions.get('type', None)) is AccountType:
            conditions['type'] = conditions['type'].value
        return super().query(conditions, connection_info)

    def balance(self, include_sub_accounts: bool = True) -> int:
        """Tally all entries for this account. Includes the balances of
            all sub-accounts if include_sub_accounts is True.
        """
        totals = {
            EntryType.CREDIT: 0,
            EntryType.DEBIT: 0,
            'subaccounts': 0,
        }
        for entries in self.entries().query().chunk(500):
            entry: Entry
            for entry in entries:
                totals[entry.type] += entry.amount

        if include_sub_accounts:
            for acct in self.children:
                totals['subaccounts'] += acct.balance(include_sub_accounts=True)

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

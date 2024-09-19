from __future__ import annotations
from hashlib import sha256
from sqloquent import HashedModel, RelatedCollection
from sqloquent.errors import vert, tert
from .AccountType import AccountType
from .Entry import Entry, EntryType
import packify


class Transaction(HashedModel):
    connection_info: str = ''
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'entry_ids', 'ledger_ids', 'timestamp', 'details', 'auth_scripts')
    id: str
    entry_ids: str
    ledger_ids: str
    timestamp: str
    details: packify.SerializableType
    auth_scripts: bytes|dict[str, bytes]
    entries: RelatedCollection
    ledgers: RelatedCollection

    @classmethod
    def encode(cls, data: dict|None) -> dict|None:
        """Encode values for saving."""
        if type(data) is not dict:
            return None
        if 'auth_scripts' in data and type(data['auth_scripts']) is dict:
            data['auth_scripts'] = packify.pack(data['auth_scripts'])
        if 'details' in data and type(data['details']) is dict:
            data['details'] = packify.pack(data['details'])
        return data

    @classmethod
    def parse(cls, data: dict) -> dict|None:
        """Parse encoded values."""
        if type(data) is not dict:
            return None
        if 'auth_scripts' in data and type(data['auth_scripts']) is bytes:
            data['auth_scripts'] = packify.unpack(data['auth_scripts'])
        if 'details' in data and type(data['details']) is bytes:
            try:
                data['details'] = packify.unpack(data['details'])
            except:
                ...
        return data

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate a txn id by hashing the entry_ids, ledger_ids,
            details, and timestamp. Raises TypeError for unencodable
            type (calls packify.pack).
        """
        data = {
            'entry_ids': sorted(data.get('entry_ids', [])),
            'ledger_ids': sorted(data.get('ledger_ids', [])),
            'details': data.get('details', None),
            'timestamp': data.get('timestamp', None),
        }
        preimage = packify.pack(data)
        return sha256(preimage).digest().hex()

    @classmethod
    def prepare(cls, entries: list[Entry], timestamp: str, auth_scripts: dict = {},
                details: packify.SerializableType = None,
                tapescript_runtime: dict = {}) -> Transaction:
        """Prepare a transaction. Raises TypeError for invalid arguments.
            Raises ValueError if the entries do not balance for each
            ledger; if a required auth script is missing; or if any of
            the entries is contained within an existing Transaction.
            Entries and Transaction will have IDs generated but will not
            be persisted to the database and must be saved separately.
        """
        tert(type(entries) is list and all([type(e) is Entry for e in entries]),
            'entries must be list[Entry]')

        for entry in entries:
            entry.id = entry.generate_id(entry.data)
            vert(Transaction.query().contains('entry_ids', entry.id).count() == 0,
                 f"entry {entry.id} is already contained within a Transaction")

        txn = cls({
            'entry_ids': ",".join(sorted([e.id for e in entries])),
            'ledger_ids': ",".join(sorted([ledger_id for ledger_id, _ in ledgers])),
            'timestamp': timestamp,
            'auth_scripts': auth_scripts,
            'details': packify.pack(details),
        })
        assert txn.validate()
        txn.id = txn.generate_id(txn.data)
        return txn

    def validate(self, tapescript_runtime: dict = {}, reload: bool = False) -> bool:
        """Determines if a Transaction is valid using the rules of accounting
            and checking all auth scripts against their locking scripts. The
            tapescript_runtime can be scoped to each entry ID. Raises TypeError
            for invalid arguments. Raises ValueError if the entries do not
            balance for each ledger; if a required auth script is missing; or
            if any of the entries is contained within an existing Transaction.
            If reload is set to True, entries and accounts will be reloaded
            from the database.
        """
        tert(type(timestamp) is str, 'timestamp must be str')
        tert(type(auth_scripts) is dict,
            'auth_scripts must be dict mapping account ID to authorizing tapescript bytecode')

        if reload:
            self.entries().reload()

        ledgers = {}
        for entry in entries:
            vert(entry.account_id in auth_scripts or not entry.account.locking_script,
                f"missing auth script for account {entry.account_id}")
            if entry.account.ledger_id not in ledgers:
                ledgers[entry.account.ledger_id] = 0
            if entry.type is EntryType.CREDIT:
                ledgers[entry.account.ledger_id] += entry.amount
            else:
                ledgers[entry.account.ledger_id] -= entry.amount

        for ledger_id, balance in ledgers.items():
            vert(balance == 0,
                f"ledger {ledger_id} unbalanced: {abs(balance)} {'Cr' if balance > 0 else 'Dr'}")

        for entry in self.entries:
            if reload:
                entry.account().reload()
            acct = entry.account

            if not acct.locking_script or entry.type not in acct.lock_entry_types:
                continue
            if acct.id not in self.auth_scripts:
                return False
            runtime = tapescript_runtime.get(entry.id, tapescript_runtime)
            if not acct.validate_script(self.auth_scripts[acct.id], runtime):
                return False

        return balance == 0


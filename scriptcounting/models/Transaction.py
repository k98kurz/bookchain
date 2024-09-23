from __future__ import annotations
from hashlib import sha256
from sqloquent import HashedModel, RelatedCollection
from sqloquent.errors import vert, tert
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
    details: bytes
    auth_scripts: bytes
    entries: RelatedCollection
    ledgers: RelatedCollection

    # override automatic properties
    @property
    def details(self) -> dict[str, bytes]:
        return packify.unpack(self.data.get('details', b'd\x00\x00\x00\x00'))
    @details.setter
    def details(self, val: dict[str, bytes]):
        if type(val) is not dict:
            return
        if not all([type(k) is str and type(v) is bytes for k, v in val.items()]):
            return
        self.data['details'] = packify.pack(val)

    @property
    def auth_scripts(self) -> dict[str, bytes]:
        return packify.unpack(self.data.get('auth_scripts', b'd\x00\x00\x00\x00'))
    @auth_scripts.setter
    def auth_scripts(self, val: dict[str, bytes]):
        if type(val) is not dict:
            return
        if not all([type(k) is str and type(v) is bytes for k, v in val.items()]):
            return
        self.data['auth_scripts'] = packify.pack(val)

    @classmethod
    def encode(cls, data: dict|None) -> dict|None:
        """Encode values for saving."""
        if type(data) is not dict:
            return None
        if type(data.get('auth_scripts', {})) is dict:
            data['auth_scripts'] = packify.pack(data.get('auth_scripts', {}))
        if type(data.get('details', {})) is dict:
            data['details'] = packify.pack(data.get('details', {}))
        return data

    @classmethod
    def parse(cls, data: dict) -> dict|None:
        """Parse encoded values."""
        if type(data) is not dict:
            return None
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
            'details': data.get('details', {}),
            'timestamp': data.get('timestamp', None),
        }
        preimage = packify.pack(data)
        return sha256(preimage).digest().hex()

    @classmethod
    def prepare(cls, entries: list[Entry], timestamp: str, auth_scripts: dict = {},
                details: packify.SerializableType = None,
                tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:
        """Prepare a transaction. Raises TypeError for invalid arguments.
            Raises ValueError if the entries do not balance for each
            ledger; if a required auth script is missing; or if any of
            the entries is contained within an existing Transaction.
            Entries and Transaction will have IDs generated but will not
            be persisted to the database and must be saved separately.
        """
        tert(type(entries) is list and all([type(e) is Entry for e in entries]),
            'entries must be list[Entry]')
        tert(type(timestamp) is str, 'timestamp must be str')

        ledgers = set()
        for entry in entries:
            entry.id = entry.generate_id(entry.data)
            if reload:
                entry.account().reload()
            vert(Transaction.query().contains('entry_ids', entry.id).count() == 0,
                 f"entry {entry.id} is already contained within a Transaction")
            ledgers.add(entry.account.ledger_id)

        txn = cls({
            'entry_ids': ",".join(sorted([
                e.id if e.id else e.generate_id(e.data)
                for e in entries
            ])),
            'ledger_ids': ",".join(sorted([ledger_id for ledger_id in ledgers])),
            'timestamp': timestamp,
        })
        txn.auth_scripts = auth_scripts
        txn.details = details
        txn.entries = entries
        assert txn.validate(tapescript_runtime, reload), \
            'transaction validation failed'
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
        tert(type(self.auth_scripts) is dict,
            'auth_scripts must be dict mapping account ID to authorizing tapescript bytecode')

        if reload:
            self.entries().reload()

        ledgers = {}
        entry: Entry
        for entry in self.entries:
            vert(entry.account_id in self.auth_scripts or not entry.account.locking_scripts
                 or entry.type not in entry.account.locking_scripts,
                f"missing auth script for account {entry.account_id} ({entry.account.name})")
            if reload:
                entry.account().reload()
            if entry.account.ledger_id not in ledgers:
                ledgers[entry.account.ledger_id] = {'Dr': 0, 'Cr': 0}
            if entry.type in (EntryType.CREDIT, EntryType.CREDIT.value):
                ledgers[entry.account.ledger_id]['Cr'] += entry.amount
            else:
                ledgers[entry.account.ledger_id]['Dr'] += entry.amount

        for ledger_id, balances in ledgers.items():
            vert(balances['Cr'] == balances['Dr'],
                f"ledger {ledger_id} unbalanced: {balances['Cr']} Cr != {balances['Dr']} Dr")

        for entry in self.entries:
            acct = entry.account

            if not acct.locking_scripts or entry.type not in acct.locking_scripts:
                continue
            if acct.id not in self.auth_scripts:
                return False
            runtime = tapescript_runtime.get(entry.id, {**tapescript_runtime})
            if 'cache' not in runtime:
                runtime['cache'] = {}
            if 'sigfield1' not in runtime['cache']:
                runtime['cache'] = {
                    **runtime['cache'],
                    **entry.get_sigfields(tapescript_runtime=tapescript_runtime)
                }
            if not acct.validate_script(entry.type, self.auth_scripts[acct.id], runtime):
                return False

        return True

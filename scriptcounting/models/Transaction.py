from __future__ import annotations
from hashlib import sha256
from sqloquent import HashedModel, RelatedCollection
from sqloquent.errors import vert
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
    auth_scripts: bytes|None
    entries: RelatedCollection
    ledgers: RelatedCollection

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate a txn id by hashing the entry_ids, ledger_ids,
            details, and timestamp. Raises TypeError for unencodable
            type (calls packify.pack).
        """
        data = {
            'entry_ids': data.get('entry_ids', []),
            'ledger_ids': data.get('ledger_ids', []),
            'details': data.get('details', None),
            'timestamp': data.get('timestamp', None),
        }
        preimage = packify.pack(data)
        return sha256(preimage).digest().hex()

    def prepare(self, entries: list[Entry], timestamp: str,
                auth_scripts: dict = {}, details: packify.SerializableType = None) -> Transaction:
        """Prepare a transaction. Raises TypeError for invalid arguments.
            Raises ValueError if the entries do not balance for each
            ledger; if a required auth script is missing; or if any of
            the entries is contained within an existing Transaction.
            Entries and Transaction will have IDs generated but will not
            be persisted to the database and must be saved separately.
        """
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

        for ledger_id, balance in ledgers:
            vert(balance == 0,
                f"ledger {ledger_id} unbalanced: {abs(balance)} {'Cr' if balance > 0 else 'Dr'}")

        for entry in entries:
            entry.id = entry.generate_id(entry.encode(entry.data))
            vert(Transaction.query().contains('entry_ids', entry.id).count() == 0,
                 f"entry {entry.id} is already contained within a Transaction")

        txn = Transaction({
            'entry_ids': ",".join(sorted([e.id for e in entries])),
            'ledger_ids': ",".join(sorted([ledger_id for ledger_id, _ in ledgers])),
            'timestamp': timestamp,
            'auth_scripts': packify.pack(auth_scripts),
            'details': packify.pack(details),
        })
        txn.id = txn.generate_id(txn.data)
        return txn

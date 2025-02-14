from __future__ import annotations
from .Correspondence import Correspondence
from .Entry import Entry, EntryType, ArchivedEntry
from .Ledger import Ledger
from .Transaction import Transaction, ArchivedTransaction
from merkleasy import Tree
from sqloquent import (
    DeletedModel,
    HashedModel,
    RelatedCollection,
    RelatedModel,
    SqlQueryBuilder,
)
from sqloquent.errors import tert, vert
from time import time
import packify
import tapescript


class TxRollup(HashedModel):
    connection_info: str = ''
    table: str = 'txn_rollups'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'height', 'parent_id', 'tx_ids', 'tx_root', 'correspondence_id',
        'ledger_id', 'balances', 'timestamp', 'auth_script'
    )
    columns_excluded_from_hash: tuple[str] = ('tx_ids', 'auth_script')
    id: str
    height: int
    parent_id: str|None
    tx_ids: str
    tx_root: str
    correspondence_id: str|None
    ledger_id: str|None
    balances: bytes
    timestamp: str
    auth_script: bytes|None
    correspondence: RelatedModel|None
    ledger: RelatedModel|None
    transactions: RelatedCollection
    parent: RelatedModel|None
    children: RelatedCollection

    @property
    def tx_ids(self) -> list[str]:
        """A list of transaction IDs."""
        return self.data.get('tx_ids', '').split(',')
    @tx_ids.setter
    def tx_ids(self, val: list[str]):
        if type(val) is not list:
            return
        # sort the ids, join into a comma-separated string
        val.sort()
        self.data['tx_ids'] = ','.join(val)
        # convert to bytes and build a merkle tree
        val = [bytes.fromhex(txn_id) for txn_id in val]
        tree = Tree.from_leaves(val)
        self.data['tx_root'] = tree.root.hex()

    @property
    def balances(self) -> dict[str, tuple[EntryType, int]]:
        """A dict mapping account IDs to tuple[EntryType, int] balances."""
        balances: dict = packify.unpack(self.data.get('balances', b'd\x00\x00\x00\x00'))
        return {
            k: (EntryType(v[0]), v[1])
            for k, v in balances.items()
        }
    @balances.setter
    def balances(self, val: dict[str, tuple[EntryType, int]]):
        tert(type(val) is dict, 'balances must be a dict')
        tert(all([
                type(k) is str and
                type(v) is tuple and
                len(v) == 2 and
                type(v[0]) is EntryType and
                type(v[1]) is int
                for k, v in val.items()
            ]),
            'balances must be a dict of str: tuple[EntryType, int]')
        val = {
            k: (v[0].value, v[1])
            for k, v in val.items()
        }
        self.data['balances'] = packify.pack(val)

    @property
    def tree(self) -> Tree:
        """A merkle tree of the transaction IDs."""
        return Tree.from_leaves([bytes.fromhex(txn_id) for txn_id in self.tx_ids])

    def prove_txn_inclusion(self, txn_id: str|bytes) -> bytes:
        """Proves that a transaction is included in the tx rollup."""
        txn_id = bytes.fromhex(txn_id) if type(txn_id) is str else txn_id
        return self.tree.prove(txn_id)

    def verify_txn_inclusion_proof(self, txn_id: str|bytes, proof: bytes) -> bool:
        """Verifies that a transaction is included in the tx rollup."""
        txn_id = bytes.fromhex(txn_id) if type(txn_id) is str else txn_id
        return self.tree.verify(bytes.fromhex(self.tx_root), txn_id, proof)

    @classmethod
    def calculate_balances(
        cls, txns: list[Transaction],
        parent_balances: dict[str, tuple[EntryType, int]]|None = None,
        reload: bool = False
    ) -> dict[str, tuple[EntryType, int]]:
        """Calculates the account balances for a list of rolled-up
            transactions. If parent_balances is provided, those are the
            starting balances to which the balances of the rolled-up
            transactions are added. If reload is True, the entries are
            reloaded from the database.
        """
        balances = parent_balances or {}
        for txn in txns:
            if reload:
                txn.entries().reload()
            for e in txn.entries:
                e: Entry
                bal = {EntryType.CREDIT: 0, EntryType.DEBIT: 0}
                if e.account_id in balances:
                    bal[balances[e.account_id][0]] = balances[e.account_id][1]
                bal[e.type] += e.amount
                net_credit = bal[EntryType.CREDIT] - bal[EntryType.DEBIT]
                if net_credit >= 0:
                    balances[e.account_id] = (EntryType.CREDIT, net_credit)
                else:
                    balances[e.account_id] = (EntryType.DEBIT, -net_credit)
        return balances

    @classmethod
    def prepare(cls, txns: list[Transaction], parent_id: str|None = None,
                correspondence: Correspondence|None = None, reload: bool = False
                ) -> TxRollup:
        """Prepare a tx rollup by checking that all txns are for the
            accounts of the given correspondence or belong to the same
            ledger if no correspondence is provided. Raises TypeError if
            txns is not a list of Transaction objects. Raises ValueError
            if any txns are not for accounts of the given correspondence
            or of the same ledger if no correspondence is provided.
        """
        tert(all([type(t) is Transaction for t in txns]),
            'txns must be a list of Transaction objects')
        tert(type(correspondence) is Correspondence or correspondence is None,
            'correspondence must be a Correspondence object or None')

        accounts = []
        acct_ids = set()
        balances = {}
        txru = TxRollup()
        txru.tx_ids = [t.id for t in txns]
        txru.height = 0

        if correspondence is None:
            # all txns must be accounts from the same ledger
            txns[0].entries().reload()
            txns[0].entries[0].account().reload()
            ledger: Ledger = txns[0].entries[0].account.ledger
            ledger.accounts().reload()
            accounts = list(ledger.accounts)
            acct_ids = set([a.id for a in accounts])
            for txn in txns:
                txn.entries().reload()
                for e in txn.entries:
                    e: Entry
                    vert(e.account_id in acct_ids,
                        'all txns must be for from the same ledger when correspondence is None')
        else:
            # all txns must be for accounts from the same correspondence
            accounts = correspondence.get_accounts()
            accounts = [a for _, aa in accounts.items() for _, a in aa.items()]
            acct_ids = set([a.id for a in accounts])
            for txn in txns:
                txn.entries().reload()
                for e in txn.entries:
                    e: Entry
                    vert(e.account_id in acct_ids,
                        'all txns must be for accounts from the same correspondence')

        # if there is a parent, get its balances if it is a tx rollup
        if parent_id is not None:
            parent: TxRollup|None = TxRollup.find(parent_id)
            vert(parent is not None, 'parent must exist')
            balances = parent.balances
            txru.height = parent.height + 1

        # aggregate balances from txn entries
        balances = cls.calculate_balances(txns, balances, reload=reload)

        txru.parent_id = parent_id
        txru.balances = balances
        txru.timestamp = str(time())
        if correspondence is not None:
            txru.correspondence_id = correspondence.id
        else:
            ledger: Ledger = txns[0].entries[0].account.ledger
            txru.ledger_id = ledger.id
        return txru

    def validate(self, reload: bool = False) -> bool:
        """Validates that a TxRollup has been authorized properly; that
            the balances are correct; and that the height is 1 + the
            height of the parent tx rollup (if one exists).
        """
        authorized = True
        balances = {}
        parent = None

        # if there is a parent, get its balances if it is a tx rollup
        if self.parent_id is not None:
            parent: TxRollup|None = TxRollup.find(self.parent_id)
            vert(parent is not None, 'parent must exist')
            balances = parent.balances

        if self.correspondence_id is not None:
            correspondence: Correspondence = Correspondence.find(self.correspondence_id)
            correspondence.identities().reload()
            # either the txru_lock has been set and fulfilled, or both
            # identities have signed independently
            txru_lock = correspondence.details.get('txru_lock', None)
            if txru_lock is None:
                pubkeys = [identity.pubkey for identity in correspondence.identities]
                # if not all identities have a pubkey and the txru_lock
                # is not set, then the txru is authorized by default
                if not all([len(pk) > 0 for pk in pubkeys]):
                    authorized = True
                else:
                    txru_lock = tapescript.make_multisig_lock(pubkeys, len(pubkeys)).bytes

            if self.auth_script is not None and txru_lock is not None:
                authorized = tapescript.run_auth_script(
                    self.auth_script + txru_lock,
                    {'sigfield1': self.id}
                )

        # validate the height
        if parent is None:
            if self.height != 0:
                return False
        else:
            if parent.height + 1 != self.height:
                return False

        # recalculate the balances
        balances = self.calculate_balances(self.transactions, balances, reload=reload)

        # compare the recalculated balances to the stored balances
        for acct_id, (entry_type, amount) in balances.items():
            if acct_id not in self.balances:
                return False
            if self.balances[acct_id][0] != entry_type:
                return False
            if self.balances[acct_id][1] != amount:
                return False

        return authorized

    def trim(self, archive: bool = True) -> int:
        """Trims the transactions and entries committed to in this tx
            rollup. Returns the number of transactions trimmed. If
            archive is True, the transactions and entries are archived
            before being deleted. Raises ValueError if the tx rollup is
            not valid.
        """
        vert(self.validate(), 'tx rollup is not valid')
        self.transactions().reload()
        txns = self.transactions
        for txn in txns:
            txn: Transaction
            txn.entries().reload()
            for e in txn.entries:
                e: Entry
                if archive:
                    e.archive()
                e.delete()
            if archive:
                txn.archive()
            txn.delete()
        return len(txns)

    def trimmed_transactions(self) -> SqlQueryBuilder:
        """Returns a query builder for DeletedModels containing the trimmed
            transactions committed to in this tx rollup.
        """
        return DeletedModel.query({'model_class': Transaction.__name__}).is_in(
            'record_id', self.tx_ids
        )

    def trimmed_entries(self) -> SqlQueryBuilder:
        """Returns a query builder for DeletedModels containing the
            trimmed entries from trimmed transactions committed to in
            this tx rollup.
        """
        txns = [
            Transaction(packify.unpack(item.record))
            for item in self.trimmed_transactions().get()
        ]
        return DeletedModel.query({'model_class': Entry.__name__}).is_in(
            'record_id',
            [
                eid
                for txn in txns
                for eid in txn.entry_ids.split(',')
            ]
        )

    def archived_transactions(self) -> SqlQueryBuilder:
        """Returns a query builder for ArchivedTransactions committed
            to in this tx rollup.
        """
        return ArchivedTransaction.query().is_in('id', self.tx_ids)

    def archived_entries(self) -> SqlQueryBuilder:
        """Returns a query builder for ArchivedEntries committed to
            in this tx rollup.
        """
        return ArchivedEntry.query().is_in(
            'id',
            [
                e.id
                for txn in self.archived_transactions().get()
                for e in txn.entries
            ]
        )

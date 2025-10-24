from __future__ import annotations
from .Correspondence import Correspondence
from .Entry import Entry, EntryType, ArchivedEntry
from .Ledger import Ledger
from .Transaction import Transaction, ArchivedTransaction
from merkleasy import Tree
from sqloquent.asyncql import (
    AsyncDeletedModel,
    AsyncHashedModel,
    AsyncRelatedCollection,
    AsyncRelatedModel,
    AsyncSqlQueryBuilder,
)
from sqloquent.errors import tert, vert
from time import time
import packify
import tapescript


class TxRollup(AsyncHashedModel):
    """A Transaction Roll-up is a collection of Transactions that have
        been consolidated: the IDs of the committed Transactions are the
        leaves of a Merkle tree, and the aggregate effects of the
        Transactions are maintained in a dict mapping account IDs to
        tuples of EntryType and int balances. A TxRollup created for a
        Correspondence must have a valid auth_script that unlocks the
        txru_lock in the Correspondence's details (or an n-of-n multisig
        lock made from the pubkeys of the Correspondence's identities if
        no txru_lock was saved). The height of a TxRollup is the number
        of TxRollups in its chain -- they form a blockchain of TxRollups,
        hence the inclusion of a parent_id. Only one child TxRollup can
        be added for a given parent TxRollup, and the balances of the
        child TxRollup are the sum of the effects of the Transactions in
        the child TxRollup and the parent TxRollup balances; i.e. the
        most recent TxRollup is the sum of all the Transactions
        committed to in previous TxRollups in the chain. Inclusion of a
        Transaction can only be proven using the Merkle tree of the
        TxRollup in which it was committed and only if the full list of
        tx_ids is saved, but the proof can be verified by mirrors that
        have only the tx_root.
    """
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
    correspondence: AsyncRelatedModel
    ledger: AsyncRelatedModel
    transactions: AsyncRelatedCollection
    parent: AsyncRelatedModel
    child: AsyncRelatedModel

    def public(self) -> dict:
        """Returns the public data for mirroring this TxRollup. Excludes
            the tx_ids.
        """
        return {
            k:v for k,v in self.data.items()
            if k != 'tx_ids'
        }

    @property
    def tx_ids(self) -> list[str]:
        """A list of transaction IDs. Setting causes the ids to be
            sorted, then combined into a Merkle Tree, the root of which
            is used to set `self.tx_root`.
        """
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
        while len(val) < 2:
            val = [b'\x00'*32, *val]
        tree = Tree.from_leaves(val)
        self.data['tx_root'] = tree.root.hex()

    @property
    def balances(self) -> dict[str, tuple[EntryType, int]]:
        """A dict mapping account IDs to tuple[EntryType, int] balances."""
        balances: dict = packify.unpack(self.data.get('balances', b'M@\x00'))
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
        return Tree.verify(bytes.fromhex(self.tx_root), txn_id, proof)

    @classmethod
    async def calculate_balances(
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
                await txn.entries().reload()
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
    async def prepare(cls, txns: list[Transaction], parent_id: str|None = None,
                correspondence: Correspondence|None = None,
                ledger: Ledger|None = None, reload: bool = False
                ) -> TxRollup:
        """Prepare a tx rollup by checking that all txns are for the
            accounts of the given correspondence or belong to the same
            ledger if no correspondence is provided. Raises TypeError if
            txns is not a list of Transaction objects. Raises ValueError
            if any txns are not for accounts of the given correspondence
            or of the same ledger if no correspondence is provided, or
            if the parent TxRollup already has a child, or if there are
            no txns and no ledger or correspondence is provided, or if
            a TxRollup chain already exists for the given ledger or
            correspondence when no parent is provided. The Transaction
            IDs are sorted and combined into a Merkle Tree, the root of
            which is used to set the `tx_root` property.
        """
        tert(all([type(t) is Transaction for t in txns]),
            'txns must be a list of Transaction objects')
        tert(type(correspondence) is Correspondence or correspondence is None,
            'correspondence must be a Correspondence object or None')
        vert(len(txns) > 0 or ledger is not None or correspondence is not None,
            'either txns, ledger, or correspondence must be provided')

        accounts = []
        acct_ids = set()
        balances = {}
        txru = TxRollup()
        txru.tx_ids = [t.id for t in txns]
        txru.height = 0

        if correspondence is None:
            # all txns must be accounts from the same ledger
            if len(txns) > 0 and ledger is None:
                await txns[0].entries().reload()
                await txns[0].entries[0].account().reload()
                ledger: Ledger = txns[0].entries[0].account.ledger
            if reload:
                await ledger.accounts().reload()
            accounts = list(ledger.accounts)
            acct_ids = set([a.id for a in accounts])
            for txn in txns:
                await txn.entries().reload()
                for e in txn.entries:
                    e: Entry
                    vert(e.account_id in acct_ids,
                        'all txns must be for from the same ledger when correspondence is None')
        else:
            # all txns must be for accounts from the same correspondence
            accounts = await correspondence.get_accounts()
            accounts = [a for _, aa in accounts.items() for _, a in aa.items()]
            acct_ids = set([a.id for a in accounts])
            for txn in txns:
                await txn.entries().reload()
                for e in txn.entries:
                    e: Entry
                    vert(e.account_id in acct_ids,
                        'all txns must be for accounts from the same correspondence')

        if parent_id is not None:
            # if there is a parent, get its balances and set the height
            parent: TxRollup|None = await TxRollup.find(parent_id)
            vert(parent is not None, 'parent must exist')
            balances = parent.balances
            txru.height = parent.height + 1
            vert((await parent.child().query().count()) == 0, 'parent already has a child')
        else:
            # if there is no parent, ensure there is no other chain
            if ledger is not None:
                vert(await TxRollup.query().equal('ledger_id', ledger.id).count() == 0,
                    'the given ledger already has a TxRollup chain')
            elif correspondence is not None:
                vert(await TxRollup.query().equal('correspondence_id', correspondence.id).count() == 0,
                    'the given correspondence already has a TxRollup chain')

        # aggregate balances from txn entries
        balances = await cls.calculate_balances(txns, balances, reload=reload)

        txru.parent_id = parent_id
        txru.balances = balances
        txru.timestamp = str(time())
        if correspondence is not None:
            txru.correspondence_id = correspondence.id
        else:
            if len(txns) > 0 and ledger is None:
                ledger: Ledger = txns[0].entries[0].account.ledger
            txru.ledger_id = ledger.id
        return txru

    async def validate(self, reload: bool = False) -> bool:
        """Validates that a TxRollup has been authorized properly; that
            the balances are correct; and that the height is 1 + the
            height of the parent tx rollup (if one exists); and that
            there is no other chain for the relevant ledger or
            correspondence when no parent is provided.
        """
        authorized = True
        balances = {}
        parent = None

        # if there is a parent, get its balances if it is a tx rollup
        if self.parent_id is not None:
            parent: TxRollup|None = await TxRollup.find(self.parent_id)
            vert(parent is not None, 'parent must exist')
            balances = parent.balances
            await parent.child().reload()
            self_id = self.id or self.generate_id(self.data)
            if parent.child.id is not None:
                if parent.child.id != self_id:
                    return False

        if self.correspondence_id is not None:
            correspondence: Correspondence = await Correspondence.find(self.correspondence_id)
            await correspondence.identities().reload()
            # either the txru_lock has been set and fulfilled, or both
            # identities have signed independently
            txru_lock = correspondence.txru_lock
            if txru_lock is None:
                pubkeys = [identity.pubkey for identity in correspondence.identities]
                # if not all identities have a pubkey and the txru_lock
                # is not set, then the txru is authorized by default
                if not all([len(pk) > 0 for pk in pubkeys]):
                    authorized = True
                else:
                    txru_lock = tapescript.make_multisig_lock(pubkeys, len(pubkeys)).bytes

            if self.auth_script is not None and txru_lock is not None:
                authorized = tapescript.run_auth_scripts(
                    [self.auth_script, txru_lock],
                    {'sigfield1': self.id}
                )

        # validate the height
        if parent is None:
            if self.height != 0:
                return False
        else:
            if parent.height + 1 != self.height:
                return False

        # ensure there is no other chain
        if parent is None:
            self_id = self.id or self.generate_id(self.data)
            if self.correspondence_id is not None:
                if await TxRollup.query().equal(
                    'correspondence_id',
                    self.correspondence_id
                ).not_equal('id', self_id).count() > 0:
                    return False
            elif self.ledger_id is not None:
                if await TxRollup.query().equal(
                    'ledger_id',
                    self.ledger_id
                ).not_equal('id', self_id).count() > 0:
                    return False
            elif len(self.tx_ids) > 0:
                txn: Transaction|None = await Transaction.find(self.tx_ids[0])
                if txn is not None:
                    await txn.entries().reload()
                    if len(txn.entries) > 0:
                        await txn.entries[0].account().reload()
                        ledger_id = txn.entries[0].account.ledger_id
                        if await TxRollup.query().equal(
                            'ledger_id',
                            ledger_id
                        ).not_equal('id', self_id).count() > 0:
                            return False

        # recalculate the balances
        balances = await self.calculate_balances(self.transactions, balances, reload=reload)

        # compare the recalculated balances to the stored balances
        for acct_id, (entry_type, amount) in balances.items():
            if acct_id not in self.balances:
                return False
            if self.balances[acct_id][0] != entry_type:
                return False
            if self.balances[acct_id][1] != amount:
                return False

        return authorized

    async def trim(self, archive: bool = True) -> int:
        """Trims the transactions and entries committed to in this tx
            rollup. Returns the number of transactions trimmed. If
            archive is True, the transactions and entries are archived
            before being deleted. Raises ValueError if the tx rollup is
            not valid.
        """
        vert(await self.validate(), 'tx rollup is not valid')
        await self.transactions().reload()
        txns = self.transactions
        for txn in txns:
            txn: Transaction
            await txn.entries().reload()
            for e in txn.entries:
                e: Entry
                if archive:
                    await e.archive()
                await e.delete()
            if archive:
                await txn.archive()
            await txn.delete()
        return len(txns)

    def trimmed_transactions(self) -> AsyncSqlQueryBuilder:
        """Returns a query builder for DeletedModels containing the trimmed
            transactions committed to in this tx rollup.
        """
        return AsyncDeletedModel.query({'model_class': Transaction.__name__}).is_in(
            'record_id', self.tx_ids
        )

    async def trimmed_entries(self) -> AsyncSqlQueryBuilder:
        """Returns a query builder for DeletedModels containing the
            trimmed entries from trimmed transactions committed to in
            this tx rollup.
        """
        txns = [
            Transaction(packify.unpack(item.record))
            for item in await self.trimmed_transactions().get()
        ]
        return AsyncDeletedModel.query({'model_class': Entry.__name__}).is_in(
            'record_id',
            [
                eid
                for txn in txns
                for eid in txn.entry_ids.split(',')
            ]
        )

    def archived_transactions(self) -> AsyncSqlQueryBuilder:
        """Returns a query builder for ArchivedTransactions committed
            to in this tx rollup.
        """
        return ArchivedTransaction.query().is_in('id', self.tx_ids)

    async def archived_entries(self) -> AsyncSqlQueryBuilder:
        """Returns a query builder for ArchivedEntries committed to
            in this tx rollup.
        """
        return ArchivedEntry.query().is_in(
            'id',
            [
                e.id
                for txn in await self.archived_transactions().get()
                for e in txn.entries
            ]
        )

from __future__ import annotations
from sqloquent import HashedModel, RelatedCollection
from sqloquent.errors import vert, tert
from .Account import Account, AccountType
from .ArchivedTransaction import ArchivedTransaction
from .Correspondence import Correspondence
from .Entry import Entry, EntryType
from .Identity import Identity
import packify


_empty_dict = packify.pack({})


class Transaction(HashedModel):
    """A Transaction is a collection of connected Entries that are
        recorded on the Ledgers of the Identities that are party to the
        Transaction. Any Entry for an Account that has a locking_script
        will require a valid tapscript unlocking script to be recorded
        in the auth_scripts dict of the Transaction.
    """
    connection_info: str = ''
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'entry_ids', 'ledger_ids', 'timestamp', 'details', 'auth_scripts',
        'description',
    )
    columns_excluded_from_hash: tuple[str] = ('auth_scripts', 'description',)
    id: str
    entry_ids: str
    ledger_ids: str
    timestamp: str
    details: bytes
    auth_scripts: bytes
    description: str|None
    entries: RelatedCollection
    ledgers: RelatedCollection
    rollups: RelatedCollection

    # override automatic properties
    @property
    def details(self) -> dict[str, bytes]:
        """A packify.SerializableType stored in the database as a blob."""
        return packify.unpack(self.data.get('details', _empty_dict))
    @details.setter
    def details(self, val: dict[str, bytes]):
        if type(val) is not dict:
            return
        if not all([type(k) is str and type(v) is bytes for k, v in val.items()]):
            return
        self.data['details'] = packify.pack(val)

    @property
    def auth_scripts(self) -> dict[str, bytes]:
        """A dict mapping account IDs to tapescript unlocking script bytes."""
        return packify.unpack(self.data.get('auth_scripts', _empty_dict))
    @auth_scripts.setter
    def auth_scripts(self, val: dict[str, bytes]):
        if type(val) is not dict:
            return
        if not all([type(k) is str and type(v) is bytes for k, v in val.items()]):
            return
        self.data['auth_scripts'] = packify.pack(val)

    @classmethod
    def _encode(cls, data: dict|None) -> dict|None:
        """Encode values for saving."""
        if type(data) is not dict:
            return None
        if type(data.get('auth_scripts', {})) is dict:
            data['auth_scripts'] = packify.pack(data.get('auth_scripts', {}))
        if type(data.get('details', {})) is dict:
            data['details'] = packify.pack(data.get('details', {}))
        return data

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
            The auth_scripts dict must map account IDs to tapescript
            bytecode bytes.
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
            'ledger_ids': ",".join(sorted(list(ledgers))),
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

        if len(self.entries) == 0:
            return False

        # first check that all ledgers balance
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

        # next check that all necessary authorizations are provided
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

        # finally check that correspondent accounting is not violated
        if len(ledgers) > 1:
            accounts = [e.account for e in self.entries]

            for acct in accounts:
                acct: Account
                if acct.type is AccountType.NOSTRO_ASSET and type(acct.details) is str \
                    and acct.details != acct.id and Identity.find(acct.details):
                    # Nostro account must have equivalent Vostro account
                    nostro = acct
                    nostro.ledger().reload()
                    cor: Correspondence = Correspondence.query().contains(
                        'identity_ids', nostro.ledger.identity_id
                    ).contains('identity_ids', nostro.details).first()
                    if cor is None:
                        continue
                    accts = cor.get_accounts()
                    if acct.details not in accts:
                        return False
                    if AccountType.VOSTRO_LIABILITY not in accts[acct.details]:
                        return False
                    vostro = accts[acct.details][AccountType.VOSTRO_LIABILITY]
                    if vostro.id not in [a.id for a in accounts]:
                        # each nostro Entry must have an offsetting vostro Entry
                        return False
                    offsetting_entry = [e for e in self.entries if e.account_id == vostro.id]
                    if len(offsetting_entry) < 1:
                        return False
                    if offsetting_entry[0].amount != entry.amount:
                        return False

                if acct.type is AccountType.VOSTRO_LIABILITY and type(acct.details) is str \
                    and acct.details != acct.id and Identity.find(acct.details):
                    # Vostro account must have equivalent Nostro account
                    vostro = acct
                    vostro.ledger().reload()
                    cor: Correspondence = Correspondence.query().contains(
                        'identity_ids', vostro.ledger.identity_id
                    ).contains('identity_ids', vostro.details).first()
                    if cor is None:
                        continue
                    accts = cor.get_accounts()
                    if acct.details not in accts:
                        return False
                    if AccountType.NOSTRO_ASSET not in accts[acct.details]:
                        return False
                    nostro = accts[acct.details][AccountType.NOSTRO_ASSET]
                    if nostro.id not in [a.id for a in accounts]:
                        # each nostro Entry must have an offsetting nostro Entry
                        return False
                    offsetting_entry = [e for e in self.entries if e.account_id == nostro.id]
                    if len(offsetting_entry) < 1:
                        return False
                    if offsetting_entry[0].amount != entry.amount:
                        return False

        return True

    def save(self, tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:
        """Validate the transaction, save the entries, then save the
            transaction.
        """
        assert self.validate(tapescript_runtime, reload), 'cannot save an invalid Transaction'
        for e in self.entries:
            e.save()
        return super().save()

    def archive(self) -> ArchivedTransaction:
        """Archive the Transaction. If it has already been archived,
            return the existing ArchivedTransaction.
        """
        archived_txn_id = ArchivedTransaction.generate_id({**self.data})
        try:
            return ArchivedTransaction.insert({**self.data})
        except Exception as e:
            return ArchivedTransaction.find(archived_txn_id)

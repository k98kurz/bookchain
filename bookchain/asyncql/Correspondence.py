from __future__ import annotations
from .Account import Account, AccountType
from .Entry import Entry, EntryType
from .Identity import Identity
from .Ledger import Ledger
from sqloquent.asyncql import AsyncHashedModel, AsyncRelatedCollection
from sqloquent.errors import vert, tert
import packify


class Correspondence(AsyncHashedModel):
    table: str = 'correspondences'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'identity_ids', 'ledger_ids', 'details', 'signatures')
    columns_excluded_from_hash: tuple[str] = ('signatures')
    id: str
    identity_ids: str
    ledger_ids: str
    details: bytes
    signatures: bytes|None
    identities: AsyncRelatedCollection
    ledgers: AsyncRelatedCollection
    rollups: AsyncRelatedCollection

    @property
    def details(self) -> dict:
        """Returns the details of the correspondence as a dict."""
        return packify.unpack(self.data.get('details', b'M@\x00'))
    @details.setter
    def details(self, val: dict):
        """Sets the details of the correspondence as a dict. Raises
            TypeError if the value is not a dict.
        """
        tert(type(val) is dict, 'details must be type dict')
        self.data['details'] = packify.pack(val)

    @property
    def signatures(self) -> dict[str, bytes]:
        """Returns the signatures of the correspondences as a dict
            mapping Identity ID to bytes signature.
        """
        return packify.unpack(self.data.get('signatures', b'M@\x00'))
    @signatures.setter
    def signatures(self, val: dict[str, bytes]):
        """Sets the signatures of the correspondences as a dict
            mapping IDs to bytes signature. Raises TypeError for invalid
            type or ValueError if an ID is not of the correspondence or
            its identities.
        """
        tert(type(val) is dict, 'signatures must be type dict[str, bytes]')
        for k, v in val.items():
            tert(type(k) is str, 'signatures must be type dict[str, bytes]')
            tert(type(v) is bytes, 'signatures must be type dict[str, bytes]')
            vert(k in self.identity_ids or k == self.id,
                 f'ID {k} not of correspondence or one of its identities')
        self.data['signatures'] = packify.pack(val)

    @property
    def txru_lock(self) -> bytes|None:
        """Returns the txru_lock directly from the details field."""
        return self.details.get('txru_lock', None)

    async def get_accounts(self) -> dict[str, dict[AccountType, Account]]:
        """Loads the relevant nostro and vostro Accounts for the
            Identities that are part of the Correspondence.
        """
        await self.ledgers().reload()
        await self.identities().reload()
        accounts = {
            identity.id: {}
            for identity in self.identities
        }
        for id1 in self.identities:
            id1: Identity
            for identity in [i for i in self.identities if i.id != id1.id]:
                identity: Identity
                for acct in await id1.get_correspondent_accounts(identity):
                    await acct.ledger().reload()
                    if acct.ledger.identity_id == identity.id:
                        accounts[identity.id][acct.type] = acct
        for ledger in self.ledgers:
            ledger: Ledger
            acct = await ledger.accounts().query().equal(
                type=AccountType.EQUITY.value
            ).first()
            if acct is not None:
                await acct.ledger().reload()
                accounts[acct.ledger.identity_id][acct.type] = acct
        return accounts

    async def setup_accounts(
            self, locking_scripts: dict[str, bytes]
        ) -> dict[str, dict[AccountType, Account]]:
        """Takes a dict mapping Identity ID to tapescript locking
            scripts. Returns a dict of Accounts necessary for setting up
            the credit Correspondence of form
            { identity.id: { AccountType: Account }}.
        """
        accounts = {}
        await self.identities().reload()
        for identity1 in self.identities:
            identity1: Identity
            for identity2 in [i for i in self.identities if i.id != identity1.id]:
                await identity1.ledgers().reload()
                ledger = [l for l in identity1.ledgers if l.id in self.ledger_ids][0]
                identity2: Identity
                nostro = Account({
                    'name': f'Receivable from (Nostro with) {identity2.name} ({identity2.id})',
                    'type': AccountType.NOSTRO_ASSET.value,
                    'ledger_id': ledger.id,
                })
                nostro.details = identity2.id
                nostro.locking_scripts = {
                    EntryType.CREDIT: locking_scripts[identity1.id],
                    EntryType.DEBIT: locking_scripts[identity2.id],
                }
                vostro = Account({
                    'name': f'Payable to (Vostro for) {identity2.name} ({identity2.id})',
                    'type': AccountType.VOSTRO_LIABILITY.value,
                    'ledger_id': ledger.id,
                })
                vostro.details = identity2.id
                vostro.locking_scripts = {
                    EntryType.CREDIT: locking_scripts[identity1.id],
                    EntryType.DEBIT: locking_scripts[identity2.id],
                }
                accounts[identity1.id] = {
                    AccountType.NOSTRO_ASSET: nostro,
                    AccountType.VOSTRO_LIABILITY: vostro,
                }
        return accounts

    async def pay_correspondent(
            self, payer: Identity, payee: Identity, amount: int, txn_nonce: bytes
        ) -> tuple[list[Entry], list[Entry]]:
        """Prepares two lists of entries in which the payer remits to
            the payee the given amount: one in which the nostro account
            on the payer's ledger is credited and one in which the
            vostro account on the payer's ledger is credited.
        """
        vert(payer.id in self.identity_ids,
             f'payer ({payer.name}, {payer.id}) not in correspondence identities')
        vert(payee.id in self.identity_ids,
             f'payee ({payee.name}, {payee.id}) not in correspondence identities')
        await payer.ledgers().reload()
        await payee.ledgers().reload()
        payer_ledger: Ledger = [l for l in payer.ledgers if l.id in self.ledger_ids][0]
        payee_ledger: Ledger = [l for l in payee.ledgers if l.id in self.ledger_ids][0]
        await payer_ledger.accounts().reload()
        await payee_ledger.accounts().reload()
        payer_equity_acct: Account = [
            a for a in payer_ledger.accounts if a.type is AccountType.EQUITY
        ][0]
        payee_equity_acct: Account = [
            a for a in payee_ledger.accounts if a.type is AccountType.EQUITY
        ][0]
        accts = await self.get_accounts()
        payer_nostro_acct = accts[payer.id][AccountType.NOSTRO_ASSET]
        payer_vostro_acct = accts[payer.id][AccountType.VOSTRO_LIABILITY]
        payee_nostro_acct = accts[payee.id][AccountType.NOSTRO_ASSET]
        payee_vostro_acct = accts[payee.id][AccountType.VOSTRO_LIABILITY]

        payer_equity_entry = Entry({
            'nonce': txn_nonce,
            'type': EntryType.DEBIT,
            'amount': amount,
            'account_id': payer_equity_acct.id,
        })
        payer_equity_entry.account = payer_equity_acct
        payer_nostro_entry = Entry({
            'nonce': txn_nonce,
            'type': EntryType.CREDIT,
            'amount': amount,
            'account_id': payer_nostro_acct.id,
        })
        payer_nostro_entry.account = payer_nostro_acct
        payer_vostro_entry = Entry({
            'nonce': txn_nonce,
            'type': EntryType.CREDIT,
            'amount': amount,
            'account_id': payer_vostro_acct.id,
        })
        payer_vostro_entry.account = payer_vostro_acct

        payee_equity_entry = Entry({
            'nonce': txn_nonce,
            'type': EntryType.CREDIT,
            'amount': amount,
            'account_id': payee_equity_acct.id,
        })
        payee_equity_entry.account = payee_equity_acct
        payee_nostro_entry = Entry({
            'nonce': txn_nonce,
            'type': EntryType.DEBIT,
            'amount': amount,
            'account_id': payee_nostro_acct.id,
        })
        payee_nostro_entry.account = payee_nostro_acct
        payee_vostro_entry = Entry({
            'nonce': txn_nonce,
            'type': EntryType.DEBIT,
            'amount': amount,
            'account_id': payee_vostro_acct.id,
        })
        payee_vostro_entry.account = payee_vostro_acct

        return (
            [payer_equity_entry, payee_equity_entry, payer_nostro_entry, payee_vostro_entry],
            [payer_equity_entry, payee_equity_entry, payer_vostro_entry, payee_nostro_entry],
        )

    async def balances(
            self, rolled_up_balances: dict[str, tuple[EntryType, int]] = {}
        ) -> dict[str, int]:
        """Returns the balances of the correspondents as a dict mapping
            str Identity ID to signed int (equal to Nostro - Vostro).
        """
        accts = await self.get_accounts()
        accts = [a for accts in accts.values() for a in accts.values()]
        balances = {}
        for acct in accts:
            await acct.ledger().reload()
            if acct.ledger.identity_id not in balances:
                balances[acct.ledger.identity_id] = 0
            if acct.type is AccountType.NOSTRO_ASSET:
                balances[acct.ledger.identity_id] += await acct.balance(
                    rolled_up_balances=rolled_up_balances
                )
            if acct.type is AccountType.VOSTRO_LIABILITY:
                balances[acct.ledger.identity_id] -= await acct.balance(
                    rolled_up_balances=rolled_up_balances
                )
        return balances

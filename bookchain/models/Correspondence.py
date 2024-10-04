from __future__ import annotations
from .Account import Account, AccountType
from .Entry import Entry, EntryType
from .Identity import Identity
from .Ledger import Ledger
from sqloquent import HashedModel, RelatedCollection
from sqloquent.errors import vert


class Correspondence(HashedModel):
    table: str = 'correspondences'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'identity_ids', 'ledger_ids', 'details')
    id: str
    identity_ids: str
    ledger_ids: str
    details: str
    identities: RelatedCollection
    ledgers: RelatedCollection

    def get_accounts(self) -> list[Account]:
        """Loads the relevant nostro and vostro Accounts for the
            Identities that are part of the Correspondence.
        """
        accounts = {}
        self.ledgers().reload()
        self.identities().reload()
        id1: Identity = self.identities[0]
        for identity in self.identities:
            if identity is id1:
                continue
            identity: Identity
            for acct in id1.get_correspondent_accounts(identity):
                acct.ledger().reload()
                accounts[acct.id] = acct
        acct_ids = set([aid for aid in accounts])
        return [accounts[i] for i in acct_ids]

    def setup_accounts(self, locking_scripts: dict[str, bytes]) -> dict[str, dict[AccountType, Account]]:
        """Takes a dict mapping Identity ID to tapescript locking
            scripts. Returns a dict of Accounts necessary for setting up
            the credit Correspondence of form
            { identity.id: { AccountType: Account }}.
        """
        accounts = {}
        self.identities().reload()
        for identity1 in self.identities:
            identity1: Identity
            for identity2 in [i for i in self.identities if i.id != identity1.id]:
                identity1.ledgers().reload()
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

    def pay_correspondent(self, payer: Identity, payee: Identity, amount: int,
                          txn_nonce: bytes, reload: bool = False
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
        payer.ledgers().reload()
        payee.ledgers().reload()
        payer_ledger: Ledger = [l for l in payer.ledgers if l.id in self.ledger_ids][0]
        payee_ledger: Ledger = [l for l in payee.ledgers if l.id in self.ledger_ids][0]
        payer_ledger.accounts().reload()
        payee_ledger.accounts().reload()
        payer_equity_acct: Account = [
            a for a in payer_ledger.accounts if a.type is AccountType.EQUITY
        ][0]
        payee_equity_acct: Account = [
            a for a in payee_ledger.accounts if a.type is AccountType.EQUITY
        ][0]
        accts = self.get_accounts()
        payer_nostro_acct: Account = [
            a for a in accts
            if a.ledger_id == payer_ledger.id and a.type is AccountType.NOSTRO_ASSET
        ][0]
        payer_vostro_acct: Account = [
            a for a in accts
            if a.ledger_id == payer_ledger.id and a.type is AccountType.VOSTRO_LIABILITY
        ][0]
        payee_nostro_acct: Account = [
            a for a in accts
            if a.ledger_id == payee_ledger.id and a.type is AccountType.NOSTRO_ASSET
        ][0]
        payee_vostro_acct: Account = [
            a for a in accts
            if a.ledger_id == payee_ledger.id and a.type is AccountType.VOSTRO_LIABILITY
        ][0]

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

    def balances(self) -> dict[str, int]:
        """Returns the balances of the correspondents as a dict mapping
            str Identity ID to signed int (equal to Nostro - Vostro).
        """
        accts = self.get_accounts()
        balances = {}
        for acct in accts:
            acct.ledger().reload()
            if acct.ledger.identity_id not in balances:
                balances[acct.ledger.identity_id] = 0
            if acct.type is AccountType.NOSTRO_ASSET:
                balances[acct.ledger.identity_id] += acct.balance()
            if acct.type is AccountType.VOSTRO_LIABILITY:
                balances[acct.ledger.identity_id] -= acct.balance()
        return balances

from context import models
from genericpath import isfile
from nacl.signing import SigningKey
from packify import pack, unpack
from sqlite3 import OperationalError
from time import time
import os
import sqloquent.tools
import tapescript
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'scriptcounting/models'


class TestCorrespondencesE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        models.Identity.connection_info = DB_FILEPATH
        models.Currency.connection_info = DB_FILEPATH
        models.Correspondence.connection_info = DB_FILEPATH
        models.Ledger.connection_info = DB_FILEPATH
        models.Account.connection_info = DB_FILEPATH
        models.Entry.connection_info = DB_FILEPATH
        models.Transaction.connection_info = DB_FILEPATH
        sqloquent.DeletedModel.connection_info = DB_FILEPATH
        super().setUpClass()

    def setUp(self):
        if isfile(DB_FILEPATH):
            os.remove(DB_FILEPATH)
        super().setUp()

    def tearDown(self):
        for file in os.listdir(MIGRATIONS_PATH):
            if isfile(f'{MIGRATIONS_PATH}/{file}'):
                os.remove(f'{MIGRATIONS_PATH}/{file}')
        if isfile(DB_FILEPATH):
            os.remove(DB_FILEPATH)
        super().tearDown()

    def automigrate(self):
        sqloquent.tools.publish_migrations(MIGRATIONS_PATH)
        modelnames = ['Identity', 'Currency', 'Ledger', 'Account', 'Entry', 'Transaction', 'Correspondence']
        for name in modelnames:
            m = sqloquent.tools.make_migration_from_model(name, f'{MODELS_PATH}/{name}.py')
            with open(f'{MIGRATIONS_PATH}/create_{name}.py', 'w') as f:
                f.write(m)
        sqloquent.tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)

    def test_e2e(self):
        with self.assertRaises(OperationalError):
            models.Account.query().count()
        self.automigrate()
        assert models.Account.query().count() == 0

        # set up cryptographic stuff
        seed_alice = os.urandom(32)
        seed_bob = os.urandom(32)
        pkey_alice = bytes(SigningKey(seed_alice).verify_key)
        pkey_bob = bytes(SigningKey(seed_bob).verify_key)
        committed_script_alice = tapescript.tools.make_delegate_key_lock(pkey_alice)
        committed_script_bob = tapescript.tools.make_delegate_key_lock(pkey_bob)
        locking_script_alice = tapescript.tools.make_taproot_lock(
            pkey_alice,
            committed_script_alice
        ).bytes
        locking_script_bob = tapescript.tools.make_taproot_lock(
            pkey_bob,
            committed_script_bob
        ).bytes
        delegate_seed = os.urandom(32) # for simplicity, both will have the same delegate
        delegate_pkey = bytes(SigningKey(delegate_seed).verify_key)
        delegate_cert_alice = {
            'pkey': delegate_pkey,
            'begin_ts': int(time()) - 1,
            'end_ts': int(time()) + 60*60*24*365
        }
        delegate_cert_bob = {**delegate_cert_alice}
        delegate_cert_alice['sig'] = tapescript.make_delegate_key_cert_sig(
            seed_alice, delegate_pkey, delegate_cert_alice['begin_ts'], delegate_cert_alice['end_ts']
        )
        delegate_cert_bob['sig'] = tapescript.make_delegate_key_cert_sig(
            seed_bob, delegate_pkey, delegate_cert_bob['begin_ts'], delegate_cert_bob['end_ts']
        )

        # set up currency
        currency = models.Currency.insert({
            'name': 'Median Human Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MHH',
            'base': 60,
            'decimals': 2,
            'details': 'Abstract value of one median hour of human time. ' +
                '1 Hour = 60 Minutes = 3600 Seconds',
        })

        # set up alice, ledger_alice, accounts, and starting capital transaction
        alice: models.Identity = models.Identity.insert({
            'name': 'Alice',
            'pubkey': pkey_alice,
            'seed': seed_alice,
        })
        ledger_alice = models.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': alice.id,
            'currency_id': currency.id,
        })
        equity_acct_alice = models.Account({
            'name': 'General Equity (Alice)',
            'type': models.AccountType.EQUITY.value,
            'ledger_id': ledger_alice.id,
        })
        equity_acct_alice.locking_scripts = {models.EntryType.DEBIT: locking_script_alice}
        equity_acct_alice.save()
        asset_acct_alice = models.Account({
            'name': 'General Asset (Alice)',
            'type': models.AccountType.ASSET.value,
            'ledger_id': ledger_alice.id,
        })
        asset_acct_alice.locking_scripts = {models.EntryType.CREDIT: locking_script_alice}
        asset_acct_alice.save()
        liability_acct_alice = models.Account.insert({
            'name': 'General Liability (Alice)',
            'type': models.AccountType.LIABILITY.value,
            'ledger_id': ledger_alice.id,
        })
        liability_acct_alice.locking_scripts = {
            models.EntryType.DEBIT: locking_script_alice,
            models.EntryType.CREDIT: locking_script_alice,
        }
        liability_acct_alice.save()
        equity_acct_alice.ledger().reload()
        asset_acct_alice.ledger().reload()
        liability_acct_alice.ledger().reload()
        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': equity_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_alice
        asset_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': asset_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_alice
        txn = models.Transaction.prepare([equity_entry, asset_entry], str(time()))
        equity_entry.save()
        asset_entry.save()
        txn.save()

        # set up bob, ledger_bob, and some accounts
        bob: models.Identity = models.Identity.insert({
            'name': 'Bob',
            'pubkey': pkey_bob,
            'seed': seed_bob,
        })
        ledger_bob = models.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': bob.id,
            'currency_id': currency.id,
        })
        equity_acct_bob = models.Account({
            'name': 'General Equity (Bob)',
            'type': models.AccountType.EQUITY.value,
            'ledger_id': ledger_bob.id,
        })
        equity_acct_bob.locking_scripts = {models.EntryType.DEBIT: locking_script_bob}
        equity_acct_bob.save()
        asset_acct_bob = models.Account({
            'name': 'General Asset (Bob)',
            'type': models.AccountType.ASSET.value,
            'ledger_id': ledger_bob.id,
        })
        asset_acct_bob.locking_scripts = {models.EntryType.CREDIT: locking_script_bob}
        asset_acct_bob.save()
        liability_acct_bob = models.Account.insert({
            'name': 'General Liability (Bob)',
            'type': models.AccountType.LIABILITY.value,
            'ledger_id': ledger_bob.id,
        })
        liability_acct_bob.locking_scripts = {
            models.EntryType.DEBIT: locking_script_bob,
            models.EntryType.CREDIT: locking_script_bob,
        }
        liability_acct_bob.save()
        equity_acct_bob.ledger().reload()
        asset_acct_bob.ledger().reload()
        liability_acct_bob.ledger().reload()
        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': equity_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_bob
        asset_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': asset_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_bob
        txn = models.Transaction.prepare([equity_entry, asset_entry], str(time()))
        equity_entry.save()
        asset_entry.save()
        txn.save()

        # set up Correspondence
        assert alice.correspondences().query().count() == 0
        assert len(alice.correspondents(reload=True)) == 0
        models.Correspondence.insert({
            'identity_ids': ','.join(sorted([alice.id, bob.id])),
            'details': pack({
                'starting_capital': 'Ħ2000',
                'limits': {
                    alice.id: 'Ħ166 M40',
                    bob.id: 'Ħ166 M40',
                },
                'locking_scripts': {
                    alice.id: locking_script_alice,
                    bob.id: locking_script_bob,
                },
            })
        })
        assert alice.correspondences().query().count() == 1
        assert len(alice.correspondents(reload=True)) == 1
        assert alice.correspondents()[0].id == bob.id
        assert bob.correspondences().query().count() == 1
        assert len(bob.correspondents(reload=True)) == 1
        assert bob.correspondents()[0].id == alice.id

        # set up correspondent accounts for alice
        cor_accts1 = alice.get_correspondent_accounts(bob)
        assert len(cor_accts1) == 0, cor_accts1
        nostro_alice = models.Account()
        nostro_alice.name = f'Receivable from {bob.name} ({bob.id})'
        nostro_alice.type = models.AccountType.ASSET
        nostro_alice.ledger_id = ledger_alice.id
        nostro_alice.details = bob.id
        nostro_alice.locking_scripts = {
            models.EntryType.CREDIT: locking_script_alice,
            models.EntryType.DEBIT: locking_script_bob,
        }
        nostro_alice.save()

        vostro_alice = models.Account()
        vostro_alice.name = f'Payable to {bob.name} ({bob.id})'
        vostro_alice.type = models.AccountType.LIABILITY
        vostro_alice.ledger_id = ledger_alice.id
        vostro_alice.details = bob.id
        vostro_alice.locking_scripts = {
            models.EntryType.CREDIT: locking_script_alice,
            models.EntryType.DEBIT: locking_script_bob,
        }
        vostro_alice.save()
        cor_accts1 = alice.get_correspondent_accounts(bob)
        assert len(cor_accts1) == 2, cor_accts1

        # set up correspondent accounts for bob
        cor_accts2 = bob.get_correspondent_accounts(alice)
        assert len(cor_accts2) == 2, cor_accts2

        nostro_bob = models.Account()
        nostro_bob.name = f'Receivable from {alice.name} ({alice.id})'
        nostro_bob.type = models.AccountType.ASSET
        nostro_bob.ledger_id = ledger_bob.id
        nostro_bob.details = alice.id
        nostro_bob.locking_scripts = {
            models.EntryType.CREDIT: locking_script_bob,
            models.EntryType.DEBIT: locking_script_alice,
        }
        nostro_bob.save()

        vostro_bob = models.Account()
        vostro_bob.name = f'Payable to {alice.name} ({alice.id})'
        vostro_bob.type = models.AccountType.LIABILITY
        vostro_bob.ledger_id = ledger_bob.id
        vostro_bob.details = alice.id
        vostro_bob.locking_scripts = {
            models.EntryType.CREDIT: locking_script_bob,
            models.EntryType.DEBIT: locking_script_alice,
        }
        vostro_bob.save()
        cor_accts2 = bob.get_correspondent_accounts(alice)
        assert len(cor_accts2) == 4, cor_accts2

        # create a valid payment transaction: Alice pays Bob 200
        nonce = os.urandom(16)
        equity_entry_alice = models.Entry({
            'type': models.EntryType.DEBIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': equity_acct_alice.id,
        })
        equity_entry_alice.details = 'Debit Alice Equity'
        equity_entry_alice.account = equity_acct_alice
        liability_entry_alice = models.Entry({
            'type': models.EntryType.CREDIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': vostro_alice.id,
        })
        liability_entry_alice.details = 'Credit Alice liability'
        liability_entry_alice.account = vostro_alice
        equity_entry_bob = models.Entry({
            'type': models.EntryType.CREDIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': equity_acct_bob.id,
        })
        equity_entry_bob.details = 'Credit Bob Equity'
        equity_entry_bob.account = equity_acct_bob
        asset_entry_bob = models.Entry({
            'type': models.EntryType.DEBIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': nostro_bob.id,
        })
        asset_entry_bob.details = 'Debit Bob Asset'
        asset_entry_bob.account = nostro_bob
        auth_scripts = {
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, equity_entry_alice.get_sigfields(), committed_script_alice
            ).bytes,
            vostro_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, liability_entry_alice.get_sigfields(), committed_script_alice
            ).bytes,
            nostro_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, asset_entry_bob.get_sigfields(), committed_script_alice
            ).bytes,
        }
        txn = models.Transaction.prepare(
            [equity_entry_alice, liability_entry_alice, equity_entry_bob, asset_entry_bob],
            str(time()), auth_scripts
        )
        txn.save()

        # create an invalid transaction: valid auth, invalid entries
        nonce = os.urandom(16)
        equity_entry_alice = models.Entry({
            'type': models.EntryType.DEBIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': equity_acct_alice.id,
        })
        equity_entry_alice.details = 'Debit Alice Equity'
        equity_entry_alice.account = equity_acct_alice
        liability_entry_alice = models.Entry({
            'type': models.EntryType.CREDIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': vostro_alice.id,
        })
        liability_entry_alice.details = 'Credit Alice liability'
        liability_entry_alice.account = vostro_alice
        equity_entry_bob = models.Entry({
            'type': models.EntryType.CREDIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': equity_acct_bob.id,
        })
        equity_entry_bob.details = 'Credit Bob Equity'
        equity_entry_bob.account = equity_acct_bob
        liability_entry_bob = models.Entry({
            'type': models.EntryType.DEBIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': vostro_bob.id,
        })
        liability_entry_bob.details = 'Debit Bob Liability'
        liability_entry_bob.account = vostro_bob
        auth_scripts = {
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, equity_entry_alice.get_sigfields(), committed_script_alice
            ).bytes,
            vostro_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, liability_entry_alice.get_sigfields(), committed_script_alice
            ).bytes,
            vostro_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, liability_entry_bob.get_sigfields(), committed_script_alice
            ).bytes,
        }
        with self.assertRaises(AssertionError) as e:
            txn = models.Transaction.prepare(
                [equity_entry_alice, liability_entry_alice, equity_entry_bob, liability_entry_bob],
                str(time()), auth_scripts
            )
        assert 'validation failed' in str(e.exception)

if __name__ == '__main__':
    unittest.main()

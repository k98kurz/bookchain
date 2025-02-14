from context import models
from genericpath import isfile
from nacl.signing import SigningKey
from packify import pack
from time import time
import os
import sqloquent.tools
import tapescript
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'bookchain/models'


class TestCorrespondencesE2E(unittest.TestCase):
    @classmethod
    def automigrate(cls):
        sqloquent.tools.publish_migrations(MIGRATIONS_PATH)
        tomigrate = [
            models.Identity, models.Currency, models.Ledger,
            models.Account, models.Entry, models.Transaction,
            models.Correspondence,
        ]
        for model in tomigrate:
            name = model.__name__
            m = sqloquent.tools.make_migration_from_model(model, name)
            with open(f'{MIGRATIONS_PATH}/create_{name}.py', 'w') as f:
                f.write(m)
        sqloquent.tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)

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
        cls.automigrate()
        super().setUpClass()

    def setUp(self):
        models.Identity.query().delete()
        models.Currency.query().delete()
        models.Correspondence.query().delete()
        models.Ledger.query().delete()
        models.Account.query().delete()
        models.Entry.query().delete()
        models.Transaction.query().delete()
        sqloquent.DeletedModel.query().delete()
        self.setup_cryptographic_values()
        super().setUp()

    def tearDown(self):
        for file in os.listdir(MIGRATIONS_PATH):
            if isfile(f'{MIGRATIONS_PATH}/{file}'):
                os.remove(f'{MIGRATIONS_PATH}/{file}')
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        if isfile(DB_FILEPATH):
            os.remove(DB_FILEPATH)
        return super().tearDownClass()

    def setup_cryptographic_values(self):
        self.seed_alice = os.urandom(32)
        self.seed_bob = os.urandom(32)
        self.pkey_alice = bytes(SigningKey(self.seed_alice).verify_key)
        self.pkey_bob = bytes(SigningKey(self.seed_bob).verify_key)
        self.committed_script_alice = tapescript.tools.make_delegate_key_lock(self.pkey_alice)
        self.committed_script_bob = tapescript.tools.make_delegate_key_lock(self.pkey_bob)
        self.locking_script_alice = tapescript.tools.make_taproot_lock(
            self.pkey_alice,
            self.committed_script_alice
        ).bytes
        self.locking_script_bob = tapescript.tools.make_taproot_lock(
            self.pkey_bob,
            self.committed_script_bob
        ).bytes
        self.delegate_seed = os.urandom(32) # for simplicity, both will have the same delegate
        self.delegate_pkey = bytes(SigningKey(self.delegate_seed).verify_key)
        self.delegate_cert_alice = {
            'pkey': self.delegate_pkey,
            'begin_ts': int(time()) - 1,
            'end_ts': int(time()) + 60*60*24*365
        }
        self.delegate_cert_bob = {**self.delegate_cert_alice}
        self.delegate_cert_alice['sig'] = tapescript.make_delegate_key_cert_sig(
            self.seed_alice, self.delegate_pkey, self.delegate_cert_alice['begin_ts'],
            self.delegate_cert_alice['end_ts']
        )
        self.delegate_cert_bob['sig'] = tapescript.make_delegate_key_cert_sig(
            self.seed_bob, self.delegate_pkey, self.delegate_cert_bob['begin_ts'],
            self.delegate_cert_bob['end_ts']
        )
        self.multisig_lock = tapescript.tools.make_multisig_lock(
            [self.pkey_alice, self.pkey_bob], 2
        ).bytes

    def test_e2e(self):
        assert models.Account.query().count() == 0

        # set up currency
        currency = models.Currency.insert({
            'name': 'Median Human Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MHH',
            'base': 60,
            'unit_divisions': 2,
            'details': 'Abstract value of one median hour of human time. ' +
                '1 Hour = 60 Minutes = 3600 Seconds',
        })

        # set up alice, ledger_alice, accounts, and starting capital transaction
        alice: models.Identity = models.Identity.insert({
            'name': 'Alice',
            'pubkey': self.pkey_alice,
            'seed': self.seed_alice,
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
        equity_acct_alice.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_alice
        }
        equity_acct_alice.save()
        asset_acct_alice = models.Account({
            'name': 'General Asset (Alice)',
            'type': models.AccountType.ASSET.value,
            'ledger_id': ledger_alice.id,
        })
        asset_acct_alice.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_alice
        }
        asset_acct_alice.save()
        liability_acct_alice = models.Account.insert({
            'name': 'General Liability (Alice)',
            'type': models.AccountType.LIABILITY.value,
            'ledger_id': ledger_alice.id,
        })
        liability_acct_alice.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_alice,
            models.EntryType.CREDIT: self.locking_script_alice,
        }

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
            'pubkey': self.pkey_bob,
            'seed': self.seed_bob,
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
        equity_acct_bob.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_bob
        }
        equity_acct_bob.save()
        asset_acct_bob = models.Account({
            'name': 'General Asset (Bob)',
            'type': models.AccountType.ASSET.value,
            'ledger_id': ledger_bob.id,
        })
        asset_acct_bob.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_bob
        }
        asset_acct_bob.save()
        liability_acct_bob = models.Account.insert({
            'name': 'General Liability (Bob)',
            'type': models.AccountType.LIABILITY.value,
            'ledger_id': ledger_bob.id,
        })
        liability_acct_bob.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_bob,
            models.EntryType.CREDIT: self.locking_script_bob,
        }
        liability_acct_bob.save()

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
        correspondence: models.Correspondence = models.Correspondence.insert({
            'identity_ids': ','.join(sorted([alice.id, bob.id])),
            'ledger_ids': ','.join(sorted([ledger_alice.id, ledger_bob.id])),
            'details': pack({
                'starting_capital': 'Ħ2000',
                'limits': {
                    alice.id: 'Ħ166 M40',
                    bob.id: 'Ħ166 M40',
                },
                'locking_scripts': {
                    alice.id: self.locking_script_alice,
                    bob.id: self.locking_script_bob,
                },
                'txru_lock': self.multisig_lock,
            })
        })
        alice_sig = tapescript.make_single_sig_witness(
            alice.seed, {'sigfield1': bytes.fromhex(correspondence.id)}
        )
        bob_sig = tapescript.make_single_sig_witness(
            bob.seed, {'sigfield1': bytes.fromhex(correspondence.id)}
        )
        correspondence.signatures = {
            alice.id: alice_sig.bytes,
            bob.id: bob_sig.bytes,
            correspondence.id: (alice_sig + bob_sig).bytes,
        }
        correspondence.save()
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
        nostro_alice.type = models.AccountType.NOSTRO_ASSET
        nostro_alice.ledger_id = ledger_alice.id
        nostro_alice.details = bob.id
        nostro_alice.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_alice,
            models.EntryType.DEBIT: self.locking_script_bob,
        }
        nostro_alice.save()

        vostro_alice = models.Account()
        vostro_alice.name = f'Payable to {bob.name} ({bob.id})'
        vostro_alice.type = models.AccountType.VOSTRO_LIABILITY
        vostro_alice.ledger_id = ledger_alice.id
        vostro_alice.details = bob.id
        vostro_alice.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_alice,
            models.EntryType.DEBIT: self.locking_script_bob,
        }
        vostro_alice.save()
        cor_accts1 = alice.get_correspondent_accounts(bob)
        assert len(cor_accts1) == 2, cor_accts1

        # set up correspondent accounts for bob
        cor_accts2 = bob.get_correspondent_accounts(alice)
        assert len(cor_accts2) == 2, cor_accts2

        nostro_bob = models.Account()
        nostro_bob.name = f'Receivable from {alice.name} ({alice.id})'
        nostro_bob.type = models.AccountType.NOSTRO_ASSET
        nostro_bob.ledger_id = ledger_bob.id
        nostro_bob.details = alice.id
        nostro_bob.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_bob,
            models.EntryType.DEBIT: self.locking_script_alice,
        }
        nostro_bob.save()

        vostro_bob = models.Account()
        vostro_bob.name = f'Payable to {alice.name} ({alice.id})'
        vostro_bob.type = models.AccountType.VOSTRO_LIABILITY
        vostro_bob.ledger_id = ledger_bob.id
        vostro_bob.details = alice.id
        vostro_bob.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_bob,
            models.EntryType.DEBIT: self.locking_script_alice,
        }
        vostro_bob.save()
        cor_accts2 = bob.get_correspondent_accounts(alice)
        assert len(cor_accts2) == 4, cor_accts2

        # get correspondence accounts
        cor_accts = correspondence.get_accounts()
        assert alice.id in cor_accts
        assert bob.id in cor_accts
        assert models.AccountType.NOSTRO_ASSET in cor_accts[alice.id]
        assert models.AccountType.VOSTRO_LIABILITY in cor_accts[alice.id]
        assert models.AccountType.EQUITY in cor_accts[alice.id]
        assert models.AccountType.NOSTRO_ASSET in cor_accts[bob.id]
        assert models.AccountType.VOSTRO_LIABILITY in cor_accts[bob.id]
        assert models.AccountType.EQUITY in cor_accts[bob.id]

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
                alice.seed, equity_entry_alice.get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, liability_entry_alice.get_sigfields(), self.committed_script_alice
            ).bytes,
            nostro_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, asset_entry_bob.get_sigfields(), self.committed_script_alice
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
                alice.seed, equity_entry_alice.get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, liability_entry_alice.get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                alice.seed, liability_entry_bob.get_sigfields(), self.committed_script_alice
            ).bytes,
        }
        with self.assertRaises(AssertionError) as e:
            txn = models.Transaction.prepare(
                [equity_entry_alice, liability_entry_alice, equity_entry_bob, liability_entry_bob],
                str(time()), auth_scripts
            )
        assert 'validation failed' in str(e.exception)

    def test_helpers_e2e(self):
        assert models.Account.query().count() == 0

        # set up currency
        currency = models.Currency.insert({
            'name': 'Median Human Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MHH',
            'base': 60,
            'unit_divisions': 2,
            'details': 'Abstract value of one median hour of human time. ' +
                '1 Hour = 60 Minutes = 3600 Seconds',
        })

        # set up alice, ledger_alice, accounts, and starting capital transaction
        alice: models.Identity = models.Identity.insert({
            'name': 'Alice',
            'pubkey': self.pkey_alice,
            'seed': self.seed_alice,
        })
        ledger_alice = models.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': alice.id,
            'currency_id': currency.id,
        })
        ledger_alice.owner = alice
        asset_acct_alice, liability_acct_alice, equity_acct_alice = ledger_alice.setup_basic_accounts()

        equity_acct_alice.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_alice
        }
        equity_acct_alice.save()

        asset_acct_alice.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_alice
        }
        asset_acct_alice.save()

        liability_acct_alice.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_alice,
            models.EntryType.CREDIT: self.locking_script_alice,
        }
        liability_acct_alice.save()

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
            'pubkey': self.pkey_bob,
            'seed': self.seed_bob,
        })
        ledger_bob = models.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': bob.id,
            'currency_id': currency.id,
        })
        asset_acct_bob, liability_acct_bob, equity_acct_bob = ledger_bob.setup_basic_accounts()
        equity_acct_bob.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_bob
        }
        equity_acct_bob.save()
        asset_acct_bob.locking_scripts = {
            models.EntryType.CREDIT: self.locking_script_bob
        }
        asset_acct_bob.save()
        liability_acct_bob.locking_scripts = {
            models.EntryType.DEBIT: self.locking_script_bob,
            models.EntryType.CREDIT: self.locking_script_bob,
        }
        liability_acct_bob.save()

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
        correspondence: models.Correspondence = models.Correspondence.insert({
            'identity_ids': ','.join(sorted([alice.id, bob.id])),
            'ledger_ids': ','.join(sorted([ledger_alice.id, ledger_bob.id])),
            'details': pack({
                'starting_capital': 'Ħ2000',
                'limits': {
                    alice.id: 'Ħ166 M40',
                    bob.id: 'Ħ166 M40',
                },
                'locking_scripts': {
                    alice.id: self.locking_script_alice,
                    bob.id: self.locking_script_bob,
                },
                'txru_lock': self.multisig_lock,
            })
        })
        alice_sig = tapescript.make_single_sig_witness(
            alice.seed, {'sigfield1': bytes.fromhex(correspondence.id)}
        )
        bob_sig = tapescript.make_single_sig_witness(
            bob.seed, {'sigfield1': bytes.fromhex(correspondence.id)}
        )
        correspondence.signatures = {
            alice.id: alice_sig.bytes,
            bob.id: bob_sig.bytes,
            correspondence.id: (alice_sig + bob_sig).bytes,
        }
        correspondence.save()
        assert alice.correspondences().query().count() == 1
        assert len(alice.correspondents(reload=True)) == 1
        assert alice.correspondents()[0].id == bob.id
        assert bob.correspondences().query().count() == 1
        assert len(bob.correspondents(reload=True)) == 1
        assert bob.correspondents()[0].id == alice.id

        # set up correspondence accounts
        cor_accts = correspondence.setup_accounts({
            alice.id: self.locking_script_alice,
            bob.id: self.locking_script_bob,
        })
        for _, acct in cor_accts[alice.id].items():
            acct.save()
        for _, acct in cor_accts[bob.id].items():
            acct.save()
        nostro_acct_alice = cor_accts[alice.id][models.AccountType.NOSTRO_ASSET]
        vostro_acct_alice = cor_accts[alice.id][models.AccountType.VOSTRO_LIABILITY]
        nostro_acct_bob = cor_accts[bob.id][models.AccountType.NOSTRO_ASSET]
        vostro_acct_bob = cor_accts[bob.id][models.AccountType.VOSTRO_LIABILITY]

        # create txn: Alice credits her ledger's nostro to pay Bob
        entries, _ = correspondence.pay_correspondent(alice, bob, 100, os.urandom(16))
        assert len([e for e in entries if e.account_id == equity_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == equity_acct_bob.id]) == 1
        assert len([e for e in entries if e.account_id == nostro_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == vostro_acct_bob.id]) == 1
        txn = models.Transaction.prepare(entries, str(time()), auth_scripts={
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[0].get_sigfields(), self.committed_script_alice
            ).bytes,
            nostro_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[2].get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[3].get_sigfields(), self.committed_script_alice
            ).bytes,
        })
        assert models.Entry.query({'id': entries[0].id}).count() == 0
        txn.save()
        assert models.Entry.query({'id': entries[0].id}).count() == 1

        # create txn: Alice credits her ledger's vostro to pay Bob
        _, entries = correspondence.pay_correspondent(alice, bob, 100, os.urandom(16))
        assert len([e for e in entries if e.account_id == equity_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == equity_acct_bob.id]) == 1
        assert len([e for e in entries if e.account_id == vostro_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == nostro_acct_bob.id]) == 1
        txn = models.Transaction.prepare(entries, str(time()), auth_scripts={
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[0].get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[2].get_sigfields(), self.committed_script_alice
            ).bytes,
            nostro_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[3].get_sigfields(), self.committed_script_alice
            ).bytes,
        })
        txn.save()

        # check balances
        balances = correspondence.balances()
        assert type(balances) is dict
        assert alice.id in balances
        assert bob.id in balances
        assert balances[alice.id] == -200, balances
        assert balances[bob.id] == 200, balances


if __name__ == '__main__':
    unittest.main()

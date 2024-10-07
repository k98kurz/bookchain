from asyncio import run
from context import asyncql
from genericpath import isfile
from nacl.signing import SigningKey
from packify import pack
from time import time
import os
import sqloquent.asyncql
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
            asyncql.Identity, asyncql.Currency, asyncql.Ledger,
            asyncql.Account, asyncql.Entry, asyncql.Transaction,
            asyncql.Correspondence,
        ]
        for model in tomigrate:
            name = model.__name__
            m = sqloquent.tools.make_migration_from_model(model, name)
            with open(f'{MIGRATIONS_PATH}/create_{name}.py', 'w') as f:
                f.write(m)
        sqloquent.tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)

    @classmethod
    def setUpClass(cls):
        asyncql.Identity.connection_info = DB_FILEPATH
        asyncql.Currency.connection_info = DB_FILEPATH
        asyncql.Correspondence.connection_info = DB_FILEPATH
        asyncql.Ledger.connection_info = DB_FILEPATH
        asyncql.Account.connection_info = DB_FILEPATH
        asyncql.Entry.connection_info = DB_FILEPATH
        asyncql.Transaction.connection_info = DB_FILEPATH
        sqloquent.asyncql.AsyncDeletedModel.connection_info = DB_FILEPATH
        cls.automigrate()
        super().setUpClass()

    def setUp(self):
        run(asyncql.Identity.query().delete())
        run(asyncql.Currency.query().delete())
        run(asyncql.Correspondence.query().delete())
        run(asyncql.Ledger.query().delete())
        run(asyncql.Account.query().delete())
        run(asyncql.Entry.query().delete())
        run(asyncql.Transaction.query().delete())
        run(sqloquent.asyncql.AsyncDeletedModel.query().delete())
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

    def test_e2e(self):
        assert run(asyncql.Account.query().count()) == 0

        # set up currency
        currency = run(asyncql.Currency.insert({
            'name': 'Median Human Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MHH',
            'base': 60,
            'decimals': 2,
            'details': 'Abstract value of one median hour of human time. ' +
                '1 Hour = 60 Minutes = 3600 Seconds',
        }))

        # set up alice, ledger_alice, accounts, and starting capital transaction
        alice: asyncql.Identity = run(asyncql.Identity.insert({
            'name': 'Alice',
            'pubkey': self.pkey_alice,
            'seed': self.seed_alice,
        }))
        ledger_alice = run(asyncql.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': alice.id,
            'currency_id': currency.id,
        }))
        equity_acct_alice = asyncql.Account({
            'name': 'General Equity (Alice)',
            'type': asyncql.AccountType.EQUITY.value,
            'ledger_id': ledger_alice.id,
        })
        equity_acct_alice.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_alice
        }
        run(equity_acct_alice.save())
        asset_acct_alice = asyncql.Account({
            'name': 'General Asset (Alice)',
            'type': asyncql.AccountType.ASSET.value,
            'ledger_id': ledger_alice.id,
        })
        asset_acct_alice.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_alice
        }
        run(asset_acct_alice.save())
        liability_acct_alice = run(asyncql.Account.insert({
            'name': 'General Liability (Alice)',
            'type': asyncql.AccountType.LIABILITY.value,
            'ledger_id': ledger_alice.id,
        }))
        liability_acct_alice.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_alice,
            asyncql.EntryType.CREDIT: self.locking_script_alice,
        }
        run(liability_acct_alice.save())
        run(equity_acct_alice.ledger().reload())
        run(asset_acct_alice.ledger().reload())
        run(liability_acct_alice.ledger().reload())
        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_alice
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_alice
        txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(time())))
        run(equity_entry.save())
        run(asset_entry.save())
        run(txn.save())

        # set up bob, ledger_bob, and some accounts
        bob: asyncql.Identity = run(asyncql.Identity.insert({
            'name': 'Bob',
            'pubkey': self.pkey_bob,
            'seed': self.seed_bob,
        }))
        ledger_bob = run(asyncql.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': bob.id,
            'currency_id': currency.id,
        }))
        equity_acct_bob = asyncql.Account({
            'name': 'General Equity (Bob)',
            'type': asyncql.AccountType.EQUITY.value,
            'ledger_id': ledger_bob.id,
        })
        equity_acct_bob.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_bob
        }
        run(equity_acct_bob.save())
        asset_acct_bob = asyncql.Account({
            'name': 'General Asset (Bob)',
            'type': asyncql.AccountType.ASSET.value,
            'ledger_id': ledger_bob.id,
        })
        asset_acct_bob.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_bob
        }
        run(asset_acct_bob.save())
        liability_acct_bob = run(asyncql.Account.insert({
            'name': 'General Liability (Bob)',
            'type': asyncql.AccountType.LIABILITY.value,
            'ledger_id': ledger_bob.id,
        }))
        liability_acct_bob.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_bob,
            asyncql.EntryType.CREDIT: self.locking_script_bob,
        }
        run(liability_acct_bob.save())
        run(equity_acct_bob.ledger().reload())
        run(asset_acct_bob.ledger().reload())
        run(liability_acct_bob.ledger().reload())
        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_bob
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_bob
        txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(time())))
        run(equity_entry.save())
        run(asset_entry.save())
        run(txn.save())

        # set up Correspondence
        assert run(alice.correspondences().query().count()) == 0
        assert len(run(alice.correspondents(reload=True))) == 0
        run(asyncql.Correspondence.insert({
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
            })
        }))
        assert run(alice.correspondences().query().count()) == 1
        assert len(run(alice.correspondents(reload=True))) == 1
        assert run(alice.correspondents())[0].id == bob.id
        assert run(bob.correspondences().query().count()) == 1
        assert len(run(bob.correspondents(reload=True))) == 1
        assert run(bob.correspondents())[0].id == alice.id

        # set up correspondent accounts for alice
        cor_accts1 = run(alice.get_correspondent_accounts(bob))
        assert len(cor_accts1) == 0, cor_accts1
        nostro_alice = asyncql.Account()
        nostro_alice.name = f'Receivable from {bob.name} ({bob.id})'
        nostro_alice.type = asyncql.AccountType.NOSTRO_ASSET
        nostro_alice.ledger_id = ledger_alice.id
        nostro_alice.details = bob.id
        nostro_alice.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_alice,
            asyncql.EntryType.DEBIT: self.locking_script_bob,
        }
        run(nostro_alice.save())

        vostro_alice = asyncql.Account()
        vostro_alice.name = f'Payable to {bob.name} ({bob.id})'
        vostro_alice.type = asyncql.AccountType.VOSTRO_LIABILITY
        vostro_alice.ledger_id = ledger_alice.id
        vostro_alice.details = bob.id
        vostro_alice.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_alice,
            asyncql.EntryType.DEBIT: self.locking_script_bob,
        }
        run(vostro_alice.save())
        cor_accts1 = run(alice.get_correspondent_accounts(bob))
        assert len(cor_accts1) == 2, cor_accts1

        # set up correspondent accounts for bob
        cor_accts2 = run(bob.get_correspondent_accounts(alice))
        assert len(cor_accts2) == 2, cor_accts2

        nostro_bob = asyncql.Account()
        nostro_bob.name = f'Receivable from {alice.name} ({alice.id})'
        nostro_bob.type = asyncql.AccountType.NOSTRO_ASSET
        nostro_bob.ledger_id = ledger_bob.id
        nostro_bob.details = alice.id
        nostro_bob.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_bob,
            asyncql.EntryType.DEBIT: self.locking_script_alice,
        }
        run(nostro_bob.save())

        vostro_bob = asyncql.Account()
        vostro_bob.name = f'Payable to {alice.name} ({alice.id})'
        vostro_bob.type = asyncql.AccountType.VOSTRO_LIABILITY
        vostro_bob.ledger_id = ledger_bob.id
        vostro_bob.details = alice.id
        vostro_bob.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_bob,
            asyncql.EntryType.DEBIT: self.locking_script_alice,
        }
        run(vostro_bob.save())
        cor_accts2 = run(bob.get_correspondent_accounts(alice))
        assert len(cor_accts2) == 4, cor_accts2

        # create a valid payment transaction: Alice pays Bob 200
        nonce = os.urandom(16)
        equity_entry_alice = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': equity_acct_alice.id,
        })
        equity_entry_alice.details = 'Debit Alice Equity'
        equity_entry_alice.account = equity_acct_alice
        liability_entry_alice = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': vostro_alice.id,
        })
        liability_entry_alice.details = 'Credit Alice liability'
        liability_entry_alice.account = vostro_alice
        equity_entry_bob = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'amount': 200,
            'nonce': nonce,
            'account_id': equity_acct_bob.id,
        })
        equity_entry_bob.details = 'Credit Bob Equity'
        equity_entry_bob.account = equity_acct_bob
        asset_entry_bob = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
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
        txn = run(asyncql.Transaction.prepare(
            [equity_entry_alice, liability_entry_alice, equity_entry_bob, asset_entry_bob],
            str(time()), auth_scripts
        ))
        run(txn.save())

        # create an invalid transaction: valid auth, invalid entries
        nonce = os.urandom(16)
        equity_entry_alice = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': equity_acct_alice.id,
        })
        equity_entry_alice.details = 'Debit Alice Equity'
        equity_entry_alice.account = equity_acct_alice
        liability_entry_alice = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': vostro_alice.id,
        })
        liability_entry_alice.details = 'Credit Alice liability'
        liability_entry_alice.account = vostro_alice
        equity_entry_bob = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'amount': 100,
            'nonce': nonce,
            'account_id': equity_acct_bob.id,
        })
        equity_entry_bob.details = 'Credit Bob Equity'
        equity_entry_bob.account = equity_acct_bob
        liability_entry_bob = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
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
            txn = run(asyncql.Transaction.prepare(
                [equity_entry_alice, liability_entry_alice, equity_entry_bob, liability_entry_bob],
                str(time()), auth_scripts
            ))
        assert 'validation failed' in str(e.exception)

    def test_helpers_e2e(self):
        assert run(asyncql.Account.query().count()) == 0

        # set up currency
        currency = run(asyncql.Currency.insert({
            'name': 'Median Human Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MHH',
            'base': 60,
            'decimals': 2,
            'details': 'Abstract value of one median hour of human time. ' +
                '1 Hour = 60 Minutes = 3600 Seconds',
        }))

        # set up alice, ledger_alice, accounts, and starting capital transaction
        alice: asyncql.Identity = run(asyncql.Identity.insert({
            'name': 'Alice',
            'pubkey': self.pkey_alice,
            'seed': self.seed_alice,
        }))
        ledger_alice = run(asyncql.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': alice.id,
            'currency_id': currency.id,
        }))
        ledger_alice.owner = alice
        asset_acct_alice, liability_acct_alice, equity_acct_alice = ledger_alice.setup_basic_accounts()

        equity_acct_alice.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_alice
        }
        run(equity_acct_alice.save())

        asset_acct_alice.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_alice
        }
        run(asset_acct_alice.save())

        liability_acct_alice.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_alice,
            asyncql.EntryType.CREDIT: self.locking_script_alice,
        }
        run(liability_acct_alice.save())
        run(equity_acct_alice.ledger().reload())
        run(asset_acct_alice.ledger().reload())
        run(liability_acct_alice.ledger().reload())

        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_alice
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_alice
        txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(time())))
        run(equity_entry.save())
        run(asset_entry.save())
        run(txn.save())

        # set up bob, ledger_bob, and some accounts
        bob: asyncql.Identity = run(asyncql.Identity.insert({
            'name': 'Bob',
            'pubkey': self.pkey_bob,
            'seed': self.seed_bob,
        }))
        ledger_bob = run(asyncql.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': bob.id,
            'currency_id': currency.id,
        }))
        asset_acct_bob, liability_acct_bob, equity_acct_bob = ledger_bob.setup_basic_accounts()
        equity_acct_bob.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_bob
        }
        run(equity_acct_bob.save())
        asset_acct_bob.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_bob
        }
        run(asset_acct_bob.save())
        liability_acct_bob.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_bob,
            asyncql.EntryType.CREDIT: self.locking_script_bob,
        }
        run(liability_acct_bob.save())
        run(equity_acct_bob.ledger().reload())
        run(asset_acct_bob.ledger().reload())
        run(liability_acct_bob.ledger().reload())

        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_bob
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_bob
        txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(time())))
        run(equity_entry.save())
        run(asset_entry.save())
        run(txn.save())

        # set up Correspondence
        assert run(alice.correspondences().query().count()) == 0
        assert len(run(alice.correspondents(reload=True))) == 0
        correspondence: asyncql.Correspondence = run(asyncql.Correspondence.insert({
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
            })
        }))
        assert run(alice.correspondences().query().count()) == 1
        assert len(run(alice.correspondents(reload=True))) == 1
        assert run(alice.correspondents())[0].id == bob.id
        assert run(bob.correspondences().query().count()) == 1
        assert len(run(bob.correspondents(reload=True))) == 1
        assert run(bob.correspondents())[0].id == alice.id

        # set up correspondence accounts
        cor_accts = run(correspondence.setup_accounts({
            alice.id: self.locking_script_alice,
            bob.id: self.locking_script_bob,
        }))
        for _, acct in cor_accts[alice.id].items():
            run(acct.save())
            run(acct.ledger().reload())
        for _, acct in cor_accts[bob.id].items():
            run(acct.save())
            run(acct.ledger().reload())
        nostro_acct_alice = cor_accts[alice.id][asyncql.AccountType.NOSTRO_ASSET]
        vostro_acct_alice = cor_accts[alice.id][asyncql.AccountType.VOSTRO_LIABILITY]
        nostro_acct_bob = cor_accts[bob.id][asyncql.AccountType.NOSTRO_ASSET]
        vostro_acct_bob = cor_accts[bob.id][asyncql.AccountType.VOSTRO_LIABILITY]

        # create txn: Alice credits her ledger's nostro to pay Bob
        entries, _ = run(correspondence.pay_correspondent(alice, bob, 100, os.urandom(16)))
        assert len([e for e in entries if e.account_id == equity_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == equity_acct_bob.id]) == 1
        assert len([e for e in entries if e.account_id == nostro_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == vostro_acct_bob.id]) == 1
        txn = run(asyncql.Transaction.prepare(entries, str(time()), auth_scripts={
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[0].get_sigfields(), self.committed_script_alice
            ).bytes,
            nostro_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[2].get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[3].get_sigfields(), self.committed_script_alice
            ).bytes,
        }))
        assert run(asyncql.Entry.query({'id': entries[0].id}).count()) == 0
        run(txn.save())
        assert run(asyncql.Entry.query({'id': entries[0].id}).count()) == 1

        # create txn: Alice credits her ledger's vostro to pay Bob
        _, entries = run(correspondence.pay_correspondent(alice, bob, 100, os.urandom(16)))
        assert len([e for e in entries if e.account_id == equity_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == equity_acct_bob.id]) == 1
        assert len([e for e in entries if e.account_id == vostro_acct_alice.id]) == 1
        assert len([e for e in entries if e.account_id == nostro_acct_bob.id]) == 1
        txn = run(asyncql.Transaction.prepare(entries, str(time()), auth_scripts={
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[0].get_sigfields(), self.committed_script_alice
            ).bytes,
            vostro_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[2].get_sigfields(), self.committed_script_alice
            ).bytes,
            nostro_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[3].get_sigfields(), self.committed_script_alice
            ).bytes,
        }))
        run(txn.save())

        # check balances
        balances = run(correspondence.balances())
        assert type(balances) is dict
        assert alice.id in balances
        assert bob.id in balances
        assert balances[alice.id] == -200, balances
        assert balances[bob.id] == 200, balances


if __name__ == '__main__':
    unittest.main()

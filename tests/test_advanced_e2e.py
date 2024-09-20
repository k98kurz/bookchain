from context import models
from genericpath import isfile
from nacl.signing import SigningKey
from sqlite3 import OperationalError
from time import time
import os
import sqloquent
import tapescript
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'scriptcounting/models'


class TestBasicE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        models.Identity.connection_info = DB_FILEPATH
        models.Currency.connection_info = DB_FILEPATH
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
        modelnames = ['Identity', 'Currency', 'Ledger', 'Account', 'Entry', 'Transaction']
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
        seed = os.urandom(32)
        pkey = bytes(SigningKey(seed).verify_key)
        committed_script = tapescript.tools.make_delegate_key_lock(pkey)
        locking_script = tapescript.tools.make_taproot_lock(
            pkey,
            committed_script
        ).bytes
        delegate_seed = os.urandom(32)
        delegate_pkey = bytes(SigningKey(delegate_seed).verify_key)
        delegate_cert = {
            'pkey': delegate_pkey,
            'begin_ts': int(time()) - 1,
            'end_ts': int(time()) + 60*60*24*365
        }
        delegate_cert['sig'] = tapescript.make_delegate_key_cert_sig(
            seed, delegate_pkey, delegate_cert['begin_ts'], delegate_cert['end_ts']
        )

        # set up identity, currency, ledger, and some accounts
        identity = models.Identity.insert({
            'name': 'Test Man',
            'pubkey': pkey,
            'seed': seed,
        })
        currency = models.Currency.insert({
            'name': 'US Dollar',
            'prefix_symbol': '$',
            'fx_symbol': 'USD',
            'base': 10,
            'decimals': 2,
        })
        ledger = models.Ledger.insert({
            'name': 'General Ledger',
            'identity_id': identity.id,
            'currency_id': currency.id,
        })
        equity_acct = models.Account({
            'name': 'General Equity',
            'type': models.AccountType.EQUITY.value,
            'ledger_id': ledger.id,
            'locking_script': locking_script,
        })
        equity_acct.LockEntryTypes = [models.EntryType.DEBIT]
        equity_acct.save()
        asset_acct = models.Account({
            'name': 'General Asset',
            'type': models.AccountType.ASSET.value,
            'ledger_id': ledger.id,
            'locking_script': locking_script,
        })
        asset_acct.LockEntryTypes = [models.EntryType.CREDIT]
        asset_acct.save()
        liability_acct = models.Account.insert({
            'name': 'General Liability',
            'type': models.AccountType.LIABILITY.value,
            'ledger_id': ledger.id,
            'locking_script': locking_script,
        })
        liability_acct.LockEntryTypes = [models.EntryType.DEBIT, models.EntryType.CREDIT]
        liability_acct.save()
        equity_acct.ledger().reload()
        asset_acct.ledger().reload()
        liability_acct.ledger().reload()

        # prepare and save a valid transaction: no auth required
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': equity_acct.id,
            'amount': 10_000_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        asset_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': asset_acct.id,
            'amount': 10_000_00,
            'nonce': txn_nonce,
        })
        asset_entry.account = asset_acct
        txn = models.Transaction.prepare([equity_entry, asset_entry], str(time()))
        assert txn.validate()
        equity_entry.save()
        asset_entry.save()
        txn.save()

        # prepare and save a valid transaction: auth required
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': liability_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        liability_entry.account = liability_acct
        liability_entry.id = liability_entry.generate_id(liability_entry.data)
        auth_scripts = {
            equity_acct.id: tapescript.tools.make_taproot_witness_keyspend(
                seed, equity_entry.get_sigfields(), committed_script
            ).bytes,
            liability_acct.id: tapescript.tools.make_taproot_witness_keyspend(
                seed, liability_entry.get_sigfields(), committed_script
            ).bytes,
        }
        txn = models.Transaction.prepare(
            [equity_entry, liability_entry],
            str(time()),
            auth_scripts,
        )
        assert txn.validate(auth_scripts=auth_scripts)
        equity_entry.save()
        asset_entry.save()
        txn.save()

        # prepare and save a valid transaction: auth required - delegated
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 90_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': liability_acct.id,
            'amount': 90_00,
            'nonce': txn_nonce,
        })
        liability_entry.account = liability_acct
        liability_entry.id = liability_entry.generate_id(liability_entry.data)
        auth_scripts = {
            equity_acct.id: (
                tapescript.tools.make_delegate_key_unlock(
                    delegate_seed,
                    delegate_pkey,
                    delegate_cert['begin_ts'],
                    delegate_cert['end_ts'],
                    delegate_cert['sig'],
                    equity_entry.get_sigfields()
                ) +
                tapescript.tools.make_taproot_witness_scriptspend(
                    pkey, committed_script
                )
            ).bytes,
            liability_acct.id: (
                tapescript.tools.make_delegate_key_unlock(
                    delegate_seed,
                    delegate_pkey,
                    delegate_cert['begin_ts'],
                    delegate_cert['end_ts'],
                    delegate_cert['sig'],
                    liability_entry.get_sigfields()
                ) +
                tapescript.tools.make_taproot_witness_scriptspend(
                    pkey, committed_script
                )
            ).bytes,
        }
        txn = models.Transaction.prepare(
            [equity_entry, liability_entry],
            str(time()),
            auth_scripts,
        )
        assert txn.validate(auth_scripts=auth_scripts)
        equity_entry.save()
        asset_entry.save()
        txn.save()

        # prepare invalid transaction: missing auth
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': liability_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        liability_entry.account = liability_acct
        liability_entry.id = liability_entry.generate_id(liability_entry.data)
        auth_scripts = {}
        with self.assertRaises(ValueError) as e:
            txn = models.Transaction.prepare(
                [equity_entry, liability_entry],
                str(time()),
                auth_scripts,
            )
        assert 'missing auth' in str(e.exception)

        # prepare invalid transaction: invalid auth
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': liability_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        liability_entry.account = liability_acct
        liability_entry.id = liability_entry.generate_id(liability_entry.data)
        auth_scripts = {
            equity_acct.id: tapescript.tools.make_taproot_witness_keyspend(
                seed, {'sigfield1': bytes.fromhex(liability_entry.id)}, committed_script
            ).bytes,
            liability_acct.id: tapescript.tools.make_taproot_witness_keyspend(
                seed, {'sigfield1': bytes.fromhex(equity_entry.id)}, committed_script
            ).bytes,
        }
        with self.assertRaises(AssertionError) as e:
            txn = models.Transaction.prepare(
                [equity_entry, liability_entry],
                str(time()),
                auth_scripts,
            )
        assert 'validation failed' in str(e.exception)

        # prepare invalid transaction: reused entries
        with self.assertRaises(ValueError) as e:
            txn = models.Transaction.prepare([equity_entry, asset_entry], str(int(time())))
        assert 'already contained within a Transaction' in str(e.exception)

        # prepare invalid transaction: unbalanced entries
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry({
            'type': models.EntryType.CREDIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        asset_entry = models.Entry({
            'type': models.EntryType.DEBIT,
            'account_id': asset_acct.id,
            'amount': 10_01,
            'nonce': txn_nonce,
        })
        asset_entry.account = asset_acct
        with self.assertRaises(ValueError) as e:
            txn = models.Transaction.prepare([equity_entry, asset_entry], str(int(time())))
        assert 'unbalanced' in str(e.exception)


if __name__ == '__main__':
    unittest.main()
from asyncio import run
from context import asyncql
from genericpath import isfile
from nacl.signing import SigningKey
from sqlite3 import OperationalError
from time import time
import os
import sqloquent.asyncql
import sqloquent.tools
import tapescript
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'bookchain/models'


class TestAsyncAdvancedE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncql.Identity.connection_info = DB_FILEPATH
        asyncql.Currency.connection_info = DB_FILEPATH
        asyncql.Ledger.connection_info = DB_FILEPATH
        asyncql.Account.connection_info = DB_FILEPATH
        asyncql.Entry.connection_info = DB_FILEPATH
        asyncql.Transaction.connection_info = DB_FILEPATH
        sqloquent.asyncql.AsyncDeletedModel.connection_info = DB_FILEPATH
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
        tomigrate = [
            asyncql.Identity, asyncql.Currency, asyncql.Ledger,
            asyncql.Account, asyncql.Entry, asyncql.Transaction,
        ]
        for model in tomigrate:
            name = model.__name__
            m = sqloquent.tools.make_migration_from_model(model, name)
            with open(f'{MIGRATIONS_PATH}/create_{name}.py', 'w') as f:
                f.write(m)
        sqloquent.tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)

    def test_e2e(self):
        with self.assertRaises(OperationalError):
            run(asyncql.Account.query().count())
        self.automigrate()
        assert run(asyncql.Account.query().count()) == 0

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
        begin_ts = int(time()) - 1
        end_ts = int(time()) + 60*60*24*365
        delegate_cert = tapescript.make_delegate_key_cert(
            seed, delegate_pkey, begin_ts, end_ts
        )

        # set up identity, currency, ledger, and some accounts
        identity = run(asyncql.Identity.insert({
            'name': 'Test Man',
            'pubkey': pkey,
            'seed': seed,
        }))
        currency = run(asyncql.Currency.insert({
            'name': 'US Dollar',
            'prefix_symbol': '$',
            'fx_symbol': 'USD',
            'base': 10,
            'unit_divisions': 2,
        }))
        ledger = run(asyncql.Ledger.insert({
            'name': 'General Ledger',
            'identity_id': identity.id,
            'currency_id': currency.id,
        }))
        equity_acct = asyncql.Account({
            'name': 'General Equity',
            'type': asyncql.AccountType.EQUITY.value,
            'ledger_id': ledger.id,
        })
        equity_acct.locking_scripts = {asyncql.EntryType.DEBIT: locking_script}
        run(equity_acct.save())
        asset_acct = asyncql.Account({
            'name': 'General Asset',
            'type': asyncql.AccountType.ASSET.value,
            'ledger_id': ledger.id,
        })
        asset_acct.locking_scripts = {asyncql.EntryType.CREDIT: locking_script}
        run(asset_acct.save())
        liability_acct = run(asyncql.Account.insert({
            'name': 'General Liability',
            'type': asyncql.AccountType.LIABILITY.value,
            'ledger_id': ledger.id,
        }))
        liability_acct.locking_scripts = {
            asyncql.EntryType.DEBIT: locking_script,
            asyncql.EntryType.CREDIT: locking_script,
        }
        run(liability_acct.save())
        run(equity_acct.ledger().reload())
        run(asset_acct.ledger().reload())
        run(liability_acct.ledger().reload())

        # prepare and save a valid transaction: no auth required
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct.id,
            'amount': 10_000_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct.id,
            'amount': 10_000_00,
            'nonce': txn_nonce,
        })
        asset_entry.account = asset_acct
        txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(time())))
        assert run(txn.validate())
        assert run(asyncql.Entry.query({'id': equity_entry.id}).count()) == 0
        assert run(asyncql.Entry.query({'id': asset_entry.id}).count()) == 0
        run(txn.save())
        assert run(asyncql.Entry.query({'id': equity_entry.id}).count()) == 1
        assert run(asyncql.Entry.query({'id': asset_entry.id}).count()) == 1
        # reload txn from database and validate it
        txn: asyncql.Transaction = run(asyncql.Transaction.find(txn.id))
        assert run(txn.validate(reload=True))

        # prepare and save a valid transaction: auth required
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
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
        assert len(equity_entry.get_sigfields()['sigfield1']) == 32
        txn = run(asyncql.Transaction.prepare(
            [equity_entry, liability_entry],
            str(time()),
            auth_scripts,
        ))
        assert run(txn.validate())
        run(equity_entry.save())
        run(liability_entry.save())
        run(txn.save())
        # reload txn from database and validate it
        txn: asyncql.Transaction = run(asyncql.Transaction.find(txn.id))
        assert run(txn.validate(reload=True))

        # prepare and save a valid transaction: auth required - delegated
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 90_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': liability_acct.id,
            'amount': 90_00,
            'nonce': txn_nonce,
        })
        liability_entry.account = liability_acct
        liability_entry.id = liability_entry.generate_id(liability_entry.data)
        auth_scripts = {
            equity_acct.id: (
                tapescript.tools.make_delegate_key_witness(
                    delegate_seed,
                    delegate_cert,
                    equity_entry.get_sigfields()
                ) +
                tapescript.tools.make_taproot_witness_scriptspend(
                    pkey, committed_script
                )
            ).bytes,
            liability_acct.id: (
                tapescript.tools.make_delegate_key_witness(
                    delegate_seed,
                    delegate_cert,
                    liability_entry.get_sigfields()
                ) +
                tapescript.tools.make_taproot_witness_scriptspend(
                    pkey, committed_script
                )
            ).bytes,
        }
        txn = run(asyncql.Transaction.prepare(
            [equity_entry, liability_entry],
            str(time()),
            auth_scripts,
        ))
        assert run(txn.validate())
        run(equity_entry.save())
        run(liability_entry.save())
        run(txn.save())
        # reload txn from database and validate it
        txn: asyncql.Transaction = run(asyncql.Transaction.find(txn.id))
        assert run(txn.validate(reload=True))

        # prepare invalid transaction: missing auth
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': liability_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        liability_entry.account = liability_acct
        liability_entry.id = liability_entry.generate_id(liability_entry.data)
        auth_scripts = {}
        with self.assertRaises(ValueError) as e:
            txn = run(asyncql.Transaction.prepare(
                [equity_entry, liability_entry],
                str(time()),
                auth_scripts,
            ))
        assert 'missing auth' in str(e.exception)

        # prepare invalid transaction: invalid auth
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
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
            txn = run(asyncql.Transaction.prepare(
                [equity_entry, liability_entry],
                str(time()),
                auth_scripts,
            ))
        assert 'validation failed' in str(e.exception)

        # prepare invalid transaction: reused entries
        with self.assertRaises(ValueError) as e:
            txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(int(time()))))
        assert 'already contained within a Transaction' in str(e.exception)

        # prepare invalid transaction: unbalanced entries
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct.id,
            'amount': 10_01,
            'nonce': txn_nonce,
        })
        asset_entry.account = asset_acct
        with self.assertRaises(ValueError) as e:
            txn = run(asyncql.Transaction.prepare([equity_entry, asset_entry], str(int(time()))))
        assert 'unbalanced' in str(e.exception)


        # test get_sigfields plugin system
        def get_sigfields(entry: asyncql.Entry, *args, **kwargs) -> dict:
            """Concat the entry id to the account id."""
            return {
                'sigfield1': bytes.fromhex(entry.id + entry.account_id)
            }
        asyncql.Entry.set_sigfield_plugin(get_sigfields)

        # prepare and save a valid transaction: auth required
        txn_nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 10_00,
            'nonce': txn_nonce,
        })
        equity_entry.account = equity_acct
        equity_entry.id = equity_entry.generate_id(equity_entry.data)
        liability_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
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
        assert len(equity_entry.get_sigfields()['sigfield1']) == 64
        txn = run(asyncql.Transaction.prepare(
            [equity_entry, liability_entry],
            str(time()),
            auth_scripts,
        ))
        assert run(txn.validate())
        run(txn.save())
        # cleanup
        del asyncql.Entry._plugin


if __name__ == '__main__':
    unittest.main()

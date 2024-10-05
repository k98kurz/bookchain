from context import models
from genericpath import isfile
from sqlite3 import OperationalError
from sqloquent import DeletedModel
from time import time
import os
import sqloquent.tools
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'


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
        tomigrate = [
            models.Identity, models.Currency, models.Ledger,
            models.Account, models.Entry, models.Transaction,
        ]
        for model in tomigrate:
            name = model.__name__
            m = sqloquent.tools.make_migration_from_model(model, name)
            with open(f'{MIGRATIONS_PATH}/create_{name}.py', 'w') as f:
                f.write(m)
        sqloquent.tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)

    def test_e2e(self):
        with self.assertRaises(OperationalError):
            models.Account.query().count()
        self.automigrate()
        assert models.Account.query().count() == 0

        # setup identity, currency, ledger, and some accounts
        identity = models.Identity.insert({'name': 'Test Man'})
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
        equity_acct = models.Account.insert({
            'name': 'General Equity',
            'type': models.AccountType.EQUITY,
            'ledger_id': ledger.id,
        })
        asset_acct = models.Account.insert({
            'name': 'General Asset',
            'type': models.AccountType.ASSET,
            'ledger_id': ledger.id,
        })
        liability_acct = models.Account.insert({
            'name': 'General Liability',
            'type': models.AccountType.LIABILITY,
            'ledger_id': ledger.id,
        })

        # make sub account
        assert len(liability_acct.children) == 0
        liability_sub_acct = models.Account.insert({
            'name': 'Liability Sub Account',
            'type': models.AccountType.LIABILITY,
            'ledger_id': ledger.id,
            'parent_id': liability_acct.id,
        })
        assert liability_sub_acct.parent is not None, liability_sub_acct.parent
        assert liability_sub_acct.parent.id == liability_acct.id, liability_sub_acct.parent
        liability_acct.children().reload()
        assert len(liability_acct.children) == 1
        assert liability_acct.children[0].id == liability_sub_acct.id

        # prepare and save a valid transaction
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
        txn = models.Transaction.prepare(
            [equity_entry, asset_entry], str(time()),
            details='Starting capital asset'
        )
        assert txn.validate()
        equity_entry.save()
        asset_entry.save()
        txn.save()
        # reload txn from database and validate it
        txn: models.Transaction = models.Transaction.find(txn.id)
        assert txn.validate(reload=True)

        # check balances
        assert equity_acct.balance() == 10_000_00, equity_acct.balance()
        assert asset_acct.balance() == 10_000_00, asset_acct.balance()
        assert liability_acct.balance() == 0, liability_acct.balance()

        # prepare and save valid transaction for liability sub account
        txn_nonce = os.urandom(16)
        equity_entry = models.Entry.insert({
            'type': models.EntryType.DEBIT,
            'account_id': equity_acct.id,
            'amount': 9_99,
            'nonce': txn_nonce,
        })
        liability_entry = models.Entry.insert({
            'type': models.EntryType.CREDIT,
            'account_id': liability_sub_acct.id,
            'amount': 9_99,
            'nonce': txn_nonce,
        })
        txn = models.Transaction.prepare([equity_entry, liability_entry], str(time()))
        assert txn.validate()
        txn.save()

        # check balances
        assert equity_acct.balance() == 10_000_00-9_99, equity_acct.balance()
        assert asset_acct.balance() == 10_000_00, asset_acct.balance()
        assert liability_sub_acct.balance() == 9_99, liability_acct.balance()
        assert liability_acct.balance() == 9_99, liability_acct.balance()
        assert liability_acct.balance(False) == 0, liability_acct.balance(False)

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

        # delete something
        deleted = identity.delete()
        assert isinstance(deleted, DeletedModel)
        assert models.Identity.find(identity.id) is None

        # restore deleted identity
        restored = deleted.restore({'Identity': models.Identity})
        assert isinstance(restored, models.Identity)
        assert restored.id == identity.id
        restored.save()
        assert models.Identity.find(identity.id) is not None


if __name__ == '__main__':
    unittest.main()

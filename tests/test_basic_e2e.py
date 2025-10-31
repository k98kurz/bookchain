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
        models.AccountCategory.connection_info = DB_FILEPATH
        models.Entry.connection_info = DB_FILEPATH
        models.Transaction.connection_info = DB_FILEPATH
        sqloquent.DeletedModel.connection_info = DB_FILEPATH
        models.Customer.connection_info = DB_FILEPATH
        models.Vendor.connection_info = DB_FILEPATH
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
            models.Account, models.AccountCategory, models.Entry,
            models.Transaction,
            models.Customer, models.Vendor,
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

        # test empty Transaction
        (models.Transaction()).details
        (models.Transaction()).auth_scripts
        assert not models.Transaction().validate()

        # setup account categories
        equity_acct_cat = models.AccountCategory.insert({
            'name': 'Equity',
            'ledger_type': models.LedgerType.CURRENT,
            'destination': 'Balance Sheet',
        })
        assert equity_acct_cat is not None
        assert models.AccountCategory.find(equity_acct_cat.id) is not None
        asset_acct_cat = models.AccountCategory.insert({
            'name': 'Asset',
            'ledger_type': models.LedgerType.CURRENT,
            'destination': 'Balance Sheet',
        })
        liability_acct_cat = models.AccountCategory.insert({
            'name': 'Liability',
            'ledger_type': models.LedgerType.CURRENT,
            'destination': 'Balance Sheet',
        })

        # setup identity, currency, ledger, and some accounts
        identity = models.Identity.insert({'name': 'Test Man'})
        currency = models.Currency.insert({
            'name': 'US Dollar',
            'prefix_symbol': '$',
            'fx_symbol': 'USD',
            'base': 10,
            'unit_divisions': 2,
        })
        ledger = models.Ledger.insert({
            'name': 'General Ledger',
            'identity_id': identity.id,
            'currency_id': currency.id,
            'type': models.LedgerType.CURRENT,
        })
        equity_acct = models.Account.insert({
            'name': 'General Equity',
            'type': models.AccountType.EQUITY,
            'ledger_id': ledger.id,
            'category_id': equity_acct_cat.id,
        })
        asset_acct = models.Account.insert({
            'name': 'General Asset',
            'type': models.AccountType.ASSET,
            'ledger_id': ledger.id,
            'category_id': asset_acct_cat.id,
        })
        liability_acct = models.Account.insert({
            'name': 'General Liability',
            'type': models.AccountType.LIABILITY,
            'ledger_id': ledger.id,
            'category_id': liability_acct_cat.id,
        })

        assert equity_acct.category.id == equity_acct_cat.id
        assert asset_acct.category.id == asset_acct_cat.id
        assert liability_acct.category.id == liability_acct_cat.id

        assert len(liability_acct_cat.accounts) == 1, liability_acct_cat.accounts

        # make sub account
        assert len(liability_acct.children) == 0
        liability_sub_acct = models.Account.insert({
            'name': 'Liability Sub Account',
            'type': models.AccountType.LIABILITY,
            'ledger_id': ledger.id,
            'parent_id': liability_acct.id,
            'category_id': liability_acct_cat.id,
        })
        assert liability_sub_acct.parent is not None, liability_sub_acct.parent
        assert liability_sub_acct.parent.id == liability_acct.id, liability_sub_acct.parent
        liability_acct.children().reload()
        assert len(liability_acct.children) == 1
        assert liability_acct.children[0].id == liability_sub_acct.id

        # test empty Entry
        (models.Entry()).details

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
        txn.save()
        # add timestamps to entries
        equity_entry.timestamp = txn.timestamp
        equity_entry.save()
        asset_entry.timestamp = txn.timestamp
        asset_entry.save()
        # reload txn from database and validate it
        txn: models.Transaction = models.Transaction.find(txn.id)
        assert txn.validate(reload=True)
        assert len(asset_entry.transactions) == 1
        assert asset_entry.transactions[0].id == txn.id, asset_entry.transactions
        # reload entries from database and ensure the timestamps were saved
        equity_entry: models.Entry = models.Entry.find(equity_entry.id)
        assert equity_entry.timestamp == txn.timestamp, equity_entry.timestamp
        asset_entry: models.Entry = models.Entry.find(asset_entry.id)
        assert asset_entry.timestamp == txn.timestamp, asset_entry.timestamp

        # check balances
        assert equity_acct.balance() == 10_000_00, equity_acct.balance()
        assert asset_acct.balance() == 10_000_00, asset_acct.balance()
        assert liability_acct.balance() == 0, liability_acct.balance()
        balances = ledger.balances(True)
        assert len(balances.keys()) == 4, balances
        assert balances[equity_acct.id][0] == 10_000_00, balances[equity_acct.id][0]
        assert balances[asset_acct.id][0] == 10_000_00, balances[asset_acct.id][0]
        assert balances[liability_acct.id][0] == 0, balances[liability_acct.id][0]
        assert balances[liability_sub_acct.id][0] == 0, balances[liability_sub_acct.id][0]

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
        balances = ledger.balances(True)
        assert len(balances.keys()) == 4, balances
        assert balances[equity_acct.id][0] == 10_000_00-9_99, balances[equity_acct.id][0]
        assert balances[asset_acct.id][0] == 10_000_00, balances[asset_acct.id][0]
        assert balances[liability_acct.id][0] == 0, balances[liability_acct.id][0]
        assert balances[liability_sub_acct.id][0] == 9_99, balances[liability_sub_acct.id][0]

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

        # test Entry.insert_many
        entries = models.Entry.insert_many([
            {
                'type': models.EntryType.CREDIT,
                'account_id': equity_acct.id,
                'amount': 10_000_00,
                'nonce': os.urandom(16),
            },
            {
                'type': models.EntryType.DEBIT,
                'account_id': asset_acct.id,
                'amount': 10_000_00,
                'nonce': os.urandom(16),
            },
        ])
        assert entries == 2, entries

        # test additional models
        customer = models.Customer({
            'name': 'John Doe',
            'code': 'JD',
            'description': 'test customer',
        })
        customer.details = {'foo': 'bar'}
        customer.save()
        assert customer.id is not None
        assert customer.details == {'foo': 'bar'}

        vendor = models.Vendor({
            'name': 'Acme Inc.',
            'code': 'ACME',
            'description': 'test vendor',
        })
        vendor.details = {'foo': 'bar'}
        vendor.save()
        assert vendor.id is not None
        assert vendor.details == {'foo': 'bar'}


if __name__ == '__main__':
    unittest.main()

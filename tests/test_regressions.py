from context import models, bookchain, asyncql, helpers
from genericpath import isfile
from sqlite3 import OperationalError
import os
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'bookchain/models'


class TestRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bookchain.set_connection_info(DB_FILEPATH)
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

    def test_AccountCategory_query_does_not_mutate_conditions(self):
        conditions = {
            'ledger_type': models.LedgerType.CURRENT,
            'account_type': models.AccountType.ASSET,
        }
        original = {**conditions}
        models.AccountCategory.query(conditions)
        assert conditions == original, (conditions, original)

    def test_async_AccountCategory_query_does_not_mutate_conditions(self):
        conditions = {
            'ledger_type': asyncql.LedgerType.CURRENT,
            'account_type': asyncql.AccountType.ASSET,
        }
        original = {**conditions}
        asyncql.AccountCategory.query(conditions)
        assert conditions == original, (conditions, original)

    def test_Account_query_does_not_mutate_conditions(self):
        conditions = {'type': models.AccountType.ASSET}
        original = {**conditions}
        models.Account.query(conditions)
        assert conditions == original, (conditions, original)

    def test_async_Account_query_does_not_mutate_conditions(self):
        conditions = {'type': asyncql.AccountType.ASSET}
        original = {**conditions}
        asyncql.Account.query(conditions)
        assert conditions == original, (conditions, original)


if __name__ == '__main__':
    unittest.main()

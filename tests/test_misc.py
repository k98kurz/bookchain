from context import models
from genericpath import isfile
from sqlite3 import OperationalError
from time import time
import os
import sqloquent.tools
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'scriptcounting/models'


class TestMisc(unittest.TestCase):
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

    def test_currency(self):
        currency = models.Currency({
            'name': 'US Dollar',
            'prefix_symbol': '$',
            'fx_symbol': 'USD',
            'base': 10,
            'decimals': 2,
        })

        assert currency.format(123) == '$1.23', currency.format(123)
        assert currency.get_units_and_change(123) == (1, 23)

        currency = models.Currency({
            'name': 'Mean Minute/Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MMH',
            'base': 60,
            'decimals': 2,
        })

        assert currency.format(60*60*1.23) == 'Ħ1.23', currency.format(60*60*1.23)
        assert currency.get_units_and_change(60*60*2 + 123) == (2, 123)


if __name__ == '__main__':
    unittest.main()

from context import models, bookchain, asyncql
from genericpath import isfile
from sqlite3 import OperationalError
from time import time
import os
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'bookchain/models'


class TestMisc(unittest.TestCase):
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

    def test_set_connection_info(self):
        bookchain.set_connection_info(DB_FILEPATH)
        for name in dir(models):
            model = getattr(models, name)
            if hasattr(model, 'connection_info'):
                assert model.connection_info == DB_FILEPATH, model
        bookchain.set_connection_info('foobar')
        for name in dir(models):
            model = getattr(models, name)
            if hasattr(model, 'connection_info'):
                assert model.connection_info == 'foobar', model

        asyncql.set_connection_info(DB_FILEPATH)
        for name in dir(asyncql):
            model = getattr(asyncql, name)
            if hasattr(model, 'connection_info'):
                assert model.connection_info == DB_FILEPATH, model
        asyncql.set_connection_info('foobar')
        for name in dir(asyncql):
            model = getattr(asyncql, name)
            if hasattr(model, 'connection_info'):
                assert model.connection_info == 'foobar', model

    def test_currency(self):
        currency = models.Currency({
            'name': 'US Dollar',
            'prefix_symbol': '$',
            'fx_symbol': 'USD',
            'base': 100,
            'unit_divisions': 1,
        })

        assert currency.format(123) == '$1.23', currency.format(123)
        assert currency.get_units(123) == (1, 23)

        currency = models.Currency({
            'name': 'Mean Minute/Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MMH',
            'base': 60,
            'unit_divisions': 2,
        })

        assert currency.format(60*60*1.23) == 'Ħ1.23', currency.format(60*60*1.23)
        assert currency.get_units((60**2)*2 + (60**1)*2 + (60**0)*3) == (2, 2, 3)
        assert currency.format(60*60 + 45, decimal_places=2) == 'Ħ1.01', \
            currency.format(60*60 + 45, decimal_places=2)

    def test_publish_migrations(self):
        assert len(os.listdir(MIGRATIONS_PATH)) < 2, os.listdir(MIGRATIONS_PATH)
        bookchain.publish_migrations(MIGRATIONS_PATH)
        assert len(os.listdir(MIGRATIONS_PATH)) > 2, os.listdir(MIGRATIONS_PATH)

    def test_automigrate(self):
        bookchain.set_connection_info(DB_FILEPATH)
        bookchain.publish_migrations(MIGRATIONS_PATH)
        with self.assertRaises(OperationalError):
            models.Account.query().count()
        bookchain.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        assert models.Account.query().count() == 0


if __name__ == '__main__':
    unittest.main()

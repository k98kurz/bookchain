from context import models, bookchain, asyncql, helpers
from decimal import Decimal
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

        amount = Decimal('1.23')
        assert currency.format(123) == '$1.23', currency.format(123)
        assert currency.get_units(123) == (1, 23), currency.get_units(123)
        assert currency.to_decimal(123) == amount, currency.to_decimal(123)
        assert currency.from_decimal(amount) == 123, currency.from_decimal(amount)

        currency = models.Currency({
            'name': 'Mean Minute/Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MMH',
            'base': 60,
            'unit_divisions': 2,
        })

        assert currency.format(60*60*1.23) == 'Ħ1.23', currency.format(60*60*1.23)
        assert currency.format(60*60 + 45, decimal_places=2) == 'Ħ1.01', \
            currency.format(60*60 + 45, decimal_places=2)
        assert currency.to_decimal(5011) == Decimal(5011)/Decimal(60*60)

        amount = (60**2)*2 + (60**1)*2 + (60**0)*3
        assert currency.get_units(amount) == (2, 2, 3)
        assert currency.format(amount, use_decimal=False, divider=':') == 'Ħ02:02:03', \
            currency.format(amount, use_decimal=False, divider=':')
        assert currency.format(amount, use_decimal=False, divider='.') == 'Ħ02.02.03', \
            currency.format(amount, use_decimal=False, divider='.')

        amount = Decimal('1.51')
        assert currency.from_decimal(amount) == 5436, currency.from_decimal(amount)

    def test_asyncql_currency(self):
        currency = asyncql.Currency({
            'name': 'US Dollar',
            'prefix_symbol': '$',
            'fx_symbol': 'USD',
            'base': 100,
            'unit_divisions': 1,
        })

        amount = Decimal('1.23')
        assert currency.format(123) == '$1.23', currency.format(123)
        assert currency.get_units(123) == (1, 23), currency.get_units(123)
        assert currency.to_decimal(123) == amount, currency.to_decimal(123)
        assert currency.from_decimal(amount) == 123, currency.from_decimal(amount)

        currency = asyncql.Currency({
            'name': 'Mean Minute/Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MMH',
            'base': 60,
            'unit_divisions': 2,
        })

        assert currency.format(60*60*1.23) == 'Ħ1.23', currency.format(60*60*1.23)
        assert currency.format(60*60 + 45, decimal_places=2) == 'Ħ1.01', \
            currency.format(60*60 + 45, decimal_places=2)
        assert currency.to_decimal(5011) == Decimal(5011)/Decimal(60*60)

        amount = (60**2)*2 + (60**1)*2 + (60**0)*3
        assert currency.get_units(amount) == (2, 2, 3)
        assert currency.format(amount, use_decimal=False, divider=':') == 'Ħ02:02:03', \
            currency.format(amount, use_decimal=False, divider=':')
        assert currency.format(amount, use_decimal=False, divider='.') == 'Ħ02.02.03', \
            currency.format(amount, use_decimal=False, divider='.')

        amount = Decimal('1.51')
        assert currency.from_decimal(amount) == 5436, currency.from_decimal(amount)

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

    def test_parse_timestamp(self):
        assert helpers.parse_timestamp('') == 0
        assert type(helpers.parse_timestamp('1234567890')) is int
        assert type(helpers.parse_timestamp('1234567890.123')) is int
        assert type(helpers.parse_timestamp('2023-01-01T00:00:00Z')) is int
        assert type(helpers.parse_timestamp('2023-01-01T00:00:00+00:00')) is int
        assert type(helpers.parse_timestamp('2023-01-01T00:00:00-00:00')) is int
        assert type(helpers.parse_timestamp('2023-01-01T00:00:00+00:00')) is int
        assert helpers.parse_timestamp('not a timestamp') is None


if __name__ == '__main__':
    unittest.main()

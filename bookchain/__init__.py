from .models import (
    Account,
    AccountCategory,
    AccountType,
    ArchivedEntry,
    ArchivedTransaction,
    Correspondence,
    Currency,
    Customer,
    Entry,
    EntryType,
    Identity,
    Ledger,
    LedgerType,
    Transaction,
    TxRollup,
    Vendor,
)
from sqloquent import DeletedModel, Attachment
from typing import Callable
import sqloquent.tools


__version__ = '0.3.1'

def version() -> str:
    """Returns the version of the bookchain package."""
    return __version__


def set_connection_info(db_file_path: str):
    """Set the connection info for all models to use the specified
        sqlite3 database file path.
    """
    Account.connection_info = db_file_path
    AccountCategory.connection_info = db_file_path
    Correspondence.connection_info = db_file_path
    Currency.connection_info = db_file_path
    Customer.connection_info = db_file_path
    Entry.connection_info = db_file_path
    Identity.connection_info = db_file_path
    Ledger.connection_info = db_file_path
    Transaction.connection_info = db_file_path
    TxRollup.connection_info = db_file_path
    ArchivedTransaction.connection_info = db_file_path
    ArchivedEntry.connection_info = db_file_path
    Vendor.connection_info = db_file_path
    DeletedModel.connection_info = db_file_path
    Attachment.connection_info = db_file_path


def get_migrations() -> dict[str, str]:
    """Returns a dict mapping model names to migration file content strs."""
    models = [
        Account,
        AccountCategory,
        ArchivedEntry,
        ArchivedTransaction,
        Correspondence,
        Currency,
        Customer,
        Entry,
        Identity,
        Ledger,
        Transaction,
        TxRollup,
        Vendor,
    ]
    migrations = {}
    for model in models:
        migrations[model.__name__] = sqloquent.tools.make_migration_from_model(model)
    return migrations

def publish_migrations(
        migration_folder_path: str,
        migration_callback: Callable[[str, str], str] = None
    ):
    """Writes migration files for the models. If a migration callback is
        provided, it will be used to modify the migration file contents.
        The migration callback will be called with the model name and
        the migration file contents, and whatever it returns will be
        used as the migration file contents.
    """
    sqloquent.tools.publish_migrations(migration_folder_path)
    migrations = get_migrations()
    for name, m in migrations.items():
        m2 = migration_callback(name, m) if migration_callback else m
        m = m2 if type(m2) is str and len(m2) > 0 else m
        with open(f'{migration_folder_path}/create_{name}.py', 'w') as f:
            f.write(m)

def automigrate(migration_folder_path: str, db_file_path: str):
    """Executes the sqloquent automigrate tool."""
    sqloquent.tools.automigrate(migration_folder_path, db_file_path)

del Callable

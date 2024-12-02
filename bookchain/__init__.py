from .models import (
    Account,
    AccountCategory,
    AccountType,
    Correspondence,
    Currency,
    Customer,
    Entry,
    EntryType,
    Identity,
    Ledger,
    Transaction,
    Vendor,
)
from sqloquent import DeletedModel, Attachment
import sqloquent.tools

__version__ = '0.1.2'

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
    Vendor.connection_info = db_file_path
    DeletedModel.connection_info = db_file_path
    Attachment.connection_info = db_file_path

def publish_migrations(migration_folder_path: str):
    """Writes migration files for the models."""
    sqloquent.tools.publish_migrations(migration_folder_path)
    models = [
        Account,
        AccountCategory,
        Correspondence,
        Currency,
        Customer,
        Entry,
        Identity,
        Ledger,
        Transaction,
        Vendor,
        DeletedModel,
        Attachment,
    ]
    for model in models:
        name = model.__name__
        m = sqloquent.tools.make_migration_from_model(model)
        with open(f'{migration_folder_path}/create_{name}.py', 'w') as f:
            f.write(m)

def automigrate(migration_folder_path: str, db_file_path: str):
    """Executes the sqloquent automigrate tool."""
    sqloquent.tools.automigrate(migration_folder_path, db_file_path)

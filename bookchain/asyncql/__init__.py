from .Account import Account, AccountType
from .AccountCategory import AccountCategory
from .ArchivedEntry import ArchivedEntry
from .ArchivedTransaction import ArchivedTransaction
from .Correspondence import Correspondence
from .Currency import Currency
from .Customer import Customer
from .Entry import Entry, EntryType
from .Identity import Identity
from .Ledger import Ledger, LedgerType
from .Transaction import Transaction
from .TxRollup import TxRollup
from .Vendor import Vendor
from sqloquent.asyncql import (
    AsyncDeletedModel, AsyncAttachment,
    async_contains, async_within, async_has_many, async_belongs_to,
)


Identity.ledgers = async_has_many(Identity, Ledger, 'identity_id')
Ledger.owner = async_belongs_to(Ledger, Identity, 'identity_id')

Ledger.currency = async_belongs_to(Ledger, Currency, 'currency_id')

Correspondence.ledgers = async_contains(Correspondence, Ledger, 'ledger_ids')

Identity.correspondences = async_within(Identity, Correspondence, 'identity_ids')
Correspondence.identities = async_contains(Correspondence, Identity, 'identity_ids')

Ledger.accounts = async_has_many(Ledger, Account, 'ledger_id')
Account.ledger = async_belongs_to(Account, Ledger, 'ledger_id')

Account.children = async_has_many(Account, Account, 'parent_id')
Account.parent = async_belongs_to(Account, Account, 'parent_id')

Account.category = async_belongs_to(Account, AccountCategory, 'category_id')
AccountCategory.accounts = async_has_many(AccountCategory, Account, 'category_id')

Account.entries = async_has_many(Account, Entry, 'account_id')
Entry.account = async_belongs_to(Entry, Account, 'account_id')

Entry.transactions = async_within(Entry, Transaction, 'entry_ids')
Transaction.entries = async_contains(Transaction, Entry, 'entry_ids')

Transaction.ledgers = async_contains(Transaction, Ledger, 'ledger_ids')
Ledger.transactions = async_within(Ledger, Transaction, 'ledger_ids')

TxRollup.transactions = async_contains(TxRollup, Transaction, 'tx_ids')
Transaction.rollups = async_within(Transaction, TxRollup, 'tx_ids')

TxRollup.ledger = async_belongs_to(TxRollup, Ledger, 'ledger_id')
Ledger.rollups = async_within(Ledger, TxRollup, 'ledger_id')

TxRollup.parent = async_belongs_to(TxRollup, TxRollup, 'parent_id')
TxRollup.children = async_has_many(TxRollup, TxRollup, 'parent_id')

TxRollup.correspondence = async_belongs_to(TxRollup, Correspondence, 'correspondence_id')
Correspondence.rollups = async_within(Correspondence, TxRollup, 'correspondence_id')

ArchivedEntry.transactions = async_within(ArchivedEntry, ArchivedTransaction, 'entry_ids')
ArchivedTransaction.entries = async_contains(ArchivedTransaction, ArchivedEntry, 'entry_ids')

ArchivedEntry.account = async_belongs_to(ArchivedEntry, Account, 'account_id')
ArchivedTransaction.ledgers = async_contains(ArchivedTransaction, Ledger, 'ledger_ids')


def set_connection_info(db_file_path: str):
    """Set the connection info for all models to use the specified
        sqlite3 database file path.
    """
    Account.connection_info = db_file_path
    AccountCategory.connection_info = db_file_path
    ArchivedEntry.connection_info = db_file_path
    ArchivedTransaction.connection_info = db_file_path
    Correspondence.connection_info = db_file_path
    Currency.connection_info = db_file_path
    Customer.connection_info = db_file_path
    Entry.connection_info = db_file_path
    Identity.connection_info = db_file_path
    Ledger.connection_info = db_file_path
    Transaction.connection_info = db_file_path
    TxRollup.connection_info = db_file_path
    Vendor.connection_info = db_file_path
    AsyncDeletedModel.connection_info = db_file_path
    AsyncAttachment.connection_info = db_file_path


# no longer needed
del async_contains
del async_belongs_to
del async_within
del async_has_many

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
from sqloquent import contains, within, has_many, belongs_to, has_one


Identity.ledgers = has_many(Identity, Ledger, 'identity_id')
Ledger.owner = belongs_to(Ledger, Identity, 'identity_id')

Ledger.currency = belongs_to(Ledger, Currency, 'currency_id')

Correspondence.ledgers = contains(Correspondence, Ledger, 'ledger_ids')

Identity.correspondences = within(Identity, Correspondence, 'identity_ids')
Correspondence.identities = contains(Correspondence, Identity, 'identity_ids')

Ledger.accounts = has_many(Ledger, Account, 'ledger_id')
Account.ledger = belongs_to(Account, Ledger, 'ledger_id')

Account.children = has_many(Account, Account, 'parent_id')
Account.parent = belongs_to(Account, Account, 'parent_id')

Account.category = belongs_to(Account, AccountCategory, 'category_id')
AccountCategory.accounts = has_many(AccountCategory, Account, 'category_id')

Account.entries = has_many(Account, Entry, 'account_id')
Entry.account = belongs_to(Entry, Account, 'account_id')

Entry.transactions = within(Entry, Transaction, 'entry_ids')
Transaction.entries = contains(Transaction, Entry, 'entry_ids')

Transaction.ledgers = contains(Transaction, Ledger, 'ledger_ids')
Ledger.transactions = within(Ledger, Transaction, 'ledger_ids')

TxRollup.transactions = contains(TxRollup, Transaction, 'tx_ids')
Transaction.rollups = within(Transaction, TxRollup, 'tx_ids')

TxRollup.ledger = belongs_to(TxRollup, Ledger, 'ledger_id')
Ledger.rollups = within(Ledger, TxRollup, 'ledger_id')

TxRollup.parent = belongs_to(TxRollup, TxRollup, 'parent_id')
TxRollup.child = has_one(TxRollup, TxRollup, 'parent_id')

TxRollup.correspondence = belongs_to(TxRollup, Correspondence, 'correspondence_id')
Correspondence.rollups = within(Correspondence, TxRollup, 'correspondence_id')

ArchivedEntry.transactions = within(ArchivedEntry, ArchivedTransaction, 'entry_ids')
ArchivedTransaction.entries = contains(ArchivedTransaction, ArchivedEntry, 'entry_ids')

ArchivedEntry.account = belongs_to(ArchivedEntry, Account, 'account_id')
Account.archived_entries = has_many(Account, ArchivedEntry, 'account_id')

ArchivedTransaction.ledgers = contains(ArchivedTransaction, Ledger, 'ledger_ids')
Ledger.archived_transactions = within(Ledger, ArchivedTransaction, 'ledger_ids')
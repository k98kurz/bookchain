from .Account import Account
from .AccountCategory import AccountCategory
from .AccountType import AccountType
from .Correspondence import Correspondence
from .Currency import Currency
from .Customer import Customer
from .Entry import Entry
from .EntryType import EntryType
from .Identity import Identity
from .Ledger import Ledger
from .LedgerType import LedgerType
from .Transaction import Transaction
from .Vendor import Vendor
from sqloquent import contains, within, has_many, belongs_to


__version__ = '0.2.0'


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

from .Account import Account, AccountType
from .Correspondence import Correspondence
from .Currency import Currency
from .Entry import Entry, EntryType
from .Identity import Identity
from .Ledger import Ledger
from .Transaction import Transaction
from sqloquent import contains, within, has_many, belongs_to


Identity.ledgers = has_many(Identity, Ledger, 'identity_id')
Ledger.owner = belongs_to(Ledger, Identity, 'identity_id')

Ledger.currency = belongs_to(Ledger, Currency, 'currency_id')

Correspondence.ledgers = contains(Correspondence, Ledger, 'ledger_ids')

Identity.correspondences = within(Identity, Correspondence, 'identity_ids')
Correspondence.identities = contains(Correspondence, Identity, 'identity_ids')

Ledger.accounts = has_many(Ledger, Account, 'ledger_id')
Account.ledger = belongs_to(Account, Ledger, 'ledger_id')

Account.entries = has_many(Account, Entry, 'account_id')
Entry.account = belongs_to(Entry, Account, 'account_id')

Entry.transactions = within(Entry, Transaction, 'entry_ids')
Transaction.entries = contains(Transaction, Entry, 'entry_ids')

Transaction.ledgers = contains(Transaction, Ledger, 'ledger_ids')
Ledger.transactions = within(Ledger, Transaction, 'ledger_ids')

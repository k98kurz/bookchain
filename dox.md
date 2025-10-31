# bookchain

## Classes

### `Account(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- type: str
- ledger_id: str
- parent_id: str
- code: str | None
- correspondence_id: str | None
- locking_scripts: bytes | None
- category_id: str | None
- active: bool | Default[True]
- description: str | None
- ledger: RelatedModel
- parent: RelatedModel
- correspondence: RelatedModel
- category: RelatedModel
- children: RelatedCollection
- entries: RelatedCollection
- archived_entries: RelatedCollection

#### Properties

- type: The AccountType of the Account.
- locking_scripts: The dict mapping EntryType to tapescript locking script
bytes.
- details: A packify.SerializableType stored in the database as a blob.
- correspondence: The related Correspondence. Setting raises TypeError if the
precondition check fails.
- ledger: The related Ledger. Setting raises TypeError if the precondition check
fails.
- children: The related Accounts. Setting raises TypeError if the precondition
check fails.
- parent: The related Account. Setting raises TypeError if the precondition
check fails.
- category: The related AccountCategory. Setting raises TypeError if the
precondition check fails.
- entries: The related Entrys. Setting raises TypeError if the precondition
check fails.
- archived_entries: The related ArchivedEntrys. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `@classmethod insert(data: dict) -> Account | None:`

Ensure data is encoded before inserting.

##### `@classmethod insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Ensure items are encoded before inserting.

##### `update(updates: dict, /, *, suppress_events: bool = False) -> Account:`

Ensure updates are encoded before updating.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:`

Ensure conditions are encoded before querying.

##### `balance(include_sub_accounts: bool = True, rolled_up_balances: dict[str, tuple[EntryType, int]] = {}) -> int:`

Tally all entries for this account. Includes the balances of all sub-accounts if
include_sub_accounts is True. To get an accurate balance, pass in the balances
from the most recent TxRollup.

##### `validate_script(entry_type: EntryType, auth_script: bytes | Script, tapescript_runtime: dict = {}) -> bool:`

Checks if the auth_script validates against the correct locking_script for the
EntryType. Returns True if it does and False if it does not (or if it errors).

### `AccountCategory(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- ledger_type: str | None
- destination: str
- accounts: RelatedCollection

#### Properties

- ledger_type: The LedgerType that this AccountCategory applies to, if any.
- accounts: The related Accounts. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> AccountCategory | None:`

Ensure data is encoded before inserting.

##### `@classmethod insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Ensure items are encoded before inserting.

##### `update(updates: dict, /, *, suppress_events: bool = False) -> AccountCategory:`

Ensure updates are encoded before updating.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:`

Ensure conditions are encoded before querying.

### `AccountType(Enum)`

Enum of valid Account types.

### `ArchivedEntry(HashedModel)`

Optional class for storing the trimmed Entries connected to an
ArchivedTransaction. Must be used in conjunction with ArchivedTransaction.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- type: str
- amount: int
- nonce: bytes
- account_id: str
- description: str | None
- account: RelatedModel
- transactions: RelatedCollection

#### Properties

- type: The EntryType of the ArchivedEntry.
- details: A packify.SerializableType stored in the database as a blob.
- transactions: The related ArchivedTransactions. Setting raises TypeError if
the precondition check fails.
- account: The related Account. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `__hash__() -> int:`

##### `@classmethod generate_id(data: dict) -> str:`

Generate an id by hashing the non-id contents. Raises TypeError for unencodable
type (calls packify.pack).

##### `@classmethod insert(data: dict) -> ArchivedEntry | None:`

Ensure data is encoded before inserting.

##### `@classmethod insert_many(items: list[dict]) -> int:`

Ensure data is encoded before inserting.

##### `@classmethod query(conditions: dict = None) -> QueryBuilderProtocol:`

Ensure conditions are encoded properly before querying.

##### `@classmethod set_sigfield_plugin(plugin: Callable):`

Sets the plugin function used by self.get_sigfields that parses the
ArchivedEntry to extract the correct sigfields for tapescript authorization.
This is an optional override.

##### `get_sigfields() -> dict[str, bytes]:`

Get the sigfields for tapescript authorization. By default, it returns
{sigfield1: self.generate_id()} because the ID cryptographically commits to all
record data. If entries are provided in the kwargs, the returned dict will
include sigfield2 set to the concatenation of the sorted entry ids. Unless
sigfield2 can be excluded from auth script validation (e.g. `sigflags='02'`),
entries should be provided in the kwargs (i.e. `get_sigfields(entries=[entry1, ...])`).
If the set_sigfield_plugin method was previously called, this will instead
return the result of calling the plugin function.

### `ArchivedTransaction(HashedModel)`

Optional class for storing a trimmed Transaction after is has included in a
TxRollup. This allows accessing the trimmed Transaction details more efficiently
than by loading the DeletedModel that contains the trimmed Transaction. Must be
used in conjunction with ArchivedEntry.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- entry_ids: str
- ledger_ids: str
- timestamp: str
- auth_scripts: bytes
- description: str | None
- entries: RelatedCollection
- ledgers: RelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- auth_scripts: A dict mapping account IDs to tapescript unlocking script bytes.
- entries: The related ArchivedEntrys. Setting raises TypeError if the
precondition check fails.
- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `validate(tapescript_runtime: dict = {}, reload: bool = False) -> bool:`

Determines if a Transaction is valid using the rules of accounting and checking
all auth scripts against their locking scripts. The tapescript_runtime can be
scoped to each entry ID. Raises TypeError for invalid arguments. Raises
ValueError if the entries do not balance for each ledger; if a required auth
script is missing; or if any of the entries is contained within an existing
Transaction. If reload is set to True, entries and accounts will be reloaded
from the database.

##### `save(tapescript_runtime: dict = {}, reload: bool = False) -> ArchivedTransaction:`

Validate the transaction, save the entries, then save the transaction.

### `Correspondence(HashedModel)`

A Correspondence is a typically bilateral credit arrangement in which two
Identities transact with each other using Nostro and Vostro accounts on their
Ledgers, where the Nostro asset account on one Identity's Ledger corresponds to
the Vostro liability account on the other Identity's Ledger. A transfer takes
the form of a Transaction with four Entries: one debiting (deducting from) the
Equity account of the payer; one crediting the Nostro or Vostro account on the
payer's Ledger; one debiting the Nostro or Vostro account on the payee's Ledger;
and one crediting the Equity account of the payee.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- identity_ids: str
- ledger_ids: str
- signatures: bytes | None
- description: str | None
- identities: RelatedCollection
- ledgers: RelatedCollection
- rollups: RelatedCollection
- accounts: RelatedCollection

#### Properties

- details: Returns the details of the correspondence as a dict.
- signatures: Returns the signatures of the correspondences as a dict mapping
Identity ID to bytes signature.
- txru_lock: Returns the txru_lock directly from the details field.
- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.
- accounts: The related Accounts. Setting raises TypeError if the precondition
check fails.
- identities: The related Identitys. Setting raises TypeError if the
precondition check fails.
- rollups: The related TxRollups. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `get_accounts(reload: bool = True) -> dict[str, dict[AccountType, Account]]:`

Loads the relevant nostro and vostro Accounts for the Identities that are part
of the Correspondence, as well as the equity Accounts for each Identity,
returning a dict of the form { identity.id: { AccountType: Account }}.

##### `setup_accounts(locking_scripts: dict[str, bytes]) -> dict[str, dict[AccountType, Account]]:`

Takes a dict mapping Identity ID to tapescript locking scripts. Returns a dict
of Accounts necessary for setting up the credit Correspondence of form {
identity.id: { AccountType: Account }}.

##### `pay_correspondent(payer: Identity, payee: Identity, amount: int, txn_nonce: bytes) -> tuple[list[Entry], list[Entry]]:`

Prepares two lists of entries in which the payer remits to the payee the given
amount: one in which the nostro account on the payer's ledger is credited and
one in which the vostro account on the payer's ledger is credited.

##### `balances(rolled_up_balances: dict[str, tuple[EntryType, int]] = {}) -> dict[str, int]:`

Returns the balances of the correspondents as a dict mapping str Identity ID to
signed int (equal to Nostro - Vostro).

### `Currency(HashedModel)`

#### Annotations

- table: <class 'str'>
- id_column: <class 'str'>
- columns: tuple[str]
- id: <class 'str'>
- name: <class 'str'>
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: <class 'str'>
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: str | None
- prefix_symbol: str | None
- postfix_symbol: str | None
- fx_symbol: str | None
- unit_divisions: <class 'int'>
- base: int | None
- description: str | None
- ledgers: <class 'sqloquent.interfaces.RelatedCollection'>

#### Properties

- details: A string stored in the database as text. Note that this will be
changed to a packify.SerializableType stored as a blob in 0.4.0.
- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `to_decimal(amount: int) -> Decimal:`

Convert the amount into a Decimal representation.

##### `from_decimal(amount: Decimal) -> int:`

Convert the amount from a Decimal representation.

##### `get_units(amount: int) -> tuple[int]:`

Get the full units and subunits. The number of subunit figures will be equal to
unit_divisions; e.g. if base=10 and unit_divisions=2, get_units(200) will return
(2, 0, 0); if base=60 and unit_divisions=2, get_units(200) will return (0, 3,
20).

##### `format(amount: int, /, *, divider: str = '.', use_fx_symbol: bool = False, use_postfix: bool = False, use_prefix: bool = True, decimal_places: int = 2, use_decimal: bool = True) -> str:`

Format an amount using the correct number of `decimal_places`. If `use_decimal`
is `False`, instead the unit subdivisions from `get_units` will be combined
using the `divider` char, and each part will be prefix padded with 0s to reach
the `decimal_places`. E.g. `.format(200, use_decimal=False, divider=':') ==
'02:00'` for a Currency with `base=100` and `unit_divisions=1`.

### `Customer(HashedModel)`

#### Annotations

- table: <class 'str'>
- id_column: <class 'str'>
- columns: tuple[str]
- id: <class 'str'>
- name: <class 'str'>
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: <class 'str'>
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- code: str | None
- description: str | None

#### Properties

- details: A packify.SerializableType stored in the database as a blob.

### `DeletedModel(SqlModel)`

Model for preserving and restoring deleted HashedModel records.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- model_class: str
- record_id: str
- record: bytes
- timestamp: str

#### Methods

##### `__init__(data: dict = {}) -> None:`

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> SqlModel | None:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict. Automatically sets a timestamp if one is not supplied.

##### `restore(inject: dict = {}, /, *, suppress_events: bool = False) -> SqlModel:`

Restore a deleted record, remove from deleted_records, and return the restored
model. Raises ValueError if model_class cannot be found. Raises TypeError if
model_class is not a subclass of SqlModel. Uses packify.unpack to unpack the
record. Raises TypeError if packed record is not a dict.

### `Entry(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- type: str
- amount: int
- nonce: bytes
- account_id: str
- description: str | None
- timestamp: str | None
- account: RelatedModel
- transactions: RelatedCollection

#### Properties

- type: The EntryType of the Entry.
- details: A packify.SerializableType stored in the database as a blob.
- account: The related Account. Setting raises TypeError if the precondition
check fails.
- transactions: The related Transactions. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `__hash__() -> int:`

##### `@classmethod generate_id(data: dict) -> str:`

Generate an id by hashing the non-id contents. Raises TypeError for unencodable
type (calls packify.pack).

##### `@classmethod insert(data: dict) -> Entry | None:`

Ensure data is encoded before inserting.

##### `@classmethod insert_many(items: list[dict]) -> int:`

Ensure data is encoded before inserting.

##### `@classmethod query(conditions: dict = None) -> QueryBuilderProtocol:`

Ensure conditions are encoded properly before querying.

##### `@classmethod set_sigfield_plugin(plugin: Callable):`

Sets the plugin function used by self.get_sigfields that parses the Entry to
extract the correct sigfields for tapescript authorization. This is an optional
override.

##### `get_sigfields() -> dict[str, bytes]:`

Get the sigfields for tapescript authorization. By default, it returns
{sigfield1: self.generate_id()} because the ID cryptographically commits to all
record data. If entries are provided in the kwargs, the returned dict will
include sigfield2 set to the concatenation of the sorted entry ids. Unless
sigfield2 can be excluded from auth script validation (e.g. `sigflags='02'`),
entries should be provided in the kwargs (i.e. `get_sigfields(entries=[entry1, ...])`).
If the set_sigfield_plugin method was previously called, this will instead
return the result of calling the plugin function.

##### `archive() -> ArchivedEntry | None:`

Archive the Entry. If it has already been archived, return the existing
ArchivedEntry.

### `EntryType(Enum)`

Enum of valid Entry types (CREDIT and DEBIT).

### `Identity(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- pubkey: bytes | None
- seed: bytes | None
- secret_details: bytes | None
- description: str | None
- ledgers: RelatedCollection
- correspondences: RelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.
- correspondences: The related Correspondences. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `public() -> dict:`

Return the public data for cloning the Identity.

##### `correspondents(reload: bool = False) -> list[Identity]:`

Get the correspondents for this Identity.

##### `get_correspondent_accounts(correspondent: Identity, reload: bool = False) -> list[Account]:`

Get the nosto and vostro accounts for a correspondent.

### `Ledger(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- type: str
- identity_id: str
- currency_id: str
- description: str | None
- owner: RelatedModel
- currency: RelatedModel
- accounts: RelatedCollection
- transactions: RelatedCollection
- archived_transactions: RelatedCollection
- rollups: RelatedCollection

#### Properties

- type: The LedgerType of the Ledger.
- owner: The related Identity. Setting raises TypeError if the precondition
check fails.
- currency: The related Currency. Setting raises TypeError if the precondition
check fails.
- accounts: The related Accounts. Setting raises TypeError if the precondition
check fails.
- transactions: The related Transactions. Setting raises TypeError if the
precondition check fails.
- rollups: The related TxRollups. Setting raises TypeError if the precondition
check fails.
- archived_transactions: The related ArchivedTransactions. Setting raises
TypeError if the precondition check fails.

#### Methods

##### `@classmethod insert(data: dict) -> Ledger | None:`

Ensure data is encoded before inserting.

##### `@classmethod insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Ensure items are encoded before inserting.

##### `update(updates: dict, /, *, suppress_events: bool = False) -> Ledger:`

Ensure updates are encoded before updating.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:`

Ensure conditions are encoded before querying.

##### `balances(reload: bool = False) -> dict[str, tuple[int, AccountType]]:`

Return a dict mapping account ids to their balances. Accounts with sub-accounts
will not include the sub-account balances; the sub-account balances will be
returned separately.

##### `setup_basic_accounts() -> list[Account]:`

Creates and returns a list of 3 unsaved Accounts covering the 3 basic
categories: Asset, Liability, Equity.

### `LedgerType(Enum)`

Enum of valid ledger types: CURRENT and FUTURE for cash and accrual accounting,
respectively.

### `Transaction(HashedModel)`

A Transaction is a collection of connected Entries that are recorded on the
Ledgers of the Identities that are party to the Transaction. Any Entry for an
Account that has a locking_script will require a valid tapscript unlocking
script to be recorded in the auth_scripts dict of the Transaction.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- entry_ids: str
- ledger_ids: str
- timestamp: str
- auth_scripts: bytes
- description: str | None
- entries: RelatedCollection
- ledgers: RelatedCollection
- rollups: RelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- auth_scripts: A dict mapping account IDs to tapescript unlocking script bytes.
- entries: The related Entrys. Setting raises TypeError if the precondition
check fails.
- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.
- rollups: The related TxRollups. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `@classmethod prepare(entries: list[Entry], timestamp: str, auth_scripts: dict = {}, details: packify.SerializableType = None, tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:`

Prepare a transaction. Raises TypeError for invalid arguments. Raises ValueError
if the entries do not balance for each ledger; if a required auth script is
missing; or if any of the entries is contained within an existing Transaction.
Entries and Transaction will have IDs generated but will not be persisted to the
database and must be saved separately. The auth_scripts dict must map account
IDs to tapescript bytecode bytes.

##### `validate(tapescript_runtime: dict = {}, reload: bool = False) -> bool:`

Determines if a Transaction is valid using the rules of accounting and checking
all auth scripts against their locking scripts. The tapescript_runtime can be
scoped to each entry ID. Raises TypeError for invalid arguments. Raises
ValueError if the entries do not balance for each ledger; if a required auth
script is missing; or if any of the entries is contained within an existing
Transaction. If reload is set to True, entries and accounts will be reloaded
from the database. Auth scripts can be provided by account ID or by entry ID;
scoping by entry ID will take precedence.

##### `save(tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:`

Validate the transaction, save the entries, then save the transaction.

##### `archive() -> ArchivedTransaction:`

Archive the Transaction. If it has already been archived, return the existing
ArchivedTransaction.

### `TxRollup(HashedModel)`

A Transaction Roll-up is a collection of Transactions that have been
consolidated: the IDs of the committed Transactions are the leaves of a Merkle
tree, and the aggregate effects of the Transactions are maintained in a dict
mapping account IDs to tuples of EntryType and int balances. A TxRollup created
for a Correspondence must have a valid auth_script that unlocks the txru_lock in
the Correspondence's details (or an n-of-n multisig lock made from the pubkeys
of the Correspondence's identities if no txru_lock was saved). The height of a
TxRollup is the number of TxRollups in its chain -- they form a blockchain of
TxRollups, hence the inclusion of a parent_id. Only one child TxRollup can be
added for a given parent TxRollup, and the balances of the child TxRollup are
the sum of the effects of the Transactions in the child TxRollup and the parent
TxRollup balances; i.e. the most recent TxRollup is the sum of all the
Transactions committed to in previous TxRollups in the chain. Inclusion of a
Transaction can only be proven using the Merkle tree of the TxRollup in which it
was committed and only if the full list of tx_ids is saved, but the proof can be
verified by mirrors that have only the tx_root.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- height: int
- parent_id: str | None
- tx_ids: str
- tx_root: str
- correspondence_id: str | None
- ledger_id: str | None
- balances: bytes
- timestamp: str
- auth_script: bytes | None
- description: str | None
- correspondence: RelatedModel
- ledger: RelatedModel
- transactions: RelatedCollection
- parent: RelatedModel
- child: RelatedModel

#### Properties

- tx_ids: A list of transaction IDs. Setting causes the ids to be sorted, then
combined into a Merkle Tree, the root of which is used to set `self.tx_root`.
- balances: A dict mapping account IDs to tuple[EntryType, int] balances.
- tree: A merkle tree of the transaction IDs.
- ledger: The related Ledger. Setting raises TypeError if the precondition check
fails.
- transactions: The related Transactions. Setting raises TypeError if the
precondition check fails.
- parent: The related TxRollup. Setting raises TypeError if the precondition
check fails.
- child: The related TxRollup. Setting raises TypeError if the precondition
check fails.
- correspondence: The related Correspondence. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `public() -> dict:`

Returns the public data for mirroring this TxRollup. Excludes the tx_ids.

##### `prove_txn_inclusion(txn_id: str | bytes) -> bytes:`

Proves that a transaction is included in the tx rollup.

##### `verify_txn_inclusion_proof(txn_id: str | bytes, proof: bytes) -> bool:`

Verifies that a transaction is included in the tx rollup.

##### `@classmethod calculate_balances(txns: list[Transaction], parent_balances: dict[str, tuple[EntryType, int]] | None = None, reload: bool = False) -> dict[str, tuple[EntryType, int]]:`

Calculates the account balances for a list of rolled-up transactions. If
parent_balances is provided, those are the starting balances to which the
balances of the rolled-up transactions are added. If reload is True, the entries
are reloaded from the database.

##### `@classmethod prepare(txns: list[Transaction], parent_id: str | None = None, correspondence: Correspondence | None = None, ledger: Ledger | None = None, reload: bool = False) -> TxRollup:`

Prepare a tx rollup by checking that all txns are for the accounts of the given
correspondence or belong to the same ledger if no correspondence is provided.
Raises TypeError if txns is not a list of Transaction objects. Raises ValueError
if any txns are not for accounts of the given correspondence or of the same
ledger if no correspondence is provided, or if the parent TxRollup already has a
child, or if there are no txns and no ledger or correspondence is provided, or
if a TxRollup chain already exists for the given ledger or correspondence when
no parent is provided. The Transaction IDs are sorted and combined into a Merkle
Tree, the root of which is used to set the `tx_root` property.

##### `validate(reload: bool = False) -> bool:`

Validates that a TxRollup has been authorized properly; that the balances are
correct; and that the height is 1 + the height of the parent tx rollup (if one
exists); and that there is no other chain for the relevant ledger or
correspondence when no parent is provided.

##### `trim(archive: bool = True) -> int:`

Trims the transactions and entries committed to in this tx rollup. Returns the
number of transactions trimmed. If archive is True, the transactions and entries
are archived before being deleted. Raises ValueError if the tx rollup is not
valid.

##### `trimmed_transactions() -> SqlQueryBuilder:`

Returns a query builder for DeletedModels containing the trimmed transactions
committed to in this tx rollup.

##### `trimmed_entries() -> SqlQueryBuilder:`

Returns a query builder for DeletedModels containing the trimmed entries from
trimmed transactions committed to in this tx rollup.

##### `archived_transactions() -> SqlQueryBuilder:`

Returns a query builder for ArchivedTransactions committed to in this tx rollup.

##### `archived_entries() -> SqlQueryBuilder:`

Returns a query builder for ArchivedEntries committed to in this tx rollup.

### `Vendor(HashedModel)`

#### Annotations

- table: <class 'str'>
- id_column: <class 'str'>
- columns: tuple[str]
- id: <class 'str'>
- name: <class 'str'>
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: <class 'str'>
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- code: str | None
- description: str | None

#### Properties

- details: A packify.SerializableType stored in the database as a blob.

## Functions

### `set_connection_info(db_file_path: str):`

Set the connection info for all models to use the specified sqlite3 database
file path.

### `get_migrations() -> dict[str, str]:`

Returns a dict mapping model names to migration file content strs.

### `publish_migrations(migration_folder_path: str, migration_callback: Callable = None):`

Writes migration files for the models. If a migration callback is provided, it
will be used to modify the migration file contents. The migration callback will
be called with the model name and the migration file contents, and whatever it
returns will be used as the migration file contents.

### `automigrate(migration_folder_path: str, db_file_path: str):`

Executes the sqloquent automigrate tool.

### `version() -> str:`

Returns the version of the bookchain package.

### `parse_timestamp(timestamp: str) -> int | None:`

Helper function to automatically parse a timestamp string into a Unix epoch
timestamp. Returns None if the timestamp is invalid. Supports: - Unix epoch as
integer string (e.g., "1234567890") - Unix epoch as float string (e.g.,
"1234567890.123") - ISO 8601 format strings (e.g., "2023-01-01T00:00:00Z") -
Other datetime formats parseable by datetime.fromisoformat() or
datetime.strptime()



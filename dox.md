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
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- type: str
- ledger_id: str
- parent_id: str
- code: str | None
- locking_scripts: bytes | None
- category: str | None
- ledger: RelatedModel
- parent: RelatedModel
- children: RelatedCollection
- entries: RelatedCollection

#### Properties

- type: The AccountType of the Account.
- locking_scripts: The dict mapping EntryType to tapescript locking script
bytes.
- details: A packify.SerializableType stored in the database as a blob.
- ledger: The related Ledger. Setting raises TypeError if the precondition check
fails.
- children: The related Accounts. Setting raises TypeError if the precondition
check fails.
- parent: The related Account. Setting raises TypeError if the precondition
check fails.
- entries: The related Entrys. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `@classmethod insert(data: dict) -> Account | None:`

Ensure data is encoded before inserting.

##### `balance(include_sub_accounts: bool = True) -> int:`

Tally all entries for this account. Includes the balances of all sub-accounts if
include_sub_accounts is True.

##### `validate_script(entry_type: EntryType, auth_script: bytes | Script, tapescript_runtime: dict = {}) -> bool:`

Checks if the auth_script validates against the correct locking_script for the
EntryType. Returns True if it does and False if it does not (or if it errors).

### `AccountType(Enum)`

Enum of valid Account types.

### `Correspondence(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- columns_excluded_from_hash: tuple[str]
- details: str
- identity_ids: str
- ledger_ids: str
- identities: RelatedCollection
- ledgers: RelatedCollection

#### Properties

- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.
- identities: The related Identitys. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `get_accounts() -> list[Account]:`

Loads the relevant nostro and vostro Accounts for the Identities that are part
of the Correspondence.

##### `setup_accounts(locking_scripts: dict[str, bytes]) -> dict[str, dict[AccountType, Account]]:`

Takes a dict mapping Identity ID to tapescript locking scripts. Returns a dict
of Accounts necessary for setting up the credit Correspondence of form {
identity.id: { AccountType: Account }}.

##### `pay_correspondent(payer: Identity, payee: Identity, amount: int, txn_nonce: bytes) -> tuple[list[Entry], list[Entry]]:`

Prepares two lists of entries in which the payer remits to the payee the given
amount: one in which the nostro account on the payer's ledger is credited and
one in which the vostro account on the payer's ledger is credited.

##### `balances() -> dict[str, int]:`

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
- columns_excluded_from_hash: tuple[str]
- details: str | None
- prefix_symbol: str | None
- postfix_symbol: str | None
- fx_symbol: str | None
- decimals: <class 'int'>
- base: int | None

#### Methods

##### `to_decimal(amount: int) -> Decimal:`

Convert the amount into a Decimal representation.

##### `get_units_and_change(amount: int) -> tuple[int, int]:`

Get the full units and subunits.

##### `format(amount: int, /, *, use_fx_symbol: bool = False, use_postfix: bool = False, use_prefix: bool = True, decimals: int = None) -> str:`

Format an amount using the correct number of decimals.

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
- columns_excluded_from_hash: tuple[str]
- details: str | None
- code: str | None

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
- columns_excluded_from_hash: tuple[str]
- details: bytes
- type: str
- amount: int
- nonce: bytes
- account_id: str
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
record data. If the set_sigfield_plugin method was previously called, this will
instead return the result of calling the plugin function.

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
- columns_excluded_from_hash: tuple[str]
- details: bytes
- pubkey: bytes | None
- seed: bytes | None
- secret_details: bytes | None
- ledgers: RelatedCollection
- correspondences: RelatedCollection

#### Properties

- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.
- correspondences: The related Correspondences. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `@classmethod generate_id(data: dict) -> str:`

Generate an ID that does not commit to the columns that should be excluded from
the cryptographic commitment.

##### `public() -> dict:`

Return the public data for cloning the Identity.

##### `correspondents(reload: bool = False) -> list[Identity]:`

Get the correspondents for this Identity.

##### `get_correspondent_accounts(correspondent: Identity) -> list[Account]:`

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
- columns_excluded_from_hash: tuple[str]
- details: bytes
- identity_id: str
- currency_id: str
- owner: RelatedModel
- currency: RelatedModel
- accounts: RelatedCollection
- transactions: RelatedCollection

#### Properties

- owner: The related Identity. Setting raises TypeError if the precondition
check fails.
- currency: The related Currency. Setting raises TypeError if the precondition
check fails.
- accounts: The related Accounts. Setting raises TypeError if the precondition
check fails.
- transactions: The related Transactions. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `balances(reload: bool = False) -> dict[str, tuple[int, AccountType]]:`

Return a dict mapping account ids to their balances. Accounts with sub-accounts
will not include the sub-account balances; the sub-account balances will be
returned separately.

##### `@classmethod find(id: str) -> Ledger:`

##### `@classmethod insert(data: dict) -> Ledger | None:`

##### `setup_basic_accounts() -> list[Account]:`

Creates and returns a list of 3 unsaved Accounts covering the 3 basic
categories: Asset, Liability, Equity.

### `Transaction(HashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- columns_excluded_from_hash: tuple[str]
- details: bytes
- entry_ids: str
- ledger_ids: str
- timestamp: str
- auth_scripts: bytes
- entries: RelatedCollection
- ledgers: RelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- auth_scripts: A dict mapping account IDs to tapescript unlocking script bytes.
- entries: The related Entrys. Setting raises TypeError if the precondition
check fails.
- ledgers: The related Ledgers. Setting raises TypeError if the precondition
check fails.

#### Methods

##### `@classmethod generate_id(data: dict) -> str:`

Generate a txn id by hashing the entry_ids, ledger_ids, details, and timestamp.
Raises TypeError for unencodable type (calls packify.pack).

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
from the database.

##### `save(tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:`

Validate the transaction, save the entries, then save the transaction.

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
- columns_excluded_from_hash: tuple[str]
- details: str | None
- code: str | None

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
- model_class: str
- record_id: str
- record: bytes
- timestamp: str

#### Methods

##### `__init__(data: dict = {}) -> None:`

##### `@classmethod insert(data: dict) -> SqlModel | None:`

##### `restore(inject: dict = {}) -> SqlModel:`

Restore a deleted record, remove from deleted_records, and return the restored
model. Raises ValueError if model_class cannot be found. Raises TypeError if
model_class is not a subclass of SqlModel. Uses packify.unpack to unpack the
record. Raises TypeError if packed record is not a dict.

### `Attachment(HashedModel)`

Class for attaching immutable details to a record.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- related_model: str
- related_id: str
- _related: SqlModel
- _details: packify.SerializableType

#### Methods

##### `related(reload: bool = False) -> SqlModel:`

Return the related record.

##### `attach_to(related: SqlModel) -> Attachment:`

Attach to related model then return self.

##### `get_details(reload: bool = False) -> packify.SerializableType:`

Decode packed bytes to dict.

##### `set_details(details: packify.SerializableType = {}) -> Attachment:`

Set the details column using either supplied data or by packifying
self._details. Return self in monad pattern. Raises packify.UsageError or
TypeError if details contains unseriazliable type.

##### `@classmethod insert(data: dict) -> Optional[Attachment]:`

Redefined for better LSP support.

## Functions

### `set_connection_info(db_file_path: str):`

Set the connection info for all models to use the specified sqlite3 database
file path.

### `publish_migrations(migration_folder_path: str):`

Writes migration files for the models.

### `automigrate(migration_folder_path: str, db_file_path: str):`

Executes the sqloquent automigrate tool.



# bookchain.asyncql

## Classes

### `AccountType(Enum)`

Enum of valid Account types.

### `EntryType(Enum)`

Enum of valid Entry types (CREDIT and DEBIT).

### `ArchivedEntry(AsyncHashedModel)`

Optional class for storing the trimmed Entries connected to an
ArchivedTransaction. Must be used in conjunction with ArchivedTransaction.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- account: AsyncRelatedModel
- transactions: AsyncRelatedCollection

#### Properties

- type: The EntryType of the ArchivedEntry.
- details: A packify.SerializableType stored in the database as a blob.
- transactions: The related `ArchivedTransaction`s. Attempting to set to a
non-`ArchivedTransaction` raises a `TypeError`.
- account: The related `Account`. Attempting to set to a non-`Account` raises a
`TypeError`.

#### Methods

##### `__hash__() -> int:`

##### `@classmethod generate_id(data: dict) -> str:`

Generate an id by hashing the non-id contents. Raises TypeError for unencodable
type (calls packify.pack).

##### `@classmethod async insert(data: dict) -> ArchivedEntry | None:`

Ensure data is encoded before inserting.

##### `@classmethod async insert_many(items: list[dict]) -> int:`

Ensure data is encoded before inserting.

##### `@classmethod query(conditions: dict = None) -> AsyncQueryBuilderProtocol:`

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

### `Entry(AsyncHashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- account: AsyncRelatedModel
- transactions: AsyncRelatedCollection

#### Properties

- type: The EntryType of the Entry.
- details: A packify.SerializableType stored in the database as a blob.
- account: The related `Account`. Attempting to set to a non-`Account` raises a
`TypeError`.
- transactions: The related `Transaction`s. Attempting to set to a
non-`Transaction` raises a `TypeError`.

#### Methods

##### `__hash__() -> int:`

##### `@classmethod generate_id(data: dict) -> str:`

Generate an id by hashing the non-id contents. Raises TypeError for unencodable
type (calls packify.pack).

##### `@classmethod async insert(data: dict) -> Entry | None:`

Ensure data is encoded before inserting.

##### `@classmethod async insert_many(items: list[dict]) -> int:`

Ensure data is encoded before inserting.

##### `@classmethod query(conditions: dict = None) -> AsyncQueryBuilderProtocol:`

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

##### `async archive() -> ArchivedEntry | None:`

Archive the Entry. If it has already been archived, return the existing
ArchivedEntry.

### `Account(AsyncHashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- ledger: AsyncRelatedModel
- parent: AsyncRelatedModel
- correspondence: AsyncRelatedModel
- category: AsyncRelatedModel
- children: AsyncRelatedCollection
- entries: AsyncRelatedCollection
- archived_entries: AsyncRelatedCollection

#### Properties

- type: The AccountType of the Account.
- locking_scripts: The dict mapping EntryType to tapescript locking script
bytes.
- details: A packify.SerializableType stored in the database as a blob.
- correspondence: The related `Correspondence`. Attempting to set to a
non-`Correspondence` raises a `TypeError`.
- ledger: The related `Ledger`. Attempting to set to a non-`Ledger` raises a
`TypeError`.
- children: The related `Account`s. Attempting to set to a non-`Account` raises
a `TypeError`.
- parent: The related `Account`. Attempting to set to a non-`Account` raises a
`TypeError`.
- category: The related `AccountCategory`. Attempting to set to a
non-`AccountCategory` raises a `TypeError`.
- entries: The related `Entry`s. Attempting to set to a non-`Entry` raises a
`TypeError`.
- archived_entries: The related `ArchivedEntry`s. Attempting to set to a
non-`ArchivedEntry` raises a `TypeError`.

#### Methods

##### `@classmethod async insert(data: dict) -> Account | None:`

Ensure data is encoded before inserting.

##### `@classmethod async insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Ensure items are encoded before inserting.

##### `async update(updates: dict, /, *, suppress_events: bool = False) -> Account:`

Ensure updates are encoded before updating.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> AsyncQueryBuilderProtocol:`

Ensure conditions are encoded before querying.

##### `async balance(include_sub_accounts: bool = True, rolled_up_balances: dict[str, tuple[EntryType, int]] = {}) -> int:`

Tally all entries for this account. Includes the balances of all sub-accounts if
include_sub_accounts is True. To get an accurate balance, pass in the balances
from the most recent TxRollup.

##### `validate_script(entry_type: EntryType, auth_script: bytes | Script, tapescript_runtime: dict = {}) -> bool:`

Checks if the auth_script validates against the correct locking_script for the
EntryType. Returns True if it does and False if it does not (or if it errors).

### `LedgerType(Enum)`

Enum of valid ledger types: CURRENT and FUTURE for cash and accrual accounting,
respectively.

### `AccountCategory(AsyncHashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes
- ledger_type: str | None
- destination: str
- accounts: AsyncRelatedCollection

#### Properties

- ledger_type: The LedgerType that this AccountCategory applies to, if any.
- accounts: The related `Account`s. Attempting to set to a non-`Account` raises
a `TypeError`.

#### Methods

##### `@classmethod async insert(data: dict, /, *, suppress_events: bool = False) -> AccountCategory | None:`

Ensure data is encoded before inserting.

##### `@classmethod async insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Ensure items are encoded before inserting.

##### `async update(updates: dict, /, *, suppress_events: bool = False) -> AccountCategory:`

Ensure updates are encoded before updating.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> AsyncQueryBuilderProtocol:`

Ensure conditions are encoded before querying.

### `Ledger(AsyncHashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- owner: AsyncRelatedModel
- currency: AsyncRelatedModel
- accounts: AsyncRelatedCollection
- transactions: AsyncRelatedCollection
- archived_transactions: AsyncRelatedCollection
- rollups: AsyncRelatedCollection

#### Properties

- type: The LedgerType of the Ledger.
- owner: The related `Identity`. Attempting to set to a non-`Identity` raises a
`TypeError`.
- currency: The related `Currency`. Attempting to set to a non-`Currency` raises
a `TypeError`.
- accounts: The related `Account`s. Attempting to set to a non-`Account` raises
a `TypeError`.
- transactions: The related `Transaction`s. Attempting to set to a
non-`Transaction` raises a `TypeError`.
- rollups: The related `TxRollup`s. Attempting to set to a non-`TxRollup` raises
a `TypeError`.
- archived_transactions: The related `ArchivedTransaction`s. Attempting to set
to a non-`ArchivedTransaction` raises a `TypeError`.

#### Methods

##### `@classmethod async insert(data: dict) -> Ledger | None:`

Ensure data is encoded before inserting.

##### `@classmethod async insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Ensure items are encoded before inserting.

##### `async update(updates: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> Ledger:`

Ensure updates are encoded before updating.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> AsyncQueryBuilderProtocol:`

Ensure conditions are encoded before querying.

##### `async balances(reload: bool = False) -> dict[str, tuple[int, AccountType]]:`

Return a dict mapping account ids to their balances. Accounts with sub-accounts
will not include the sub-account balances; the sub-account balances will be
returned separately.

##### `setup_basic_accounts() -> list[Account]:`

Creates and returns a list of 3 unsaved Accounts covering the 3 basic
categories: Asset, Liability, Equity.

### `Identity(AsyncHashedModel)`

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- ledgers: AsyncRelatedCollection
- correspondences: AsyncRelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- ledgers: The related `Ledger`s. Attempting to set to a non-`Ledger` raises a
`TypeError`.
- correspondences: The related `Correspondence`s. Attempting to set to a
non-`Correspondence` raises a `TypeError`.

#### Methods

##### `public() -> dict:`

Return the public data for cloning the Identity.

##### `async correspondents(reload: bool = False) -> list[Identity]:`

Get the correspondents for this Identity.

##### `async get_correspondent_accounts(correspondent: Identity, reload: bool = False) -> list[Account]:`

Get the nosto and vostro accounts for a correspondent.

### `Correspondence(AsyncHashedModel)`

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
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- identities: AsyncRelatedCollection
- ledgers: AsyncRelatedCollection
- rollups: AsyncRelatedCollection
- accounts: AsyncRelatedCollection

#### Properties

- details: Returns the details of the correspondence as a dict.
- signatures: Returns the signatures of the correspondences as a dict mapping
Identity ID to bytes signature.
- txru_lock: Returns the txru_lock directly from the details field.
- ledgers: The related `Ledger`s. Attempting to set to a non-`Ledger` raises a
`TypeError`.
- accounts: The related `Account`s. Attempting to set to a non-`Account` raises
a `TypeError`.
- identities: The related `Identity`s. Attempting to set to a non-`Identity`
raises a `TypeError`.
- rollups: The related `TxRollup`s. Attempting to set to a non-`TxRollup` raises
a `TypeError`.

#### Methods

##### `async get_accounts(reload: bool = True) -> dict[str, dict[AccountType, Account]]:`

Loads the relevant nostro and vostro Accounts for the Identities that are part
of the Correspondence, as well as the equity Accounts for each Identity,
returning a dict of the form { identity.id: { AccountType: Account }}.

##### `async setup_accounts(locking_scripts: dict[str, bytes]) -> dict[str, dict[AccountType, Account]]:`

Takes a dict mapping Identity ID to tapescript locking scripts. Returns a dict
of Accounts necessary for setting up the credit Correspondence of form {
identity.id: { AccountType: Account }}.

##### `async pay_correspondent(payer: Identity, payee: Identity, amount: int, txn_nonce: bytes) -> tuple[list[Entry], list[Entry]]:`

Prepares two lists of entries in which the payer remits to the payee the given
amount: one in which the nostro account on the payer's ledger is credited and
one in which the vostro account on the payer's ledger is credited.

##### `async balances(rolled_up_balances: dict[str, tuple[EntryType, int]] = {}) -> dict[str, int]:`

Returns the balances of the correspondents as a dict mapping str Identity ID to
signed int (equal to Nostro - Vostro).

### `ArchivedTransaction(AsyncHashedModel)`

Optional class for storing a trimmed Transaction after is has included in a
TxRollup. This allows accessing the trimmed Transaction details more efficiently
than by loading the AsyncDeletedModel that contains the trimmed Transaction.
Must be used in conjunction with ArchivedEntry.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- entries: AsyncRelatedCollection
- ledgers: AsyncRelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- auth_scripts: A dict mapping account IDs to tapescript unlocking script bytes.
- entries: The related `ArchivedEntry`s. Attempting to set to a
non-`ArchivedEntry` raises a `TypeError`.
- ledgers: The related `Ledger`s. Attempting to set to a non-`Ledger` raises a
`TypeError`.

#### Methods

##### `async validate(tapescript_runtime: dict = {}, reload: bool = False) -> bool:`

Determines if a Transaction is valid using the rules of accounting and checking
all auth scripts against their locking scripts. The tapescript_runtime can be
scoped to each entry ID. Raises TypeError for invalid arguments. Raises
ValueError if the entries do not balance for each ledger; if a required auth
script is missing; or if any of the entries is contained within an existing
Transaction. If reload is set to True, entries and accounts will be reloaded
from the database.

##### `async save(tapescript_runtime: dict = {}, reload: bool = False) -> ArchivedTransaction:`

Validate the transaction, save the entries, then save the transaction.

### `Currency(AsyncHashedModel)`

#### Annotations

- table: <class 'str'>
- id_column: <class 'str'>
- columns: tuple[str]
- id: <class 'str'>
- name: <class 'str'>
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- ledgers: <class 'sqloquent.asyncql.interfaces.AsyncRelatedCollection'>

#### Properties

- details: A string stored in the database as text. Note that this will be
changed to a packify.SerializableType stored as a blob in 0.4.0.
- ledgers: The related `Ledger`s. Attempting to set to a non-`Ledger` raises a
`TypeError`.

#### Methods

##### `to_decimal(amount: int) -> Decimal:`

Convert the amount into a Decimal representation.

##### `from_decimal(amount: Decimal) -> int:`

Convert the amount from a Decimal representation.

##### `get_units(amount: int) -> tuple[int]:`

Get the full units and subunits. The number of subunit figures will be equal to
`unit_divisions`; e.g. if `base=10` and `unit_divisions=2`, `get_units(200)`
will return `(2, 0, 0)`; if `base=60` and `unit_divisions=2`, `get_units(200)`
will return `(0, 3, 20)`.

##### `format(amount: int, /, *, divider: str = '.', use_fx_symbol: bool = False, use_postfix: bool = False, use_prefix: bool = True, decimal_places: int = 2, use_decimal: bool = True) -> str:`

Format an amount using the correct number of `decimal_places`. If `use_decimal`
is `False`, instead the unit subdivisions from `get_units` will be combined
using the `divider` char, and each part will be prefix padded with 0s to reach
the `decimal_places`. E.g. `.format(200, use_decimal=False, divider=':') ==
'02:00'` for a Currency with `base=100` and `unit_divisions=1`.

##### `parse(amount_str: str, /, *, divider: str = '.', decimal_places: int = 2, use_decimal: bool = True) -> str:`

Inverse of `format`: takes a formatted `str` and outputs the correct `int`
amount of base units.

### `Customer(AsyncHashedModel)`

#### Annotations

- table: <class 'str'>
- id_column: <class 'str'>
- columns: tuple[str]
- id: <class 'str'>
- name: <class 'str'>
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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

### `Transaction(AsyncHashedModel)`

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
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- entries: AsyncRelatedCollection
- ledgers: AsyncRelatedCollection
- rollups: AsyncRelatedCollection

#### Properties

- details: A packify.SerializableType stored in the database as a blob.
- auth_scripts: A dict mapping account IDs to tapescript unlocking script bytes.
- entries: The related `Entry`s. Attempting to set to a non-`Entry` raises a
`TypeError`.
- ledgers: The related `Ledger`s. Attempting to set to a non-`Ledger` raises a
`TypeError`.
- rollups: The related `TxRollup`s. Attempting to set to a non-`TxRollup` raises
a `TypeError`.

#### Methods

##### `@classmethod async prepare(entries: list[Entry], timestamp: str, auth_scripts: dict = {}, details: packify.SerializableType = None, tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:`

Prepare a transaction. Raises TypeError for invalid arguments. Raises ValueError
if the entries do not balance for each ledger; if a required auth script is
missing; or if any of the entries is contained within an existing Transaction.
Entries and Transaction will have IDs generated but will not be persisted to the
database and must be saved separately. The auth_scripts dict must map account
IDs to tapescript bytecode bytes.

##### `async validate(tapescript_runtime: dict = {}, reload: bool = False) -> bool:`

Determines if a Transaction is valid using the rules of accounting and checking
all auth scripts against their locking scripts. The tapescript_runtime can be
scoped to each entry ID. Raises TypeError for invalid arguments. Raises
ValueError if the entries do not balance for each ledger; if a required auth
script is missing; or if any of the entries is contained within an existing
Transaction. If reload is set to True, entries and accounts will be reloaded
from the database. Auth scripts can be provided by account ID or by entry ID;
scoping by entry ID will take precedence.

##### `async save(tapescript_runtime: dict = {}, reload: bool = False) -> Transaction:`

Validate the transaction, save the entries, then save the transaction.

##### `async archive() -> ArchivedTransaction:`

Archive the Transaction. If it has already been archived, return the existing
ArchivedTransaction.

### `TxRollup(AsyncHashedModel)`

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
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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
- correspondence: AsyncRelatedModel
- ledger: AsyncRelatedModel
- transactions: AsyncRelatedCollection
- parent: AsyncRelatedModel
- child: AsyncRelatedModel

#### Properties

- tx_ids: A list of transaction IDs. Setting causes the ids to be sorted, then
combined into a Merkle Tree, the root of which is used to set `self.tx_root`.
- balances: A dict mapping account IDs to tuple[EntryType, int] balances.
- tree: A merkle tree of the transaction IDs.
- ledger: The related `Ledger`. Attempting to set to a non-`Ledger` raises a
`TypeError`.
- transactions: The related `Transaction`s. Attempting to set to a
non-`Transaction` raises a `TypeError`.
- parent: The related `TxRollup`. Attempting to set to a non-`TxRollup` raises a
`TypeError`.
- child: The related `TxRollup`. Attempting to set to a non-`TxRollup` raises a
`TypeError`.
- correspondence: The related `Correspondence`. Attempting to set to a
non-`Correspondence` raises a `TypeError`.

#### Methods

##### `public() -> dict:`

Returns the public data for mirroring this TxRollup. Excludes the tx_ids.

##### `prove_txn_inclusion(txn_id: str | bytes) -> bytes:`

Proves that a transaction is included in the tx rollup.

##### `verify_txn_inclusion_proof(txn_id: str | bytes, proof: bytes) -> bool:`

Verifies that a transaction is included in the tx rollup.

##### `@classmethod async calculate_balances(txns: list[Transaction], parent_balances: dict[str, tuple[EntryType, int]] | None = None, reload: bool = False) -> dict[str, tuple[EntryType, int]]:`

Calculates the account balances for a list of rolled-up transactions. If
parent_balances is provided, those are the starting balances to which the
balances of the rolled-up transactions are added. If reload is True, the entries
are reloaded from the database.

##### `@classmethod async prepare(txns: list[Transaction], parent_id: str | None = None, correspondence: Correspondence | None = None, ledger: Ledger | None = None, reload: bool = False) -> TxRollup:`

Prepare a tx rollup by checking that all txns are for the accounts of the given
correspondence or belong to the same ledger if no correspondence is provided.
Raises TypeError if txns is not a list of Transaction objects. Raises ValueError
if any txns are not for accounts of the given correspondence or of the same
ledger if no correspondence is provided, or if the parent TxRollup already has a
child, or if there are no txns and no ledger or correspondence is provided, or
if a TxRollup chain already exists for the given ledger or correspondence when
no parent is provided. The Transaction IDs are sorted and combined into a Merkle
Tree, the root of which is used to set the `tx_root` property.

##### `async validate(reload: bool = False) -> bool:`

Validates that a TxRollup has been authorized properly; that the balances are
correct; and that the height is 1 + the height of the parent tx rollup (if one
exists); and that there is no other chain for the relevant ledger or
correspondence when no parent is provided.

##### `async trim(archive: bool = True) -> int:`

Trims the transactions and entries committed to in this tx rollup. Returns the
number of transactions trimmed. If archive is True, the transactions and entries
are archived before being deleted. Raises ValueError if the tx rollup is not
valid.

##### `trimmed_transactions() -> AsyncSqlQueryBuilder:`

Returns a query builder for AsyncDeletedModels containing the trimmed
transactions committed to in this tx rollup.

##### `async trimmed_entries() -> AsyncSqlQueryBuilder:`

Returns a query builder for AsyncDeletedModels containing the trimmed entries
from trimmed transactions committed to in this tx rollup.

##### `archived_transactions() -> AsyncSqlQueryBuilder:`

Returns a query builder for ArchivedTransactions committed to in this tx rollup.

##### `async archived_entries() -> AsyncSqlQueryBuilder:`

Returns a query builder for ArchivedEntries committed to in this tx rollup.

### `Vendor(AsyncHashedModel)`

#### Annotations

- table: <class 'str'>
- id_column: <class 'str'>
- columns: tuple[str]
- id: <class 'str'>
- name: <class 'str'>
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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

### `AsyncDeletedModel(AsyncSqlModel)`

Model for preserving and restoring deleted AsyncHashedModel records.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
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

##### `@classmethod async insert(data: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel | None:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict. Automatically sets a timestamp if one is not supplied.

##### `async restore(inject: dict = {}, /, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel:`

Restore a deleted record, remove from deleted_records, and return the restored
model. Raises ValueError if model_class cannot be found. Raises TypeError if
model_class is not a subclass of AsyncSqlModel. Uses packify.unpack to unpack
the record. Raises TypeError if packed record is not a dict.

### `AsyncAttachment(AsyncHashedModel)`

Class for attaching immutable details to a record.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
- connection_info: str
- data: dict
- data_original: MappingProxyType
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- related_model: str
- related_id: str
- _related: AsyncSqlModel
- _details: packify.SerializableType

#### Methods

##### `async related(reload: bool = False) -> AsyncSqlModel:`

Return the related record.

##### `attach_to(related: AsyncSqlModel) -> AsyncAttachment:`

Attach to related model then return self.

##### `get_details(reload: bool = False) -> packify.SerializableType:`

Decode packed bytes to dict.

##### `set_details(details: packify.SerializableType = {}) -> AsyncAttachment:`

Set the details column using either supplied data or by packifying
self._details. Return self in monad pattern. Raises packify.UsageError or
TypeError if details contains unseriazliable type.

## Functions

### `set_connection_info(db_file_path: str):`

Set the connection info for all models to use the specified sqlite3 database
file path.


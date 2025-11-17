# BookChain

BookChain is an accounting library that provides a cryptographic audit trail of
every identity, ledger, account, transaction, and entry to ensure data
integrity. It also uses the tapescript package to ensure account security and
reject invalid transactions if controls are configured on the involved accounts.
Included are tools for establishing correspondent credit relations as well as
accomplishing basic bookkeeping tasks.

This package uses
[sqloquent](https://pypi.org/project/sqloquent) for database persistence,
[tapescript](https://pypi.org/project/tapescript) for authorization, and
[packify](https://pypi.org/project/packify) for deterministic encoding.

## Status

All initially planned features have been implemented and tested.

Open issues can be found [here](https://github.com/k98kurz/bookchain/issues).

The async implementation has an upstream issue from the sqloquent dependency
that can be tracked [here](https://github.com/k98kurz/sqloquent/issues/16). Once
that is fixed, the dependency will be updated, and this notice will be removed.

## Overview

This library provides an accounting system using sqloquent for persistence,
packify for deterministic encoding, tapescript for authorization, and the
classic rules of double-entry bookkeeping. All entries and transactions have
deterministic content IDs determined by hashing the relevant contents, and the
inclusion of tapescript allows for Bitcoin-style locking and unlocking scripts
to encode access controls at the account level.

### Class organization

`Currency` represents a currency/unit of account for a `Ledger`. It includes the
number of subunits to track and optionally the base for conversion to decimal
(defaults to 10), FX symbol, prefix symbol, and/or postfix symbol to be used with
the `format` method (e.g. `USD.format(1200)` could result in "12.00 USD",
"$12.00", or "12.00$", respectively). It also includes `to_decimal` method for
formatting int amounts into `Decimal`s, and `get_units` method for getting a
tuple of whole units and remainders.

`Identity` represents a legal person or other entity that can sign contracts
or engage in transactions. It includes the name, details, and optionally public
key bytes and private key seed bytes.

`Ledger` represents a general ledger for a given `Identity` using a specific
`Currency`. It includes a name, a `LedgerType`, the `Identity` id, and the
`Currency` id. `LedgerType` is an enum representing the valid ledger types,
either `PRESENT` or `FUTURE` for cash and accrual accounting, respectively, or
for other uses the package user may define.

`Account` represents an account for a given `Ledger`. It includes a name, a type
(one of the `AccountType` enum options), the `Ledger` id, an optional locking
script for access control, and optional details.

`AccountCategory` represents a category for `Account`s. It includes a name, a
`LedgerType`, and a destination (str description; e.g. "Balance Sheet" or
"Profit and Loss").

`AccountType` is an enum representing the valid account types. The options are
`DEBIT_BALANCE`, `ASSET`, `CONTRA_ASSET`, `CREDIT_BALANCE`, `LIABILITY`,
`EQUITY`, `CONTRA_LIABILITY`, and `CONTRA_EQUITY`.

`Entry` represents an entry in the general ledger for a given `Account`. It
includes a type (one of the `EntryType` enum options), an amount, a nonce, the
`Account` id, and optional details, description, and timestamp.

`EntryType` is an enum representing the valid entry types. The options are
CREDIT and DEBIT.

`Transaction` represents a transaction made of `Entry`s. It includes the `Entry`
ids, `Ledger` ids, a timestamp, details, and the auth script(s). Each
`Transaction` must include entries that balance the number of credits and debits
applied to each ledger affected by the transaction. Use `Transaction.prepare` to
prepare a transaction -- it will raise validation errors if the transaction is
not valid -- then call `.save()` on the result to persist it to the database.
Transactions in the database can be validated by using `.validate()`, which will
return `True` if it is valid and `False` if it is not (it will also raise errors
in some situations that require more information about the validation failure).

`TxRollup` represents a rollup of `Transaction`s. It commits the `Transaction`
ids into a Merkle tree and includes the root hash, timestamp, optional details,
aggregate account balance changes of the committed `Transaction`s, the
`TxRollup` id of the parent `TxRollup` (or `None` for the genesis `TxRollup`),
the height of the `TxRollup` (number of `TxRollup`s in the chain), and the
`Correspondence` id or `Ledger` id. Inclusion proofs for `Transaction`s can be
generated using the `TxRollup.get_inclusion_proof` method and verified using
the `TxRollup.verify_inclusion_proof` method; the latter requires only the
`tx_root`, but the former requires the full list of `tx_ids`.

`ArchivedEntry` and `ArchivedTransaction` are optional classes for storing the
trimmed `Entry`s and `Transaction`s, respectively, after they have been included
in a `TxRollup`. The default behavior of `TxRollup.trim` is to use these archive
classes, but `trim(False)` can be used to prevent archiving. (The trimmed txns
and entries will be retrievable by using `TxRollup.trimmed_transactions` and
`TxRollup.trimmed_entries`, respectively, but they are not optimized for ease of
use.)

`Correspondence` represents a correspondent credit relationship between several
`Identity`s.

`Customer` and `Vendor` are optional classes for storing customer and vendor
information, respectively. They include a name, code, optional details, and
optional description. There are no relations defined for these classes.

### Relations

- `Identity` has many `Ledger`s and is within `Correspondence`s
- `Ledger` belongs to `Identity` and `Currency`, has many `Account`s, is within
  `Transaction`s, and has many `TxRollup`s
- `Account` belongs to `Ledger` and `AccountCategory`, and has many `Entry`s
- `AccountCategory` has many `Account`s
- `Entry` belongs to `Account` and is within `Transaction`s
- `Transaction` contains `Ledger`s and `Entry`s
- `Correspondence` contains `Identity`s and has many `TxRollup`s
- `TxRollup` belongs to `Correspondence` or `Ledger` and belongs to and has one
  `TxRollup`
- `ArchivedTransaction` contains `ArchivedEntry`s
- `ArchivedEntry` belongs to `Account` and is within `ArchivedTransaction`s

### Cryptographic audit trail

Models inherit from `sqloquent.HashedModel`, so all data is hashed into the ID,
guaranteeing a unique, deterministic ID for each unique record.

Whenever something is deleted, it will be encoded and inserted into the
`deleted_models` table to maintain an audit trail.

Accounts may be created with locking scripts, which will require the Transaction
to include valid auth scripts for the associated Entries. These scripts are
executed using tapescript. If some tapescript runtime values are required for
validation, e.g. cache or plugins, they can be saved in `Transaction.details`
and passed to `Transaction.prepare`, `Transaction.validate`, and
`Account.validate_script`.

`TxRollup`s include a `tx_root` which is the root hash of the Merkle tree of
the `Transaction`s they contain. This allows for efficient inclusion proofs
(`TxRollup.get_inclusion_proof`) and verification of the presence of a
`Transaction` in a `TxRollup` (`TxRollup.verify_inclusion_proof`). `TxRollup`s
made for a `Correspondence` will require an `auth_script` if the
`Correspondence` contains a `txru_lock` or if the `Identity`s each have a
pubkey (a 2-of-2 multisig lock will be generated as the default `txru_lock` if
one was not set). This system allows for old `Transaction`s to be trimmed from
the local database while ensuring that all parties validated the aggregate
account balance changes of the trimmed `Transaction`s were preserved.

#### Tapescript runtime

When an auth script is being validated, the tapescript runtime cache will
consist of the following:

- "sigfield1": the current entry ID in byte form
- "sigfield2": the catenation of the sorted IDs of all entries, allowing
  locking scripts to require binding to the full transaction or just a
  single entry (`sigflags='02'` to allow masking out sigfield2).
- "timestamp": `parse_timestamp(transaction.timestamp)`, if it can be
  parsed; otherwise left unset.
- "e_idx": the index of the current `Entry` in the lists of entry values
- "e_ids": the `transaction.entry_ids` list of `Entry` IDs
- "e_type": a list of bools for each `Entry` where `True` means it is credit
  and `False` means it is a debit entry
- "e_amount": the list of `Entry.amount`s
- "e_nonce": the list of `Entry.nonce`s
- "e_acct_id": the list of `Entry.account_id`s

Advanced locking scripts can be written that programmatically access these
values using the `val s"{name}"` syntax, e.g. `val s"e_idx" @= idx 1`. The
general expectation is that most locking scripts will be simple signature checks,
taproot, graftroot, or delegate key locks.

## Installation and Setup

Install with `pip install bookchain`. If you want to use the async version,
instead install with `pip install bookchain[asyncql]`.

Once installed, use the following to setup your project as appropriate:

```python
import bookchain

bookchain.publish_migrations(folder_for_migration_files)

bookchain.automigrate(folder_for_migration_files, db_file_path)

bookchain.set_connection_info(db_file_path)
```

To use the async version:

```python
import bookchain
import bookchain.asyncql

bookchain.publish_migrations(folder_for_migration_files)

bookchain.automigrate(folder_for_migration_files, db_file_path)

bookchain.asyncql.set_connection_info(db_file_path)
```

The `bookchain.publish_migrations` function can be passed a callback that
takes the str model name and str migration file contents, and returns the
modified str migration file contents. This can be used to modify the migration
file contents before they are written to disk. For example, if you wanted to
modify the `Account` migration file to add a unique constraint to the `name`
column, you could do the following:

```python
def migration_callback(name: str, m: str) -> str:
    if name == 'Account':
        return m.replace("t.text('name').index()", "t.text('name').unique()")
    return m

bookchain.publish_migrations(path_to_migrations_folder, migration_callback)
```

## More Resources

Documentation generated by [autodox](https://pypi.org/project/autodox) can be
found [here](https://github.com/k98kurz/bookchain/blob/v0.4.2/dox.md). Docs for
the async version can be found
[here](https://github.com/k98kurz/bookchain/blob/v0.4.2/asyncql_dox.md).

Check out the [Pycelium discord server](https://discord.gg/b2QFEJDX69). If you
experience a problem, please discuss it on the Discord server. All suggestions
for improvement are also welcome, and the best place for that is also Discord.
If you experience a bug and do not use Discord, open an issue on Github.

## Tests

There are a total of 18 tests (12 e2e tests and 6 tests for miscellaneous
tools/features). To run them, clone the repo, set up a virtual environment
(e.g. `python -m venv venv && source venv/bin/activate`), install the
dependencies with `pip install -r requirements.txt`, and then run the following:
`find tests -name test_*.py -print -exec python {} \;`. On Windows, the 9 test
files will have to be individually run with the following:

```bash
python tests/test_advanced_e2e.py
python tests/test_async_advanced_e2e.py
python tests/test_async_basic_e2e.py
python tests/test_async_correspondences_e2e.py
python tests/test_async_txrollup_e2e.py
python tests/test_basic_e2e.py
python tests/test_correspondences_e2e.py
python tests/test_misc.py
python tests/test_txrollup_e2e.py
```

## Personal, Non-commercial Use License

Copyright (c) 2025 Jonathan Voss (k98kurz)

Permission to use, copy, modify, and/or distribute this software
for any personal, non-commercial purpose is hereby granted, provided
that the above copyright notice and this permission notice appear in
all copies. For other uses, contact the software author.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

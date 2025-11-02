## 0.4.1

- Bug fix: `Currency.format` was not using the `divider` argument properly;
  fixed and coverage added to test suite
- Small documentation update

## 0.4.0

- Renamed `LedgerType.PRESENT` to `LedgerType.CURRENT`.
- Added a `parse_timestamp` helper to parse string timestamps into Unix epoch ints
- `Transaction.validate()` updated:
  - Each auth script can now be scoped to an entry ID (falls back to account ID)
  - Tapescript runtime cache now includes the following:
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
- Added `Account.correspondence_id` field and `Account.correspondence` relation.
  - Updated `Correspondence.get_accounts()`, `.setup_accounts()`, and
    `.pay_correspondent()` to make use of the new column and relation.
  - Updated `Identity.get_correspondent_accounts` to use the new relation.
- Updated `Correspondence` system to require a "General Equity" account for each
  participating `Identity`/`Ledger`.
- Added nullable, non-hashed `Entry.timestamp` column to make querying easier.
- `Customer` and `Vendor`: `details` column is now a packify.SerializableType
  stored as a blob.
- Bug fix: `Entry.insert_many()` and `ArchivedEntry.insert_many()` did not
  function and had been skipped in tests. They now work as expected and are
  covered by e2e test suite.

## 0.3.3

- Added text `description` column to the following models:
  - `Account`
  - `ArchivedEntry`
  - `ArchivedTransaction`
  - `Correspondence`
  - `Currency`
  - `Customer`
  - `Entry`
  - `Identity`
  - `Ledger`
  - `Transaction`
  - `TxRollup`
  - `Vendor`
- Corrected `Customer` and `Vendor`: `details` column was incorrectly handled as
  a packify.SerializableType stored as a blob, but the column type was text.
  This has been corrected, and a note has been added to the documentation to
  indicate that this will be changed to a packify.SerializableType stored as a
  blob in 0.4.0.
- Replaced hard-coded default `packify` serialized values with dynamically
  calculated ones across all models
- Small improvements to some documentation

## 0.3.2

- Updated tapescript to 0.7.2
- Updated packify to 0.3.1 and applied compatibility patches
- Updated `Currency`:
    - Added `from_decimal` method
    - Updated `format` method to include non-decimal formatting,
      e.g. 'H00:00:00'
- Improved documentation for `TxRollup.prepare`
- Updated 'Correspondence': added missing '.ledgers' relation

## 0.3.1

- Updated tapescript dependency to 0.7.1
- Slightly improved `Identity.get_correspondent_accounts`

## 0.3.0

- Updated `Correspondence`:
  - New `signatures` column that is excluded from hashing
  - `details` and `signatures` columns are stored as bytes but parsed as dicts
    using packify
  - Changed `get_accounts()` to return a dict with the same format as
    `setup_accounts()`
  - Updated `pay_correspondent()` and `balances()` internals to use new
    `get_accounts()` output format
- Added new `TxRollup` class to roll-up and prune old transactions
- Added new `ArchivedTransaction` and `ArchivedEntry` classes to
  archive transactions and entries (used by default, but can be skipped by
  calling `TxRollup.trim(False)`)
- Updated `Entry`: added `archive()` method
- Updated `Transaction`:
  - Added `archive()` method
  - Updated `validate()` to use new `Correspondence.get_accounts()` output
    format
- Updated `Account`: `balance()` now accepts `rolled_up_balances` parameter
  to get an accurate balance using the latest `TxRollup.balances` values
- Added `version()` function to get the version of the package

## 0.2.3

- Added `active` column to `Account` model
  - Type annotation is `bool|Default[True]`
  - Column is excluded from hashing
- Updated migration tools:
  - Added `get_migrations(): dict[str, str]` function
  - Updated `publish_migrations()` to accept a `migration_callback` parameter

## 0.2.2

- Bug fix: exposed `LedgerType` enum

## 0.2.1

- Minor fix: updated `__version__` str from 0.1.2 to 0.2.1

## 0.2.0

- Added `AccountCategory` model and `LedgerType` enum

## 0.1.2

- Bug fix in `Currency`

## 0.1.1

- Updated `Currency` formatting
- Misc fixes

## 0.1.0

- Initial release

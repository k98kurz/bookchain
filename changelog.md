## 0.3.2

- Updated tapescript to 0.7.2
- Updated packify to 0.3.1 and applied compatibility patches
- Updated `Currency`:
    - Added `from_decimal` method
    - Updated `format` method to include non-decimal formatting,
      e.g. 'H00:00:00'
- Improved documentation for `TxRollup.prepare`

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

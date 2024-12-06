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

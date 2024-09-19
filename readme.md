@TODO

Separate locking scripts for each entry type (credit and debit) per Account.

# scriptcounting

Double-entry accounting system with cryptographic audit trail and optional
cryptographic transaction verification.

## Status

- [ ] Base classes
- [ ] Accounting rules
- [ ] Tests
- [ ] Documentation

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
formatting int amounts into `Decimal`s.

`Identity` represents a legal person or other entity that can sign contracts
or engage in transactions. It includes the name, details, and optionally public
key bytes and private key seed bytes.

`Ledger` represents a general ledger for a given `Identity` using a specific
`Currency`. It includes a name, the `Identity` id, and the `Currency` id.

`Account` represents an account for a given `Ledger`. It includes a name, a type
(one of the `AccountType` enum options), the `Ledger` id, an optional locking
script for access control, and optional details.

`AccountType` is an enum representing the valid account types. The options are
`DEBIT_BALANCE`, `ASSET`, `CONTRA_ASSET`, `CREDIT_BALANCE`, `LIABILITY`,
`EQUITY`, `CONTRA_LIABILITY`, and `CONTRA_EQUITY`.

`Entry` represents an entry in the general ledger for a given `Account`. It
includes a type (one of the `EntryType` enum options), an amount, a nonce, the
`Account` id, and optional details.

`EntryType` is an enum representing the valid entry types. The options are
CREDIT and DEBIT.

`Transaction` represents a transaction made of `Entry`s. It includes the `Entry`
ids, `Ledger` ids, a timestamp, details, and the auth script(s). Each
`Transaction` must include entries that balance the number of credits and debits
applied to each ledger affected by the transaction.

`Correspondence` represents a correspondent credit relationship between several
`Identity`s.

- `Identity` has many `Ledger`s and is within `Correspondence`s
- `Ledger` belongs to `Identity` and `Currency`, has many `Account`s, and is within `Transaction`s
- `Account` belongs to `Ledger` and has many `Entry`s
- `Entry` belongs to `Account` and is within `Transaction`s
- `Transaction` contains `Ledger`s and `Entry`s
- `Correspondence` contains `Identity`s

### Cryptographic audit trail

Models inherit from `sqloquent.HashedModel`, so all data is hashed into the ID,
guaranteeing a unique, deterministic ID for each unique model.

Whenever something is deleted, it will be encoded and inserted into the
`deleted_models` table to maintain an audit trail.

Accounts may be created with locking scripts, which will require associated
Entries to provide valid auth scripts. These scripts are executed using
tapescript. If some tapescript runtime values are required for validation,
e.g. cache or plugins, they can be saved in Transaction.details and passed to
`Transaction.validate` and `Account.validate_script`.


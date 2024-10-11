from enum import Enum


class EntryType(Enum):
    """Enum of valid Entry types (CREDIT and DEBIT)."""
    CREDIT = 'c'
    DEBIT = 'd'

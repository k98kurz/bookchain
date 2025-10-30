from enum import Enum


class LedgerType(Enum):
    """Enum of valid ledger types: CURRENT and FUTURE for cash and
        accrual accounting, respectively.
    """
    CURRENT = 'Current'
    FUTURE = 'Future'

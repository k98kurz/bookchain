from enum import Enum


class LedgerType(Enum):
    """Enum of valid ledger types: PRESENT and FUTURE for cash and
        accrual accounting, respectively.
    """
    PRESENT = 'Present'
    FUTURE = 'Future'

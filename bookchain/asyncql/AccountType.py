from enum import Enum


class AccountType(Enum):
    """Enum of valid Account types."""
    DEBIT_BALANCE = 'd'
    ASSET = 'a'
    NOSTRO_ASSET = 'n'
    CONTRA_ASSET = '-a'
    CREDIT_BALANCE = 'c'
    LIABILITY = 'l'
    VOSTRO_LIABILITY = 'v'
    EQUITY = 'e'
    CONTRA_LIABILITY = '-l'
    CONTRA_EQUITY = '-e'

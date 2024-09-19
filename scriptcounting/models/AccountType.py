from enum import Enum


class AccountType(Enum):
    DEBIT_BALANCE = 'd'
    ASSET = 'a'
    CONTRA_ASSET = '-a'
    CREDIT_BALANCE = 'c'
    LIABILITY = 'l'
    EQUITY = 'e'
    CONTRA_LIABILITY = '-l'
    CONTRA_EQUITY = '-e'


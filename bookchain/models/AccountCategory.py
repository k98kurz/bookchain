from __future__ import annotations

from sqloquent.interfaces import QueryBuilderProtocol
from .LedgerType import LedgerType
from typing import Any
from sqloquent import HashedModel, RelatedCollection


class AccountCategory(HashedModel):
    connection_info: str = ''
    table: str = 'account_categories'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'ledger_type', 'destination')
    id: str
    name: str
    ledger_type: str|None
    destination: str
    accounts: RelatedCollection

    @property
    def ledger_type(self) -> LedgerType|None:
        """The LedgerType that this AccountCategory applies to, if any."""
        return LedgerType(self.data['ledger_type']) if self.data['ledger_type'] else None
    @ledger_type.setter
    def ledger_type(self, value: LedgerType) -> None:
        if not isinstance(value, LedgerType):
            raise ValueError(f'Expected LedgerType, got {type(value)}')
        self.data['ledger_type'] = value.value

    @classmethod
    def _encode(cls, data: dict) -> dict:
        """Encode AccountCategory data without modifying the original dict."""
        if type(data) is not dict:
            return data
        data = {**data}
        if type(data.get('ledger_type', None)) is LedgerType:
            data['ledger_type'] = data['ledger_type'].value
        return data

    @classmethod
    def insert(cls, data: dict, /, *, suppress_events: bool = False) -> AccountCategory|None:
        """Ensure data is encoded before inserting."""
        return super().insert(cls._encode(data), suppress_events=suppress_events)

    @classmethod
    def insert_many(cls, items: list[dict], /, *, suppress_events: bool = False) -> int:
        """Ensure items are encoded before inserting."""
        items = [cls._encode(item) for item in items]
        return super().insert_many(items, suppress_events=suppress_events)

    def update(self, updates: dict, /, *, suppress_events: bool = False) -> AccountCategory:
        """Ensure updates are encoded before updating."""
        updates = self._encode(updates)
        return super().update(updates, suppress_events=suppress_events)

    @classmethod
    def query(cls, conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:
        """Ensure conditions are encoded before querying."""
        if conditions and 'ledger_type' in conditions and isinstance(conditions['ledger_type'], LedgerType):
            conditions['ledger_type'] = conditions['ledger_type'].value
        return super().query(conditions, connection_info)

from sqloquent import HashedModel, RelatedCollection


class Transaction(HashedModel):
    connection_info: str = ''
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'entry_ids', 'ledger_ids', 'timestamp', 'details')
    id: str
    entry_ids: str
    ledger_ids: str
    timestamp: str
    details: str|None
    entries: RelatedCollection
    ledgers: RelatedCollection

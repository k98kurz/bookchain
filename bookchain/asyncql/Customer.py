from sqloquent.asyncql import AsyncHashedModel


class Customer(AsyncHashedModel):
    connection_info: str = ''
    table: str = 'customers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'code', 'details')
    id: str
    name: str
    code: str|None
    details: str|None

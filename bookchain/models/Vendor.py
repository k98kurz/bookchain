from sqloquent import HashedModel


class Vendor(HashedModel):
    connection_info: str = ''
    table: str = 'vendors'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'code', 'details')
    id: str
    name: str
    code: str|None
    details: str|None


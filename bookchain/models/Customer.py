from sqloquent import HashedModel


class Customer(HashedModel):
    connection_info: str = ''
    table: str = 'customers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'code', 'details', 'description')
    columns_excluded_from_hash: tuple[str] = ('description',)
    id: str
    name: str
    code: str|None
    details: str|None
    description: str|None

    # override automatic property
    @property
    def details(self) -> str|None:
        """A string stored in the database as text. Note that this will
            be changed to a packify.SerializableType stored as a blob in
            0.4.0.
        """
        return self.data.get('details', None)
    @details.setter
    def details(self, val: str|None):
        self.data['details'] = val

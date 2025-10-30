from sqloquent import HashedModel
import packify


_empty_dict = packify.pack({})


class Vendor(HashedModel):
    connection_info: str = ''
    table: str = 'vendors'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'code', 'details', 'description')
    columns_excluded_from_hash: tuple[str] = ('description',)
    id: str
    name: str
    code: str|None
    details: bytes|None
    description: str|None

    # override automatic property
    @property
    def details(self) -> packify.SerializableType:
        """A packify.SerializableType stored in the database as a blob."""
        return packify.unpack(self.data.get('details', _empty_dict))
    @details.setter
    def details(self, val: packify.SerializableType):
        self.data['details'] = packify.pack(val)

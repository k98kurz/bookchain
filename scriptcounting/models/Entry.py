from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol
from .EntryType import EntryType
from typing import Callable
import packify


class Entry(HashedModel):
    connection_info: str = ''
    table: str = 'entries'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'type', 'amount', 'nonce', 'account_id', 'details')
    id: str
    type: str
    amount: int
    nonce: bytes
    account_id: str
    details: bytes
    account: RelatedModel
    transactions: RelatedCollection

    def __hash__(self) -> int:
        data = self.encode_value(self.encode(self.data))
        return hash(bytes(data, 'utf-8'))

    # override automatic properties
    @property
    def type(self) -> EntryType:
        return EntryType(self.data['type'])
    @type.setter
    def type(self, val: EntryType):
        if type(val) is not EntryType:
            return
        self.data['type'] = val.value

    @property
    def details(self) -> packify.SerializableType:
        return packify.unpack(self.data.get('details', b'n\x00\x00\x00\x00'))
    @details.setter
    def details(self, val: packify.SerializableType):
        self.data['details'] = packify.pack(val)

    @staticmethod
    def encode(data: dict|None) -> dict|None:
        if type(data) is not dict:
            return data
        if type(data.get('type', None)) is EntryType:
            data['type'] = data['type'].value
        if type(data.get('details', {})) is not bytes:
            data['details'] = packify.pack(data.get('details', None))
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is dict and type(data['amount']) is str:
            data['amount'] = int(data['amount'])
        return data

    @staticmethod
    def parse(models: Entry|list[Entry]) -> Entry|list[Entry]:
        if type(models) is list:
            for model in models:
                model.data = Entry._parse(model.data)
        else:
            models.data = Entry._parse(models.data)
        return models

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate an id by hashing the non-id contents. Raises
            TypeError for unencodable type (calls packify.pack).
        """
        return super().generate_id(cls.encode({**data}))

    @classmethod
    def insert(cls, data: dict) -> Entry | None:
        result = super().insert(cls.encode(data))
        if result is not None:
            result.data = cls._parse(result.data)
        return result

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        items = [Entry.encode(data) for data in list]
        return super().insert_many(items)

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        return super().query(cls.encode(conditions))

    @classmethod
    def set_sigfield_plugin(cls, plugin: Callable):
        cls._plugin = plugin

    def get_sigfields(self, *args, **kwargs) -> dict[str, bytes]:
        """Get the sigfields for tapescript authorization."""
        if hasattr(self, '_plugin') and callable(self._plugin):
            return self._plugin(self, *args, **kwargs)
        return {'sigfield1': bytes.fromhex(self.generate_id(self.data))}

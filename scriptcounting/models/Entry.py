from __future__ import annotations
from sqloquent import HashedModel, RelatedModel, RelatedCollection, QueryBuilderProtocol
from .EntryType import EntryType
import packify


class Entry(HashedModel):
    connection_info: str = ''
    table: str = 'entries'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'type', 'amount', 'nonce', 'account_id', 'details')
    id: str
    type: EntryType
    amount: int
    nonce: str
    account_id: str
    details: packify.SerializableType
    account: RelatedModel
    transactions: RelatedCollection

    def __hash__(self) -> int:
        data = self.encode_value(self.encode(self.data))
        return hash(bytes(data, 'utf-8'))

    @staticmethod
    def encode(data: dict|None) -> dict|None:
        if type(data) is not dict:
            return data
        if type(data['type']) is EntryType:
            data['type'] = data['type'].value
        data['details'] = packify.pack(data['details'])
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is dict and type(data['type']) is str:
            data['type'] = EntryType(data['type'])
        if type(data) is dict and type(data['amount']) is str:
            data['amount'] = int(data['amount'])
        if type(data['details']) is bytes:
            data['details'] = packify.unpack(data['details'])
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
    def generate_id(cls, data: dict) -> bytes:
        """Generate an id by hashing the non-id contents. Raises
            TypeError for unencodable type (calls packify.pack).
        """
        return super().generate_id(cls.encode(data))

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


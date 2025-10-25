from __future__ import annotations
from sqloquent.asyncql import (
    AsyncHashedModel, AsyncRelatedModel, AsyncRelatedCollection, AsyncQueryBuilderProtocol
)
from .ArchivedEntry import ArchivedEntry
from .EntryType import EntryType
from typing import Callable
import packify


_empty_dict = packify.pack({})


class Entry(AsyncHashedModel):
    connection_info: str = ''
    table: str = 'entries'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'type', 'amount', 'nonce', 'account_id', 'details', 'description'
    )
    columns_excluded_from_hash: tuple[str] = ('description',)
    id: str
    type: str
    amount: int
    nonce: bytes
    account_id: str
    details: bytes
    description: str|None
    account: AsyncRelatedModel
    transactions: AsyncRelatedCollection

    def __hash__(self) -> int:
        data = self.encode_value(self._encode(self.data))
        return hash(bytes(data, 'utf-8'))

    # override automatic properties
    @property
    def type(self) -> EntryType:
        """The EntryType of the Entry."""
        return EntryType(self.data['type'])
    @type.setter
    def type(self, val: EntryType):
        if type(val) is not EntryType:
            return
        self.data['type'] = val.value

    @property
    def details(self) -> packify.SerializableType:
        """A packify.SerializableType stored in the database as a blob."""
        return packify.unpack(self.data.get('details', _empty_dict))
    @details.setter
    def details(self, val: packify.SerializableType):
        self.data['details'] = packify.pack(val)

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is not dict:
            return data
        if type(data.get('type', None)) is EntryType:
            data['type'] = data['type'].value
        if type(data.get('details', {})) is not bytes:
            data['details'] = packify.pack(data.get('details', None))
        return data

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate an id by hashing the non-id contents. Raises
            TypeError for unencodable type (calls packify.pack).
        """
        return super().generate_id(cls._encode({**data}))

    @classmethod
    async def insert(cls, data: dict) -> Entry | None:
        """Ensure data is encoded before inserting."""
        result = await super().insert(cls._encode(data))
        return result

    @classmethod
    async def insert_many(cls, items: list[dict]) -> int:
        """Ensure data is encoded before inserting."""
        items = [cls._encode(data) for data in list]
        return await super().insert_many(items)

    @classmethod
    def query(cls, conditions: dict = None) -> AsyncQueryBuilderProtocol:
        """Ensure conditions are encoded properly before querying."""
        return super().query(cls._encode(conditions))

    @classmethod
    def set_sigfield_plugin(cls, plugin: Callable):
        """Sets the plugin function used by self.get_sigfields that
            parses the Entry to extract the correct sigfields for
            tapescript authorization. This is an optional override.
        """
        cls._plugin = plugin

    def get_sigfields(self, *args, **kwargs) -> dict[str, bytes]:
        """Get the sigfields for tapescript authorization. By default,
            it returns {sigfield1: self.generate_id()} because the ID
            cryptographically commits to all record data. If the
            set_sigfield_plugin method was previously called, this will
            instead return the result of calling the plugin function.
        """
        if hasattr(self, '_plugin') and callable(self._plugin):
            return self._plugin(self, *args, **kwargs)
        return {'sigfield1': bytes.fromhex(self.generate_id({**self.data}))}

    async def archive(self) -> ArchivedEntry|None:
        """Archive the Entry. If it has already been archived,
            return the existing ArchivedEntry.
        """
        archived_entry_id = ArchivedEntry.generate_id({**self.data})
        try:
            return await ArchivedEntry.insert({**self.data})
        except Exception as e:
            return await ArchivedEntry.find(archived_entry_id)

from __future__ import annotations
from sqloquent import HashedModel, RelatedCollection
from sqloquent.classes import SqlModel
from sqloquent.errors import vert


class Identity(HashedModel):
    connection_info: str = ''
    table: str = 'identities'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'details', 'pubkey', 'seed', 'secret_details')
    columns_excluded_from_hash: tuple[str] = ('seed', 'secret_details')
    id: str
    name: str
    details: bytes
    pubkey: bytes|None
    seed: bytes|None
    secret_details: bytes|None
    ledgers: RelatedCollection
    correspondences: RelatedCollection

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate an ID that does not commit to the columns that
            should be excluded from the cryptographic commitment.
        """
        return super().generate_id({
            k:v for k,v in data.items()
            if k not in cls.columns_excluded_from_hash
        })

    def public(self) -> dict:
        """Return the public data for cloning the Identity."""
        return {
            k:v for k,v in self.data.items()
            if k not in self.columns_excluded_from_hash
        }

    def update(self, updates: dict, conditions: dict = None) -> Identity:
        """Unlike an ordinary HashedModel, there are two columns on an
            Identity that are not hashed, meaning they can be updated
            without changing the ID. This is mainly for convenience so
            that secret values can be saved locally without requiring
            their dissemination to synchronize Identities within a
            correspondent system.
        """
        # merge data into updates
        for key in self.data:
            if key in self.columns and not key in updates:
                updates[key] = self.data[key]

        for key in updates:
            vert(key in self.columns, f'unrecognized column: {key}')

        if self.generate_id(updates) != self.id:
            return super().update(updates)

        # parse conditions
        conditions = conditions if conditions is not None else {}
        if self.id_column in self.data and self.id_column not in conditions:
            conditions[self.id_column] = self.data[self.id_column]

        # run update query
        self.query().update(updates, conditions)

        return self

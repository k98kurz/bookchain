from __future__ import annotations
from sqloquent import HashedModel, RelatedCollection


class Correspondence(HashedModel):
    table: str = 'correspondences'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'identity_ids', 'details')
    id: str
    identity_ids: str
    details: str
    identities: RelatedCollection

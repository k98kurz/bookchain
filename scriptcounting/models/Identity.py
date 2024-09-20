from sqloquent import HashedModel, RelatedCollection


class Identity(HashedModel):
    connection_info: str = ''
    table: str = 'identities'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'details', 'pubkey', 'seed')
    id: str
    name: str
    details: bytes
    pubkey: bytes|None
    seed: bytes|None
    ledgers: RelatedCollection
    correspondences: RelatedCollection

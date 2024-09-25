from __future__ import annotations
from .Account import Account
from .Identity import Identity
from sqloquent import HashedModel, RelatedCollection


class Correspondence(HashedModel):
    table: str = 'correspondences'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'identity_ids', 'details', 'account_ids')
    id: str
    identity_ids: str
    details: str
    identities: RelatedCollection

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Override generate_id to exclude account_ids."""
        return super().generate_id({
            k:v for k,v in data.items()
            if k != 'account_ids'
        })

    def get_accounts(self) -> list[Account]:
        accounts = {}
        self.identities().reload()
        id1: Identity = self.identities[0]
        for identity in self.identities:
            if identity is id1:
                continue
            identity: Identity
            for acct in id1.get_correspondent_accounts(identity):
                acct.ledger().reload()
                accounts[acct.id] = acct
        acct_ids = set([aid for aid in accounts])
        return [accounts[i] for i in acct_ids]

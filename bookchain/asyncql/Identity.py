from __future__ import annotations
from .Account import Account, AccountType
from .Ledger import Ledger
from sqloquent.asyncql import AsyncHashedModel, AsyncRelatedCollection
from sqloquent.errors import vert


class Identity(AsyncHashedModel):
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
    ledgers: AsyncRelatedCollection
    correspondences: AsyncRelatedCollection

    def public(self) -> dict:
        """Return the public data for cloning the Identity."""
        return {
            k:v for k,v in self.data.items()
            if k not in self.columns_excluded_from_hash
        }

    async def correspondents(self, reload: bool = False) -> list[Identity]:
        """Get the correspondents for this Identity."""
        if reload:
            await self.correspondences().reload()

        correspondents = []
        for correspondence in self.correspondences:
            if reload:
                await correspondence.identities().reload()
            for identity in correspondence.identities:
                if identity.id != self.id:
                    correspondents.append(identity)
        return correspondents

    async def get_correspondent_accounts(self, correspondent: Identity) -> list[Account]:
        """Get the nosto and vostro accounts for a correspondent."""
        accounts = []
        ledger: Ledger
        for ledger in await Ledger.query().get():
            nostros = await Account.query({
                'ledger_id': ledger.id,
                'type': AccountType.NOSTRO_ASSET.value,
            }).contains('name', correspondent.id).get()
            if len(nostros):
                accounts.extend(nostros)
            vostros = await Account.query({
                'ledger_id': ledger.id,
                'type': AccountType.VOSTRO_LIABILITY.value,
            }).contains('name', correspondent.id).get()
            if len(vostros):
                accounts.extend(vostros)
            nostros = await Account.query({
                'ledger_id': ledger.id,
                'type': AccountType.NOSTRO_ASSET.value,
            }).contains('name', self.id).get()
            if len(nostros):
                accounts.extend(nostros)
            vostros = await Account.query({
                'ledger_id': ledger.id,
                'type': AccountType.VOSTRO_LIABILITY.value,
            }).contains('name', self.id).get()
            if len(vostros):
                accounts.extend(vostros)
        return accounts

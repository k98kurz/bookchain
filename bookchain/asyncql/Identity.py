from __future__ import annotations
from .Account import Account, AccountType
from .Ledger import Ledger
from sqloquent.asyncql import AsyncHashedModel, AsyncRelatedCollection
import packify


_empty_dict = packify.pack({})


class Identity(AsyncHashedModel):
    connection_info: str = ''
    table: str = 'identities'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'details', 'pubkey', 'seed', 'secret_details', 'description'
    )
    columns_excluded_from_hash: tuple[str] = ('seed', 'secret_details', 'description')
    id: str
    name: str
    details: bytes
    pubkey: bytes|None
    seed: bytes|None
    secret_details: bytes|None
    description: str|None
    ledgers: AsyncRelatedCollection
    correspondences: AsyncRelatedCollection

    # override automatic property
    @property
    def details(self) -> packify.SerializableType:
        """A packify.SerializableType stored in the database as a blob."""
        return packify.unpack(self.data.get('details', _empty_dict))
    @details.setter
    def details(self, val: packify.SerializableType):
        self.data['details'] = packify.pack(val)

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

    async def get_correspondent_accounts(
            self, correspondent: Identity, reload: bool = False
        ) -> list[Account]:
        """Get the nosto and vostro accounts for a correspondent."""
        if reload:
            await self.correspondences().reload()

        accounts = []
        correspondence = [
            c for c in self.correspondences if correspondent.id in c.identity_ids
        ][0]
        for _, accts in (await correspondence.get_accounts(reload=reload)).items():
            for acct_type, acct in accts.items():
                if acct_type is AccountType.NOSTRO_ASSET:
                    accounts.append(acct)
                if acct_type is AccountType.VOSTRO_LIABILITY:
                    accounts.append(acct)

        return accounts

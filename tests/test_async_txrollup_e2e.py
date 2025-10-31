from asyncio import run
from context import asyncql
from genericpath import isfile
from nacl.signing import SigningKey
from packify import pack, unpack
from time import time
import os
import sqloquent.asyncql
import sqloquent.tools
import tapescript
import unittest


DB_FILEPATH = 'tests/test.db'
MIGRATIONS_PATH = 'tests/migrations'
MODELS_PATH = 'bookchain/models'


class TestTxRollupE2E(unittest.TestCase):
    @classmethod
    def automigrate(cls):
        sqloquent.tools.publish_migrations(MIGRATIONS_PATH)
        tomigrate = [
            asyncql.Identity, asyncql.Currency, asyncql.Ledger,
            asyncql.Account, asyncql.Entry, asyncql.Transaction,
            asyncql.Correspondence, asyncql.TxRollup,
            asyncql.ArchivedTransaction, asyncql.ArchivedEntry
        ]
        for model in tomigrate:
            name = model.__name__
            m = sqloquent.tools.make_migration_from_model(model, name)
            with open(f'{MIGRATIONS_PATH}/create_{name}.py', 'w') as f:
                f.write(m)
        sqloquent.tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)

    @classmethod
    def setUpClass(cls):
        asyncql.Identity.connection_info = DB_FILEPATH
        asyncql.Currency.connection_info = DB_FILEPATH
        asyncql.Correspondence.connection_info = DB_FILEPATH
        asyncql.Ledger.connection_info = DB_FILEPATH
        asyncql.Account.connection_info = DB_FILEPATH
        asyncql.Entry.connection_info = DB_FILEPATH
        asyncql.Transaction.connection_info = DB_FILEPATH
        asyncql.TxRollup.connection_info = DB_FILEPATH
        asyncql.ArchivedTransaction.connection_info = DB_FILEPATH
        asyncql.ArchivedEntry.connection_info = DB_FILEPATH
        sqloquent.asyncql.AsyncDeletedModel.connection_info = DB_FILEPATH
        cls.automigrate()
        super().setUpClass()

    def setUp(self):
        run(asyncql.Identity.query().delete())
        run(asyncql.Currency.query().delete())
        run(asyncql.Correspondence.query().delete())
        run(asyncql.Ledger.query().delete())
        run(asyncql.Account.query().delete())
        run(asyncql.Entry.query().delete())
        run(asyncql.Transaction.query().delete())
        run(asyncql.TxRollup.query().delete())
        run(asyncql.ArchivedTransaction.query().delete())
        run(asyncql.ArchivedEntry.query().delete())
        run(sqloquent.asyncql.AsyncDeletedModel.query().delete())
        self.setup_cryptographic_values()
        super().setUp()

    def tearDown(self):
        for file in os.listdir(MIGRATIONS_PATH):
            if isfile(f'{MIGRATIONS_PATH}/{file}'):
                os.remove(f'{MIGRATIONS_PATH}/{file}')
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        if isfile(DB_FILEPATH):
            os.remove(DB_FILEPATH)
        return super().tearDownClass()

    def setup_cryptographic_values(self):
        self.seed_alice = os.urandom(32)
        self.seed_bob = os.urandom(32)
        self.pkey_alice = bytes(SigningKey(self.seed_alice).verify_key)
        self.pkey_bob = bytes(SigningKey(self.seed_bob).verify_key)
        self.committed_script_alice = tapescript.tools.make_delegate_key_lock(self.pkey_alice)
        self.committed_script_bob = tapescript.tools.make_delegate_key_lock(self.pkey_bob)
        self.locking_script_alice = tapescript.tools.make_taproot_lock(
            self.pkey_alice,
            self.committed_script_alice
        ).bytes
        self.locking_script_bob = tapescript.tools.make_taproot_lock(
            self.pkey_bob,
            self.committed_script_bob
        ).bytes
        self.delegate_seed = os.urandom(32) # for simplicity, both will have the same delegate
        self.delegate_pkey = bytes(SigningKey(self.delegate_seed).verify_key)
        begin_ts = int(time()) - 1
        end_ts = int(time()) + 60*60*24*365
        self.delegate_cert_alice = tapescript.make_delegate_key_cert(
            self.seed_alice, self.delegate_pkey, begin_ts, end_ts
        )
        self.delegate_cert_bob = tapescript.make_delegate_key_cert(
            self.seed_bob, self.delegate_pkey, begin_ts, end_ts
        )
        self.multisig_lock = tapescript.tools.make_multisig_lock(
            [self.pkey_alice, self.pkey_bob], 2
        ).bytes

    async def setup_currency(self) -> asyncql.Currency:
        # set up currency
        self.currency = await asyncql.Currency.insert({
            'name': 'Median Human Hour',
            'prefix_symbol': 'Ħ',
            'fx_symbol': 'MHH',
            'base': 60,
            'unit_divisions': 2,
            'details': 'Abstract value of one median hour of human time. ' +
                '1 Hour = 60 Minutes = 3600 Seconds',
        })
        return self.currency

    async def setup_identities(self) -> tuple[asyncql.Identity, asyncql.Identity]:
        # set up alice, ledger_alice, accounts, and starting capital transaction
        alice: asyncql.Identity = await asyncql.Identity.insert({
            'name': 'Alice',
            'pubkey': self.pkey_alice,
            'seed': self.seed_alice,
        })
        ledger_alice = await asyncql.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': alice.id,
            'currency_id': self.currency.id,
        })
        asset_acct_alice, liability_acct_alice, equity_acct_alice = ledger_alice.setup_basic_accounts()

        equity_acct_alice.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_alice
        }
        await equity_acct_alice.save()

        asset_acct_alice.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_alice
        }
        await asset_acct_alice.save()

        liability_acct_alice.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_alice,
            asyncql.EntryType.CREDIT: self.locking_script_alice,
        }
        await liability_acct_alice.save()

        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_alice
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct_alice.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_alice
        txn = await asyncql.Transaction.prepare([equity_entry, asset_entry], str(time()))
        await equity_entry.save()
        await asset_entry.save()
        await txn.save()

        # set up bob, ledger_bob, and some accounts
        bob: asyncql.Identity = await asyncql.Identity.insert({
            'name': 'Bob',
            'pubkey': self.pkey_bob,
            'seed': self.seed_bob,
        })
        ledger_bob = await asyncql.Ledger.insert({
            'name': 'Current Ledger',
            'identity_id': bob.id,
            'currency_id': self.currency.id,
        })
        asset_acct_bob, liability_acct_bob, equity_acct_bob = ledger_bob.setup_basic_accounts()
        equity_acct_bob.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_bob
        }
        await equity_acct_bob.save()
        asset_acct_bob.locking_scripts = {
            asyncql.EntryType.CREDIT: self.locking_script_bob
        }
        await asset_acct_bob.save()
        liability_acct_bob.locking_scripts = {
            asyncql.EntryType.DEBIT: self.locking_script_bob,
            asyncql.EntryType.CREDIT: self.locking_script_bob,
        }
        await liability_acct_bob.save()

        # fund the Identity with starting capital
        nonce = os.urandom(16)
        equity_entry = asyncql.Entry({
            'type': asyncql.EntryType.CREDIT,
            'account_id': equity_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        equity_entry.account = equity_acct_bob
        asset_entry = asyncql.Entry({
            'type': asyncql.EntryType.DEBIT,
            'account_id': asset_acct_bob.id,
            'amount': 2_000 * 60*60, # 2000 hours = 50 weeks * 40 hours/week
            'nonce': nonce,
        })
        asset_entry.account = asset_acct_bob
        txn = await asyncql.Transaction.prepare([equity_entry, asset_entry], str(time()))
        await equity_entry.save()
        await asset_entry.save()
        await txn.save()

        return alice, bob

    async def setup_correspondence(self) -> asyncql.Correspondence:
        alice: asyncql.Identity = await asyncql.Identity.query().equal(name='Alice').first()
        bob: asyncql.Identity = await asyncql.Identity.query().equal(name='Bob').first()
        ledger_alice: asyncql.Ledger = await asyncql.Ledger.query().equal(identity_id=alice.id).first()
        ledger_bob: asyncql.Ledger = await asyncql.Ledger.query().equal(identity_id=bob.id).first()

        # set up Correspondence
        assert await alice.correspondences().query().count() == 0
        assert len(await alice.correspondents(reload=True)) == 0
        correspondence: asyncql.Correspondence = await asyncql.Correspondence.insert({
            'identity_ids': ','.join(sorted([alice.id, bob.id])),
            'ledger_ids': ','.join(sorted([ledger_alice.id, ledger_bob.id])),
            'details': pack({
                'starting_capital': 'Ħ2000',
                'limits': {
                    alice.id: 'Ħ166 M40',
                    bob.id: 'Ħ166 M40',
                },
                'locking_scripts': {
                    alice.id: self.locking_script_alice,
                    bob.id: self.locking_script_bob,
                },
            })
        })
        assert await alice.correspondences().query().count() == 1
        assert len(await alice.correspondents(reload=True)) == 1
        assert (await alice.correspondents(reload=True))[0].id == bob.id
        assert await bob.correspondences().query().count() == 1
        assert len(await bob.correspondents(reload=True)) == 1
        assert (await bob.correspondents(reload=True))[0].id == alice.id

        # set up correspondence accounts
        cor_accts = await correspondence.setup_accounts({
            alice.id: self.locking_script_alice,
            bob.id: self.locking_script_bob,
        })
        for _, acct in cor_accts[alice.id].items():
            await acct.save()
        for _, acct in cor_accts[bob.id].items():
            await acct.save()

        return correspondence

    async def create_txn(self, acct1: asyncql.Account, acct2: asyncql.Account, amount: int) -> asyncql.Transaction:
        nonce = os.urandom(16)
        entries = [
            asyncql.Entry({
                'type': asyncql.EntryType.DEBIT,
                'account_id': acct1.id,
                'amount': amount,
                'nonce': nonce,
            }),
            asyncql.Entry({
                'type': asyncql.EntryType.CREDIT,
                'account_id': acct2.id,
                'amount': amount,
                'nonce': nonce,
            }),
        ]
        txn = await asyncql.Transaction.prepare(entries, str(time()))
        await txn.save()
        return txn

    def test_simple_e2e(self):
        run(self.setup_currency())
        alice, _ = run(self.setup_identities())
        ledger: asyncql.Ledger = alice.ledgers[0]

        asset_acct: asyncql.Account = [acct for acct in ledger.accounts if acct.type == asyncql.AccountType.ASSET][0]
        equity_acct: asyncql.Account = [acct for acct in ledger.accounts if acct.type == asyncql.AccountType.EQUITY][0]
        asset_starting_balance = run(asset_acct.balance())
        equity_starting_balance = run(equity_acct.balance())

        # create txns: Alice adds assets to her ledger
        txn1 = run(self.create_txn(asset_acct, equity_acct, 100))
        txn2 = run(self.create_txn(asset_acct, equity_acct, 200))

        # ensure the balances are correct
        assert run(asset_acct.balance()) == asset_starting_balance + 300, \
            f'{run(asset_acct.balance())} != {asset_starting_balance} + 300'
        assert run(equity_acct.balance()) == equity_starting_balance + 300, \
            f'{run(equity_acct.balance())} != {equity_starting_balance} + 300'

        # test empty txrollup
        txrollup = asyncql.TxRollup()
        txrollup.balances
        txrollup.tx_ids

        # create a txrollup
        txrollup = run(asyncql.TxRollup.prepare([txn1, txn2]))
        assert run(txrollup.validate())
        run(txrollup.save())

        # prove inclusion of txn
        proof = txrollup.prove_txn_inclusion(txn1.id)
        assert txrollup.verify_txn_inclusion_proof(txn1.id, proof)
        proof = txrollup.prove_txn_inclusion(txn2.id)
        assert txrollup.verify_txn_inclusion_proof(txn2.id, proof)

        # test empty ArchivedTransaction and ArchivedEntry

        (asyncql.ArchivedTransaction()).details
        (asyncql.ArchivedTransaction()).auth_scripts
        (asyncql.ArchivedEntry()).details

        # archive and trim txn and entries
        assert run(txrollup.trim()) == 2
        assert run(txrollup.archived_transactions().count()) == 2, run(txrollup.archived_transactions().count())
        assert run(run(txrollup.archived_entries()).count()) == 4, run(run(txrollup.archived_entries()).count())

        # ensure the txn has been trimmed
        assert run(txrollup.trimmed_transactions().count()) == 2
        assert run(run(txrollup.trimmed_entries()).count()) == 4
        assert run(asyncql.Transaction.query().is_in('id', txrollup.tx_ids).count()) == 0
        entry_ids = [e.id for e in txn1.entries] + [e.id for e in txn2.entries]
        assert run(asyncql.Entry.query().is_in('id', entry_ids).count()) == 0

        # ensure the balances are correct
        assert run(asset_acct.balance()) == asset_starting_balance # without rolled up balances
        assert run(asset_acct.balance(rolled_up_balances=txrollup.balances)) == asset_starting_balance + 300, \
            f'{run(asset_acct.balance(rolled_up_balances=txrollup.balances))} != {asset_starting_balance} + 300'
        assert run(equity_acct.balance()) == equity_starting_balance # without rolled up balances
        assert run(equity_acct.balance(rolled_up_balances=txrollup.balances)) == equity_starting_balance + 300, \
            f'{run(equity_acct.balance(rolled_up_balances=txrollup.balances))} != {equity_starting_balance} + 300'

        # mirror the txrollup's public data
        public_data = txrollup.public()
        mirrored = asyncql.TxRollup(public_data)
        assert run(mirrored.validate())
        # inclusion proofs should be verified by mirrored TxRollup
        proof = txrollup.prove_txn_inclusion(txn2.id)
        assert mirrored.verify_txn_inclusion_proof(txn2.id, proof)

        # create more txns and txrollups
        txn3 = run(self.create_txn(asset_acct, equity_acct, 10))
        txn4 = run(self.create_txn(asset_acct, equity_acct, 20))
        txrollup2 = run(asyncql.TxRollup.prepare([txn3, txn4], txrollup.id))
        assert run(txrollup2.validate())
        run(txrollup2.save())

        # attempt to create a competing txrollup chain
        with self.assertRaises(ValueError) as e:
            run(asyncql.TxRollup.prepare([txn3, txn4]))
        assert str(e.exception) == 'the given ledger already has a TxRollup chain'

        # prove inclusion of txn
        proof = txrollup2.prove_txn_inclusion(txn3.id)
        assert txrollup2.verify_txn_inclusion_proof(txn3.id, proof)
        proof = txrollup2.prove_txn_inclusion(txn4.id)
        assert txrollup2.verify_txn_inclusion_proof(txn4.id, proof)

        # archive and trim txn and entries
        assert run(txrollup2.trim()) == 2
        assert run(txrollup2.archived_transactions().count()) == 2, run(txrollup2.archived_transactions().count())
        assert run(run(txrollup2.archived_entries()).count()) == 4, run(run(txrollup2.archived_entries()).count())

        # ensure the balances are correct
        assert run(asset_acct.balance(rolled_up_balances=txrollup2.balances)) == asset_starting_balance + 330, \
            f'{run(asset_acct.balance(rolled_up_balances=txrollup2.balances))} != {asset_starting_balance} + 330'
        assert run(equity_acct.balance(rolled_up_balances=txrollup2.balances)) == equity_starting_balance + 330, \
            f'{run(equity_acct.balance(rolled_up_balances=txrollup2.balances))} != {equity_starting_balance} + 330'

        # check relations
        assert len(ledger.rollups) == 2
        assert txrollup.id in [r.id for r in ledger.rollups]
        assert txrollup2.id in [r.id for r in ledger.rollups]
        assert txrollup.ledger.id == ledger.id
        assert txrollup2.ledger.id == ledger.id
        assert len(ledger.archived_transactions) == 4
        archived_txn: asyncql.ArchivedTransaction = ledger.archived_transactions[0]
        assert len(archived_txn.entries) == 2
        archived_entry: asyncql.ArchivedEntry = archived_txn.entries[0]
        assert len(archived_entry.transactions) == 1
        assert archived_entry.transactions[0].id == archived_txn.id
        assert len(asset_acct.archived_entries) == 4

        # make some more txns
        txn5 = run(self.create_txn(asset_acct, equity_acct, 100))
        txn6 = run(self.create_txn(asset_acct, equity_acct, 200))

        # try to add a second child txrollup to the same parent
        with self.assertRaises(ValueError) as e:
            run(asyncql.TxRollup.prepare([txn5, txn6], txrollup.id))
        assert str(e.exception) == 'parent already has a child'
        # fake it
        txrollup3 = run(asyncql.TxRollup.prepare([txn5, txn6], txrollup2.id))
        txrollup3.parent_id = txrollup.id
        txrollup3.height = txrollup.height + 1
        txrollup3.balances = run(asyncql.TxRollup.calculate_balances([txn5, txn6], txrollup.balances))
        assert not run(txrollup3.validate())
        # reset the parent_id and height to attempt to make a competing chain
        txrollup3.parent_id = None
        txrollup3.height = 0
        txrollup3.balances = run(asyncql.TxRollup.calculate_balances([txn5, txn6]))
        assert not run(txrollup3.validate())

        # prepare a txrollup with just one txn
        txrollup3 = run(asyncql.TxRollup.prepare([txn5], txrollup2.id))
        assert run(txrollup3.validate())

        # prepare an empty txrollup
        txrollup3 = run(asyncql.TxRollup.prepare([], txrollup2.id, ledger=ledger))
        assert run(txrollup3.validate())

    def test_with_correspondence_e2e(self):
        run(self.setup_currency())
        alice, bob = run(self.setup_identities())
        correspondence = run(self.setup_correspondence())

        cor_accts = run(correspondence.get_accounts())
        nostro_acct_alice = cor_accts[alice.id][asyncql.AccountType.NOSTRO_ASSET]
        vostro_acct_alice = cor_accts[alice.id][asyncql.AccountType.VOSTRO_LIABILITY]
        equity_acct_alice = cor_accts[alice.id][asyncql.AccountType.EQUITY]
        nostro_acct_bob = cor_accts[bob.id][asyncql.AccountType.NOSTRO_ASSET]
        vostro_acct_bob = cor_accts[bob.id][asyncql.AccountType.VOSTRO_LIABILITY]
        equity_acct_bob = cor_accts[bob.id][asyncql.AccountType.EQUITY]

        # create txn: Alice credits her ledger's vostro to pay Bob
        _, entries = run(correspondence.pay_correspondent(alice, bob, 200, os.urandom(16)))
        txn = run(asyncql.Transaction.prepare(entries, str(time()), auth_scripts={
            equity_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[0].get_sigfields(entries=entries), self.committed_script_alice
            ).bytes,
            vostro_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[2].get_sigfields(entries=entries), self.committed_script_alice
            ).bytes,
            nostro_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_alice, entries[3].get_sigfields(entries=entries), self.committed_script_alice
            ).bytes,
        }))
        run(txn.save())
        assert run(nostro_acct_bob.balance()) == 200
        assert run(vostro_acct_alice.balance()) == 200

        # create txn: Bob credits his ledger's nostro to pay Alice
        entries, _ = run(correspondence.pay_correspondent(bob, alice, 100, os.urandom(16)))
        txn2 = run(asyncql.Transaction.prepare(entries, str(time()), auth_scripts={
            equity_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_bob, entries[0].get_sigfields(entries=entries), self.committed_script_bob
            ).bytes,
            nostro_acct_bob.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_bob, entries[2].get_sigfields(entries=entries), self.committed_script_bob
            ).bytes,
            vostro_acct_alice.id: tapescript.tools.make_taproot_witness_keyspend(
                self.seed_bob, entries[3].get_sigfields(entries=entries), self.committed_script_bob
            ).bytes,
        }))
        run(txn2.save())
        assert run(nostro_acct_bob.balance()) == 100
        assert run(vostro_acct_alice.balance()) == 100

        # create a txrollup
        txrollup = run(asyncql.TxRollup.prepare([txn, txn2], correspondence=correspondence))
        assert run(txrollup.validate())
        run(txrollup.save())

        # prove inclusion of each txn
        proof = txrollup.prove_txn_inclusion(txn.id)
        assert txrollup.verify_txn_inclusion_proof(txn.id, proof)
        proof = txrollup.prove_txn_inclusion(txn2.id)
        assert txrollup.verify_txn_inclusion_proof(txn2.id, proof)

        # archive and trim txns and entries
        assert run(txrollup.trim()) == 2
        assert run(txrollup.archived_transactions().count()) == 2, run(txrollup.archived_transactions().count())
        assert run(run(txrollup.archived_entries()).count()) == 8, run(run(txrollup.archived_entries()).count())

        # ensure the txns have been trimmed
        assert run(txrollup.trimmed_transactions().count()) == 2
        assert run(run(txrollup.trimmed_entries()).count()) == 8
        assert run(asyncql.Transaction.query().is_in('id', txrollup.tx_ids).count()) == 0
        entry_ids = [e.id for e in txn.entries] + [e.id for e in txn2.entries]
        assert run(asyncql.Entry.query().is_in('id', entry_ids).count()) == 0

        # prove inclusion of each trimmed txn
        txns = [asyncql.Transaction(unpack(item.record)) for item in run(txrollup.trimmed_transactions().get())]
        for txn in txns:
            assert len(txn.id) > 0
            proof = txrollup.prove_txn_inclusion(txn.id)
            assert txrollup.verify_txn_inclusion_proof(txn.id, proof)

        # prove inclusion of each archived txn
        txns = run(txrollup.archived_transactions().get())
        for txn in txns:
            assert len(txn.id) > 0
            proof = txrollup.prove_txn_inclusion(txn.id)
            assert txrollup.verify_txn_inclusion_proof(txn.id, proof)

        # prove that the balances are correct when using rolled up balances
        assert run(nostro_acct_bob.balance()) == 0
        assert run(nostro_acct_bob.balance(rolled_up_balances=txrollup.balances)) == 100, \
            run(nostro_acct_bob.balance(rolled_up_balances=txrollup.balances))
        assert run(vostro_acct_alice.balance()) == 0
        assert run(vostro_acct_alice.balance(rolled_up_balances=txrollup.balances)) == 100, \
            run(vostro_acct_alice.balance(rolled_up_balances=txrollup.balances))
        balances = run(correspondence.balances())
        assert balances[alice.id] == 0, balances[alice.id]
        assert balances[bob.id] == 0, balances[bob.id]
        balances = run(correspondence.balances(rolled_up_balances=txrollup.balances))
        assert balances[alice.id] == -100, balances[alice.id]
        assert balances[bob.id] == 100, balances[bob.id]

        # check relations
        assert len(correspondence.rollups) == 1
        assert txrollup.id in [r.id for r in correspondence.rollups]
        assert txrollup.correspondence.id == correspondence.id


if __name__ == '__main__':
    unittest.main()

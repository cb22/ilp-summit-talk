import asyncio
from typing import Optional
import asyncpg
import time

from dataclasses import dataclass, astuple, field
from collections import defaultdict
from uuid import UUID, uuid4

from uuid6 import uuid6

@dataclass
class Account:
    id: UUID = field(default_factory=uuid6)
    debits_pending: int = 0
    debits_posted: int = 0
    credits_pending: int = 0
    credits_posted: int = 0
    user_data_128: bytes = b"\x00"*16
    user_data_64: bytes = b"\x00"*8
    user_data_32: bytes = b"\x00"*4
    ledger: int = 0
    code: int = 0
    flags: bytes = b"\x00"*2
    timestamp: int = field(default_factory=time.time)


@dataclass
class Transfer:
    id: UUID = field(default_factory=uuid6)
    debit_account_id: UUID = field(default_factory=uuid6)
    credit_account_id: UUID  = field(default_factory=uuid6)
    amount: int = 0
    pending_id: Optional[UUID] = None
    user_data_128: bytes = b"\x00"*16
    user_data_64: bytes = b"\x00"*8
    user_data_32: bytes = b"\x00"*4
    timeout: int = 0
    ledger: int = 0
    code: int = 0
    flags: bytes = b"\x00"*2
    timestamp: int = field(default_factory=time.time)


@dataclass
class AccountUpdate:
    debits_pending: int = 0
    debits_posted: int = 0
    credits_pending: int = 0
    credits_posted: int = 0

# This could use multi-row inserts, but we're not benchmarking it so no need.
async def create_accounts(conn, accounts):
    async with conn.transaction():
        for account in accounts:
            await conn.execute('''
                INSERT INTO accounts(id, debits_pending, debits_posted, credits_pending, credits_posted, user_data_128, user_data_64, user_data_32, ledger, code, flags, timestamp) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ''', *account)

async def create_transfers(conn, transfers):
    async with conn.transaction():
        account_updates = defaultdict(AccountUpdate)
        tuple_transfers = []
        for transfer in transfers:
            account_updates[transfer.credit_account_id].credits_posted += transfer.amount
            account_updates[transfer.debit_account_id].debits_posted += transfer.amount
            tuple_transfers.append(astuple(transfer))
            # TODO: Pending transfers are unsupported :)

        # Create the transfers. TODO: Benchmark this against executemany.
        await conn.copy_records_to_table('transfers', records=tuple_transfers)

        # Update the account balances.
        for id, account_update in account_updates.items():
            await conn.execute('''UPDATE accounts SET credits_posted = credits_posted + $1, debits_posted = debits_posted + $2 WHERE id = $3''', account_update.credits_posted, account_update.debits_posted, id)

        # print(account_updates)
            # await conn.execute('''
            #     INSERT INTO accounts(id, debits_pending, debits_posted, credits_pending, credits_posted, user_data_128, user_data_64, user_data_32, ledger, code, flags, timestamp) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            # ''', *account.values())

async def main():
    conn = await asyncpg.connect('postgresql://postgres@localhost/tigerbeetle')
    # accounts = [astuple(Account()) for i in range(0, 2)]
    # await create_accounts(conn, accounts)

    for i in range(0, 100):
        transfers = []
        for i in range(0,1024):
            transfers.extend([
                Transfer(debit_account_id=UUID("1ee733d0-6ce0-6db9-acdc-496f3d280584"), credit_account_id=UUID("1ee733d0-cae4-61e2-83ab-c80fcb2ec0cd"), amount=1000),
                Transfer(debit_account_id=UUID("1ee733d0-cae4-61e2-83ab-c80fcb2ec0cd"), credit_account_id=UUID("1ee733d0-6ce0-6db9-acdc-496f3d280584"), amount=1000)])

        start = time.monotonic()
        await create_transfers(conn, transfers)
        end = time.monotonic()

        print((end-start) * 1000)

    # # Select a row from the table.
    # row = await conn.fetchrow(
    #     'SELECT * FROM users WHERE name = $1', 'Bob')
    # # *row* now contains
    # # asyncpg.Record(id=1, name='Bob', dob=datetime.date(1984, 3, 1))

    # Close the connection.
    await conn.close()

asyncio.get_event_loop().run_until_complete(main())
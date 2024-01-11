import asyncio
from typing import Optional
import asyncpg
import time
import os
import sys

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
    user_data_128: bytes = b"\x00" * 16
    user_data_64: bytes = b"\x00" * 8
    user_data_32: bytes = b"\x00" * 4
    ledger: int = 0
    code: int = 0
    flags: bytes = b"\x00" * 2
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class Transfer:
    id: UUID = field(default_factory=uuid6)
    debit_account_id: UUID = field(default_factory=uuid6)
    credit_account_id: UUID = field(default_factory=uuid6)
    amount: int = 0
    pending_id: Optional[UUID] = None
    user_data_128: bytes = b"\x00" * 16
    user_data_64: bytes = b"\x00" * 8
    user_data_32: bytes = b"\x00" * 4
    timeout: int = 0
    ledger: int = 0
    code: int = 0
    flags: bytes = b"\x00" * 2
    timestamp: int = field(default_factory=lambda: int(time.time()))


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
            await conn.execute(
                """
                INSERT INTO accounts(id, debits_pending, debits_posted, credits_pending, credits_posted, user_data_128, user_data_64, user_data_32, ledger, code, flags, timestamp) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                *account,
            )


# Clear any existing entries
async def clear_database(conn):
    await conn.execute("TRUNCATE TABLE accounts, transfers")


transfer_target = None
transfer_count = 0
terminal_width = os.get_terminal_size()[0]
last_log = time.monotonic()

def log_progress(name, count):
    global transfer_target, transfer_count, last_log
    transfer_count += count

    if count == 1 and transfer_count != 1 and transfer_count % 512 != 0:
        last_log = time.monotonic()
        return

    delta_t = time.monotonic() - last_log

    tps = round(count / delta_t)
    info = f"{tps: 6} TPS, {transfer_count: 7}/{transfer_target}"

    progress = ""
    width_without_progress = len(f"{name}: {progress} {info}")
    width_for_progress = terminal_width - width_without_progress

    completed = ">" * round((width_for_progress - 2) * (transfer_count / transfer_target))
    progress = "|" + completed + " " * (width_for_progress - 2 - len(completed)) + "|"

    print(f"\n{name}: {progress} {info}", end="")
    last_log = time.monotonic()


# create_transfers_v3:
# * Batches balance updates fully on client side.
# * Uses copy_records_to_table for transfer inserts.
# * Batch size limited by feature set, can't support more complicated logic.
async def create_transfers_v3(conn, transfers):
    async with conn.transaction():
        account_updates = defaultdict(AccountUpdate)
        tuple_transfers = []
        for transfer in transfers:
            account_updates[
                transfer.credit_account_id
            ].credits_posted += transfer.amount
            account_updates[transfer.debit_account_id].debits_posted += transfer.amount
            tuple_transfers.append(astuple(transfer))

        # Create the transfers.
        await conn.copy_records_to_table("transfers", records=tuple_transfers)

        # Update the account balances.
        for id, account_update in account_updates.items():
            await conn.execute(
                """UPDATE accounts SET credits_posted = credits_posted + $1,
                                       debits_posted = debits_posted + $2
                                   WHERE id = $3""",
                account_update.credits_posted,
                account_update.debits_posted,
                id,
            )
    log_progress("create_transfers_v3", len(transfers))


# create_transfers_v2:
# * Batches balance update queries with executemany.
# * Uses copy_records_to_table for transfer inserts.
async def create_transfers_v2(conn, transfers):
    async with conn.transaction():
        tuple_transfers = []
        credit_updates = []
        debit_updates = []
        for transfer in transfers:
            tuple_transfers.append(astuple(transfer))
            credit_updates.append((transfer.amount, transfer.credit_account_id))
            debit_updates.append((transfer.amount, transfer.debit_account_id))

        await conn.executemany(
            """UPDATE accounts SET credits_posted = credits_posted + $1 WHERE id = $2""",
            credit_updates,
        )
        await conn.executemany(
            """UPDATE accounts SET debits_posted = debits_posted + $1 WHERE id = $2""",
            debit_updates,
        )

        # Create the transfers.
        await conn.copy_records_to_table("transfers", records=tuple_transfers)
    log_progress("create_transfers_v2", len(transfers))


# create_transfers_v1:
# * No balance update batches.
# * No transfer insert batching.
# * Not transactional :).
async def create_transfers_v1(conn, transfers):
    for transfer in transfers:
        await conn.execute(
            """UPDATE accounts SET credits_posted = credits_posted + $1 WHERE id = $2""",
            transfer.amount,
            transfer.credit_account_id,
        )
        await conn.execute(
            """UPDATE accounts SET debits_posted = debits_posted + $1 WHERE id = $2""",
            transfer.amount,
            transfer.debit_account_id,
        )
        await conn.execute(
            """INSERT INTO transfers VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)""",
            *astuple(transfer),
        )
        log_progress("create_transfers_v1", 1)


async def main(fn, batches):
    localhost = "postgresql://postgres@localhost/tigerbeetle"

    # Don't get any clever ideas - it's limited to the VPC :)
    prod = "postgresql://postgres:uHUch8TZMyTVM1A4@costadb.cwdzzbfspceb.us-east-2.rds.amazonaws.com/tigerbeetle"

    conn = await asyncpg.connect(prod)
    await clear_database(conn)

    accounts = [astuple(Account()) for i in range(0, 2)]
    await create_accounts(conn, accounts)

    batch_size = 1024
    batch_multiple = 2

    global transfer_target
    transfer_target = batches * batch_size * batch_multiple

    for _ in range(0, batches):
        transfers = []
        for i in range(0, batch_size):
            transfers.extend(
                [
                    Transfer(
                        debit_account_id=accounts[0][0],
                        credit_account_id=accounts[1][0],
                        amount=1000,
                    ),
                    Transfer(
                        debit_account_id=accounts[1][0],
                        credit_account_id=accounts[0][0],
                        amount=1000,
                    ),
                ]
            )

        start = time.monotonic()
        await fn(conn, transfers)
        end = time.monotonic()

#        print((end - start) * 1000)

    # Close the connection.
    await conn.close()


if sys.argv[1] == "create_transfers_v1":
    fn = create_transfers_v1
    batches = 100
elif sys.argv[1] == "create_transfers_v2":
    fn = create_transfers_v2
    batches = 100
elif sys.argv[1] == "create_transfers_v3":
    fn = create_transfers_v3
    batches = 1000

asyncio.get_event_loop().run_until_complete(main(fn, batches))

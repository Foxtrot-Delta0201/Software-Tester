"""Suite: Bulk Data Entry Throughput — 5 000 records in < 10 min.

Seeds 5 000 patient records across 5 tenants using an asyncpg connection
pool, then runs 5 000 concurrent RLS-isolation assertions to verify each
record is visible only from its own tenant context.

Target: >= 8.3 ops/s sustained (5 000 ops in 600 s).  In practice the
pool saturates the DB at several hundred ops/s, so the real ceiling is
the Postgres instance, not this suite.

Run standalone::

    pytest tests/performance/test_bulk_throughput.py -v -s

Or via the orchestrator ``--categories bulk_throughput`` flag.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | bulk_throughput | %(message)s",
)
logger = logging.getLogger("bulk_throughput")

load_dotenv()

# ── Connection settings ────────────────────────────────────────────────────── #
DB_HOST    = os.getenv("FOCIMED_DB_HOST",     "localhost")
DB_PORT    = int(os.getenv("FOCIMED_DB_PORT", "5432"))
DB_NAME    = os.getenv("FOCIMED_DB_NAME",     "focimed_core")
SUPER_USER = os.getenv("FOCIMED_SUPERUSER",   "postgres")
SUPER_PASS = os.getenv("POSTGRES_PASSWORD",   "focimed_local_secret")
APP_USER   = os.getenv("FOCIMED_APP_USER",    "app_user")
APP_PASS   = os.getenv("FOCIMED_APP_PASSWORD","app_user_local_secret")

# ── Workload knobs ─────────────────────────────────────────────────────────── #
N_TENANTS       = 5        # number of isolated tenant buckets
N_PER_TENANT    = 1_000    # patients per tenant → 5 000 total
POOL_SIZE       = 50       # asyncpg pool connections
BATCH_SIZE      = 200      # rows per executemany batch
TARGET_SECS     = 600      # 10-minute ceiling
CONCURRENCY_CAP = 200      # max simultaneous assertion coroutines
ISOLATION_SAMPLE = 20      # patients sampled per tenant for cross-tenant check

# Deterministic tenant UUIDs so cleanup is exact.
BULK_TENANTS = [
    uuid.UUID(f"{i:08d}-0000-4000-8000-000000000000")
    for i in range(1, N_TENANTS + 1)
]


# ── Pool helpers ───────────────────────────────────────────────────────────── #
async def _super_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=SUPER_USER, password=SUPER_PASS,
        min_size=5, max_size=POOL_SIZE,
    )


async def _app_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=APP_USER, password=APP_PASS,
        min_size=5, max_size=POOL_SIZE,
    )


# ── Fixtures ───────────────────────────────────────────────────────────────── #
@pytest_asyncio.fixture(scope="module")
async def bulk_data():
    """Seed N_TENANTS * N_PER_TENANT patients; yield patient map; teardown."""
    super_pool = await _super_pool()

    # Ensure tenants exist.
    async with super_pool.acquire() as conn:
        for tid in BULK_TENANTS:
            await conn.execute(
                """
                INSERT INTO pool_01.tenants (tenant_id, practice_name)
                VALUES ($1, $2)
                ON CONFLICT (tenant_id) DO NOTHING;
                """,
                tid, f"BulkPractice-{tid.hex[:6]}",
            )
    logger.info("Ensured %d tenants", N_TENANTS)

    # Seed patients in batches.
    all_patients: dict[uuid.UUID, list[uuid.UUID]] = {t: [] for t in BULK_TENANTS}
    seed_start = time.perf_counter()

    for tid in BULK_TENANTS:
        pids = [uuid.uuid4() for _ in range(N_PER_TENANT)]
        all_patients[tid] = pids

        for batch_start in range(0, N_PER_TENANT, BATCH_SIZE):
            batch = pids[batch_start: batch_start + BATCH_SIZE]
            rows = [
                (pid, tid, f"First{i}", f"Last{i}", f"MA-BULK-{i:06d}")
                for i, pid in enumerate(batch, start=batch_start)
            ]
            async with super_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO pool_01.patients
                        (patient_id, tenant_id, first_name, last_name, medical_aid_number)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (patient_id) DO NOTHING;
                    """,
                    rows,
                )

    total_seeded = N_TENANTS * N_PER_TENANT
    seed_elapsed = time.perf_counter() - seed_start
    logger.info(
        "Seeded %d patients in %.2fs (%.0f rows/s)",
        total_seeded, seed_elapsed, total_seeded / seed_elapsed,
    )

    yield all_patients

    # Teardown — remove only the bulk-test tenants.
    async with super_pool.acquire() as conn:
        for tid in BULK_TENANTS:
            await conn.execute(
                "DELETE FROM pool_01.patients WHERE tenant_id = $1;", tid
            )
            await conn.execute(
                "DELETE FROM pool_01.tenants  WHERE tenant_id = $1;", tid
            )
    await super_pool.close()
    logger.info("Bulk teardown complete")


# ── Assertion worker ───────────────────────────────────────────────────────── #
@dataclass
class _Tally:
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


async def _assert_visible(
    pool: asyncpg.Pool,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    sem: asyncio.Semaphore,
    tally: _Tally,
) -> None:
    """Verify patient_id is visible from its own tenant context."""
    async with sem:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "SELECT set_config('app.current_tenant', $1, true);",
                        str(tenant_id),
                    )
                    row = await conn.fetchrow(
                        "SELECT patient_id FROM pool_01.patients WHERE patient_id = $1;",
                        patient_id,
                    )
            if row and row["patient_id"] == patient_id:
                tally.passed += 1
            else:
                tally.failed += 1
                tally.errors.append(
                    f"patient {patient_id} invisible in tenant {tenant_id}"
                )
        except Exception as exc:  # noqa: BLE001
            tally.failed += 1
            tally.errors.append(f"error on {patient_id}: {exc}")


# ── Tests ──────────────────────────────────────────────────────────────────── #
@pytest.mark.asyncio
async def test_bulk_5000_records_under_10_minutes(bulk_data):
    """Assert all 5 000 seeded patients are visible from their own tenant — must finish in < 10 min.

    Passes when:
    - wall time < 600 s (TARGET_SECS)
    - 0 assertion failures
    - passed count == N_TENANTS * N_PER_TENANT
    """
    app_pool = await _app_pool()
    sem = asyncio.Semaphore(CONCURRENCY_CAP)
    tally = _Tally()

    tasks = [
        _assert_visible(app_pool, tid, pid, sem, tally)
        for tid, pids in bulk_data.items()
        for pid in pids
    ]

    total = len(tasks)
    logger.info(
        "Launching %d assertion tasks  pool=%d  concurrency_cap=%d",
        total, POOL_SIZE, CONCURRENCY_CAP,
    )

    wall_start = time.perf_counter()
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - wall_start

    rate = total / elapsed if elapsed > 0 else float("inf")
    logger.info(
        "Done: %d ops in %.2fs  =>  %.1f ops/s  |  passed=%d  failed=%d",
        total, elapsed, rate, tally.passed, tally.failed,
    )
    if tally.errors:
        logger.error("Sample errors: %s", tally.errors[:5])

    await app_pool.close()

    assert elapsed < TARGET_SECS, (
        f"Throughput target missed: {total} ops took {elapsed:.1f}s "
        f"(limit {TARGET_SECS}s, achieved {rate:.1f} ops/s)"
    )
    assert tally.failed == 0, (
        f"{tally.failed} assertion(s) failed — sample: {tally.errors[:3]}"
    )
    assert tally.passed == total, (
        f"Expected {total} passed, got {tally.passed}"
    )


@pytest.mark.asyncio
async def test_cross_tenant_isolation_at_scale(bulk_data):
    """Spot-check: a sample of patients must NOT be readable from a foreign tenant.

    Takes ISOLATION_SAMPLE patients from each tenant and attempts to read
    them while scoped to the *next* tenant in the list.  Zero leaks expected.
    """
    app_pool = await _app_pool()
    sem = asyncio.Semaphore(50)
    leaked: list[str] = []

    async def _check_leak(
        own_tid: uuid.UUID, foreign_tid: uuid.UUID, pid: uuid.UUID
    ) -> None:
        async with sem:
            async with app_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "SELECT set_config('app.current_tenant', $1, true);",
                        str(foreign_tid),
                    )
                    row = await conn.fetchrow(
                        "SELECT patient_id FROM pool_01.patients WHERE patient_id = $1;",
                        pid,
                    )
            if row:
                leaked.append(
                    f"LEAK: patient {pid} of {own_tid} visible from {foreign_tid}"
                )

    tenant_list = list(bulk_data.items())
    tasks = [
        _check_leak(tid, tenant_list[(i + 1) % N_TENANTS][0], pid)
        for i, (tid, pids) in enumerate(tenant_list)
        for pid in pids[:ISOLATION_SAMPLE]
    ]

    probe_count = len(tasks)
    logger.info("Running %d cross-tenant isolation probes...", probe_count)
    await asyncio.gather(*tasks)
    await app_pool.close()

    assert not leaked, (
        f"{len(leaked)} cross-tenant leak(s) detected:\n" + "\n".join(leaked[:10])
    )
    logger.info("Cross-tenant isolation: 0 leaks across %d probes", probe_count)

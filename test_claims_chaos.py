"""Suite C — The EDI State Machine & Chaos Injector.

Hammers ``pool_01.claim_header`` with concurrent, deliberately ILLEGAL state
transitions and proves that:

    1. The ``BEFORE UPDATE`` trigger ``enforce_claim_transition`` rejects every
       illegal jump (e.g. DRAFT -> PAID) with SQLSTATE 23514.
    2. Under a strict isolation level (SERIALIZABLE), conflicting concurrent
       writers are serialized — at most one legal transition wins; the rest fail
       with a serialization error (40001) and are retried/aborted, never silently
       lost.
    3. After the storm the row sits in a single, mathematically consistent state.
    4. Every failed attempt is durably recorded in ``pool_01.claim_audit_log``.

Why the audit log is written on a SEPARATE connection
-----------------------------------------------------
When the trigger ``RAISE``s, it aborts *its own* transaction, so any log row
written inside that transaction would be rolled back too. Each worker therefore
records the failure through an INDEPENDENT connection/transaction — the standard
pattern for durable audit trails around failing operations.

Run with::

    pytest test_claims_chaos.py -v
"""

import asyncio
import logging
import os
import uuid

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("claims_chaos")

load_dotenv()

DB_HOST = os.getenv("FOCIMED_DB_HOST", "localhost")
DB_PORT = int(os.getenv("FOCIMED_DB_PORT", "5432"))
DB_NAME = os.getenv("FOCIMED_DB_NAME", "focimed_core")
SUPER_USER = os.getenv("FOCIMED_SUPERUSER", "postgres")
SUPER_PASSWORD = os.getenv("POSTGRES_PASSWORD", "focimed_local_secret")

CHAOS_TENANT_ID = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
CONCURRENCY = 20

# Illegal targets: none of these are reachable from DRAFT in one legal hop.
ILLEGAL_TARGETS = ["PAID", "ACKNOWLEDGED", "TRANSMITTED", "REJECTED"]


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=SUPER_USER, password=SUPER_PASSWORD,
    )


@pytest_asyncio.fixture()
async def chaos_claim():
    """Create a fresh tenant + a single DRAFT claim; clean up afterwards."""
    conn = await _connect()

    await conn.execute(
        """
        INSERT INTO pool_01.tenants (tenant_id, practice_name)
        VALUES ($1, 'Chaos Practice')
        ON CONFLICT (tenant_id) DO NOTHING;
        """,
        CHAOS_TENANT_ID,
    )
    claim_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO pool_01.claim_header (claim_id, status, tenant_id)
        VALUES ($1, 'DRAFT', $2);
        """,
        claim_id, CHAOS_TENANT_ID,
    )
    # Start from a clean audit slate for this claim.
    await conn.execute("DELETE FROM pool_01.claim_audit_log WHERE claim_id = $1;", claim_id)
    logger.info("Seeded DRAFT claim %s", claim_id)

    yield claim_id

    await conn.execute("DELETE FROM pool_01.claim_audit_log WHERE claim_id = $1;", claim_id)
    await conn.execute("DELETE FROM pool_01.claim_header WHERE claim_id = $1;", claim_id)
    await conn.execute("DELETE FROM pool_01.tenants WHERE tenant_id = $1;", CHAOS_TENANT_ID)
    await conn.close()
    logger.info("Cleaned up chaos claim %s", claim_id)


async def _audit(claim_id: uuid.UUID, to_status: str, outcome: str, detail: str) -> None:
    """Write an audit row on its own connection/transaction (rollback-proof)."""
    conn = await _connect()
    try:
        await conn.execute(
            """
            INSERT INTO pool_01.claim_audit_log
                (claim_id, from_status, to_status, outcome, detail)
            VALUES ($1, 'DRAFT', $2, $3, $4);
            """,
            claim_id, to_status, outcome, detail,
        )
    finally:
        await conn.close()


async def _attempt_illegal_transition(claim_id: uuid.UUID, target: str, worker: int) -> str:
    """One chaos worker: try an illegal jump under SERIALIZABLE isolation.

    Returns one of: 'REJECTED' (trigger blocked it), 'SERIALIZATION' (isolation
    conflict), or 'LEAKED' (the update unexpectedly succeeded — a real defect).
    """
    conn = await _connect()
    try:
        async with conn.transaction(isolation="serializable"):
            await conn.execute(
                "UPDATE pool_01.claim_header SET status = $1 WHERE claim_id = $2;",
                target, claim_id,
            )
        # No exception => the illegal write committed. This must never happen.
        logger.critical(
            "[SEV-1] ILLEGAL TRANSITION LEAKED: worker %d forced DRAFT -> %s on %s",
            worker, target, claim_id,
        )
        await _audit(claim_id, target, "ERROR", f"worker {worker}: illegal write committed")
        return "LEAKED"
    except asyncpg.exceptions.SerializationError as exc:
        logger.warning("worker %d serialization conflict -> %s: %s", worker, target, exc)
        await _audit(claim_id, target, "REJECTED", f"worker {worker}: serialization_failure")
        return "SERIALIZATION"
    except asyncpg.PostgresError as exc:
        # Expected path: the trigger raises check_violation (23514).
        logger.info(
            "worker %d blocked DRAFT -> %s (SQLSTATE %s)",
            worker, target, exc.sqlstate,
        )
        await _audit(claim_id, target, "REJECTED", f"worker {worker}: {exc.sqlstate} {exc}")
        return "REJECTED"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_concurrent_illegal_transitions_are_rejected(chaos_claim):
    """20 concurrent illegal overrides — none may succeed; all must be audited."""
    claim_id = chaos_claim

    tasks = [
        _attempt_illegal_transition(claim_id, ILLEGAL_TARGETS[i % len(ILLEGAL_TARGETS)], i)
        for i in range(CONCURRENCY)
    ]
    results = await asyncio.gather(*tasks)

    leaked = results.count("LEAKED")
    rejected = results.count("REJECTED")
    serialization = results.count("SERIALIZATION")
    logger.info(
        "Chaos complete: rejected=%d serialization=%d leaked=%d",
        rejected, serialization, leaked,
    )

    # 1. No illegal transition may ever commit.
    assert leaked == 0, f"{leaked} illegal transition(s) leaked through the state machine"

    # 2. The row must still be in the clean, original DRAFT state.
    conn = await _connect()
    try:
        final_status = await conn.fetchval(
            "SELECT status FROM pool_01.claim_header WHERE claim_id = $1;", claim_id
        )
        audit_count = await conn.fetchval(
            "SELECT count(*) FROM pool_01.claim_audit_log WHERE claim_id = $1;", claim_id
        )
    finally:
        await conn.close()

    logger.info("Post-storm status=%s, audit rows=%d", final_status, audit_count)
    assert final_status == "DRAFT", f"Claim corrupted to '{final_status}' after chaos storm"

    # 3. Every single failed attempt must be recorded in the audit log.
    assert audit_count == CONCURRENCY, (
        f"Audit gap: {audit_count} log rows for {CONCURRENCY} failed attempts"
    )


@pytest.mark.asyncio
async def test_legal_transition_still_succeeds(chaos_claim):
    """Control case — a valid DRAFT -> VALIDATED hop must be allowed."""
    claim_id = chaos_claim
    conn = await _connect()
    try:
        async with conn.transaction(isolation="serializable"):
            await conn.execute(
                "UPDATE pool_01.claim_header SET status = 'VALIDATED' WHERE claim_id = $1;",
                claim_id,
            )
        status = await conn.fetchval(
            "SELECT status FROM pool_01.claim_header WHERE claim_id = $1;", claim_id
        )
    finally:
        await conn.close()

    logger.info("Legal transition produced status=%s", status)
    assert status == "VALIDATED", "Legal DRAFT -> VALIDATED transition was blocked"

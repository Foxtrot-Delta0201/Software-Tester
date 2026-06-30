"""Foci-Med Bulk Data Seeder.

Generates and inserts realistic South African medical practice data at high
throughput using an asyncpg connection pool.  Progress is streamed back to
the caller via an asyncio.Queue so the FastAPI SSE endpoint can forward it
to the browser in real time.

Entity types seeded
-------------------
  Tenants    — named medical practices
  Patients   — SA names, ID numbers, medical aid references
  Encounters — basic consultation records linked to patients
  Claims     — DRAFT billing claims linked to encounters
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from datetime import date, timedelta
from typing import Any

import asyncpg

# ── South African reference data ───────────────────────────────────────────── #
_FIRST_NAMES = [
    "Sipho", "Thabo", "Nokwanda", "Zanele", "Nomsa", "Bongani", "Lerato",
    "Tumelo", "Andile", "Sandile", "Lungelo", "Thandeka", "Nkosi", "Siyanda",
    "Ayanda", "Nhlanhla", "Lindiwe", "Mbuso", "Sifiso", "Nompumelelo",
    "Pieter", "Anneke", "Johan", "Hendrik", "Maria", "Elmarie", "Christiaan",
    "Mohammed", "Fatima", "Yusuf", "Aisha", "Ibrahim", "Raheema",
    "Priya", "Raj", "Kavitha", "Sanjay", "Nadia", "Reza",
    "Tshepo", "Kagiso", "Dikeledi", "Lesedi", "Mpho", "Refilwe",
]

_LAST_NAMES = [
    "Dlamini", "Zulu", "Nkosi", "Ndlovu", "Mkhize", "Cele", "Ntuli",
    "Khoza", "Shabalala", "Buthelezi", "Mokoena", "Molefe", "Khumalo",
    "van der Merwe", "Botha", "Smit", "Du Plessis", "Visser", "Pretorius",
    "Coetzee", "Joubert", "Nel", "Fourie",
    "Mohamed", "Adams", "Hendricks", "January", "Petersen", "Williams",
    "Maharaj", "Pillay", "Naidoo", "Govender", "Singh", "Reddy",
    "Mahlangu", "Sithole", "Masondo", "Nxumalo", "Zwane",
]

_PRACTICE_SUFFIXES = [
    "Family Practice", "Medical Centre", "Clinic", "Health Centre",
    "Medical Practice", "GP Practice", "Wellness Clinic",
]

_PRACTICE_LOCATIONS = [
    "Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth",
    "Bloemfontein", "East London", "Sandton", "Soweto", "Centurion",
    "Randburg", "Roodepoort", "Midrand", "Benoni", "Boksburg",
]

_MEDICAL_AIDS = ["DH", "BON", "MED", "GEMS", "MOM", "KEY", "BES", "CAP"]

_ICD10_CODES = [
    "J06.9",  # URTI
    "J45.0",  # Asthma
    "E11.9",  # Type 2 DM
    "I10",    # Hypertension
    "K21.0",  # GORD
    "M54.5",  # Low back pain
    "F32.9",  # Depression
    "N39.0",  # UTI
    "Z23",    # Immunization encounter
    "J18.9",  # Pneumonia
    "K59.0",  # Constipation
    "L20.9",  # Atopic dermatitis
    "H10.9",  # Conjunctivitis
    "M79.3",  # Panniculitis
    "R51",    # Headache
]

_TARIFF_CODES = ["0101", "0190", "0191", "1211", "0146", "0189"]

_CLAIM_STATUSES = ["DRAFT", "VALIDATED", "TRANSMITTED"]

POOL_SIZE  = 50
BATCH_SIZE = 250


# ── Helpers ────────────────────────────────────────────────────────────────── #
def _sa_id() -> str:
    """Generate a plausible (but fake) South African 13-digit ID number."""
    dob = _rand_dob()
    yy  = str(dob.year)[-2:]
    mm  = f"{dob.month:02d}"
    dd  = f"{dob.day:02d}"
    seq = random.randint(5000, 9999)
    cit = 0  # SA citizen
    check = random.randint(0, 9)
    return f"{yy}{mm}{dd}{seq}{cit}{check:02d}"


def _rand_dob(min_age: int = 18, max_age: int = 85) -> date:
    today = date.today()
    days  = random.randint(min_age * 365, max_age * 365)
    return today - timedelta(days=days)


def _ma_number() -> str:
    prefix = random.choice(_MEDICAL_AIDS)
    return f"{prefix}-{random.randint(10_000_000, 99_999_999)}"


def _practice_name() -> str:
    loc    = random.choice(_PRACTICE_LOCATIONS)
    suffix = random.choice(_PRACTICE_SUFFIXES)
    return f"{loc} {suffix}"


def _rand_name() -> tuple[str, str]:
    return random.choice(_FIRST_NAMES), random.choice(_LAST_NAMES)


async def _pool(cfg: dict) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=cfg["db_host"], port=cfg["db_port"],
        database=cfg["db_name"], user=cfg["db_user"],
        password=cfg["db_password"],
        min_size=5, max_size=POOL_SIZE,
    )


# ── Seeding functions ──────────────────────────────────────────────────────── #
async def _seed_tenants(pool: asyncpg.Pool, n: int, clear: bool) -> list[uuid.UUID]:
    tenant_ids = [uuid.uuid4() for _ in range(n)]
    async with pool.acquire() as conn:
        if clear:
            await conn.execute("DELETE FROM pool_01.tenants WHERE practice_name LIKE '%[SEED]%';")
        await conn.executemany(
            "INSERT INTO pool_01.tenants (tenant_id, practice_name) VALUES ($1, $2) ON CONFLICT DO NOTHING;",
            [(tid, f"{_practice_name()} [SEED]") for tid in tenant_ids],
        )
    return tenant_ids


async def _seed_patients_batch(
    pool: asyncpg.Pool,
    tenant_id: uuid.UUID,
    batch: list[tuple],
) -> int:
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO pool_01.patients
                (patient_id, tenant_id, first_name, last_name, date_of_birth, medical_aid_number)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (patient_id) DO NOTHING;
            """,
            batch,
        )
    return len(batch)


async def _seed_encounters_batch(
    pool: asyncpg.Pool,
    tenant_id: uuid.UUID,
    patient_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Insert one encounter per patient; return encounter IDs."""
    encounter_ids = [uuid.uuid4() for _ in patient_ids]
    rows = [
        (
            eid, pid, tenant_id,
            random.choice(_ICD10_CODES),
            f"Patient presents with {random.choice(['fever', 'cough', 'fatigue', 'pain', 'nausea'])}",
            date.today() - timedelta(days=random.randint(0, 365)),
        )
        for eid, pid in zip(encounter_ids, patient_ids)
    ]
    async with pool.acquire() as conn:
        try:
            await conn.executemany(
                """
                INSERT INTO pool_01.encounters
                    (encounter_id, patient_id, tenant_id, icd10_primary, chief_complaint, encounter_date)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (encounter_id) DO NOTHING;
                """,
                rows,
            )
        except asyncpg.UndefinedTableError:
            return []   # encounters table not yet migrated — skip gracefully
        except asyncpg.UndefinedColumnError:
            return []
    return encounter_ids


async def _seed_claims_batch(
    pool: asyncpg.Pool,
    tenant_id: uuid.UUID,
    encounter_ids: list[uuid.UUID],
) -> int:
    if not encounter_ids:
        return 0
    rows = [
        (
            uuid.uuid4(), tenant_id,
            random.choice(_CLAIM_STATUSES),
            random.choice(_TARIFF_CODES),
            eid,
        )
        for eid in encounter_ids
    ]
    async with pool.acquire() as conn:
        try:
            await conn.executemany(
                """
                INSERT INTO pool_01.claim_header
                    (claim_id, tenant_id, status, tariff_code, encounter_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (claim_id) DO NOTHING;
                """,
                rows,
            )
        except (asyncpg.UndefinedTableError, asyncpg.UndefinedColumnError):
            # Fallback: insert without encounter_id if column absent.
            try:
                await conn.executemany(
                    """
                    INSERT INTO pool_01.claim_header (claim_id, tenant_id, status)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (claim_id) DO NOTHING;
                    """,
                    [(r[0], r[1], r[2]) for r in rows],
                )
            except Exception:
                return 0
    return len(rows)


# ── Main entry point ───────────────────────────────────────────────────────── #
async def run_seed(q: asyncio.Queue, cfg: dict, params: dict) -> None:
    """Bulk-seed the database and stream progress events into q."""

    async def log(msg: str, level: str = "info") -> None:
        await q.put({"level": level, "msg": msg})

    n_tenants  = params.get("n_tenants", 5)
    n_patients = params.get("n_patients_per_tenant", 1_000)
    do_enc     = params.get("include_encounters", True)
    do_claims  = params.get("include_claims", True)
    clear      = params.get("clear_existing", False)
    total      = n_tenants * n_patients

    await log(f"Starting seed: {n_tenants} tenants × {n_patients} patients = {total:,} total")

    pool = await _pool(cfg)
    grand_start = time.perf_counter()

    try:
        # ── Tenants ───────────────────────────────────────────────────────── #
        tenant_ids = await _seed_tenants(pool, n_tenants, clear)
        await log(f"Tenants created: {n_tenants}")

        patients_done = 0
        encounters_done = 0
        claims_done = 0

        for t_idx, tenant_id in enumerate(tenant_ids, 1):
            t_start = time.perf_counter()
            patient_ids: list[uuid.UUID] = []

            # ── Patients (batched) ─────────────────────────────────────────── #
            for batch_start in range(0, n_patients, BATCH_SIZE):
                batch_pids = [uuid.uuid4() for _ in range(min(BATCH_SIZE, n_patients - batch_start))]
                batch_rows = [
                    (
                        pid, tenant_id,
                        *_rand_name(),
                        _rand_dob(),
                        _ma_number(),
                    )
                    for pid in batch_pids
                ]
                await _seed_patients_batch(pool, tenant_id, batch_rows)
                patient_ids.extend(batch_pids)
                patients_done += len(batch_pids)

            rate = patients_done / max(time.perf_counter() - grand_start, 0.001)
            pct  = int(patients_done / total * 100)
            await log(
                f"Tenant {t_idx}/{n_tenants} — patients: {patients_done:,}/{total:,} "
                f"({pct}%) | {rate:.0f} rows/s",
                "progress",
            )
            await q.put({"type": "progress", "value": pct})

            # ── Encounters ────────────────────────────────────────────────── #
            if do_enc:
                enc_ids = await _seed_encounters_batch(pool, tenant_id, patient_ids)
                encounters_done += len(enc_ids)
                if enc_ids:
                    await log(f"  Encounters: {encounters_done:,} inserted")

                    # ── Claims ─────────────────────────────────────────────── #
                    if do_claims:
                        n = await _seed_claims_batch(pool, tenant_id, enc_ids)
                        claims_done += n
                        if n:
                            await log(f"  Claims: {claims_done:,} inserted")

        elapsed = time.perf_counter() - grand_start
        summary = (
            f"Done in {elapsed:.1f}s — "
            f"{patients_done:,} patients, "
            f"{encounters_done:,} encounters, "
            f"{claims_done:,} claims"
        )
        await log(summary, "success")
        await q.put({
            "done": True,
            "level": "success",
            "msg": summary,
            "stats": {
                "patients":   patients_done,
                "encounters": encounters_done,
                "claims":     claims_done,
                "elapsed_s":  round(elapsed, 2),
            },
        })

    finally:
        await pool.close()

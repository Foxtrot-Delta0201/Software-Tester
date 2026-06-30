"""Suite B — The Temporal Time-Travel Auditor.

Validates Slowly-Changing-Dimension (SCD Type 2) pricing of South African
tariff codes in ``public.sys_tariffs``. The core question: when a claim arrives
with a historical Date of Service (DoS), does the database resolve the price
that was effective *at that moment*, rather than today's price?

Temporal query / boundary handling
-----------------------------------
Each tariff version is stored as a HALF-OPEN interval ``[effective_from, effective_to)``:

    effective_from <= DoS  AND  (effective_to IS NULL OR DoS < effective_to)

* The lower bound is INCLUSIVE and the upper bound EXCLUSIVE. Adjacent versions
  therefore share a single boundary instant with no overlap and no gap: the
  exact instant ``2026-06-01 00:00`` belongs to the NEW version only.
* ``effective_to IS NULL`` marks the open-ended current version.
* All columns are ``TIMESTAMPTZ`` so comparisons are timezone-safe.

The resolution itself is delegated to ``public.resolve_tariff_price(code, dos)``
which also fail-closes on future-dated (out-of-range) service dates.

Run with::

    pytest test_temporal_tariffs.py -v
"""

import logging
import os
from decimal import Decimal

import psycopg2
import pytest
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("temporal_tariffs")

load_dotenv()

DB_HOST = os.getenv("FOCIMED_DB_HOST", "localhost")
DB_PORT = int(os.getenv("FOCIMED_DB_PORT", "5432"))
DB_NAME = os.getenv("FOCIMED_DB_NAME", "focimed_core")
SUPER_USER = os.getenv("FOCIMED_SUPERUSER", "postgres")
SUPER_PASSWORD = os.getenv("POSTGRES_PASSWORD", "focimed_local_secret")

TARIFF_CODE = "0101"  # Standard consultation
PRICE_OLD = Decimal("400.00")
PRICE_NEW = Decimal("450.00")


@pytest.fixture()
def db_connection():
    """Connect as superuser (this suite manages reference data in ``public``)."""
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=SUPER_USER, password=SUPER_PASSWORD,
    )
    conn.autocommit = True
    logger.info("Opened session for temporal tariff suite")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def seed_tariff_history(db_connection):
    """Test Case 1 — build the SCD2 history for code '0101'.

    Step 1: insert R400.00 effective 2026-01-01 .. 2026-06-01 (exclusive),
            marked non-current.
    Step 2: insert R450.00 effective 2026-06-01 .. open-ended, marked current.

    Using 2026-06-01 as BOTH the old version's exclusive upper bound and the new
    version's inclusive lower bound yields a clean, gapless cut-over.
    """
    cur = db_connection.cursor()
    cur.execute("DELETE FROM public.sys_tariffs WHERE tariff_code = %s;", (TARIFF_CODE,))

    cur.execute(
        """
        INSERT INTO public.sys_tariffs
            (tariff_code, base_price, effective_from, effective_to, is_current)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (TARIFF_CODE, PRICE_OLD, "2026-01-01 00:00:00+02",
         "2026-06-01 00:00:00+02", False),
    )
    cur.execute(
        """
        INSERT INTO public.sys_tariffs
            (tariff_code, base_price, effective_from, effective_to, is_current)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (TARIFF_CODE, PRICE_NEW, "2026-06-01 00:00:00+02", None, True),
    )
    logger.info(
        "Seeded SCD2 history: %s @ R%s (closed) -> R%s (current)",
        TARIFF_CODE, PRICE_OLD, PRICE_NEW,
    )

    yield
    cur.execute("DELETE FROM public.sys_tariffs WHERE tariff_code = %s;", (TARIFF_CODE,))


def _resolve(cur, dos: str) -> Decimal:
    """Resolve the effective price for a tariff code at a Date of Service."""
    cur.execute("SELECT public.resolve_tariff_price(%s, %s);", (TARIFF_CODE, dos))
    return cur.fetchone()[0]


def test_backdated_claim_resolves_old_price(db_connection, seed_tariff_history):
    """Test Case 2 — DoS 2026-04-15 (old window) must resolve to R400.00."""
    cur = db_connection.cursor()
    price = _resolve(cur, "2026-04-15 09:30:00+02")
    logger.info("Backdated DoS 2026-04-15 resolved to R%s", price)
    assert price == PRICE_OLD, (
        f"Temporal mismatch: backdated claim priced at R{price}, expected R{PRICE_OLD}"
    )


def test_current_claim_resolves_new_price(db_connection, seed_tariff_history):
    """Test Case 3 — DoS 2026-06-15 (current window) must resolve to R450.00."""
    cur = db_connection.cursor()
    price = _resolve(cur, "2026-06-15 09:30:00+02")
    logger.info("Current DoS 2026-06-15 resolved to R%s", price)
    assert price == PRICE_NEW, (
        f"Temporal mismatch: current claim priced at R{price}, expected R{PRICE_NEW}"
    )


def test_boundary_instant_belongs_to_new_version(db_connection, seed_tariff_history):
    """Boundary check — the exact cut-over instant resolves to the NEW price.

    Confirms the half-open ``[from, to)`` semantics: 2026-06-01 00:00 is excluded
    from the old version and included in the new one.
    """
    cur = db_connection.cursor()
    price = _resolve(cur, "2026-06-01 00:00:00+02")
    logger.info("Boundary instant 2026-06-01 00:00 resolved to R%s", price)
    assert price == PRICE_NEW, "Boundary instant must belong to the new version"


def test_future_dos_is_rejected(db_connection, seed_tariff_history):
    """Test Case 4 — a 2028 DoS must raise an out-of-range exception."""
    cur = db_connection.cursor()
    with pytest.raises(psycopg2.Error) as exc_info:
        _resolve(cur, "2028-03-10 09:30:00+02")

    pgcode = exc_info.value.pgcode
    logger.info(
        "Future DoS 2028-03-10 correctly rejected with SQLSTATE %s: %s",
        pgcode, str(exc_info.value).strip(),
    )
    # 22008 = datetime_field_overflow (raised by resolve_tariff_price).
    assert pgcode == "22008", f"Expected out-of-range SQLSTATE 22008, got {pgcode}"

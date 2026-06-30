"""Suite A — The RLS Leak Detector.

Actively attempts cross-tenant data leaks against ``pool_01.patients`` to prove
that the Row-Level Security (RLS) tenant-isolation policy is leakproof.

Design:
    * All tenant-scoped queries run as the NON-superuser role ``app_user`` so
      that RLS actually applies (superusers and, without FORCE, table owners
      bypass RLS).
    * Test data is seeded with the superuser connection, which bypasses RLS and
      can therefore populate both tenants.
    * Isolation key: the session GUC ``app.current_tenant``.

Run with::

    pytest test_rls_leak_detector.py -v
"""

import logging
import os
import uuid

import psycopg2
import pytest
from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("rls_leak_detector")

load_dotenv()

# --------------------------------------------------------------------------- #
# Connection settings
# --------------------------------------------------------------------------- #
DB_HOST = os.getenv("FOCIMED_DB_HOST", "localhost")
DB_PORT = int(os.getenv("FOCIMED_DB_PORT", "5432"))
DB_NAME = os.getenv("FOCIMED_DB_NAME", "focimed_core")

# Superuser — admin + seeding only (bypasses RLS).
SUPER_USER = os.getenv("FOCIMED_SUPERUSER", "postgres")
SUPER_PASSWORD = os.getenv("POSTGRES_PASSWORD", "focimed_local_secret")

# Application role — subject to RLS; all isolation assertions run as this user.
APP_USER = os.getenv("FOCIMED_APP_USER", "app_user")
APP_PASSWORD = os.getenv("FOCIMED_APP_PASSWORD", "app_user_local_secret")

# Deterministic tenant identifiers so assertions can reference them directly.
TENANT_ID_A = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TENANT_ID_B = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PATIENTS_PER_TENANT = 5


def _connect(user: str, password: str):
    """Open a psycopg2 connection for the given role."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=user,
        password=password,
    )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture()
def db_connection():
    """Establish and tear down an ``app_user`` session (RLS-bound)."""
    conn = _connect(APP_USER, APP_PASSWORD)
    logger.info("Opened app_user session to %s/%s", DB_HOST, DB_NAME)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
        logger.info("Closed app_user session")


@pytest.fixture()
def setup_test_data():
    """Seed two tenants with 5 patients each, then clean up afterwards.

    Seeding uses the SUPERUSER connection because RLS would otherwise block
    inserts for the 'wrong' tenant. UUIDs are generated with the cryptographic
    ``uuid4`` for non-guessable identifiers.
    """
    conn = _connect(SUPER_USER, SUPER_PASSWORD)
    conn.autocommit = True
    cur = conn.cursor()

    logger.info("Seeding mock tenants and patients (superuser)")
    # Clean slate for repeatable runs.
    cur.execute("DELETE FROM pool_01.patients;")
    cur.execute("DELETE FROM pool_01.tenants;")

    cur.execute(
        "INSERT INTO pool_01.tenants (tenant_id, practice_name) VALUES (%s, %s), (%s, %s);",
        (str(TENANT_ID_A), "Practice A", str(TENANT_ID_B), "Practice B"),
    )

    for tenant_id, prefix in ((TENANT_ID_A, "A"), (TENANT_ID_B, "B")):
        for i in range(PATIENTS_PER_TENANT):
            cur.execute(
                """
                INSERT INTO pool_01.patients
                    (patient_id, tenant_id, first_name, last_name, medical_aid_number)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    str(uuid.uuid4()),
                    str(tenant_id),
                    f"{prefix}First{i}",
                    f"{prefix}Last{i}",
                    f"MA-{prefix}-{i:04d}",
                ),
            )

    logger.info(
        "Seed complete: 2 tenants, %d patients total",
        PATIENTS_PER_TENANT * 2,
    )

    yield {"tenant_a": TENANT_ID_A, "tenant_b": TENANT_ID_B}

    # Teardown.
    cur.execute("DELETE FROM pool_01.patients;")
    cur.execute("DELETE FROM pool_01.tenants;")
    cur.close()
    conn.close()
    logger.info("Tore down mock data")


def _set_current_tenant(cur, tenant_id: uuid.UUID) -> None:
    """Bind ``app.current_tenant`` for the current session/transaction."""
    # set_config(parameter, value, is_local) — parameterized to avoid injection.
    cur.execute("SELECT set_config('app.current_tenant', %s, false);", (str(tenant_id),))


# --------------------------------------------------------------------------- #
# Test cases
# --------------------------------------------------------------------------- #
def test_cross_tenant_isolation(db_connection, setup_test_data):
    """Tenant A must NOT be able to read Tenant B's patients."""
    tenant_b = setup_test_data["tenant_b"]
    cur = db_connection.cursor()

    # Act as Tenant A.
    _set_current_tenant(cur, setup_test_data["tenant_a"])

    # Sanity: Tenant A can see its own rows.
    cur.execute("SELECT count(*) FROM pool_01.patients;")
    own_visible = cur.fetchone()[0]
    logger.info("Tenant A sees %d of its own patients", own_visible)
    assert own_visible == PATIENTS_PER_TENANT, "RLS hid Tenant A's own rows"

    # Attack: explicitly try to read Tenant B's rows while scoped to Tenant A.
    cur.execute(
        "SELECT * FROM pool_01.patients WHERE tenant_id = %s;",
        (str(tenant_b),),
    )
    leaked = cur.fetchall()
    leaked_count = len(leaked)

    if leaked_count != 0:
        logger.critical(
            "[SEV-1] CROSS-TENANT LEAK: Tenant A retrieved %d Tenant B rows. "
            "Leakage point: pool_01.patients via tenant_id=%s. Sample=%r",
            leaked_count,
            tenant_b,
            leaked[0],
        )
    else:
        logger.info("No cross-tenant rows returned — isolation holding")

    assert leaked_count == 0, (
        f"RLS LEAK: {leaked_count} Tenant B row(s) visible while scoped to Tenant A"
    )


def test_rls_bypass_as_app_user(db_connection, setup_test_data):
    """Without ``app.current_tenant`` set, access must fail-closed.

    The policy uses strict ``current_setting('app.current_tenant', false)``, so
    an unset variable raises ``undefined_object``. We accept EITHER outcome:
        * an exception (preferred, fail-closed), or
        * 0 rows returned,
    and we explicitly reject any case where data is returned.
    """
    cur = db_connection.cursor()

    # Deliberately do NOT set app.current_tenant.
    try:
        cur.execute("SELECT * FROM pool_01.patients;")
        rows = cur.fetchall()
    except psycopg2.Error as exc:
        # Fail-closed via exception is the expected, strongest outcome.
        db_connection.rollback()
        logger.info(
            "Access denied by default (fail-closed) with SQLSTATE %s: %s",
            exc.pgcode,
            str(exc).strip(),
        )
        return

    # If no exception was raised, the only acceptable result is zero rows.
    logger.info("No exception raised; rows returned without tenant context: %d", len(rows))
    assert len(rows) == 0, (
        "RLS DEFAULT-ALLOW VIOLATION: rows were returned with no app.current_tenant set"
    )

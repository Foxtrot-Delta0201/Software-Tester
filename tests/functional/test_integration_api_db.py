"""Functional / Integration tests — real API -> real DB round trip.

Unlike the unit suite, these exercise the genuine wiring between an HTTP API and
the PostgreSQL database. They are skipped automatically when the target services
are not reachable, so the orchestrator can run them opportunistically.

INJECT YOUR LOGIC:
    * Point ``API_BASE`` at your running service.
    * Replace the SQL/connection details with your real schema if they differ.
"""

from __future__ import annotations

import os

import pytest

requests = pytest.importorskip("requests")  # skip cleanly if not installed
psycopg2 = pytest.importorskip("psycopg2")

API_BASE = os.getenv("FOCI_API_BASE", "http://localhost:8000")
DB_DSN = os.getenv(
    "FOCI_DB_DSN",
    "host=localhost port=5432 dbname=focimed_core user=postgres "
    "password=focimed_local_secret",
)


def _api_up() -> bool:
    try:
        return requests.get(f"{API_BASE}/health", timeout=2).ok
    except Exception:  # noqa: BLE001
        return False


def _db_up() -> bool:
    try:
        conn = psycopg2.connect(DB_DSN)
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not (_api_up() and _db_up()),
    reason="API and/or PostgreSQL not reachable for integration test",
)


def test_submit_claim_persists_to_db() -> None:
    """POSTing a claim through the API should create a matching DB row.

    INJECT YOUR LOGIC: adjust the payload and the verification query to match
    your real claim-submission contract.
    """
    payload = {
        "tariff_code": "0101",
        "date_of_service": "2026-04-15",
        "tenant_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    }
    resp = requests.post(f"{API_BASE}/api/v1/claims/submit", json=payload, timeout=5)
    assert resp.status_code in (200, 201), resp.text
    claim_id = resp.json().get("claim_id")
    assert claim_id, "API did not return a claim_id"

    conn = psycopg2.connect(DB_DSN)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status FROM pool_01.claim_header WHERE claim_id = %s;",
            (claim_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None, "claim was not persisted to the database"
    assert row[0] == "DRAFT", f"new claim should start in DRAFT, got {row[0]}"

"""Grey/Black-Box / Data-Driven — claim state transitions via HTTP only.

Black-box: we know NOTHING about the internals. We feed transition payloads to
the public API and assert ONLY on the observable HTTP response (status code +
body). The legal state machine is:

    DRAFT -> VALIDATED -> TRANSMITTED -> ACKNOWLEDGED -> PAID | REJECTED

Anything else (e.g. DRAFT -> PAID) must be refused by the API.

The test is data-driven via pytest parametrization: add a row to TRANSITION_CASES
to cover a new payload — no new test code required.

INJECT YOUR LOGIC:
    * Set ``API_BASE`` and the request/route contract to match your service.
    * Adjust expected status codes to your API's conventions.
"""

from __future__ import annotations

import os

import pytest

requests = pytest.importorskip("requests")

API_BASE = os.getenv("FOCI_API_BASE", "http://localhost:8000")


def _api_up() -> bool:
    try:
        return requests.get(f"{API_BASE}/health", timeout=2).ok
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _api_up(), reason="API not reachable for black-box transition tests"
)


# (from_status, to_status, expected_http_status, is_legal) — data table.
TRANSITION_CASES = [
    pytest.param("DRAFT", "VALIDATED", 200, True, id="legal_draft_to_validated"),
    pytest.param("VALIDATED", "TRANSMITTED", 200, True, id="legal_validated_to_transmitted"),
    pytest.param("TRANSMITTED", "ACKNOWLEDGED", 200, True, id="legal_transmitted_to_ack"),
    pytest.param("ACKNOWLEDGED", "PAID", 200, True, id="legal_ack_to_paid"),
    pytest.param("DRAFT", "PAID", 409, False, id="illegal_draft_to_paid"),
    pytest.param("DRAFT", "TRANSMITTED", 409, False, id="illegal_skip_validated"),
    pytest.param("PAID", "DRAFT", 409, False, id="illegal_reopen_paid"),
]


def _seed_claim(status: str) -> str:
    """Create a claim in a known status and return its id.

    INJECT YOUR LOGIC: implement against your real seeding/admin endpoint.
    """
    resp = requests.post(
        f"{API_BASE}/api/v1/claims/_seed",
        json={"status": status},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()["claim_id"]


@pytest.mark.parametrize("from_status,to_status,expected_http,is_legal", TRANSITION_CASES)
def test_transition_http_contract(
    from_status: str, to_status: str, expected_http: int, is_legal: bool
) -> None:
    """Drive a transition and assert ONLY on the black-box HTTP response."""
    claim_id = _seed_claim(from_status)

    resp = requests.patch(
        f"{API_BASE}/api/v1/claims/{claim_id}/status",
        json={"status": to_status},
        timeout=5,
    )

    assert resp.status_code == expected_http, (
        f"{from_status}->{to_status}: expected HTTP {expected_http}, "
        f"got {resp.status_code} ({resp.text})"
    )

    # For legal transitions the body should echo the new status; for illegal
    # ones the resource must remain unchanged (still observable via GET).
    if is_legal:
        assert resp.json().get("status") == to_status
    else:
        check = requests.get(f"{API_BASE}/api/v1/claims/{claim_id}", timeout=5)
        assert check.json().get("status") == from_status, (
            "illegal transition must not mutate the resource"
        )

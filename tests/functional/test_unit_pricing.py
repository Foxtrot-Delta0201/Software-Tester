"""Functional / Unit tests — pure logic with all DB calls MOCKED.

Unit tests must run with zero external dependencies. Here the database access
layer is replaced with a mock so we exercise ONLY the pricing logic.

INJECT YOUR LOGIC: replace ``price_repository`` / ``calculate_claim_total`` with
imports from your real application package.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest


# --- Stand-in business logic (replace with real imports) -------------------- #
def calculate_claim_total(repo, tariff_code: str, dos: str, quantity: int) -> Decimal:
    """Resolve a unit price via the repository and multiply by quantity.

    INJECT YOUR LOGIC: this is a placeholder that mirrors the real call shape.
    ``repo.get_price(code, dos)`` is the seam we mock in the tests below.
    """
    unit = repo.get_price(tariff_code, dos)
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    return Decimal(unit) * quantity


# --- Tests ------------------------------------------------------------------ #
@pytest.fixture()
def mock_repo() -> MagicMock:
    """A mocked price repository — no real DB connection is opened."""
    repo = MagicMock(name="PriceRepository")
    repo.get_price.return_value = Decimal("400.00")
    return repo


def test_total_uses_repository_price(mock_repo: MagicMock) -> None:
    total = calculate_claim_total(mock_repo, "0101", "2026-04-15", quantity=2)
    assert total == Decimal("800.00")
    # Verify the DB seam was called exactly as expected (interaction test).
    mock_repo.get_price.assert_called_once_with("0101", "2026-04-15")


def test_zero_quantity_rejected(mock_repo: MagicMock) -> None:
    with pytest.raises(ValueError):
        calculate_claim_total(mock_repo, "0101", "2026-04-15", quantity=0)


def test_repository_failure_propagates(mock_repo: MagicMock) -> None:
    # Simulate the DB layer raising; the unit under test must not swallow it.
    mock_repo.get_price.side_effect = RuntimeError("db unavailable")
    with pytest.raises(RuntimeError):
        calculate_claim_total(mock_repo, "0101", "2026-04-15", quantity=1)

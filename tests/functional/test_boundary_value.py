"""Functional / Boundary Value Analysis (BVA) — tariff price edge cases.

BVA targets the values AT and JUST BEYOND the edges of valid input partitions,
where off-by-one and inclusive/exclusive-boundary bugs hide.

Validity rule under test (replace with your real validator):
    * A tariff base price must be within [MIN_PRICE, MAX_PRICE].
    * Boundaries are INCLUSIVE.

INJECT YOUR LOGIC: swap ``validate_price`` for your production validator.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

MIN_PRICE = Decimal("0.00")
MAX_PRICE = Decimal("100000.00")


def validate_price(price: Decimal) -> bool:
    """Return True if price is within the inclusive valid range."""
    return MIN_PRICE <= price <= MAX_PRICE


# (value, expected_valid) pairs probing each boundary and its neighbours.
BVA_CASES = [
    (Decimal("-0.01"), False),         # just below minimum
    (MIN_PRICE, True),                 # exact minimum (inclusive)
    (Decimal("0.01"), True),           # just inside minimum
    (Decimal("400.00"), True),         # nominal interior value
    (Decimal("99999.99"), True),       # just inside maximum
    (MAX_PRICE, True),                 # exact maximum (inclusive)
    (Decimal("100000.01"), False),     # just above maximum
]


@pytest.mark.parametrize("price,expected", BVA_CASES)
def test_price_boundaries(price: Decimal, expected: bool) -> None:
    assert validate_price(price) is expected, (
        f"BVA failure at {price}: expected valid={expected}"
    )

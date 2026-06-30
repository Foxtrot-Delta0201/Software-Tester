"""Functional / Equivalence Partitioning (EP) — one representative per class.

EP divides the input domain into classes that should be handled identically,
then tests ONE representative from each — efficient coverage without redundancy.

Domain under test: medical-aid number format classification.
    * VALID    — 'MA-' prefix + 4 digits.
    * INVALID  — wrong prefix, wrong length, non-numeric body, empty.

INJECT YOUR LOGIC: replace ``classify_medical_aid_number`` with your validator.
"""

from __future__ import annotations

import pytest


def classify_medical_aid_number(value: str) -> str:
    """Return 'VALID' or 'INVALID' for a medical-aid number string."""
    if not value:
        return "INVALID"
    if not value.startswith("MA-"):
        return "INVALID"
    body = value[3:]
    return "VALID" if (len(body) == 4 and body.isdigit()) else "INVALID"


# One representative per equivalence class, labelled for traceability.
EP_CASES = [
    pytest.param("MA-0001", "VALID", id="valid_well_formed"),
    pytest.param("XX-0001", "INVALID", id="invalid_prefix"),
    pytest.param("MA-12", "INVALID", id="invalid_too_short"),
    pytest.param("MA-ABCD", "INVALID", id="invalid_non_numeric_body"),
    pytest.param("", "INVALID", id="invalid_empty"),
]


@pytest.mark.parametrize("value,expected", EP_CASES)
def test_medical_aid_classification(value: str, expected: str) -> None:
    assert classify_medical_aid_number(value) == expected

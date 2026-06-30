"""Specialized / AI testing — Master Data matching: Data Drift & Bias.

Foci-Med matches incoming free-text provider/discipline strings to canonical
master-data records using an ML matcher. Two failure modes matter here:

    1. DATA DRIFT — the live input distribution diverges from the training
       baseline, silently degrading match quality. We detect it with a
       Population Stability Index (PSI) over a categorical feature.
    2. BIAS — the matcher systematically REJECTS certain protected groups (here,
       medical disciplines). We assert approval-rate parity within a tolerance
       (a demographic-parity / disparate-impact style check).

INJECT YOUR LOGIC:
    * Replace ``predict_match`` with your real model's inference call.
    * Replace the baseline/live samples with real reference + production data.
"""

from __future__ import annotations

import math
from collections import Counter

import pytest

# Disciplines we must treat fairly (the "protected" categorical for this check).
DISCIPLINES = ["GP", "Physiotherapy", "Psychiatry", "Dentistry", "Optometry"]

# Tolerances — tune to your governance thresholds.
PSI_DRIFT_THRESHOLD = 0.25      # PSI > 0.25 => significant drift (industry rule of thumb)
MAX_APPROVAL_GAP = 0.15         # max allowed spread in approval rate across groups


# --- Placeholder model + data (replace with real artifacts) ----------------- #
def predict_match(discipline: str, provider_name: str) -> bool:
    """Return True if the record is matched/approved by the model.

    INJECT YOUR LOGIC: call your actual matcher. The placeholder approves most
    records uniformly so the bias test passes on healthy logic; flip a branch to
    see the test catch systematic rejection of a discipline.
    """
    # Deterministic pseudo-logic: approve unless the provider name is blank.
    return bool(provider_name.strip())


def _baseline_distribution() -> Counter:
    # Reference (training-time) discipline mix.
    return Counter({"GP": 50, "Physiotherapy": 20, "Psychiatry": 10,
                    "Dentistry": 12, "Optometry": 8})


def _live_distribution() -> Counter:
    # Production (current) discipline mix — close to baseline = no drift.
    return Counter({"GP": 48, "Physiotherapy": 22, "Psychiatry": 11,
                    "Dentistry": 11, "Optometry": 8})


# --- Drift -------------------------------------------------------------------#
def _psi(baseline: Counter, live: Counter, categories: list[str]) -> float:
    """Population Stability Index across categorical buckets."""
    base_total = sum(baseline.values()) or 1
    live_total = sum(live.values()) or 1
    psi = 0.0
    for cat in categories:
        # Floor proportions to avoid div-by-zero / log(0).
        b = max(baseline.get(cat, 0) / base_total, 1e-6)
        l = max(live.get(cat, 0) / live_total, 1e-6)
        psi += (l - b) * math.log(l / b)
    return psi


def test_no_significant_data_drift() -> None:
    psi = _psi(_baseline_distribution(), _live_distribution(), DISCIPLINES)
    assert psi < PSI_DRIFT_THRESHOLD, (
        f"Data drift detected: PSI={psi:.4f} exceeds {PSI_DRIFT_THRESHOLD}"
    )


# --- Bias --------------------------------------------------------------------#
def _approval_rates(samples_per_group: int = 100) -> dict[str, float]:
    """Compute per-discipline approval rate from the model."""
    rates: dict[str, float] = {}
    for discipline in DISCIPLINES:
        approvals = sum(
            predict_match(discipline, f"Provider {i}")
            for i in range(samples_per_group)
        )
        rates[discipline] = approvals / samples_per_group
    return rates


def test_no_discipline_bias() -> None:
    """No discipline may be systematically approved/rejected vs. the others."""
    rates = _approval_rates()
    spread = max(rates.values()) - min(rates.values())
    assert spread <= MAX_APPROVAL_GAP, (
        f"Bias detected: approval-rate spread {spread:.3f} exceeds "
        f"{MAX_APPROVAL_GAP}. Per-group rates: {rates}"
    )


@pytest.mark.parametrize("discipline", DISCIPLINES)
def test_each_discipline_has_nonzero_approval(discipline: str) -> None:
    """Guard against a single discipline being categorically rejected."""
    rate = sum(predict_match(discipline, f"Provider {i}") for i in range(50)) / 50
    assert rate > 0.0, f"Discipline '{discipline}' is being categorically rejected"

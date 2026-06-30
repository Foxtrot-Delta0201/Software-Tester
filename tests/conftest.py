"""Shared pytest configuration for the Foci-Med Omni-Channel test tree.

Registers custom markers so the orchestrator can select categories and so
`pytest --strict-markers` doesn't error on the labels used across suites.
"""

from __future__ import annotations


def pytest_configure(config) -> None:
    for marker in (
        "functional: functional correctness tests",
        "integration: API<->DB integration tests",
        "performance: load/stress/spike/soak (usually run via locust)",
        "specialized: AI/ML drift and bias tests",
        "blackbox: data-driven HTTP contract tests",
    ):
        config.addinivalue_line("markers", marker)

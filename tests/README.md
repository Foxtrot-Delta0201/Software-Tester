# Foci-Med Omni-Channel Test Suite

Directory layout consumed by `foci_orchestrator.py`:

```
tests/
├── conftest.py                  # shared markers
├── functional/                  # Pytest — Unit, Integration, BVA, EP
│   ├── test_unit_pricing.py             # unit, DB mocked
│   ├── test_integration_api_db.py       # API -> DB round trip (auto-skips)
│   ├── test_boundary_value.py           # tariff price edge cases
│   └── test_equivalence_partitioning.py # one representative per class
├── performance/                 # Locust — Spike & Soak
│   └── locustfile.py            # /api/v1/claims/submit workload
├── whitebox/                    # Coverage.py — branch + statement, fail < 90%
│   └── .coveragerc
├── specialized/                 # AI/ML — data drift (PSI) + bias parity
│   └── test_ai_matching_drift_bias.py
└── blackbox/                    # Data-driven HTTP state-transition contract
    └── test_state_transitions_blackbox.py
```

## Running

```bash
# Everything, orchestrated:
python foci_orchestrator.py --target-dir .

# A subset, in parallel:
python foci_orchestrator.py --target-dir . --parallel \
    --categories functional,whitebox,security

# Then visualize:
streamlit run qa_dashboard.py
```

Each file marks where to **inject your business logic** — the placeholders are
runnable stand-ins so the harness is green out of the box and turns red the
moment a real defect is wired in.

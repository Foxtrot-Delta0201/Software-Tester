"""Non-Functional performance suite — Spike & Soak via Locust.

Targets the claim submission endpoint ``/api/v1/claims/submit`` and models a
realistic medical-practice workload: many short reads (status checks, tariff
lookups) punctuated by heavier claim submissions.

Run profiles
------------
Spike  — ramp users up sharply, then drop, to probe elastic recovery::

    locust -f locustfile.py --headless -u 500 -r 200 -t 2m \
        --host http://localhost:8000

Soak   — moderate steady load held for hours to surface leaks/degradation::

    locust -f locustfile.py --headless -u 100 -r 10 -t 4h \
        --host http://localhost:8000

The orchestrator drives a short bounded smoke version of this file.

INJECT YOUR LOGIC: set realistic auth headers, payload fields, and any
tenant-routing your API requires.
"""

from __future__ import annotations

import random
import uuid

from locust import HttpUser, LoadTestShape, between, task

# A pool of pretend tenants/practices so requests aren't single-key hot.
_TENANTS = [str(uuid.uuid4()) for _ in range(10)]
_TARIFF_CODES = ["0101", "0190", "0191", "1211", "0146"]


class PracticeUser(HttpUser):
    """Simulates a busy practice's mix of reads and claim submissions."""

    # Think-time between actions — humans aren't infinitely fast.
    wait_time = between(0.5, 3.0)

    def on_start(self) -> None:
        """INJECT YOUR LOGIC: authenticate once per simulated user here."""
        self.tenant_id = random.choice(_TENANTS)
        # self.client.headers.update({"Authorization": "Bearer <token>"})

    @task(5)
    def check_health(self) -> None:
        """Lightweight read — dominant traffic in a real practice."""
        self.client.get("/health", name="GET /health")

    @task(3)
    def lookup_tariff(self) -> None:
        code = random.choice(_TARIFF_CODES)
        self.client.get(f"/api/v1/tariffs/{code}", name="GET /tariffs/:code")

    @task(2)
    def submit_claim(self) -> None:
        """Heavier write path — the endpoint under primary scrutiny."""
        payload = {
            "tariff_code": random.choice(_TARIFF_CODES),
            "date_of_service": "2026-04-15",
            "tenant_id": self.tenant_id,
            "patient_ref": str(uuid.uuid4()),
        }
        with self.client.post(
            "/api/v1/claims/submit",
            json=payload,
            name="POST /claims/submit",
            catch_response=True,
        ) as resp:
            # Treat anything other than 2xx as a failure for perf accounting.
            if resp.status_code >= 400:
                resp.failure(f"submit failed: HTTP {resp.status_code}")


class SpikeShape(LoadTestShape):
    """Optional programmatic SPIKE profile.

    Enable with ``--shape`` aware runs (or just use the -u/-r CLI flags above).
    Stages: warm -> sharp spike -> recovery -> baseline.
    """

    stages = [
        {"duration": 30, "users": 20, "spawn_rate": 5},     # warm-up
        {"duration": 60, "users": 500, "spawn_rate": 200},  # spike
        {"duration": 90, "users": 50, "spawn_rate": 50},    # recovery
        {"duration": 150, "users": 100, "spawn_rate": 10},  # steady baseline
    ]

    def tick(self):
        run_time = self.get_run_time()
        elapsed = 0
        for stage in self.stages:
            elapsed += stage["duration"]
            if run_time < elapsed:
                return stage["users"], stage["spawn_rate"]
        return None

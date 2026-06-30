"""Foci-Med Test Runner.

Wraps the existing pytest suites and the Foci orchestrator as async
subprocesses, streaming stdout line-by-line into the caller's asyncio.Queue
so the FastAPI SSE endpoint can forward every log line to the browser in
real time.

Supported suite keys (map to actual test paths)
------------------------------------------------
  functional      → tests/functional/
  blackbox        → tests/blackbox/
  specialized     → tests/specialized/
  performance     → tests/performance/locustfile.py  (locust smoke)
  bulk_throughput → tests/performance/test_bulk_throughput.py
  rls             → test_rls_leak_detector.py
  tariffs         → test_temporal_tariffs.py
  chaos           → test_claims_chaos.py
  security        → bandit static scan
  all             → foci_orchestrator.py (runs every category)
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any

# ── Suite → command mapping ────────────────────────────────────────────────── #
# Each value is a callable(project_dir) -> list[str] (the argv list to run).

def _pytest(rel_path: str):
    def _build(d: str) -> list[str]:
        return [sys.executable, "-m", "pytest", os.path.join(d, rel_path), "-v", "--tb=short"]
    return _build

def _locust(d: str) -> list[str]:
    lf = os.path.join(d, "tests", "performance", "locustfile.py")
    return [
        "locust", "-f", lf, "--headless",
        "-u", "25", "-r", "5", "-t", "30s",
        "--host", "http://localhost:8000",
    ]

def _orchestrator(d: str) -> list[str]:
    return [sys.executable, os.path.join(d, "foci_orchestrator.py"), "--target-dir", d]

def _bandit(d: str) -> list[str]:
    return [sys.executable, "-m", "bandit", "-r", d, "-x", ".git,venv,.venv,node_modules,frontend"]

SUITE_COMMANDS: dict[str, Any] = {
    "functional":      _pytest("tests/functional"),
    "blackbox":        _pytest("tests/blackbox"),
    "specialized":     _pytest("tests/specialized"),
    "bulk_throughput": _pytest("tests/performance/test_bulk_throughput.py"),
    "rls":             _pytest("test_rls_leak_detector.py"),
    "tariffs":         _pytest("test_temporal_tariffs.py"),
    "chaos":           _pytest("test_claims_chaos.py"),
    "performance":     _locust,
    "security":        _bandit,
    "all":             _orchestrator,
}


# ── Core runner ────────────────────────────────────────────────────────────── #
async def _stream_process(
    cmd: list[str],
    cwd: str,
    q: asyncio.Queue,
    env: dict | None = None,
) -> int:
    """Run cmd as a subprocess; stream every stdout/stderr line into q.  Returns exit code."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
        env=env,
    )

    async def _read_lines():
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip()
            if line:
                await q.put({"level": "log", "msg": line})

    await _read_lines()
    await proc.wait()
    return proc.returncode or 0


async def run_tests(
    q: asyncio.Queue,
    project_dir: str,
    suites: list[str],
    cfg: dict,
) -> dict:
    """Run the requested suites sequentially; stream output into q."""

    async def log(msg: str, level: str = "info"):
        await q.put({"level": level, "msg": msg})

    project_dir = os.path.abspath(project_dir)
    results: dict[str, str] = {}

    # Build environment with DB credentials for subprocesses.
    env = os.environ.copy()
    env.update({
        "FOCIMED_DB_HOST":     cfg.get("db_host",     "localhost"),
        "FOCIMED_DB_PORT":     str(cfg.get("db_port", 5432)),
        "FOCIMED_DB_NAME":     cfg.get("db_name",     "focimed_core"),
        "FOCIMED_SUPERUSER":   cfg.get("db_user",     "postgres"),
        "POSTGRES_PASSWORD":   cfg.get("db_password", "focimed_local_secret"),
        "FOCIMED_APP_USER":    cfg.get("app_user",    "app_user"),
        "FOCIMED_APP_PASSWORD":cfg.get("app_password","app_user_local_secret"),
        "PYTHONUNBUFFERED":    "1",
    })

    total_start = time.perf_counter()
    await log(f"Project dir: {project_dir}")
    await log(f"Suites: {', '.join(suites)}")

    for suite in suites:
        builder = SUITE_COMMANDS.get(suite)
        if builder is None:
            await log(f"[{suite}] Unknown suite — skipped", "warning")
            results[suite] = "SKIPPED"
            continue

        cmd = builder(project_dir)
        await log(f"\n{'─'*50}", "separator")
        await log(f"▶ Running suite: {suite}", "header")
        await log(f"  cmd: {' '.join(cmd)}")
        await log(f"{'─'*50}", "separator")

        suite_start = time.perf_counter()
        rc = await _stream_process(cmd, project_dir, q, env=env)
        elapsed = time.perf_counter() - suite_start

        status = "PASS" if rc == 0 else "FAIL"
        results[suite] = status
        level = "success" if rc == 0 else "error"
        await log(
            f"◀ Suite [{suite}]: {status}  ({elapsed:.1f}s,  exit {rc})", level
        )

    total_elapsed = time.perf_counter() - total_start
    passed  = sum(1 for s in results.values() if s == "PASS")
    failed  = sum(1 for s in results.values() if s == "FAIL")
    skipped = sum(1 for s in results.values() if s == "SKIPPED")

    summary_msg = (
        f"All suites done in {total_elapsed:.1f}s — "
        f"PASS: {passed}  FAIL: {failed}  SKIPPED: {skipped}"
    )
    await log(f"\n{'═'*50}", "separator")
    await log(summary_msg, "success" if failed == 0 else "error")

    summary = {
        "suites":   results,
        "passed":   passed,
        "failed":   failed,
        "skipped":  skipped,
        "elapsed_s":round(total_elapsed, 2),
        "overall":  "PASS" if failed == 0 else "FAIL",
    }
    await q.put({"done": True, "level": "success" if failed == 0 else "error",
                 "msg": summary_msg, "summary": summary})
    return summary

"""Foci-Med Universal Test Orchestrator.

Discovers and executes every category of test in a target project directory,
then aggregates exit codes, stdout/stderr, and any tool-emitted JSON reports
into a single master telemetry file: ``foci_omni_telemetry.json``.

Supported runners (auto-skipped when the tool or its inputs are absent):

    Category          Tool            Trigger condition
    ----------------  --------------  ----------------------------------------
    Functional        pytest          tests/functional (or any test_*.py)
    White-Box         coverage.py     tests/whitebox/.coveragerc present
    Non-Functional    locust          tests/performance/locustfile.py present
    Security          bandit          any *.py under target (headless)
    End-to-End / UI   playwright      tests/e2e present + playwright importable

Design principles:
    * **Isolation** — each runner executes in its own subprocess; a crash in one
      never takes down the orchestrator. Failures are captured, logged, and the
      run proceeds to the next suite.
    * **Evidence-first** — every runner writes a JSON artifact into a temp
      reports dir; the orchestrator ingests those plus raw console output.
    * **Determinism** — exit codes are normalized into PASS/FAIL/ERROR/SKIPPED.

Usage::

    python foci_orchestrator.py --target-dir /path/to/project
    python foci_orchestrator.py --target-dir . --parallel --categories functional,security
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | orchestrator | %(message)s",
)
logger = logging.getLogger("foci_orchestrator")

# Normalized outcome vocabulary.
PASS = "PASS"
FAIL = "FAIL"
ERROR = "ERROR"      # Runner itself crashed / could not start.
SKIPPED = "SKIPPED"  # Tool or inputs not present.

# Per-runner wall-clock ceiling (seconds) to stop a hung suite blocking the run.
DEFAULT_TIMEOUT = 1800


@dataclass
class SuiteTelemetry:
    """Normalized result for a single test category."""

    category: str
    tool: str
    status: str = SKIPPED
    exit_code: Optional[int] = None
    duration_s: float = 0.0
    command: list[str] = field(default_factory=list)
    stdout_tail: str = ""
    stderr_tail: str = ""
    report_file: Optional[str] = None
    report_json: Optional[dict] = None
    note: str = ""


def _tail(text: str, max_chars: int = 4000) -> str:
    """Keep telemetry compact: retain only the trailing slice of console output."""
    if not text:
        return ""
    return text if len(text) <= max_chars else "...<truncated>...\n" + text[-max_chars:]


def _tool_available(tool: str) -> bool:
    """Return True if a CLI tool or python module entry point is resolvable."""
    if shutil.which(tool):
        return True
    # Fall back to `python -m <tool>` style availability.
    probe = subprocess.run(
        [sys.executable, "-m", tool, "--version"],
        capture_output=True, text=True,
    )
    return probe.returncode == 0


def _run(command: list[str], cwd: str, timeout: int) -> tuple[int, str, str]:
    """Execute a subprocess, capturing output. Never raises on tool failure."""
    proc = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# --------------------------------------------------------------------------- #
# Individual runners. Each returns a SuiteTelemetry and must not raise.
# --------------------------------------------------------------------------- #
def run_functional(target: str, reports: str, timeout: int) -> SuiteTelemetry:
    """Pytest across functional/integration/system/smoke/regression tests."""
    t = SuiteTelemetry(category="functional", tool="pytest")
    test_root = _first_existing(target, ["tests/functional", "tests", "."])
    if not _tool_available("pytest"):
        t.note = "pytest not installed"
        return t

    report_path = os.path.join(reports, "functional_pytest.json")
    t.command = [
        sys.executable, "-m", "pytest", test_root,
        "-q", "--json-report", f"--json-report-file={report_path}",
    ]
    return _exec_and_capture(t, target, timeout, report_path)


def run_whitebox(target: str, reports: str, timeout: int) -> SuiteTelemetry:
    """Coverage.py run enforcing the project's .coveragerc thresholds."""
    t = SuiteTelemetry(category="whitebox", tool="coverage")
    coveragerc = os.path.join(target, "tests", "whitebox", ".coveragerc")
    if not os.path.isfile(coveragerc):
        t.note = "no tests/whitebox/.coveragerc found"
        return t
    if not _tool_available("coverage"):
        t.note = "coverage.py not installed"
        return t

    json_path = os.path.join(reports, "whitebox_coverage.json")
    # Run the suite under coverage, then emit a JSON summary and enforce the gate.
    rc_run, out1, err1 = _safe_run(
        [sys.executable, "-m", "coverage", "run",
         f"--rcfile={coveragerc}", "-m", "pytest", "-q"],
        target, timeout, t,
    )
    if t.status == ERROR:
        return t
    _safe_run([sys.executable, "-m", "coverage", "json",
               f"--rcfile={coveragerc}", "-o", json_path], target, timeout, t)
    rc_gate, out2, err2 = _safe_run(
        [sys.executable, "-m", "coverage", "report", f"--rcfile={coveragerc}"],
        target, timeout, t,
    )
    t.exit_code = rc_gate
    t.command = ["coverage run -> json -> report (fail_under from .coveragerc)"]
    t.stdout_tail = _tail((out1 or "") + "\n" + (out2 or ""))
    t.stderr_tail = _tail((err1 or "") + "\n" + (err2 or ""))
    t.status = PASS if rc_gate == 0 else FAIL
    t.report_file = json_path if os.path.isfile(json_path) else None
    t.report_json = _load_json(json_path)
    return t


def run_performance(target: str, reports: str, timeout: int) -> SuiteTelemetry:
    """Locust headless run (short bounded window for CI smoke of perf suite)."""
    t = SuiteTelemetry(category="performance", tool="locust")
    locustfile = os.path.join(target, "tests", "performance", "locustfile.py")
    if not os.path.isfile(locustfile):
        t.note = "no tests/performance/locustfile.py found"
        return t
    if not _tool_available("locust"):
        t.note = "locust not installed"
        return t

    host = os.environ.get("FOCI_PERF_HOST", "http://localhost:8000")
    csv_prefix = os.path.join(reports, "performance_locust")
    t.command = [
        "locust", "-f", locustfile, "--headless",
        "-u", os.environ.get("FOCI_PERF_USERS", "25"),
        "-r", os.environ.get("FOCI_PERF_SPAWN", "5"),
        "-t", os.environ.get("FOCI_PERF_DURATION", "30s"),
        "--host", host, "--csv", csv_prefix, "--json",
    ]
    rc, out, err = _safe_run(t.command, target, timeout, t)
    if t.status == ERROR:
        return t
    t.exit_code = rc
    t.stdout_tail = _tail(out)
    t.stderr_tail = _tail(err)
    # Locust prints aggregated stats as JSON to stdout with --json.
    t.report_json = _parse_trailing_json(out)
    stats_csv = f"{csv_prefix}_stats.csv"
    t.report_file = stats_csv if os.path.isfile(stats_csv) else None
    t.status = PASS if rc == 0 else FAIL
    return t


def run_security(target: str, reports: str, timeout: int) -> SuiteTelemetry:
    """Bandit static security scan (grey-box) over the project sources."""
    t = SuiteTelemetry(category="security", tool="bandit")
    if not _tool_available("bandit"):
        t.note = "bandit not installed (OWASP ZAP CLI is an alternative)"
        return t

    report_path = os.path.join(reports, "security_bandit.json")
    t.command = [sys.executable, "-m", "bandit", "-r", target,
                 "-f", "json", "-o", report_path,
                 "-x", ".git,venv,.venv,node_modules"]
    rc, out, err = _safe_run(t.command, target, timeout, t)
    if t.status == ERROR:
        return t
    t.exit_code = rc
    t.stdout_tail = _tail(out)
    t.stderr_tail = _tail(err)
    t.report_file = report_path if os.path.isfile(report_path) else None
    t.report_json = _load_json(report_path)
    # Bandit exits non-zero when issues are found; treat HIGH severity as FAIL.
    high = 0
    if isinstance(t.report_json, dict):
        high = sum(
            1 for r in t.report_json.get("results", [])
            if r.get("issue_severity", "").upper() == "HIGH"
        )
    t.note = f"{high} HIGH-severity finding(s)"
    t.status = FAIL if high > 0 else PASS
    return t


def run_bulk_throughput(target: str, reports: str, timeout: int) -> SuiteTelemetry:
    """Async bulk data-entry throughput suite: 5 000 records in < 10 min."""
    t = SuiteTelemetry(category="bulk_throughput", tool="pytest")
    suite_file = os.path.join(target, "tests", "performance", "test_bulk_throughput.py")
    if not os.path.isfile(suite_file):
        t.note = "no tests/performance/test_bulk_throughput.py found"
        return t
    if not _tool_available("pytest"):
        t.note = "pytest not installed"
        return t

    report_path = os.path.join(reports, "bulk_throughput_pytest.json")
    t.command = [
        sys.executable, "-m", "pytest", suite_file,
        "-v", "-s",
        "--json-report", f"--json-report-file={report_path}",
    ]
    return _exec_and_capture(t, target, timeout, report_path)


def run_e2e(target: str, reports: str, timeout: int) -> SuiteTelemetry:
    """End-to-end / UI suite via Playwright's pytest plugin (Selenium fallback)."""
    t = SuiteTelemetry(category="e2e", tool="playwright")
    e2e_root = _first_existing(target, ["tests/e2e", "tests/ui"])
    if e2e_root is None:
        t.note = "no tests/e2e or tests/ui directory found"
        return t
    if not _module_importable("playwright"):
        t.tool = "selenium" if _module_importable("selenium") else "playwright"
        if not _module_importable("selenium"):
            t.note = "neither playwright nor selenium installed"
            return t

    report_path = os.path.join(reports, "e2e_pytest.json")
    t.command = [
        sys.executable, "-m", "pytest", e2e_root,
        "-q", "--json-report", f"--json-report-file={report_path}",
    ]
    return _exec_and_capture(t, target, timeout, report_path)


# --------------------------------------------------------------------------- #
# Shared execution helpers
# --------------------------------------------------------------------------- #
def _exec_and_capture(
    t: SuiteTelemetry, cwd: str, timeout: int, report_path: str
) -> SuiteTelemetry:
    """Run a pytest-style command and ingest its JSON report."""
    rc, out, err = _safe_run(t.command, cwd, timeout, t)
    if t.status == ERROR:
        return t
    t.exit_code = rc
    t.stdout_tail = _tail(out)
    t.stderr_tail = _tail(err)
    t.report_file = report_path if os.path.isfile(report_path) else None
    t.report_json = _load_json(report_path)
    # pytest: 0 = all passed, 1 = tests failed, 5 = no tests collected.
    if rc == 0:
        t.status = PASS
    elif rc == 5:
        t.status = SKIPPED
        t.note = "no tests collected"
    else:
        t.status = FAIL
    return t


def _safe_run(
    command: list[str], cwd: str, timeout: int, t: SuiteTelemetry
) -> tuple[int, str, str]:
    """Wrapper that converts ANY runner failure into telemetry, never a crash."""
    try:
        return _run(command, cwd, timeout)
    except subprocess.TimeoutExpired:
        t.status = ERROR
        t.note = f"timed out after {timeout}s"
        logger.error("%s/%s timed out", t.category, t.tool)
        return -1, "", "timeout"
    except FileNotFoundError as exc:
        t.status = ERROR
        t.note = f"executable not found: {exc}"
        logger.error("%s/%s executable missing: %s", t.category, t.tool, exc)
        return -1, "", str(exc)
    except Exception as exc:  # noqa: BLE001 - orchestrator must never die
        t.status = ERROR
        t.note = f"unexpected runner error: {exc}"
        logger.exception("%s/%s crashed", t.category, t.tool)
        return -1, "", str(exc)


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _parse_trailing_json(text: str) -> Optional[dict]:
    """Extract the last JSON object/array from mixed console output."""
    if not text:
        return None
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.rfind(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return {"data": json.loads(text[start:end + 1])}
            except json.JSONDecodeError:
                continue
    return None


def _first_existing(target: str, candidates: list[str]) -> Optional[str]:
    for rel in candidates:
        path = os.path.join(target, rel)
        if os.path.exists(path):
            return path
    return None


def _module_importable(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is not None


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
RUNNERS: dict[str, Callable[[str, str, int], SuiteTelemetry]] = {
    "functional": run_functional,
    "whitebox": run_whitebox,
    "performance": run_performance,
    "bulk_throughput": run_bulk_throughput,
    "security": run_security,
    "e2e": run_e2e,
}


def orchestrate(
    target_dir: str,
    categories: list[str],
    parallel: bool,
    timeout: int,
    output: str,
) -> dict:
    """Run the selected categories and write the unified telemetry file."""
    target_dir = os.path.abspath(target_dir)
    if not os.path.isdir(target_dir):
        raise NotADirectoryError(f"--target-dir does not exist: {target_dir}")

    reports_dir = tempfile.mkdtemp(prefix="foci_reports_")
    logger.info("Target: %s | categories: %s | parallel: %s",
                target_dir, ",".join(categories), parallel)
    logger.info("Intermediate reports: %s", reports_dir)

    selected = [(c, RUNNERS[c]) for c in categories if c in RUNNERS]
    results: list[SuiteTelemetry] = []

    def _invoke(item: tuple[str, Callable]) -> SuiteTelemetry:
        name, fn = item
        started = dt.datetime.now()
        logger.info("-> running %s", name)
        # The runner functions already self-protect, but wrap once more so a
        # truly unexpected fault still yields telemetry instead of aborting.
        try:
            tele = fn(target_dir, reports_dir, timeout)
        except Exception as exc:  # noqa: BLE001
            tele = SuiteTelemetry(category=name, tool="unknown",
                                  status=ERROR, note=f"orchestrator fault: {exc}")
            logger.exception("Runner %s faulted at orchestrator level", name)
        tele.duration_s = round((dt.datetime.now() - started).total_seconds(), 3)
        logger.info("<- %s: %s (%.2fs) %s",
                    name, tele.status, tele.duration_s,
                    f"[{tele.note}]" if tele.note else "")
        return tele

    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected) or 1) as pool:
            results = list(pool.map(_invoke, selected))
    else:
        results = [_invoke(item) for item in selected]

    telemetry = _assemble(target_dir, results)
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(telemetry, fh, indent=2)
    logger.info("Wrote unified telemetry -> %s", output)
    return telemetry


def _assemble(target_dir: str, results: list[SuiteTelemetry]) -> dict:
    """Roll individual suite telemetry into the master document."""
    counts = {s: 0 for s in (PASS, FAIL, ERROR, SKIPPED)}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    executed = [r for r in results if r.status in (PASS, FAIL, ERROR)]
    overall = PASS
    if any(r.status in (FAIL, ERROR) for r in executed):
        overall = FAIL
    elif not executed:
        overall = SKIPPED

    return {
        "schema": "foci.omni.telemetry/v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target_dir": target_dir,
        "overall_status": overall,
        "category_counts": counts,
        "suites": [asdict(r) for r in results],
    }


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Foci-Med Universal Test Orchestrator.",
    )
    parser.add_argument("--target-dir", required=True,
                        help="Path to the project folder to test.")
    parser.add_argument("--categories",
                        default="functional,whitebox,performance,bulk_throughput,security,e2e",
                        help="Comma-separated subset of: "
                             "functional,whitebox,performance,bulk_throughput,security,e2e")
    parser.add_argument("--parallel", action="store_true",
                        help="Run runners concurrently (default: sequential).")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Per-runner timeout in seconds (default {DEFAULT_TIMEOUT}).")
    parser.add_argument("--output", default="foci_omni_telemetry.json",
                        help="Master telemetry output path.")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    try:
        telemetry = orchestrate(
            target_dir=args.target_dir,
            categories=categories,
            parallel=args.parallel,
            timeout=args.timeout,
            output=args.output,
        )
    except (NotADirectoryError, OSError) as exc:
        logger.error("Fatal: %s", exc)
        return 2

    # Exit code mirrors the aggregate so CI can gate on the orchestrator alone.
    return 0 if telemetry["overall_status"] in (PASS, SKIPPED) else 1


if __name__ == "__main__":
    raise SystemExit(main())

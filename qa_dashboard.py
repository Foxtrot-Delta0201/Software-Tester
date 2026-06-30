"""Foci-Med QA Telemetry Dashboard (Streamlit).

Reads ``foci_omni_telemetry.json`` produced by ``foci_orchestrator.py`` and
renders an interactive, multi-page view of Functional, Non-Functional,
Specialized, White-Box and Black-Box results.

Run::

    streamlit run qa_dashboard.py
    # or point at a specific file:
    FOCI_TELEMETRY=/path/to/foci_omni_telemetry.json streamlit run qa_dashboard.py

Design notes:
    * Strict typing throughout; all parsing is defensive so a missing or skipped
      suite degrades to a clear "not available" state instead of crashing.
    * Plotly is used for performance line charts and coverage gauges.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import streamlit as st

try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:  # pragma: no cover - dashboard still works without plotly
    _HAS_PLOTLY = False

DEFAULT_TELEMETRY = os.getenv("FOCI_TELEMETRY", "foci_omni_telemetry.json")

PASS, FAIL, ERROR, SKIPPED = "PASS", "FAIL", "ERROR", "SKIPPED"
_STATUS_COLOR = {PASS: "#1a9850", FAIL: "#d73027", ERROR: "#f46d43", SKIPPED: "#999999"}


# --------------------------------------------------------------------------- #
# Typed model
# --------------------------------------------------------------------------- #
@dataclass
class Suite:
    category: str
    tool: str
    status: str
    exit_code: Optional[int]
    duration_s: float
    note: str
    report_json: Optional[dict[str, Any]]
    stdout_tail: str
    stderr_tail: str


@dataclass
class Telemetry:
    generated_at: str
    target_dir: str
    overall_status: str
    category_counts: dict[str, int] = field(default_factory=dict)
    suites: list[Suite] = field(default_factory=list)

    def suite(self, category: str) -> Optional[Suite]:
        return next((s for s in self.suites if s.category == category), None)


@st.cache_data(show_spinner=False)
def load_telemetry(path: str) -> Optional[Telemetry]:
    """Load and normalize the telemetry file; return None if unavailable."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    suites = [
        Suite(
            category=str(s.get("category", "unknown")),
            tool=str(s.get("tool", "unknown")),
            status=str(s.get("status", SKIPPED)),
            exit_code=s.get("exit_code"),
            duration_s=float(s.get("duration_s", 0.0) or 0.0),
            note=str(s.get("note", "")),
            report_json=s.get("report_json"),
            stdout_tail=str(s.get("stdout_tail", "")),
            stderr_tail=str(s.get("stderr_tail", "")),
        )
        for s in raw.get("suites", [])
    ]
    return Telemetry(
        generated_at=str(raw.get("generated_at", "unknown")),
        target_dir=str(raw.get("target_dir", "unknown")),
        overall_status=str(raw.get("overall_status", SKIPPED)),
        category_counts=dict(raw.get("category_counts", {})),
        suites=suites,
    )


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _status_badge(status: str) -> str:
    color = _STATUS_COLOR.get(status, "#999999")
    return f"<span style='color:{color};font-weight:700'>{status}</span>"


def _functional_summary(t: Telemetry) -> tuple[int, int, int]:
    """Return (passed, total, failed) from the functional pytest report."""
    suite = t.suite("functional")
    if not suite or not isinstance(suite.report_json, dict):
        return (0, 0, 0)
    summary = suite.report_json.get("summary", {}) or {}
    passed = int(summary.get("passed", 0))
    total = int(summary.get("total", 0))
    failed = int(summary.get("failed", 0)) + int(summary.get("error", 0))
    return (passed, total, failed)


def _gauge(label: str, value: float, threshold: float = 90.0):
    """Plotly gauge for a coverage percentage."""
    if not _HAS_PLOTLY:
        st.progress(min(value / 100.0, 1.0), text=f"{label}: {value:.1f}%")
        return
    color = _STATUS_COLOR[PASS] if value >= threshold else _STATUS_COLOR[FAIL]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": label},
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "threshold": {
                "line": {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": threshold,
            },
        },
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_overview(t: Telemetry) -> None:
    st.header("Overview")
    passed, total, failed = _functional_summary(t)
    pass_rate = (passed / total * 100.0) if total else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Pass Rate", f"{pass_rate:.1f}%")
    c2.metric("Functional Tests Run", f"{total}")
    c3.metric("Failures", f"{failed}")
    c4.markdown("**Run status**")
    c4.markdown(_status_badge(t.overall_status), unsafe_allow_html=True)

    st.divider()
    # POPIA / HIPAA indicator is derived from the security/compliance suites.
    sec = t.suite("security")
    compliance_status = sec.status if sec else SKIPPED
    st.subheader("POPIA / HIPAA Compliance")
    if compliance_status == SKIPPED:
        st.warning("Compliance/security suite was skipped during this run.")
    else:
        st.markdown(
            f"Status: {_status_badge(compliance_status)}"
            + (f" — {sec.note}" if sec and sec.note else ""),
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("Suite category counts")
    st.bar_chart(t.category_counts or {"(none)": 0})
    st.caption(f"Target: `{t.target_dir}`  •  Generated: {t.generated_at}")


def page_compliance(t: Telemetry) -> None:
    st.header("Compliance & Security")
    for category in ("security", "functional"):
        suite = t.suite(category)
        st.subheader(category.title())
        if not suite or suite.status == SKIPPED:
            st.info(f"`{category}` suite not available in this run.")
            continue
        st.markdown(
            f"Tool: `{suite.tool}` • Status: {_status_badge(suite.status)}"
            + (f" • {suite.note}" if suite.note else ""),
            unsafe_allow_html=True,
        )
        if category == "security" and isinstance(suite.report_json, dict):
            results = suite.report_json.get("results", [])
            if results:
                rows = [
                    {
                        "severity": r.get("issue_severity"),
                        "confidence": r.get("issue_confidence"),
                        "test": r.get("test_name"),
                        "file": r.get("filename"),
                        "line": r.get("line_number"),
                    }
                    for r in results
                ]
                st.dataframe(rows, use_container_width=True)
            else:
                st.success("No security findings reported.")


def page_performance(t: Telemetry) -> None:
    st.header("Performance (Load / Stress / Spike / Soak)")
    suite = t.suite("performance")
    if not suite or suite.status == SKIPPED:
        st.info("Performance suite not available — run the Locust profile to populate.")
        return

    data = _extract_locust_series(suite)
    if not data:
        st.warning("Performance suite ran but emitted no parseable metrics.")
        st.code(suite.stdout_tail or "(no output captured)")
        return

    names = [d["name"] for d in data]
    median = [d["median_response_time"] for d in data]
    p95 = [d["p95_response_time"] for d in data]
    rps = [d["rps"] for d in data]

    st.subheader("Response Time by Endpoint (ms)")
    if _HAS_PLOTLY:
        fig = go.Figure()
        fig.add_bar(name="Median", x=names, y=median)
        fig.add_bar(name="p95", x=names, y=p95)
        fig.update_layout(barmode="group", height=350, margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart({"median": dict(zip(names, median)), "p95": dict(zip(names, p95))})

    st.subheader("Throughput (requests / sec)")
    st.line_chart(dict(zip(names, rps)) if names else {"(none)": 0})


def page_coverage(t: Telemetry) -> None:
    st.header("White-Box Coverage")
    suite = t.suite("whitebox")
    if not suite or suite.status == SKIPPED:
        st.info("Coverage suite not available — run with a tests/whitebox/.coveragerc.")
        return

    stmt, branch = _extract_coverage(suite)
    # Path coverage is not measured by coverage.py; show branch as its proxy.
    c1, c2, c3 = st.columns(3)
    with c1:
        _gauge("Statement", stmt)
    with c2:
        _gauge("Branch", branch)
    with c3:
        _gauge("Path (proxy = branch)", branch)

    gate = PASS if (stmt >= 90 and branch >= 90) else FAIL
    st.markdown(f"90% gate: {_status_badge(gate)}", unsafe_allow_html=True)


def page_functional(t: Telemetry) -> None:
    st.header("Functional Breakdown & I/O Explorer")
    rows = _collect_test_rows(t)
    if not rows:
        st.info("No per-test detail available in this run.")
        return

    categories = sorted({r["category"] for r in rows})
    outcomes = sorted({r["outcome"] for r in rows})
    col1, col2 = st.columns(2)
    sel_cat = col1.multiselect("Category", categories, default=categories)
    sel_out = col2.multiselect("Outcome", outcomes, default=outcomes)
    query = st.text_input("Filter by test name contains", "")

    filtered = [
        r for r in rows
        if r["category"] in sel_cat
        and r["outcome"] in sel_out
        and query.lower() in r["test"].lower()
    ]
    st.caption(f"{len(filtered)} / {len(rows)} tests shown")
    st.dataframe(filtered, use_container_width=True)

    st.subheader("Test Input / Output Explorer")
    if filtered:
        names = [r["test"] for r in filtered]
        chosen = st.selectbox("Inspect a specific test", names)
        record = next((r for r in filtered if r["test"] == chosen), None)
        if record:
            ic, oc = st.columns(2)
            ic.markdown("**Input / parameters**")
            ic.json(record.get("input", {"note": "no captured input for this test"}))
            oc.markdown("**Outcome**")
            oc.json({
                "expected": record.get("expected", "pass"),
                "actual": record["outcome"],
                "duration_s": record.get("duration", 0.0),
            })


# --------------------------------------------------------------------------- #
# Extraction helpers (all defensive)
# --------------------------------------------------------------------------- #
def _extract_locust_series(suite: Suite) -> list[dict[str, Any]]:
    """Normalize Locust per-endpoint stats into chartable dicts."""
    report = suite.report_json
    entries: list[dict[str, Any]] = []
    payload: Any = None
    if isinstance(report, dict):
        payload = report.get("data", report)
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("stats", payload.get("entries", []))
    else:
        records = []

    for r in records or []:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or r.get("Name") or "aggregate"
        if name in ("Aggregated", "Total"):
            continue
        entries.append({
            "name": str(name),
            "median_response_time": float(
                r.get("median_response_time", r.get("Median Response Time", 0)) or 0
            ),
            "p95_response_time": float(
                r.get("response_time_percentile_0.95",
                      r.get("95%", r.get("p95", 0))) or 0
            ),
            "rps": float(r.get("current_rps", r.get("Requests/s", 0)) or 0),
        })
    return entries


def _extract_coverage(suite: Suite) -> tuple[float, float]:
    """Return (statement_pct, branch_pct) from coverage.py JSON."""
    report = suite.report_json
    if not isinstance(report, dict):
        return (0.0, 0.0)
    totals = report.get("totals", {}) or {}
    stmt = float(totals.get("percent_covered", 0.0) or 0.0)
    covered_branches = float(totals.get("covered_branches", 0) or 0)
    num_branches = float(totals.get("num_branches", 0) or 0)
    branch = (covered_branches / num_branches * 100.0) if num_branches else stmt
    return (round(stmt, 2), round(branch, 2))


def _collect_test_rows(t: Telemetry) -> list[dict[str, Any]]:
    """Flatten every suite's pytest-json tests into explorer rows."""
    rows: list[dict[str, Any]] = []
    for suite in t.suites:
        report = suite.report_json
        if not isinstance(report, dict):
            continue
        for test in report.get("tests", []) or []:
            if not isinstance(test, dict):
                continue
            # pytest-json-report stores parametrized inputs under call/user_properties;
            # fall back to the nodeid's parameter slice for the input view.
            nodeid = str(test.get("nodeid", "<unknown>"))
            param = nodeid.split("[", 1)[1].rstrip("]") if "[" in nodeid else None
            rows.append({
                "category": suite.category,
                "test": nodeid,
                "outcome": str(test.get("outcome", "unknown")),
                "duration": float(test.get("call", {}).get("duration", 0.0) or 0.0)
                if isinstance(test.get("call"), dict) else 0.0,
                "input": {"parameters": param} if param else {},
                "expected": "pass",
            })
    return rows


# --------------------------------------------------------------------------- #
# App shell
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Foci-Med QA Telemetry", layout="wide")
    st.title("Foci-Med — QA Telemetry Dashboard")

    with st.sidebar:
        st.subheader("Telemetry source")
        path = st.text_input("foci_omni_telemetry.json path", DEFAULT_TELEMETRY)
        if st.button("Reload", use_container_width=True):
            st.cache_data.clear()
        st.divider()
        page = st.radio(
            "Navigate",
            ["Overview", "Compliance & Security", "Performance (Load/Stress)",
             "White-Box Coverage", "Functional Breakdown"],
        )

    telemetry = load_telemetry(path)
    if telemetry is None:
        st.error(
            f"Could not load telemetry from `{path}`. "
            "Run `foci_orchestrator.py` first, or correct the path in the sidebar."
        )
        return

    if page == "Overview":
        page_overview(telemetry)
    elif page == "Compliance & Security":
        page_compliance(telemetry)
    elif page == "Performance (Load/Stress)":
        page_performance(telemetry)
    elif page == "White-Box Coverage":
        page_coverage(telemetry)
    elif page == "Functional Breakdown":
        page_functional(telemetry)


if __name__ == "__main__":
    main()

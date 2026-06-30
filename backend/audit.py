"""Formal Audit Report Compiler.

Takes a list of TestResult objects and produces a structured, professional
audit report suitable for delivery to stakeholders.  The report calculates
an overall risk score, per-category scores, a risk matrix, prioritised
recommendations, and an executive summary.
"""

from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import List

from executor import TestResult, Finding


# ── Report structure ───────────────────────────────────────────────────────── #
@dataclass
class CategoryScore:
    name: str
    score: int          # 0–100
    risk: str           # CRITICAL | HIGH | MEDIUM | LOW | N/A
    passed: int
    failed: int
    warned: int
    skipped: int
    manual: int
    tests: list[dict] = field(default_factory=list)


@dataclass
class AuditReport:
    id: str
    generated_at: str
    target: str
    overall_score: int
    risk_level: str
    categories: list[CategoryScore] = field(default_factory=list)
    critical_findings: list[dict] = field(default_factory=list)
    all_findings: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warned: int = 0
    skipped: int = 0
    manual: int = 0
    total: int = 0
    owasp_coverage: dict = field(default_factory=dict)
    executive_summary: str = ""
    mode: str = "standard"   # standard | cyber | sandbox

    def to_dict(self) -> dict:
        d = asdict(self)
        d["categories"] = [asdict(c) for c in self.categories]
        return d


# ── OWASP Top 10 mapping ───────────────────────────────────────────────────── #
OWASP_MAP = {
    "A01 Broken Access Control":     ["authz_test", "cy_rbac", "cy_idor", "cy_priv_esc", "cy_bac"],
    "A02 Cryptographic Failures":    ["enc_test", "cy_tls", "cy_cert", "cy_enc_strength", "cy_hash"],
    "A03 Injection":                 ["cy_sqli", "cy_nosqli", "cy_cmdi", "cy_ssti", "sast"],
    "A04 Insecure Design":           ["threat", "cy_biz_logic", "cy_risk", "risk_based"],
    "A05 Security Misconfiguration": ["cy_config_review", "cy_iac", "cy_sec_config", "config"],
    "A06 Vulnerable Components":     ["vuln_scan", "sca", "cy_dep_analysis", "cy_patch"],
    "A07 Authentication Failures":   ["auth_test", "cy_login", "cy_brute", "cy_mfa", "cy_jwt"],
    "A08 Data Integrity Failures":   ["cy_secret_det", "secret_scan", "cy_dep_analysis"],
    "A09 Logging & Monitoring":      ["cy_logging", "cy_audit_ready", "compliance"],
    "A10 SSRF":                      ["cy_ssrf", "cy_open_redirect"],
}


# ── Scoring helpers ────────────────────────────────────────────────────────── #
def _risk(score: int) -> str:
    if score >= 85: return "LOW"
    if score >= 65: return "MEDIUM"
    if score >= 40: return "HIGH"
    return "CRITICAL"


SEVERITY_WEIGHT = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0, "ERROR": 0}


def _category_from_id(test_id: str) -> str:
    from catalog import ALL_TESTS_BY_ID, CYBER_CATEGORIES
    t = ALL_TESTS_BY_ID.get(test_id)
    if t:
        return t.group
    for cat in CYBER_CATEGORIES:
        for test in cat["tests"]:
            if test["id"] == test_id:
                return f"Cyber — {cat['name']}"
    return "Specialised"


def _recommendations_from_results(results: List[TestResult]) -> list[str]:
    recs: list[str] = []
    seen: set[str] = set()
    # Priority: critical/fail first
    for r in sorted(results, key=lambda x: (x.status != "FAIL", x.score)):
        for rec in r.recommendations:
            if rec and rec not in seen:
                seen.add(rec)
                recs.append(rec)
    return recs[:30]


def _owasp_coverage(results: List[TestResult]) -> dict:
    run_ids = {r.test_id for r in results}
    coverage = {}
    for owasp, test_ids in OWASP_MAP.items():
        covered = [tid for tid in test_ids if tid in run_ids]
        passed  = [r for r in results if r.test_id in covered and r.status == "PASS"]
        coverage[owasp] = {
            "covered":   len(covered),
            "total_map": len(test_ids),
            "passed":    len(passed),
            "status":    "COVERED" if covered else "NOT TESTED",
        }
    return coverage


def _executive_summary(report: AuditReport) -> str:
    pct = int(report.passed / max(report.total, 1) * 100)
    critical_count = len([f for f in report.all_findings if f.get("severity") == "CRITICAL"])
    high_count     = len([f for f in report.all_findings if f.get("severity") == "HIGH"])
    lines = [
        f"Audit conducted on {report.generated_at[:10]} against target: {report.target}.",
        f"Overall platform health score: {report.overall_score}/100 — Risk Level: {report.risk_level}.",
        f"{report.total} tests executed: {report.passed} PASS, {report.failed} FAIL, "
        f"{report.warned} WARNING, {report.skipped} SKIPPED, {report.manual} MANUAL.",
        f"{critical_count} CRITICAL and {high_count} HIGH severity findings require immediate remediation.",
    ]
    if report.risk_level in ("CRITICAL", "HIGH"):
        lines.append("⚠ RECOMMENDATION: Platform must NOT be promoted to production until critical findings are resolved.")
    elif report.risk_level == "MEDIUM":
        lines.append("Platform may proceed to production with a remediation plan in place for HIGH/MEDIUM findings.")
    else:
        lines.append("Platform demonstrates a strong security and quality posture. Maintain and re-test quarterly.")
    return " ".join(lines)


# ── Main compiler ──────────────────────────────────────────────────────────── #
def compile_audit(
    results: List[TestResult],
    target: str = "uploaded project",
    mode: str = "standard",
) -> AuditReport:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Tally counts
    passed  = sum(1 for r in results if r.status == "PASS")
    failed  = sum(1 for r in results if r.status == "FAIL")
    warned  = sum(1 for r in results if r.status == "WARNING")
    skipped = sum(1 for r in results if r.status in ("SKIPPED", "ERROR"))
    manual  = sum(1 for r in results if r.status == "MANUAL")
    total   = len(results)

    # Scored results only (exclude MANUAL and SKIPPED from score calc)
    scored  = [r for r in results if r.score >= 0 and r.status not in ("MANUAL", "SKIPPED", "ERROR")]
    overall = int(sum(r.score for r in scored) / max(len(scored), 1)) if scored else 50

    # All findings flattened
    all_findings: list[dict] = []
    for r in results:
        for f in r.findings:
            all_findings.append({
                "test_id":     r.test_id,
                "test_name":   r.name,
                "severity":    f.severity,
                "title":       f.title,
                "description": f.description,
                "location":    f.location,
                "evidence":    f.evidence,
            })

    # Sort findings by severity
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4, "ERROR": 5}
    all_findings.sort(key=lambda f: sev_order.get(f.get("severity", "INFO"), 5))
    critical_findings = [f for f in all_findings if f.get("severity") in ("CRITICAL", "HIGH")]

    # Per-category aggregation
    cat_map: dict[str, list[TestResult]] = {}
    for r in results:
        cat = _category_from_id(r.test_id)
        cat_map.setdefault(cat, []).append(r)

    categories: list[CategoryScore] = []
    for cat_name, cat_results in cat_map.items():
        cat_scored = [r for r in cat_results if r.score >= 0 and r.status not in ("MANUAL","SKIPPED","ERROR")]
        cat_score  = int(sum(r.score for r in cat_scored) / max(len(cat_scored), 1)) if cat_scored else 50
        categories.append(CategoryScore(
            name=cat_name,
            score=cat_score,
            risk=_risk(cat_score),
            passed  =sum(1 for r in cat_results if r.status == "PASS"),
            failed  =sum(1 for r in cat_results if r.status == "FAIL"),
            warned  =sum(1 for r in cat_results if r.status == "WARNING"),
            skipped =sum(1 for r in cat_results if r.status in ("SKIPPED","ERROR")),
            manual  =sum(1 for r in cat_results if r.status == "MANUAL"),
            tests=[{
                "id": r.test_id, "name": r.name, "status": r.status,
                "score": r.score, "duration": r.duration,
                "tool": r.tool_used,
                "findings_count": len(r.findings),
                "findings": [asdict(f) for f in r.findings[:5]],
                "recommendations": r.recommendations[:3],
                "manual_checklist": r.manual_checklist,
            } for r in cat_results],
        ))
    categories.sort(key=lambda c: c.score)

    report = AuditReport(
        id=str(uuid.uuid4()),
        generated_at=now,
        target=target,
        overall_score=overall,
        risk_level=_risk(overall),
        categories=categories,
        critical_findings=critical_findings[:50],
        all_findings=all_findings[:200],
        recommendations=_recommendations_from_results(results),
        passed=passed, failed=failed, warned=warned,
        skipped=skipped, manual=manual, total=total,
        owasp_coverage=_owasp_coverage(results),
        mode=mode,
    )
    report.executive_summary = _executive_summary(report)
    return report

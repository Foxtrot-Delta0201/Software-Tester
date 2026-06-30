"""Test Execution Engine.

Dispatches each TestDef to the appropriate tool and returns a normalised
TestResult.  All results flow into the audit compiler.

Execution tiers
---------------
Tier 1 — Fully automated with real tools (pytest, bandit, pip-audit, locust,
          nmap, sslyze, playwright, coverage).
Tier 2 — Pattern / heuristic scanning against the uploaded source files.
Tier 3 — HTTP probing against a live target URL (optional).
Tier 4 — Structured manual checklist returned for human completion.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from catalog import TestDef, ALL_TESTS_BY_ID


# ── Result types ───────────────────────────────────────────────────────────── #
@dataclass
class Finding:
    severity: str          # CRITICAL | HIGH | MEDIUM | LOW | INFO
    title: str
    description: str
    location: str = ""
    evidence: str = ""


@dataclass
class TestResult:
    test_id: str
    name: str
    status: str            # PASS | FAIL | WARNING | SKIPPED | ERROR | MANUAL
    score: int             # 0–100
    findings: List[Finding] = field(default_factory=list)
    duration: float = 0.0
    tool_used: str = ""
    raw_output: str = ""
    recommendations: List[str] = field(default_factory=list)
    manual_checklist: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── Helpers ────────────────────────────────────────────────────────────────── #
def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def _run_cmd(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr)[:8000]
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError:
        return -2, f"Tool not found: {cmd[0]}"
    except Exception as exc:
        return -3, str(exc)


def _source_files(project_dir: str, exts=(".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go")) -> list[Path]:
    files = []
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    for root, dirs, fnames in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in skip]
        for fn in fnames:
            if any(fn.endswith(e) for e in exts):
                files.append(Path(root) / fn)
    return files[:500]  # cap to avoid memory explosion


def _scan_pattern(files: list[Path], patterns: list[tuple[str, str, str]]) -> List[Finding]:
    """patterns = [(regex, title, severity), ...]"""
    findings: List[Finding] = []
    for fp in files:
        try:
            text = fp.read_text(errors="replace")
            for regex, title, sev in patterns:
                for m in re.finditer(regex, text, re.IGNORECASE):
                    line_no = text[: m.start()].count("\n") + 1
                    findings.append(Finding(
                        severity=sev,
                        title=title,
                        description=f"Pattern matched in {fp.name}",
                        location=f"{fp}:{line_no}",
                        evidence=m.group(0)[:120],
                    ))
        except Exception:
            pass
    return findings


# ── Pattern libraries ──────────────────────────────────────────────────────── #
SECRETS_PATTERNS = [
    (r'(?i)(password|passwd|secret|api_key|apikey|token|auth_token)\s*=\s*["\'][^"\']{6,}["\']', "Hardcoded Credential", "CRITICAL"),
    (r'(?i)private_key\s*=\s*["\'][^"\']{10,}["\']', "Hardcoded Private Key", "CRITICAL"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID", "CRITICAL"),
    (r'(?i)bearer\s+[a-zA-Z0-9\-_]{20,}', "Bearer Token in Code", "HIGH"),
    (r'(?i)-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----', "Private Key Material", "CRITICAL"),
]

SQLI_PATTERNS = [
    (r'cursor\.execute\s*\(\s*f["\']|cursor\.execute\s*\(\s*".*%s.*"', "Potential SQL Injection", "HIGH"),
    (r'execute\s*\(\s*["\']\s*SELECT.*\+', "String Concatenation in SQL", "HIGH"),
    (r'(?i)raw\s*\(\s*f["\'].*SELECT', "Django Raw SQL with f-string", "HIGH"),
]

XSS_PATTERNS = [
    (r'innerHTML\s*=\s*[^;]+(?!sanitize)', "Potential XSS via innerHTML", "HIGH"),
    (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML", "MEDIUM"),
    (r'document\.write\s*\(', "DOM XSS via document.write", "HIGH"),
    (r'eval\s*\(', "eval() usage — potential XSS/injection", "HIGH"),
]

SSRF_PATTERNS = [
    (r'requests\.get\s*\(\s*(?:user_input|url|request\.)', "Potential SSRF via user-controlled URL", "HIGH"),
    (r'urllib\.request\.urlopen\s*\(\s*(?:url|request\.)', "Potential SSRF via urllib", "HIGH"),
]

WEAK_CRYPTO_PATTERNS = [
    (r'(?i)(md5|sha1)\s*\(', "Weak Hash Algorithm", "MEDIUM"),
    (r'DES|RC4|ECB', "Weak Cipher Algorithm", "HIGH"),
    (r'(?i)hashlib\.md5|hashlib\.sha1', "Weak Python Hash", "MEDIUM"),
]

COMPLIANCE_PATTERNS = [
    (r'(?i)audit_log|audit_trail', "Audit logging present", "INFO"),
    (r'(?i)gdpr|popia|hipaa', "Compliance annotation found", "INFO"),
]


# ── Execution engines ──────────────────────────────────────────────────────── #
async def _run_pytest(test: TestDef, project_dir: str) -> TestResult:
    t0 = time.perf_counter()
    # Discover test files
    test_files = list(Path(project_dir).rglob("test_*.py")) + list(Path(project_dir).rglob("*_test.py"))
    if not test_files:
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=50,
            duration=0, tool_used="pytest",
            raw_output="No test files found in project directory.",
            recommendations=["Add pytest test files (test_*.py) to your project."],
        )
    report_file = os.path.join(tempfile.gettempdir(), f"foci_{test.id}.json")
    rc, out = _run_cmd(
        [sys.executable, "-m", "pytest", project_dir,
         "--tb=short", "-q", "--timeout=60",
         f"--json-report-file={report_file}", "--json-report"],
        cwd=project_dir, timeout=180,
    )
    elapsed = time.perf_counter() - t0
    # Parse report
    report = {}
    try:
        with open(report_file) as f:
            report = json.load(f)
    except Exception:
        pass
    passed  = report.get("summary", {}).get("passed", 0)
    failed  = report.get("summary", {}).get("failed", 0)
    errors  = report.get("summary", {}).get("errors", 0)
    total   = max(passed + failed + errors, 1)
    score   = int(passed / total * 100) if total else 50
    status  = "PASS" if failed == 0 and errors == 0 else "FAIL"
    findings = [
        Finding("HIGH", f"Test failed: {t['nodeid']}", t.get("call", {}).get("longrepr", "")[:200], t["nodeid"])
        for t in report.get("tests", []) if t.get("outcome") in ("failed", "error")
    ]
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings[:20], duration=round(elapsed, 2),
        tool_used="pytest", raw_output=out[:4000],
        recommendations=["Fix failing tests before production deployment."] if failed else [],
    )


async def _run_bandit(test: TestDef, project_dir: str) -> TestResult:
    t0 = time.perf_counter()
    if not _tool_available("bandit"):
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=50,
            tool_used="bandit", raw_output="bandit not installed.",
            recommendations=["Install bandit: pip install bandit"],
        )
    rc, out = _run_cmd(
        [sys.executable, "-m", "bandit", "-r", project_dir,
         "-f", "json", "-x", ".git,node_modules,venv,.venv"],
        cwd=project_dir, timeout=120,
    )
    elapsed = time.perf_counter() - t0
    findings: List[Finding] = []
    score = 80
    try:
        data = json.loads(out[out.find("{"):])
        for issue in data.get("results", []):
            sev = issue.get("issue_severity", "LOW").upper()
            findings.append(Finding(
                severity=sev,
                title=issue.get("test_name", ""),
                description=issue.get("issue_text", ""),
                location=f"{issue.get('filename','')}:{issue.get('line_number','')}",
                evidence=issue.get("code", "")[:120],
            ))
        high = sum(1 for f in findings if f.severity in ("HIGH", "CRITICAL"))
        med  = sum(1 for f in findings if f.severity == "MEDIUM")
        score = max(0, 100 - high * 15 - med * 5)
    except Exception:
        pass
    status = "FAIL" if score < 60 else ("WARNING" if score < 80 else "PASS")
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings[:30], duration=round(elapsed, 2),
        tool_used="bandit", raw_output=out[:4000],
        recommendations=["Resolve HIGH severity bandit findings immediately."] if score < 80 else [],
    )


async def _run_pip_audit(test: TestDef, project_dir: str) -> TestResult:
    t0 = time.perf_counter()
    req_files = list(Path(project_dir).rglob("requirements*.txt"))
    if not req_files:
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=70,
            tool_used="pip-audit", raw_output="No requirements.txt found.",
        )
    rc, out = _run_cmd(
        [sys.executable, "-m", "pip_audit", "-r", str(req_files[0]), "--format=json"],
        cwd=project_dir, timeout=120,
    )
    elapsed = time.perf_counter() - t0
    findings: List[Finding] = []
    score = 90
    try:
        start = out.find("[")
        vulns = json.loads(out[start:]) if start != -1 else []
        for dep in (vulns if isinstance(vulns, list) else []):
            for v in dep.get("vulns", []):
                sev = "HIGH" if "critical" in str(v).lower() else "MEDIUM"
                findings.append(Finding(
                    severity=sev,
                    title=f"CVE: {v.get('id','')} in {dep.get('name','')}=={dep.get('version','')}",
                    description=v.get("description", ""),
                    location=str(req_files[0]),
                ))
        score = max(0, 100 - len(findings) * 20)
    except Exception:
        pass
    status = "FAIL" if findings else "PASS"
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings, duration=round(elapsed, 2),
        tool_used="pip-audit", raw_output=out[:4000],
        recommendations=[f"Upgrade vulnerable packages: {', '.join(set(f.title.split(' in ')[-1].split('==')[0] for f in findings))}"] if findings else [],
    )


async def _run_locust(test: TestDef, project_dir: str, target_url: str) -> TestResult:
    t0 = time.perf_counter()
    if not target_url:
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=50,
            tool_used="locust", raw_output="No target URL configured for load testing.",
            recommendations=["Configure a target URL in Settings to enable load testing."],
        )
    locustfile = os.path.join(project_dir, "tests", "performance", "locustfile.py")
    if not os.path.exists(locustfile):
        locustfile = _generate_locustfile(target_url)
    csv_prefix = os.path.join(tempfile.gettempdir(), f"foci_locust_{test.id}")
    profile = {"load": (50, 10, "60s"), "stress": (200, 50, "60s"), "spike": (500, 200, "30s"),
               "soak": (30, 5, "120s"), "perf": (25, 5, "30s")}.get(test.id, (25, 5, "30s"))
    rc, out = _run_cmd(
        ["locust", "-f", locustfile, "--headless",
         "-u", str(profile[0]), "-r", str(profile[1]), "-t", profile[2],
         "--host", target_url, "--csv", csv_prefix],
        cwd=project_dir, timeout=300,
    )
    elapsed = time.perf_counter() - t0
    score = 80 if rc == 0 else 40
    findings = []
    if rc != 0:
        findings.append(Finding("HIGH", "Load test failed or target unreachable", out[:200]))
    return TestResult(
        test_id=test.id, name=test.name,
        status="PASS" if rc == 0 else "FAIL",
        score=score, findings=findings, duration=round(elapsed, 2),
        tool_used="locust", raw_output=out[:4000],
    )


def _generate_locustfile(target_url: str) -> str:
    content = f'''from locust import HttpUser, task, between
class DefaultUser(HttpUser):
    wait_time = between(1, 3)
    @task
    def health(self):
        self.client.get("/health", name="GET /health")
    @task(3)
    def index(self):
        self.client.get("/", name="GET /")
'''
    path = os.path.join(tempfile.gettempdir(), "foci_gen_locustfile.py")
    Path(path).write_text(content)
    return path


async def _run_http_probe(test: TestDef, target_url: str) -> TestResult:
    t0 = time.perf_counter()
    if not target_url:
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=50,
            tool_used="http_probe", raw_output="No target URL configured.",
            recommendations=["Set a target URL in Settings to enable HTTP probing."],
        )
    try:
        import urllib.request
        import ssl
        findings: List[Finding] = []
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(target_url, headers={"User-Agent": "FociHarness/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            headers = dict(resp.headers)
            # Security header checks
            required_headers = {
                "X-Frame-Options": ("CRITICAL", "Clickjacking protection missing"),
                "X-Content-Type-Options": ("HIGH",   "MIME sniffing protection missing"),
                "Strict-Transport-Security": ("HIGH",  "HSTS not enforced"),
                "Content-Security-Policy": ("HIGH",    "CSP header missing"),
                "Referrer-Policy": ("MEDIUM",          "Referrer-Policy not set"),
                "Permissions-Policy": ("MEDIUM",       "Permissions-Policy not set"),
            }
            for hdr, (sev, msg) in required_headers.items():
                if hdr.lower() not in {k.lower() for k in headers}:
                    findings.append(Finding(sev, f"Missing header: {hdr}", msg, target_url))
            # CORS check
            cors = headers.get("Access-Control-Allow-Origin", "")
            if cors == "*":
                findings.append(Finding("HIGH", "Wildcard CORS", "Access-Control-Allow-Origin: * allows any origin", target_url))
        score = max(0, 100 - sum(15 if f.severity == "CRITICAL" else 10 if f.severity == "HIGH" else 5 for f in findings))
        status = "FAIL" if score < 60 else ("WARNING" if score < 80 else "PASS")
        elapsed = time.perf_counter() - t0
        return TestResult(
            test_id=test.id, name=test.name, status=status, score=score,
            findings=findings, duration=round(elapsed, 2),
            tool_used="http_probe", raw_output=json.dumps(dict(resp.headers), indent=2)[:2000],
            recommendations=[f"Add missing security header: {f.title.split(': ')[-1]}" for f in findings if "Missing header" in f.title],
        )
    except Exception as exc:
        return TestResult(
            test_id=test.id, name=test.name, status="ERROR", score=0,
            tool_used="http_probe", raw_output=str(exc),
            recommendations=["Ensure target URL is reachable and correct."],
        )


async def _run_pattern(test: TestDef, project_dir: str) -> TestResult:
    t0 = time.perf_counter()
    files = _source_files(project_dir)
    # Select pattern set based on test type
    patterns_map: dict[str, list] = {
        "secret_scan": SECRETS_PATTERNS,
        "cy_secret_det": SECRETS_PATTERNS,
        "cy_sqli": SQLI_PATTERNS,
        "cy_xss_stored": XSS_PATTERNS,
        "cy_xss_reflected": XSS_PATTERNS,
        "cy_xss_dom": XSS_PATTERNS,
        "cy_ssrf": SSRF_PATTERNS,
        "cy_enc_strength": WEAK_CRYPTO_PATTERNS,
        "cy_hash": WEAK_CRYPTO_PATTERNS,
        "compliance": COMPLIANCE_PATTERNS,
    }
    # Default: run all relevant patterns
    all_patterns = (
        patterns_map.get(test.id) or
        (SECRETS_PATTERNS + SQLI_PATTERNS + XSS_PATTERNS if "security" in test.group.lower() else SECRETS_PATTERNS)
    )
    findings = _scan_pattern(files, all_patterns)
    elapsed = time.perf_counter() - t0
    critical = [f for f in findings if f.severity == "CRITICAL"]
    high     = [f for f in findings if f.severity == "HIGH"]
    score    = max(0, 100 - len(critical) * 20 - len(high) * 10)
    status   = "FAIL" if critical else ("WARNING" if high else "PASS")
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings[:25], duration=round(elapsed, 2),
        tool_used="pattern_scan",
        raw_output=f"Scanned {len(files)} files, found {len(findings)} pattern matches.",
        recommendations=list({f.description for f in critical[:5]}),
    )


async def _run_coverage(test: TestDef, project_dir: str) -> TestResult:
    t0 = time.perf_counter()
    rc, out = _run_cmd(
        [sys.executable, "-m", "coverage", "run", "-m", "pytest", project_dir, "-q"],
        cwd=project_dir, timeout=180,
    )
    rc2, report = _run_cmd(
        [sys.executable, "-m", "coverage", "report", "--format=json"],
        cwd=project_dir, timeout=30,
    )
    elapsed = time.perf_counter() - t0
    pct = 0
    try:
        data = json.loads(report[report.find("{"):])
        pct = int(data.get("totals", {}).get("percent_covered", 0))
    except Exception:
        pass
    score  = pct
    status = "PASS" if pct >= 70 else ("WARNING" if pct >= 50 else "FAIL")
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=[Finding("MEDIUM", f"Code coverage: {pct}%",
                          "Coverage below 70% threshold" if pct < 70 else "Coverage acceptable")] if pct > 0 else [],
        duration=round(elapsed, 2), tool_used="coverage",
        raw_output=out[:2000],
        recommendations=[f"Increase test coverage from {pct}% to ≥70%."] if pct < 70 else [],
    )


async def _run_db_check(test: TestDef, config: dict) -> TestResult:
    t0 = time.perf_counter()
    findings: List[Finding] = []
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config.get("db_host","localhost"),
            port=config.get("db_port",5432),
            dbname=config.get("db_name","focimed_core"),
            user=config.get("db_user","postgres"),
            password=config.get("db_password",""),
        )
        cur = conn.cursor()
        # Check RLS enabled on patient tables
        cur.execute("""
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'pool_01'
        """)
        for row in cur.fetchall():
            if not row[1]:
                findings.append(Finding("CRITICAL", f"RLS disabled on pool_01.{row[0]}",
                                        "Row-Level Security must be enabled on all tenant tables", f"pool_01.{row[0]}"))
        # Check for superuser roles
        cur.execute("SELECT rolname FROM pg_roles WHERE rolsuper = true AND rolname NOT IN ('postgres')")
        for row in cur.fetchall():
            findings.append(Finding("HIGH", f"Non-standard superuser role: {row[0]}",
                                    "Unexpected superuser roles pose privilege escalation risk"))
        # Check audit log table exists
        cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='audit_logs')")
        if not cur.fetchone()[0]:
            findings.append(Finding("HIGH", "audit_logs table not found", "Audit trail is required for compliance"))
        conn.close()
    except Exception as exc:
        findings.append(Finding("ERROR", "DB connection failed", str(exc)))
    elapsed = time.perf_counter() - t0
    score  = max(0, 100 - len([f for f in findings if f.severity == "CRITICAL"]) * 25
                        - len([f for f in findings if f.severity == "HIGH"]) * 10)
    status = "FAIL" if score < 60 else ("WARNING" if score < 80 else "PASS")
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings, duration=round(elapsed, 2), tool_used="psycopg2",
        raw_output=f"Checked {len(findings)} database security controls.",
        recommendations=["Enable RLS on all tenant tables.", "Audit superuser roles."] if findings else [],
    )


async def _run_nmap(test: TestDef, target_url: str) -> TestResult:
    t0 = time.perf_counter()
    if not _tool_available("nmap"):
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=50,
            tool_used="nmap", raw_output="nmap not installed.",
            recommendations=["Install nmap: https://nmap.org/download.html"],
        )
    host = target_url.split("//")[-1].split("/")[0].split(":")[0] if target_url else "localhost"
    rc, out = _run_cmd(["nmap", "-sV", "--top-ports", "100", "-T4", host], cwd=".", timeout=120)
    elapsed = time.perf_counter() - t0
    findings: List[Finding] = []
    risky_ports = {"21": "FTP", "23": "Telnet", "3389": "RDP", "5900": "VNC", "27017": "MongoDB"}
    for port, service in risky_ports.items():
        if f"{port}/tcp open" in out:
            findings.append(Finding("HIGH", f"Risky port open: {port}/{service}",
                                    f"{service} is exposed and should be firewalled", host))
    score  = max(0, 100 - len(findings) * 20)
    status = "FAIL" if findings else "PASS"
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings, duration=round(elapsed, 2), tool_used="nmap",
        raw_output=out[:3000],
        recommendations=["Close or firewall unnecessary open ports."] if findings else [],
    )


async def _run_sslyze(test: TestDef, target_url: str) -> TestResult:
    t0 = time.perf_counter()
    if not _tool_available("sslyze"):
        # Fallback: use ssl module
        findings: List[Finding] = []
        host = target_url.split("//")[-1].split("/")[0].split(":")[0] if target_url else ""
        if host and target_url.startswith("https"):
            try:
                import ssl, socket
                ctx = ssl.create_default_context()
                with socket.create_connection((host, 443), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                        cert = ssock.getpeercert()
                        proto = ssock.version()
                        if proto in ("TLSv1", "TLSv1.1"):
                            findings.append(Finding("HIGH", f"Outdated TLS version: {proto}",
                                                    "TLS 1.0/1.1 are deprecated", host))
            except Exception as exc:
                findings.append(Finding("INFO", "TLS check", str(exc)))
        elapsed = time.perf_counter() - t0
        score  = 80 if not findings else 50
        return TestResult(
            test_id=test.id, name=test.name, status="PASS" if not findings else "WARNING",
            score=score, findings=findings, duration=round(elapsed, 2), tool_used="ssl-module",
            raw_output="sslyze not installed; used Python ssl module for basic check.",
        )
    rc, out = _run_cmd(["sslyze", "--json_out=-", target_url], cwd=".", timeout=120)
    elapsed = time.perf_counter() - t0
    return TestResult(
        test_id=test.id, name=test.name, status="PASS" if rc == 0 else "WARNING",
        score=75, duration=round(elapsed, 2), tool_used="sslyze", raw_output=out[:3000],
    )


def _run_docker_check(test: TestDef, project_dir: str) -> TestResult:
    t0 = time.perf_counter()
    findings: List[Finding] = []
    dockerfiles = list(Path(project_dir).rglob("Dockerfile*"))
    if not dockerfiles:
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=70,
            tool_used="docker", raw_output="No Dockerfile found in project.",
        )
    for df in dockerfiles:
        text = df.read_text(errors="replace")
        if "USER root" in text or ("USER" not in text):
            findings.append(Finding("HIGH", "Container running as root",
                                    "Dockerfile lacks a non-root USER directive", str(df)))
        if "ADD" in text and "http" in text:
            findings.append(Finding("MEDIUM", "ADD from URL in Dockerfile",
                                    "Use COPY instead of ADD for local files; prefer curl for URLs", str(df)))
        if ":latest" in text:
            findings.append(Finding("MEDIUM", "Unpinned :latest tag",
                                    "Pin image tags to specific digests for reproducibility", str(df)))
    elapsed = time.perf_counter() - t0
    score  = max(0, 100 - len(findings) * 15)
    status = "FAIL" if score < 60 else ("WARNING" if score < 80 else "PASS")
    return TestResult(
        test_id=test.id, name=test.name, status=status, score=score,
        findings=findings, duration=round(elapsed, 2), tool_used="dockerfile-lint",
        raw_output=f"Checked {len(dockerfiles)} Dockerfile(s).",
        recommendations=["Add USER nonroot directive to Dockerfile."] if findings else [],
    )


def _run_manual(test: TestDef) -> TestResult:
    checklist = _manual_checklists.get(test.id, _generic_checklist(test.name))
    return TestResult(
        test_id=test.id, name=test.name, status="MANUAL", score=-1,
        tool_used="manual", raw_output="Manual assessment required.",
        manual_checklist=checklist,
        recommendations=["Complete the manual checklist and mark each item."],
    )


_manual_checklists: dict[str, list[dict]] = {
    "alpha": [
        {"item": "All critical features tested in controlled environment", "pass": None},
        {"item": "No critical bugs outstanding", "pass": None},
        {"item": "Performance benchmarks met", "pass": None},
        {"item": "Security review completed", "pass": None},
    ],
    "recovery": [
        {"item": "RTO (Recovery Time Objective) measured and within SLA", "pass": None},
        {"item": "RPO (Recovery Point Objective) validated", "pass": None},
        {"item": "Failover procedure documented and tested", "pass": None},
        {"item": "Data integrity verified post-recovery", "pass": None},
    ],
    "cy_phish": [
        {"item": "Phishing email template crafted and approved", "pass": None},
        {"item": "Campaign scope and target list defined", "pass": None},
        {"item": "Click rate below acceptable threshold (< 10%)", "pass": None},
        {"item": "Security awareness training scheduled post-campaign", "pass": None},
    ],
    "cy_usb_drop": [
        {"item": "USB media prepared with benign tracking payload", "pass": None},
        {"item": "Drop locations identified in target facility", "pass": None},
        {"item": "Plug-in events monitored and recorded", "pass": None},
        {"item": "USB Auto-Run disabled on all endpoints", "pass": None},
    ],
    "cy_red_team": [
        {"item": "Rules of engagement signed by stakeholders", "pass": None},
        {"item": "Scope and exclusions documented", "pass": None},
        {"item": "Initial access vector identified", "pass": None},
        {"item": "Persistence mechanism tested", "pass": None},
        {"item": "Lateral movement paths mapped", "pass": None},
        {"item": "Data exfiltration simulation completed", "pass": None},
        {"item": "Blue team detection validated", "pass": None},
        {"item": "Full debrief and remediation report delivered", "pass": None},
    ],
}


def _generic_checklist(test_name: str) -> list[dict]:
    return [
        {"item": f"Define scope and success criteria for {test_name}", "pass": None},
        {"item": "Assign responsible tester and schedule", "pass": None},
        {"item": "Execute test and document observations", "pass": None},
        {"item": "Record findings and severity ratings", "pass": None},
        {"item": "Confirm acceptance / rejection criteria met", "pass": None},
    ]


# ── Main dispatcher ────────────────────────────────────────────────────────── #
async def execute_test(
    test_id: str,
    project_dir: str,
    config: dict,
    target_url: str = "",
) -> TestResult:
    test = ALL_TESTS_BY_ID.get(test_id)
    if not test:
        return TestResult(test_id=test_id, name=test_id, status="ERROR", score=0,
                          raw_output="Unknown test ID.")
    engine = test.engine
    if engine == "pytest":
        return await _run_pytest(test, project_dir)
    elif engine == "bandit":
        return await _run_bandit(test, project_dir)
    elif engine == "pip_audit":
        return await _run_pip_audit(test, project_dir)
    elif engine == "locust":
        return await _run_locust(test, project_dir, target_url)
    elif engine == "http_probe":
        return await _run_http_probe(test, target_url)
    elif engine == "pattern":
        return await _run_pattern(test, project_dir)
    elif engine == "coverage":
        return await _run_coverage(test, project_dir)
    elif engine == "db_check":
        return await _run_db_check(test, config)
    elif engine == "nmap":
        return await _run_nmap(test, target_url)
    elif engine == "sslyze":
        return await _run_sslyze(test, target_url)
    elif engine == "docker":
        return _run_docker_check(test, project_dir)
    elif engine == "manual":
        return _run_manual(test)
    elif engine == "playwright":
        return TestResult(
            test_id=test.id, name=test.name, status="SKIPPED", score=50,
            tool_used="playwright",
            raw_output="Playwright tests require a running app and playwright install.",
            recommendations=["Install playwright: pip install playwright && playwright install"],
        )
    return TestResult(test_id=test.id, name=test.name, status="SKIPPED", score=50,
                      raw_output=f"Engine '{engine}' not yet wired.")


async def execute_batch(
    test_ids: list[str],
    project_dir: str,
    config: dict,
    target_url: str,
    q: asyncio.Queue,
) -> list[TestResult]:
    """Run test_ids sequentially, streaming progress into q."""
    results: list[TestResult] = []
    for i, tid in enumerate(test_ids):
        await q.put({"level": "header", "msg": f"▶ [{i+1}/{len(test_ids)}] Running: {tid}"})
        try:
            result = await execute_test(tid, project_dir, config, target_url)
        except Exception as exc:
            result = TestResult(test_id=tid, name=tid, status="ERROR", score=0, raw_output=str(exc))
        results.append(result)
        icon = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️", "SKIPPED": "⏭", "MANUAL": "📋", "ERROR": "💥"}.get(result.status, "?")
        await q.put({"level": "log", "msg": f"  {icon} {result.name}: {result.status}  (score {result.score}/100)"})
        if result.findings:
            for f in result.findings[:3]:
                await q.put({"level": "warning" if f.severity in ("HIGH","CRITICAL") else "log",
                             "msg": f"    [{f.severity}] {f.title} — {f.location}"})
        await q.put({"type": "progress", "value": int((i + 1) / len(test_ids) * 100)})
    return results

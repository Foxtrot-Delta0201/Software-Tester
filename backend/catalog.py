"""Full test catalog — every test type mapped to an execution engine.

Engines
-------
pytest       Run pytest suites found in the project directory.
bandit       Static security analysis (Python).
semgrep      Multi-language SAST (if installed).
pip_audit    Python dependency CVE scan.
locust       HTTP load / performance testing.
http_probe   Live HTTP endpoint checks (headers, CORS, auth).
pattern      Regex pattern scan across source files.
coverage     Code coverage measurement.
playwright   Browser / E2E / accessibility via Playwright.
docker       Container / image security checks.
db_check     PostgreSQL security & integrity checks.
nmap         Network port / service scan (if nmap installed).
sslyze       TLS/SSL certificate & config analysis.
manual       Structured checklist — user marks pass/fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class TestDef:
    id: str
    name: str
    group: str        # top-level group
    category: str     # sub-category
    description: str
    engine: str
    automated: bool
    severity: str     # critical | high | medium | low  (audit weighting)
    deps: List[str] = field(default_factory=list)   # tools that must be installed
    tags: List[str] = field(default_factory=list)


# ── Functional Testing ─────────────────────────────────────────────────────── #
FUNCTIONAL: List[TestDef] = [
    TestDef("unit",          "Unit Testing",              "Functional", "Core",        "Test individual units of code in isolation",                    "pytest",    True,  "critical", ["pytest"]),
    TestDef("component",     "Component Testing",         "Functional", "Core",        "Test discrete components/modules independently",                "pytest",    True,  "high",     ["pytest"]),
    TestDef("integration",   "Integration Testing",       "Functional", "Core",        "Verify interactions between integrated units",                  "pytest",    True,  "critical", ["pytest"]),
    TestDef("interface",     "Interface Testing",         "Functional", "Core",        "Validate API contracts and data interfaces",                    "http_probe",True,  "high"),
    TestDef("system",        "System Testing",            "Functional", "Core",        "End-to-end system validation against requirements",             "pytest",    True,  "critical", ["pytest"]),
    TestDef("e2e",           "End-to-End (E2E) Testing",  "Functional", "Core",        "Full user journey through the running application",             "playwright",True,  "high",     ["playwright"]),
    TestDef("smoke",         "Smoke Testing",             "Functional", "Confidence",  "Quick sanity check that critical paths are alive",              "pytest",    True,  "critical", ["pytest"]),
    TestDef("sanity",        "Sanity Testing",            "Functional", "Confidence",  "Narrow regression after a targeted fix",                        "pytest",    True,  "high",     ["pytest"]),
    TestDef("regression",    "Regression Testing",        "Functional", "Confidence",  "Full suite re-run to catch unintended regressions",             "pytest",    True,  "critical", ["pytest"]),
    TestDef("retesting",     "Retesting / Confirmation",  "Functional", "Confidence",  "Re-verify previously failing tests after a fix",                "pytest",    True,  "high",     ["pytest"]),
    TestDef("uat",           "Acceptance Testing (UAT)",  "Functional", "Acceptance",  "Validate against business requirements / user criteria",         "pytest",    True,  "critical", ["pytest"]),
    TestDef("alpha",         "Alpha Testing",             "Functional", "Acceptance",  "Internal pre-release validation in a controlled environment",    "manual",    False, "high"),
    TestDef("beta",          "Beta Testing",              "Functional", "Acceptance",  "External pre-release validation with real users",                "manual",    False, "medium"),
    TestDef("exploratory",   "Exploratory Testing",       "Functional", "Discovery",   "Unscripted discovery of defects through ad-hoc exploration",     "manual",    False, "high"),
    TestDef("ad_hoc",        "Ad Hoc Testing",            "Functional", "Discovery",   "Informal testing without test cases, relies on intuition",       "manual",    False, "medium"),
    TestDef("api",           "API Testing",               "Functional", "Interface",   "Validate API endpoints for correctness and contract compliance", "http_probe",True,  "critical"),
    TestDef("ui",            "UI Testing",                "Functional", "Interface",   "Verify the UI renders correctly and responds to interactions",   "playwright",True,  "high",     ["playwright"]),
    TestDef("gui",           "GUI Testing",               "Functional", "Interface",   "Graphical element validation, layout and visual regression",     "playwright",True,  "high",     ["playwright"]),
    TestDef("blackbox",      "Black Box Testing",         "Functional", "Technique",   "Test without internal knowledge — purely behaviour-driven",      "pytest",    True,  "high",     ["pytest"]),
    TestDef("whitebox",      "White Box Testing",         "Functional", "Technique",   "Test with full internal knowledge — structural coverage",        "coverage",  True,  "high",     ["coverage"]),
    TestDef("greybox",       "Grey Box Testing",          "Functional", "Technique",   "Partial knowledge testing — hybrid of black and white box",      "bandit",    True,  "medium",   ["bandit"]),
]

# ── Non-Functional Testing ─────────────────────────────────────────────────── #
NON_FUNCTIONAL: List[TestDef] = [
    TestDef("perf",          "Performance Testing",       "Non-Functional", "Performance", "Baseline performance profiling under normal load",          "locust",    True,  "high",     ["locust"]),
    TestDef("load",          "Load Testing",              "Non-Functional", "Performance", "Behaviour under expected peak user load",                    "locust",    True,  "high",     ["locust"]),
    TestDef("stress",        "Stress Testing",            "Non-Functional", "Performance", "Push beyond limits to find breaking point",                  "locust",    True,  "high",     ["locust"]),
    TestDef("spike",         "Spike Testing",             "Non-Functional", "Performance", "Sudden sharp traffic spike and recovery",                    "locust",    True,  "high",     ["locust"]),
    TestDef("soak",          "Endurance / Soak Testing",  "Non-Functional", "Performance", "Sustained load over hours to surface memory leaks",          "locust",    True,  "medium",   ["locust"]),
    TestDef("volume",        "Volume Testing",            "Non-Functional", "Performance", "Large data volumes — DB growth, file sizes",                 "db_check",  True,  "medium"),
    TestDef("scalability",   "Scalability Testing",       "Non-Functional", "Performance", "Verify system scales linearly with resources",               "locust",    True,  "medium",   ["locust"]),
    TestDef("capacity",      "Capacity Testing",          "Non-Functional", "Performance", "Determine max capacity before SLA breach",                   "locust",    True,  "medium",   ["locust"]),
    TestDef("reliability",   "Reliability Testing",       "Non-Functional", "Resilience",  "Consistent correct behaviour over repeated runs",            "pytest",    True,  "high",     ["pytest"]),
    TestDef("stability",     "Stability Testing",         "Non-Functional", "Resilience",  "No degradation under prolonged operation",                   "locust",    True,  "medium",   ["locust"]),
    TestDef("availability",  "Availability Testing",      "Non-Functional", "Resilience",  "Uptime measurement and SLA validation",                      "http_probe",True,  "high"),
    TestDef("resilience",    "Resilience Testing",        "Non-Functional", "Resilience",  "Recovery from partial component failures",                   "pytest",    True,  "high",     ["pytest"]),
    TestDef("recovery",      "Recovery Testing",          "Non-Functional", "Resilience",  "RTO and RPO validation after failure injection",             "manual",    False, "high"),
    TestDef("failover",      "Failover Testing",          "Non-Functional", "Resilience",  "Automatic failover to standby under primary failure",        "manual",    False, "high"),
    TestDef("backup",        "Backup & Restore Testing",  "Non-Functional", "Resilience",  "Verify backup integrity and restoration procedure",          "manual",    False, "critical"),
    TestDef("dr",            "Disaster Recovery Testing", "Non-Functional", "Resilience",  "Full DR plan execution and RTO/RPO compliance",              "manual",    False, "critical"),
]

# ── Security Testing ───────────────────────────────────────────────────────── #
SECURITY: List[TestDef] = [
    TestDef("pentest",       "Penetration Testing",       "Security", "Adversarial",  "Controlled attack simulation to find exploitable weaknesses",   "bandit",    True,  "critical", ["bandit"]),
    TestDef("vuln_scan",     "Vulnerability Testing",     "Security", "Scanning",     "Automated CVE and weakness scanning of code and deps",          "pip_audit", True,  "critical", ["pip-audit"]),
    TestDef("auth_test",     "Authentication Testing",    "Security", "IAM",          "Login flows, MFA, credential handling validation",              "http_probe",True,  "critical"),
    TestDef("authz_test",    "Authorization Testing",     "Security", "IAM",          "RBAC, privilege escalation, IDOR checks",                       "http_probe",True,  "critical"),
    TestDef("session_test",  "Session Management Testing","Security", "IAM",          "Session fixation, hijacking, timeout, cookie flags",            "http_probe",True,  "critical"),
    TestDef("enc_test",      "Encryption Testing",        "Security", "Crypto",       "TLS configuration, cipher strength, cert validity",             "sslyze",    True,  "critical", ["sslyze"]),
    TestDef("compliance",    "Compliance Testing",        "Security", "Governance",   "POPIA / GDPR / HIPAA checklist against the codebase",           "pattern",   True,  "critical"),
    TestDef("secret_scan",   "Secret Detection",          "Security", "Scanning",     "Hardcoded credentials, API keys, tokens in source",             "pattern",   True,  "critical"),
    TestDef("sast",          "Static Application Security Testing (SAST)", "Security", "Code", "Source code security analysis", "bandit",   True,  "critical", ["bandit"]),
    TestDef("dast",          "Dynamic Application Security Testing (DAST)","Security", "Runtime","Runtime vulnerability probing against live app", "http_probe",True, "critical"),
    TestDef("sca",           "Software Composition Analysis (SCA)",        "Security", "Deps",  "Open-source dependency risk analysis",            "pip_audit", True,  "high",     ["pip-audit"]),
]

# ── Compatibility / Accessibility / Usability ──────────────────────────────── #
COMPAT: List[TestDef] = [
    TestDef("a11y",          "Accessibility Testing",     "Compatibility", "A11Y",     "WCAG 2.1 AA compliance — ARIA, labels, contrast, keyboard",    "playwright",True,  "high",     ["playwright"]),
    TestDef("usability",     "Usability Testing",         "Compatibility", "UX",       "Real-user task completion, cognitive load, error recovery",     "manual",    False, "medium"),
    TestDef("compat",        "Compatibility Testing",     "Compatibility", "Platform", "Verify across supported OS, browser, runtime matrix",           "playwright",True,  "medium",   ["playwright"]),
    TestDef("cross_browser", "Cross-Browser Testing",     "Compatibility", "Browser",  "Chrome, Firefox, Safari, Edge functional parity",               "playwright",True,  "medium",   ["playwright"]),
    TestDef("cross_platform","Cross-Platform Testing",    "Compatibility", "Platform", "Windows, macOS, Linux, mobile OS compatibility",                "manual",    False, "medium"),
    TestDef("responsive",    "Responsive Testing",        "Compatibility", "Browser",  "Mobile/tablet/desktop layout verification",                     "playwright",True,  "medium",   ["playwright"]),
    TestDef("l10n",          "Localization Testing",      "Compatibility", "I18N",     "Date, currency, text expansion, RTL layout validation",         "pattern",   True,  "low"),
    TestDef("i18n",          "Internationalization Testing","Compatibility","I18N",    "Unicode, encoding, locale switching correctness",               "pattern",   True,  "low"),
    TestDef("install",       "Install/Uninstall Testing", "Compatibility", "Lifecycle","Installation, upgrade, uninstall clean-up verification",         "manual",    False, "medium"),
    TestDef("config",        "Configuration Testing",     "Compatibility", "Platform", "Correct behaviour across environment configurations",            "pattern",   True,  "medium"),
]

# ── Test Design Techniques ─────────────────────────────────────────────────── #
DESIGN: List[TestDef] = [
    TestDef("bva",           "Boundary Value Analysis",   "Techniques", "Design",     "Test at and around boundary conditions",                        "pytest",    True,  "high",     ["pytest"]),
    TestDef("ep",            "Equivalence Partitioning",  "Techniques", "Design",     "Group inputs into equivalent classes, test one per class",       "pytest",    True,  "high",     ["pytest"]),
    TestDef("decision",      "Decision Table Testing",    "Techniques", "Design",     "Combinatorial business-rule coverage via decision tables",        "manual",    False, "medium"),
    TestDef("state_trans",   "State Transition Testing",  "Techniques", "Design",     "State machine coverage — legal and illegal transitions",          "pytest",    True,  "critical", ["pytest"]),
    TestDef("use_case",      "Use Case Testing",          "Techniques", "Design",     "Actor / system interaction scenario coverage",                    "manual",    False, "high"),
    TestDef("pairwise",      "Pairwise Testing",          "Techniques", "Design",     "Combinatorial factor coverage with minimal test cases",           "manual",    False, "medium"),
    TestDef("error_guess",   "Error Guessing",            "Techniques", "Heuristic",  "Intuition-based injection of likely fault conditions",            "manual",    False, "medium"),
    TestDef("risk_based",    "Risk-Based Testing",        "Techniques", "Heuristic",  "Prioritise tests by risk exposure and business impact",           "pattern",   True,  "high"),
    TestDef("model_based",   "Model-Based Testing",       "Techniques", "Automation", "Generate test cases from formal models or diagrams",              "manual",    False, "medium"),
]

# ── Code-Oriented / Static Testing ────────────────────────────────────────── #
CODE: List[TestDef] = [
    TestDef("static_analysis","Static Code Analysis",     "Code Quality", "Static",   "Automated lint, style, and bug-detection scan",                 "bandit",    True,  "high",     ["bandit"]),
    TestDef("code_review",    "Code Review",              "Code Quality", "Static",   "Automated rule-based code quality analysis",                     "bandit",    True,  "high",     ["bandit"]),
    TestDef("peer_review",    "Peer Review",              "Code Quality", "Manual",   "Human peer-review checklist for logic and standards",             "manual",    False, "medium"),
    TestDef("walkthrough",    "Walkthrough",              "Code Quality", "Manual",   "Author-led walk through the code for understanding",              "manual",    False, "low"),
    TestDef("tech_review",    "Technical Review",         "Code Quality", "Static",   "Technical correctness and architecture review",                   "bandit",    True,  "medium",   ["bandit"]),
    TestDef("inspection",     "Formal Inspection",        "Code Quality", "Static",   "Structured defect discovery with roles and checklists",           "bandit",    True,  "high",     ["bandit"]),
    TestDef("mutation",       "Mutation Testing",         "Code Quality", "Dynamic",  "Introduce small code mutations — verify tests catch them",        "coverage",  True,  "medium",   ["pytest", "coverage"]),
    TestDef("dynamic",        "Dynamic Testing",          "Code Quality", "Dynamic",  "Runtime behaviour analysis and profiling",                        "pytest",    True,  "high",     ["pytest"]),
]

# ── Specialised Testing ────────────────────────────────────────────────────── #
SPECIALISED: List[TestDef] = [
    TestDef("db",            "Database Testing",          "Specialised", "Data",      "Schema, constraints, RLS, indexes, query performance",          "db_check",  True,  "critical"),
    TestDef("etl",           "ETL Testing",               "Specialised", "Data",      "Extract-Transform-Load pipeline correctness",                    "db_check",  True,  "high"),
    TestDef("data_migration","Data Migration Testing",    "Specialised", "Data",      "Pre/post migration row counts, checksums, integrity",            "db_check",  True,  "critical"),
    TestDef("data_integrity","Data Integrity Testing",    "Specialised", "Data",      "Referential integrity, constraint enforcement, orphan rows",      "db_check",  True,  "critical"),
    TestDef("microservices", "Microservices Testing",     "Specialised", "Arch",      "Individual service contracts, inter-service communication",      "http_probe",True,  "high"),
    TestDef("api_contract",  "API Contract Testing",      "Specialised", "Arch",      "OpenAPI / Pact contract compliance between producer and consumer","http_probe",True,  "high"),
    TestDef("chaos",         "Chaos Testing",             "Specialised", "Resilience","Random failure injection to probe system resilience",             "pytest",    True,  "high",     ["pytest"]),
    TestDef("monkey",        "Monkey Testing",            "Specialised", "Resilience","Random, unscripted inputs to find unexpected crashes",            "pytest",    True,  "medium",   ["pytest"]),
    TestDef("gorilla",       "Gorilla Testing",           "Specialised", "Resilience","Intensive, repeated testing of a single module",                  "pytest",    True,  "medium",   ["pytest"]),
    TestDef("fuzz",          "Fuzz Testing",              "Specialised", "Resilience","Malformed / random input injection to find parsing errors",       "pattern",   True,  "high"),
    TestDef("a_b",           "A/B Testing",               "Specialised", "Product",   "Measure user behaviour difference between two variants",          "manual",    False, "low"),
    TestDef("canary",        "Canary Testing",            "Specialised", "DevOps",    "Gradual rollout validation with a small user cohort",             "manual",    False, "medium"),
    TestDef("cloud",         "Cloud Testing",             "Specialised", "Platform",  "Cloud resource provisioning, IAM, network, storage checks",       "docker",    True,  "high"),
    TestDef("container",     "Container / Docker Testing","Specialised", "Platform",  "Image security, Dockerfile lint, runtime checks",                 "docker",    True,  "high"),
]

# ── DevOps & Release ───────────────────────────────────────────────────────── #
DEVOPS: List[TestDef] = [
    TestDef("continuous",    "Continuous Testing",        "DevOps", "CI/CD",          "Test every commit via the CI pipeline",                          "pytest",    True,  "high",     ["pytest"]),
    TestDef("shift_left",    "Shift-Left Testing",        "DevOps", "CI/CD",          "Run static analysis and unit tests at earliest stage",           "bandit",    True,  "high",     ["bandit"]),
    TestDef("bvt",           "Build Verification Testing","DevOps", "Release",        "Smoke test the build artifact before wider deployment",           "pytest",    True,  "critical", ["pytest"]),
    TestDef("release",       "Release Testing",           "DevOps", "Release",        "Full test pass before a production release",                     "pytest",    True,  "critical", ["pytest"]),
    TestDef("prod_test",     "Production Testing",        "DevOps", "Release",        "Synthetic probes against live production endpoints",              "http_probe",True,  "high"),
    TestDef("synthetic_mon", "Synthetic Monitoring",      "DevOps", "Observability",  "Scheduled synthetic transactions to validate live system",        "http_probe",True,  "high"),
]

# ── AI / ML Testing ────────────────────────────────────────────────────────── #
AI_ML: List[TestDef] = [
    TestDef("model_val",     "Model Validation",          "AI/ML", "Quality",         "Accuracy, precision, recall vs. held-out test set",             "pytest",    True,  "critical", ["pytest"]),
    TestDef("bias",          "Bias Testing",              "AI/ML", "Fairness",        "Demographic parity, equalised odds across protected groups",      "pytest",    True,  "critical", ["pytest"]),
    TestDef("fairness",      "Fairness Testing",          "AI/ML", "Fairness",        "Disparate impact and predictive parity analysis",                 "pytest",    True,  "critical", ["pytest"]),
    TestDef("robustness",    "Robustness Testing",        "AI/ML", "Quality",         "Performance under distribution shift and noisy inputs",           "pytest",    True,  "high",     ["pytest"]),
    TestDef("drift",         "Drift Testing",             "AI/ML", "Quality",         "Data drift and model degradation detection over time",            "pytest",    True,  "high",     ["pytest"]),
    TestDef("explainability","Explainability Testing",    "AI/ML", "Transparency",    "SHAP/LIME feature importance and decision auditability",           "manual",    False, "medium"),
    TestDef("adversarial",   "Adversarial Testing",       "AI/ML", "Security",        "Adversarial example construction and robustness measurement",     "pytest",    True,  "high",     ["pytest"]),
]

# ── Cyber Mode — all 22 categories ────────────────────────────────────────── #
CYBER_CATEGORIES = [
    {
        "id": "vuln_assessment",
        "name": "Vulnerability Assessment",
        "icon": "🔍",
        "color": "orange",
        "tests": [
            {"id": "cy_vuln_scan",       "name": "Vulnerability Scanning",     "engine": "pip_audit",  "desc": "CVE scan of deps and code"},
            {"id": "cy_config_review",   "name": "Configuration Review",       "engine": "pattern",    "desc": "Insecure defaults, debug flags, exposed secrets"},
            {"id": "cy_patch",           "name": "Missing Patch Assessment",   "engine": "pip_audit",  "desc": "Outdated packages with known CVEs"},
            {"id": "cy_cve",             "name": "CVE Analysis",               "engine": "pip_audit",  "desc": "Matched CVE database against installed versions"},
            {"id": "cy_risk",            "name": "Risk Assessment",            "engine": "bandit",     "desc": "Prioritised risk scoring by severity"},
            {"id": "cy_threat",          "name": "Threat Assessment",          "engine": "bandit",     "desc": "Attack surface and threat modelling"},
            {"id": "cy_exposure",        "name": "Exposure Assessment",        "engine": "http_probe", "desc": "Public endpoint and data exposure analysis"},
        ],
    },
    {
        "id": "pentest",
        "name": "Penetration Testing",
        "icon": "🎯",
        "color": "red",
        "tests": [
            {"id": "cy_ext_net",         "name": "External Network Pentest",   "engine": "nmap",       "desc": "External port/service enumeration"},
            {"id": "cy_int_net",         "name": "Internal Network Pentest",   "engine": "nmap",       "desc": "Internal network attack surface"},
            {"id": "cy_webapp_pen",      "name": "Web Application Pentest",    "engine": "http_probe", "desc": "OWASP Top 10 active probing"},
            {"id": "cy_api_pen",         "name": "API Penetration Testing",    "engine": "http_probe", "desc": "REST/GraphQL API attack simulation"},
            {"id": "cy_cloud_pen",       "name": "Cloud Penetration Testing",  "engine": "docker",     "desc": "Cloud config and IAM enumeration"},
            {"id": "cy_container_pen",   "name": "Container Penetration Testing","engine": "docker",   "desc": "Container escape and privilege escalation"},
            {"id": "cy_social_eng",      "name": "Social Engineering Pentest", "engine": "manual",     "desc": "Phishing campaign simulation checklist"},
            {"id": "cy_red_team",        "name": "Red Team Exercise",          "engine": "manual",     "desc": "Full adversary simulation checklist"},
        ],
    },
    {
        "id": "auth_testing",
        "name": "Authentication Testing",
        "icon": "🔐",
        "color": "blue",
        "tests": [
            {"id": "cy_login",           "name": "Login Testing",              "engine": "http_probe", "desc": "Login flow correctness and error handling"},
            {"id": "cy_pwd_policy",      "name": "Password Policy Testing",    "engine": "pattern",    "desc": "Minimum length, complexity, history checks"},
            {"id": "cy_brute",           "name": "Brute Force Resistance",     "engine": "http_probe", "desc": "Account lockout and rate-limit validation"},
            {"id": "cy_mfa",             "name": "MFA Testing",                "engine": "http_probe", "desc": "TOTP/FIDO2 factor enforcement"},
            {"id": "cy_oauth",           "name": "OAuth Testing",              "engine": "http_probe", "desc": "OAuth 2.0 flow, PKCE, token handling"},
            {"id": "cy_jwt",             "name": "JWT Security Testing",       "engine": "pattern",    "desc": "Algorithm confusion, none alg, weak secrets"},
            {"id": "cy_saml",            "name": "SAML Testing",               "engine": "http_probe", "desc": "XML signature, assertion replay checks"},
        ],
    },
    {
        "id": "authz_testing",
        "name": "Authorization Testing",
        "icon": "🛡",
        "color": "purple",
        "tests": [
            {"id": "cy_rbac",            "name": "RBAC Testing",               "engine": "http_probe", "desc": "Role boundary enforcement"},
            {"id": "cy_priv_esc",        "name": "Privilege Escalation",       "engine": "http_probe", "desc": "Horizontal and vertical escalation attempts"},
            {"id": "cy_idor",            "name": "IDOR Testing",               "engine": "http_probe", "desc": "Direct object reference enumeration"},
            {"id": "cy_bac",             "name": "Broken Access Control",      "engine": "http_probe", "desc": "Forced browsing and access control gaps"},
        ],
    },
    {
        "id": "session_testing",
        "name": "Session Management Testing",
        "icon": "🍪",
        "color": "yellow",
        "tests": [
            {"id": "cy_session_fix",     "name": "Session Fixation",           "engine": "http_probe", "desc": "Pre-auth session ID reuse attack"},
            {"id": "cy_session_timeout", "name": "Session Timeout",            "engine": "http_probe", "desc": "Idle and absolute timeout validation"},
            {"id": "cy_cookie_sec",      "name": "Cookie Security",            "engine": "http_probe", "desc": "Secure, HttpOnly, SameSite flags"},
            {"id": "cy_csrf",            "name": "CSRF Token Validation",      "engine": "http_probe", "desc": "Anti-CSRF token presence and validation"},
        ],
    },
    {
        "id": "input_validation",
        "name": "Input Validation Testing",
        "icon": "💉",
        "color": "red",
        "tests": [
            {"id": "cy_sqli",            "name": "SQL Injection",              "engine": "pattern",    "desc": "Raw SQL, unsanitised parameters"},
            {"id": "cy_nosqli",          "name": "NoSQL Injection",            "engine": "pattern",    "desc": "MongoDB operator injection patterns"},
            {"id": "cy_cmdi",            "name": "Command Injection",          "engine": "bandit",     "desc": "OS command execution via user input"},
            {"id": "cy_ssti",            "name": "Template Injection (SSTI)",  "engine": "bandit",     "desc": "Server-side template engine injection"},
            {"id": "cy_xxe",             "name": "XXE Injection",              "engine": "bandit",     "desc": "XML external entity processing"},
            {"id": "cy_crlf",            "name": "CRLF Injection",             "engine": "pattern",    "desc": "HTTP response splitting via CRLF"},
            {"id": "cy_host_hdr",        "name": "Host Header Injection",      "engine": "http_probe", "desc": "Host header manipulation attacks"},
        ],
    },
    {
        "id": "xss_testing",
        "name": "Cross-Site Attack Testing",
        "icon": "⚡",
        "color": "orange",
        "tests": [
            {"id": "cy_xss_stored",      "name": "Stored XSS",                 "engine": "pattern",    "desc": "Persistent XSS in DB-rendered content"},
            {"id": "cy_xss_reflected",   "name": "Reflected XSS",              "engine": "pattern",    "desc": "URL parameter reflected without encoding"},
            {"id": "cy_xss_dom",         "name": "DOM XSS",                    "engine": "pattern",    "desc": "Client-side DOM manipulation sinks"},
            {"id": "cy_csrf_attack",     "name": "CSRF Attack Testing",        "engine": "http_probe", "desc": "State-changing requests without token"},
            {"id": "cy_clickjacking",    "name": "Clickjacking",               "engine": "http_probe", "desc": "X-Frame-Options / CSP frame-ancestors"},
            {"id": "cy_cors",            "name": "CORS Testing",               "engine": "http_probe", "desc": "CORS origin whitelist and credentials"},
        ],
    },
    {
        "id": "api_security",
        "name": "API Security Testing",
        "icon": "🔌",
        "color": "cyan",
        "tests": [
            {"id": "cy_rest_api",        "name": "REST API Security",          "engine": "http_probe", "desc": "REST verb abuse, status codes, schema"},
            {"id": "cy_graphql",         "name": "GraphQL Security",           "engine": "http_probe", "desc": "Introspection, batching, nested queries"},
            {"id": "cy_api_rate",        "name": "Rate Limiting Testing",      "engine": "http_probe", "desc": "API rate-limit bypass and enumeration"},
            {"id": "cy_api_fuzzing",     "name": "API Fuzzing",                "engine": "http_probe", "desc": "Malformed payload injection into endpoints"},
            {"id": "cy_bola",            "name": "BOLA / IDOR (API)",          "engine": "http_probe", "desc": "Broken Object Level Authorization"},
            {"id": "cy_mass_assign",     "name": "Mass Assignment Testing",    "engine": "pattern",    "desc": "Unwhitelisted property binding vulnerabilities"},
        ],
    },
    {
        "id": "webapp_security",
        "name": "Web Application Security",
        "icon": "🌐",
        "color": "blue",
        "tests": [
            {"id": "cy_file_upload",     "name": "File Upload Security",       "engine": "pattern",    "desc": "MIME type bypass, path traversal via upload"},
            {"id": "cy_path_traversal",  "name": "Directory Traversal",        "engine": "bandit",     "desc": "../ path traversal and LFI"},
            {"id": "cy_ssrf",            "name": "SSRF Testing",               "engine": "pattern",    "desc": "Server-side request forgery payloads"},
            {"id": "cy_open_redirect",   "name": "Open Redirect Testing",      "engine": "pattern",    "desc": "Unvalidated redirect destinations"},
            {"id": "cy_cache_poison",    "name": "Cache Poisoning",            "engine": "http_probe", "desc": "Cache-key injection and poisoning"},
            {"id": "cy_smuggling",       "name": "Request Smuggling",          "engine": "http_probe", "desc": "HTTP/1.1 CL.TE and TE.CL smuggling"},
            {"id": "cy_biz_logic",       "name": "Business Logic Testing",     "engine": "manual",     "desc": "Abuse of legitimate workflows"},
        ],
    },
    {
        "id": "secure_code",
        "name": "Secure Code Testing",
        "icon": "💻",
        "color": "green",
        "tests": [
            {"id": "cy_sast2",           "name": "SAST",                       "engine": "bandit",     "desc": "Static Application Security Testing"},
            {"id": "cy_dast2",           "name": "DAST",                       "engine": "http_probe", "desc": "Dynamic Application Security Testing"},
            {"id": "cy_secret_det",      "name": "Secret Detection",           "engine": "pattern",    "desc": "API keys, tokens, passwords in code"},
            {"id": "cy_dep_analysis",    "name": "Dependency Analysis",        "engine": "pip_audit",  "desc": "Third-party library vulnerability mapping"},
            {"id": "cy_sca2",            "name": "Software Composition Analysis","engine":"pip_audit",  "desc": "OSS license and CVE risk by component"},
        ],
    },
    {
        "id": "cloud_security",
        "name": "Cloud Security Testing",
        "icon": "☁️",
        "color": "sky",
        "tests": [
            {"id": "cy_iam",             "name": "IAM Review",                 "engine": "pattern",    "desc": "Over-permissive roles and policies"},
            {"id": "cy_bucket",          "name": "Storage Bucket Security",    "engine": "pattern",    "desc": "Public bucket ACL and encryption"},
            {"id": "cy_container_sec",   "name": "Container Security",         "engine": "docker",     "desc": "Image scanning, root user, capabilities"},
            {"id": "cy_k8s",             "name": "Kubernetes Security",        "engine": "docker",     "desc": "Pod security, network policies, RBAC"},
            {"id": "cy_iac",             "name": "Infrastructure as Code Security","engine":"pattern",  "desc": "Terraform / Ansible / CFN misconfigs"},
            {"id": "cy_secret_mgmt",     "name": "Secret Management",          "engine": "pattern",    "desc": "Secrets in env vars, config files, repos"},
        ],
    },
    {
        "id": "network_security",
        "name": "Network Security Testing",
        "icon": "🌐",
        "color": "indigo",
        "tests": [
            {"id": "cy_port_scan",       "name": "Port Scanning",              "engine": "nmap",       "desc": "Open port and service enumeration"},
            {"id": "cy_banner",          "name": "Banner Grabbing",            "engine": "nmap",       "desc": "Service version and fingerprint collection"},
            {"id": "cy_firewall",        "name": "Firewall Testing",           "engine": "nmap",       "desc": "Firewall rule bypass and egress testing"},
            {"id": "cy_dns_sec",         "name": "DNS Security Testing",       "engine": "http_probe", "desc": "DNSSEC, zone transfer, subdomain enum"},
            {"id": "cy_net_seg",         "name": "Network Segmentation",       "engine": "nmap",       "desc": "VLAN isolation and lateral movement paths"},
        ],
    },
    {
        "id": "crypto_testing",
        "name": "Cryptography Testing",
        "icon": "🔒",
        "color": "violet",
        "tests": [
            {"id": "cy_tls",             "name": "TLS Configuration",          "engine": "sslyze",     "desc": "Protocol version, cipher suites, HSTS"},
            {"id": "cy_cert",            "name": "Certificate Validation",     "engine": "sslyze",     "desc": "Expiry, chain, hostname, revocation"},
            {"id": "cy_enc_strength",    "name": "Encryption Strength",        "engine": "pattern",    "desc": "Weak algorithms: MD5, SHA1, DES, RC4"},
            {"id": "cy_key_mgmt",        "name": "Key Management",             "engine": "pattern",    "desc": "Hardcoded keys, weak entropy sources"},
            {"id": "cy_hash",            "name": "Hash Algorithm Validation",  "engine": "pattern",    "desc": "Password storage: bcrypt vs MD5 etc."},
        ],
    },
    {
        "id": "mobile_security",
        "name": "Mobile Security Testing",
        "icon": "📱",
        "color": "teal",
        "tests": [
            {"id": "cy_android",         "name": "Android Security Testing",   "engine": "pattern",    "desc": "AndroidManifest, Logcat, storage, exports"},
            {"id": "cy_ios",             "name": "iOS Security Testing",       "engine": "pattern",    "desc": "Info.plist, keychain, ATS configuration"},
            {"id": "cy_cert_pin",        "name": "Certificate Pinning",        "engine": "pattern",    "desc": "Pin bypass resistance in mobile apps"},
            {"id": "cy_root_detect",     "name": "Root/Jailbreak Detection",   "engine": "pattern",    "desc": "Runtime tamper detection checks"},
        ],
    },
    {
        "id": "fuzz_testing",
        "name": "Fuzz Testing",
        "icon": "🌀",
        "color": "amber",
        "tests": [
            {"id": "cy_proto_fuzz",      "name": "Protocol Fuzzing",           "engine": "pattern",    "desc": "Malformed protocol messages"},
            {"id": "cy_api_fuzz",        "name": "API Fuzzing",                "engine": "http_probe", "desc": "Random/boundary inputs to API endpoints"},
            {"id": "cy_input_fuzz",      "name": "Input Fuzzing",              "engine": "pattern",    "desc": "Random inputs to all form fields / params"},
            {"id": "cy_file_fuzz",       "name": "File Format Fuzzing",        "engine": "pattern",    "desc": "Malformed file uploads"},
        ],
    },
    {
        "id": "dos_testing",
        "name": "Denial-of-Service Testing",
        "icon": "💥",
        "color": "red",
        "tests": [
            {"id": "cy_dos",             "name": "DoS Testing",                "engine": "locust",     "desc": "Single-source resource exhaustion"},
            {"id": "cy_rate_limit_val",  "name": "Rate Limiting Validation",   "engine": "http_probe", "desc": "API rate-limit enforcement check"},
            {"id": "cy_resource_exhaust","name": "Resource Exhaustion Testing","engine": "locust",     "desc": "CPU, memory, connection pool exhaustion"},
        ],
    },
    {
        "id": "iam_testing",
        "name": "Identity & Access Testing",
        "icon": "🪪",
        "color": "blue",
        "tests": [
            {"id": "cy_ad",              "name": "Active Directory Assessment","engine": "manual",     "desc": "AD attack paths and Kerberos checks"},
            {"id": "cy_sso",             "name": "Single Sign-On Testing",     "engine": "http_probe", "desc": "SSO bypass and federation trust checks"},
            {"id": "cy_ldap_sec",        "name": "LDAP Security",              "engine": "pattern",    "desc": "LDAP injection and anonymous bind"},
        ],
    },
    {
        "id": "infra_security",
        "name": "Infrastructure Security Testing",
        "icon": "🏗",
        "color": "gray",
        "tests": [
            {"id": "cy_os_hard",         "name": "OS Hardening Review",        "engine": "manual",     "desc": "CIS benchmark compliance checklist"},
            {"id": "cy_docker_sec",      "name": "Docker Security",            "engine": "docker",     "desc": "Dockerfile, runtime, capability audit"},
            {"id": "cy_fw_review",       "name": "Firewall Review",            "engine": "manual",     "desc": "Rule-base analysis and egress control"},
        ],
    },
    {
        "id": "human_security",
        "name": "Human Security Testing",
        "icon": "👤",
        "color": "pink",
        "tests": [
            {"id": "cy_phish",           "name": "Phishing Campaign",          "engine": "manual",     "desc": "Simulated spear-phishing assessment"},
            {"id": "cy_vishing",         "name": "Vishing (Voice Phishing)",   "engine": "manual",     "desc": "Phone-based social engineering test"},
            {"id": "cy_usb_drop",        "name": "USB Drop Testing",           "engine": "manual",     "desc": "Physical media attack simulation"},
            {"id": "cy_tailgate",        "name": "Tailgating Testing",         "engine": "manual",     "desc": "Physical access control bypass"},
        ],
    },
    {
        "id": "adversary_sim",
        "name": "Adversary Simulation",
        "icon": "🗡",
        "color": "red",
        "tests": [
            {"id": "cy_red_team2",       "name": "Red Team Exercise",          "engine": "manual",     "desc": "Full-scope adversary emulation"},
            {"id": "cy_purple_team",     "name": "Purple Team Exercise",       "engine": "manual",     "desc": "Collaborative attack/detect cycle"},
            {"id": "cy_bas",             "name": "Breach & Attack Simulation", "engine": "manual",     "desc": "BAS platform-driven attack validation"},
            {"id": "cy_mitre",           "name": "MITRE ATT&CK Mapping",       "engine": "manual",     "desc": "TTP coverage against ATT&CK framework"},
        ],
    },
    {
        "id": "compliance_gov",
        "name": "Compliance & Governance Testing",
        "icon": "📋",
        "color": "green",
        "tests": [
            {"id": "cy_sec_config",      "name": "Security Configuration Review","engine":"pattern",   "desc": "Baseline security config audit"},
            {"id": "cy_audit_ready",     "name": "Audit Readiness Testing",    "engine": "pattern",    "desc": "Evidence collection and log coverage"},
            {"id": "cy_logging",         "name": "Logging & Monitoring Review","engine": "pattern",    "desc": "SIEM coverage and alert completeness"},
            {"id": "cy_ir",              "name": "Incident Response Testing",  "engine": "manual",     "desc": "IR playbook drill and tabletop exercise"},
            {"id": "cy_bcp",             "name": "Business Continuity Testing","engine": "manual",     "desc": "BCP/DR plan completeness and execution"},
        ],
    },
]

import re as _re


def _slug(s: str) -> str:
    return _re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')


# ── Sandbox types ──────────────────────────────────────────────────────────── #
SANDBOX_TYPES = [
    {"id": "functional_sb", "name": "Functional Sandbox",   "icon": "⚙️",  "color": "blue",
     "purpose": "Verify functionality without affecting production",
     "tests": ["Feature validation","User workflow testing","API testing","UI testing","Integration testing"]},
    {"id": "security_sb",   "name": "Security Sandbox",     "icon": "🛡",  "color": "red",
     "purpose": "Observe malicious behaviour safely",
     "tests": ["Malware analysis","Exploit testing","Payload execution","Phishing attachment analysis","Ransomware behaviour analysis","Zero-day investigation"]},
    {"id": "pentest_sb",    "name": "Penetration Testing Sandbox","icon": "🎯","color": "orange",
     "purpose": "Attack a cloned environment without business risk",
     "tests": ["Exploit development","Privilege escalation","Lateral movement","Persistence testing","Credential attacks","Post-exploitation"]},
    {"id": "api_sb",        "name": "API Sandbox",          "icon": "🔌",  "color": "cyan",
     "purpose": "Test against non-production APIs safely",
     "tests": ["Endpoint testing","Authentication testing","OAuth testing","Rate limiting","Webhook validation","SDK testing"]},
    {"id": "cloud_sb",      "name": "Cloud Sandbox",        "icon": "☁️",  "color": "sky",
     "purpose": "Safely test cloud resources and configurations",
     "tests": ["Infrastructure testing","IAM testing","Network security","Storage configuration","Auto-scaling","IaC validation"]},
    {"id": "dev_sb",        "name": "Dev/Test Sandbox",     "icon": "💻",  "color": "green",
     "purpose": "Day-to-day development and testing",
     "tests": ["New feature development","Branch testing","CI pipeline","CD pipeline","Dependency upgrades","Database migrations"]},
    {"id": "database_sb",   "name": "Database Sandbox",     "icon": "🗄",  "color": "purple",
     "purpose": "Work with realistic data without risking production",
     "tests": ["Query testing","Backup restoration","Data migration","ETL testing","Performance tuning","Schema changes"]},
    {"id": "mobile_sb",     "name": "Mobile Sandbox",       "icon": "📱",  "color": "teal",
     "purpose": "Test mobile apps across devices and operating systems",
     "tests": ["Android testing","iOS testing","Device compatibility","Permission testing","Push notifications","Mobile security"]},
    {"id": "browser_sb",    "name": "Browser Sandbox",      "icon": "🌐",  "color": "indigo",
     "purpose": "Validate browser-specific behaviour",
     "tests": ["Cross-browser testing","Extension testing","JavaScript execution","Cookie behaviour","CORS testing","WebAssembly testing"]},
    {"id": "malware_sb",    "name": "Malware Sandbox",      "icon": "☠️",  "color": "red",
     "purpose": "Understand malicious software behaviour safely",
     "tests": ["Static analysis","Dynamic analysis","Behavioural analysis","Network traffic monitoring","Registry monitoring","Memory analysis"]},
    {"id": "ai_sb",         "name": "AI/ML Sandbox",        "icon": "🤖",  "color": "violet",
     "purpose": "Evaluate AI models before deployment",
     "tests": ["Model evaluation","Prompt testing","Hallucination testing","Adversarial prompt testing","Bias testing","Safety testing"]},
    {"id": "perf_sb",       "name": "Performance Sandbox",  "icon": "📊",  "color": "amber",
     "purpose": "Measure system behaviour under varying workloads",
     "tests": ["Load testing","Stress testing","Soak testing","Spike testing","Capacity testing","Scalability testing"]},
    {"id": "network_sb",    "name": "Network Sandbox",      "icon": "🕸",  "color": "gray",
     "purpose": "Validate network configurations safely",
     "tests": ["Firewall testing","Routing validation","VPN testing","DNS testing","IDS/IPS testing","Network segmentation"]},
    {"id": "container_sb",  "name": "Container Sandbox",    "icon": "📦",  "color": "blue",
     "purpose": "Test containerised applications and infrastructure",
     "tests": ["Docker image testing","Kubernetes deployment","Container escape testing","Runtime security","Secret management","Image vulnerability scanning"]},
    {"id": "iot_sb",        "name": "IoT Sandbox",          "icon": "🔧",  "color": "green",
     "purpose": "Safely test connected devices and embedded software",
     "tests": ["Firmware testing","Device communication","MQTT testing","Sensor validation","OTA update testing","Embedded security"]},
]

# ── Convert sandbox test strings → proper objects ──────────────────────────── #
_SB_ENGINE: dict[str, str] = {
    "functional_sb": "pytest",   "security_sb": "bandit",   "pentest_sb": "bandit",
    "api_sb": "http_probe",      "cloud_sb": "docker",      "dev_sb": "pytest",
    "database_sb": "db_check",   "mobile_sb": "pattern",    "browser_sb": "playwright",
    "malware_sb": "pattern",     "ai_sb": "pytest",         "perf_sb": "locust",
    "network_sb": "nmap",        "container_sb": "docker",  "iot_sb": "pattern",
}
_SB_SEVERITY: dict[str, str] = {
    "security_sb": "critical",   "pentest_sb": "critical",  "malware_sb": "high",
    "network_sb": "high",        "perf_sb": "high",
}

for _sb in SANDBOX_TYPES:
    _engine  = _SB_ENGINE.get(_sb["id"], "manual")
    _sev     = _SB_SEVERITY.get(_sb["id"], "medium")
    _sb["tests"] = [
        {
            "id":          f"{_sb['id']}__{_slug(t)}",
            "name":        t,
            "description": f"{t} in {_sb['name']}",
            "severity":    _sev,
            "engine":      _engine,
            "automated":   _engine != "manual",
        }
        for t in _sb["tests"]
    ]


# ── Master catalog ─────────────────────────────────────────────────────────── #
ALL_TESTS: List[TestDef] = (
    FUNCTIONAL + NON_FUNCTIONAL + SECURITY + COMPAT +
    DESIGN + CODE + SPECIALISED + DEVOPS + AI_ML
)

ALL_TESTS_BY_ID: dict[str, TestDef] = {t.id: t for t in ALL_TESTS}

# Register cyber tests in ALL_TESTS_BY_ID so the executor can dispatch them
for _cat in CYBER_CATEGORIES:
    _cat_sev = "critical" if _cat.get("color") in ("red", "orange") else "high"
    for _t in _cat["tests"]:
        _def = TestDef(
            id=_t["id"],
            name=_t["name"],
            group=f"Cyber — {_cat['name']}",
            category=_cat["name"],
            description=_t.get("desc", _t["name"]),
            engine=_t["engine"],
            automated=_t["engine"] != "manual",
            severity=_cat_sev,
        )
        ALL_TESTS_BY_ID[_def.id] = _def

# Register sandbox tests in ALL_TESTS_BY_ID
for _sb in SANDBOX_TYPES:
    for _t in _sb["tests"]:
        _def = TestDef(
            id=_t["id"],
            name=_t["name"],
            group=f"Sandbox — {_sb['name']}",
            category=_sb["name"],
            description=_t["description"],
            engine=_t["engine"],
            automated=_t["automated"],
            severity=_t["severity"],
        )
        ALL_TESTS_BY_ID[_def.id] = _def


def get_catalog_json() -> dict:
    """Return catalog shaped for the three frontend consumers."""
    # groups: flat dict group_name → [test_def, ...]
    groups: dict[str, list[dict]] = {}
    for t in ALL_TESTS:
        entry = groups.setdefault(t.group, [])
        entry.append({
            "id":          t.id,
            "name":        t.name,
            "group":       t.group,
            "category":    t.category,
            "description": t.description,
            "engine":      t.engine,
            "automated":   t.automated,
            "severity":    t.severity,
            "tags":        t.tags,
        })

    # cyber_categories: map desc → description, derive automated/severity
    cyber_categories = []
    for cat in CYBER_CATEGORIES:
        sev = "critical" if cat.get("color") in ("red", "orange") else "high"
        cyber_categories.append({
            "id":    cat["id"],
            "name":  cat["name"],
            "icon":  cat.get("icon", ""),
            "color": cat.get("color", ""),
            "tests": [
                {
                    "id":          t["id"],
                    "name":        t["name"],
                    "engine":      t["engine"],
                    "description": t.get("desc", t["name"]),
                    "automated":   t["engine"] != "manual",
                    "severity":    sev,
                }
                for t in cat["tests"]
            ],
        })

    # sandbox_types: tests already converted to proper objects above
    sandbox_types = [
        {
            "id":          sb["id"],
            "name":        sb["name"],
            "icon":        sb.get("icon", ""),
            "color":       sb.get("color", ""),
            "description": sb.get("purpose", ""),
            "tests": [
                {
                    "id":          t["id"],
                    "name":        t["name"],
                    "description": t["description"],
                    "automated":   t["automated"],
                    "severity":    t["severity"],
                }
                for t in sb["tests"]
            ],
        }
        for sb in SANDBOX_TYPES
    ]

    return {
        "groups":           groups,
        "cyber_categories": cyber_categories,
        "sandbox_types":    sandbox_types,
    }

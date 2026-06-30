/** Full test catalog — embedded in the frontend so test selection works without a backend. */

export interface TestDef {
  id: string
  name: string
  group: string
  category: string
  description: string
  engine: string
  automated: boolean
  severity: string
  tags: string[]
}

export interface CyberTest {
  id: string
  name: string
  description: string
  engine: string
  automated: boolean
  severity: string
}

export interface CyberCategory {
  id: string
  name: string
  tests: CyberTest[]
}

export interface SandboxTest {
  id: string
  name: string
  description: string
  automated: boolean
  severity: string
}

export interface SandboxType {
  id: string
  name: string
  description: string
  tests: SandboxTest[]
}

// ── Functional ─────────────────────────────────────────────────────────────── //
const FUNCTIONAL: TestDef[] = [
  { id:"unit",         name:"Unit Testing",             group:"Functional", category:"Core",       description:"Test individual units of code in isolation",                   engine:"pytest",    automated:true,  severity:"critical", tags:["pytest"] },
  { id:"component",    name:"Component Testing",        group:"Functional", category:"Core",       description:"Test discrete components/modules independently",               engine:"pytest",    automated:true,  severity:"high",     tags:["pytest"] },
  { id:"integration",  name:"Integration Testing",      group:"Functional", category:"Core",       description:"Verify interactions between integrated units",                 engine:"pytest",    automated:true,  severity:"critical", tags:["pytest"] },
  { id:"interface",    name:"Interface Testing",        group:"Functional", category:"Core",       description:"Validate API contracts and data interfaces",                   engine:"http_probe",automated:true,  severity:"high",     tags:[] },
  { id:"system",       name:"System Testing",           group:"Functional", category:"Core",       description:"End-to-end system validation against requirements",            engine:"pytest",    automated:true,  severity:"critical", tags:["pytest"] },
  { id:"e2e",          name:"End-to-End (E2E) Testing", group:"Functional", category:"Core",       description:"Full user journey through the running application",            engine:"playwright",automated:true,  severity:"high",     tags:["playwright"] },
  { id:"smoke",        name:"Smoke Testing",            group:"Functional", category:"Confidence", description:"Quick sanity check that critical paths are alive",             engine:"pytest",    automated:true,  severity:"critical", tags:["pytest"] },
  { id:"sanity",       name:"Sanity Testing",           group:"Functional", category:"Confidence", description:"Narrow regression after a targeted fix",                       engine:"pytest",    automated:true,  severity:"high",     tags:["pytest"] },
  { id:"regression",   name:"Regression Testing",       group:"Functional", category:"Confidence", description:"Full suite re-run to catch unintended regressions",            engine:"pytest",    automated:true,  severity:"critical", tags:["pytest"] },
  { id:"retesting",    name:"Retesting / Confirmation", group:"Functional", category:"Confidence", description:"Re-verify previously failing tests after a fix",               engine:"pytest",    automated:true,  severity:"high",     tags:["pytest"] },
  { id:"uat",          name:"Acceptance Testing (UAT)", group:"Functional", category:"Acceptance", description:"Validate against business requirements and user criteria",      engine:"pytest",    automated:true,  severity:"critical", tags:["pytest"] },
  { id:"alpha",        name:"Alpha Testing",            group:"Functional", category:"Acceptance", description:"Internal pre-release validation in a controlled environment",   engine:"manual",    automated:false, severity:"high",     tags:[] },
  { id:"beta",         name:"Beta Testing",             group:"Functional", category:"Acceptance", description:"External pre-release validation with real users",               engine:"manual",    automated:false, severity:"medium",   tags:[] },
  { id:"exploratory",  name:"Exploratory Testing",      group:"Functional", category:"Discovery",  description:"Unscripted discovery of defects through ad-hoc exploration",    engine:"manual",    automated:false, severity:"high",     tags:[] },
  { id:"ad_hoc",       name:"Ad Hoc Testing",           group:"Functional", category:"Discovery",  description:"Informal testing without test cases, relies on intuition",      engine:"manual",    automated:false, severity:"medium",   tags:[] },
  { id:"api",          name:"API Testing",              group:"Functional", category:"Interface",  description:"Validate API endpoints for correctness and contract compliance", engine:"http_probe",automated:true,  severity:"critical", tags:[] },
  { id:"ui",           name:"UI Testing",               group:"Functional", category:"Interface",  description:"Verify the UI renders correctly and responds to interactions",  engine:"playwright",automated:true,  severity:"high",     tags:["playwright"] },
  { id:"gui",          name:"GUI Testing",              group:"Functional", category:"Interface",  description:"Graphical element validation, layout and visual regression",    engine:"playwright",automated:true,  severity:"high",     tags:["playwright"] },
  { id:"blackbox",     name:"Black Box Testing",        group:"Functional", category:"Technique",  description:"Test without internal knowledge — purely behaviour-driven",      engine:"pytest",    automated:true,  severity:"high",     tags:["pytest"] },
  { id:"whitebox",     name:"White Box Testing",        group:"Functional", category:"Technique",  description:"Test with full internal knowledge — structural coverage",        engine:"coverage",  automated:true,  severity:"high",     tags:["coverage"] },
  { id:"greybox",      name:"Grey Box Testing",         group:"Functional", category:"Technique",  description:"Partial knowledge testing — hybrid of black and white box",      engine:"bandit",    automated:true,  severity:"medium",   tags:["bandit"] },
]

// ── Non-Functional ─────────────────────────────────────────────────────────── //
const NON_FUNCTIONAL: TestDef[] = [
  { id:"perf",         name:"Performance Testing",      group:"Non-Functional", category:"Performance", description:"Baseline performance profiling under normal load",        engine:"locust",    automated:true,  severity:"high",     tags:["locust"] },
  { id:"load",         name:"Load Testing",             group:"Non-Functional", category:"Performance", description:"Behaviour under expected peak user load",                engine:"locust",    automated:true,  severity:"high",     tags:["locust"] },
  { id:"stress",       name:"Stress Testing",           group:"Non-Functional", category:"Performance", description:"Push beyond limits to find breaking point",              engine:"locust",    automated:true,  severity:"high",     tags:["locust"] },
  { id:"spike",        name:"Spike Testing",            group:"Non-Functional", category:"Performance", description:"Sudden sharp traffic spike and recovery",               engine:"locust",    automated:true,  severity:"high",     tags:["locust"] },
  { id:"soak",         name:"Endurance / Soak Testing", group:"Non-Functional", category:"Performance", description:"Sustained load over hours to surface memory leaks",      engine:"locust",    automated:true,  severity:"medium",   tags:["locust"] },
  { id:"volume",       name:"Volume Testing",           group:"Non-Functional", category:"Performance", description:"Large data volumes — DB growth, file sizes",             engine:"db_check",  automated:true,  severity:"medium",   tags:[] },
  { id:"scalability",  name:"Scalability Testing",      group:"Non-Functional", category:"Performance", description:"Verify system scales linearly with resources",           engine:"locust",    automated:true,  severity:"medium",   tags:["locust"] },
  { id:"capacity",     name:"Capacity Testing",         group:"Non-Functional", category:"Performance", description:"Determine max capacity before SLA breach",              engine:"locust",    automated:true,  severity:"medium",   tags:["locust"] },
  { id:"reliability",  name:"Reliability Testing",      group:"Non-Functional", category:"Resilience",  description:"Consistent correct behaviour over repeated runs",        engine:"pytest",    automated:true,  severity:"high",     tags:["pytest"] },
  { id:"stability",    name:"Stability Testing",        group:"Non-Functional", category:"Resilience",  description:"No degradation under prolonged operation",              engine:"locust",    automated:true,  severity:"medium",   tags:["locust"] },
  { id:"availability", name:"Availability Testing",     group:"Non-Functional", category:"Resilience",  description:"Uptime measurement and SLA validation",                 engine:"http_probe",automated:true,  severity:"high",     tags:[] },
  { id:"resilience",   name:"Resilience Testing",       group:"Non-Functional", category:"Resilience",  description:"Recovery from partial component failures",              engine:"pytest",    automated:true,  severity:"high",     tags:["pytest"] },
  { id:"recovery",     name:"Recovery Testing",         group:"Non-Functional", category:"Resilience",  description:"RTO and RPO validation after failure injection",         engine:"manual",    automated:false, severity:"high",     tags:[] },
  { id:"failover",     name:"Failover Testing",         group:"Non-Functional", category:"Resilience",  description:"Automatic failover to standby under primary failure",   engine:"manual",    automated:false, severity:"high",     tags:[] },
  { id:"backup",       name:"Backup & Restore Testing", group:"Non-Functional", category:"Resilience",  description:"Verify backup integrity and restoration procedure",      engine:"manual",    automated:false, severity:"critical", tags:[] },
  { id:"dr",           name:"Disaster Recovery Testing",group:"Non-Functional", category:"Resilience",  description:"Full DR plan execution and RTO/RPO compliance",         engine:"manual",    automated:false, severity:"critical", tags:[] },
]

// ── Security ───────────────────────────────────────────────────────────────── //
const SECURITY: TestDef[] = [
  { id:"pentest",      name:"Penetration Testing",                       group:"Security", category:"Adversarial", description:"Controlled attack simulation to find exploitable weaknesses",     engine:"bandit",    automated:true,  severity:"critical", tags:["bandit"] },
  { id:"vuln_scan",    name:"Vulnerability Testing",                     group:"Security", category:"Scanning",    description:"Automated CVE and weakness scanning of code and deps",           engine:"pip_audit", automated:true,  severity:"critical", tags:["pip-audit"] },
  { id:"auth_test",    name:"Authentication Testing",                    group:"Security", category:"IAM",         description:"Login flows, MFA, credential handling validation",               engine:"http_probe",automated:true,  severity:"critical", tags:[] },
  { id:"authz_test",   name:"Authorization Testing",                     group:"Security", category:"IAM",         description:"RBAC, privilege escalation, IDOR checks",                        engine:"http_probe",automated:true,  severity:"critical", tags:[] },
  { id:"session_test", name:"Session Management Testing",                group:"Security", category:"IAM",         description:"Session fixation, hijacking, timeout, cookie flags",             engine:"http_probe",automated:true,  severity:"critical", tags:[] },
  { id:"enc_test",     name:"Encryption Testing",                        group:"Security", category:"Crypto",      description:"TLS configuration, cipher strength, cert validity",              engine:"sslyze",    automated:true,  severity:"critical", tags:["sslyze"] },
  { id:"compliance",   name:"Compliance Testing",                        group:"Security", category:"Governance",  description:"GDPR / HIPAA / SOC2 checklist against the codebase",             engine:"pattern",   automated:true,  severity:"critical", tags:[] },
  { id:"secret_scan",  name:"Secret Detection",                          group:"Security", category:"Scanning",    description:"Hardcoded credentials, API keys, tokens in source",              engine:"pattern",   automated:true,  severity:"critical", tags:[] },
  { id:"sast",         name:"Static Application Security Testing (SAST)",group:"Security", category:"Code",        description:"Source code security analysis",                                  engine:"bandit",    automated:true,  severity:"critical", tags:["bandit"] },
  { id:"dast",         name:"Dynamic Application Security Testing (DAST)",group:"Security",category:"Runtime",     description:"Runtime vulnerability probing against live app",                  engine:"http_probe",automated:true,  severity:"critical", tags:[] },
  { id:"sca",          name:"Software Composition Analysis (SCA)",       group:"Security", category:"Deps",        description:"Open-source dependency risk analysis",                           engine:"pip_audit", automated:true,  severity:"high",     tags:["pip-audit"] },
]

// ── Compatibility ──────────────────────────────────────────────────────────── //
const COMPAT: TestDef[] = [
  { id:"a11y",         name:"Accessibility Testing",    group:"Compatibility", category:"A11Y",    description:"WCAG 2.1 AA compliance — ARIA, labels, contrast, keyboard",  engine:"playwright",automated:true,  severity:"high",   tags:["playwright"] },
  { id:"usability",    name:"Usability Testing",        group:"Compatibility", category:"UX",      description:"Real-user task completion, cognitive load, error recovery",   engine:"manual",    automated:false, severity:"medium", tags:[] },
  { id:"compat",       name:"Compatibility Testing",    group:"Compatibility", category:"Platform",description:"Verify across supported OS, browser, runtime matrix",         engine:"playwright",automated:true,  severity:"medium", tags:["playwright"] },
  { id:"cross_browser",name:"Cross-Browser Testing",    group:"Compatibility", category:"Browser", description:"Chrome, Firefox, Safari, Edge functional parity",             engine:"playwright",automated:true,  severity:"medium", tags:["playwright"] },
  { id:"cross_platform",name:"Cross-Platform Testing",  group:"Compatibility", category:"Platform",description:"Windows, macOS, Linux, mobile OS compatibility",              engine:"manual",    automated:false, severity:"medium", tags:[] },
  { id:"responsive",   name:"Responsive Testing",       group:"Compatibility", category:"Browser", description:"Mobile/tablet/desktop layout verification",                   engine:"playwright",automated:true,  severity:"medium", tags:["playwright"] },
  { id:"l10n",         name:"Localization Testing",     group:"Compatibility", category:"I18N",    description:"Date, currency, text expansion, RTL layout validation",       engine:"pattern",   automated:true,  severity:"low",    tags:[] },
  { id:"i18n",         name:"Internationalization Testing",group:"Compatibility",category:"I18N",  description:"Unicode, encoding, locale switching correctness",              engine:"pattern",   automated:true,  severity:"low",    tags:[] },
  { id:"install",      name:"Install/Uninstall Testing",group:"Compatibility", category:"Lifecycle",description:"Installation, upgrade, uninstall clean-up verification",     engine:"manual",    automated:false, severity:"medium", tags:[] },
  { id:"config",       name:"Configuration Testing",    group:"Compatibility", category:"Platform",description:"Correct behaviour across environment configurations",         engine:"pattern",   automated:true,  severity:"medium", tags:[] },
]

// ── Test Design Techniques ─────────────────────────────────────────────────── //
const DESIGN: TestDef[] = [
  { id:"bva",          name:"Boundary Value Analysis",  group:"Techniques", category:"Design",   description:"Test at and around boundary conditions",                    engine:"pytest",  automated:true,  severity:"high",   tags:["pytest"] },
  { id:"ep",           name:"Equivalence Partitioning", group:"Techniques", category:"Design",   description:"Group inputs into equivalent classes, test one per class",  engine:"pytest",  automated:true,  severity:"high",   tags:["pytest"] },
  { id:"decision",     name:"Decision Table Testing",   group:"Techniques", category:"Design",   description:"Combinatorial business-rule coverage via decision tables",   engine:"manual",  automated:false, severity:"medium", tags:[] },
  { id:"state_trans",  name:"State Transition Testing", group:"Techniques", category:"Design",   description:"State machine coverage — legal and illegal transitions",     engine:"pytest",  automated:true,  severity:"critical",tags:["pytest"] },
  { id:"use_case",     name:"Use Case Testing",         group:"Techniques", category:"Design",   description:"Actor / system interaction scenario coverage",               engine:"manual",  automated:false, severity:"high",   tags:[] },
  { id:"pairwise",     name:"Pairwise Testing",         group:"Techniques", category:"Design",   description:"Combinatorial factor coverage with minimal test cases",      engine:"manual",  automated:false, severity:"medium", tags:[] },
  { id:"error_guess",  name:"Error Guessing",           group:"Techniques", category:"Heuristic",description:"Intuition-based injection of likely fault conditions",       engine:"manual",  automated:false, severity:"medium", tags:[] },
  { id:"risk_based",   name:"Risk-Based Testing",       group:"Techniques", category:"Heuristic",description:"Prioritise tests by risk exposure and business impact",      engine:"pattern", automated:true,  severity:"high",   tags:[] },
  { id:"model_based",  name:"Model-Based Testing",      group:"Techniques", category:"Automation",description:"Generate test cases from formal models or diagrams",        engine:"manual",  automated:false, severity:"medium", tags:[] },
]

// ── Code Quality ───────────────────────────────────────────────────────────── //
const CODE: TestDef[] = [
  { id:"static_analysis",name:"Static Code Analysis",  group:"Code Quality", category:"Static",  description:"Automated lint, style, and bug-detection scan",             engine:"bandit",  automated:true,  severity:"high",   tags:["bandit"] },
  { id:"code_review",    name:"Code Review",            group:"Code Quality", category:"Static",  description:"Automated rule-based code quality analysis",                engine:"bandit",  automated:true,  severity:"high",   tags:["bandit"] },
  { id:"peer_review",    name:"Peer Review",            group:"Code Quality", category:"Manual",  description:"Human peer-review checklist for logic and standards",        engine:"manual",  automated:false, severity:"medium", tags:[] },
  { id:"walkthrough",    name:"Walkthrough",            group:"Code Quality", category:"Manual",  description:"Author-led walk through the code for understanding",         engine:"manual",  automated:false, severity:"low",    tags:[] },
  { id:"tech_review",    name:"Technical Review",       group:"Code Quality", category:"Static",  description:"Technical correctness and architecture review",              engine:"bandit",  automated:true,  severity:"medium", tags:["bandit"] },
  { id:"inspection",     name:"Formal Inspection",      group:"Code Quality", category:"Static",  description:"Structured defect discovery with roles and checklists",      engine:"bandit",  automated:true,  severity:"high",   tags:["bandit"] },
  { id:"mutation",       name:"Mutation Testing",       group:"Code Quality", category:"Dynamic", description:"Introduce small code mutations — verify tests catch them",   engine:"coverage",automated:true,  severity:"medium", tags:["pytest","coverage"] },
  { id:"dynamic",        name:"Dynamic Testing",        group:"Code Quality", category:"Dynamic", description:"Runtime behaviour analysis and profiling",                   engine:"pytest",  automated:true,  severity:"high",   tags:["pytest"] },
]

// ── Specialised ────────────────────────────────────────────────────────────── //
const SPECIALISED: TestDef[] = [
  { id:"db",            name:"Database Testing",          group:"Specialised", category:"Data",      description:"Schema, constraints, RLS, indexes, query performance",    engine:"db_check", automated:true,  severity:"critical", tags:[] },
  { id:"etl",           name:"ETL Testing",               group:"Specialised", category:"Data",      description:"Extract-Transform-Load pipeline correctness",              engine:"db_check", automated:true,  severity:"high",     tags:[] },
  { id:"data_migration",name:"Data Migration Testing",    group:"Specialised", category:"Data",      description:"Pre/post migration row counts, checksums, integrity",      engine:"db_check", automated:true,  severity:"critical", tags:[] },
  { id:"data_integrity",name:"Data Integrity Testing",    group:"Specialised", category:"Data",      description:"Referential integrity, constraint enforcement, orphan rows",engine:"db_check", automated:true,  severity:"critical", tags:[] },
  { id:"microservices", name:"Microservices Testing",     group:"Specialised", category:"Arch",      description:"Individual service contracts, inter-service communication",engine:"http_probe",automated:true,  severity:"high",     tags:[] },
  { id:"api_contract",  name:"API Contract Testing",      group:"Specialised", category:"Arch",      description:"OpenAPI / Pact contract compliance between services",       engine:"http_probe",automated:true,  severity:"high",     tags:[] },
  { id:"chaos",         name:"Chaos Testing",             group:"Specialised", category:"Resilience",description:"Random failure injection to probe system resilience",       engine:"pytest",   automated:true,  severity:"high",     tags:["pytest"] },
  { id:"monkey",        name:"Monkey Testing",            group:"Specialised", category:"Resilience",description:"Random, unscripted inputs to find unexpected crashes",      engine:"pytest",   automated:true,  severity:"medium",   tags:["pytest"] },
  { id:"gorilla",       name:"Gorilla Testing",           group:"Specialised", category:"Resilience",description:"Intensive, repeated testing of a single module",            engine:"pytest",   automated:true,  severity:"medium",   tags:["pytest"] },
  { id:"fuzz",          name:"Fuzz Testing",              group:"Specialised", category:"Resilience",description:"Malformed/random input injection to find parsing errors",   engine:"pattern",  automated:true,  severity:"high",     tags:[] },
  { id:"a_b",           name:"A/B Testing",               group:"Specialised", category:"Product",   description:"Measure user behaviour difference between two variants",    engine:"manual",   automated:false, severity:"low",      tags:[] },
  { id:"canary",        name:"Canary Testing",            group:"Specialised", category:"DevOps",    description:"Gradual rollout validation with a small user cohort",        engine:"manual",   automated:false, severity:"medium",   tags:[] },
  { id:"cloud",         name:"Cloud Testing",             group:"Specialised", category:"Platform",  description:"Cloud resource provisioning, IAM, network, storage checks",  engine:"docker",   automated:true,  severity:"high",     tags:[] },
  { id:"container",     name:"Container / Docker Testing",group:"Specialised", category:"Platform",  description:"Image security, Dockerfile lint, runtime checks",             engine:"docker",   automated:true,  severity:"high",     tags:[] },
]

// ── DevOps ─────────────────────────────────────────────────────────────────── //
const DEVOPS: TestDef[] = [
  { id:"continuous",   name:"Continuous Testing",        group:"DevOps", category:"CI/CD",       description:"Test every commit via the CI pipeline",                     engine:"pytest",    automated:true, severity:"high",     tags:["pytest"] },
  { id:"shift_left",   name:"Shift-Left Testing",        group:"DevOps", category:"CI/CD",       description:"Run static analysis and unit tests at earliest stage",      engine:"bandit",    automated:true, severity:"high",     tags:["bandit"] },
  { id:"bvt",          name:"Build Verification Testing",group:"DevOps", category:"Release",     description:"Smoke test the build artifact before wider deployment",      engine:"pytest",    automated:true, severity:"critical", tags:["pytest"] },
  { id:"release",      name:"Release Testing",           group:"DevOps", category:"Release",     description:"Full test pass before a production release",                engine:"pytest",    automated:true, severity:"critical", tags:["pytest"] },
  { id:"prod_test",    name:"Production Testing",        group:"DevOps", category:"Release",     description:"Synthetic probes against live production endpoints",         engine:"http_probe",automated:true, severity:"high",     tags:[] },
  { id:"synthetic_mon",name:"Synthetic Monitoring",      group:"DevOps", category:"Observability",description:"Scheduled synthetic transactions to validate live system", engine:"http_probe",automated:true, severity:"high",     tags:[] },
]

// ── AI / ML ────────────────────────────────────────────────────────────────── //
const AI_ML: TestDef[] = [
  { id:"model_val",    name:"Model Validation",          group:"AI/ML", category:"Quality",     description:"Accuracy, precision, recall vs. held-out test set",         engine:"pytest", automated:true,  severity:"critical", tags:["pytest"] },
  { id:"bias",         name:"Bias Testing",              group:"AI/ML", category:"Fairness",    description:"Demographic parity, equalised odds across protected groups", engine:"pytest", automated:true,  severity:"critical", tags:["pytest"] },
  { id:"fairness",     name:"Fairness Testing",          group:"AI/ML", category:"Fairness",    description:"Disparate impact and predictive parity analysis",            engine:"pytest", automated:true,  severity:"critical", tags:["pytest"] },
  { id:"robustness",   name:"Robustness Testing",        group:"AI/ML", category:"Quality",     description:"Performance under distribution shift and noisy inputs",      engine:"pytest", automated:true,  severity:"high",     tags:["pytest"] },
  { id:"drift",        name:"Drift Testing",             group:"AI/ML", category:"Quality",     description:"Data drift and model degradation detection over time",       engine:"pytest", automated:true,  severity:"high",     tags:["pytest"] },
  { id:"explainability",name:"Explainability Testing",   group:"AI/ML", category:"Transparency",description:"SHAP/LIME feature importance and decision auditability",     engine:"manual", automated:false, severity:"medium",   tags:[] },
  { id:"adversarial",  name:"Adversarial Testing",       group:"AI/ML", category:"Security",    description:"Adversarial example construction and robustness measurement",engine:"pytest", automated:true,  severity:"high",     tags:["pytest"] },
]

// ── Master catalog ─────────────────────────────────────────────────────────── //
const ALL: TestDef[] = [
  ...FUNCTIONAL, ...NON_FUNCTIONAL, ...SECURITY, ...COMPAT,
  ...DESIGN, ...CODE, ...SPECIALISED, ...DEVOPS, ...AI_ML,
]

export const CATALOG_GROUPS: Record<string, TestDef[]> = {}
for (const t of ALL) {
  if (!CATALOG_GROUPS[t.group]) CATALOG_GROUPS[t.group] = []
  CATALOG_GROUPS[t.group].push(t)
}

// ── Cyber categories ───────────────────────────────────────────────────────── //
export const CYBER_CATEGORIES: CyberCategory[] = [
  { id:"vuln_assessment", name:"Vulnerability Assessment", tests:[
    { id:"cy_vuln_scan",     name:"Vulnerability Scanning",   description:"CVE scan of deps and code",                   engine:"pip_audit",  automated:true,  severity:"critical" },
    { id:"cy_config_review", name:"Configuration Review",     description:"Insecure defaults, debug flags, exposed secrets",engine:"pattern",  automated:true,  severity:"high"     },
    { id:"cy_patch",         name:"Missing Patch Assessment", description:"Outdated packages with known CVEs",            engine:"pip_audit",  automated:true,  severity:"high"     },
    { id:"cy_cve",           name:"CVE Analysis",             description:"Matched CVE database against installed versions",engine:"pip_audit", automated:true,  severity:"critical" },
    { id:"cy_risk",          name:"Risk Assessment",          description:"Prioritised risk scoring by severity",          engine:"bandit",     automated:true,  severity:"high"     },
    { id:"cy_threat",        name:"Threat Assessment",        description:"Attack surface and threat modelling",           engine:"bandit",     automated:true,  severity:"high"     },
    { id:"cy_exposure",      name:"Exposure Assessment",      description:"Public endpoint and data exposure analysis",    engine:"http_probe", automated:true,  severity:"high"     },
  ]},
  { id:"pentest", name:"Penetration Testing", tests:[
    { id:"cy_ext_net",       name:"External Network Pentest",     description:"External port/service enumeration",       engine:"nmap",       automated:true,  severity:"critical" },
    { id:"cy_int_net",       name:"Internal Network Pentest",     description:"Internal network attack surface",         engine:"nmap",       automated:true,  severity:"critical" },
    { id:"cy_webapp_pen",    name:"Web Application Pentest",      description:"OWASP Top 10 active probing",            engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_api_pen",       name:"API Penetration Testing",      description:"REST/GraphQL API attack simulation",     engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_cloud_pen",     name:"Cloud Penetration Testing",    description:"Cloud config and IAM enumeration",       engine:"docker",     automated:true,  severity:"critical" },
    { id:"cy_container_pen", name:"Container Penetration Testing",description:"Container escape and privilege escalation",engine:"docker",   automated:true,  severity:"critical" },
    { id:"cy_social_eng",    name:"Social Engineering Pentest",   description:"Phishing campaign simulation checklist", engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_red_team",      name:"Red Team Exercise",            description:"Full adversary simulation checklist",    engine:"manual",     automated:false, severity:"critical" },
  ]},
  { id:"auth_testing", name:"Authentication Testing", tests:[
    { id:"cy_login",         name:"Login Testing",           description:"Login flow correctness and error handling",    engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_pwd_policy",    name:"Password Policy Testing", description:"Minimum length, complexity, history checks",  engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_brute",         name:"Brute Force Resistance",  description:"Account lockout and rate-limit validation",    engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_mfa",           name:"MFA Testing",             description:"TOTP/FIDO2 factor enforcement",               engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_oauth",         name:"OAuth Testing",           description:"OAuth 2.0 flow, PKCE, token handling",        engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_jwt",           name:"JWT Security Testing",    description:"Algorithm confusion, none alg, weak secrets",  engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_saml",          name:"SAML Testing",            description:"XML signature, assertion replay checks",       engine:"http_probe", automated:true,  severity:"high"     },
  ]},
  { id:"authz_testing", name:"Authorization Testing", tests:[
    { id:"cy_rbac",          name:"RBAC Testing",            description:"Role boundary enforcement",                    engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_priv_esc",      name:"Privilege Escalation",    description:"Horizontal and vertical escalation attempts",  engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_idor",          name:"IDOR Testing",            description:"Direct object reference enumeration",          engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_bac",           name:"Broken Access Control",   description:"Forced browsing and access control gaps",      engine:"http_probe", automated:true,  severity:"critical" },
  ]},
  { id:"session_testing", name:"Session Management Testing", tests:[
    { id:"cy_session_fix",    name:"Session Fixation",       description:"Pre-auth session ID reuse attack",             engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_session_timeout",name:"Session Timeout",        description:"Idle and absolute timeout validation",         engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_cookie_sec",     name:"Cookie Security",        description:"Secure, HttpOnly, SameSite flags",             engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_csrf",           name:"CSRF Token Validation",  description:"Anti-CSRF token presence and validation",      engine:"http_probe", automated:true,  severity:"high"     },
  ]},
  { id:"input_validation", name:"Input Validation Testing", tests:[
    { id:"cy_sqli",          name:"SQL Injection",           description:"Raw SQL, unsanitised parameters",              engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_nosqli",        name:"NoSQL Injection",         description:"MongoDB operator injection patterns",          engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_cmdi",          name:"Command Injection",       description:"OS command execution via user input",          engine:"bandit",     automated:true,  severity:"critical" },
    { id:"cy_ssti",          name:"Template Injection (SSTI)",description:"Server-side template engine injection",       engine:"bandit",     automated:true,  severity:"critical" },
    { id:"cy_xxe",           name:"XXE Injection",           description:"XML external entity processing",               engine:"bandit",     automated:true,  severity:"critical" },
    { id:"cy_crlf",          name:"CRLF Injection",          description:"HTTP response splitting via CRLF",             engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_host_hdr",      name:"Host Header Injection",   description:"Host header manipulation attacks",             engine:"http_probe", automated:true,  severity:"high"     },
  ]},
  { id:"xss_testing", name:"Cross-Site Attack Testing", tests:[
    { id:"cy_xss_stored",    name:"Stored XSS",              description:"Persistent XSS in DB-rendered content",        engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_xss_reflected", name:"Reflected XSS",           description:"URL parameter reflected without encoding",     engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_xss_dom",       name:"DOM XSS",                 description:"Client-side DOM manipulation sinks",           engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_csrf_attack",   name:"CSRF Attack Testing",     description:"State-changing requests without token",        engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_clickjacking",  name:"Clickjacking",            description:"X-Frame-Options / CSP frame-ancestors",        engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_cors",          name:"CORS Testing",            description:"CORS origin whitelist and credentials",        engine:"http_probe", automated:true,  severity:"high"     },
  ]},
  { id:"api_security", name:"API Security Testing", tests:[
    { id:"cy_rest_api",      name:"REST API Security",       description:"REST verb abuse, status codes, schema",        engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_graphql",       name:"GraphQL Security",        description:"Introspection, batching, nested queries",      engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_api_rate",      name:"Rate Limiting Testing",   description:"API rate-limit bypass and enumeration",        engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_api_fuzzing",   name:"API Fuzzing",             description:"Malformed payload injection into endpoints",   engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_bola",          name:"BOLA / IDOR (API)",       description:"Broken Object Level Authorization",            engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_mass_assign",   name:"Mass Assignment Testing", description:"Unwhitelisted property binding vulnerabilities",engine:"pattern",   automated:true,  severity:"high"     },
  ]},
  { id:"webapp_security", name:"Web Application Security", tests:[
    { id:"cy_file_upload",   name:"File Upload Security",    description:"MIME type bypass, path traversal via upload",  engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_path_traversal",name:"Directory Traversal",     description:"../ path traversal and LFI",                  engine:"bandit",     automated:true,  severity:"critical" },
    { id:"cy_ssrf",          name:"SSRF Testing",            description:"Server-side request forgery payloads",         engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_open_redirect", name:"Open Redirect Testing",   description:"Unvalidated redirect destinations",            engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_cache_poison",  name:"Cache Poisoning",         description:"Cache-key injection and poisoning",            engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_smuggling",     name:"Request Smuggling",       description:"HTTP/1.1 CL.TE and TE.CL smuggling",          engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_biz_logic",     name:"Business Logic Testing",  description:"Abuse of legitimate workflows",               engine:"manual",     automated:false, severity:"high"     },
  ]},
  { id:"secure_code", name:"Secure Code Testing", tests:[
    { id:"cy_sast2",         name:"SAST",                    description:"Static Application Security Testing",          engine:"bandit",     automated:true,  severity:"critical" },
    { id:"cy_dast2",         name:"DAST",                    description:"Dynamic Application Security Testing",         engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_secret_det",    name:"Secret Detection",        description:"API keys, tokens, passwords in code",          engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_dep_analysis",  name:"Dependency Analysis",     description:"Third-party library vulnerability mapping",    engine:"pip_audit",  automated:true,  severity:"high"     },
    { id:"cy_sca2",          name:"Software Composition Analysis",description:"OSS license and CVE risk by component",  engine:"pip_audit",  automated:true,  severity:"high"     },
  ]},
  { id:"cloud_security", name:"Cloud Security Testing", tests:[
    { id:"cy_iam",           name:"IAM Review",              description:"Over-permissive roles and policies",           engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_bucket",        name:"Storage Bucket Security", description:"Public bucket ACL and encryption",             engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_container_sec", name:"Container Security",      description:"Image scanning, root user, capabilities",      engine:"docker",     automated:true,  severity:"high"     },
    { id:"cy_k8s",           name:"Kubernetes Security",     description:"Pod security, network policies, RBAC",         engine:"docker",     automated:true,  severity:"high"     },
    { id:"cy_iac",           name:"Infrastructure as Code Security",description:"Terraform/Ansible/CFN misconfigs",     engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_secret_mgmt",   name:"Secret Management",       description:"Secrets in env vars, config files, repos",    engine:"pattern",    automated:true,  severity:"critical" },
  ]},
  { id:"network_security", name:"Network Security Testing", tests:[
    { id:"cy_port_scan",     name:"Port Scanning",           description:"Open port and service enumeration",            engine:"nmap",       automated:true,  severity:"high"     },
    { id:"cy_banner",        name:"Banner Grabbing",         description:"Service version and fingerprint collection",   engine:"nmap",       automated:true,  severity:"medium"   },
    { id:"cy_firewall",      name:"Firewall Testing",        description:"Firewall rule bypass and egress testing",      engine:"nmap",       automated:true,  severity:"high"     },
    { id:"cy_dns_sec",       name:"DNS Security Testing",    description:"DNSSEC, zone transfer, subdomain enum",        engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_net_seg",       name:"Network Segmentation",    description:"VLAN isolation and lateral movement paths",    engine:"nmap",       automated:true,  severity:"high"     },
  ]},
  { id:"crypto_testing", name:"Cryptography Testing", tests:[
    { id:"cy_tls",           name:"TLS Configuration",       description:"Protocol version, cipher suites, HSTS",        engine:"sslyze",     automated:true,  severity:"critical" },
    { id:"cy_cert",          name:"Certificate Validation",  description:"Expiry, chain, hostname, revocation",          engine:"sslyze",     automated:true,  severity:"critical" },
    { id:"cy_enc_strength",  name:"Encryption Strength",     description:"Weak algorithms: MD5, SHA1, DES, RC4",         engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_key_mgmt",      name:"Key Management",          description:"Hardcoded keys, weak entropy sources",         engine:"pattern",    automated:true,  severity:"critical" },
    { id:"cy_hash",          name:"Hash Algorithm Validation",description:"Password storage: bcrypt vs MD5 etc.",        engine:"pattern",    automated:true,  severity:"critical" },
  ]},
  { id:"mobile_security", name:"Mobile Security Testing", tests:[
    { id:"cy_android",       name:"Android Security Testing",description:"AndroidManifest, Logcat, storage, exports",    engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_ios",           name:"iOS Security Testing",    description:"Info.plist, keychain, ATS configuration",      engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_cert_pin",      name:"Certificate Pinning",     description:"Pin bypass resistance in mobile apps",         engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_root_detect",   name:"Root/Jailbreak Detection",description:"Runtime tamper detection checks",              engine:"pattern",    automated:true,  severity:"high"     },
  ]},
  { id:"fuzz_testing", name:"Fuzz Testing", tests:[
    { id:"cy_proto_fuzz",    name:"Protocol Fuzzing",        description:"Malformed protocol messages",                  engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_api_fuzz",      name:"API Fuzzing",             description:"Random/boundary inputs to API endpoints",      engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_input_fuzz",    name:"Input Fuzzing",           description:"Random inputs to all form fields / params",    engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_file_fuzz",     name:"File Format Fuzzing",     description:"Malformed file uploads",                      engine:"pattern",    automated:true,  severity:"high"     },
  ]},
  { id:"dos_testing", name:"Denial-of-Service Testing", tests:[
    { id:"cy_dos",           name:"DoS Testing",             description:"Single-source resource exhaustion",            engine:"locust",     automated:true,  severity:"high"     },
    { id:"cy_rate_limit_val",name:"Rate Limiting Validation",description:"API rate-limit enforcement check",             engine:"http_probe", automated:true,  severity:"high"     },
    { id:"cy_resource_exhaust",name:"Resource Exhaustion",   description:"CPU, memory, connection pool exhaustion",      engine:"locust",     automated:true,  severity:"high"     },
  ]},
  { id:"iam_testing", name:"Identity & Access Testing", tests:[
    { id:"cy_ad",            name:"Active Directory Assessment",description:"AD attack paths and Kerberos checks",       engine:"manual",     automated:false, severity:"critical" },
    { id:"cy_sso",           name:"Single Sign-On Testing",  description:"SSO bypass and federation trust checks",       engine:"http_probe", automated:true,  severity:"critical" },
    { id:"cy_ldap_sec",      name:"LDAP Security",           description:"LDAP injection and anonymous bind",            engine:"pattern",    automated:true,  severity:"high"     },
  ]},
  { id:"infra_security", name:"Infrastructure Security Testing", tests:[
    { id:"cy_os_hard",       name:"OS Hardening Review",     description:"CIS benchmark compliance checklist",           engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_docker_sec",    name:"Docker Security",         description:"Dockerfile, runtime, capability audit",        engine:"docker",     automated:true,  severity:"high"     },
    { id:"cy_fw_review",     name:"Firewall Review",         description:"Rule-base analysis and egress control",        engine:"manual",     automated:false, severity:"high"     },
  ]},
  { id:"human_security", name:"Human Security Testing", tests:[
    { id:"cy_phish",         name:"Phishing Campaign",       description:"Simulated spear-phishing assessment",          engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_vishing",       name:"Vishing (Voice Phishing)",description:"Phone-based social engineering test",          engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_usb_drop",      name:"USB Drop Testing",        description:"Physical media attack simulation",             engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_tailgate",      name:"Tailgating Testing",      description:"Physical access control bypass",               engine:"manual",     automated:false, severity:"medium"   },
  ]},
  { id:"adversary_sim", name:"Adversary Simulation", tests:[
    { id:"cy_red_team2",     name:"Red Team Exercise",       description:"Full-scope adversary emulation",               engine:"manual",     automated:false, severity:"critical" },
    { id:"cy_purple_team",   name:"Purple Team Exercise",    description:"Collaborative attack/detect cycle",            engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_bas",           name:"Breach & Attack Simulation",description:"BAS platform-driven attack validation",     engine:"manual",     automated:false, severity:"high"     },
    { id:"cy_mitre",         name:"MITRE ATT&CK Mapping",   description:"TTP coverage against ATT&CK framework",        engine:"manual",     automated:false, severity:"high"     },
  ]},
  { id:"compliance_gov", name:"Compliance & Governance Testing", tests:[
    { id:"cy_sec_config",    name:"Security Configuration Review",description:"Baseline security config audit",         engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_audit_ready",   name:"Audit Readiness Testing", description:"Evidence collection and log coverage",        engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_logging",       name:"Logging & Monitoring Review",description:"SIEM coverage and alert completeness",     engine:"pattern",    automated:true,  severity:"high"     },
    { id:"cy_ir",            name:"Incident Response Testing",description:"IR playbook drill and tabletop exercise",    engine:"manual",     automated:false, severity:"critical" },
    { id:"cy_bcp",           name:"Business Continuity Testing",description:"BCP/DR plan completeness and execution",  engine:"manual",     automated:false, severity:"critical" },
  ]},
]

// ── Sandbox types ──────────────────────────────────────────────────────────── //
function sbTests(prefix: string, names: string[], severity = "medium"): SandboxTest[] {
  return names.map((name, i) => ({
    id: `${prefix}_${i}`,
    name,
    description: name,
    automated: true,
    severity,
  }))
}

export const SANDBOX_TYPES: SandboxType[] = [
  { id:"functional_sb", name:"Functional Sandbox",           description:"Verify functionality without affecting production",
    tests: sbTests("func", ["Feature validation","User workflow testing","API testing","UI testing","Integration testing"]) },
  { id:"security_sb",   name:"Security Sandbox",             description:"Observe malicious behaviour safely",
    tests: sbTests("sec",  ["Malware analysis","Exploit testing","Payload execution","Phishing attachment analysis","Ransomware analysis","Zero-day investigation"],"high") },
  { id:"pentest_sb",    name:"Penetration Testing Sandbox",  description:"Attack a cloned environment without business risk",
    tests: sbTests("pt",   ["Exploit development","Privilege escalation","Lateral movement","Persistence testing","Credential attacks","Post-exploitation"],"critical") },
  { id:"api_sb",        name:"API Sandbox",                  description:"Test against non-production APIs safely",
    tests: sbTests("api",  ["Endpoint testing","Authentication testing","OAuth testing","Rate limiting","Webhook validation","SDK testing"]) },
  { id:"cloud_sb",      name:"Cloud Sandbox",                description:"Safely test cloud resources and configurations",
    tests: sbTests("cld",  ["Infrastructure testing","IAM testing","Network security","Storage configuration","Auto-scaling","IaC validation"],"high") },
  { id:"dev_sb",        name:"Dev/Test Sandbox",             description:"Day-to-day development and testing",
    tests: sbTests("dev",  ["New feature development","Branch testing","CI pipeline","CD pipeline","Dependency upgrades","Database migrations"]) },
  { id:"database_sb",   name:"Database Sandbox",             description:"Work with realistic data without risking production",
    tests: sbTests("db",   ["Query testing","Backup restoration","Data migration","ETL testing","Performance tuning","Schema changes"],"high") },
  { id:"mobile_sb",     name:"Mobile Sandbox",               description:"Test mobile apps across devices and operating systems",
    tests: sbTests("mob",  ["Android testing","iOS testing","Device compatibility","Permission testing","Push notifications","Mobile security"]) },
  { id:"browser_sb",    name:"Browser Sandbox",              description:"Validate browser-specific behaviour",
    tests: sbTests("br",   ["Cross-browser testing","Extension testing","JavaScript execution","Cookie behaviour","CORS testing","WebAssembly testing"]) },
  { id:"malware_sb",    name:"Malware Sandbox",              description:"Understand malicious software behaviour safely",
    tests: sbTests("mal",  ["Static analysis","Dynamic analysis","Behavioural analysis","Network traffic monitoring","Registry monitoring","Memory analysis"],"critical") },
  { id:"ai_sb",         name:"AI/ML Sandbox",                description:"Evaluate AI models before deployment",
    tests: sbTests("ai",   ["Model evaluation","Prompt testing","Hallucination testing","Adversarial prompt testing","Bias testing","Safety testing"]) },
  { id:"perf_sb",       name:"Performance Sandbox",          description:"Measure system behaviour under varying workloads",
    tests: sbTests("perf", ["Load testing","Stress testing","Soak testing","Spike testing","Capacity testing","Scalability testing"],"high") },
  { id:"network_sb",    name:"Network Sandbox",              description:"Validate network configurations safely",
    tests: sbTests("net",  ["Firewall testing","Routing validation","VPN testing","DNS testing","IDS/IPS testing","Network segmentation"],"high") },
  { id:"container_sb",  name:"Container Sandbox",            description:"Test containerised applications and infrastructure",
    tests: sbTests("con",  ["Docker image testing","Kubernetes deployment","Container escape testing","Runtime security","Secret management","Image vulnerability scanning"],"high") },
  { id:"iot_sb",        name:"IoT Sandbox",                  description:"Safely test connected devices and embedded software",
    tests: sbTests("iot",  ["Firmware testing","Device communication","MQTT testing","Sensor validation","OTA update testing","Embedded security"],"high") },
]

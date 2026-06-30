/** Foci-Med Harness API client — v2 */

const BASE = import.meta.env.VITE_API_URL ?? ''

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts?.headers ?? {}) },
    ...opts,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

// ── Types ──────────────────────────────────────────────────────────────────── #
export interface Stats {
  db: { tenants: number; patients: number; claims: number }
  jobs: { total: number; done: number }
  audits_total?: number
  db_connected: boolean
  error?: string
}

export interface Config {
  project_dir: string
  db_host: string
  db_port: number
  db_name: string
  db_user: string
  app_user: string
}

export type JobType = 'seed' | 'test' | 'catalog' | 'cyber' | 'sandbox'
export type JobStatus = 'running' | 'done' | 'error'

export interface Job {
  id: string
  type: JobType
  status: JobStatus
  started: number
  summary?: Record<string, unknown>
}

export interface SeedParams {
  n_tenants: number
  n_patients_per_tenant: number
  include_encounters: boolean
  include_claims: boolean
  clear_existing: boolean
}

export interface TestParams {
  suites: string[]
  project_dir?: string
}

export interface CatalogRunParams {
  test_ids: string[]
  project_dir?: string
  target_url?: string
}

export interface CyberRunParams {
  test_ids: string[]
  target_url: string
  project_dir?: string
}

export interface SandboxRunParams {
  sandbox_id: string
  test_ids: string[]
  target_url?: string
  project_dir?: string
}

export interface AuditHistory {
  job_id: string
  audit_id?: string
  generated_at?: string
  target?: string
  overall_score?: number
  risk_level?: string
  total?: number
  passed?: number
  failed?: number
  mode?: string
}

export interface Finding {
  test_id: string
  test_name: string
  severity: string
  title: string
  description: string
  location: string
  evidence: string
}

export interface CategoryScore {
  name: string
  score: number
  risk: string
  passed: number
  failed: number
  warned: number
  skipped: number
  manual: number
  tests: TestDetail[]
}

export interface TestDetail {
  id: string
  name: string
  status: string
  score: number
  duration: number
  tool: string
  findings_count: number
  findings: Finding[]
  recommendations: string[]
  manual_checklist: { item: string; done: boolean }[]
}

export interface AuditReport {
  id: string
  generated_at: string
  target: string
  overall_score: number
  risk_level: string
  categories: CategoryScore[]
  critical_findings: Finding[]
  all_findings: Finding[]
  recommendations: string[]
  passed: number
  failed: number
  warned: number
  skipped: number
  manual: number
  total: number
  owasp_coverage: Record<string, { covered: number; total_map: number; passed: number; status: string }>
  executive_summary: string
  mode: string
}

// ── API calls ──────────────────────────────────────────────────────────────── #
export const api = {
  health:      () => req<{ status: string }>('/api/health'),
  stats:       () => req<Stats>('/api/stats'),
  getConfig:   () => req<Config>('/api/config'),
  updateConfig:(body: Partial<Config> & { db_password?: string }) =>
    req<{ updated: boolean }>('/api/config', { method: 'POST', body: JSON.stringify(body) }),

  startSeed: (params: SeedParams) =>
    req<{ job_id: string }>('/api/seed', { method: 'POST', body: JSON.stringify(params) }),

  startTests: (params: TestParams) =>
    req<{ job_id: string }>('/api/tests/run', { method: 'POST', body: JSON.stringify(params) }),

  jobs:    () => req<Job[]>('/api/jobs'),
  catalog: () => req<unknown>('/api/catalog'),

  runCatalog: (params: CatalogRunParams) =>
    req<{ job_id: string }>('/api/catalog/run', { method: 'POST', body: JSON.stringify(params) }),

  getAudit: (jobId: string) => req<AuditReport>(`/api/audit/${jobId}`),
  history:  () => req<AuditHistory[]>('/api/history'),

  uploadProject: (files: FileList | File[]) => {
    const fd = new FormData()
    Array.from(files).forEach(f => fd.append('files', f, (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name))
    return fetch(`${BASE}/api/upload`, { method: 'POST', body: fd }).then(r => {
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
      return r.json() as Promise<{ upload_id: string; project_dir: string; files_saved: number }>
    })
  },

  runCyber: (params: CyberRunParams) =>
    req<{ job_id: string }>('/api/cyber/run', { method: 'POST', body: JSON.stringify(params) }),

  runSandbox: (params: SandboxRunParams) =>
    req<{ job_id: string }>('/api/sandbox/run', { method: 'POST', body: JSON.stringify(params) }),

  reset: () => req<{ reset: boolean; ts: number }>('/api/reset', { method: 'POST' }),
}

// ── SSE stream helper ──────────────────────────────────────────────────────── #
export interface LogEvent {
  level?: string
  msg?: string
  done?: boolean
  type?: string
  value?: number
  summary?: Record<string, unknown>
  stats?: Record<string, unknown>
  ping?: boolean
  audit_id?: string
  score?: number
  risk?: string
  test_id?: string
  test_name?: string
  status?: string
  error?: string
}

export function openStream(
  url: string,
  onEvent: (e: LogEvent) => void,
  onDone?: () => void,
): () => void {
  const es = new EventSource(`${BASE}${url}`)
  es.onmessage = (ev) => {
    try {
      const data: LogEvent = JSON.parse(ev.data)
      if (data.ping) return
      onEvent(data)
      if (data.done) {
        es.close()
        onDone?.()
      }
    } catch {
      // ignore malformed frames
    }
  }
  es.onerror = () => { es.close(); onDone?.() }
  return () => es.close()
}

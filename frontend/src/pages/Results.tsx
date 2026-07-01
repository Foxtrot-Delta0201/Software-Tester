import { useEffect, useState } from 'react'
import { RefreshCw, Users, FlaskConical, Clock, ChevronDown, ChevronRight, Shield, Box, BookOpen, FileBarChart2 } from 'lucide-react'
import { api, type Job, type AuditReport } from '../api'
import StatusBadge from '../components/StatusBadge'
import AuditReportView from '../components/AuditReport'

export default function Results() {
  const [jobs,      setJobs]      = useState<Job[]>([])
  const [loading,   setLoading]   = useState(true)
  const [expanded,  setExpanded]  = useState<string | null>(null)
  const [auditMap,  setAuditMap]  = useState<Record<string, AuditReport | 'loading' | null>>({})

  const load = async () => {
    setLoading(true)
    const data = await api.jobs().catch(() => [])
    setJobs(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function toggleExpand(jobId: string, hasAudit: boolean) {
    if (expanded === jobId) { setExpanded(null); return }
    setExpanded(jobId)
    if (hasAudit && !auditMap[jobId]) {
      setAuditMap(m => ({ ...m, [jobId]: 'loading' }))
      try {
        const r = await api.getAudit(jobId)
        setAuditMap(m => ({ ...m, [jobId]: r }))
      } catch {
        setAuditMap(m => ({ ...m, [jobId]: null }))
      }
    }
  }

  const seedJobs    = jobs.filter(j => j.type === 'seed')
  const testJobs    = jobs.filter(j => j.type === 'test')
  const auditJobs   = jobs.filter(j => ['catalog', 'cyber', 'sandbox'].includes(j.type))

  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Job Results</h1>
          <p className="text-slate-400 text-sm mt-0.5">All jobs from the current session</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-white/5 transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Audit jobs (catalog / cyber / sandbox) */}
      {auditJobs.length > 0 && (
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
            <FileBarChart2 size={15} className="text-blue-400" /> Audit Runs
            <span className="ml-1 px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-400 text-xs font-normal">{auditJobs.length}</span>
          </h2>
          <div className="space-y-2">
            {auditJobs.map(job => {
              const isExp   = expanded === job.id
              const audit   = auditMap[job.id]
              const typeTag = job.type === 'cyber' ? (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900/40 text-red-300">CYBER</span>
              ) : job.type === 'sandbox' ? (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900/40 text-green-300">SANDBOX</span>
              ) : (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/40 text-blue-300">CATALOG</span>
              )
              const Icon = job.type === 'cyber' ? Shield : job.type === 'sandbox' ? Box : BookOpen
              return (
                <div key={job.id} className="glass overflow-hidden">
                  <div
                    className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-white/5 transition-colors"
                    onClick={() => toggleExpand(job.id, job.status === 'done')}
                  >
                    <div className="flex items-center gap-3">
                      <button className="text-slate-400">
                        {isExp ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                      <Icon size={14} className="text-slate-400 shrink-0" />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-slate-200 font-mono">{job.id.slice(0, 8)}…</p>
                          {typeTag}
                        </div>
                        <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                          <Clock size={11} />
                          {new Date(job.started * 1000).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {job.status === 'done' && (
                        <span className="text-xs text-blue-400 hover:text-blue-300">View audit →</span>
                      )}
                      <StatusBadge status={job.status} />
                    </div>
                  </div>

                  {isExp && (
                    <div className="border-t px-5 py-4" style={{ borderColor: 'var(--border)' }}>
                      {audit === 'loading' && (
                        <p className="text-sm text-slate-400 text-center py-4">Loading audit report…</p>
                      )}
                      {audit === null && (
                        <p className="text-sm text-slate-500 text-center py-4">Audit report not available.</p>
                      )}
                      {audit && audit !== 'loading' && (
                        <AuditReportView report={audit} />
                      )}
                      {!audit && audit !== 'loading' && job.status !== 'done' && (
                        <p className="text-sm text-slate-500 text-center py-4">Job still running…</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Test runner jobs */}
      <Section
        title="Test Runs"
        icon={<FlaskConical size={15} className="text-green-400" />}
        jobs={testJobs}
        loading={loading}
        expanded={expanded}
        setExpanded={id => setExpanded(id)}
        renderSummary={(job) => {
          const s = job.summary as Record<string, unknown> | undefined
          if (!s) return null
          return (
            <div className="grid grid-cols-4 gap-3 mt-3">
              <Metric label="Passed"  value={s.passed  as number} color="text-green-400" />
              <Metric label="Failed"  value={s.failed  as number} color="text-red-400"   />
              <Metric label="Skipped" value={s.skipped as number} color="text-slate-500"  />
              <Metric label="Time"    value={`${s.elapsed_s as number}s`} color="text-slate-300" />
            </div>
          )
        }}
        renderExpanded={(job) => {
          const s = job.summary as Record<string, unknown> | undefined
          const suites = s?.suites as Record<string, string> | undefined
          if (!suites) return null
          return (
            <div className="mt-3 space-y-1">
              {Object.entries(suites).map(([suite, status]) => (
                <div key={suite} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5">
                  <span className="text-sm font-medium text-slate-300">{suite}</span>
                  <StatusBadge status={status} />
                </div>
              ))}
            </div>
          )
        }}
      />

      {/* Seed jobs */}
      <Section
        title="Data Seeds"
        icon={<Users size={15} className="text-blue-400" />}
        jobs={seedJobs}
        loading={loading}
        expanded={expanded}
        setExpanded={id => setExpanded(id)}
        renderSummary={(job) => {
          const s = job.summary as Record<string, unknown> | undefined
          const stats = s?.stats as Record<string, number> | undefined
          if (!stats) return null
          return (
            <div className="grid grid-cols-4 gap-3 mt-3">
              <Metric label="Patients"   value={stats.patients}   color="text-blue-400"   />
              <Metric label="Encounters" value={stats.encounters} color="text-purple-400" />
              <Metric label="Claims"     value={stats.claims}     color="text-orange-400" />
              <Metric label="Time"       value={`${stats.elapsed_s}s`} color="text-slate-300" />
            </div>
          )
        }}
        renderExpanded={() => null}
      />

      {jobs.length === 0 && !loading && (
        <div className="glass p-12 text-center text-slate-500 text-sm">
          No jobs recorded yet. Run tests to see results here.
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="text-center bg-white/5 border border-slate-700/40 rounded-lg py-2">
      <p className={`text-lg font-bold ${color}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  )
}

interface SectionProps {
  title:          string
  icon:           React.ReactNode
  jobs:           Job[]
  loading:        boolean
  expanded:       string | null
  setExpanded:    (id: string | null) => void
  renderSummary:  (job: Job) => React.ReactNode
  renderExpanded: (job: Job) => React.ReactNode
}

function Section({ title, icon, jobs, loading, expanded, setExpanded, renderSummary, renderExpanded }: SectionProps) {
  if (jobs.length === 0 && !loading) return null
  return (
    <div>
      <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
        {icon} {title}
        <span className="ml-1 px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-400 text-xs font-normal">{jobs.length}</span>
      </h2>
      <div className="space-y-2">
        {jobs.map(job => {
          const isExpanded = expanded === job.id
          return (
            <div key={job.id} className="glass overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setExpanded(isExpanded ? null : job.id)}
                    className="text-slate-400 hover:text-slate-200"
                  >
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </button>
                  <div>
                    <p className="text-sm font-medium text-slate-200 font-mono">{job.id.slice(0, 8)}…</p>
                    <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                      <Clock size={11} />
                      {new Date(job.started * 1000).toLocaleString()}
                    </p>
                  </div>
                </div>
                <StatusBadge status={job.status} />
              </div>

              {job.summary && (
                <div className="px-5 pb-4">
                  {renderSummary(job)}
                  {isExpanded && renderExpanded(job)}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

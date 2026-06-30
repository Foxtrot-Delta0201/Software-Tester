import { useEffect, useState } from 'react'
import { RefreshCw, Users, FlaskConical, Clock, ChevronDown, ChevronRight } from 'lucide-react'
import { api, type Job } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function Results() {
  const [jobs,     setJobs]     = useState<Job[]>([])
  const [loading,  setLoading]  = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    const data = await api.jobs()
    setJobs(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const seedJobs = jobs.filter(j => j.type === 'seed')
  const testJobs = jobs.filter(j => j.type === 'test')

  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Job Results</h1>
          <p className="text-slate-500 text-sm mt-0.5">All seed and test jobs from the current session</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg border border-slate-300 hover:bg-slate-100 transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Test jobs */}
      <Section
        title="Test Runs"
        icon={<FlaskConical size={15} className="text-green-600" />}
        jobs={testJobs}
        loading={loading}
        expanded={expanded}
        setExpanded={setExpanded}
        renderSummary={(job) => {
          const s = job.summary as Record<string, unknown> | undefined
          if (!s) return null
          return (
            <div className="grid grid-cols-4 gap-3 mt-3">
              <Metric label="Passed"  value={s.passed  as number} color="text-green-700" />
              <Metric label="Failed"  value={s.failed  as number} color="text-red-600"   />
              <Metric label="Skipped" value={s.skipped as number} color="text-slate-500"  />
              <Metric label="Time"    value={`${s.elapsed_s as number}s`} color="text-slate-700" />
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
                <div key={suite} className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50">
                  <span className="text-sm font-medium text-slate-700">{suite}</span>
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
        icon={<Users size={15} className="text-blue-600" />}
        jobs={seedJobs}
        loading={loading}
        expanded={expanded}
        setExpanded={setExpanded}
        renderSummary={(job) => {
          const s = job.summary as Record<string, unknown> | undefined
          const stats = s?.stats as Record<string, number> | undefined
          if (!stats) return null
          return (
            <div className="grid grid-cols-4 gap-3 mt-3">
              <Metric label="Patients"   value={stats.patients}   color="text-blue-700"   />
              <Metric label="Encounters" value={stats.encounters} color="text-purple-700" />
              <Metric label="Claims"     value={stats.claims}     color="text-orange-700" />
              <Metric label="Time"       value={`${stats.elapsed_s}s`} color="text-slate-700" />
            </div>
          )
        }}
        renderExpanded={() => null}
      />

      {jobs.length === 0 && !loading && (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-slate-400 text-sm">
          No jobs recorded yet. Seed data or run tests to see results here.
        </div>
      )}
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────────── #
function Metric({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="text-center bg-white border border-slate-100 rounded-lg py-2">
      <p className={`text-lg font-bold ${color}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
      <p className="text-xs text-slate-400">{label}</p>
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
        <span className="ml-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-normal">{jobs.length}</span>
      </h2>
      <div className="space-y-2">
        {jobs.map(job => {
          const isExpanded = expanded === job.id
          return (
            <div key={job.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setExpanded(isExpanded ? null : job.id)}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </button>
                  <div>
                    <p className="text-sm font-medium text-slate-800 font-mono">{job.id.slice(0, 8)}…</p>
                    <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                      <Clock size={11} />
                      {new Date(job.started * 1000).toLocaleString()}
                    </p>
                  </div>
                </div>
                <StatusBadge status={job.status} />
              </div>

              {/* Inline summary metrics */}
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

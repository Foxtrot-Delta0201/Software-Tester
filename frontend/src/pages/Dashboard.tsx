import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, Building2, FileText, CheckCircle, XCircle, Clock, Wifi, WifiOff } from 'lucide-react'
import { api, type Stats, type Job } from '../api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const nav = useNavigate()
  const [stats,   setStats]   = useState<Stats | null>(null)
  const [jobs,    setJobs]    = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    const [s, j] = await Promise.all([api.stats(), api.jobs()])
    setStats(s)
    setJobs(j)
    setLoading(false)
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 5_000)
    return () => clearInterval(id)
  }, [])

  const recent = jobs.slice(0, 6)
  const connected = stats?.db_connected ?? false

  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Harness Dashboard</h1>
          <p className="text-slate-500 text-sm mt-0.5">Monitor your tests and data pipeline at a glance</p>
        </div>
        <div className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-full border ${
          connected ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
          {connected ? 'DB connected' : 'DB offline'}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Tenants"  value={stats?.db.tenants  ?? 0} icon={Building2} color="blue"   loading={loading} />
        <StatCard label="Patients" value={stats?.db.patients ?? 0} icon={Users}     color="green"  loading={loading} />
        <StatCard label="Claims"   value={stats?.db.claims   ?? 0} icon={FileText}  color="purple" loading={loading} />
        <StatCard
          label="Jobs run"
          value={stats?.jobs.total ?? 0}
          sub={`${stats?.jobs.done ?? 0} completed`}
          icon={CheckCircle}
          color="orange"
          loading={loading}
        />
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button
            onClick={() => nav('/seed')}
            className="flex flex-col items-start gap-2 p-5 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 transition-colors text-left"
          >
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
              <Users size={18} className="text-white" />
            </div>
            <div>
              <p className="font-semibold text-slate-800">Seed Data</p>
              <p className="text-xs text-slate-500 mt-0.5">Generate SA patients, encounters &amp; claims at scale</p>
            </div>
          </button>

          <button
            onClick={() => nav('/tests')}
            className="flex flex-col items-start gap-2 p-5 rounded-xl border border-green-200 bg-green-50 hover:bg-green-100 transition-colors text-left"
          >
            <div className="w-9 h-9 rounded-lg bg-green-600 flex items-center justify-center">
              <CheckCircle size={18} className="text-white" />
            </div>
            <div>
              <p className="font-semibold text-slate-800">Run Tests</p>
              <p className="text-xs text-slate-500 mt-0.5">Execute RLS, tariff, chaos, and compliance suites</p>
            </div>
          </button>

          <button
            onClick={() => nav('/results')}
            className="flex flex-col items-start gap-2 p-5 rounded-xl border border-purple-200 bg-purple-50 hover:bg-purple-100 transition-colors text-left"
          >
            <div className="w-9 h-9 rounded-lg bg-purple-600 flex items-center justify-center">
              <FileText size={18} className="text-white" />
            </div>
            <div>
              <p className="font-semibold text-slate-800">View Results</p>
              <p className="text-xs text-slate-500 mt-0.5">Browse all job history and test outcomes</p>
            </div>
          </button>
        </div>
      </div>

      {/* Recent jobs */}
      <div>
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Recent Jobs</h2>
        {recent.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400 text-sm">
            No jobs yet — seed some data or run the tests to get started.
          </div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100 overflow-hidden">
            {recent.map((job) => {
              const summary = job.summary as Record<string, unknown> | undefined
              return (
                <div key={job.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    {job.type === 'seed' ? (
                      <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center">
                        <Users size={13} className="text-blue-600" />
                      </div>
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-green-100 flex items-center justify-center">
                        <CheckCircle size={13} className="text-green-600" />
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium text-slate-800 capitalize">{job.type} job</p>
                      {summary && (
                        <p className="text-xs text-slate-400">
                          {job.type === 'seed'
                            ? `${(summary.patients as number)?.toLocaleString() ?? '?'} patients inserted`
                            : `${summary.passed ?? '?'} passed · ${summary.failed ?? '?'} failed`}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock size={12} />
                      {new Date(job.started * 1000).toLocaleTimeString()}
                    </span>
                    <StatusBadge status={job.status} />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Error banner */}
      {stats?.error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <XCircle size={16} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Database unreachable</p>
            <p className="text-xs mt-0.5 text-red-600">{stats.error}</p>
            <p className="text-xs mt-1 text-red-500">Make sure Docker Compose is running: <code className="font-mono">docker compose up -d</code></p>
          </div>
        </div>
      )}
    </div>
  )
}

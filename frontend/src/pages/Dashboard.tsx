import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BookOpen, Shield, Box, ClipboardList,
  CheckCircle, XCircle, Clock, Activity,
  Wifi, WifiOff, Play, FileSearch,
} from 'lucide-react'
import { api, type Job } from '../api'
import StatusBadge from '../components/StatusBadge'

interface DashStats {
  totalJobs: number
  passed: number
  failed: number
  audits: number
  backendOnline: boolean
}

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number; icon: React.ElementType; color: string
}) {
  const colors: Record<string, string> = {
    blue:   'text-blue-400 bg-blue-500/10 border-blue-500/20',
    green:  'text-green-400 bg-green-500/10 border-green-500/20',
    red:    'text-red-400 bg-red-500/10 border-red-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  }
  return (
    <div className="glass p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${colors[color]}`}>
        <Icon size={18} />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value.toLocaleString()}</div>
        <div className="text-xs text-slate-500 mt-0.5">{label}</div>
      </div>
    </div>
  )
}

const JOB_TYPE_ICON: Record<string, React.ElementType> = {
  seed:    Activity,
  test:    Play,
  catalog: BookOpen,
  cyber:   Shield,
  sandbox: Box,
}

export default function Dashboard() {
  const nav = useNavigate()
  const [stats,   setStats]   = useState<DashStats>({ totalJobs: 0, passed: 0, failed: 0, audits: 0, backendOnline: false })
  const [jobs,    setJobs]    = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    try {
      const [s, j, h] = await Promise.all([api.stats(), api.jobs(), api.history()])
      const passed  = j.filter(x => x.status === 'done').length
      const failed  = j.filter(x => x.status === 'error').length
      setStats({
        totalJobs:     j.length,
        passed,
        failed,
        audits:        h.length,
        backendOnline: true,
      })
      setJobs(j)
    } catch {
      setStats(prev => ({ ...prev, backendOnline: false }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 6_000)
    return () => clearInterval(id)
  }, [])

  const recent = jobs.slice(0, 8)

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">Comprehensive software testing at a glance</p>
        </div>
        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${
          stats.backendOnline
            ? 'bg-green-500/10 border-green-500/30 text-green-400'
            : 'bg-red-500/10 border-red-500/30 text-red-400'
        }`}>
          {stats.backendOnline ? <Wifi size={13} /> : <WifiOff size={13} />}
          {stats.backendOnline ? 'Backend online' : 'Backend offline'}
        </div>
      </div>

      {/* Backend offline banner */}
      {!loading && !stats.backendOnline && (
        <div className="glass p-4 flex items-start gap-3 border-red-500/30">
          <XCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-red-300">Backend not connected</p>
            <p className="text-slate-400 text-xs mt-1">
              The frontend is live but needs a running backend to execute tests.
              Deploy the <code className="text-slate-300">backend/</code> folder to Railway or Render,
              then set <code className="text-slate-300">VITE_API_URL</code> in Netlify environment variables.
            </p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Jobs run"       value={stats.totalJobs} icon={Activity}     color="blue"   />
        <StatCard label="Completed"      value={stats.passed}    icon={CheckCircle}  color="green"  />
        <StatCard label="Errored"        value={stats.failed}    icon={XCircle}      color="red"    />
        <StatCard label="Audit reports"  value={stats.audits}    icon={FileSearch}   color="purple" />
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              path: '/catalog', icon: BookOpen, color: 'blue',
              title: 'Test Catalog',
              desc: 'Toggle from 120+ tests across 9 categories and get a formal audit report',
            },
            {
              path: '/cyber', icon: Shield, color: 'red',
              title: 'Cyber Mode',
              desc: '22 security categories — penetration, auth, injection, cryptography and more',
            },
            {
              path: '/sandbox', icon: Box, color: 'green',
              title: 'Sandbox',
              desc: '15 isolated test environments — functional, cloud, mobile, AI/ML, IoT and more',
            },
          ].map(({ path, icon: Icon, color, title, desc }) => (
            <button
              key={path}
              onClick={() => nav(path)}
              className={`glass-hover flex flex-col items-start gap-3 p-5 text-left transition-all ${
                color === 'red' ? 'hover:border-red-500/40' :
                color === 'green' ? 'hover:border-green-500/40' : 'hover:border-blue-500/40'
              }`}
            >
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                color === 'red'   ? 'bg-red-600/20 text-red-400' :
                color === 'green' ? 'bg-green-600/20 text-green-400' :
                                    'bg-blue-600/20 text-blue-400'
              }`}>
                <Icon size={18} />
              </div>
              <div>
                <p className="font-semibold text-slate-200 text-sm">{title}</p>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Recent jobs */}
      <div>
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Recent Jobs</h2>
        {recent.length === 0 ? (
          <div className="glass p-8 text-center text-slate-500 text-sm">
            No jobs yet — open the Test Catalog or Cyber Mode to run your first test.
          </div>
        ) : (
          <div className="glass divide-y" style={{ borderColor: 'var(--border)' }}>
            {recent.map((job) => {
              const summary = job.summary as Record<string, unknown> | undefined
              const Icon = JOB_TYPE_ICON[job.type] ?? Play
              return (
                <div key={job.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-slate-700/60 flex items-center justify-center">
                      <Icon size={13} className="text-slate-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-200 capitalize">{job.type} job</p>
                      {summary && (
                        <p className="text-xs text-slate-500">
                          {summary.score != null
                            ? `Score ${summary.score}/100 · Risk: ${summary.risk ?? 'N/A'}`
                            : `${summary.passed ?? '?'} passed · ${summary.failed ?? '?'} failed`}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-slate-600 flex items-center gap-1">
                      <Clock size={11} />
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
    </div>
  )
}

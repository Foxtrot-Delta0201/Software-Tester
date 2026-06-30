import { useState, useCallback } from 'react'
import { Database, Play, RotateCcw, Users, FileText, Stethoscope } from 'lucide-react'
import { api, openStream, type SeedParams, type LogEvent } from '../api'
import LogStream, { type LogLine } from '../components/LogStream'

const DEFAULT_PARAMS: SeedParams = {
  n_tenants: 5,
  n_patients_per_tenant: 1_000,
  include_encounters: true,
  include_claims: true,
  clear_existing: false,
}

export default function DataSeeder() {
  const [params,   setParams]   = useState<SeedParams>(DEFAULT_PARAMS)
  const [running,  setRunning]  = useState(false)
  const [logs,     setLogs]     = useState<LogLine[]>([])
  const [progress, setProgress] = useState<number | null>(null)
  const [done,     setDone]     = useState<LogEvent | null>(null)

  const total = params.n_tenants * params.n_patients_per_tenant

  const set = (k: keyof SeedParams, v: unknown) =>
    setParams(p => ({ ...p, [k]: v }))

  const handleRun = useCallback(async () => {
    setRunning(true)
    setLogs([])
    setProgress(null)
    setDone(null)

    const { job_id } = await api.startSeed(params)

    const stop = openStream(
      `/api/seed/${job_id}/stream`,
      (ev) => {
        if (ev.type === 'progress' && typeof ev.value === 'number') {
          setProgress(ev.value)
        } else if (ev.msg) {
          setLogs(prev => [...prev, { level: ev.level, msg: ev.msg }])
        }
        if (ev.done) {
          setDone(ev)
          setProgress(100)
        }
      },
      () => setRunning(false),
    )
    return stop
  }, [params])

  return (
    <div className="p-8 space-y-7 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Database size={22} className="text-blue-600" /> Data Seeder
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Generate realistic South African medical records at high throughput using an asyncpg connection pool.
        </p>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Config panel */}
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-5">
            <h2 className="font-semibold text-slate-700 text-sm">Seed Configuration</h2>

            {/* Tenants */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                <Building size={12} className="inline mr-1" />Practices / Tenants
              </label>
              <input
                type="number" min={1} max={50}
                value={params.n_tenants}
                onChange={e => set('n_tenants', parseInt(e.target.value) || 1)}
                disabled={running}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
            </div>

            {/* Patients per tenant */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                <Users size={12} className="inline mr-1" />Patients per practice
              </label>
              <input
                type="number" min={1} max={50_000}
                value={params.n_patients_per_tenant}
                onChange={e => set('n_patients_per_tenant', parseInt(e.target.value) || 1)}
                disabled={running}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
            </div>

            {/* Total preview */}
            <div className="rounded-lg bg-blue-50 border border-blue-100 px-4 py-3 text-center">
              <p className="text-xs text-slate-500">Total records to insert</p>
              <p className="text-2xl font-bold text-blue-700 mt-0.5">{total.toLocaleString()}</p>
              <p className="text-xs text-slate-400 mt-0.5">patients</p>
            </div>

            {/* Quick presets */}
            <div>
              <p className="text-xs font-medium text-slate-600 mb-2">Quick presets</p>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: '1K',   t: 2,  p: 500   },
                  { label: '5K',   t: 5,  p: 1_000 },
                  { label: '10K',  t: 5,  p: 2_000 },
                  { label: '50K',  t: 10, p: 5_000 },
                ].map(({ label, t, p }) => (
                  <button
                    key={label}
                    disabled={running}
                    onClick={() => setParams(prev => ({ ...prev, n_tenants: t, n_patients_per_tenant: p }))}
                    className="px-3 py-1 rounded-full text-xs border border-slate-300 hover:bg-slate-100 disabled:opacity-40 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Toggles */}
            <div className="space-y-3">
              {(
                [
                  { key: 'include_encounters', label: 'Include Encounters', icon: Stethoscope },
                  { key: 'include_claims',     label: 'Include Claims',     icon: FileText    },
                  { key: 'clear_existing',     label: 'Clear seed data first', icon: RotateCcw },
                ] as const
              ).map(({ key, label, icon: Icon }) => (
                <label key={key} className="flex items-center gap-3 cursor-pointer">
                  <div
                    onClick={() => !running && set(key, !params[key])}
                    className={`w-9 h-5 rounded-full transition-colors relative ${params[key] ? 'bg-blue-600' : 'bg-slate-300'} ${running ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${params[key] ? 'translate-x-4' : ''}`} />
                  </div>
                  <Icon size={13} className="text-slate-500" />
                  <span className="text-sm text-slate-700">{label}</span>
                </label>
              ))}
            </div>

            {/* Run button */}
            <button
              onClick={handleRun}
              disabled={running}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold rounded-lg px-4 py-3 transition-colors"
            >
              {running ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Seeding…
                </>
              ) : (
                <>
                  <Play size={16} />
                  Seed {total.toLocaleString()} records
                </>
              )}
            </button>
          </div>
        </div>

        {/* Log panel */}
        <div className="lg:col-span-3 space-y-4">
          {/* Progress bar */}
          {(running || progress !== null) && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-2">
              <div className="flex justify-between text-xs text-slate-500">
                <span>Seeding progress</span>
                <span>{progress ?? 0}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress ?? 0}%` }}
                />
              </div>
            </div>
          )}

          {/* Done summary */}
          {done?.stats && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-green-800 mb-2">Seeding complete</p>
              <div className="grid grid-cols-3 gap-3 text-center">
                {Object.entries(done.stats as Record<string, number>)
                  .filter(([k]) => k !== 'elapsed_s')
                  .map(([k, v]) => (
                    <div key={k} className="bg-white rounded-lg border border-green-100 py-2">
                      <p className="text-lg font-bold text-slate-800">{Number(v).toLocaleString()}</p>
                      <p className="text-xs text-slate-500 capitalize">{k}</p>
                    </div>
                  ))}
              </div>
              {!!done.stats.elapsed_s && (
                <p className="text-xs text-slate-400 mt-2 text-center">
                  Completed in {done.stats.elapsed_s as number}s
                </p>
              )}
            </div>
          )}

          <LogStream lines={logs} running={running} height="h-[480px]" />
        </div>
      </div>
    </div>
  )
}

// tiny icon component used inline above
function Building({ size, className }: { size: number; className?: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M3 9h18"/></svg>
}

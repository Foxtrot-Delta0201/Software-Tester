import { useState } from 'react'
import {
  Box, Play, RotateCcw, CheckSquare, Square,
  Loader2, Server, ChevronDown, ChevronRight, Zap,
} from 'lucide-react'
import { api, openStream, LogEvent, AuditReport as AuditReportType } from '../api'
import { SANDBOX_TYPES, SandboxType } from '../catalog'
import AuditReport from '../components/AuditReport'
import LogStream from '../components/LogStream'

// ── Sandbox card ───────────────────────────────────────────────────────────── //
function SandboxCard({
  sb, isActive, selected, onSelect, onToggleTest,
}: {
  sb: SandboxType
  isActive: boolean
  selected: Set<string>
  onSelect: () => void
  onToggleTest: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const selCount = sb.tests.filter(t => selected.has(t.id)).length

  return (
    <div
      className={`rounded-xl border transition-all overflow-hidden ${
        isActive
          ? 'border-green-500/60 glow-green cursor-default'
          : 'border-green-900/30 hover:border-green-700/40 cursor-pointer'
      }`}
      style={{ background: isActive ? 'rgba(0,30,10,0.7)' : 'rgba(5,15,10,0.5)' }}
    >
      <div className="flex items-center gap-3 px-4 py-3" onClick={isActive ? undefined : onSelect}>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          isActive ? 'bg-green-600/30' : 'bg-green-900/20'
        }`}>
          <Server size={16} className={isActive ? 'text-green-400' : 'text-green-700'} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-semibold ${isActive ? 'text-green-300' : 'text-green-100/60'}`}>
              {sb.name}
            </span>
            {isActive && (
              <span className="text-[10px] px-1.5 rounded bg-green-600/30 text-green-400 font-semibold pulse-dot">
                ACTIVE
              </span>
            )}
          </div>
          <div className="text-[11px] text-green-400/40 line-clamp-1">{sb.description}</div>
        </div>
        {!isActive && (
          <span className="text-[10px] text-green-700 border border-green-900/40 px-2 py-0.5 rounded">
            Activate
          </span>
        )}
        {isActive && <span className="text-xs text-green-400/50">{selCount}/{sb.tests.length}</span>}
      </div>

      {isActive && (
        <>
          <div
            className="flex items-center gap-2 px-4 py-2 border-t border-green-900/30 hover:bg-green-950/20 cursor-pointer"
            onClick={() => setOpen(o => !o)}
          >
            {open ? <ChevronDown size={12} className="text-green-400/40" /> : <ChevronRight size={12} className="text-green-400/40" />}
            <span className="text-xs text-green-400/60">
              {open ? 'Hide' : 'Show'} {sb.tests.length} tests
            </span>
            <div className="flex-1" />
            <button
              className="text-[10px] text-green-400/60 hover:text-green-300 underline"
              onClick={e => {
                e.stopPropagation()
                sb.tests.forEach(t => { if (!selected.has(t.id)) onToggleTest(t.id) })
              }}
            >
              Select All
            </button>
          </div>

          {open && (
            <div className="divide-y divide-green-900/20 border-t border-green-900/30">
              {sb.tests.map(t => (
                <label key={t.id}
                       className="flex items-start gap-3 px-4 py-2.5 cursor-pointer hover:bg-green-950/20 transition-colors">
                  <input
                    type="checkbox"
                    className="mt-0.5 accent-green-500"
                    checked={selected.has(t.id)}
                    onChange={() => onToggleTest(t.id)}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-green-200/80">{t.name}</div>
                    <div className="text-[11px] text-green-400/40 mt-0.5 line-clamp-1">{t.description}</div>
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                    t.severity === 'critical' ? 'risk-critical' :
                    t.severity === 'high'     ? 'risk-high'     :
                    t.severity === 'medium'   ? 'risk-medium'   : 'risk-low'
                  }`}>{t.severity}</span>
                </label>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────── //
export default function SandboxPage() {
  const [activeId,   setActiveId]   = useState<string | null>(null)
  const [selected,   setSelected]   = useState<Set<string>>(new Set())
  const [targetUrl,  setTargetUrl]  = useState('')
  const [projectDir, setProjectDir] = useState('')

  const [running,    setRunning]    = useState(false)
  const [logs,       setLogs]       = useState<LogEvent[]>([])
  const [progress,   setProgress]   = useState(0)
  const [report,     setReport]     = useState<AuditReportType | null>(null)
  const [error,      setError]      = useState<string | null>(null)
  const [envStatus,  setEnvStatus]  = useState<string>('idle')

  function toggleTest(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function activateSandbox(id: string) {
    setActiveId(id)
    setEnvStatus('ready')
    setSelected(new Set())
    setReport(null); setLogs([]); setProgress(0); setError(null)
  }

  async function runSandbox() {
    if (!activeId || selected.size === 0) return
    setError(null); setLogs([]); setReport(null); setProgress(0)
    setRunning(true); setEnvStatus('running')
    try {
      const res = await api.runSandbox({
        sandbox_id:  activeId,
        test_ids:    [...selected],
        target_url:  targetUrl  || undefined,
        project_dir: projectDir || undefined,
      })

      const close = openStream(`/api/sandbox/${res.job_id}/stream`, (ev) => {
        if (ev.ping) return
        setLogs(prev => [...prev, ev])
        if (ev.type === 'progress' && ev.value != null) setProgress(ev.value)
        if (ev.done) {
          close()
          setRunning(false); setEnvStatus('done')
          if (ev.audit_id) {
            api.getAudit(res.job_id)
               .then(r => setReport(r as unknown as AuditReportType))
               .catch(() => {})
          }
        }
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Backend not connected — deploy the backend and set VITE_API_URL to run tests.')
      setRunning(false); setEnvStatus('error')
    }
  }

  function reset() {
    setLogs([]); setReport(null); setProgress(0); setRunning(false)
    setSelected(new Set()); setError(null); setActiveId(null); setEnvStatus('idle')
  }

  const activeSb = SANDBOX_TYPES.find(s => s.id === activeId)

  const statusColor: Record<string, string> = {
    idle: 'text-slate-500', ready: 'text-green-400',
    running: 'text-yellow-400', done: 'text-green-300', error: 'text-red-400',
  }
  const statusLabel: Record<string, string> = {
    idle: 'No environment active', ready: 'Environment ready',
    running: 'Tests running…', done: 'Run complete', error: 'Error',
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl"
         style={{ background: 'linear-gradient(135deg, rgba(0,20,5,0.4) 0%, transparent 100%)' }}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-600/20 border border-green-500/30 flex items-center justify-center glow-green">
            <Box size={22} className="text-green-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-green-100 tracking-wide">SANDBOX</h1>
            <p className="text-xs text-green-400/60">
              {SANDBOX_TYPES.length} isolated environments · Click to activate, then select tests and run
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Zap size={13} className={`${statusColor[envStatus]} ${envStatus === 'running' ? 'pulse-dot' : ''}`} />
            <span className={`text-xs font-mono ${statusColor[envStatus]}`}>{statusLabel[envStatus]}</span>
          </div>
          <button onClick={reset}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
                             text-green-400/60 hover:text-green-300 border border-green-900/40
                             hover:border-green-700/40 transition-all">
            <RotateCcw size={12} /> Reset
          </button>
        </div>
      </div>

      {/* Run controls — shown when sandbox is active */}
      {activeId && (
        <div className="p-4 rounded-xl border border-green-900/30 space-y-3"
             style={{ background: 'rgba(0,30,10,0.5)' }}>
          <div className="flex items-center gap-2">
            <Server size={14} className="text-green-400" />
            <span className="text-sm font-semibold text-green-200">{activeSb?.name} — Configuration</span>
          </div>
          <div className="flex gap-3 flex-wrap">
            <div className="flex-1 min-w-48">
              <label className="text-xs text-green-400/60 mb-1 block">Target URL (optional)</label>
              <input
                value={targetUrl}
                onChange={e => setTargetUrl(e.target.value)}
                placeholder="http://localhost:3000"
                className="w-full rounded-lg px-3 py-2 text-sm text-green-100 placeholder-green-900
                           bg-green-950/30 border border-green-900/40 focus:outline-none focus:border-green-500"
              />
            </div>
            <div className="flex-1 min-w-48">
              <label className="text-xs text-green-400/60 mb-1 block">Project Directory (optional)</label>
              <input
                value={projectDir}
                onChange={e => setProjectDir(e.target.value)}
                placeholder="/path/to/project"
                className="w-full rounded-lg px-3 py-2 text-sm text-green-100 placeholder-green-900
                           bg-green-950/30 border border-green-900/40 focus:outline-none focus:border-green-500"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-green-400/50">{selected.size} tests selected</span>
            <button
              onClick={runSandbox}
              disabled={running || selected.size === 0}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold
                         bg-green-700 hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed
                         text-white transition-all glow-green"
            >
              {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {running ? 'Running…' : 'Run Sandbox Tests'}
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg text-sm text-red-400 border border-red-900/40 bg-red-950/30">{error}</div>
      )}

      {/* Progress */}
      {running && (
        <div>
          <div className="flex justify-between text-xs text-green-400/60 mb-1">
            <span>Sandbox tests running…</span><span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-green-950/60 overflow-hidden">
            <div className="h-full bg-green-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Log stream */}
      {logs.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-green-400/60 mb-2 uppercase tracking-wider">Live Output</h3>
          <LogStream events={logs} />
        </div>
      )}

      {/* Audit report */}
      {report && (
        <div>
          <h2 className="text-lg font-bold text-green-100 mb-4 flex items-center gap-2">
            <Box size={18} className="text-green-400" />
            Sandbox Audit Report
          </h2>
          <AuditReport report={report} />
        </div>
      )}

      {/* Sandbox grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {SANDBOX_TYPES.map(sb => (
          <SandboxCard
            key={sb.id}
            sb={sb}
            isActive={activeId === sb.id}
            selected={selected}
            onSelect={() => activateSandbox(sb.id)}
            onToggleTest={toggleTest}
          />
        ))}
      </div>
    </div>
  )
}

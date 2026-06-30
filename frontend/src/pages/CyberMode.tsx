import { useState, useMemo } from 'react'
import {
  Shield, Play, RotateCcw, ChevronDown, ChevronRight,
  CheckSquare, Square, Loader2, Target, Zap,
} from 'lucide-react'
import { api, openStream, LogEvent, AuditReport as AuditReportType } from '../api'
import { CYBER_CATEGORIES, CyberCategory } from '../catalog'
import AuditReport from '../components/AuditReport'
import LogStream from '../components/LogStream'

// ── Category accordion ─────────────────────────────────────────────────────── //
function CyberCategoryRow({
  cat, selected, onToggle,
}: {
  cat: CyberCategory
  selected: Set<string>
  onToggle: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const allSel  = cat.tests.every(t => selected.has(t.id))
  const someSel = !allSel && cat.tests.some(t => selected.has(t.id))
  const selCount = cat.tests.filter(t => selected.has(t.id)).length

  function toggleAll() {
    if (allSel) cat.tests.forEach(t => onToggle(t.id))
    else        cat.tests.filter(t => !selected.has(t.id)).forEach(t => onToggle(t.id))
  }

  return (
    <div className="overflow-hidden rounded-xl border border-red-900/30"
         style={{ background: 'rgba(20,6,6,0.6)' }}>
      <div className="flex items-center gap-3 px-4 py-3 hover:bg-red-950/20 cursor-pointer"
           onClick={() => setOpen(o => !o)}>
        <button className="shrink-0 text-red-400/60 hover:text-red-300"
                onClick={e => { e.stopPropagation(); toggleAll() }}>
          {allSel
            ? <CheckSquare size={16} className="text-red-400" />
            : someSel
              ? <CheckSquare size={16} className="text-red-300/50" />
              : <Square size={16} />}
        </button>
        <span className="flex-1 text-sm font-semibold text-red-100">{cat.name}</span>
        <span className="text-xs text-red-400/60">{selCount}/{cat.tests.length}</span>
        {open
          ? <ChevronDown  size={14} className="text-red-400/40" />
          : <ChevronRight size={14} className="text-red-400/40" />}
      </div>

      {open && (
        <div className="border-t border-red-900/30 divide-y divide-red-900/20">
          {cat.tests.map(t => (
            <label key={t.id}
                   className="flex items-start gap-3 px-4 py-2.5 cursor-pointer hover:bg-red-950/20 transition-colors">
              <input
                type="checkbox"
                className="mt-0.5 accent-red-500"
                checked={selected.has(t.id)}
                onChange={() => onToggle(t.id)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-red-100">{t.name}</span>
                  <span className="text-[10px] text-red-400/50 font-mono">{t.engine}</span>
                  {!t.automated && (
                    <span className="text-[10px] px-1.5 rounded bg-yellow-900/40 text-yellow-400">manual</span>
                  )}
                </div>
                <div className="text-[11px] text-red-300/40 mt-0.5 line-clamp-1">{t.description}</div>
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
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────── //
export default function CyberMode() {
  const [selected,   setSelected]   = useState<Set<string>>(new Set())
  const [targetUrl,  setTargetUrl]  = useState('http://localhost:3000')
  const [projectDir, setProjectDir] = useState('')

  const [running,    setRunning]    = useState(false)
  const [logs,       setLogs]       = useState<LogEvent[]>([])
  const [progress,   setProgress]   = useState(0)
  const [report,     setReport]     = useState<AuditReportType | null>(null)
  const [error,      setError]      = useState<string | null>(null)

  const totalTests = useMemo(() => CYBER_CATEGORIES.reduce((s, c) => s + c.tests.length, 0), [])
  const allIds     = useMemo(() => CYBER_CATEGORIES.flatMap(c => c.tests.map(t => t.id)), [])

  function toggleTest(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function selectAll()  { setSelected(new Set(allIds)) }
  function selectNone() { setSelected(new Set()) }

  async function runCyber() {
    if (selected.size === 0) return
    setError(null); setLogs([]); setReport(null); setProgress(0)
    setRunning(true)
    try {
      const res = await api.runCyber({
        test_ids:    [...selected],
        target_url:  targetUrl,
        project_dir: projectDir || undefined,
      })

      const close = openStream(`/api/cyber/${res.job_id}/stream`, (ev) => {
        if (ev.ping) return
        setLogs(prev => [...prev, ev])
        if (ev.type === 'progress' && ev.value != null) setProgress(ev.value)
        if (ev.done) {
          close()
          setRunning(false)
          if (ev.audit_id) {
            api.getAudit(res.job_id)
               .then(r => setReport(r as unknown as AuditReportType))
               .catch(() => {})
          }
        }
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Backend not connected — deploy the backend and set VITE_API_URL to run tests.')
      setRunning(false)
    }
  }

  function reset() {
    setLogs([]); setReport(null); setProgress(0); setRunning(false)
    setSelected(new Set()); setError(null)
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl"
         style={{ background: 'linear-gradient(135deg, rgba(20,0,0,0.4) 0%, transparent 100%)' }}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center glow-red">
            <Shield size={22} className="text-red-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-red-100 tracking-wide">CYBER MODE</h1>
            <p className="text-xs text-red-400/60">
              {CYBER_CATEGORIES.length} categories · {totalTests} tests · Advanced penetration & security testing
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-red-400 pulse-dot" />
          <span className="text-xs text-red-400/70 font-mono">SECURITY SUITE ACTIVE</span>
          <button onClick={reset}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
                             text-red-400/60 hover:text-red-300 border border-red-900/40
                             hover:border-red-700/40 transition-all">
            <RotateCcw size={12} /> Reset
          </button>
        </div>
      </div>

      {/* Target config */}
      <div className="p-4 rounded-xl border border-red-900/30 space-y-3"
           style={{ background: 'rgba(30,0,0,0.5)' }}>
        <div className="flex items-center gap-2">
          <Target size={14} className="text-red-400" />
          <span className="text-sm font-semibold text-red-200">Target Configuration</span>
        </div>
        <div className="flex gap-3 flex-wrap">
          <div className="flex-1 min-w-48">
            <label className="text-xs text-red-400/60 mb-1 block">Target URL</label>
            <input
              value={targetUrl}
              onChange={e => setTargetUrl(e.target.value)}
              placeholder="https://target.example.com"
              className="w-full rounded-lg px-3 py-2 text-sm text-red-100 placeholder-red-900
                         bg-red-950/30 border border-red-900/40 focus:outline-none focus:border-red-500"
            />
          </div>
          <div className="flex-1 min-w-48">
            <label className="text-xs text-red-400/60 mb-1 block">Project Directory (optional)</label>
            <input
              value={projectDir}
              onChange={e => setProjectDir(e.target.value)}
              placeholder="/path/to/project"
              className="w-full rounded-lg px-3 py-2 text-sm text-red-100 placeholder-red-900
                         bg-red-950/30 border border-red-900/40 focus:outline-none focus:border-red-500"
            />
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={selectAll}  className="text-xs text-red-400 hover:text-red-300 underline">Select All</button>
        <button onClick={selectNone} className="text-xs text-red-400/50 hover:text-red-300 underline">None</button>
        <span className="text-xs text-red-400/50">{selected.size} selected</span>
        <div className="flex-1" />
        <button
          onClick={runCyber}
          disabled={running || selected.size === 0}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold
                     bg-red-700 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed
                     text-white transition-all glow-red"
        >
          {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {running ? 'Running Cyber Tests…' : `Launch ${selected.size > 0 ? selected.size : ''} Tests`}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg text-sm text-red-400 border border-red-900/40 bg-red-950/30">{error}</div>
      )}

      {/* Progress */}
      {running && (
        <div>
          <div className="flex justify-between text-xs text-red-400/60 mb-1">
            <span>Executing cyber tests…</span><span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-red-950/60 overflow-hidden">
            <div className="h-full bg-red-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Log stream */}
      {logs.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-red-400/60 mb-2 uppercase tracking-wider">Live Output</h3>
          <LogStream events={logs} />
        </div>
      )}

      {/* Audit report */}
      {report && (
        <div>
          <h2 className="text-lg font-bold text-red-100 mb-4 flex items-center gap-2">
            <Shield size={18} className="text-red-400" />
            Cyber Security Audit Report
          </h2>
          <AuditReport report={report} />
        </div>
      )}

      {/* Category grid */}
      <div className="space-y-2">
        {CYBER_CATEGORIES.map(cat => (
          <CyberCategoryRow key={cat.id} cat={cat} selected={selected} onToggle={toggleTest} />
        ))}
      </div>
    </div>
  )
}

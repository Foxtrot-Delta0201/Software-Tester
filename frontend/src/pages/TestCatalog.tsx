import { useEffect, useState, useMemo } from 'react'
import {
  Search, Play, RotateCcw, ChevronDown, ChevronRight,
  CheckSquare, Square, Loader2, BookOpen,
} from 'lucide-react'
import { api, openStream, LogEvent, AuditReport as AuditReportType } from '../api'
import UploadZone from '../components/UploadZone'
import AuditReport from '../components/AuditReport'
import LogStream from '../components/LogStream'

// ── Types from catalog API ─────────────────────────────────────────────────── //
interface TestDef {
  id: string; name: string; group: string; category: string
  description: string; engine: string; automated: boolean; severity: string
  tags: string[]
}

interface CatalogData {
  groups: Record<string, TestDef[]>
}

// ── Group accordion ────────────────────────────────────────────────────────── //
function GroupSection({
  name, tests, selected, onToggle,
}: {
  name: string
  tests: TestDef[]
  selected: Set<string>
  onToggle: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const allSel  = tests.every(t => selected.has(t.id))
  const someSel = tests.some(t => selected.has(t.id))

  function toggleAll() {
    if (allSel) tests.forEach(t => onToggle(t.id))
    else        tests.filter(t => !selected.has(t.id)).forEach(t => onToggle(t.id))
  }

  return (
    <div className="glass overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 hover:bg-white/5 cursor-pointer"
           onClick={() => setOpen(o => !o)}>
        <button className="shrink-0 text-slate-400 hover:text-white"
                onClick={e => { e.stopPropagation(); toggleAll() }}>
          {allSel ? <CheckSquare size={16} className="text-blue-400" /> : someSel ? <CheckSquare size={16} className="text-blue-300/50" /> : <Square size={16} />}
        </button>
        <span className="flex-1 text-sm font-semibold text-slate-200">{name}</span>
        <span className="text-xs text-slate-500">{tests.filter(t => selected.has(t.id)).length}/{tests.length}</span>
        {open ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
      </div>

      {/* Tests */}
      {open && (
        <div className="border-t border-slate-700/40 divide-y divide-slate-700/20">
          {tests.map(t => (
            <label key={t.id}
                   className="flex items-start gap-3 px-4 py-2.5 cursor-pointer hover:bg-white/5 transition-colors">
              <input
                type="checkbox"
                className="mt-0.5 accent-blue-500"
                checked={selected.has(t.id)}
                onChange={() => onToggle(t.id)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-slate-200">{t.name}</span>
                  <span className="text-[10px] text-slate-600 font-mono">{t.engine}</span>
                  {!t.automated && (
                    <span className="text-[10px] px-1.5 py-0 rounded bg-yellow-900/40 text-yellow-400">manual</span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{t.description}</div>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                t.severity === 'CRITICAL' ? 'risk-critical' :
                t.severity === 'HIGH'     ? 'risk-high'     :
                t.severity === 'MEDIUM'   ? 'risk-medium'   : 'risk-low'
              }`}>{t.severity}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────── //
export default function TestCatalog() {
  const [catalog,     setCatalog]     = useState<CatalogData | null>(null)
  const [loading,     setLoading]     = useState(true)
  const [query,       setQuery]       = useState('')
  const [selected,    setSelected]    = useState<Set<string>>(new Set())
  const [projectDir,  setProjectDir]  = useState('')
  const [targetUrl,   setTargetUrl]   = useState('http://localhost:3000')

  const [running,     setRunning]     = useState(false)
  const [jobId,       setJobId]       = useState<string | null>(null)
  const [logs,        setLogs]        = useState<LogEvent[]>([])
  const [progress,    setProgress]    = useState(0)
  const [report,      setReport]      = useState<AuditReportType | null>(null)
  const [error,       setError]       = useState<string | null>(null)

  useEffect(() => {
    api.catalog()
       .then(d => setCatalog(d as CatalogData))
       .catch(() => setError('Failed to load catalog'))
       .finally(() => setLoading(false))
  }, [])

  const filteredGroups = useMemo(() => {
    if (!catalog) return {}
    const q = query.toLowerCase()
    if (!q) return catalog.groups
    const result: Record<string, TestDef[]> = {}
    for (const [group, tests] of Object.entries(catalog.groups)) {
      const filtered = tests.filter(t =>
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.engine.toLowerCase().includes(q) ||
        t.tags.some(tag => tag.toLowerCase().includes(q))
      )
      if (filtered.length) result[group] = filtered
    }
    return result
  }, [catalog, query])

  const allVisible = useMemo(() =>
    Object.values(filteredGroups).flat().map(t => t.id),
    [filteredGroups],
  )

  function toggleTest(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function selectAll()   { setSelected(new Set(allVisible)) }
  function selectNone()  { setSelected(new Set()) }

  async function runSelected() {
    if (selected.size === 0) return
    setError(null); setLogs([]); setReport(null); setProgress(0)
    setRunning(true)
    try {
      const res = await api.runCatalog({
        test_ids: [...selected],
        project_dir: projectDir || undefined,
        target_url: targetUrl || undefined,
      })
      setJobId(res.job_id)

      const close = openStream(`/api/catalog/${res.job_id}/stream`, (ev) => {
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
      setError(e instanceof Error ? e.message : 'Failed to start')
      setRunning(false)
    }
  }

  function reset() {
    setLogs([]); setReport(null); setProgress(0); setJobId(null)
    setRunning(false); setSelected(new Set()); setError(null)
  }

  const selectedCount = selected.size

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BookOpen size={20} className="text-blue-400" />
            Test Catalog
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">Toggle tests, upload your project, run and get a formal audit report.</p>
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400
                     hover:text-slate-200 hover:bg-white/5 transition-all border border-slate-700/50"
        >
          <RotateCcw size={14} /> Restart
        </button>
      </div>

      {/* Upload zone */}
      <UploadZone onUploaded={(dir) => setProjectDir(dir)} />

      {/* Config row */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex-1 min-w-48">
          <label className="text-xs text-slate-500 mb-1 block">Project Directory (override)</label>
          <input
            value={projectDir}
            onChange={e => setProjectDir(e.target.value)}
            placeholder="/path/to/project"
            className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2
                       text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex-1 min-w-48">
          <label className="text-xs text-slate-500 mb-1 block">Target URL</label>
          <input
            value={targetUrl}
            onChange={e => setTargetUrl(e.target.value)}
            placeholder="http://localhost:3000"
            className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-2
                       text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Search + select controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search tests…"
            className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg pl-8 pr-3 py-2
                       text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
          />
        </div>
        <button onClick={selectAll}  className="text-xs text-blue-400 hover:text-blue-300 underline">All</button>
        <button onClick={selectNone} className="text-xs text-slate-500 hover:text-slate-300 underline">None</button>
        <span className="text-xs text-slate-500">{selectedCount} selected</span>

        <button
          onClick={runSelected}
          disabled={running || selectedCount === 0}
          className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold
                     bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed
                     text-white transition-all glow-blue"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? 'Running…' : `Run ${selectedCount || ''} Tests`}
        </button>
      </div>

      {/* Error */}
      {error && <div className="glass p-3 text-sm text-red-400">{error}</div>}

      {/* Progress */}
      {running && (
        <div>
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Running tests…</span><span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
            <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Log stream */}
      {logs.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Live Output</h3>
          <LogStream events={logs} />
        </div>
      )}

      {/* Audit report */}
      {report && (
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Audit Report</h2>
          <AuditReport report={report} />
        </div>
      )}

      {/* Catalog grid */}
      {loading && (
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Loader2 size={16} className="animate-spin" /> Loading catalog…
        </div>
      )}

      {!loading && (
        <div className="space-y-3">
          {Object.entries(filteredGroups).map(([group, tests]) => (
            <GroupSection
              key={group}
              name={group}
              tests={tests}
              selected={selected}
              onToggle={toggleTest}
            />
          ))}
          {Object.keys(filteredGroups).length === 0 && (
            <div className="text-sm text-slate-500 text-center py-8">No tests match your search.</div>
          )}
        </div>
      )}
    </div>
  )
}

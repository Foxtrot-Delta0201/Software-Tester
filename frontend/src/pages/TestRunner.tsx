import { useState, useCallback } from 'react'
import { FlaskConical, Play, FolderOpen, CheckSquare, Square } from 'lucide-react'
import { api, openStream, type LogEvent } from '../api'
import LogStream, { type LogLine } from '../components/LogStream'
import StatusBadge from '../components/StatusBadge'

interface Suite {
  key:    string
  label:  string
  desc:   string
  group:  string
}

const SUITES: Suite[] = [
  { key: 'rls',             label: 'RLS Leak Detector',    desc: 'Cross-tenant data isolation',           group: 'Security' },
  { key: 'chaos',           label: 'Claims Chaos',         desc: 'Concurrent illegal state transitions',  group: 'Security' },
  { key: 'tariffs',         label: 'Temporal Tariffs',     desc: 'Historical SCD2 pricing correctness',   group: 'Financial' },
  { key: 'bulk_throughput', label: 'Bulk Throughput',      desc: '5 000 records, < 10 min',               group: 'Performance' },
  { key: 'functional',      label: 'Functional Suite',     desc: 'Unit, integration & boundary tests',    group: 'Functional' },
  { key: 'blackbox',        label: 'Black-box HTTP',       desc: 'HTTP contract / state-machine tests',   group: 'Functional' },
  { key: 'specialized',     label: 'AI / Drift Tests',     desc: 'Model bias and drift detection',        group: 'Specialised' },
  { key: 'security',        label: 'Bandit Scan',          desc: 'Static security analysis (OWASP)',      group: 'Security' },
  { key: 'performance',     label: 'Locust Load Test',     desc: 'Spike & soak HTTP performance',         group: 'Performance' },
  { key: 'all',             label: 'Full Orchestrator',    desc: 'All categories via foci_orchestrator',  group: 'Meta' },
]

const GROUPS = [...new Set(SUITES.map(s => s.group))]

type SuiteStatus = 'PASS' | 'FAIL' | 'SKIPPED' | 'running'

export default function TestRunner() {
  const [selected,    setSelected]    = useState<Set<string>>(new Set(['rls', 'tariffs', 'chaos']))
  const [projectDir,  setProjectDir]  = useState('')
  const [running,     setRunning]     = useState(false)
  const [logs,        setLogs]        = useState<LogLine[]>([])
  const [suiteStatus, setSuiteStatus] = useState<Record<string, SuiteStatus>>({})
  const [summary,     setSummary]     = useState<Record<string, unknown> | null>(null)

  const toggle = (key: string) =>
    setSelected(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })

  const toggleGroup = (group: string) => {
    const groupKeys = SUITES.filter(s => s.group === group).map(s => s.key)
    const allOn = groupKeys.every(k => selected.has(k))
    setSelected(prev => {
      const next = new Set(prev)
      groupKeys.forEach(k => allOn ? next.delete(k) : next.add(k))
      return next
    })
  }

  const handleRun = useCallback(async () => {
    if (selected.size === 0) return
    setRunning(true)
    setLogs([])
    setSuiteStatus({})
    setSummary(null)

    const suites = [...selected]
    const { job_id } = await api.startTests({
      suites,
      project_dir: projectDir || undefined,
    })

    let currentSuite = ''
    openStream(
      `/api/tests/${job_id}/stream`,
      (ev: LogEvent) => {
        if (ev.msg) {
          // Detect suite header lines "▶ Running suite: xxx"
          const m = ev.msg.match(/▶ Running suite: (\S+)/)
          if (m) {
            currentSuite = m[1]
            setSuiteStatus(prev => ({ ...prev, [currentSuite]: 'running' }))
          }
          // Detect suite result lines "◀ Suite [xxx]: PASS/FAIL"
          const r = ev.msg.match(/◀ Suite \[(\S+)\]: (PASS|FAIL|SKIPPED)/)
          if (r) {
            setSuiteStatus(prev => ({ ...prev, [r[1]]: r[2] as SuiteStatus }))
          }
          setLogs(prev => [...prev, { level: ev.level, msg: ev.msg }])
        }
        if (ev.done && ev.summary) {
          setSummary(ev.summary as Record<string, unknown>)
        }
      },
      () => setRunning(false),
    )
  }, [selected, projectDir])

  return (
    <div className="p-8 space-y-7 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <FlaskConical size={22} className="text-green-600" /> Test Runner
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Select suites, optionally override the project directory, then click Run.
          Output streams live below.
        </p>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Left: config */}
        <div className="lg:col-span-2 space-y-4">
          {/* Project dir */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-2">
            <label className="text-xs font-medium text-slate-600 flex items-center gap-1">
              <FolderOpen size={12} /> Project directory (optional)
            </label>
            <input
              type="text"
              value={projectDir}
              onChange={e => setProjectDir(e.target.value)}
              placeholder="Defaults to harness root"
              disabled={running}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            />
            <p className="text-xs text-slate-400">Leave blank to use the path set in Settings.</p>
          </div>

          {/* Suite selector */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-slate-600">Suites ({selected.size} selected)</p>
              <div className="flex gap-2">
                <button onClick={() => setSelected(new Set(SUITES.map(s => s.key)))} className="text-xs text-blue-600 hover:underline">All</button>
                <span className="text-slate-300">|</span>
                <button onClick={() => setSelected(new Set())} className="text-xs text-slate-500 hover:underline">None</button>
              </div>
            </div>

            {GROUPS.map(group => {
              const groupSuites = SUITES.filter(s => s.group === group)
              const allOn = groupSuites.every(s => selected.has(s.key))
              return (
                <div key={group}>
                  <button
                    onClick={() => toggleGroup(group)}
                    className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5 hover:text-slate-700"
                  >
                    {allOn ? <CheckSquare size={13} className="text-blue-500" /> : <Square size={13} />}
                    {group}
                  </button>
                  <div className="space-y-1 pl-4">
                    {groupSuites.map(suite => {
                      const on = selected.has(suite.key)
                      const st = suiteStatus[suite.key]
                      return (
                        <button
                          key={suite.key}
                          onClick={() => !running && toggle(suite.key)}
                          disabled={running}
                          className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-left transition-colors text-sm ${
                            on ? 'bg-green-50 border border-green-200' : 'hover:bg-slate-50 border border-transparent'
                          } disabled:cursor-default`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <div className={`w-3.5 h-3.5 rounded flex items-center justify-center shrink-0 ${on ? 'bg-green-600' : 'bg-slate-200'}`}>
                              {on && <span className="text-white text-[9px] font-bold">✓</span>}
                            </div>
                            <div className="min-w-0">
                              <p className="font-medium text-slate-800 truncate">{suite.label}</p>
                              <p className="text-xs text-slate-400 truncate">{suite.desc}</p>
                            </div>
                          </div>
                          {st && <StatusBadge status={st} />}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Run button */}
          <button
            onClick={handleRun}
            disabled={running || selected.size === 0}
            className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg px-4 py-3 transition-colors"
          >
            {running ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running {selected.size} suite{selected.size !== 1 ? 's' : ''}…
              </>
            ) : (
              <>
                <Play size={16} />
                Run {selected.size} suite{selected.size !== 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>

        {/* Right: log + summary */}
        <div className="lg:col-span-3 space-y-4">
          {/* Summary card */}
          {summary && (
            <div className={`rounded-xl border p-4 ${
              (summary.overall as string) === 'PASS'
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}>
              <p className={`font-semibold text-sm mb-3 ${
                (summary.overall as string) === 'PASS' ? 'text-green-800' : 'text-red-800'
              }`}>
                Overall: {summary.overall as string} — {summary.elapsed_s as number}s
              </p>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-white rounded-lg border border-green-100 py-2">
                  <p className="text-xl font-bold text-green-700">{summary.passed as number}</p>
                  <p className="text-xs text-slate-500">Passed</p>
                </div>
                <div className="bg-white rounded-lg border border-red-100 py-2">
                  <p className="text-xl font-bold text-red-600">{summary.failed as number}</p>
                  <p className="text-xs text-slate-500">Failed</p>
                </div>
                <div className="bg-white rounded-lg border border-slate-100 py-2">
                  <p className="text-xl font-bold text-slate-500">{summary.skipped as number}</p>
                  <p className="text-xs text-slate-500">Skipped</p>
                </div>
              </div>
            </div>
          )}

          <LogStream lines={logs} running={running} height="h-[540px]" />
        </div>
      </div>
    </div>
  )
}

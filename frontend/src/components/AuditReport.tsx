import { useState } from 'react'
import {
  ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2,
  ChevronDown, ChevronRight, Info, BookOpen,
} from 'lucide-react'
import { AuditReport as AuditReportType, CategoryScore, Finding } from '../api'

// ── Helpers ────────────────────────────────────────────────────────────────── //
function riskBadge(risk: string) {
  const cls =
    risk === 'CRITICAL' ? 'risk-critical' :
    risk === 'HIGH'     ? 'risk-high'     :
    risk === 'MEDIUM'   ? 'risk-medium'   : 'risk-low'
  return <span className={`text-xs px-2 py-0.5 rounded font-semibold ${cls}`}>{risk}</span>
}

function scoreColor(score: number) {
  if (score >= 85) return 'text-green-400'
  if (score >= 65) return 'text-yellow-400'
  if (score >= 40) return 'text-orange-400'
  return 'text-red-400'
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 85 ? 'bg-green-500' :
    score >= 65 ? 'bg-yellow-500' :
    score >= 40 ? 'bg-orange-500' : 'bg-red-500'
  return (
    <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden w-full">
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${score}%` }} />
    </div>
  )
}

function SeverityDot({ sev }: { sev: string }) {
  const cls =
    sev === 'CRITICAL' ? 'bg-red-500' :
    sev === 'HIGH'     ? 'bg-orange-500' :
    sev === 'MEDIUM'   ? 'bg-yellow-500' : 'bg-blue-500'
  return <span className={`inline-block w-2 h-2 rounded-full ${cls} shrink-0 mt-1`} />
}

// ── Category accordion ─────────────────────────────────────────────────────── //
function CategoryRow({ cat }: { cat: CategoryScore }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="glass overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        {open ? <ChevronDown size={14} className="text-slate-500 shrink-0" /> : <ChevronRight size={14} className="text-slate-500 shrink-0" />}
        <span className="flex-1 text-sm font-medium text-slate-200 truncate">{cat.name}</span>
        <div className="flex items-center gap-3">
          <div className="w-24 hidden sm:block">
            <ScoreBar score={cat.score} />
          </div>
          <span className={`text-sm font-bold w-10 text-right ${scoreColor(cat.score)}`}>{cat.score}</span>
          {riskBadge(cat.risk)}
          <div className="flex gap-2 text-xs text-slate-500 hidden md:flex">
            <span className="text-green-400">{cat.passed}✓</span>
            <span className="text-red-400">{cat.failed}✗</span>
          </div>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-700/50 divide-y divide-slate-700/30">
          {cat.tests.map(t => (
            <div key={t.id} className="px-4 py-3 flex items-start gap-3">
              <div className="mt-0.5 shrink-0">
                {t.status === 'PASS'    && <CheckCircle2 size={14} className="text-green-400" />}
                {t.status === 'FAIL'    && <ShieldAlert  size={14} className="text-red-400" />}
                {t.status === 'WARNING' && <AlertTriangle size={14} className="text-yellow-400" />}
                {t.status === 'MANUAL'  && <Info size={14} className="text-blue-400" />}
                {!['PASS','FAIL','WARNING','MANUAL'].includes(t.status) && <Info size={14} className="text-slate-500" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-300">{t.name}</span>
                  <span className="text-[10px] text-slate-600">{t.tool}</span>
                </div>
                {t.recommendations.slice(0, 1).map((r, i) => (
                  <div key={i} className="text-[11px] text-slate-500 mt-0.5 truncate">{r}</div>
                ))}
              </div>
              <span className={`text-xs font-bold ${scoreColor(t.score)}`}>{t.score}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Findings table ─────────────────────────────────────────────────────────── //
function FindingsTable({ findings, title }: { findings: Finding[]; title: string }) {
  const [show, setShow] = useState(10)
  if (findings.length === 0) return null
  return (
    <div>
      <h3 className="text-sm font-semibold text-white mb-3">{title}</h3>
      <div className="space-y-2">
        {findings.slice(0, show).map((f, i) => (
          <div key={i} className="glass p-3 flex gap-3 items-start">
            <SeverityDot sev={f.severity} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-semibold text-slate-200">{f.title}</span>
                <span className="text-[10px] text-slate-500">{f.test_name}</span>
              </div>
              {f.location && <div className="text-[11px] text-slate-500 truncate mt-0.5">{f.location}</div>}
              {f.evidence  && <div className="text-[11px] text-slate-400 mt-0.5 font-mono">{f.evidence.slice(0, 120)}</div>}
            </div>
            <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
              f.severity === 'CRITICAL' ? 'risk-critical' :
              f.severity === 'HIGH'     ? 'risk-high'     :
              f.severity === 'MEDIUM'   ? 'risk-medium'   : 'risk-low'
            }`}>{f.severity}</span>
          </div>
        ))}
        {findings.length > show && (
          <button className="text-xs text-slate-500 hover:text-slate-300 underline"
                  onClick={() => setShow(s => s + 20)}>
            Show {Math.min(20, findings.length - show)} more…
          </button>
        )}
      </div>
    </div>
  )
}

// ── Main report component ──────────────────────────────────────────────────── //
interface Props {
  report: AuditReportType
}

export default function AuditReport({ report }: Props) {
  const ovColor = scoreColor(report.overall_score)

  return (
    <div className="space-y-6">
      {/* Executive summary */}
      <div className="glass p-5">
        <div className="flex items-start gap-4">
          <div className="shrink-0">
            {report.risk_level === 'CRITICAL' || report.risk_level === 'HIGH'
              ? <ShieldAlert size={36} className="text-red-400" />
              : <ShieldCheck  size={36} className="text-green-400" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-2">
              <span className={`text-4xl font-black ${ovColor}`}>{report.overall_score}</span>
              <span className="text-slate-400 text-sm">/100</span>
              {riskBadge(report.risk_level)}
              <span className="text-xs text-slate-500">
                {new Date(report.generated_at).toLocaleString()}
              </span>
              {report.mode !== 'standard' && (
                <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                  report.mode === 'cyber'   ? 'bg-red-900/50 text-red-300' :
                  report.mode === 'sandbox' ? 'bg-green-900/50 text-green-300' : ''
                }`}>{report.mode.toUpperCase()}</span>
              )}
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{report.executive_summary}</p>
          </div>
        </div>
      </div>

      {/* Counts grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: 'Total',   value: report.total,   color: 'text-slate-300' },
          { label: 'Passed',  value: report.passed,  color: 'text-green-400' },
          { label: 'Failed',  value: report.failed,  color: 'text-red-400'   },
          { label: 'Warning', value: report.warned,  color: 'text-yellow-400'},
          { label: 'Manual',  value: report.manual,  color: 'text-blue-400'  },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass p-3 text-center">
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Category breakdown */}
      {report.categories.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <BookOpen size={14} className="text-slate-400" />
            Category Breakdown
          </h3>
          <div className="space-y-2">
            {report.categories.map(cat => (
              <CategoryRow key={cat.name} cat={cat} />
            ))}
          </div>
        </div>
      )}

      {/* Critical + high findings */}
      <FindingsTable findings={report.critical_findings} title="Critical & High Findings" />

      {/* OWASP coverage */}
      {Object.keys(report.owasp_coverage).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-3">OWASP Top 10 Coverage</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(report.owasp_coverage).map(([owasp, data]) => (
              <div key={owasp} className="glass p-3 flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full shrink-0 ${
                  data.status === 'COVERED' ? 'bg-green-500' : 'bg-slate-600'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-slate-300 truncate">{owasp}</div>
                  <div className="text-[10px] text-slate-500">
                    {data.covered}/{data.total_map} tests covered · {data.passed} passed
                  </div>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  data.status === 'COVERED' ? 'bg-green-900/50 text-green-300' : 'bg-slate-700 text-slate-500'
                }`}>{data.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-3">Recommendations</h3>
          <div className="glass p-4 space-y-2">
            {report.recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="text-slate-600 shrink-0 text-xs mt-0.5">{i + 1}.</span>
                {rec}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

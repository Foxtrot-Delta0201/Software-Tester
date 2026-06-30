import { useEffect, useState } from 'react'
import { X, Trophy, AlertTriangle, ShieldAlert, CheckCircle } from 'lucide-react'
import { api, AuditHistory } from '../api'

interface Props {
  onClose: () => void
}

function riskIcon(risk?: string) {
  switch (risk) {
    case 'CRITICAL': return <ShieldAlert size={14} className="text-red-400" />
    case 'HIGH':     return <AlertTriangle size={14} className="text-orange-400" />
    case 'MEDIUM':   return <AlertTriangle size={14} className="text-yellow-400" />
    default:         return <CheckCircle size={14} className="text-green-400" />
  }
}

function riskClass(risk?: string) {
  if (risk === 'CRITICAL') return 'risk-critical'
  if (risk === 'HIGH')     return 'risk-high'
  if (risk === 'MEDIUM')   return 'risk-medium'
  return 'risk-low'
}

function modeTag(mode?: string) {
  if (mode === 'cyber')   return <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-900/50 text-red-300">CYBER</span>
  if (mode === 'sandbox') return <span className="px-1.5 py-0.5 rounded text-[10px] bg-green-900/50 text-green-300">SANDBOX</span>
  return <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-900/50 text-blue-300">STANDARD</span>
}

export default function ResultsSidebar({ onClose }: Props) {
  const [items,   setItems]   = useState<AuditHistory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.history()
       .then(setItems)
       .catch(() => setItems([]))
       .finally(() => setLoading(false))
  }, [])

  return (
    <div className="w-80 flex flex-col border-r shrink-0"
         style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b"
           style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <Trophy size={16} className="text-yellow-400" />
          <span className="text-sm font-semibold text-white">Audit History</span>
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
          <X size={16} />
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2">
        {loading && (
          <div className="text-xs text-slate-500 text-center py-8">Loading history…</div>
        )}
        {!loading && items.length === 0 && (
          <div className="text-xs text-slate-500 text-center py-8">No audits yet.</div>
        )}
        {items.map(item => (
          <div key={item.job_id} className="glass p-3 space-y-2">
            {/* Top row */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-1.5 min-w-0">
                {riskIcon(item.risk_level)}
                <span className={`text-[11px] px-1.5 py-0.5 rounded font-semibold ${riskClass(item.risk_level)}`}>
                  {item.risk_level ?? 'N/A'}
                </span>
                {modeTag(item.mode)}
              </div>
              <span className="text-[10px] text-slate-500 shrink-0">
                {item.overall_score != null ? `${item.overall_score}/100` : '—'}
              </span>
            </div>

            {/* Target */}
            <div className="text-[11px] text-slate-300 truncate" title={item.target}>
              {item.target ?? 'unknown target'}
            </div>

            {/* Stats */}
            <div className="flex gap-3 text-[10px] text-slate-500">
              <span className="text-green-400">{item.passed ?? 0} pass</span>
              <span className="text-red-400">{item.failed ?? 0} fail</span>
              <span>{item.total ?? 0} total</span>
            </div>

            {/* Date */}
            <div className="text-[10px] text-slate-600">
              {item.generated_at ? new Date(item.generated_at).toLocaleString() : ''}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

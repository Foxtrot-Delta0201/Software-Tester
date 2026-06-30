type Status = 'running' | 'done' | 'error' | 'PASS' | 'FAIL' | 'SKIPPED' | string

const MAP: Record<string, string> = {
  running: 'bg-blue-100 text-blue-700 border border-blue-200',
  done:    'bg-green-100 text-green-700 border border-green-200',
  error:   'bg-red-100 text-red-700 border border-red-200',
  PASS:    'bg-green-100 text-green-700 border border-green-200',
  FAIL:    'bg-red-100 text-red-700 border border-red-200',
  SKIPPED: 'bg-slate-100 text-slate-500 border border-slate-200',
}

const DOTS: Record<string, string> = {
  running: 'bg-blue-500 animate-pulse',
  done:    'bg-green-500',
  error:   'bg-red-500',
  PASS:    'bg-green-500',
  FAIL:    'bg-red-500',
  SKIPPED: 'bg-slate-400',
}

export default function StatusBadge({ status }: { status: Status }) {
  const cls  = MAP[status]  ?? 'bg-slate-100 text-slate-500 border border-slate-200'
  const dot  = DOTS[status] ?? 'bg-slate-400'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {status}
    </span>
  )
}

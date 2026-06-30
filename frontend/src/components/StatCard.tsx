import type { LucideIcon } from 'lucide-react'

interface Props {
  label:    string
  value:    string | number
  sub?:     string
  icon:     LucideIcon
  color?:   'blue' | 'green' | 'purple' | 'orange' | 'red'
  loading?: boolean
}

const COLORS = {
  blue:   'bg-blue-50   text-blue-600   border-blue-100',
  green:  'bg-green-50  text-green-600  border-green-100',
  purple: 'bg-purple-50 text-purple-600 border-purple-100',
  orange: 'bg-orange-50 text-orange-600 border-orange-100',
  red:    'bg-red-50    text-red-600    border-red-100',
}

const ICON_COLORS = {
  blue:   'bg-blue-100   text-blue-600',
  green:  'bg-green-100  text-green-600',
  purple: 'bg-purple-100 text-purple-600',
  orange: 'bg-orange-100 text-orange-600',
  red:    'bg-red-100    text-red-600',
}

export default function StatCard({
  label, value, sub, icon: Icon,
  color = 'blue', loading = false,
}: Props) {
  return (
    <div className={`rounded-xl border p-5 ${COLORS[color]} flex items-start gap-4`}>
      <div className={`rounded-lg p-2.5 ${ICON_COLORS[color]}`}>
        <Icon size={20} />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
        {loading ? (
          <div className="h-7 w-20 bg-slate-200 rounded animate-pulse mt-1" />
        ) : (
          <p className="text-2xl font-bold text-slate-800 mt-0.5">{value.toLocaleString()}</p>
        )}
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

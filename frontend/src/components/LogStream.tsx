import { useEffect, useRef } from 'react'
import { LogEvent } from '../api'

// Kept for backward-compat with existing pages that pass `lines`
export interface LogLine {
  level?: string
  msg?: string
}

const LINE_COLOR: Record<string, string> = {
  error:     'log-error',
  warning:   'log-warning',
  success:   'log-success',
  info:      'log-info',
  header:    'text-blue-300 font-semibold',
  separator: 'text-slate-600',
  progress:  'text-cyan-400',
  log:       'log-default',
}

interface Props {
  lines?:   LogLine[]    // legacy prop
  events?:  LogEvent[]   // preferred
  running?: boolean
  height?:  string
}

export default function LogStream({ lines, events, running = false, height = 'h-80' }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const entries: LogLine[] = events ?? lines ?? []

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries.length])

  return (
    <div
      className={`${height} rounded-xl border overflow-y-auto scrollbar-thin font-mono text-xs p-4`}
      style={{ background: '#050a18', borderColor: 'var(--border)' }}
    >
      {entries.length === 0 && (
        <p className="text-slate-700 italic">Waiting for output…</p>
      )}
      {entries.map((line, i) => {
        if ('ping' in line && (line as LogEvent).ping) return null
        const color = LINE_COLOR[(line.level ?? 'log').toLowerCase()] ?? 'log-default'
        return (
          <div key={i} className={`leading-relaxed whitespace-pre-wrap break-all ${color}`}>
            {(line as LogEvent).msg ?? ''}
          </div>
        )
      })}
      {running && (
        <div className="flex items-center gap-1.5 mt-1 text-slate-600">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 pulse-dot" />
          <span>Running…</span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

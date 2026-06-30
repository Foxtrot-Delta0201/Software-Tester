import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Database, FlaskConical, BookOpen,
  ClipboardList, Settings, Activity, Shield, Box,
  RotateCcw, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { api } from '../api'
import ResultsSidebar from './ResultsSidebar'

const NAV_MAIN = [
  { to: '/',        icon: LayoutDashboard, label: 'Dashboard'   },
  { to: '/seed',    icon: Database,        label: 'Data Seeder' },
  { to: '/tests',   icon: FlaskConical,    label: 'Test Runner' },
  { to: '/catalog', icon: BookOpen,        label: 'Test Catalog'},
  { to: '/results', icon: ClipboardList,   label: 'History'     },
  { to: '/settings',icon: Settings,        label: 'Settings'    },
]

export default function Sidebar() {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [resetting,   setResetting]   = useState(false)

  async function handleReset() {
    if (!confirm('Reset all jobs and audit history?')) return
    setResetting(true)
    try { await api.reset() } finally { setResetting(false) }
  }

  return (
    <>
      <aside className="w-60 flex flex-col shrink-0 border-r"
             style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
        {/* Logo */}
        <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <Activity className="text-blue-400" size={20} />
            <div>
              <div className="font-bold text-sm text-white tracking-wide">Software Tester</div>
              <div className="text-xs text-slate-400">QA Platform</div>
            </div>
          </div>
        </div>

        {/* Main nav */}
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto scrollbar-thin">
          {NAV_MAIN.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600/90 text-white glow-blue'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-white/5'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}

          {/* Divider */}
          <div className="my-3 border-t" style={{ borderColor: 'var(--border)' }} />

          {/* Cyber Mode */}
          <NavLink
            to="/cyber"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-bold transition-all ${
                isActive
                  ? 'bg-red-600/80 text-white glow-red'
                  : 'text-red-400 hover:text-red-300 hover:bg-red-900/20'
              }`
            }
          >
            <Shield size={16} />
            Cyber Mode
          </NavLink>

          {/* Sandbox */}
          <NavLink
            to="/sandbox"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-bold transition-all ${
                isActive
                  ? 'bg-green-600/80 text-white glow-green'
                  : 'text-green-400 hover:text-green-300 hover:bg-green-900/20'
              }`
            }
          >
            <Box size={16} />
            Sandbox
          </NavLink>
        </nav>

        {/* Bottom actions */}
        <div className="px-2 pb-3 space-y-1 border-t pt-3" style={{ borderColor: 'var(--border)' }}>
          {/* History toggle */}
          <button
            onClick={() => setHistoryOpen(o => !o)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400
                       hover:text-slate-100 hover:bg-white/5 transition-all"
          >
            <ClipboardList size={16} />
            <span className="flex-1 text-left">Audit History</span>
            {historyOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </button>

          {/* Reset */}
          <button
            onClick={handleReset}
            disabled={resetting}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-500
                       hover:text-slate-300 hover:bg-white/5 transition-all"
          >
            <RotateCcw size={16} className={resetting ? 'animate-spin' : ''} />
            {resetting ? 'Resetting…' : 'Reset Session'}
          </button>
        </div>

        <div className="px-5 py-3 border-t text-xs text-slate-600"
             style={{ borderColor: 'var(--border)' }}>
          v2.0.0 · Software Tester
        </div>
      </aside>

      {/* Slide-out history panel */}
      {historyOpen && (
        <ResultsSidebar onClose={() => setHistoryOpen(false)} />
      )}
    </>
  )
}

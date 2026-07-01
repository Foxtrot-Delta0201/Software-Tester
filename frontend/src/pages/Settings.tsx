import { useEffect, useState } from 'react'
import { Settings as SettingsIcon, Save, FolderOpen, Database } from 'lucide-react'
import { api, type Config } from '../api'

export default function Settings() {
  const [cfg,     setCfg]     = useState<Partial<Config & { db_password: string }>>({})
  const [loading, setLoading] = useState(true)
  const [saved,   setSaved]   = useState(false)
  const [error,   setError]   = useState('')

  useEffect(() => {
    api.getConfig().then(c => { setCfg(c); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const set = (k: string, v: string | number) => setCfg(p => ({ ...p, [k]: v }))

  const handleSave = async () => {
    try {
      setError('')
      await api.updateConfig(cfg as Parameters<typeof api.updateConfig>[0])
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e: unknown) {
      setError((e as Error).message)
    }
  }

  if (loading) return (
    <div className="p-8 flex items-center justify-center h-64 text-slate-400 text-sm">Loading…</div>
  )

  return (
    <div className="p-8 space-y-7 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <SettingsIcon size={22} className="text-slate-400" /> Settings
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Configure the database connection and default project directory.
          Changes apply immediately to the running backend.
        </p>
      </div>

      {/* Project directory */}
      <div className="glass p-5 space-y-4">
        <h2 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
          <FolderOpen size={15} /> Project Directory
        </h2>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Path to project folder</label>
          <input
            type="text"
            value={cfg.project_dir ?? ''}
            onChange={e => set('project_dir', e.target.value)}
            placeholder="/path/to/project"
            className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 text-slate-200 px-3 py-2 text-sm font-mono focus:outline-none focus:border-blue-500 placeholder-slate-600"
          />
          <p className="text-xs text-slate-500 mt-1">
            The test runner uses this path to discover test suites.
            On Windows use backslashes or forward slashes.
          </p>
        </div>
      </div>

      {/* Database */}
      <div className="glass p-5 space-y-4">
        <h2 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
          <Database size={15} /> Database Connection
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Host"     value={cfg.db_host ?? ''} onChange={v => set('db_host', v)} mono />
          <Field label="Port"     value={String(cfg.db_port ?? 5432)} onChange={v => set('db_port', parseInt(v))} mono />
          <Field label="Database" value={cfg.db_name ?? ''} onChange={v => set('db_name', v)} mono />
          <Field label="User"     value={cfg.db_user ?? ''} onChange={v => set('db_user', v)} mono />
          <Field label="Password (write-only)" value={cfg.db_password ?? ''} onChange={v => set('db_password', v)} mono password />
          <Field label="App user" value={cfg.app_user ?? ''} onChange={v => set('app_user', v)} mono />
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg px-5 py-2.5 text-sm transition-colors"
        >
          <Save size={15} />
          Save settings
        </button>
        {saved && <span className="text-sm text-green-400 font-medium">Saved ✓</span>}
        {error && <span className="text-sm text-red-400">{error}</span>}
      </div>

      {/* Deployment note */}
      <div className="glass border-amber-700/30 p-4 text-sm text-amber-300 space-y-1">
        <p className="font-semibold">Deploying?</p>
        <p>The backend must run separately (Railway, Render, Fly.io, or locally via ngrok).<br />
          Set <code className="font-mono text-xs bg-amber-900/30 px-1 rounded">VITE_API_URL</code> in your Netlify environment variables to point to your backend URL.
        </p>
      </div>
    </div>
  )
}

function Field({
  label, value, onChange, mono = false, password = false,
}: {
  label: string; value: string; onChange: (v: string) => void;
  mono?: boolean; password?: boolean
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1">{label}</label>
      <input
        type={password ? 'password' : 'text'}
        value={value}
        onChange={e => onChange(e.target.value)}
        className={`w-full rounded-lg bg-slate-800/60 border border-slate-700/50 text-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-blue-500 placeholder-slate-600 ${mono ? 'font-mono' : ''}`}
      />
    </div>
  )
}

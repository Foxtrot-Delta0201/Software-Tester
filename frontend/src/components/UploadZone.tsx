import { useState, useRef, DragEvent } from 'react'
import { UploadCloud, FolderOpen, CheckCircle, Loader2, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react'
import { api } from '../api'

interface Props {
  projectDir: string
  onProjectDir: (dir: string) => void
  onUploaded: (projectDir: string, fileCount: number) => void
}

export default function UploadZone({ projectDir, onProjectDir, onUploaded }: Props) {
  const [uploadOpen,  setUploadOpen]  = useState(false)
  const [dragging,    setDragging]    = useState(false)
  const [uploading,   setUploading]   = useState(false)
  const [uploaded,    setUploaded]    = useState<{ dir: string; count: number } | null>(null)
  const [error,       setError]       = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    if (files.length > 2000) {
      setError(`Too many files (${files.length.toLocaleString()}). For large projects use the path input above instead.`)
      return
    }
    setError(null)
    setUploading(true)
    try {
      const res = await api.uploadProject(files)
      setUploaded({ dir: res.project_dir, count: res.files_saved })
      onUploaded(res.project_dir, res.files_saved)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="glass space-y-4 p-4">
      {/* ── Primary: path input ──────────────────────────────────────────── */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
          Project Path
          <span className="ml-2 text-[10px] normal-case font-normal text-green-400 px-1.5 py-0.5 rounded bg-green-900/30">
            Works for any size project
          </span>
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <FolderOpen size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={projectDir}
              onChange={e => onProjectDir(e.target.value)}
              placeholder="C:\Users\you\my-project  or  /home/user/my-project"
              className="w-full bg-slate-800/60 border border-slate-700/50 rounded-lg pl-9 pr-3 py-2.5
                         text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
        <p className="text-[11px] text-slate-600 mt-1.5">
          Enter the full path to your project folder on the machine running the backend. Supports any number of files.
        </p>
      </div>

      {/* ── Divider ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-slate-700/40" />
        <span className="text-[10px] text-slate-600 uppercase tracking-wider">or for small projects (&lt;2000 files)</span>
        <div className="flex-1 h-px bg-slate-700/40" />
      </div>

      {/* ── Secondary: file upload ────────────────────────────────────────── */}
      <div>
        <button
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          onClick={() => setUploadOpen(o => !o)}
        >
          {uploadOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          Upload folder from browser
        </button>

        {uploadOpen && (
          <div className="mt-3">
            {uploaded ? (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-green-900/20 border border-green-700/30">
                <CheckCircle className="text-green-400 mt-0.5 shrink-0" size={16} />
                <div>
                  <div className="text-xs font-semibold text-green-400">{uploaded.count.toLocaleString()} files uploaded</div>
                  <div className="text-[11px] text-slate-400 mt-0.5 break-all">{uploaded.dir}</div>
                  <button className="mt-1.5 text-[11px] text-slate-500 hover:text-slate-300 underline"
                          onClick={() => { setUploaded(null); onUploaded('', 0) }}>
                    Upload different folder
                  </button>
                </div>
              </div>
            ) : (
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                className={`cursor-pointer rounded-lg border-2 border-dashed p-6 flex flex-col items-center gap-2
                  transition-all ${dragging
                    ? 'border-blue-400 bg-blue-500/5'
                    : 'border-slate-700/60 hover:border-slate-500 hover:bg-white/3'}`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  // @ts-expect-error — non-standard but widely supported
                  webkitdirectory="true"
                  multiple
                  className="hidden"
                  onChange={e => handleFiles(e.target.files)}
                />
                {uploading
                  ? <Loader2 className="animate-spin text-blue-400" size={24} />
                  : <UploadCloud className={dragging ? 'text-blue-400' : 'text-slate-600'} size={24} />}
                <span className="text-xs text-slate-400">
                  {uploading ? 'Uploading…' : 'Drop folder or click to browse'}
                </span>
                <div className="flex items-center gap-1.5 text-[11px] text-yellow-500/70">
                  <AlertTriangle size={11} />
                  <span>Max ~2,000 files. For larger projects use the path input above.</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs text-yellow-400 bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-3">
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          {error}
        </div>
      )}
    </div>
  )
}

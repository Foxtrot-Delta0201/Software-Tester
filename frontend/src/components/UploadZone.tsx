import { useState, useRef, DragEvent } from 'react'
import { UploadCloud, FolderOpen, CheckCircle, Loader2 } from 'lucide-react'
import { api } from '../api'

interface Props {
  onUploaded: (projectDir: string, fileCount: number) => void
}

export default function UploadZone({ onUploaded }: Props) {
  const [dragging,   setDragging]   = useState(false)
  const [uploading,  setUploading]  = useState(false)
  const [uploaded,   setUploaded]   = useState<{ dir: string; count: number } | null>(null)
  const [error,      setError]      = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
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
    // Try dataTransfer.items first to get folder structure
    const files = e.dataTransfer.files
    handleFiles(files)
  }

  if (uploaded) {
    return (
      <div className="glass p-4 flex items-start gap-3">
        <CheckCircle className="text-green-400 mt-0.5 shrink-0" size={18} />
        <div>
          <div className="text-sm font-semibold text-green-400">Project uploaded</div>
          <div className="text-xs text-slate-400 mt-0.5">{uploaded.count} files · {uploaded.dir}</div>
          <button
            className="mt-2 text-xs text-slate-500 hover:text-slate-300 underline"
            onClick={() => { setUploaded(null); onUploaded('', 0) }}
          >
            Upload different folder
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`relative glass cursor-pointer transition-all p-6 flex flex-col items-center gap-3
        ${dragging ? 'border-blue-400 glow-blue' : 'hover:border-slate-500'}`}
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

      {uploading ? (
        <Loader2 className="animate-spin text-blue-400" size={32} />
      ) : (
        <UploadCloud className={dragging ? 'text-blue-400' : 'text-slate-500'} size={32} />
      )}

      <div className="text-center">
        <div className="text-sm font-semibold text-slate-300">
          {uploading ? 'Uploading…' : dragging ? 'Drop folder here' : 'Upload Project Folder'}
        </div>
        <div className="text-xs text-slate-500 mt-1">
          Drag & drop a folder or click to browse
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <FolderOpen size={12} />
        <span>All file types accepted</span>
      </div>

      {error && <div className="text-xs text-red-400">{error}</div>}
    </div>
  )
}

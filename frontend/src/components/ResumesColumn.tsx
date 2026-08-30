import { useRef, useState } from 'react'
import { CheckCircle2, FileText, Loader2, Trash2, Upload } from 'lucide-react'
import api from '@/api/client'
import { formatDate, getErrorMessage } from '@/lib/helpers'
import type { Resume } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { ColumnCard, EmptyState } from '@/components/ColumnCard'

export function ResumesColumn({
  resumes,
  setResumes,
}: {
  resumes: Resume[]
  setResumes: React.Dispatch<React.SetStateAction<Resume[]>>
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  function flashSuccess(msg: string) {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 3000)
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post<Resume>('/resumes/upload', formData)
      setResumes((prev) => [data, ...prev])
      flashSuccess('Resume uploaded successfully.')
    } catch (err) {
      setError(getErrorMessage(err, 'Upload failed. Please try again.'))
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function handleDelete(id: Resume['id']) {
    setError('')
    const prev = resumes
    setResumes((list) => list.filter((r) => r.id !== id))
    try {
      await api.delete(`/resumes/${id}`)
    } catch (err) {
      setResumes(prev)
      setError(getErrorMessage(err, 'Could not delete resume.'))
    }
  }

  return (
    <ColumnCard title="My Resumes" count={resumes.length} icon={<FileText className="size-4" />}>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={handleFile}
      />
      <Button
        className="w-full"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
      >
        {uploading ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
        {uploading ? 'Uploading...' : 'Upload Resume'}
      </Button>

      {success && (
        <div className="flex items-center gap-2 rounded-lg bg-success/15 px-3 py-2 text-sm text-success">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {resumes.length === 0 ? (
        <EmptyState
          icon={<FileText className="size-8" />}
          message="No resumes yet. Upload your first one."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {resumes.map((resume) => (
            <li
              key={resume.id}
              className="flex items-center gap-3 rounded-lg border border-border/70 bg-background/40 px-3 py-2.5"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                <FileText className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{resume.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(resume.created_at ?? resume.uploaded_at)}
                </p>
              </div>
              <Button
                variant="destructive"
                size="icon-sm"
                aria-label={`Delete ${resume.filename}`}
                onClick={() => handleDelete(resume.id)}
              >
                <Trash2 className="size-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </ColumnCard>
  )
}

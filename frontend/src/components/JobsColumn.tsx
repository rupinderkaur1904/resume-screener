import { useState } from 'react'
import { Briefcase, CheckCircle2, Loader2, Plus, Trash2, X } from 'lucide-react'
import api from '@/api/client'
import { getErrorMessage } from '@/lib/helpers'
import type { Job } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { ColumnCard, EmptyState } from '@/components/ColumnCard'

const EMPTY = { title: '', company: '', description: '', requirements: '' }

export function JobsColumn({
  jobs,
  setJobs,
}: {
  jobs: Job[]
  setJobs: React.Dispatch<React.SetStateAction<Job[]>>
}) {
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const canSave = form.title.trim() !== '' && form.company.trim() !== ''

  function flashSuccess(msg: string) {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 3000)
  }

  function cancel() {
    setShowForm(false)
    setForm(EMPTY)
    setError('')
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!canSave) return
    setError('')
    setSaving(true)
    try {
      const { data } = await api.post<Job>('/jobs/', {
        title: form.title,
        company: form.company,
        description: form.description,
        requirements: form.requirements,
      })
      setJobs((prev) => [data, ...prev])
      setForm(EMPTY)
      setShowForm(false)
      flashSuccess('Job saved successfully.')
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save job.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: Job['id']) {
    setError('')
    const prev = jobs
    setJobs((list) => list.filter((j) => j.id !== id))
    try {
      await api.delete(`/jobs/${id}`)
    } catch (err) {
      setJobs(prev)
      setError(getErrorMessage(err, 'Could not delete job.'))
    }
  }

  return (
    <ColumnCard title="Saved Jobs" count={jobs.length} icon={<Briefcase className="size-4" />}>
      {!showForm ? (
        <Button className="w-full" onClick={() => setShowForm(true)}>
          <Plus className="size-4" />
          Add Job
        </Button>
      ) : (
        <form
          onSubmit={handleSave}
          className="flex flex-col gap-3 rounded-lg border border-border/70 bg-background/40 p-3"
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="job-title">Job Title</Label>
            <Input
              id="job-title"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="Senior Frontend Engineer"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="job-company">Company</Label>
            <Input
              id="job-company"
              value={form.company}
              onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
              placeholder="Acme Inc."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="job-description">Description</Label>
            <Textarea
              id="job-description"
              rows={4}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Role responsibilities and context..."
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="job-requirements">Requirements</Label>
            <Textarea
              id="job-requirements"
              rows={3}
              value={form.requirements}
              onChange={(e) => setForm((f) => ({ ...f, requirements: e.target.value }))}
              placeholder="Required skills and qualifications..."
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" className="flex-1" disabled={!canSave || saving}>
              {saving && <Loader2 className="size-4 animate-spin" />}
              {saving ? 'Saving...' : 'Save Job'}
            </Button>
            <Button type="button" variant="outline" onClick={cancel}>
              <X className="size-4" />
              Cancel
            </Button>
          </div>
        </form>
      )}

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

      {jobs.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="size-8" />}
          message="No jobs yet. Add one to get started."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {jobs.map((job) => (
            <li
              key={job.id}
              className="flex items-start gap-3 rounded-lg border border-border/70 bg-background/40 px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{job.title}</p>
                <p className="text-xs text-muted-foreground">{job.company}</p>
                {job.description && (
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                    {job.description.length > 120
                      ? `${job.description.slice(0, 120)}...`
                      : job.description}
                  </p>
                )}
              </div>
              <Button
                variant="destructive"
                size="icon-sm"
                aria-label={`Delete ${job.title}`}
                onClick={() => handleDelete(job.id)}
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

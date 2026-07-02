import { useEffect, useState } from 'react'
import { Loader2, Sparkles, Target } from 'lucide-react'
import api from '@/api/client'
import { getErrorMessage, scoreColor } from '@/lib/helpers'
import type { Job, MatchResponse, MatchResult, Resume } from '@/lib/types'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ColumnCard, EmptyState } from '@/components/ColumnCard'
import { cn } from '@/lib/utils'

const SCORE_CLASSES = {
  success: { text: 'text-success', bar: 'bg-success', ring: 'bg-success/15' },
  warning: { text: 'text-warning', bar: 'bg-warning', ring: 'bg-warning/15' },
  destructive: { text: 'text-destructive', bar: 'bg-destructive', ring: 'bg-destructive/15' },
} as const

export function MatchesColumn({ resumes, jobs }: { resumes: Resume[]; jobs: Job[] }) {
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState<MatchResult[] | null>(null)

  // Clear selection if the chosen resume gets deleted.
  useEffect(() => {
    if (selected && !resumes.some((r) => String(r.id) === selected)) {
      setSelected('')
    }
  }, [resumes, selected])

  const hasResumes = resumes.length > 0
  const hasJobs = jobs.length > 0

  async function findMatches() {
    if (!selected) return
    setError('')
    setLoading(true)
    setResults(null)
    try {
      const { data } = await api.post<MatchResponse>(
        `/matches/compute?resume_id=${selected}`,
      )
      const sorted = [...data.results].sort((a, b) => b.score - a.score)
      setResults(sorted)
    } catch (err) {
      setError(
        getErrorMessage(err, 'No jobs with embeddings found. Add some jobs first.'),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <ColumnCard title="Match Results" icon={<Sparkles className="size-4" />}>
      <Select value={selected} onValueChange={(v) => setSelected(v as string)} disabled={!hasResumes}>
        <SelectTrigger className="w-full">
          <SelectValue
            placeholder={hasResumes ? 'Select a resume...' : 'Upload a resume first'}
          />
        </SelectTrigger>
        <SelectContent>
          {resumes.map((r) => (
            <SelectItem key={r.id} value={String(r.id)}>
              {r.filename}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        className="w-full"
        size="lg"
        disabled={!selected || !hasJobs || loading}
        onClick={findMatches}
      >
        {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
        {loading ? 'Scoring your resume...' : 'Find Matches'}
      </Button>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {!results && !loading && !error && (
        <EmptyState
          icon={<Target className="size-8" />}
          message="Select a resume and click Find Matches"
        />
      )}

      {results && results.length > 0 && (
        <ul className="flex flex-col gap-3">
          {results.map((result, index) => {
            const tone = scoreColor(result.score)
            const c = SCORE_CLASSES[tone]
            return (
              <li
                key={result.job_id}
                className="rounded-lg border border-border/70 bg-background/40 p-3"
              >
                <div className="flex items-start gap-3">
                  <span
                    className={cn(
                      'flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-primary',
                      'bg-primary/15',
                    )}
                  >
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{result.company}</p>
                    <p className="truncate text-xs text-muted-foreground">{result.title}</p>
                  </div>
                  <span className={cn('text-2xl font-bold leading-none', c.text)}>
                    {Math.round(result.score)}%
                  </span>
                </div>

                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn('h-full rounded-full transition-all', c.bar)}
                    style={{ width: `${Math.min(100, Math.max(0, result.score))}%` }}
                  />
                </div>

                {result.explanation?.summary && (
                  <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                    {result.explanation.summary}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {results && results.length === 0 && (
        <EmptyState
          icon={<Target className="size-8" />}
          message="No matches returned. Try adding more jobs."
        />
      )}
    </ColumnCard>
  )
}

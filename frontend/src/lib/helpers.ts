import { AxiosError } from 'axios'

/** Format a date string like "Jun 26 2026". Falls back gracefully. */
export function formatDate(value?: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  })
}

/** Pull a human-friendly message out of an unknown error. */
export function getErrorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    return err.message || fallback
  }
  if (err instanceof Error) return err.message
  return fallback
}

/** Decode the JWT payload to read the user's email (best effort). */
export function getEmailFromToken(token: string | null): string {
  if (!token) return ''
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.email || payload.sub || ''
  } catch {
    return ''
  }
}

/** Color bucket for a match score. */
export function scoreColor(score: number): 'success' | 'warning' | 'destructive' {
  if (score >= 70) return 'success'
  if (score >= 40) return 'warning'
  return 'destructive'
}

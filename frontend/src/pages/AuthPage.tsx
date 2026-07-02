import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, CheckCircle2 } from 'lucide-react'
import api from '@/api/client'
import { getErrorMessage } from '@/lib/helpers'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
// Local fallback for Label component (avoids import resolution issues)
function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="text-sm font-medium">
      {children}
    </label>
  )
}
import { cn } from '@/lib/utils'

type Mode = 'signin' | 'signup'

export default function AuthPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('signin')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  function switchMode(next: Mode) {
    setMode(next)
    setError('')
    if (next === 'signup') setSuccess('')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'signin') {
        const { data } = await api.post('/auth/login', { email, password })
        localStorage.setItem('token', data.access_token)
        navigate('/dashboard')
      } else {
        await api.post('/auth/register', {
          full_name: fullName,
          email,
          password,
        })
        setSuccess('Account created. Please sign in.')
        setMode('signin')
        setPassword('')
        setFullName('')
      }
    } catch (err) {
      setError(getErrorMessage(err, 'Authentication failed. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-10">
      {/* Background grid + glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,oklch(1_0_0/0.04)_1px,transparent_1px),linear-gradient(to_bottom,oklch(1_0_0/0.04)_1px,transparent_1px)] [background-size:48px_48px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 left-1/2 size-[480px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]"
      />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo iconClassName="size-11 rounded-2xl" textClassName="text-2xl" className="gap-3" />
          <p className="mt-4 text-pretty text-sm text-muted-foreground">
            Match your resume to the right jobs, powered by AI
          </p>
        </div>

        <div className="rounded-xl bg-card/80 p-1.5 shadow-2xl shadow-black/40 ring-1 ring-foreground/10 backdrop-blur">
          {/* Tabs */}
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-muted/60 p-1">
            {(['signin', 'signup'] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => switchMode(m)}
                className={cn(
                  'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  mode === m
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {m === 'signin' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
            {success && mode === 'signin' && (
              <div className="flex items-center gap-2 rounded-lg bg-success/15 px-3 py-2 text-sm text-success">
                <CheckCircle2 className="size-4 shrink-0" />
                <span>{success}</span>
              </div>
            )}

            {mode === 'signup' && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="fullName">Full Name</Label>
                <Input
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ada Lovelace"
                  required
                  autoComplete="name"
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" size="lg" disabled={loading} className="mt-1 w-full">
              {loading && <Loader2 className="size-4 animate-spin" />}
              {loading
                ? mode === 'signin'
                  ? 'Signing in...'
                  : 'Creating account...'
                : mode === 'signin'
                  ? 'Sign In'
                  : 'Create Account'}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            onClick={() => switchMode(mode === 'signin' ? 'signup' : 'signin')}
            className="font-medium text-primary hover:underline"
          >
            {mode === 'signin' ? 'Create one' : 'Sign in'}
          </button>
        </p>
      </div>
    </main>
  )
}

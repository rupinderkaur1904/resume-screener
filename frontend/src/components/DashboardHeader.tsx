import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/Logo'

export function DashboardHeader({ email }: { email: string }) {
  const navigate = useNavigate()

  function logout() {
    localStorage.clear()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <div className="flex items-center gap-3">
          {email && (
            <span className="hidden text-sm text-muted-foreground sm:inline">{email}</span>
          )}
          <Button variant="outline" size="sm" onClick={logout}>
            <LogOut className="size-4" />
            Logout
          </Button>
        </div>
      </div>
    </header>
  )
}

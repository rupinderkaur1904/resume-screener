import { cn } from '@/lib/utils'

export function ColumnCard({
  title,
  count,
  icon,
  children,
  className,
}: {
  title: string
  count?: number
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        'flex h-full flex-col gap-4 rounded-xl bg-card/80 p-5 shadow-xl shadow-black/20 ring-1 ring-foreground/10 backdrop-blur',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {icon && <span className="text-primary">{icon}</span>}
        <h2 className="text-base font-semibold">{title}</h2>
        {typeof count === 'number' && (
          <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/15 px-1.5 text-xs font-semibold text-primary">
            {count}
          </span>
        )}
      </div>
      {children}
    </section>
  )
}

export function EmptyState({
  icon,
  message,
}: {
  icon: React.ReactNode
  message: string
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border/80 px-4 py-10 text-center">
      <span className="text-muted-foreground/70">{icon}</span>
      <p className="text-pretty text-sm text-muted-foreground">{message}</p>
    </div>
  )
}

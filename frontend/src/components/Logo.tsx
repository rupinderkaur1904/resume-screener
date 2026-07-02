import { Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Logo({
  className,
  iconClassName,
  textClassName,
  showText = true,
}: {
  className?: string
  iconClassName?: string
  textClassName?: string
  showText?: boolean
}) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span
        className={cn(
          'flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-[0_0_18px_-2px] shadow-primary/60',
          iconClassName,
        )}
      >
        <Zap className="size-4 fill-current" />
      </span>
      {showText && (
        <span className={cn('text-lg font-bold tracking-tight', textClassName)}>
          Resume<span className="text-primary">AI</span>
        </span>
      )}
    </div>
  )
}

import * as React from 'react'
import { cn } from '../../lib/utils'

const Card = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      `
      bg-[var(--bg-card)] backdrop-blur-[12px] border border-[var(--border)]
      rounded-[12px] p-5 transition-all duration-300
      ease-[cubic-bezier(0.4,0,0.2,1)] relative overflow-hidden
      hover:border-[var(--border-glow)] hover:shadow-[0_16px_40px_rgba(0,0,0,0.45),0_0_0_1px_rgba(124,58,237,0.14)]
      hover:-translate-y-0.5
    `,
      className
    )}
    {...props}
  />
))
Card.displayName = 'Card'

const CardHeader = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      `
      flex items-center justify-between mb-5 pb-4
      border-b border-[var(--border-light)] gap-3
    `,
      className
    )}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      `
      font-['Space_Grotesk'] text-[0.95rem] font-bold
      text-[var(--text-primary)] tracking-tight
    `,
      className
    )}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-[var(--text-muted)]', className)}
    {...props}
  />
))
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('', className)} {...props} />
))
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'flex items-center pt-4 mt-4 border-t border-[var(--border-light)]',
      className
    )}
    {...props}
  />
))
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }

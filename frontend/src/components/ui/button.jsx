import * as React from 'react'
import { cva } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const buttonVariants = cva(
  `
    inline-flex items-center justify-center gap-2 whitespace-nowrap
    rounded-[10px] font-semibold text-sm font-['Plus_Jakarta_Sans']
    transition-all duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2
    disabled:pointer-events-none disabled:opacity-45
  `,
  {
    variants: {
      variant: {
        primary: `
          bg-gradient-to-br from-[#7c3aed] via-[#6366f1] to-[#06b6d4]
          text-white shadow-[0_2px_10px_rgba(124,58,237,0.3)]
          hover:shadow-[0_0_30px_rgba(124,58,237,0.35),0_0_60px_rgba(6,182,212,0.1)]
          hover:-translate-y-0.5 active:scale-[0.97]
          ring-1 ring-white/10 inset-0
        `,
        secondary: `
          bg-[var(--bg-elevated)] text-[var(--text-primary)]
          border border-[var(--border)]
          hover:bg-[var(--bg-hover)] hover:border-[var(--border-active)]
          hover:-translate-y-0.5 active:scale-[0.97]
        `,
        accent: `
          bg-gradient-to-br from-[#06d6a0] to-[#10b981]
          text-white shadow-[0_2px_10px_rgba(6,214,160,0.3)]
          hover:shadow-[0_0_30px_rgba(6,214,160,0.3)]
          hover:-translate-y-0.5 active:scale-[0.97]
        `,
        ghost: `
          bg-transparent text-[var(--text-secondary)]
          border border-[var(--border)]
          hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]
          hover:border-[var(--border-active)]
          hover:-translate-y-0.5 active:scale-[0.97]
        `,
        danger: `
          bg-[var(--danger-bg)] text-[var(--danger)]
          border border-[var(--danger-border)]
          hover:bg-[var(--danger)] hover:text-white
          hover:-translate-y-0.5 active:scale-[0.97]
        `,
        link: `
          text-[var(--primary-light)] underline-offset-4
          hover:underline hover:text-[var(--primary)]
        `,
        outline: `
          bg-transparent text-[var(--text-primary)]
          border border-[var(--border)]
          hover:bg-[var(--bg-hover)]
          hover:border-[var(--border-active)]
          hover:-translate-y-0.5 active:scale-[0.97]
        `,
      },
      size: {
        sm: 'h-8 px-3 text-xs rounded-[8px]',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base rounded-[12px]',
        xl: 'h-14 px-8 text-base rounded-[14px]',
        icon: 'h-10 w-10 rounded-[10px]',
        'icon-sm': 'h-8 w-8 rounded-[8px]',
        'icon-lg': 'h-12 w-12 rounded-[12px]',
        full: 'w-full h-10 text-sm',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

const Button = React.forwardRef(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? 'span' : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }

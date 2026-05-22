import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { cn } from '../../lib/utils'

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      `
      inline-flex items-center gap-1 p-1
      bg-[var(--bg-surface)] border border-[var(--border)]
      rounded-[12px]
    `,
      className
    )}
    {...props}
  />
))
TabsList.displayName = 'TabsList'

const TabsTrigger = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      `
      inline-flex items-center justify-center whitespace-nowrap
      px-4 py-2 text-[0.82rem] font-semibold
      text-[var(--text-muted)]
      bg-transparent rounded-[9px] transition-all duration-200
      border border-transparent
      hover:text-[var(--text-primary)]
      hover:bg-[var(--bg-hover)]
      focus-visible:outline-none focus-visible:ring-2
      focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2
      disabled:pointer-events-none disabled:opacity-50
      data-[state=active]:
        bg-gradient-to-br from-[#7c3aed] via-[#6366f1] to-[#06b6d4]
        text-white shadow-[0_2px_8px_rgba(124,58,237,0.3)]
        border-white/10
    `,
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      `
      mt-4 focus-visible:outline-none
      data-[state=active]:animate-in data-[state=active]:fade-in-0
      data-[state=active]:slide-in-from-bottom-2
      data-[state=inactive]:hidden
    `,
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }

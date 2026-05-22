import * as React from 'react'
import { cn } from '../../lib/utils'

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        'w-full px-3.5 py-2.5',
        'bg-[var(--bg-surface)] border border-[var(--border)]',
        'rounded-[10px] text-[0.875rem] text-[var(--text-primary)]',
        "font-['Plus_Jakarta_Sans']",
        'placeholder:text-[var(--text-disabled)]',
        'transition-all duration-200',
        'focus:outline-none focus:border-[var(--primary)]',
        'focus:shadow-[0_0_0_3px_rgba(124,58,237,0.15),0_2px_8px_rgba(0,0,0,0.2)]',
        'focus:bg-[var(--bg-elevated)]',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'appearance-none',
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Input.displayName = 'Input'

const Label = React.forwardRef(({ className, required, ...props }, ref) => (
  <label
    ref={ref}
    className={cn(
      'text-[0.78rem] font-semibold text-[var(--text-muted)]',
      'tracking-wide leading-none mb-1 block',
      className
    )}
    {...props}
  >
    {props.children}
    {required && <span className="text-[var(--danger)] ml-0.5">*</span>}
  </label>
))
Label.displayName = 'Label'

const FormGroup = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex flex-col gap-1', className)} {...props} />
))
FormGroup.displayName = 'FormGroup'

const FormHint = ({ className, children, ...props }) => (
  <span className={cn('text-[0.72rem] text-[var(--text-muted)]', className)} {...props}>
    {children}
  </span>
)

const FormError = ({ className, children, ...props }) => (
  <span className={cn('text-[0.72rem] text-[var(--danger)] font-medium', className)} {...props}>
    {children}
  </span>
)

const Select = React.forwardRef(({ className, children, ...props }, ref) => {
  return (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          'w-full px-3.5 py-2.5 pr-10',
          'bg-[var(--bg-surface)] border border-[var(--border)]',
          'rounded-[10px] text-[0.875rem] text-[var(--text-primary)]',
          "font-['Plus_Jakarta_Sans']",
          'transition-all duration-200 appearance-none cursor-pointer',
          'focus:outline-none focus:border-[var(--primary)]',
          'focus:shadow-[0_0_0_3px_rgba(124,58,237,0.15)]',
          'focus:bg-[var(--bg-elevated)]',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%235c6a8a' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 0.875rem center',
        }}
        {...props}
      >
        {children}
      </select>
    </div>
  )
})
Select.displayName = 'Select'

const Textarea = React.forwardRef(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        'w-full px-3.5 py-2.5 min-h-[80px] resize-y',
        'bg-[var(--bg-surface)] border border-[var(--border)]',
        'rounded-[10px] text-[0.875rem] text-[var(--text-primary)]',
        "font-['Plus_Jakarta_Sans']",
        'placeholder:text-[var(--text-disabled)]',
        'transition-all duration-200',
        'focus:outline-none focus:border-[var(--primary)]',
        'focus:shadow-[0_0_0_3px_rgba(124,58,237,0.15)]',
        'focus:bg-[var(--bg-elevated)]',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
})
Textarea.displayName = 'Textarea'

export { Input, Label, FormGroup, FormHint, FormError, Select, Textarea }

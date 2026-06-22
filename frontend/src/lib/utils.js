import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind classes with clsx
 * Standard cn() utility used across the project
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

/**
 * Format VND currency
 */
export function formatVnd(value) {
  if (!value) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFraction: 0,
  }).format(value)
}

/**
 * Format number with locale
 */
export function formatNumber(value) {
  if (!value) return '—'
  return new Intl.NumberFormat('vi-VN').format(value)
}

/**
 * Format percentage
 */
export function formatPct(value, decimals = 1) {
  if (value == null) return '—'
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format compact number (1.2B, 850M)
 */
export function formatCompact(value) {
  if (!value) return '—'
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`
  return String(value)
}

/**
 * Capitalize first letter
 */
export function capitalize(str) {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Slugify text
 */
export function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^\w-]+/g, '')
    .replace(/--+/g, '-')
}

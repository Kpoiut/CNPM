/**
 * Shared hooks and utilities — single barrel export.
 *
 * Merged from hooks/ + utils/ to keep frontend/src/ under 5 subdirs.
 * Import:  import { useAsyncApi, formatVnd } from '../lib'
 */

// --- Hooks ---
export { useAsyncApi, useChatMessages, useAbortController } from './useAsyncApi'

// --- Formatters & Constants ---
export {
  API_BASE, V2_BASE,
  EVIDENCE_TIERS, EVIDENCE_TIER_KEYS, TIER_COLORS, EVIDENCE_LABELS, EVIDENCE_WEIGHTS,
  GRADE_COLORS, PROPERTY_ICONS, PROPERTY_TYPE_COLORS, PIE_CHART_COLORS,
  PRICE_RANGES, PAGE_SIZES,
  formatVnd, formatVndShort, formatPct, formatDate, formatDateTime, formatRelativeTime,
  evidenceTierBadge, confidenceGradeBadge,
} from './formatters'

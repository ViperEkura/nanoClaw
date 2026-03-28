import { DEFAULT_TRUNCATE_LENGTH } from '../constants'

/**
 * Format ISO date string to a short time string.
 * - Today: "14:30"
 * - Other days: "03/26"
 */
export function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

/**
 * Format number with K/M suffixes.
 */
export function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

/**
 * Format a value as pretty-printed JSON string.
 */
export function formatJson(value) {
  if (value == null) return ''
  const str = typeof value === 'string' ? value : JSON.stringify(value)
  try { return JSON.stringify(JSON.parse(str), null, 2) } catch { return str }
}

/**
 * Truncate text to max characters with ellipsis.
 */
export function truncate(text, max = DEFAULT_TRUNCATE_LENGTH) {
  if (!text) return ''
  const str = text.replace(/\s+/g, ' ').trim()
  return str.length > max ? str.slice(0, max) + '\u2026' : str
}

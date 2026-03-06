/**
 * Timezone-Aware Timestamp Utilities
 *
 * IMPORTANT: Backend timestamps are in UTC (with or without 'Z' suffix).
 * These utilities ensure consistent parsing regardless of user timezone.
 *
 * Usage:
 *   import { parseUTC, getTimestampMs } from '@/utils/timestamps'
 *
 *   // Parse backend timestamp
 *   const date = parseUTC("2026-01-15T10:30:00")  // Assumes UTC
 *
 *   // Get Unix ms for calculations
 *   const ms = getTimestampMs("2026-01-15T10:30:00")
 *
 *   // Display in user's local timezone
 *   date.toLocaleString()  // Automatically converts to local time
 */

/**
 * Parse a UTC timestamp from the backend.
 *
 * Handles timestamps with or without timezone indicator:
 * - "2026-01-15T10:30:00Z" -> parsed as UTC (correct)
 * - "2026-01-15T10:30:00+00:00" -> parsed as UTC (correct)
 * - "2026-01-15T10:30:00" -> ASSUMED to be UTC (adds Z suffix)
 *
 * @param {string} timestamp - ISO 8601 timestamp string
 * @returns {Date} Date object representing the correct instant in time
 */
export function parseUTC(timestamp) {
  if (!timestamp) return new Date()

  // Check if timestamp already has timezone info
  const hasTimezone = timestamp.endsWith('Z') ||
                     timestamp.includes('+') ||
                     (timestamp.length > 19 && timestamp.includes('-', 10))

  // If no timezone indicator, assume UTC by adding 'Z'
  if (!hasTimezone) {
    timestamp = timestamp + 'Z'
  }

  return new Date(timestamp)
}

/**
 * Get Unix timestamp (ms) from a UTC timestamp string.
 * Use this for timeline positioning and duration calculations.
 *
 * @param {string} timestamp - ISO 8601 timestamp string
 * @returns {number} Unix timestamp in milliseconds
 */
export function getTimestampMs(timestamp) {
  return parseUTC(timestamp).getTime()
}

/**
 * Format a UTC timestamp for display in user's local timezone.
 *
 * @param {string} timestamp - ISO 8601 timestamp string (UTC)
 * @param {object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted date string in user's local timezone
 */
export function formatLocalTime(timestamp, options = {}) {
  if (!timestamp) return ''
  const date = parseUTC(timestamp)
  return date.toLocaleString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    ...options
  })
}

/**
 * Format a UTC timestamp as local date and time.
 *
 * @param {string} timestamp - ISO 8601 timestamp string (UTC)
 * @returns {string} Formatted as "Jan 15, 2026 10:30:00 AM" in user's timezone
 */
export function formatLocalDateTime(timestamp) {
  if (!timestamp) return ''
  const date = parseUTC(timestamp)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * Format relative time (e.g., "2 hours ago")
 *
 * @param {string} timestamp - ISO 8601 timestamp string (UTC)
 * @returns {string} Human-readable relative time
 */
export function formatRelativeTime(timestamp) {
  if (!timestamp) return 'Unknown'
  const date = parseUTC(timestamp)
  const now = new Date()
  const diffSeconds = Math.floor((now - date) / 1000)

  if (diffSeconds < 0) return 'in the future'
  if (diffSeconds < 60) return 'just now'
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} minutes ago`
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} hours ago`
  if (diffSeconds < 604800) return `${Math.floor(diffSeconds / 86400)} days ago`
  return date.toLocaleDateString()
}

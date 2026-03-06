/**
 * Execution Status Utility (THINK-001)
 *
 * Maps Claude Code stream-json events to human-readable status labels
 * for the dynamic thinking status indicator in Chat.
 */

const TOOL_STATUS_MAP = {
  Read: 'Reading file...',
  Grep: 'Searching code...',
  Glob: 'Finding files...',
  Bash: 'Running command...',
  Edit: 'Editing code...',
  Write: 'Writing file...',
  WebSearch: 'Searching web...',
  WebFetch: 'Fetching page...',
  Task: 'Delegating to agent...',
  NotebookEdit: 'Editing notebook...',
}

/**
 * Extract a human-readable status label from a stream-json event.
 *
 * @param {Object} event - Parsed stream-json event from Claude Code
 * @returns {string|null} Status label, or null if no status change
 */
export function getStatusFromStreamEvent(event) {
  if (!event) return null

  // Init event
  if (event.type === 'init') return 'Starting session...'

  // Result event = done
  if (event.type === 'result') return null

  // Stream end
  if (event.type === 'stream_end') return null

  // Error event
  if (event.type === 'error') return null

  // Content block events (assistant messages)
  const content = event.message?.content || event.content || []
  if (!Array.isArray(content)) return null

  for (const block of content) {
    if (block.type === 'thinking') return 'Thinking...'
    if (block.type === 'text') return 'Responding...'
    if (block.type === 'tool_use') {
      const name = block.name || ''
      if (name.startsWith('mcp__')) {
        const server = name.split('__')[1] || 'tool'
        return `Using ${server}...`
      }
      return TOOL_STATUS_MAP[name] || 'Working...'
    }
    if (block.type === 'tool_result') return 'Processing results...'
  }

  return null
}

/**
 * Minimum display time (ms) per label to prevent flicker on fast tool calls.
 */
export const MIN_LABEL_DISPLAY_MS = 500

/**
 * Heartbeat timeout (ms) - fall back to "Working..." if no events received.
 */
export const HEARTBEAT_TIMEOUT_MS = 10000

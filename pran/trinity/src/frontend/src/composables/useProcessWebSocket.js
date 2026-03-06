/**
 * WebSocket Composable for Process Events
 *
 * Provides real-time updates for process executions via WebSocket.
 * Part of the Process-Driven Platform feature.
 */

import { ref, onMounted, onUnmounted, watch } from 'vue'

/**
 * Composable for subscribing to process execution events via WebSocket.
 *
 * @param {Object} options - Configuration options
 * @param {Ref<string>} options.executionId - The execution ID to subscribe to
 * @param {Function} options.onStepStarted - Callback when a step starts
 * @param {Function} options.onStepCompleted - Callback when a step completes
 * @param {Function} options.onStepFailed - Callback when a step fails
 * @param {Function} options.onProcessCompleted - Callback when the process completes
 * @param {Function} options.onProcessFailed - Callback when the process fails
 */
export function useProcessWebSocket(options = {}) {
  const {
    executionId = ref(null),
    onStepStarted = () => {},
    onStepCompleted = () => {},
    onStepFailed = () => {},
    onProcessCompleted = () => {},
    onProcessFailed = () => {},
    onCompensationStarted = () => {},
    onCompensationCompleted = () => {},
    onCompensationFailed = () => {},
  } = options

  const isConnected = ref(false)
  const lastEvent = ref(null)
  const error = ref(null)

  let ws = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  function connect() {
    const token = localStorage.getItem('token')
    if (!token) {
      error.value = 'No authentication token'
      return
    }

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws?token=${encodeURIComponent(token)}`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        isConnected.value = true
        error.value = null
        reconnectAttempts = 0
        console.log('[ProcessWS] Connected')
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (e) {
          console.error('[ProcessWS] Failed to parse message:', e)
        }
      }

      ws.onclose = (event) => {
        isConnected.value = false
        console.log('[ProcessWS] Disconnected:', event.code, event.reason)

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          console.log(`[ProcessWS] Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`)
          setTimeout(connect, reconnectDelay)
        } else {
          error.value = 'Connection lost. Please refresh the page.'
        }
      }

      ws.onerror = (err) => {
        console.error('[ProcessWS] Error:', err)
        error.value = 'WebSocket error'
      }
    } catch (e) {
      console.error('[ProcessWS] Failed to connect:', e)
      error.value = 'Failed to connect'
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  function handleMessage(message) {
    // Only process events for process_event type
    if (message.type !== 'process_event') {
      return
    }

    // Filter by execution ID if set
    if (executionId.value && message.execution_id !== executionId.value) {
      return
    }

    lastEvent.value = message

    // Route to appropriate callback
    switch (message.event_type) {
      case 'step_started':
        onStepStarted(message)
        break
      case 'step_completed':
        onStepCompleted(message)
        break
      case 'step_failed':
        onStepFailed(message)
        break
      case 'process_completed':
        onProcessCompleted(message)
        break
      case 'process_failed':
        onProcessFailed(message)
        break
      case 'compensation_started':
        onCompensationStarted(message)
        break
      case 'compensation_completed':
        onCompensationCompleted(message)
        break
      case 'compensation_failed':
        onCompensationFailed(message)
        break
    }
  }

  // Connect on mount
  onMounted(() => {
    connect()
  })

  // Disconnect on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    lastEvent,
    error,
    reconnect: connect,
  }
}

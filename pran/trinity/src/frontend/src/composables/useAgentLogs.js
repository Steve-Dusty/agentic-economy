import { ref, watch, onUnmounted, nextTick } from 'vue'

/**
 * Composable for agent logs management
 * Handles log fetching, auto-refresh, and scroll management
 */
export function useAgentLogs(agentRef, agentsStore) {
  const logs = ref('')
  const logLines = ref(100)
  const autoRefreshLogs = ref(false)
  const logsContainer = ref(null)
  const userScrolledUp = ref(false)
  let logsRefreshInterval = null

  const refreshLogs = async () => {
    if (!agentRef.value) return
    try {
      logs.value = await agentsStore.getAgentLogs(agentRef.value.name, logLines.value)
      // Auto-scroll to bottom if user hasn't scrolled up
      if (!userScrolledUp.value) {
        await nextTick()
        scrollLogsToBottom()
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  }

  const scrollLogsToBottom = () => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  }

  const handleLogsScroll = () => {
    if (!logsContainer.value) return
    const { scrollTop, scrollHeight, clientHeight } = logsContainer.value
    // User is considered "scrolled up" if not near the bottom (within 50px)
    userScrolledUp.value = scrollTop + clientHeight < scrollHeight - 50
  }

  // Watch for auto-refresh toggle
  watch(autoRefreshLogs, (enabled) => {
    if (enabled) {
      logsRefreshInterval = setInterval(refreshLogs, 15000)
    } else {
      if (logsRefreshInterval) {
        clearInterval(logsRefreshInterval)
        logsRefreshInterval = null
      }
    }
  })

  // Cleanup on unmount
  onUnmounted(() => {
    if (logsRefreshInterval) {
      clearInterval(logsRefreshInterval)
      logsRefreshInterval = null
    }
  })

  return {
    logs,
    logLines,
    autoRefreshLogs,
    logsContainer,
    userScrolledUp,
    refreshLogs,
    handleLogsScroll
  }
}

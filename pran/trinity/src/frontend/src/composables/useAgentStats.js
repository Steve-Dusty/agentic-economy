import { ref, onUnmounted } from 'vue'

// History configuration: 30 samples at 10s intervals = 5 minutes
const MAX_POINTS = 30

/**
 * Composable for agent container stats polling with history tracking
 * Manages CPU, memory, uptime metrics with auto-polling
 * Maintains rolling history for sparkline charts
 */
export function useAgentStats(agentRef, agentsStore) {
  const agentStats = ref(null)
  const statsLoading = ref(false)

  // History arrays for sparkline charts
  const cpuHistory = ref([])
  const memoryHistory = ref([])

  let statsRefreshInterval = null

  // Initialize history with nulls
  const initHistory = () => {
    cpuHistory.value = Array(MAX_POINTS).fill(null)
    memoryHistory.value = Array(MAX_POINTS).fill(null)
  }

  const loadStats = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    statsLoading.value = true
    try {
      const stats = await agentsStore.getAgentStats(agentRef.value.name)
      agentStats.value = stats

      // Push new values and maintain rolling window
      cpuHistory.value.push(stats.cpu_percent ?? null)
      memoryHistory.value.push(stats.memory_percent ?? null)

      // Trim to max points
      if (cpuHistory.value.length > MAX_POINTS) {
        cpuHistory.value.shift()
      }
      if (memoryHistory.value.length > MAX_POINTS) {
        memoryHistory.value.shift()
      }
    } catch (err) {
      // Don't log 400 errors (agent not running)
      if (err.response?.status !== 400) {
        console.error('Failed to load stats:', err)
      }
      agentStats.value = null
    } finally {
      statsLoading.value = false
    }
  }

  const startStatsPolling = () => {
    initHistory() // Reset history on start
    loadStats() // Load immediately
    statsRefreshInterval = setInterval(loadStats, 10000) // Then every 10 seconds
  }

  const stopStatsPolling = () => {
    if (statsRefreshInterval) {
      clearInterval(statsRefreshInterval)
      statsRefreshInterval = null
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopStatsPolling()
  })

  return {
    agentStats,
    statsLoading,
    cpuHistory,
    memoryHistory,
    loadStats,
    startStatsPolling,
    stopStatsPolling
  }
}

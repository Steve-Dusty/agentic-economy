<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Agent Monitoring</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Fleet-wide health status and alerts
            </p>
          </div>

          <div class="flex items-center gap-3">
            <!-- Service status -->
            <span
              class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
              :class="monitoringStore.enabled ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'"
            >
              <span class="w-2 h-2 rounded-full mr-2" :class="monitoringStore.enabled ? 'bg-green-500' : 'bg-gray-400'"></span>
              {{ monitoringStore.enabled ? 'Monitoring Active' : 'Monitoring Disabled' }}
            </span>

            <!-- Auto-refresh indicator -->
            <span v-if="autoRefreshEnabled" class="text-xs text-gray-500 dark:text-gray-400">
              Auto-refresh: {{ refreshCountdown }}s
            </span>

            <button
              @click="toggleAutoRefresh"
              :class="autoRefreshEnabled ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'"
              class="px-3 py-1.5 text-sm rounded-lg hover:bg-opacity-80 transition-colors"
              :title="autoRefreshEnabled ? 'Disable auto-refresh' : 'Enable auto-refresh'"
            >
              <ClockIcon class="w-4 h-4" />
            </button>

            <button
              @click="refreshAll"
              :disabled="monitoringStore.loading"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg"
              title="Refresh"
            >
              <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': monitoringStore.loading }" />
            </button>

            <!-- Admin controls -->
            <button
              v-if="isAdmin"
              @click="triggerFleetCheck"
              :disabled="triggeringCheck"
              class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
            >
              {{ triggeringCheck ? 'Checking...' : 'Check All' }}
            </button>
          </div>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">{{ monitoringStore.summary.total_agents }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total Agents</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-green-500">
            <div class="text-3xl font-bold text-green-600 dark:text-green-400">{{ monitoringStore.summary.healthy }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Healthy</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-yellow-500">
            <div class="text-3xl font-bold text-yellow-600 dark:text-yellow-400">{{ monitoringStore.summary.degraded }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Degraded</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-500">
            <div class="text-3xl font-bold text-red-600 dark:text-red-400">{{ monitoringStore.summary.unhealthy }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Unhealthy</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-700">
            <div class="text-3xl font-bold text-red-700 dark:text-red-500">{{ monitoringStore.summary.critical }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Critical</div>
          </div>
        </div>

        <!-- Active Alerts -->
        <div v-if="monitoringStore.hasActiveAlerts" class="bg-red-50 dark:bg-red-900/20 rounded-lg shadow mb-6 p-4">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-lg font-medium text-red-800 dark:text-red-200 flex items-center">
              <BellAlertIcon class="w-5 h-5 mr-2" />
              Active Alerts ({{ monitoringStore.alerts.length }})
            </h2>
          </div>
          <div class="space-y-2">
            <div
              v-for="alert in monitoringStore.alerts.slice(0, 5)"
              :key="alert.id"
              class="bg-white dark:bg-gray-800 rounded p-3 flex items-center justify-between"
            >
              <div class="flex items-center gap-3">
                <ExclamationTriangleIcon
                  class="w-5 h-5"
                  :class="alert.priority === 'urgent' ? 'text-red-600' : 'text-yellow-600'"
                />
                <div>
                  <span class="font-medium text-gray-900 dark:text-white">{{ alert.agent_name }}</span>
                  <span class="text-gray-500 dark:text-gray-400 ml-2">{{ alert.title }}</span>
                </div>
              </div>
              <span class="text-xs text-gray-400">{{ formatRelativeTime(alert.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Agent Health Grid -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Agent Health Status</h2>

            <!-- Status filter -->
            <div class="flex items-center gap-2">
              <select
                v-model="statusFilter"
                class="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              >
                <option value="">All Statuses</option>
                <option value="healthy">Healthy</option>
                <option value="degraded">Degraded</option>
                <option value="unhealthy">Unhealthy</option>
                <option value="critical">Critical</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
          </div>

          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="agent in filteredAgents"
              :key="agent.name"
              class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
              @click="viewAgentDetail(agent.name)"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <!-- Status indicator -->
                  <div
                    class="w-10 h-10 rounded-full flex items-center justify-center"
                    :class="getStatusBgClass(agent.status)"
                  >
                    <component
                      :is="getStatusIcon(agent.status)"
                      class="w-5 h-5"
                      :class="getStatusTextClass(agent.status)"
                    />
                  </div>

                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-gray-900 dark:text-white">{{ agent.name }}</span>
                      <span
                        class="px-2 py-0.5 text-xs font-medium rounded capitalize"
                        :class="getStatusBadgeClass(agent.status)"
                      >
                        {{ agent.status }}
                      </span>
                    </div>
                    <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      <span v-if="agent.docker_status">Container: {{ agent.docker_status }}</span>
                      <span v-if="agent.network_reachable !== undefined" class="ml-3">
                        Network: {{ agent.network_reachable ? 'Reachable' : 'Unreachable' }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-4">
                  <!-- Issues list -->
                  <div v-if="agent.issues && agent.issues.length > 0" class="text-right">
                    <div class="text-sm text-red-600 dark:text-red-400">
                      {{ agent.issues.length }} issue{{ agent.issues.length > 1 ? 's' : '' }}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 max-w-xs truncate">
                      {{ agent.issues[0] }}
                    </div>
                  </div>

                  <!-- Last check time -->
                  <div class="text-right">
                    <div class="text-xs text-gray-400">Last check</div>
                    <div class="text-sm text-gray-600 dark:text-gray-300">
                      {{ agent.last_check_at ? formatRelativeTime(agent.last_check_at) : 'Never' }}
                    </div>
                  </div>

                  <!-- Action button -->
                  <button
                    v-if="isAdmin"
                    @click.stop="triggerAgentCheck(agent.name)"
                    :disabled="checkingAgent === agent.name"
                    class="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg"
                    title="Trigger health check"
                  >
                    <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': checkingAgent === agent.name }" />
                  </button>

                  <ChevronRightIcon class="w-5 h-5 text-gray-400" />
                </div>
              </div>
            </div>

            <div v-if="filteredAgents.length === 0" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
              <HeartIcon class="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
              <p class="text-lg font-medium">No agents found</p>
              <p class="text-sm mt-1">
                {{ statusFilter ? 'No agents match the selected filter' : 'No agents are being monitored' }}
              </p>
            </div>
          </div>
        </div>

        <!-- Last updated -->
        <div v-if="monitoringStore.lastCheck" class="mt-4 text-center text-xs text-gray-400">
          Last updated: {{ formatTime(monitoringStore.lastCheck) }}
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMonitoringStore } from '../stores/monitoring'
import { useAuthStore } from '../stores/auth'
import NavBar from '../components/NavBar.vue'
import {
  ArrowPathIcon,
  BellAlertIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  QuestionMarkCircleIcon,
  ChevronRightIcon,
  ClockIcon,
  HeartIcon,
} from '@heroicons/vue/24/outline'
import axios from 'axios'

const router = useRouter()
const monitoringStore = useMonitoringStore()
const authStore = useAuthStore()

// State
const isAdmin = ref(false)
const statusFilter = ref('')
const triggeringCheck = ref(false)
const checkingAgent = ref(null)
const autoRefreshEnabled = ref(true)
const refreshCountdown = ref(30)
let refreshInterval = null
let countdownInterval = null

// Computed
const filteredAgents = computed(() => {
  if (!statusFilter.value) {
    return monitoringStore.agents
  }
  return monitoringStore.agents.filter(a => a.status === statusFilter.value)
})

// Lifecycle
onMounted(async () => {
  // Fetch initial data
  await refreshAll()

  // Check if user is admin
  try {
    const response = await axios.get('/api/users/me', {
      headers: authStore.authHeader
    })
    isAdmin.value = response.data.role === 'admin'
  } catch (e) {
    console.warn('Failed to fetch user role:', e)
  }

  // Start auto-refresh
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

// Methods
async function refreshAll() {
  await Promise.all([
    monitoringStore.fetchStatus(),
    isAdmin.value ? monitoringStore.fetchAlerts() : Promise.resolve()
  ])
  refreshCountdown.value = 30
}

function startAutoRefresh() {
  if (refreshInterval) return

  refreshInterval = setInterval(() => {
    if (autoRefreshEnabled.value) {
      refreshAll()
    }
  }, 30000)

  countdownInterval = setInterval(() => {
    if (autoRefreshEnabled.value && refreshCountdown.value > 0) {
      refreshCountdown.value--
    }
  }, 1000)
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
}

function toggleAutoRefresh() {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  if (autoRefreshEnabled.value) {
    refreshCountdown.value = 30
  }
}

async function triggerFleetCheck() {
  triggeringCheck.value = true
  try {
    await monitoringStore.triggerFleetCheck()
    // Wait a moment then refresh
    setTimeout(() => refreshAll(), 2000)
  } catch (err) {
    console.error('Failed to trigger fleet check:', err)
  } finally {
    triggeringCheck.value = false
  }
}

async function triggerAgentCheck(agentName) {
  checkingAgent.value = agentName
  try {
    await monitoringStore.triggerCheck(agentName)
  } catch (err) {
    console.error('Failed to trigger agent check:', err)
  } finally {
    checkingAgent.value = null
  }
}

function viewAgentDetail(agentName) {
  router.push(`/agents/${agentName}`)
}

function getStatusIcon(status) {
  switch (status) {
    case 'healthy': return CheckCircleIcon
    case 'degraded': return ExclamationTriangleIcon
    case 'unhealthy': return XCircleIcon
    case 'critical': return XCircleIcon
    default: return QuestionMarkCircleIcon
  }
}

function getStatusBgClass(status) {
  switch (status) {
    case 'healthy': return 'bg-green-100 dark:bg-green-900/30'
    case 'degraded': return 'bg-yellow-100 dark:bg-yellow-900/30'
    case 'unhealthy': return 'bg-red-100 dark:bg-red-900/30'
    case 'critical': return 'bg-red-200 dark:bg-red-900/50'
    default: return 'bg-gray-100 dark:bg-gray-700'
  }
}

function getStatusTextClass(status) {
  switch (status) {
    case 'healthy': return 'text-green-600 dark:text-green-400'
    case 'degraded': return 'text-yellow-600 dark:text-yellow-400'
    case 'unhealthy': return 'text-red-600 dark:text-red-400'
    case 'critical': return 'text-red-700 dark:text-red-500'
    default: return 'text-gray-500 dark:text-gray-400'
  }
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'healthy': return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
    case 'degraded': return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
    case 'unhealthy': return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
    case 'critical': return 'bg-red-200 dark:bg-red-900/50 text-red-800 dark:text-red-200'
    default: return 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
  }
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString()
}
</script>

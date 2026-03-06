<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 sm:px-0">
        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Executions</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Monitor and manage process executions
            </p>
          </div>

          <div class="flex items-center gap-3">
            <!-- Auto-refresh indicator -->
            <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <span
                class="w-2 h-2 rounded-full"
                :class="autoRefresh ? 'bg-green-500 animate-pulse' : 'bg-gray-400'"
              ></span>
              <span>{{ autoRefresh ? 'Live' : 'Paused' }}</span>
            </div>

            <button
              @click="toggleAutoRefresh"
              class="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            >
              {{ autoRefresh ? 'Pause' : 'Resume' }}
            </button>

            <button
              @click="executionsStore.fetchExecutions()"
              :disabled="executionsStore.loading"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': executionsStore.loading }" />
            </button>
          </div>
        </div>

        <!-- Filters -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
          <div class="flex flex-wrap gap-4 items-center">
            <!-- Status filter -->
            <div class="flex-1 min-w-[150px]">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Status</label>
              <select
                v-model="statusFilter"
                @change="applyFilters"
                class="w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
              >
                <option value="">All Status</option>
                <option value="pending">⏳ Pending</option>
                <option value="running">🔄 Running</option>
                <option value="paused">🔔 Awaiting Approval</option>
                <option value="completed">✅ Completed</option>
                <option value="failed">❌ Failed</option>
                <option value="cancelled">⛔ Cancelled</option>
                <option value="skipped">⏭️ Skipped</option>
              </select>
            </div>

            <!-- Process filter -->
            <div class="flex-1 min-w-[200px]">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Process</label>
              <select
                v-model="processFilter"
                @change="applyFilters"
                class="w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
              >
                <option value="">All Processes</option>
                <option v-for="p in uniqueProcesses" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </select>
            </div>

            <!-- Clear filters -->
            <div class="flex items-end">
              <button
                v-if="statusFilter || processFilter"
                @click="clearFilters"
                class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <!-- Stats cards -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ executionsStore.stats.total }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ executionsStore.stats.completed }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Completed</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-red-600 dark:text-red-400">{{ executionsStore.stats.failed }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Failed</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{{ executionsStore.stats.running }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Running</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">${{ executionsStore.stats.totalCost }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total Cost</div>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="executionsStore.loading && executionsStore.executions.length === 0" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading executions...</span>
          </div>
        </div>

        <!-- Executions table -->
        <div v-else-if="executionsStore.executions.length > 0" class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Process</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Started</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Duration</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Cost</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="execution in executionsStore.executions"
                :key="execution.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                @click="viewExecution(execution)"
              >
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getStatusClasses(getDisplayStatus(execution))" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium">
                    <span>{{ getStatusIcon(getDisplayStatus(execution)) }}</span>
                    <span class="capitalize">{{ getDisplayStatusText(execution) }}</span>
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900 dark:text-white">{{ execution.process_name }}</div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">{{ execution.triggered_by }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  <div>{{ formatDate(execution.started_at) }}</div>
                  <div class="text-xs">{{ formatRelativeTime(execution.started_at) }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDuration(execution.duration_seconds) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ execution.total_cost || '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm" @click.stop>
                  <div class="flex items-center justify-end gap-2">
                    <!-- Cancel button (for running/pending) -->
                    <button
                      v-if="execution.status === 'running' || execution.status === 'pending'"
                      @click="handleCancel(execution)"
                      class="p-1.5 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
                      title="Cancel"
                    >
                      <StopIcon class="h-4 w-4" />
                    </button>

                    <!-- Retry button (for failed) -->
                    <button
                      v-if="execution.status === 'failed'"
                      @click="handleRetry(execution)"
                      class="p-1.5 rounded-lg text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 transition-colors"
                      title="Retry"
                    >
                      <ArrowPathIcon class="h-4 w-4" />
                    </button>

                    <!-- View button -->
                    <router-link
                      :to="`/executions/${execution.id}`"
                      class="p-1.5 rounded-lg text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                      title="View details"
                    >
                      <EyeIcon class="h-4 w-4" />
                    </router-link>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Pagination -->
          <div class="bg-gray-50 dark:bg-gray-900/50 px-6 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700">
            <div class="text-sm text-gray-500 dark:text-gray-400">
              Showing {{ executionsStore.executions.length }} of {{ executionsStore.total }} executions
            </div>
            <div class="flex gap-2">
              <button
                @click="previousPage"
                :disabled="executionsStore.filters.offset === 0"
                class="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Previous
              </button>
              <button
                @click="nextPage"
                :disabled="executionsStore.filters.offset + executionsStore.filters.limit >= executionsStore.total"
                class="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
          <ClockIcon class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">No executions</h3>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {{ statusFilter || processFilter ? 'No executions match your filters.' : 'Execute a process to see results here.' }}
          </p>
          <div class="mt-6">
            <router-link
              to="/processes"
              class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Go to Processes
            </router-link>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useExecutionsStore } from '../stores/executions'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import {
  ArrowPathIcon,
  EyeIcon,
  StopIcon,
  ClockIcon,
} from '@heroicons/vue/24/outline'

const router = useRouter()
const executionsStore = useExecutionsStore()

// Local state
const autoRefresh = ref(true)
const statusFilter = ref('')
const processFilter = ref('')

// Computed
const uniqueProcesses = computed(() => {
  const seen = new Map()
  executionsStore.executions.forEach(e => {
    if (!seen.has(e.process_id)) {
      seen.set(e.process_id, { id: e.process_id, name: e.process_name })
    }
  })
  return Array.from(seen.values())
})

// Lifecycle
onMounted(() => {
  if (autoRefresh.value) {
    executionsStore.startPolling(30000)
  } else {
    executionsStore.fetchExecutions()
  }
})

onUnmounted(() => {
  executionsStore.stopPolling()
})

// Methods
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    executionsStore.startPolling(30000)
  } else {
    executionsStore.stopPolling()
  }
}

function applyFilters() {
  executionsStore.setFilters({
    status: statusFilter.value,
    processId: processFilter.value,
    offset: 0,
  })
}

function clearFilters() {
  statusFilter.value = ''
  processFilter.value = ''
  executionsStore.clearFilters()
}

function previousPage() {
  const newOffset = Math.max(0, executionsStore.filters.offset - executionsStore.filters.limit)
  executionsStore.setFilters({ offset: newOffset })
}

function nextPage() {
  executionsStore.setFilters({ offset: executionsStore.filters.offset + executionsStore.filters.limit })
}

function viewExecution(execution) {
  router.push(`/executions/${execution.id}`)
}

async function handleCancel(execution) {
  try {
    await executionsStore.cancelExecution(execution.id)
  } catch (error) {
    console.error('Failed to cancel execution:', error)
  }
}

async function handleRetry(execution) {
  try {
    await executionsStore.retryExecution(execution.id)
  } catch (error) {
    console.error('Failed to retry execution:', error)
  }
}

// Formatters
function getStatusIcon(status) {
  const icons = {
    pending: '⏳',
    running: '🔄',
    completed: '✅',
    failed: '❌',
    cancelled: '⛔',
    paused: '⏸️',
    awaiting_approval: '🔔',
    skipped: '⏭️',
  }
  return icons[status] || '❓'
}

function getStatusClasses(status) {
  const classes = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
    cancelled: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
    paused: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
    awaiting_approval: 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300',
    skipped: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
  }
  return classes[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
}

// Enhanced status display for paused executions
// In list view, steps data isn't loaded, so treat ALL paused as awaiting approval
function getDisplayStatus(execution) {
  if (execution.status === 'paused') {
    return 'awaiting_approval'
  }
  return execution.status
}

function getDisplayStatusText(execution) {
  const status = getDisplayStatus(execution)
  if (status === 'awaiting_approval') return 'Awaiting Approval'
  return status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}
</script>

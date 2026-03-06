<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 sm:px-0">
        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Process Dashboard</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Overview of process health and execution metrics
            </p>
          </div>

          <div class="flex items-center gap-3">
            <!-- Time period selector -->
            <select
              v-model="selectedDays"
              @change="onDaysChange"
              class="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option :value="7">Last 7 days</option>
              <option :value="30">Last 30 days</option>
              <option :value="90">Last 90 days</option>
            </select>

            <button
              @click="refreshData"
              :disabled="loading"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': loading }" />
            </button>
          </div>
        </div>

        <!-- Overall stats -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">{{ processesStore.processes.length }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total Processes</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-green-600 dark:text-green-400">{{ publishedCount }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Published</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">{{ analyticsStore.totalExecutions }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Executions ({{ selectedDays }}d)</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold" :class="successRateColor">{{ analyticsStore.overallSuccessRate.toFixed(0) }}%</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Success Rate</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">{{ executionsStore.stats.running }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Running Now</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">{{ analyticsStore.totalCost }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total Cost</div>
          </div>
        </div>

        <!-- Trend Charts -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <TrendChart
              title="Execution Trend"
              :data="analyticsStore.dailyTrends"
              :days="selectedDays"
              chart-type="executions"
            />
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <TrendChart
              title="Cost Trend"
              :data="analyticsStore.dailyTrends"
              :days="selectedDays"
              chart-type="cost"
            />
          </div>
        </div>

        <!-- Process Health Cards -->
        <div v-if="analyticsStore.processMetrics.length > 0" class="mb-6">
          <h2 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Process Health</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="process in analyticsStore.topProcessesByExecutions"
              :key="process.process_id"
              @click="$router.push(`/processes/${process.process_id}`)"
              class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="font-medium text-gray-900 dark:text-white truncate">{{ process.process_name }}</span>
                <span
                  class="px-2 py-0.5 text-xs font-medium rounded"
                  :class="getHealthBadgeClass(process.success_rate)"
                >
                  {{ process.success_rate.toFixed(0) }}%
                </span>
              </div>
              <div class="grid grid-cols-3 gap-2 text-xs text-gray-500 dark:text-gray-400">
                <div>
                  <div class="font-medium text-gray-900 dark:text-white">{{ process.execution_count }}</div>
                  <div>Executions</div>
                </div>
                <div>
                  <div class="font-medium text-gray-900 dark:text-white">{{ formatDuration(process.average_duration_seconds) }}</div>
                  <div>Avg Time</div>
                </div>
                <div>
                  <div class="font-medium text-gray-900 dark:text-white">{{ process.average_cost || '-' }}</div>
                  <div>Avg Cost</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step Performance -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <!-- Slowest Steps -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Slowest Steps</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400">Steps with highest average duration</p>
            </div>
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="step in analyticsStore.slowestSteps.slice(0, 5)"
                :key="`slow-${step.step_id}-${step.process_name}`"
                class="px-6 py-3"
              >
                <div class="flex items-center justify-between">
                  <div class="min-w-0 flex-1">
                    <div class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ step.step_id }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{{ step.process_name }}</div>
                  </div>
                  <div class="text-sm font-medium text-orange-600 dark:text-orange-400 ml-4">
                    {{ formatDuration(step.average_duration_seconds) }}
                  </div>
                </div>
              </div>
              <div v-if="analyticsStore.slowestSteps.length === 0" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No data available
              </div>
            </div>
          </div>

          <!-- Most Expensive Steps -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Most Expensive Steps</h2>
              <p class="text-xs text-gray-500 dark:text-gray-400">Steps with highest total cost</p>
            </div>
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="step in analyticsStore.mostExpensiveSteps.slice(0, 5)"
                :key="`exp-${step.step_id}-${step.process_name}`"
                class="px-6 py-3"
              >
                <div class="flex items-center justify-between">
                  <div class="min-w-0 flex-1">
                    <div class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ step.step_id }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{{ step.process_name }}</div>
                  </div>
                  <div class="text-sm font-medium text-blue-600 dark:text-blue-400 ml-4">
                    {{ step.total_cost }}
                  </div>
                </div>
              </div>
              <div v-if="analyticsStore.mostExpensiveSteps.length === 0" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No data available
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Recent executions -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Recent Executions</h2>
              <router-link
                to="/executions"
                class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
              >
                View all →
              </router-link>
            </div>
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="execution in recentExecutions"
                :key="execution.id"
                @click="$router.push(`/executions/${execution.id}`)"
                class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <span :class="getStatusDotClasses(execution.status)" class="w-2.5 h-2.5 rounded-full"></span>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-white">{{ execution.process_name }}</div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">{{ formatRelativeTime(execution.started_at) }}</div>
                    </div>
                  </div>
                  <span :class="getStatusBadgeClasses(execution.status)" class="px-2 py-0.5 rounded text-xs font-medium capitalize">
                    {{ execution.status }}
                  </span>
                </div>
              </div>
              <div v-if="recentExecutions.length === 0" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No recent executions
              </div>
            </div>
          </div>

          <!-- Active processes -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h2 class="text-lg font-medium text-gray-900 dark:text-white">Published Processes</h2>
              <router-link
                to="/processes"
                class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
              >
                View all →
              </router-link>
            </div>
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="process in publishedProcesses"
                :key="process.id"
                @click="$router.push(`/processes/${process.id}`)"
                class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-gray-900 dark:text-white">{{ process.name }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">v{{ process.version }} · {{ process.step_count || 0 }} steps</div>
                  </div>
                  <button
                    @click.stop="executeProcess(process)"
                    class="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded transition-colors"
                  >
                    Execute
                  </button>
                </div>
              </div>
              <div v-if="publishedProcesses.length === 0" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No published processes
              </div>
            </div>
          </div>
        </div>

        <!-- Quick actions -->
        <div class="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Quick Actions</h2>
          <div class="flex flex-wrap gap-4">
            <router-link
              to="/processes/new"
              class="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <PlusIcon class="w-4 h-4 mr-2" />
              Create Process
            </router-link>
            <router-link
              to="/executions"
              class="inline-flex items-center px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors"
            >
              <ClockIcon class="w-4 h-4 mr-2" />
              View All Executions
            </router-link>
            <router-link
              to="/processes"
              class="inline-flex items-center px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition-colors"
            >
              <CubeIcon class="w-4 h-4 mr-2" />
              Manage Processes
            </router-link>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useProcessesStore } from '../stores/processes'
import { useExecutionsStore } from '../stores/executions'
import { useAnalyticsStore } from '../stores/analytics'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import TrendChart from '../components/process/TrendChart.vue'
import {
  ArrowPathIcon,
  PlusIcon,
  ClockIcon,
  CubeIcon,
} from '@heroicons/vue/24/outline'

const processesStore = useProcessesStore()
const executionsStore = useExecutionsStore()
const analyticsStore = useAnalyticsStore()

// State
const loading = ref(false)
const selectedDays = ref(30)

// Computed
const publishedCount = computed(() =>
  processesStore.processes.filter(p => p.status === 'published').length
)

const publishedProcesses = computed(() =>
  processesStore.processes.filter(p => p.status === 'published').slice(0, 5)
)

const recentExecutions = computed(() =>
  executionsStore.executions.slice(0, 5)
)

const successRateColor = computed(() => {
  const rate = analyticsStore.overallSuccessRate
  if (rate >= 80) return 'text-green-600 dark:text-green-400'
  if (rate >= 50) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
})

// Lifecycle
onMounted(() => {
  refreshData()
})

// Methods
async function refreshData() {
  loading.value = true
  try {
    await Promise.all([
      processesStore.fetchProcesses(),
      executionsStore.fetchExecutions(),
      analyticsStore.fetchAllAnalytics(selectedDays.value),
    ])
  } finally {
    loading.value = false
  }
}

function onDaysChange() {
  analyticsStore.fetchAllAnalytics(selectedDays.value)
}

async function executeProcess(process) {
  try {
    await processesStore.executeProcess(process.id)
    await executionsStore.fetchExecutions()
  } catch (error) {
    console.error('Failed to execute process:', error)
  }
}

function getHealthBadgeClass(successRate) {
  if (successRate >= 80) return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
  if (successRate >= 50) return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
  return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

// Formatters
function getStatusDotClasses(status) {
  const classes = {
    pending: 'bg-yellow-500',
    running: 'bg-blue-500 animate-pulse',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-400',
  }
  return classes[status] || 'bg-gray-400'
}

function getStatusBadgeClasses(status) {
  const classes = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    cancelled: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  }
  return classes[status] || 'bg-gray-100 text-gray-600'
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
</script>

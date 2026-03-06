<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 sm:px-0">
        <!-- Breadcrumb navigation for nested executions -->
        <nav v-if="breadcrumbs.length > 1" class="flex items-center space-x-2 text-sm mb-4" aria-label="Breadcrumb">
          <HomeIcon class="w-4 h-4 text-gray-400" />
          <template v-for="(crumb, index) in breadcrumbs" :key="crumb.id">
            <ChevronRightIcon class="w-4 h-4 text-gray-400" />
            <router-link
              v-if="index < breadcrumbs.length - 1"
              :to="`/executions/${crumb.id}`"
              class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
            >
              {{ crumb.process_name }}
            </router-link>
            <span v-else class="text-gray-700 dark:text-gray-300 font-medium">
              {{ crumb.process_name }}
            </span>
          </template>
        </nav>

        <!-- Loading state -->
        <div v-if="loading" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading execution...</span>
          </div>
        </div>

        <template v-else-if="execution">
          <!-- Header -->
          <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-4">
              <router-link
                to="/executions"
                class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Back to executions"
              >
                <ArrowLeftIcon class="h-5 w-5" />
              </router-link>
              <div>
                <div class="flex items-center gap-3">
                  <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                    {{ execution.process_name }}
                  </h1>
                  <span
                    :class="getStatusClasses(displayStatus)"
                    class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium cursor-help group relative"
                    :title="getStatusExplanation(displayStatus)"
                  >
                    <span>{{ getStatusIcon(displayStatus) }}</span>
                    <span class="capitalize">{{ displayStatusText }}</span>
                    <InformationCircleIcon class="w-4 h-4 opacity-60 group-hover:opacity-100" />
                    <!-- Tooltip -->
                    <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-xs font-normal text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                      {{ getStatusExplanation(displayStatus) }}
                      <span v-if="displayStatus === 'paused' || displayStatus === 'awaiting_approval'" class="block mt-1 text-indigo-300">
                        → Go to Approvals page
                      </span>
                    </span>
                  </span>
                </div>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Execution ID: <code class="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-xs">{{ execution.id }}</code>
                </p>
                <!-- Retry relationship badge -->
                <p v-if="execution.retry_of" class="mt-1 text-sm">
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                    <ArrowPathIcon class="w-3 h-3" />
                    Retry of:
                    <router-link
                      :to="`/executions/${execution.retry_of}`"
                      class="underline hover:text-amber-900 dark:hover:text-amber-100"
                    >
                      {{ execution.retry_of.substring(0, 8) }}...
                    </router-link>
                  </span>
                </p>
                <!-- Sub-process relationship badge (Called by parent) -->
                <p v-if="execution.parent_execution_id" class="mt-1 text-sm">
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
                    <ArrowUpIcon class="w-3 h-3" />
                    Called by:
                    <router-link
                      :to="`/executions/${execution.parent_execution_id}`"
                      class="underline hover:text-indigo-900 dark:hover:text-indigo-100"
                    >
                      {{ execution.parent_execution_id.substring(0, 8) }}...
                    </router-link>
                    <span v-if="execution.parent_step_id" class="text-indigo-500 dark:text-indigo-400">
                      (step: {{ execution.parent_step_id }})
                    </span>
                  </span>
                </p>
                <!-- Child executions indicator -->
                <p v-if="execution.child_execution_ids && execution.child_execution_ids.length > 0" class="mt-1 text-sm">
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300">
                    <ArrowDownIcon class="w-3 h-3" />
                    {{ execution.child_execution_ids.length }} child execution{{ execution.child_execution_ids.length > 1 ? 's' : '' }}
                  </span>
                </p>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <!-- WebSocket connection indicator -->
              <div
                v-if="execution.status === 'running' || execution.status === 'pending' || execution.status === 'paused'"
                class="flex items-center gap-2 text-sm"
              >
                <span
                  class="w-2 h-2 rounded-full"
                  :class="wsConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'"
                ></span>
                <span :class="wsConnected ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'">
                  {{ wsConnected ? 'Live' : 'Polling' }}
                </span>
              </div>

              <!-- Cancel button (for running/pending) -->
              <button
                v-if="execution.status === 'running' || execution.status === 'pending'"
                @click="handleCancel"
                :disabled="actionInProgress"
                class="px-4 py-2 text-sm font-medium text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 disabled:opacity-50 transition-colors"
              >
                Cancel Execution
              </button>

              <!-- Retry button (for failed) -->
              <button
                v-if="execution.status === 'failed'"
                @click="handleRetry"
                :disabled="actionInProgress"
                class="px-4 py-2 text-sm font-medium text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/50 disabled:opacity-50 transition-colors"
              >
                Retry Execution
              </button>

              <!-- Refresh button -->
              <button
                @click="loadExecution"
                :disabled="loading"
                class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Refresh"
              >
                <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': loading }" />
              </button>
            </div>
          </div>

          <!-- Info cards -->
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Triggered By</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white capitalize">{{ execution.triggered_by }}</div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Started</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ execution.started_at ? formatDateTime(execution.started_at) : '-' }}
              </div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Completed</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ execution.completed_at ? formatDateTime(execution.completed_at) : '-' }}
              </div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Duration</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ formatDuration(execution.duration_seconds) }}
              </div>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Cost</div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">
                {{ execution.total_cost || '-' }}
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div class="border-b border-gray-200 dark:border-gray-700">
              <nav class="flex -mb-px">
                <button
                  @click="activeTab = 'timeline'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'timeline'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Timeline
                </button>
                <button
                  @click="activeTab = 'input'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'input'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Input Data
                </button>
                <button
                  @click="activeTab = 'output'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'output'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Output Data
                </button>
                <button
                  @click="activeTab = 'events'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'events'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                  ]"
                >
                  Event History
                </button>
              </nav>
            </div>

            <div class="p-6">
              <!-- Timeline tab -->
              <div v-if="activeTab === 'timeline'">
                <ExecutionTimeline
                  :execution-id="execution.id"
                  :steps="execution.steps || []"
                  @approval-decided="handleApprovalDecided"
                />
              </div>

              <!-- Input data tab -->
              <div v-else-if="activeTab === 'input'">
                <div v-if="Object.keys(execution.input_data || {}).length > 0">
                  <div class="flex justify-end mb-2">
                    <button
                      @click="copyToClipboard(JSON.stringify(execution.input_data, null, 2))"
                      class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-700 dark:text-gray-300 overflow-auto max-h-96 font-mono">{{ JSON.stringify(execution.input_data, null, 2) }}</pre>
                </div>
                <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
                  No input data
                </div>
              </div>

              <!-- Output data tab -->
              <div v-else-if="activeTab === 'output'">
                <div v-if="Object.keys(execution.output_data || {}).length > 0">
                  <div class="flex justify-end mb-2">
                    <button
                      @click="copyToClipboard(JSON.stringify(execution.output_data, null, 2))"
                      class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-700 dark:text-gray-300 overflow-auto max-h-96 font-mono">{{ JSON.stringify(execution.output_data, null, 2) }}</pre>
                </div>
                <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
                  {{ execution.status === 'completed' ? 'No output data' : 'Execution not yet completed' }}
                </div>
              </div>

              <!-- Events tab -->
              <div v-else-if="activeTab === 'events'">
                <div v-if="events.length > 0" class="flow-root">
                  <ul role="list" class="-mb-8">
                    <li v-for="(event, eventIdx) in events" :key="eventIdx">
                      <div class="relative pb-8">
                        <span v-if="eventIdx !== events.length - 1" class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200 dark:bg-gray-700" aria-hidden="true"></span>
                        <div class="relative flex space-x-3">
                          <div>
                            <span class="h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white dark:ring-gray-800" :class="getEventIconClass(event.event_type)">
                              <component :is="getEventIcon(event.event_type)" class="h-5 w-5 text-white" aria-hidden="true" />
                            </span>
                          </div>
                          <div class="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                            <div>
                              <p class="text-sm text-gray-900 dark:text-gray-200">
                                <span class="font-medium">{{ formatEventType(event.event_type) }}</span>
                                <span v-if="event.step_name" class="ml-2 text-gray-500 dark:text-gray-400">
                                  Step: {{ event.step_name }}
                                </span>
                              </p>
                              <!-- Error message -->
                              <div v-if="event.error_message" class="mt-1 text-sm text-red-600 dark:text-red-400">
                                {{ event.error_message }}
                              </div>
                              <!-- Retry info -->
                              <div v-if="event.attempt" class="mt-1 text-xs text-amber-600 dark:text-amber-400">
                                Attempt {{ event.attempt }} of {{ event.max_attempts }}
                                <span v-if="event.next_retry_at" class="ml-2 text-gray-500 dark:text-gray-400">
                                  Next retry: {{ formatDateTime(event.next_retry_at) }}
                                </span>
                              </div>
                              <!-- Retry count for failures -->
                              <div v-if="event.retry_count > 0 && event.event_type.includes('Failed')" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                After {{ event.retry_count }} retry attempts
                              </div>
                            </div>
                            <div class="text-right text-sm whitespace-nowrap text-gray-500 dark:text-gray-400">
                              <time :datetime="event.timestamp">{{ formatDateTime(event.timestamp) }}</time>
                            </div>
                          </div>
                        </div>
                      </div>
                    </li>
                  </ul>
                </div>
                <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
                  No events found
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Error state -->
        <div v-else class="text-center py-12 bg-white dark:bg-gray-800 rounded-xl shadow">
          <ExclamationCircleIcon class="mx-auto h-12 w-12 text-red-400" />
          <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">Execution not found</h3>
          <div class="mt-6">
            <router-link
              to="/executions"
              class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
            >
              Back to executions
            </router-link>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExecutionsStore } from '../stores/executions'
import { useProcessWebSocket } from '../composables/useProcessWebSocket'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import ExecutionTimeline from '../components/ExecutionTimeline.vue'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ExclamationCircleIcon,
  PlayIcon,
  CheckIcon,
  XMarkIcon,
  ClockIcon,
  PauseIcon,
  UserIcon,
  HomeIcon,
  ChevronRightIcon,
  InformationCircleIcon,
} from '@heroicons/vue/24/outline'
import { useOnboarding } from '../composables/useOnboarding'

const route = useRoute()
const router = useRouter()
const executionsStore = useExecutionsStore()
const { markChecklistItem } = useOnboarding()

// State
const loading = ref(false)
const execution = ref(null)
const activeTab = ref('timeline')
const actionInProgress = ref(false)
const executionId = computed(() => route.params.id)
const events = ref([])
const breadcrumbs = ref([])  // For nested sub-process navigation

// Check if paused due to waiting_approval
const hasWaitingApproval = computed(() => {
  return execution.value?.steps?.some(s => s.status === 'waiting_approval') || false
})

// Display status (enhanced for approval visibility)
const displayStatus = computed(() => {
  if (execution.value?.status === 'paused' && hasWaitingApproval.value) {
    return 'awaiting_approval'
  }
  return execution.value?.status || 'unknown'
})

const displayStatusText = computed(() => {
  if (displayStatus.value === 'awaiting_approval') {
    return 'Awaiting Approval'
  }
  return displayStatus.value
})

// Watch active tab to load events
watch(activeTab, (newTab) => {
  if (newTab === 'events' && events.value.length === 0) {
    loadEvents()
  }
})

// Watch execution ID to clear stale data when navigating to different execution
watch(executionId, () => {
  events.value = []  // Clear events for new execution
  breadcrumbs.value = []  // Clear breadcrumbs for new execution
})

// WebSocket for real-time updates
const { isConnected: wsConnected, error: wsError } = useProcessWebSocket({
  executionId,
  onStepStarted: (event) => {
    // Update step status in UI
    if (execution.value) {
      const step = execution.value.steps?.find(s => s.step_id === event.step_id)
      if (step) {
        step.status = 'running'
        step.started_at = event.timestamp
      }
    }
    // Add to events list if active
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
  },
  onStepCompleted: (event) => {
    // Update step status in UI
    if (execution.value) {
      const step = execution.value.steps?.find(s => s.step_id === event.step_id)
      if (step) {
        step.status = 'completed'
        step.completed_at = event.timestamp
      }
    }
    // Add to events list if active
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
  },
  onStepFailed: (event) => {
    // Update step status in UI
    if (execution.value) {
      const step = execution.value.steps?.find(s => s.step_id === event.step_id)
      if (step) {
        step.status = 'failed'
        step.completed_at = event.timestamp
        // Construct error object from event fields
        step.error = {
          message: event.error_message || event.error || 'Unknown error',
          code: event.error_code || null,
          failed_at: event.timestamp,
        }
        step.retry_count = event.retry_count || 0
      }
    }
    // Add to events list if active
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
  },
  onProcessCompleted: (event) => {
    // Add event immediately for real-time feedback
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
    // Reload after short delay to ensure all events are persisted
    setTimeout(() => loadExecution(), 500)
  },
  onProcessFailed: (event) => {
    // Add event immediately for real-time feedback
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
    // Reload after short delay to ensure all events are persisted
    setTimeout(() => loadExecution(), 500)
  },
  onCompensationStarted: (event) => {
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
  },
  onCompensationCompleted: (event) => {
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
  },
  onCompensationFailed: (event) => {
    if (activeTab.value === 'events') {
      events.value.push(event)
    }
  },
})

// Auto-refresh interval (fallback when WebSocket not connected)
let refreshInterval = null

// Lifecycle
onMounted(() => {
  loadExecution()

  // Fallback auto-refresh for active executions (when WS not working)
  // Includes 'paused' because it may be waiting for approval
  refreshInterval = setInterval(() => {
    if (!wsConnected.value && execution.value &&
        (execution.value.status === 'running' || execution.value.status === 'pending' || execution.value.status === 'paused')) {
      loadExecution()
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// Methods
async function loadExecution() {
  loading.value = true
  try {
    execution.value = await executionsStore.getExecution(route.params.id)
    if (activeTab.value === 'events') {
      await loadEvents()
    }
    // Build breadcrumb chain for nested sub-process navigation
    await buildBreadcrumbs()
    // Mark onboarding item as complete when viewing an execution
    markChecklistItem('monitorExecution')
  } catch (error) {
    console.error('Failed to load execution:', error)
    execution.value = null
  } finally {
    loading.value = false
  }
}

async function buildBreadcrumbs() {
  const crumbs = []
  let currentExec = execution.value

  // Start with current execution
  if (currentExec) {
    crumbs.unshift({
      id: currentExec.id,
      process_name: currentExec.process_name,
    })
  }

  // Traverse up the parent chain (max 10 levels to prevent infinite loops)
  let depth = 0
  while (currentExec?.parent_execution_id && depth < 10) {
    try {
      const parentExec = await executionsStore.getExecution(currentExec.parent_execution_id)
      if (parentExec) {
        crumbs.unshift({
          id: parentExec.id,
          process_name: parentExec.process_name,
        })
        currentExec = parentExec
      } else {
        break
      }
    } catch (e) {
      console.warn('Failed to load parent execution:', e)
      break
    }
    depth++
  }

  breadcrumbs.value = crumbs
}

async function loadEvents() {
  try {
    events.value = await executionsStore.getExecutionEvents(executionId.value)
  } catch (error) {
    console.error('Failed to load events:', error)
  }
}

async function handleCancel() {
  if (!execution.value?.id) {
    console.error('Cannot cancel: execution not loaded')
    return
  }
  actionInProgress.value = true
  try {
    await executionsStore.cancelExecution(execution.value.id)
    await loadExecution()
  } catch (error) {
    console.error('Failed to cancel execution:', error)
  } finally {
    actionInProgress.value = false
  }
}

async function handleRetry() {
  if (!execution.value?.id) {
    console.error('Cannot retry: execution not loaded')
    return
  }
  actionInProgress.value = true
  try {
    const newExecution = await executionsStore.retryExecution(execution.value.id)
    // Navigate to new execution
    router.push(`/executions/${newExecution.id}`)
  } catch (error) {
    console.error('Failed to retry execution:', error)
  } finally {
    actionInProgress.value = false
  }
}

async function handleApprovalDecided({ stepId, decision }) {
  console.log(`Approval ${decision} for step ${stepId}`)
  // Refresh execution data to show updated status
  await loadExecution()
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
}

function getEventIconClass(type) {
  if (!type) return 'bg-gray-400'
  // Compensation events
  if (type.toLowerCase().includes('compensation')) {
    if (type.toLowerCase().includes('completed')) return 'bg-green-500'
    if (type.toLowerCase().includes('failed')) return 'bg-red-500'
    return 'bg-amber-500'  // Started
  }
  if (type.includes('Retrying')) return 'bg-amber-500'
  if (type.includes('Started')) return 'bg-blue-500'
  if (type.includes('Completed')) return 'bg-green-500'
  if (type.includes('Failed')) return 'bg-red-500'
  if (type.includes('Cancelled')) return 'bg-gray-500'
  if (type.includes('Skipped')) return 'bg-gray-400'
  if (type.includes('Approval')) return 'bg-purple-500'
  return 'bg-gray-400'
}

function getEventIcon(type) {
  if (type.includes('Retrying')) return ArrowPathIcon
  if (type.includes('Started')) return PlayIcon
  if (type.includes('Completed')) return CheckIcon
  if (type.includes('Failed')) return XMarkIcon
  if (type.includes('Cancelled')) return XMarkIcon
  if (type.includes('Skipped')) return PauseIcon
  if (type.includes('Approval')) return UserIcon
  return ClockIcon
}

function formatEventType(type) {
  if (!type) return 'Unknown'
  // Handle snake_case (step_completed -> Step Completed)
  if (type.includes('_')) {
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
  }
  // Handle PascalCase (StepCompleted -> Step Completed)
  return type.replace(/([A-Z])/g, ' $1').trim()
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
    awaiting_approval: '🔔',  // Alert bell for approval
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
    awaiting_approval: 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 animate-pulse',  // Amber with pulse
    skipped: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
  }
  return classes[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
}

// Status explanations for tooltips
function getStatusExplanation(status) {
  const explanations = {
    pending: 'Waiting to start. The execution is queued and will begin shortly.',
    running: 'Execution in progress. Steps are being processed by agents.',
    completed: 'All steps finished successfully. View step outputs below.',
    failed: 'Execution stopped due to an error. Check step details for more information.',
    cancelled: 'Execution was manually cancelled before completion.',
    paused: 'Awaiting human approval. Check the Approvals page to continue.',
    awaiting_approval: 'A step requires your approval before continuing. Go to Approvals to review.',
    skipped: 'Execution was skipped because the previous execution was still running at trigger time.',
  }
  return explanations[status] || 'Unknown status'
}

// Step-level status explanations
function getStepStatusExplanation(status, stepData = {}) {
  const explanations = {
    pending: 'Waiting to start',
    waiting: stepData.depends_on?.length
      ? `Waiting for: ${stepData.depends_on.join(', ')}`
      : 'Waiting for dependencies to complete',
    running: 'Currently executing',
    completed: 'Finished successfully',
    failed: stepData.error ? `Error: ${stepData.error}` : 'Failed with an error',
    skipped: stepData.skip_reason || 'Skipped based on gateway condition',
    cancelled: 'Cancelled before execution',
    awaiting_approval: 'Waiting for human approval',
  }
  return explanations[status] || 'Unknown status'
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
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

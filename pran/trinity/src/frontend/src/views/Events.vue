<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Events</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Notifications from your agents
            </p>
          </div>

          <div class="flex items-center gap-3">
            <button
              @click="fetchNotifications"
              :disabled="loading"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg"
              title="Refresh"
            >
              <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': loading }" />
            </button>
          </div>
        </div>

        <!-- Filters -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
          <div class="flex flex-wrap gap-4 items-end">
            <!-- Agent filter -->
            <div class="flex-1 min-w-[150px]">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Agent</label>
              <select
                v-model="agentFilter"
                @change="applyFilters"
                class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              >
                <option value="">All Agents</option>
                <option v-for="agent in availableAgents" :key="agent" :value="agent">
                  {{ agent }}
                </option>
              </select>
            </div>

            <!-- Type filter -->
            <div class="flex-1 min-w-[150px]">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Type</label>
              <select
                v-model="typeFilter"
                @change="applyFilters"
                class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              >
                <option value="">All Types</option>
                <option value="alert">Alert</option>
                <option value="info">Info</option>
                <option value="status">Status</option>
                <option value="completion">Completion</option>
                <option value="question">Question</option>
              </select>
            </div>

            <!-- Priority filter -->
            <div class="flex-1 min-w-[150px]">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Priority</label>
              <select
                v-model="priorityFilter"
                @change="applyFilters"
                class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              >
                <option value="">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>

            <!-- Status filter -->
            <div class="flex-1 min-w-[150px]">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Status</label>
              <select
                v-model="statusFilter"
                @change="applyFilters"
                class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              >
                <option value="pending">Pending</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="">All</option>
              </select>
            </div>

            <!-- Show dismissed checkbox -->
            <div class="flex items-center gap-2">
              <input
                type="checkbox"
                id="showDismissed"
                v-model="showDismissed"
                @change="applyFilters"
                class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <label for="showDismissed" class="text-sm text-gray-500 dark:text-gray-400">
                Show dismissed
              </label>
            </div>

            <!-- Clear filters -->
            <button
              v-if="hasActiveFilters"
              @click="clearFilters"
              class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
            >
              <XMarkIcon class="w-4 h-4" />
              Clear filters
            </button>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-red-600 dark:text-red-400">{{ notificationsStore.pendingCount }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Pending</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-green-600 dark:text-green-400">{{ acknowledgedCount }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Acknowledged</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-gray-900 dark:text-white">{{ notificationsStore.totalCount }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">{{ Object.keys(notificationsStore.agentCounts).length }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Agents</div>
          </div>
        </div>

        <!-- Bulk Actions -->
        <div v-if="notificationsStore.selectedIds.length > 0" class="bg-blue-50 dark:bg-blue-900/30 rounded-lg shadow p-4 mb-4 flex items-center justify-between">
          <span class="text-sm text-blue-700 dark:text-blue-300">
            {{ notificationsStore.selectedIds.length }} selected
          </span>
          <div class="flex gap-2">
            <button
              @click="bulkAcknowledge"
              class="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg"
            >
              Acknowledge Selected
            </button>
            <button
              @click="bulkDismiss"
              class="px-3 py-1.5 text-xs font-medium text-white bg-gray-600 hover:bg-gray-700 rounded-lg"
            >
              Dismiss Selected
            </button>
            <button
              @click="notificationsStore.clearSelection"
              class="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Notifications List -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 class="text-lg font-medium text-gray-900 dark:text-white">Notifications</h2>
            <div v-if="displayedNotifications.length > 0" class="flex items-center gap-2">
              <input
                type="checkbox"
                :checked="allSelected"
                @change="toggleSelectAll"
                class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <label class="text-xs text-gray-500 dark:text-gray-400">Select all</label>
            </div>
          </div>

          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="notification in displayedNotifications"
              :key="notification.id"
              class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              :class="{
                'bg-red-50 dark:bg-red-900/10': notification.status === 'pending' && notification.priority === 'urgent',
                'bg-orange-50 dark:bg-orange-900/10': notification.status === 'pending' && notification.priority === 'high',
                'opacity-60': notification.status === 'dismissed'
              }"
            >
              <div class="flex items-start gap-3">
                <!-- Checkbox -->
                <input
                  type="checkbox"
                  :checked="notificationsStore.selectedIds.includes(notification.id)"
                  @change="notificationsStore.toggleSelected(notification.id)"
                  class="mt-1 w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                />

                <!-- Priority/Type Icon -->
                <div
                  class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                  :class="getPriorityIconBg(notification.priority)"
                >
                  <component :is="getTypeIcon(notification.notification_type)" class="w-5 h-5" :class="getPriorityIconColor(notification.priority)" />
                </div>

                <!-- Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="px-2 py-0.5 text-xs font-medium rounded" :class="getPriorityBadge(notification.priority)">
                      {{ notification.priority.toUpperCase() }}
                    </span>
                    <router-link
                      :to="`/agents/${notification.agent_name}`"
                      class="font-medium text-blue-600 dark:text-blue-400 hover:underline truncate"
                    >
                      {{ notification.agent_name }}
                    </router-link>
                    <span class="text-xs text-gray-500 dark:text-gray-400">
                      {{ formatRelativeTime(notification.created_at) }}
                    </span>
                  </div>

                  <h3 class="font-medium text-gray-900 dark:text-white mt-1">{{ notification.title }}</h3>

                  <p v-if="notification.message" class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {{ truncateMessage(notification.message) }}
                    <button
                      v-if="notification.message.length > 150"
                      @click="toggleExpanded(notification.id)"
                      class="text-blue-600 dark:text-blue-400 hover:underline text-xs ml-1"
                    >
                      {{ expandedIds.includes(notification.id) ? 'Show less' : 'Show more' }}
                    </button>
                  </p>

                  <div class="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                    <span v-if="notification.category" class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
                      {{ notification.category }}
                    </span>
                    <span class="px-2 py-0.5 rounded" :class="getTypeBadge(notification.notification_type)">
                      {{ notification.notification_type }}
                    </span>
                    <span v-if="notification.status === 'acknowledged'" class="flex items-center gap-1 text-green-600 dark:text-green-400">
                      <CheckIcon class="w-3 h-3" />
                      Acknowledged
                    </span>
                    <span v-if="notification.status === 'dismissed'" class="text-gray-400 dark:text-gray-500">
                      Dismissed
                    </span>
                  </div>

                  <!-- Metadata (expandable) -->
                  <div v-if="notification.metadata && expandedIds.includes(notification.id)" class="mt-3 p-2 bg-gray-50 dark:bg-gray-700 rounded text-xs font-mono overflow-x-auto">
                    <pre>{{ JSON.stringify(notification.metadata, null, 2) }}</pre>
                  </div>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-2 flex-shrink-0">
                  <span
                    class="px-2 py-1 text-xs font-medium rounded capitalize"
                    :class="getStatusBadge(notification.status)"
                  >
                    {{ notification.status }}
                  </span>

                  <button
                    v-if="notification.status === 'pending'"
                    @click="acknowledge(notification.id)"
                    class="px-3 py-1.5 text-xs font-medium text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded hover:bg-green-200 dark:hover:bg-green-900/50"
                    title="Acknowledge"
                  >
                    <CheckIcon class="w-4 h-4" />
                  </button>

                  <button
                    v-if="notification.status !== 'dismissed'"
                    @click="dismiss(notification.id)"
                    class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-600"
                    title="Dismiss"
                  >
                    <XMarkIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-if="displayedNotifications.length === 0 && !loading" class="px-6 py-12 text-center">
              <InboxIcon class="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
              <p class="text-lg font-medium text-gray-900 dark:text-white">
                {{ hasActiveFilters ? 'No matching events' : 'No events yet' }}
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {{ hasActiveFilters ? 'Try adjusting your filters' : 'Notifications from your agents will appear here when they send them.' }}
              </p>
              <button
                v-if="hasActiveFilters"
                @click="clearFilters"
                class="mt-4 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
              >
                Clear all filters
              </button>
            </div>
          </div>

          <!-- Load More -->
          <div v-if="notificationsStore.hasMore && displayedNotifications.length > 0" class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="loadMore"
              :disabled="loading"
              class="w-full py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg"
            >
              {{ loading ? 'Loading...' : 'Load more' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useNotificationsStore } from '../stores/notifications'
import NavBar from '../components/NavBar.vue'
import {
  ArrowPathIcon,
  XMarkIcon,
  CheckIcon,
  InboxIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ChartBarIcon,
  CheckCircleIcon,
  QuestionMarkCircleIcon,
  BellIcon,
} from '@heroicons/vue/24/outline'

const notificationsStore = useNotificationsStore()

// State
const loading = ref(false)
const statusFilter = ref('pending')
const priorityFilter = ref('')
const agentFilter = ref('')
const typeFilter = ref('')
const showDismissed = ref(false)
const expandedIds = ref([])

// Computed
const hasActiveFilters = computed(() => {
  return statusFilter.value !== 'pending' ||
         priorityFilter.value !== '' ||
         agentFilter.value !== '' ||
         typeFilter.value !== '' ||
         showDismissed.value
})

const availableAgents = computed(() => {
  const agents = new Set()
  notificationsStore.notifications.forEach(n => agents.add(n.agent_name))
  return Array.from(agents).sort()
})

const displayedNotifications = computed(() => {
  let result = [...notificationsStore.notifications]

  // Filter by type (client-side, not in API)
  if (typeFilter.value) {
    result = result.filter(n => n.notification_type === typeFilter.value)
  }

  // Filter out dismissed unless showing
  if (!showDismissed.value) {
    result = result.filter(n => n.status !== 'dismissed')
  }

  return result
})

const acknowledgedCount = computed(() => {
  return notificationsStore.notifications.filter(n => n.status === 'acknowledged').length
})

const allSelected = computed(() => {
  return displayedNotifications.value.length > 0 &&
         displayedNotifications.value.every(n => notificationsStore.selectedIds.includes(n.id))
})

// Lifecycle
onMounted(() => {
  fetchNotifications()
})

// Methods
async function fetchNotifications() {
  loading.value = true
  try {
    await notificationsStore.fetchNotifications({
      status: statusFilter.value || undefined,
      priority: priorityFilter.value || undefined,
      agentName: agentFilter.value || undefined,
      offset: 0,
    })
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  notificationsStore.setFilters({
    status: statusFilter.value,
    priority: priorityFilter.value,
    agentName: agentFilter.value,
    showDismissed: showDismissed.value,
  })
  fetchNotifications()
}

function clearFilters() {
  statusFilter.value = 'pending'
  priorityFilter.value = ''
  agentFilter.value = ''
  typeFilter.value = ''
  showDismissed.value = false
  notificationsStore.clearFilters()
  fetchNotifications()
}

async function acknowledge(notificationId) {
  try {
    await notificationsStore.acknowledgeNotification(notificationId)
  } catch (err) {
    console.error('Failed to acknowledge notification:', err)
  }
}

async function dismiss(notificationId) {
  try {
    await notificationsStore.dismissNotification(notificationId)
  } catch (err) {
    console.error('Failed to dismiss notification:', err)
  }
}

async function bulkAcknowledge() {
  try {
    await notificationsStore.bulkAcknowledge(notificationsStore.selectedIds)
  } catch (err) {
    console.error('Failed to bulk acknowledge:', err)
  }
}

async function bulkDismiss() {
  try {
    await notificationsStore.bulkDismiss(notificationsStore.selectedIds)
  } catch (err) {
    console.error('Failed to bulk dismiss:', err)
  }
}

function loadMore() {
  notificationsStore.loadMore()
}

function toggleSelectAll() {
  if (allSelected.value) {
    notificationsStore.clearSelection()
  } else {
    displayedNotifications.value.forEach(n => {
      if (!notificationsStore.selectedIds.includes(n.id)) {
        notificationsStore.toggleSelected(n.id)
      }
    })
  }
}

function toggleExpanded(notificationId) {
  const index = expandedIds.value.indexOf(notificationId)
  if (index === -1) {
    expandedIds.value.push(notificationId)
  } else {
    expandedIds.value.splice(index, 1)
  }
}

function truncateMessage(message) {
  if (!message) return ''
  const id = expandedIds.value.find(id => notificationsStore.notifications.find(n => n.id === id && n.message === message))
  if (id) return message
  return message.length > 150 ? message.substring(0, 150) + '...' : message
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

function getTypeIcon(type) {
  const icons = {
    alert: ExclamationTriangleIcon,
    info: InformationCircleIcon,
    status: ChartBarIcon,
    completion: CheckCircleIcon,
    question: QuestionMarkCircleIcon,
  }
  return icons[type] || BellIcon
}

function getPriorityIconBg(priority) {
  const classes = {
    urgent: 'bg-red-100 dark:bg-red-900/30',
    high: 'bg-orange-100 dark:bg-orange-900/30',
    normal: 'bg-blue-100 dark:bg-blue-900/30',
    low: 'bg-gray-100 dark:bg-gray-700',
  }
  return classes[priority] || 'bg-gray-100 dark:bg-gray-700'
}

function getPriorityIconColor(priority) {
  const classes = {
    urgent: 'text-red-600 dark:text-red-400',
    high: 'text-orange-600 dark:text-orange-400',
    normal: 'text-blue-600 dark:text-blue-400',
    low: 'text-gray-600 dark:text-gray-400',
  }
  return classes[priority] || 'text-gray-600 dark:text-gray-400'
}

function getPriorityBadge(priority) {
  const classes = {
    urgent: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    high: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
    normal: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    low: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
  }
  return classes[priority] || 'bg-gray-100 text-gray-700'
}

function getTypeBadge(type) {
  const classes = {
    alert: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    info: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    status: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
    completion: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    question: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  }
  return classes[type] || 'bg-gray-100 text-gray-700'
}

function getStatusBadge(status) {
  const classes = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    acknowledged: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    dismissed: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}
</script>

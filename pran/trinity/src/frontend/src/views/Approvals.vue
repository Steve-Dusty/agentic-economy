<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav :pending-approvals="pendingCount" />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 sm:px-0">
        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Approvals</h1>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Review and manage pending approval requests
            </p>
          </div>

          <div class="flex items-center gap-3">
            <button
              @click="loadApprovals"
              :disabled="loading"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': loading }" />
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
                @change="loadApprovals"
                class="w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 bg-white dark:bg-gray-700 dark:text-gray-200 border"
              >
                <option value="">All Status</option>
                <option value="pending">⏳ Pending</option>
                <option value="approved">✅ Approved</option>
                <option value="rejected">❌ Rejected</option>
              </select>
            </div>

            <!-- Clear filters -->
            <div class="flex items-end">
              <button
                v-if="statusFilter"
                @click="clearFilters"
                class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <!-- Stats cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.total }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-amber-600 dark:text-amber-400">{{ stats.pending }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Pending</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ stats.approved }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Approved</div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="text-2xl font-bold text-red-600 dark:text-red-400">{{ stats.rejected }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Rejected</div>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading && approvals.length === 0" class="flex justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 dark:border-indigo-400"></div>
        </div>

        <!-- Empty state -->
        <div v-else-if="approvals.length === 0" class="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <ClipboardDocumentCheckIcon class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
          <h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-white">No approvals found</h3>
          <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {{ statusFilter ? 'Try changing the filter' : 'There are no approval requests yet' }}
          </p>
        </div>

        <!-- Approvals list -->
        <div v-else class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Title
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Step
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Created
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Deadline
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="approval in approvals"
                :key="approval.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="getStatusClasses(approval.status)"
                  >
                    {{ getStatusIcon(approval.status) }} {{ approval.status }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div class="text-sm font-medium text-gray-900 dark:text-white">
                    {{ approval.title }}
                  </div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">
                    {{ approval.description || 'No description' }}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ approval.step_id }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(approval.created_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <span v-if="approval.deadline" :class="isOverdue(approval.deadline) ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'">
                    {{ formatDate(approval.deadline) }}
                    <span v-if="isOverdue(approval.deadline)" class="ml-1 text-red-600 dark:text-red-400">(Overdue)</span>
                  </span>
                  <span v-else class="text-gray-400 dark:text-gray-500">-</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end gap-2">
                    <!-- View execution button -->
                    <router-link
                      :to="`/executions/${approval.execution_id}`"
                      class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
                      title="View Execution"
                    >
                      <ArrowTopRightOnSquareIcon class="w-5 h-5" />
                    </router-link>

                    <!-- Approve button (only for pending) -->
                    <button
                      v-if="approval.status === 'pending'"
                      @click="approveRequest(approval)"
                      :disabled="actionLoading === approval.id"
                      class="text-green-600 dark:text-green-400 hover:text-green-900 dark:hover:text-green-300 disabled:opacity-50"
                      title="Approve"
                    >
                      <CheckCircleIcon class="w-5 h-5" />
                    </button>

                    <!-- Reject button (only for pending) -->
                    <button
                      v-if="approval.status === 'pending'"
                      @click="showRejectModal(approval)"
                      :disabled="actionLoading === approval.id"
                      class="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 disabled:opacity-50"
                      title="Reject"
                    >
                      <XCircleIcon class="w-5 h-5" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>

    <!-- Reject Modal -->
    <div
      v-if="rejectingApproval"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="rejectingApproval = null"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Reject Approval
        </h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Please provide a reason for rejection:
        </p>
        <textarea
          v-model="rejectReason"
          rows="3"
          class="w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-red-500 focus:ring-red-500 text-sm bg-white dark:bg-gray-700 dark:text-gray-200"
          placeholder="Rejection reason (required)"
        ></textarea>
        <div class="flex justify-end gap-3 mt-4">
          <button
            @click="rejectingApproval = null; rejectReason = ''"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            @click="confirmReject"
            :disabled="!rejectReason.trim() || actionLoading"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-gray-400"
          >
            {{ actionLoading ? 'Rejecting...' : 'Reject' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import {
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClipboardDocumentCheckIcon
} from '@heroicons/vue/24/outline'

const router = useRouter()

// State
const loading = ref(false)
const approvals = ref([])
const statusFilter = ref('')
const actionLoading = ref(null)
const rejectingApproval = ref(null)
const rejectReason = ref('')

// Computed
const pendingCount = computed(() => approvals.value.filter(a => a.status === 'pending').length)

const stats = computed(() => {
  const all = approvals.value
  return {
    total: all.length,
    pending: all.filter(a => a.status === 'pending').length,
    approved: all.filter(a => a.status === 'approved').length,
    rejected: all.filter(a => a.status === 'rejected').length,
  }
})

// Methods
async function loadApprovals() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (statusFilter.value) params.append('status', statusFilter.value)

    const response = await fetch(`/api/approvals?${params}`)
    if (response.ok) {
      const data = await response.json()
      // Sort by created_at descending (newest first)
      approvals.value = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    }
  } catch (error) {
    console.error('Failed to load approvals:', error)
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  statusFilter.value = ''
  loadApprovals()
}

function getStatusIcon(status) {
  switch (status) {
    case 'pending': return '⏳'
    case 'approved': return '✅'
    case 'rejected': return '❌'
    case 'expired': return '⏰'
    default: return '❓'
  }
}

function getStatusClasses(status) {
  switch (status) {
    case 'pending':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
    case 'approved':
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
    case 'rejected':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
    case 'expired':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function isOverdue(deadline) {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

async function approveRequest(approval) {
  actionLoading.value = approval.id
  try {
    const response = await fetch(`/api/approvals/${approval.id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: '' })
    })
    if (response.ok) {
      await loadApprovals()
    } else {
      const error = await response.json()
      alert('Failed to approve: ' + (error.detail || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to approve:', error)
    alert('Failed to approve: ' + error.message)
  } finally {
    actionLoading.value = null
  }
}

function showRejectModal(approval) {
  rejectingApproval.value = approval
  rejectReason.value = ''
}

async function confirmReject() {
  if (!rejectingApproval.value || !rejectReason.value.trim()) return

  actionLoading.value = rejectingApproval.value.id
  try {
    const response = await fetch(`/api/approvals/${rejectingApproval.value.id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: rejectReason.value })
    })
    if (response.ok) {
      rejectingApproval.value = null
      rejectReason.value = ''
      await loadApprovals()
    } else {
      const error = await response.json()
      alert('Failed to reject: ' + (error.detail || 'Unknown error'))
    }
  } catch (error) {
    console.error('Failed to reject:', error)
    alert('Failed to reject: ' + error.message)
  } finally {
    actionLoading.value = null
  }
}

// Lifecycle
onMounted(() => {
  loadApprovals()
})
</script>

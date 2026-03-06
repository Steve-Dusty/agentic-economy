<template>
  <div class="p-6 space-y-8">
    <!-- Team Sharing Section -->
    <div>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Team Sharing</h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Share this agent with team members by entering their email address.
      </p>

      <!-- Share Form -->
      <form @submit.prevent="shareWithUser" class="flex items-center space-x-3">
        <input
          v-model="shareEmail"
          type="email"
          placeholder="user@example.com"
          :disabled="shareLoading"
          class="flex-1 max-w-md px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100 dark:disabled:bg-gray-900"
        />
        <button
          type="submit"
          :disabled="shareLoading || !shareEmail.trim()"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed"
        >
          <svg v-if="shareLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ shareLoading ? 'Sharing...' : 'Share' }}
        </button>
      </form>

      <!-- Share Error/Success Message -->
      <div v-if="shareMessage" :class="[
        'mt-3 p-3 rounded-lg text-sm',
        shareMessage.type === 'success' ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
      ]">
        {{ shareMessage.text }}
      </div>

      <!-- Shared Users List -->
      <div class="mt-4">
        <div v-if="!shares || shares.length === 0" class="text-center py-6 text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
          <svg class="mx-auto h-10 w-10 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <p class="mt-2 text-sm">Not shared with anyone</p>
        </div>

        <ul v-else class="divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg">
          <li v-for="share in shares" :key="share.id" class="px-4 py-3 flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="flex-shrink-0 h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                <span class="text-sm font-medium text-gray-600 dark:text-gray-300">
                  {{ (share.shared_with_name || share.shared_with_email || '?')[0].toUpperCase() }}
                </span>
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {{ share.shared_with_name || share.shared_with_email }}
                </p>
                <p v-if="share.shared_with_name" class="text-xs text-gray-500 dark:text-gray-400">
                  {{ share.shared_with_email }}
                </p>
              </div>
            </div>
            <button
              @click="removeShare(share.shared_with_email)"
              :disabled="unshareLoading === share.shared_with_email"
              class="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm font-medium disabled:opacity-50"
            >
              <span v-if="unshareLoading === share.shared_with_email">Removing...</span>
              <span v-else>Remove</span>
            </button>
          </li>
        </ul>
      </div>
    </div>

    <!-- Divider -->
    <div class="border-t border-gray-200 dark:border-gray-700"></div>

    <!-- Public Links Section -->
    <PublicLinksPanel :agent-name="agentName" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAgentsStore } from '../stores/agents'
import { useAgentSharing } from '../composables/useAgentSharing'
import { useNotification } from '../composables'
import PublicLinksPanel from './PublicLinksPanel.vue'

const props = defineProps({
  agentName: {
    type: String,
    required: true
  },
  shares: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['agent-updated'])

const agentsStore = useAgentsStore()
const { showNotification } = useNotification()

// Create agent ref for composable
const agent = ref({ name: props.agentName, shares: props.shares })

// Update agent ref when props change
watch(() => [props.agentName, props.shares], () => {
  agent.value = { name: props.agentName, shares: props.shares }
}, { deep: true })

// Reload agent function for composable
const loadAgent = () => {
  emit('agent-updated')
}

const {
  shareEmail,
  shareLoading,
  shareMessage,
  unshareLoading,
  shareWithUser,
  removeShare
} = useAgentSharing(agent, agentsStore, loadAgent, showNotification)
</script>

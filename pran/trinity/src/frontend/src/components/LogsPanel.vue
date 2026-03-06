<template>
  <div class="p-6">
    <div
      ref="logsContainer"
      @scroll="handleLogsScroll"
      class="bg-gray-900 text-gray-300 p-4 rounded-lg h-96 overflow-auto mb-4"
    >
      <pre class="text-sm font-mono whitespace-pre-wrap">{{ logs || 'No logs available' }}</pre>
    </div>
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-4">
        <button
          @click="refreshLogs"
          class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Refresh Logs
        </button>
        <label class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
          <input type="checkbox" v-model="autoRefreshLogs" class="rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700" />
          <span>Auto-refresh (10s)</span>
        </label>
      </div>
      <div class="flex items-center space-x-2">
        <label class="text-sm text-gray-600 dark:text-gray-400">Lines:</label>
        <select v-model="logLines" @change="refreshLogs" class="border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm bg-white dark:bg-gray-800 dark:text-gray-200">
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="200">200</option>
          <option value="500">500</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useAgentsStore } from '../stores/agents'
import { useAgentLogs } from '../composables/useAgentLogs'

const props = defineProps({
  agentName: {
    type: String,
    required: true
  },
  agentStatus: {
    type: String,
    default: 'stopped'
  }
})

const agentsStore = useAgentsStore()

// Create a computed agent ref for the composable
const agent = computed(() => ({
  name: props.agentName,
  status: props.agentStatus
}))

const {
  logs,
  logLines,
  autoRefreshLogs,
  logsContainer,
  refreshLogs,
  handleLogsScroll
} = useAgentLogs(agent, agentsStore)

// Reload when agent name changes (navigating between agents)
watch(() => props.agentName, (newName, oldName) => {
  if (newName && newName !== oldName) {
    refreshLogs()
  }
})

// Load logs on mount
onMounted(() => {
  refreshLogs()
})
</script>

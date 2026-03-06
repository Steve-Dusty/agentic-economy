import { ref } from 'vue'
import { useAgentsStore } from '../stores/agents'
import { useNotificationsStore } from '../stores/notifications'

const ws = ref(null)
const isConnected = ref(false)

export function useWebSocket() {
  const agentsStore = useAgentsStore()
  const notificationsStore = useNotificationsStore()

  const connect = () => {
    if (ws.value) return

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      isConnected.value = true
      console.log('WebSocket connected')
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
      ws.value = null
      console.log('WebSocket disconnected')
      // Attempt to reconnect after 5 seconds
      setTimeout(connect, 5000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      isConnected.value = false
    }
  }

  const handleMessage = (data) => {
    switch (data.event) {
      case 'agent_created':
        // Add to list (createAgent() no longer pushes to avoid race conditions)
        // Still check for duplicates in case of reconnection/replay
        if (!agentsStore.agents.find(a => a.name === data.data.name)) {
          agentsStore.agents.push(data.data)
        }
        break
      case 'agent_deleted':
        agentsStore.agents = agentsStore.agents.filter(a => a.name !== data.data.name)
        break
      case 'agent_started':
        agentsStore.updateAgentStatus(data.data.name, 'running')
        break
      case 'agent_stopped':
        agentsStore.updateAgentStatus(data.data.name, 'stopped')
        break
      case 'agent_notification':
        // Real-time notification from an agent
        // The WebSocket event contains: notification_id, agent_name, notification_type, title, priority, category, timestamp
        // We update the pending count and can add to list if we have full details
        notificationsStore.fetchPendingCount()
        // If we have enough data, we can add a partial notification
        if (data.notification_id && data.agent_name && data.title) {
          notificationsStore.addNotification({
            id: data.notification_id,
            agent_name: data.agent_name,
            notification_type: data.notification_type || 'info',
            title: data.title,
            priority: data.priority || 'normal',
            category: data.category || null,
            status: 'pending',
            created_at: data.timestamp || new Date().toISOString(),
            message: null,
            metadata: null,
          })
        }
        break
      default:
        console.log('Unknown WebSocket event:', data.event)
    }
  }

  return {
    connect,
    disconnect,
    isConnected
  }
}

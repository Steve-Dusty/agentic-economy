import { ref } from 'vue'

/**
 * Composable for agent sharing functionality
 * Manages sharing agents with other users
 */
export function useAgentSharing(agentRef, agentsStore, loadAgent, showNotification) {
  const shareEmail = ref('')
  const shareLoading = ref(false)
  const shareMessage = ref(null)
  const unshareLoading = ref(null)

  const shareWithUser = async () => {
    if (!agentRef.value || !shareEmail.value.trim()) return

    shareLoading.value = true
    shareMessage.value = null

    try {
      const result = await agentsStore.shareAgent(agentRef.value.name, shareEmail.value.trim())
      shareMessage.value = {
        type: 'success',
        text: `Agent shared with ${shareEmail.value.trim()}`
      }
      shareEmail.value = ''
      // Refresh agent data to update shares list
      await loadAgent()
    } catch (err) {
      console.error('Failed to share agent:', err)
      shareMessage.value = {
        type: 'error',
        text: err.response?.data?.detail || err.message || 'Failed to share agent'
      }
    } finally {
      shareLoading.value = false
      // Clear message after 5 seconds
      setTimeout(() => {
        shareMessage.value = null
      }, 5000)
    }
  }

  const removeShare = async (email) => {
    if (!agentRef.value) return

    unshareLoading.value = email

    try {
      await agentsStore.unshareAgent(agentRef.value.name, email)
      showNotification(`Sharing removed for ${email}`, 'success')
      // Refresh agent data to update shares list
      await loadAgent()
    } catch (err) {
      console.error('Failed to remove share:', err)
      showNotification(err.response?.data?.detail || 'Failed to remove sharing', 'error')
    } finally {
      unshareLoading.value = null
    }
  }

  return {
    shareEmail,
    shareLoading,
    shareMessage,
    unshareLoading,
    shareWithUser,
    removeShare
  }
}

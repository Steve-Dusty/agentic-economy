import { ref, computed } from 'vue'

/**
 * Composable for agent-to-agent permissions (Phase 9.10)
 * Manages which agents can communicate with this agent
 */
export function useAgentPermissions(agentRef, agentsStore) {
  const availableAgents = ref([])
  const permissionsLoading = ref(false)
  const permissionsSaving = ref(false)
  const permissionsDirty = ref(false)
  const permissionsMessage = ref(null)

  const permittedAgentsCount = computed(() =>
    availableAgents.value.filter(a => a.permitted).length
  )

  const loadPermissions = async () => {
    if (!agentRef.value) return

    permissionsLoading.value = true
    permissionsMessage.value = null

    try {
      const response = await agentsStore.getAgentPermissions(agentRef.value.name)
      availableAgents.value = response.available_agents || []
      permissionsDirty.value = false
    } catch (err) {
      console.error('Failed to load permissions:', err)
      permissionsMessage.value = {
        type: 'error',
        text: err.response?.data?.detail || 'Failed to load permissions'
      }
    } finally {
      permissionsLoading.value = false
    }
  }

  const savePermissions = async () => {
    if (!agentRef.value || !permissionsDirty.value) return

    permissionsSaving.value = true
    permissionsMessage.value = null

    const permittedAgentNames = availableAgents.value
      .filter(a => a.permitted)
      .map(a => a.name)

    try {
      await agentsStore.setAgentPermissions(agentRef.value.name, permittedAgentNames)
      permissionsDirty.value = false
      permissionsMessage.value = {
        type: 'success',
        text: `Permissions saved (${permittedAgentNames.length} agents allowed)`
      }
      setTimeout(() => { permissionsMessage.value = null }, 3000)
    } catch (err) {
      console.error('Failed to save permissions:', err)
      permissionsMessage.value = {
        type: 'error',
        text: err.response?.data?.detail || 'Failed to save permissions'
      }
    } finally {
      permissionsSaving.value = false
    }
  }

  const allowAllAgents = () => {
    availableAgents.value.forEach(a => { a.permitted = true })
    permissionsDirty.value = true
  }

  const allowNoAgents = () => {
    availableAgents.value.forEach(a => { a.permitted = false })
    permissionsDirty.value = true
  }

  const markDirty = () => {
    permissionsDirty.value = true
  }

  return {
    availableAgents,
    permissionsLoading,
    permissionsSaving,
    permissionsDirty,
    permissionsMessage,
    permittedAgentsCount,
    loadPermissions,
    savePermissions,
    allowAllAgents,
    allowNoAgents,
    markDirty
  }
}

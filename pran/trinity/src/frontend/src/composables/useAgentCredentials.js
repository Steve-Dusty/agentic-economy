import { ref } from 'vue'

/**
 * Composable for agent credential management
 *
 * This uses the new simplified credential system (CRED-002):
 * - Direct file injection (no Redis assignments)
 * - Export/import via encrypted .credentials.enc file
 * - Quick inject for .env format credentials
 */
export function useAgentCredentials(agentRef, agentsStore, showNotification) {
  // Credential status
  const credentialStatus = ref(null)

  // Loading states
  const loading = ref(false)
  const injecting = ref(false)
  const exporting = ref(false)
  const importing = ref(false)

  // Quick-add functionality
  const quickAddText = ref('')
  const quickAddLoading = ref(false)
  const quickAddResult = ref(null)

  /**
   * Load credential status from agent
   */
  const loadCredentials = async () => {
    if (!agentRef.value) return
    if (agentRef.value.status !== 'running') {
      credentialStatus.value = null
      return
    }

    loading.value = true
    try {
      credentialStatus.value = await agentsStore.getCredentialStatus(agentRef.value.name)
    } catch (err) {
      console.error('Failed to load credential status:', err)
      credentialStatus.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Inject credential files directly into agent
   */
  const injectFiles = async (files) => {
    if (!agentRef.value || agentRef.value.status !== 'running') return

    injecting.value = true
    try {
      const result = await agentsStore.injectCredentials(agentRef.value.name, files)
      await loadCredentials()
      if (showNotification) {
        showNotification(`Injected ${result.files_written.length} file(s)`, 'success')
      }
      return result
    } catch (err) {
      console.error('Failed to inject credentials:', err)
      if (showNotification) {
        showNotification(err.response?.data?.detail || 'Failed to inject credentials', 'error')
      }
      throw err
    } finally {
      injecting.value = false
    }
  }

  /**
   * Export credentials to encrypted file
   */
  const exportToGit = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return

    exporting.value = true
    try {
      const result = await agentsStore.exportCredentials(agentRef.value.name)
      await loadCredentials()
      if (showNotification) {
        showNotification(`Exported ${result.files_exported} file(s) to .credentials.enc`, 'success')
      }
      return result
    } catch (err) {
      console.error('Failed to export credentials:', err)
      if (showNotification) {
        showNotification(err.response?.data?.detail || 'Failed to export credentials', 'error')
      }
      throw err
    } finally {
      exporting.value = false
    }
  }

  /**
   * Import credentials from encrypted file
   */
  const importFromGit = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return

    importing.value = true
    try {
      const result = await agentsStore.importCredentials(agentRef.value.name)
      await loadCredentials()
      if (showNotification) {
        showNotification(`Imported ${result.files_imported.length} file(s)`, 'success')
      }
      return result
    } catch (err) {
      console.error('Failed to import credentials:', err)
      if (showNotification) {
        showNotification(err.response?.data?.detail || 'Failed to import credentials', 'error')
      }
      throw err
    } finally {
      importing.value = false
    }
  }

  /**
   * Count credentials in .env-style text
   */
  const countCredentials = (text) => {
    if (!text) return 0
    let count = 0
    for (const line of text.split('\n')) {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        count++
      }
    }
    return count
  }

  /**
   * Parse .env-style text to key-value pairs
   */
  const parseEnvText = (text) => {
    const credentials = {}
    for (const line of text.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      const eqIndex = trimmed.indexOf('=')
      if (eqIndex > 0) {
        const key = trimmed.substring(0, eqIndex).trim()
        let value = trimmed.substring(eqIndex + 1).trim()
        // Remove surrounding quotes
        if ((value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))) {
          value = value.slice(1, -1)
        }
        if (key) {
          credentials[key] = value
        }
      }
    }
    return credentials
  }

  /**
   * Format credentials as .env content
   */
  const formatEnvContent = (credentials) => {
    const lines = ['# Credential file - managed by Trinity', '']
    for (const [key, value] of Object.entries(credentials)) {
      const escapedValue = String(value).replace(/"/g, '\\"')
      lines.push(`${key}="${escapedValue}"`)
    }
    return lines.join('\n') + '\n'
  }

  /**
   * Quick-add credentials from .env-style text
   */
  const quickAddCredentials = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    if (!quickAddText.value.trim()) return

    quickAddLoading.value = true
    quickAddResult.value = null

    try {
      const newCredentials = parseEnvText(quickAddText.value)
      const credCount = Object.keys(newCredentials).length

      if (credCount === 0) {
        quickAddResult.value = {
          success: false,
          message: 'No valid KEY=VALUE pairs found'
        }
        return
      }

      // Get existing .env content and merge
      let existingEnv = {}
      try {
        const content = await agentsStore.downloadAgentFile(
          agentRef.value.name,
          '/home/developer/.env'
        )
        existingEnv = parseEnvText(content)
      } catch (e) {
        // File doesn't exist, start fresh
      }

      // Merge new credentials (overwrite existing keys)
      const merged = { ...existingEnv, ...newCredentials }
      const envContent = formatEnvContent(merged)

      // Inject the merged .env file
      await agentsStore.injectCredentials(agentRef.value.name, {
        '.env': envContent
      })

      quickAddResult.value = {
        success: true,
        message: `Injected ${credCount} credential(s)`,
        credentials: Object.keys(newCredentials)
      }
      quickAddText.value = ''
      await loadCredentials()

      if (showNotification) {
        showNotification('Credentials added', 'success')
      }
    } catch (err) {
      console.error('Quick add failed:', err)
      quickAddResult.value = {
        success: false,
        message: err.response?.data?.detail || err.message || 'Failed to add credentials'
      }
    } finally {
      quickAddLoading.value = false
    }
  }

  // Legacy API aliases for backward compatibility
  const assignedCredentials = ref([])
  const availableCredentials = ref([])
  const hotReloadText = quickAddText
  const hotReloadLoading = quickAddLoading
  const hotReloadResult = quickAddResult
  const performHotReload = quickAddCredentials

  return {
    // New simplified API
    credentialStatus,
    loading,
    injecting,
    exporting,
    importing,
    quickAddText,
    quickAddLoading,
    quickAddResult,
    loadCredentials,
    injectFiles,
    exportToGit,
    importFromGit,
    quickAddCredentials,
    countCredentials,

    // Legacy API for backward compatibility
    assignedCredentials,
    availableCredentials,
    applying: injecting,
    hasChanges: ref(false),
    hotReloadText,
    hotReloadLoading,
    hotReloadResult,
    performHotReload,
    assignCredential: async () => {},
    unassignCredential: async () => {},
    applyToAgent: async () => {}
  }
}

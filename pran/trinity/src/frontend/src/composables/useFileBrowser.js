import { ref, computed } from 'vue'

/**
 * Composable for file tree loading and operations
 * Manages file browser functionality
 */
export function useFileBrowser(agentRef, agentsStore, showNotification) {
  const fileTree = ref([])
  const filesLoading = ref(false)
  const filesError = ref(null)
  const fileSearchQuery = ref('')
  const expandedFolders = ref(new Set())
  const totalFileCount = ref(0)

  const filteredFileTree = computed(() => {
    if (!fileSearchQuery.value) return fileTree.value

    const query = fileSearchQuery.value.toLowerCase()

    const filterTree = (items) => {
      return items.filter(item => {
        if (item.type === 'file') {
          return item.name.toLowerCase().includes(query)
        } else {
          // For directories, include if name matches or has matching children
          const nameMatches = item.name.toLowerCase().includes(query)
          const filteredChildren = filterTree(item.children || [])
          if (nameMatches || filteredChildren.length > 0) {
            // Auto-expand folders when searching
            if (fileSearchQuery.value) {
              expandedFolders.value.add(item.path)
            }
            return true
          }
          return false
        }
      }).map(item => {
        if (item.type === 'directory') {
          return {
            ...item,
            children: filterTree(item.children || [])
          }
        }
        return item
      })
    }

    return filterTree(fileTree.value)
  })

  const loadFiles = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    filesLoading.value = true
    filesError.value = null
    try {
      const response = await agentsStore.listAgentFiles(agentRef.value.name)
      fileTree.value = response.tree || []
      totalFileCount.value = response.total_files || 0
    } catch (err) {
      console.error('Failed to load files:', err)
      filesError.value = err.response?.data?.detail || 'Failed to load files'
    } finally {
      filesLoading.value = false
    }
  }

  const toggleFolder = (path) => {
    if (expandedFolders.value.has(path)) {
      expandedFolders.value.delete(path)
    } else {
      expandedFolders.value.add(path)
    }
    // Trigger reactivity
    expandedFolders.value = new Set(expandedFolders.value)
  }

  const downloadFile = async (filePath, fileName) => {
    if (!agentRef.value) return
    try {
      const content = await agentsStore.downloadAgentFile(agentRef.value.name, filePath)
      // Create blob and download
      const blob = new Blob([content], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      showNotification(`Downloaded ${fileName}`, 'success')
    } catch (err) {
      console.error('Failed to download file:', err)
      showNotification(err.response?.data?.detail || 'Failed to download file', 'error')
    }
  }

  return {
    fileTree,
    filesLoading,
    filesError,
    fileSearchQuery,
    expandedFolders,
    totalFileCount,
    filteredFileTree,
    loadFiles,
    toggleFolder,
    downloadFile
  }
}

/**
 * Process Definitions Store
 * 
 * Pinia store for managing process definitions state.
 * Part of the Process-Driven Platform feature.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useProcessesStore = defineStore('processes', () => {
  // State
  const processes = ref([])
  const loading = ref(false)
  const error = ref(null)
  const sortBy = ref('created_desc')

  // Getters
  const sortedProcesses = computed(() => {
    const list = [...processes.value]
    
    switch (sortBy.value) {
      case 'created_desc':
        return list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      case 'created_asc':
        return list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      case 'name_asc':
        return list.sort((a, b) => a.name.localeCompare(b.name))
      case 'name_desc':
        return list.sort((a, b) => b.name.localeCompare(a.name))
      case 'status':
        return list.sort((a, b) => {
          const order = { published: 0, draft: 1, archived: 2 }
          return (order[a.status] || 3) - (order[b.status] || 3)
        })
      default:
        return list
    }
  })

  const publishedProcesses = computed(() => 
    processes.value.filter(p => p.status === 'published')
  )

  const draftProcesses = computed(() => 
    processes.value.filter(p => p.status === 'draft')
  )

  // Actions
  async function fetchProcesses() {
    loading.value = true
    error.value = null
    
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/processes', {
        headers: { Authorization: `Bearer ${token}` }
      })
      processes.value = response.data.processes || []
    } catch (err) {
      console.error('Failed to fetch processes:', err)
      error.value = err.response?.data?.detail || 'Failed to load processes'
      processes.value = []
    } finally {
      loading.value = false
    }
  }

  async function getProcess(id) {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/processes/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return response.data
  }

  async function createProcess(yamlContent) {
    const token = localStorage.getItem('token')
    const response = await axios.post('/api/processes', 
      { yaml_content: yamlContent },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    await fetchProcesses()
    return response.data
  }

  async function updateProcess(id, yamlContent) {
    const token = localStorage.getItem('token')
    const response = await axios.put(`/api/processes/${id}`,
      { yaml_content: yamlContent },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    await fetchProcesses()
    return response.data
  }

  async function deleteProcess(id) {
    const token = localStorage.getItem('token')
    await axios.delete(`/api/processes/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await fetchProcesses()
  }

  async function publishProcess(id) {
    const token = localStorage.getItem('token')
    const response = await axios.post(`/api/processes/${id}/publish`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await fetchProcesses()
    return response.data
  }

  async function archiveProcess(id) {
    const token = localStorage.getItem('token')
    const response = await axios.post(`/api/processes/${id}/archive`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await fetchProcesses()
    return response.data
  }

  async function createNewVersion(id) {
    const token = localStorage.getItem('token')
    const response = await axios.post(`/api/processes/${id}/new-version`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await fetchProcesses()
    return response.data
  }

  async function validateYaml(yamlContent) {
    const token = localStorage.getItem('token')
    const response = await axios.post('/api/processes/validate',
      { yaml_content: yamlContent },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  }

  async function executeProcess(id, inputData = {}) {
    const token = localStorage.getItem('token')
    const response = await axios.post(`/api/executions/processes/${id}/execute`,
      { input_data: inputData },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  }

  return {
    // State
    processes,
    loading,
    error,
    sortBy,
    // Getters
    sortedProcesses,
    publishedProcesses,
    draftProcesses,
    // Actions
    fetchProcesses,
    getProcess,
    createProcess,
    updateProcess,
    deleteProcess,
    publishProcess,
    archiveProcess,
    createNewVersion,
    validateYaml,
    executeProcess,
  }
})

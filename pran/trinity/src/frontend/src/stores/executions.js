/**
 * Process Executions Store
 * 
 * Pinia store for managing process execution state.
 * Part of the Process-Driven Platform feature.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useExecutionsStore = defineStore('executions', () => {
  // State
  const executions = ref([])
  const currentExecution = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const total = ref(0)
  
  // Filters
  const filters = ref({
    status: '',
    processId: '',
    limit: 50,
    offset: 0,
  })

  // Polling
  let pollInterval = null

  // Getters
  const activeExecutions = computed(() => 
    executions.value.filter(e => e.status === 'running' || e.status === 'pending')
  )

  const completedExecutions = computed(() => 
    executions.value.filter(e => e.status === 'completed')
  )

  const failedExecutions = computed(() => 
    executions.value.filter(e => e.status === 'failed')
  )

  // Statistics
  const stats = computed(() => {
    const all = executions.value
    const completed = all.filter(e => e.status === 'completed').length
    const failed = all.filter(e => e.status === 'failed').length
    const running = all.filter(e => e.status === 'running').length
    const totalCost = all.reduce((sum, e) => {
      if (e.total_cost) {
        // Parse cost string like "$0.05 USD"
        const match = e.total_cost.match(/[\d.]+/)
        return sum + (match ? parseFloat(match[0]) : 0)
      }
      return sum
    }, 0)

    return {
      total: all.length,
      completed,
      failed,
      running,
      successRate: all.length > 0 ? Math.round((completed / (completed + failed || 1)) * 100) : 0,
      totalCost: totalCost.toFixed(2),
    }
  })

  // Actions
  async function fetchExecutions(options = {}) {
    loading.value = true
    error.value = null
    
    try {
      const token = localStorage.getItem('token')
      const params = new URLSearchParams()
      
      if (options.status || filters.value.status) {
        params.append('status', options.status || filters.value.status)
      }
      if (options.processId || filters.value.processId) {
        params.append('process_id', options.processId || filters.value.processId)
      }
      params.append('limit', options.limit || filters.value.limit)
      params.append('offset', options.offset || filters.value.offset)
      
      const response = await axios.get(`/api/executions?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      executions.value = response.data.executions || []
      total.value = response.data.total || 0
    } catch (err) {
      console.error('Failed to fetch executions:', err)
      error.value = err.response?.data?.detail || 'Failed to load executions'
      executions.value = []
    } finally {
      loading.value = false
    }
  }

  async function getExecution(id) {
    if (!id) {
      console.warn('getExecution called with no ID')
      return null
    }
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/executions/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    currentExecution.value = response.data
    return response.data
  }

  async function cancelExecution(id) {
    const token = localStorage.getItem('token')
    const response = await axios.post(`/api/executions/${id}/cancel`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await fetchExecutions()
    return response.data
  }

  async function retryExecution(id) {
    const token = localStorage.getItem('token')
    const response = await axios.post(`/api/executions/${id}/retry`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await fetchExecutions()
    return response.data
  }

  async function getStepOutput(executionId, stepId) {
    if (!executionId || !stepId) {
      console.warn('getStepOutput called with missing IDs')
      return null
    }
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/executions/${executionId}/steps/${stepId}/output`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return response.data.output
  }

  async function getExecutionEvents(id) {
    if (!id) {
      console.warn('getExecutionEvents called with no ID')
      return []
    }
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/executions/${id}/events`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    return response.data
  }

  // Polling for auto-refresh
  function startPolling(intervalMs = 30000) {
    stopPolling()
    fetchExecutions()
    pollInterval = setInterval(() => {
      fetchExecutions()
    }, intervalMs)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  // Set filters and refetch
  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    fetchExecutions()
  }

  function clearFilters() {
    filters.value = {
      status: '',
      processId: '',
      limit: 50,
      offset: 0,
    }
    fetchExecutions()
  }

  return {
    // State
    executions,
    currentExecution,
    loading,
    error,
    total,
    filters,
    // Getters
    activeExecutions,
    completedExecutions,
    failedExecutions,
    stats,
    // Actions
    fetchExecutions,
    getExecution,
    cancelExecution,
    retryExecution,
    getStepOutput,
    getExecutionEvents,
    startPolling,
    stopPolling,
    setFilters,
    clearFilters,
  }
})

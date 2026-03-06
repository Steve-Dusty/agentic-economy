/**
 * Cost Alerts Store
 *
 * Pinia store for managing cost alerts and thresholds.
 * Part of the Process-Driven Platform feature (E11-03).
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAlertsStore = defineStore('alerts', () => {
  // State
  const alerts = ref([])
  const activeCount = ref(0)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const activeAlerts = computed(() =>
    alerts.value.filter(a => a.status === 'active')
  )

  const dismissedAlerts = computed(() =>
    alerts.value.filter(a => a.status === 'dismissed')
  )

  const hasActiveAlerts = computed(() => activeCount.value > 0)

  // Actions
  async function fetchAlerts(options = {}) {
    loading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('token')
      const params = new URLSearchParams()

      if (options.status) {
        params.append('status', options.status)
      }
      if (options.processId) {
        params.append('process_id', options.processId)
      }
      params.append('limit', options.limit || 50)
      params.append('offset', options.offset || 0)

      const response = await axios.get(`/api/alerts?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      alerts.value = response.data.alerts || []
      activeCount.value = response.data.active_count || 0
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
      error.value = err.response?.data?.detail || 'Failed to load alerts'
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveCount() {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/alerts/count', {
        headers: { Authorization: `Bearer ${token}` },
      })
      activeCount.value = response.data.active_count || 0
    } catch (err) {
      console.error('Failed to fetch alert count:', err)
    }
  }

  async function dismissAlert(alertId) {
    try {
      const token = localStorage.getItem('token')
      await axios.post(`/api/alerts/${alertId}/dismiss`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      })

      // Update local state
      const alert = alerts.value.find(a => a.id === alertId)
      if (alert) {
        alert.status = 'dismissed'
        alert.dismissed_at = new Date().toISOString()
      }
      activeCount.value = Math.max(0, activeCount.value - 1)

      return true
    } catch (err) {
      console.error('Failed to dismiss alert:', err)
      throw err
    }
  }

  // Threshold management
  async function getThresholds(processId) {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/alerts/thresholds/${processId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      return response.data.thresholds || []
    } catch (err) {
      console.error('Failed to fetch thresholds:', err)
      throw err
    }
  }

  async function setThreshold(processId, thresholdType, amount, enabled = true) {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.put(
        `/api/alerts/thresholds/${processId}`,
        {
          threshold_type: thresholdType,
          amount: amount,
          enabled: enabled,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      return response.data.threshold
    } catch (err) {
      console.error('Failed to set threshold:', err)
      throw err
    }
  }

  async function deleteThreshold(processId, thresholdType) {
    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/alerts/thresholds/${processId}/${thresholdType}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      return true
    } catch (err) {
      console.error('Failed to delete threshold:', err)
      throw err
    }
  }

  // Start polling for active alerts (for badge updates)
  let pollInterval = null

  function startPolling(intervalMs = 60000) {
    stopPolling()
    fetchActiveCount()
    pollInterval = setInterval(() => {
      fetchActiveCount()
    }, intervalMs)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  return {
    // State
    alerts,
    activeCount,
    loading,
    error,
    // Getters
    activeAlerts,
    dismissedAlerts,
    hasActiveAlerts,
    // Actions
    fetchAlerts,
    fetchActiveCount,
    dismissAlert,
    getThresholds,
    setThreshold,
    deleteThreshold,
    startPolling,
    stopPolling,
  }
})

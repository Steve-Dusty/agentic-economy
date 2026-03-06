/**
 * Process Analytics Store
 *
 * Pinia store for managing process analytics data.
 * Part of the Process-Driven Platform feature (E11-02).
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAnalyticsStore = defineStore('analytics', () => {
  // State
  const trendData = ref(null)
  const processMetrics = ref([])
  const stepPerformance = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const selectedDays = ref(30)

  // Getters
  const dailyTrends = computed(() => trendData.value?.daily_trends || [])

  const totalExecutions = computed(() => trendData.value?.total_executions || 0)

  const overallSuccessRate = computed(() => trendData.value?.overall_success_rate || 0)

  const totalCost = computed(() => trendData.value?.total_cost || '$0.00')

  const slowestSteps = computed(() => stepPerformance.value?.slowest_steps || [])

  const mostExpensiveSteps = computed(() => stepPerformance.value?.most_expensive_steps || [])

  const topProcessesByExecutions = computed(() => {
    return [...processMetrics.value]
      .sort((a, b) => b.execution_count - a.execution_count)
      .slice(0, 5)
  })

  const processesWithIssues = computed(() => {
    return processMetrics.value.filter(p => p.success_rate < 80 && p.execution_count > 0)
  })

  // Actions
  async function fetchTrendData(days = 30) {
    loading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/processes/analytics/trends?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      trendData.value = response.data
      selectedDays.value = days
    } catch (err) {
      console.error('Failed to fetch trend data:', err)
      error.value = err.response?.data?.detail || 'Failed to load trend data'
    } finally {
      loading.value = false
    }
  }

  async function fetchAllProcessMetrics(days = 30) {
    loading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/processes/analytics/all?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      processMetrics.value = response.data.processes || []
    } catch (err) {
      console.error('Failed to fetch process metrics:', err)
      error.value = err.response?.data?.detail || 'Failed to load process metrics'
    } finally {
      loading.value = false
    }
  }

  async function fetchProcessMetrics(processId, days = 30) {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/processes/${processId}/analytics?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      return response.data
    } catch (err) {
      console.error('Failed to fetch process metrics:', err)
      throw err
    }
  }

  async function fetchStepPerformance(days = 30, limit = 10) {
    loading.value = true
    error.value = null

    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/executions/analytics/steps?days=${days}&limit=${limit}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      stepPerformance.value = response.data
    } catch (err) {
      console.error('Failed to fetch step performance:', err)
      error.value = err.response?.data?.detail || 'Failed to load step performance'
    } finally {
      loading.value = false
    }
  }

  async function fetchAllAnalytics(days = 30) {
    loading.value = true
    error.value = null

    try {
      await Promise.all([
        fetchTrendData(days),
        fetchAllProcessMetrics(days),
        fetchStepPerformance(days),
      ])
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
      error.value = 'Failed to load analytics data'
    } finally {
      loading.value = false
    }
  }

  function setDays(days) {
    selectedDays.value = days
    fetchAllAnalytics(days)
  }

  return {
    // State
    trendData,
    processMetrics,
    stepPerformance,
    loading,
    error,
    selectedDays,
    // Getters
    dailyTrends,
    totalExecutions,
    overallSuccessRate,
    totalCost,
    slowestSteps,
    mostExpensiveSteps,
    topProcessesByExecutions,
    processesWithIssues,
    // Actions
    fetchTrendData,
    fetchAllProcessMetrics,
    fetchProcessMetrics,
    fetchStepPerformance,
    fetchAllAnalytics,
    setDays,
  }
})

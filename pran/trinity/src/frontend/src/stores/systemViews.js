import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useSystemViewsStore = defineStore('systemViews', () => {
  // State
  const views = ref([])
  const activeViewId = ref(null) // Currently selected view (null = "All Agents")
  const isLoading = ref(false)
  const error = ref(null)

  // Computed
  const activeView = computed(() => {
    if (!activeViewId.value) return null
    return views.value.find(v => v.id === activeViewId.value) || null
  })

  const activeFilterTags = computed(() => {
    return activeView.value?.filter_tags || []
  })

  const sortedViews = computed(() => {
    return [...views.value].sort((a, b) => a.name.localeCompare(b.name))
  })

  // Actions
  async function fetchViews() {
    isLoading.value = true
    error.value = null
    try {
      const response = await axios.get('/api/system-views')
      views.value = response.data.views || []
    } catch (err) {
      console.error('Failed to fetch system views:', err)
      error.value = err.response?.data?.detail || 'Failed to load system views'
    } finally {
      isLoading.value = false
    }
  }

  async function createView(viewData) {
    isLoading.value = true
    error.value = null
    try {
      const response = await axios.post('/api/system-views', viewData)
      views.value.push(response.data)
      return response.data
    } catch (err) {
      console.error('Failed to create system view:', err)
      error.value = err.response?.data?.detail || 'Failed to create system view'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateView(viewId, viewData) {
    isLoading.value = true
    error.value = null
    try {
      const response = await axios.put(`/api/system-views/${viewId}`, viewData)
      const index = views.value.findIndex(v => v.id === viewId)
      if (index !== -1) {
        views.value[index] = response.data
      }
      return response.data
    } catch (err) {
      console.error('Failed to update system view:', err)
      error.value = err.response?.data?.detail || 'Failed to update system view'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteView(viewId) {
    isLoading.value = true
    error.value = null
    try {
      await axios.delete(`/api/system-views/${viewId}`)
      views.value = views.value.filter(v => v.id !== viewId)
      if (activeViewId.value === viewId) {
        activeViewId.value = null
      }
    } catch (err) {
      console.error('Failed to delete system view:', err)
      error.value = err.response?.data?.detail || 'Failed to delete system view'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function selectView(viewId) {
    activeViewId.value = viewId
    // Persist to localStorage
    if (viewId) {
      localStorage.setItem('trinity-active-view', viewId)
    } else {
      localStorage.removeItem('trinity-active-view')
    }
  }

  function clearSelection() {
    activeViewId.value = null
    localStorage.removeItem('trinity-active-view')
  }

  // Initialize from localStorage
  function initialize() {
    const savedViewId = localStorage.getItem('trinity-active-view')
    if (savedViewId) {
      activeViewId.value = savedViewId
    }
  }

  return {
    // State
    views,
    activeViewId,
    isLoading,
    error,
    // Computed
    activeView,
    activeFilterTags,
    sortedViews,
    // Actions
    fetchViews,
    createView,
    updateView,
    deleteView,
    selectView,
    clearSelection,
    initialize
  }
})

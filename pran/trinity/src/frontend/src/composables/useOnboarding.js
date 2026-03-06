import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

const STORAGE_KEY = 'trinity_onboarding'

// Shared state across all component instances
const state = ref(null)
const initialized = ref(false)
// Track data counts for first-run detection
const dataState = ref({
  processCount: 0,
  executionCount: 0,
  hasSchedule: false,
  hasApproval: false
})
// Celebration state - triggers animation in checklist
const celebrateStep = ref(null)

export function useOnboarding() {
  const authStore = useAuthStore()

  // Get storage key based on user
  const getStorageKey = () => `${STORAGE_KEY}_${authStore.user?.id || 'anon'}`

  // Initialize state from localStorage
  const initState = () => {
    if (initialized.value) return

    try {
      const stored = localStorage.getItem(getStorageKey())
      if (stored) {
        state.value = JSON.parse(stored)
      } else {
        state.value = getDefaultState()
      }
    } catch (e) {
      console.warn('Failed to load onboarding state:', e)
      state.value = getDefaultState()
    }
    initialized.value = true
  }

  // Default state structure
  const getDefaultState = () => ({
    dismissed: false,
    tourCompleted: false,
    checklistMinimized: false,
    onboardingCompletedAt: null, // Timestamp when onboarding was completed
    checklist: {
      createProcess: false,
      runExecution: false,
      monitorExecution: false,
      setupSchedule: false,
      configureApproval: false
    }
  })

  // Save state to localStorage
  const saveState = () => {
    if (!state.value) return
    try {
      localStorage.setItem(getStorageKey(), JSON.stringify(state.value))
    } catch (e) {
      console.warn('Failed to save onboarding state:', e)
    }
  }

  // Watch for changes and persist
  watch(state, () => {
    saveState()
  }, { deep: true })

  // Computed properties

  // True if user hasn't dismissed onboarding AND hasn't created any processes yet
  const isFirstRun = computed(() => {
    if (!state.value) return false
    // First run = not dismissed AND (no processes OR checklist items incomplete)
    return !state.value.dismissed && dataState.value.processCount === 0
  })

  // True if onboarding should show (not dismissed, regardless of process count)
  const shouldShowOnboarding = computed(() => {
    if (!state.value) return false
    return !state.value.dismissed
  })

  // True if onboarding has been completed (all required items done)
  const hasCompletedOnboarding = computed(() => {
    if (!state.value) return false
    return !!state.value.onboardingCompletedAt
  })

  const checklistProgress = computed(() => {
    if (!state.value) return { completed: 0, total: 5, required: 3 }

    const requiredItems = ['createProcess', 'runExecution', 'monitorExecution']
    const optionalItems = ['setupSchedule', 'configureApproval']

    const requiredCompleted = requiredItems.filter(item => state.value.checklist[item]).length
    const optionalCompleted = optionalItems.filter(item => state.value.checklist[item]).length

    return {
      completed: requiredCompleted + optionalCompleted,
      total: 5,
      required: 3,
      requiredCompleted
    }
  })

  const isChecklistComplete = computed(() => {
    return checklistProgress.value.requiredCompleted >= checklistProgress.value.required
  })

  // Methods
  const markChecklistItem = (item) => {
    if (!state.value) return
    if (!(item in state.value.checklist)) return

    // Enforce ordering: can't complete a step if previous required steps aren't done
    const requiredOrder = ['createProcess', 'runExecution', 'monitorExecution']
    const itemIndex = requiredOrder.indexOf(item)

    if (itemIndex > 0) {
      // Check all previous required steps are complete
      for (let i = 0; i < itemIndex; i++) {
        if (!state.value.checklist[requiredOrder[i]]) {
          // Previous step not complete, mark that one instead
          return
        }
      }
    }

    state.value.checklist[item] = true
    saveState()
  }

  // Mark step complete and celebrate - expands checklist and highlights next step
  const celebrateCompletion = (item) => {
    if (!state.value) return

    // Mark the item as complete
    if (item in state.value.checklist && !state.value.checklist[item]) {
      state.value.checklist[item] = true

      // Expand the checklist if minimized
      state.value.checklistMinimized = false

      // Trigger celebration animation
      celebrateStep.value = item

      // Clear celebration after animation
      setTimeout(() => {
        celebrateStep.value = null
      }, 3000)

      saveState()
    }
  }

  // Expand the checklist (used when user should see next steps)
  const expandChecklist = () => {
    if (!state.value) return
    state.value.checklistMinimized = false
    saveState()
  }

  const dismissOnboarding = () => {
    if (!state.value) return
    state.value.dismissed = true
    saveState()
  }

  // Mark onboarding as fully complete (all required items done)
  const markOnboardingComplete = () => {
    if (!state.value) return
    state.value.onboardingCompletedAt = new Date().toISOString()
    state.value.dismissed = true
    saveState()
  }

  const markTourCompleted = () => {
    if (!state.value) return
    state.value.tourCompleted = true
    saveState()
  }

  const toggleChecklistMinimized = () => {
    if (!state.value) return
    state.value.checklistMinimized = !state.value.checklistMinimized
    saveState()
  }

  const resetOnboarding = () => {
    state.value = getDefaultState()
    saveState()
  }

  // Auto-detect completion based on API data
  const syncWithData = ({ processCount = 0, executionCount = 0, hasSchedule = false, hasApproval = false }) => {
    // Update data state for first-run detection
    dataState.value = { processCount, executionCount, hasSchedule, hasApproval }

    if (!state.value) return

    // Mark steps in order - each step requires the previous to be complete
    if (processCount > 0 && !state.value.checklist.createProcess) {
      state.value.checklist.createProcess = true
    }
    // Only mark runExecution if createProcess is done
    if (executionCount > 0 && state.value.checklist.createProcess && !state.value.checklist.runExecution) {
      state.value.checklist.runExecution = true
    }
    // Only mark monitorExecution if runExecution is done
    if (executionCount > 0 && state.value.checklist.runExecution && !state.value.checklist.monitorExecution) {
      state.value.checklist.monitorExecution = true
    }
    if (hasSchedule && !state.value.checklist.setupSchedule) {
      state.value.checklist.setupSchedule = true
    }
    if (hasApproval && !state.value.checklist.configureApproval) {
      state.value.checklist.configureApproval = true
    }

    // Auto-mark complete if all required items are done
    if (checklistProgress.value.requiredCompleted >= checklistProgress.value.required) {
      if (!state.value.onboardingCompletedAt) {
        state.value.onboardingCompletedAt = new Date().toISOString()
      }
    }

    saveState()
  }

  // Initialize on first use
  initState()

  return {
    state: computed(() => state.value),
    dataState: computed(() => dataState.value),
    celebrateStep: computed(() => celebrateStep.value),
    isFirstRun,
    shouldShowOnboarding,
    hasCompletedOnboarding,
    checklistProgress,
    isChecklistComplete,
    markChecklistItem,
    celebrateCompletion,
    expandChecklist,
    dismissOnboarding,
    markOnboardingComplete,
    markTourCompleted,
    toggleChecklistMinimized,
    resetOnboarding,
    syncWithData
  }
}

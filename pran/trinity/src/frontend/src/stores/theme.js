import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'trinity-theme'

export const useThemeStore = defineStore('theme', () => {
  // Theme can be 'light', 'dark', or 'system'
  const theme = ref(getStoredTheme())

  // Computed actual theme based on system preference if theme is 'system'
  const isDark = ref(false)

  function getStoredTheme() {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && ['light', 'dark', 'system'].includes(stored)) {
      return stored
    }
    return 'system'
  }

  function setTheme(newTheme) {
    theme.value = newTheme
    localStorage.setItem(STORAGE_KEY, newTheme)
    applyTheme()
  }

  function toggleTheme() {
    // Cycle through: light -> dark -> system -> light
    const cycle = { light: 'dark', dark: 'system', system: 'light' }
    setTheme(cycle[theme.value])
  }

  function applyTheme() {
    const root = document.documentElement

    if (theme.value === 'system') {
      // Use system preference
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    } else {
      isDark.value = theme.value === 'dark'
    }

    if (isDark.value) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }

  function initTheme() {
    // Apply theme immediately
    applyTheme()

    // Listen for system preference changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', () => {
      if (theme.value === 'system') {
        applyTheme()
      }
    })
  }

  // Watch for theme changes
  watch(theme, applyTheme)

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
    initTheme
  }
})

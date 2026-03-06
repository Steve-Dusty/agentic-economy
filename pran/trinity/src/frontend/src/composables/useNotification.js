import { ref } from 'vue'

/**
 * Composable for toast notification management
 * Provides a simple notification system with auto-dismiss
 */
export function useNotification() {
  const notification = ref(null)

  const showNotification = (message, type = 'success') => {
    notification.value = { message, type }
    setTimeout(() => {
      notification.value = null
    }, 3000)
  }

  return {
    notification,
    showNotification
  }
}

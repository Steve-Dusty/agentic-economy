import { ref, nextTick } from 'vue'

/**
 * Composable for terminal fullscreen and keyboard handling
 * Manages terminal state and events
 */
export function useAgentTerminal(showNotification) {
  const isTerminalFullscreen = ref(false)
  const terminalRef = ref(null)

  const toggleTerminalFullscreen = () => {
    isTerminalFullscreen.value = !isTerminalFullscreen.value
    nextTick(() => {
      if (terminalRef.value?.fit) {
        terminalRef.value.fit()
      }
    })
  }

  const handleTerminalKeydown = (event) => {
    if (event.key === 'Escape' && isTerminalFullscreen.value) {
      toggleTerminalFullscreen()
    }
  }

  const onTerminalConnected = () => {
    showNotification('Terminal connected', 'success')
  }

  const onTerminalDisconnected = () => {
    showNotification('Terminal disconnected', 'info')
  }

  const onTerminalError = (errorMsg) => {
    showNotification(`Terminal error: ${errorMsg}`, 'error')
  }

  return {
    isTerminalFullscreen,
    terminalRef,
    toggleTerminalFullscreen,
    handleTerminalKeydown,
    onTerminalConnected,
    onTerminalDisconnected,
    onTerminalError
  }
}

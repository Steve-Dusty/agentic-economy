import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import router from './router'
import App from './App.vue'
import './style.css'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialize auth state from localStorage/cookies on app startup
const authStore = useAuthStore()
authStore.initializeAuth()

// Setup axios interceptor to handle token expiration
axios.interceptors.response.use(
  response => response,
  error => {
    // If we get a 401 Unauthorized, token is expired or invalid
    if (error.response?.status === 401) {
      // Get the current route
      const currentPath = router.currentRoute.value.path

      // Don't redirect if already on login or setup page
      if (currentPath !== '/login' && currentPath !== '/setup') {
        console.log('🔐 Session expired - redirecting to login')

        // Clear auth state
        authStore.logout()

        // Redirect to login
        router.push('/login')
      }
    }
    return Promise.reject(error)
  }
)

app.mount('#app')

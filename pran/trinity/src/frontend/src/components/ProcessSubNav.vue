<template>
  <div class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 mb-6">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <nav class="-mb-px flex space-x-8">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap inline-flex items-center',
            isActive(item.path)
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
          ]"
        >
          <component :is="item.icon" class="h-4 w-4 mr-2" />
          {{ item.label }}
          <span
            v-if="item.badge && item.badge > 0"
            class="ml-2 px-2 py-0.5 text-xs font-semibold bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 rounded-full"
          >
            {{ item.badge }}
          </span>
        </router-link>
      </nav>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  QueueListIcon,
  ChartBarIcon,
  PlayCircleIcon,
  CheckCircleIcon,
  BookOpenIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  pendingApprovals: {
    type: Number,
    default: 0
  }
})

const route = useRoute()

const navItems = computed(() => [
  {
    path: '/processes',
    label: 'Processes',
    icon: QueueListIcon,
  },
  {
    path: '/process-dashboard',
    label: 'Dashboard',
    icon: ChartBarIcon,
  },
  {
    path: '/executions',
    label: 'Executions',
    icon: PlayCircleIcon,
  },
  {
    path: '/approvals',
    label: 'Approvals',
    icon: CheckCircleIcon,
    badge: props.pendingApprovals,
  },
  {
    path: '/processes/docs',
    label: 'Docs',
    icon: BookOpenIcon,
  },
])

const isActive = (path) => {
  // Exact match for most routes
  if (route.path === path) return true
  // For docs, match /processes/docs/*
  if (path === '/processes/docs' && route.path.startsWith('/processes/docs')) return true
  // For processes, also match /processes/new and /processes/:id but NOT /processes/docs
  if (path === '/processes' && route.path.startsWith('/processes/') && !route.path.startsWith('/processes/docs')) return true
  // For executions, also match /executions/:id
  if (path === '/executions' && route.path.startsWith('/executions/')) return true
  return false
}
</script>

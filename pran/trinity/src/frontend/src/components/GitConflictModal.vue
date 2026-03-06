<template>
  <div v-if="show" class="fixed z-50 inset-0 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:p-0">
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity" @click="$emit('dismiss')"></div>

      <!-- Modal content -->
      <div class="inline-block align-middle bg-white dark:bg-gray-800 rounded-lg text-left shadow-xl transform transition-all sm:max-w-lg sm:w-full">
        <div class="px-4 pt-5 pb-4 sm:p-6">
          <!-- Header with icon -->
          <div class="flex items-start">
            <div class="flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-full bg-yellow-100 dark:bg-yellow-900/30">
              <svg class="h-6 w-6 text-yellow-600 dark:text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div class="ml-4 flex-1">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                {{ isPull ? 'Pull Conflict' : 'Push Conflict' }}
              </h3>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {{ conflict?.message || 'A conflict was detected. Choose how to proceed:' }}
              </p>
            </div>
          </div>

          <!-- Options for Pull conflicts -->
          <div v-if="isPull" class="mt-6 space-y-3">
            <button
              @click="$emit('resolve', 'stash_reapply')"
              class="w-full flex items-start p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group"
            >
              <div class="flex-shrink-0 flex items-center justify-center h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
              </div>
              <div class="ml-4 text-left">
                <p class="text-sm font-medium text-gray-900 dark:text-white">Stash & Reapply (Recommended)</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Save local changes, pull remote, then reapply your changes</p>
              </div>
            </button>

            <button
              @click="$emit('resolve', 'force_reset')"
              class="w-full flex items-start p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-red-500 dark:hover:border-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors group"
            >
              <div class="flex-shrink-0 flex items-center justify-center h-8 w-8 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 group-hover:bg-red-200 dark:group-hover:bg-red-900/50">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <div class="ml-4 text-left">
                <p class="text-sm font-medium text-gray-900 dark:text-white">Force Replace Local</p>
                <p class="text-xs text-red-600 dark:text-red-400 mt-0.5">Discard all local changes and reset to remote (destructive!)</p>
              </div>
            </button>
          </div>

          <!-- Options for Sync/Push conflicts -->
          <div v-else class="mt-6 space-y-3">
            <button
              @click="$emit('resolve', 'pull_first')"
              class="w-full flex items-start p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group"
            >
              <div class="flex-shrink-0 flex items-center justify-center h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <div class="ml-4 text-left">
                <p class="text-sm font-medium text-gray-900 dark:text-white">Pull First, Then Push (Recommended)</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Fetch remote changes, merge with yours, then push</p>
              </div>
            </button>

            <button
              @click="$emit('resolve', 'force_push')"
              class="w-full flex items-start p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-red-500 dark:hover:border-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors group"
            >
              <div class="flex-shrink-0 flex items-center justify-center h-8 w-8 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 group-hover:bg-red-200 dark:group-hover:bg-red-900/50">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
              </div>
              <div class="ml-4 text-left">
                <p class="text-sm font-medium text-gray-900 dark:text-white">Force Push</p>
                <p class="text-xs text-red-600 dark:text-red-400 mt-0.5">Overwrite remote with your local changes (destructive!)</p>
              </div>
            </button>
          </div>
        </div>

        <!-- Footer -->
        <div class="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 flex justify-end">
          <button
            @click="$emit('dismiss')"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  conflict: {
    type: Object,
    default: null
    // { type: 'pull'|'sync', conflictType: string, message: string }
  }
})

defineEmits(['resolve', 'dismiss'])

const isPull = computed(() => props.conflict?.type === 'pull')
</script>

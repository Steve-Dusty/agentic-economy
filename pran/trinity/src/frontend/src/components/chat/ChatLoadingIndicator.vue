<template>
  <div class="px-2">
    <div class="bg-white dark:bg-gray-800 rounded-xl px-4 py-3 shadow-sm max-w-[85%]">
      <div class="flex items-center space-x-2">
        <div class="flex space-x-1">
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
          <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
        </div>
        <span class="text-sm text-gray-500 dark:text-gray-400 status-text" :key="text">{{ text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: 'Thinking...'
  }
})
</script>

<style scoped>
/* Custom bounce animation for loading dots */
@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

/* Fade transition for status text changes */
.status-text {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

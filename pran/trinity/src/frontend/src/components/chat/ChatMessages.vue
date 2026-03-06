<template>
  <div class="flex-1 overflow-y-auto" ref="containerRef">
    <!-- Inner wrapper with min-height to enable bottom alignment -->
    <div class="min-h-full flex flex-col justify-end">
      <!-- Messages content wrapper -->
      <div class="space-y-4 pb-4">
        <!-- Empty state slot -->
        <slot v-if="messages.length === 0 && !loading" name="empty">
          <div class="text-center py-12">
            <div class="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg class="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Start a Conversation</h3>
            <p class="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto">
              Type a message below to begin chatting.
            </p>
          </div>
        </slot>

        <!-- Message list -->
        <div v-for="(msg, index) in messages" :key="index" class="px-2">
          <ChatBubble :role="msg.role" :content="msg.content" />
        </div>

        <!-- Loading indicator -->
        <ChatLoadingIndicator v-if="loading" :text="loadingText" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ChatBubble from './ChatBubble.vue'
import ChatLoadingIndicator from './ChatLoadingIndicator.vue'

const props = defineProps({
  messages: {
    type: Array,
    required: true,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  loadingText: {
    type: String,
    default: 'Thinking...'
  },
  autoScroll: {
    type: Boolean,
    default: true
  }
})

const containerRef = ref(null)

// Scroll to bottom
const scrollToBottom = () => {
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight
  }
}

// Auto-scroll on new messages
watch(() => props.messages.length, () => {
  if (props.autoScroll) {
    nextTick(scrollToBottom)
  }
})

// Auto-scroll when loading state changes
watch(() => props.loading, () => {
  if (props.autoScroll) {
    nextTick(scrollToBottom)
  }
})

// Expose scrollToBottom for parent components
defineExpose({
  scrollToBottom
})
</script>

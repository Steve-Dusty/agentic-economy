<template>
  <div class="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl shadow-lg p-3">
    <form @submit.prevent="handleSubmit" class="flex items-end space-x-2">
      <textarea
        ref="textareaRef"
        v-model="localMessage"
        rows="1"
        :placeholder="placeholder"
        class="flex-1 resize-none border-0 bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-0 focus:outline-none"
        :disabled="disabled"
        @keydown.enter.exact.prevent="handleSubmit"
        @input="autoResize"
      ></textarea>
      <button
        type="submit"
        :disabled="disabled || !localMessage.trim()"
        class="p-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg transition-colors"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
        </svg>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: 'Type your message...'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const localMessage = ref(props.modelValue)
const textareaRef = ref(null)

// Sync with v-model
watch(() => props.modelValue, (newVal) => {
  localMessage.value = newVal
})

watch(localMessage, (newVal) => {
  emit('update:modelValue', newVal)
})

// Auto-resize textarea
const autoResize = (event) => {
  const textarea = event.target
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
}

// Handle submit
const handleSubmit = () => {
  if (localMessage.value.trim() && !props.disabled) {
    emit('submit', localMessage.value.trim())
    localMessage.value = ''
    // Reset textarea height
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }
  }
}

// Expose focus method
defineExpose({
  focus: () => textareaRef.value?.focus()
})
</script>

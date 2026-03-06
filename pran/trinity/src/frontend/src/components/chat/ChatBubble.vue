<template>
  <!-- User message (plain text) -->
  <div
    v-if="role === 'user'"
    class="rounded-xl px-4 py-3 max-w-[85%] bg-indigo-600 text-white ml-auto"
  >
    <p class="whitespace-pre-wrap">{{ content }}</p>
  </div>
  <!-- Assistant message (markdown rendered) -->
  <div
    v-else
    class="rounded-xl px-4 py-3 max-w-[85%] bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm"
  >
    <div
      class="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-ol:my-2 prose-li:my-0 prose-pre:my-2 prose-code:text-indigo-600 dark:prose-code:text-indigo-400 prose-code:bg-gray-100 dark:prose-code:bg-gray-700 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
      v-html="renderedContent"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  role: {
    type: String,
    required: true,
    validator: (value) => ['user', 'assistant'].includes(value)
  },
  content: {
    type: String,
    required: true
  }
})

// Configure marked for safe, simple output
marked.setOptions({
  breaks: true,  // Convert \n to <br>
  gfm: true      // GitHub Flavored Markdown
})

// Custom renderer to open links in new window
const renderer = new marked.Renderer()
renderer.link = (href, title, text) => {
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`
}
marked.use({ renderer })

const renderedContent = computed(() => {
  if (!props.content) return ''
  return marked(props.content)
})
</script>

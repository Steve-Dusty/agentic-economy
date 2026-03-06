<template>
  <div class="process-chat-assistant flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
      <div class="flex items-center gap-2">
        <SparklesIcon class="h-5 w-5 text-indigo-500" />
        <span class="font-medium text-gray-900 dark:text-white">Process Assistant</span>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="messages.length > 0"
          @click="clearChat"
          class="text-xs px-2 py-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          title="Clear conversation"
        >
          Clear
        </button>
        <span
          class="text-xs px-2 py-0.5 rounded-full"
          :class="systemAgentStatus === 'running'
            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
            : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'"
        >
          {{ systemAgentStatus === 'running' ? 'Connected' : 'Connecting...' }}
        </span>
      </div>
    </div>

    <!-- Validation Errors Banner -->
    <div v-if="validationErrors.length > 0" class="mx-4 mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1">
          <p class="text-sm font-medium text-red-700 dark:text-red-400">
            {{ validationErrors.length }} validation error{{ validationErrors.length > 1 ? 's' : '' }} found
          </p>
          <p class="text-xs text-red-600 dark:text-red-500 mt-0.5">
            {{ validationErrors[0] }}{{ validationErrors.length > 1 ? ` (+${validationErrors.length - 1} more)` : '' }}
          </p>
        </div>
        <button
          @click="askForHelp"
          class="flex-shrink-0 text-xs px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          Help me fix
        </button>
      </div>
    </div>

    <!-- Selected Text Banner -->
    <div v-if="selectedText" class="mx-4 mt-3 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-indigo-700 dark:text-indigo-400">
            Selected code
          </p>
          <p class="text-xs text-indigo-600 dark:text-indigo-500 mt-0.5 font-mono truncate">
            {{ selectedText.slice(0, 50) }}{{ selectedText.length > 50 ? '...' : '' }}
          </p>
        </div>
        <div class="flex gap-1 flex-shrink-0">
          <button
            @click="askAboutSelection('explain')"
            class="text-xs px-2 py-1.5 bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800 rounded transition-colors"
          >
            Explain
          </button>
          <button
            @click="askAboutSelection('edit')"
            class="text-xs px-2 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded transition-colors"
          >
            Edit this
          </button>
        </div>
      </div>
    </div>

    <!-- Messages area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Welcome message -->
      <div v-if="messages.length === 0" class="text-center py-8">
        <div class="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <SparklesIcon class="w-8 h-8 text-indigo-500" />
        </div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
          Let's create your process!
        </h3>
        <p class="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto mb-4">
          Describe what you want to automate, and I'll help you build it step by step.
        </p>

        <!-- Suggested prompts -->
        <div class="flex flex-wrap justify-center gap-2 mt-4">
          <button
            v-for="prompt in suggestedPrompts"
            :key="prompt"
            @click="sendSuggestedPrompt(prompt)"
            class="text-xs px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-full text-gray-600 dark:text-gray-300 hover:border-indigo-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <!-- Message list -->
      <div v-for="(msg, index) in messages" :key="index" class="animate-fade-in">
        <!-- User message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="max-w-[85%] bg-indigo-600 text-white rounded-xl rounded-br-sm px-4 py-3">
            <p class="whitespace-pre-wrap text-sm">{{ msg.content }}</p>
          </div>
        </div>

        <!-- Assistant message -->
        <div v-else class="flex justify-start">
          <div class="max-w-[85%] bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100 dark:border-gray-700">
            <!-- Check for YAML code blocks -->
            <div v-if="hasYamlBlock(msg.content)" class="space-y-3">
              <div v-for="(part, i) in parseMessageParts(msg.content)" :key="i">
                <!-- Text content with markdown -->
                <div v-if="part.type === 'text'" class="prose prose-sm dark:prose-invert max-w-none" v-html="renderMarkdown(part.content)"></div>

                <!-- YAML code block -->
                <div v-else-if="part.type === 'yaml'" class="relative">
                  <div class="bg-gray-900 rounded-lg overflow-hidden">
                    <div class="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
                      <span class="text-xs text-gray-400 font-mono">process.yaml</span>
                      <span class="flex items-center gap-1 text-xs px-2 py-1 text-green-400">
                        <CheckIcon class="h-3 w-3" />
                        Auto-synced
                      </span>
                    </div>
                    <pre class="p-3 text-sm text-gray-100 overflow-x-auto"><code>{{ part.content }}</code></pre>
                  </div>
                </div>
              </div>
            </div>

            <!-- Plain text message with markdown -->
            <div v-else class="prose prose-sm dark:prose-invert max-w-none" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
      </div>

      <!-- Loading indicator (waiting for API) -->
      <div v-if="loading && !typingMessage" class="flex justify-start">
        <div class="bg-white dark:bg-gray-800 rounded-xl px-4 py-3 shadow-sm border border-gray-100 dark:border-gray-700">
          <div class="flex items-center gap-2">
            <div class="flex space-x-1">
              <span class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
            <span class="text-sm text-gray-500 dark:text-gray-400">Thinking...</span>
          </div>
        </div>
      </div>

      <!-- Typing animation (assistant response appearing) -->
      <div v-if="typingMessage !== null" class="flex justify-start animate-fade-in">
        <div class="max-w-[85%] bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100 dark:border-gray-700">
          <div class="prose prose-sm dark:prose-invert max-w-none" v-html="renderMarkdown(typingMessage)"></div>
          <span class="inline-block w-1 h-4 ml-1 bg-indigo-500 animate-pulse"></span>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="error" class="flex justify-center">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {{ error }}
          <button @click="error = null" class="ml-2 underline">Dismiss</button>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="border-t border-gray-200 dark:border-gray-700 p-3 bg-white dark:bg-gray-800">
      <form @submit.prevent="sendMessage" class="flex items-end gap-2">
        <textarea
          ref="inputRef"
          v-model="inputMessage"
          rows="1"
          placeholder="Describe what you want to automate..."
          class="flex-1 resize-none border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
          :disabled="loading"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
        ></textarea>
        <button
          type="submit"
          :disabled="loading || !inputMessage.trim()"
          class="p-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          <PaperAirplaneIcon class="w-5 h-5" />
        </button>
      </form>
      <p class="text-xs text-gray-400 mt-2 text-center">
        Powered by Trinity System Agent
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { SparklesIcon, PaperAirplaneIcon, CheckIcon } from '@heroicons/vue/24/outline'
import { marked } from 'marked'
import api from '../api'

// Configure marked for simple output
marked.setOptions({
  breaks: true,
  gfm: true
})

// Props and emits
const props = defineProps({
  validationErrors: {
    type: Array,
    default: () => []
  },
  currentYaml: {
    type: String,
    default: ''
  },
  selectedText: {
    type: String,
    default: ''
  },
  processStatus: {
    type: String,
    default: 'draft'
  }
})
const emit = defineEmits(['yaml-update'])

// LocalStorage key for chat persistence
const STORAGE_KEY = 'trinity_process_assistant_chat'

// State
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const error = ref(null)
const systemAgentStatus = ref('connecting')
const messagesContainer = ref(null)
const inputRef = ref(null)
const typingMessage = ref(null) // Currently typing assistant message
const typingIndex = ref(0)

// Extract YAML from content
function extractYaml(content) {
  const match = content.match(/```ya?ml\n?([\s\S]*?)```/i)
  return match ? match[1].trim() : null
}

// Typing animation - reveals text word by word
async function typeMessage(fullContent) {
  typingMessage.value = ''
  typingIndex.value = 0

  // Split by words but keep whitespace
  const words = fullContent.split(/(\s+)/)

  for (let i = 0; i < words.length; i++) {
    typingMessage.value += words[i]
    typingIndex.value = i
    scrollToBottom()

    // Check for YAML and emit live updates to editor
    const yaml = extractYaml(typingMessage.value)
    if (yaml) {
      emit('yaml-update', yaml)
    }

    // Faster for whitespace, slower for actual words
    const delay = words[i].trim() ? 30 : 5
    await new Promise(resolve => setTimeout(resolve, delay))
  }

  // Done typing - add to messages and clear typing state
  messages.value.push({
    role: 'assistant',
    content: fullContent
  })
  typingMessage.value = null

  // Final YAML emit
  const finalYaml = extractYaml(fullContent)
  if (finalYaml) {
    emit('yaml-update', finalYaml)
  }
}

// Load chat from localStorage
function loadChat() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const data = JSON.parse(saved)
      messages.value = data.messages || []
    }
  } catch (e) {
    console.error('Failed to load chat from localStorage:', e)
  }
}

// Save chat to localStorage
function saveChat() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      messages: messages.value,
      updatedAt: new Date().toISOString()
    }))
  } catch (e) {
    console.error('Failed to save chat to localStorage:', e)
  }
}

// Clear chat history
function clearChat() {
  if (confirm('Clear conversation history? This cannot be undone.')) {
    messages.value = []
    localStorage.removeItem(STORAGE_KEY)
  }
}

// Suggested prompts for empty state
const suggestedPrompts = [
  "Review content before publishing",
  "Analyze data and generate reports",
  "Route support tickets to agents",
  "Automate approval workflows"
]

// Process creation context - prepended to first message
const PROCESS_ASSISTANT_CONTEXT = `You are a friendly Process Assistant helping users create workflow automations.

CONVERSATION STYLE:
- Be warm and conversational, like a helpful colleague
- Ask ONE question at a time, don't overwhelm with lists
- Keep responses concise (2-3 sentences max unless generating YAML)
- Build understanding gradually through back-and-forth dialogue
- Don't use markdown bold (**text**) - just write naturally

APPROACH:
1. First, understand what they want to accomplish in simple terms
2. Then ask about who/what should do the work (which agents)
3. Then ask if humans need to approve anything
4. Finally, generate the YAML when you have enough info

BE PROACTIVE WITH EDITS:
- When users ask to change something, IMMEDIATELY show the updated YAML
- Don't ask "want me to show you?" - just show the change
- Briefly explain what you changed, then include the full updated YAML

PROCESS STATUS AWARENESS:
- If you receive [CONTEXT: PUBLISHED process], the process is read-only
- Tell the user: "This process is published. Click 'New Version' to create an editable draft, then I can help you make changes."
- Don't offer to edit published processes directly

YAML RULES (when generating):
- Wrap in \`\`\`yaml code blocks
- Use kebab-case for names
- Version format: "1.0"
- Step types: agent_task, human_approval, gateway, notification
- Use depends_on: [step_id] for ordering

CRITICAL - agent_task step format (DO NOT nest in config):
  - id: my-step
    name: "My Step"
    type: agent_task
    agent: "agent-name"     # Required, at step level
    message: "Task message" # Required, at step level

CRITICAL - human_approval step format:
  - id: review
    name: "Review Step"
    type: human_approval
    approvers: ["email@example.com"]
    timeout_hours: 24

Example good response: "That sounds like a content review workflow! Who typically reviews the content - is it one person or a team?"

Example bad response: "**Great!** Here are the options: - Option 1... - Option 2..."

User's message: `

// Check system agent status on mount
onMounted(async () => {
  // Load previous conversation
  loadChat()

  try {
    const response = await api.get('/api/system-agent/status')
    systemAgentStatus.value = response.data.status === 'running' ? 'running' : 'stopped'
  } catch (e) {
    systemAgentStatus.value = 'unavailable'
    console.error('Failed to check system agent status:', e)
  }

  // Focus input
  inputRef.value?.focus()
})

// Send message to system agent
async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''
  error.value = null

  // Reset textarea height
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }

  // Add user message to chat
  messages.value.push({
    role: 'user',
    content: userMessage
  })

  // Scroll to bottom
  await nextTick()
  scrollToBottom()

  loading.value = true

  try {
    // Build message with context for first message
    let messageToSend = userMessage
    if (messages.value.length === 1) {
      messageToSend = PROCESS_ASSISTANT_CONTEXT + userMessage
    }

    // Add process status context when relevant
    if (props.processStatus === 'published') {
      messageToSend = `[CONTEXT: This is a PUBLISHED process - it's read-only. To make changes, the user must click "New Version" to create an editable draft copy first.]\n\n` + messageToSend
    } else if (props.processStatus === 'archived') {
      messageToSend = `[CONTEXT: This is an ARCHIVED process - it cannot be edited or executed.]\n\n` + messageToSend
    }

    const response = await api.post('/api/agents/trinity-system/chat', {
      message: messageToSend
    })

    // Stop showing "Thinking..." and start typing animation
    loading.value = false
    await typeMessage(response.data.response)
  } catch (err) {
    console.error('Chat error:', err)
    if (err.response?.status === 503) {
      error.value = 'System agent is not running. Please start it from the Settings page.'
    } else if (err.response?.status === 429) {
      error.value = 'System agent is busy. Please wait a moment.'
    } else {
      error.value = err.response?.data?.detail || 'Failed to get response. Please try again.'
    }
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

// Send suggested prompt
function sendSuggestedPrompt(prompt) {
  inputMessage.value = `I want to ${prompt.toLowerCase()}`
  sendMessage()
}

// Ask for help with validation errors
function askForHelp() {
  const errorList = props.validationErrors.join('\n- ')
  const yamlPreview = props.currentYaml ? props.currentYaml.slice(0, 500) : ''

  inputMessage.value = `I have validation errors in my process YAML. Can you help me fix them?

Errors:
- ${errorList}

${yamlPreview ? `Current YAML (first 500 chars):\n\`\`\`yaml\n${yamlPreview}\n\`\`\`` : ''}`
  sendMessage()
}

// Ask about selected code
function askAboutSelection(action) {
  const selected = props.selectedText
  if (!selected) return

  if (action === 'explain') {
    inputMessage.value = `Can you explain what this part of the YAML does?

\`\`\`yaml
${selected}
\`\`\``
  } else if (action === 'edit') {
    inputMessage.value = `I want to modify this part of my process:

\`\`\`yaml
${selected}
\`\`\`

What would you like me to change?`
  }
  sendMessage()
}

// Check if message contains YAML code block
function hasYamlBlock(content) {
  return /```ya?ml[\s\S]*?```/i.test(content)
}

// Parse message into text and YAML parts
function parseMessageParts(content) {
  const parts = []
  const regex = /```ya?ml\n?([\s\S]*?)```/gi
  let lastIndex = 0
  let match

  while ((match = regex.exec(content)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      const text = content.slice(lastIndex, match.index).trim()
      if (text) {
        parts.push({ type: 'text', content: text })
      }
    }

    // Add YAML block
    parts.push({ type: 'yaml', content: match[1].trim() })
    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < content.length) {
    const text = content.slice(lastIndex).trim()
    if (text) {
      parts.push({ type: 'text', content: text })
    }
  }

  return parts
}

// Apply YAML to editor
// Render markdown to HTML
function renderMarkdown(text) {
  if (!text) return ''
  return marked(text)
}

// Auto-resize textarea
function autoResize(event) {
  const textarea = event.target
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
}

// Scroll to bottom of messages
function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Watch for new messages and auto-scroll
watch(messages, () => {
  nextTick(() => scrollToBottom())
  // Persist to localStorage
  if (messages.value.length > 0) {
    saveChat()
  }
}, { deep: true })
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

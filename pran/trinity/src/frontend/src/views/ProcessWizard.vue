<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center gap-4 mb-4">
          <button
            @click="handleCancel"
            class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            <ArrowLeftIcon class="h-5 w-5" />
          </button>
          <div>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Create Your First Process</h1>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Follow the steps below to create an automated workflow
            </p>
          </div>
        </div>

        <!-- Step Indicator -->
        <div class="flex items-center justify-center">
          <div class="flex items-center gap-2">
            <template v-for="(stepInfo, index) in steps" :key="index">
              <div
                class="flex items-center gap-2"
                :class="index <= currentStep ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500'"
              >
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors"
                  :class="[
                    index < currentStep
                      ? 'bg-indigo-600 text-white'
                      : index === currentStep
                        ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 ring-2 ring-indigo-600 dark:ring-indigo-400'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                  ]"
                >
                  <CheckIcon v-if="index < currentStep" class="h-4 w-4" />
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <span class="text-sm font-medium hidden sm:inline">{{ stepInfo.title }}</span>
              </div>
              <div
                v-if="index < steps.length - 1"
                class="w-12 h-0.5 mx-2"
                :class="index < currentStep ? 'bg-indigo-600 dark:bg-indigo-400' : 'bg-gray-300 dark:bg-gray-600'"
              />
            </template>
          </div>
        </div>
      </div>

      <!-- Step Content -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
        <!-- Step 1: Goal Selection -->
        <div v-if="currentStep === 0" class="p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">What do you want to automate?</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">Choose a workflow type to get started</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="goal in goalOptions"
              :key="goal.id"
              @click="selectGoal(goal)"
              :class="[
                'relative p-5 border-2 rounded-xl cursor-pointer transition-all',
                wizardState.selectedGoal?.id === goal.id
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 ring-2 ring-indigo-500'
                  : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600'
              ]"
            >
              <div class="flex items-start gap-4">
                <div
                  class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  :class="goal.iconBg"
                >
                  <component :is="goal.icon" class="h-6 w-6" :class="goal.iconColor" />
                </div>
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold text-gray-900 dark:text-white">{{ goal.title }}</h3>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ goal.description }}</p>
                  <div class="flex items-center gap-4 mt-3 text-xs text-gray-400 dark:text-gray-500">
                    <span class="flex items-center gap-1">
                      <Squares2X2Icon class="h-3.5 w-3.5" />
                      {{ goal.steps.length }} steps
                    </span>
                    <span v-if="goal.hasApproval" class="flex items-center gap-1">
                      <CheckCircleIcon class="h-3.5 w-3.5" />
                      Includes approval
                    </span>
                  </div>
                </div>
              </div>
              <CheckCircleIcon
                v-if="wizardState.selectedGoal?.id === goal.id"
                class="absolute top-3 right-3 h-6 w-6 text-indigo-600 dark:text-indigo-400"
              />
            </div>
          </div>
        </div>

        <!-- Step 2: Agent Assignment -->
        <div v-else-if="currentStep === 1" class="p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Assign agents to steps</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">Select which agent will handle each step</p>

          <div v-if="availableAgents.length === 0" class="text-center py-8">
            <ExclamationTriangleIcon class="h-12 w-12 text-amber-500 mx-auto mb-4" />
            <p class="text-gray-600 dark:text-gray-400 mb-4">No agents found. Create an agent first to continue.</p>
            <router-link
              to="/agents"
              class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
            >
              <PlusIcon class="h-4 w-4" />
              Create Agent
            </router-link>
          </div>

          <div v-else class="space-y-4">
            <div
              v-for="(step, index) in wizardState.steps"
              :key="step.id"
              class="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
            >
              <!-- Step number and flow indicator -->
              <div class="flex flex-col items-center">
                <div class="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-sm font-medium text-indigo-600 dark:text-indigo-400">
                  {{ index + 1 }}
                </div>
                <div v-if="index < wizardState.steps.length - 1" class="w-0.5 h-4 bg-gray-300 dark:bg-gray-600 mt-1" />
              </div>

              <!-- Step details -->
              <div class="flex-1 min-w-0">
                <p class="font-medium text-gray-900 dark:text-white">{{ step.name }}</p>
                <p class="text-sm text-gray-500 dark:text-gray-400">{{ step.description }}</p>
              </div>

              <!-- Agent selector -->
              <div class="w-48 flex-shrink-0">
                <select
                  v-model="step.agent"
                  class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="">Select agent...</option>
                  <option v-for="agent in availableAgents" :key="agent.name" :value="agent.name">
                    {{ agent.name }} {{ agent.status === 'running' ? '●' : '○' }}
                  </option>
                </select>
                <p v-if="step.agent && getAgentStatus(step.agent) !== 'running'" class="text-xs text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
                  <ExclamationTriangleIcon class="h-3 w-3" />
                  Agent not running
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3: Customize -->
        <div v-else-if="currentStep === 2" class="p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Customize your workflow</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">Adjust step details or skip to use defaults</p>

          <div class="space-y-6">
            <div
              v-for="(step, index) in wizardState.steps"
              :key="step.id"
              class="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
            >
              <div class="flex items-center gap-3 mb-4">
                <div class="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-xs font-medium text-indigo-600 dark:text-indigo-400">
                  {{ index + 1 }}
                </div>
                <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Step {{ index + 1 }}</span>
              </div>

              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Step Name</label>
                  <input
                    v-model="step.name"
                    type="text"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Instructions for Agent</label>
                  <textarea
                    v-model="step.message"
                    rows="3"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    :placeholder="step.messagePlaceholder"
                  />
                </div>

                <div class="flex gap-4">
                  <div class="w-32">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Timeout</label>
                    <select
                      v-model="step.timeout"
                      class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    >
                      <option value="5m">5 minutes</option>
                      <option value="10m">10 minutes</option>
                      <option value="15m">15 minutes</option>
                      <option value="30m">30 minutes</option>
                      <option value="1h">1 hour</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 4: Review -->
        <div v-else-if="currentStep === 3" class="p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Review and create</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">Review your process before creating it</p>

          <div class="space-y-6">
            <!-- Process Name -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Process Name</label>
              <input
                v-model="wizardState.processName"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="my-workflow"
              />
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Lowercase, no spaces</p>
            </div>

            <!-- Flow Preview -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Workflow Preview</label>
              <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <ProcessFlowPreview
                  :yaml-content="generatedYaml"
                  :validation-errors="[]"
                  height="250px"
                />
              </div>
            </div>

            <!-- YAML Preview (Collapsible) -->
            <div>
              <button
                @click="showYamlPreview = !showYamlPreview"
                class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400"
              >
                <ChevronDownIcon
                  class="h-4 w-4 transition-transform"
                  :class="showYamlPreview ? 'rotate-180' : ''"
                />
                {{ showYamlPreview ? 'Hide' : 'Show' }} generated YAML
              </button>
              <div v-if="showYamlPreview" class="mt-2">
                <pre class="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs overflow-x-auto max-h-64">{{ generatedYaml }}</pre>
              </div>
            </div>

            <!-- Options -->
            <div class="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <input
                id="runImmediately"
                v-model="wizardState.runImmediately"
                type="checkbox"
                class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label for="runImmediately" class="text-sm text-gray-700 dark:text-gray-300">
                Run immediately after creation
              </label>
            </div>
          </div>
        </div>

        <!-- Navigation Footer -->
        <div class="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <button
            v-if="currentStep > 0"
            @click="prevStep"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors"
          >
            ← Back
          </button>
          <div v-else></div>

          <div class="flex items-center gap-3">
            <button
              @click="handleCancel"
              class="px-4 py-2 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              Cancel
            </button>

            <button
              v-if="currentStep < steps.length - 1"
              @click="nextStep"
              :disabled="!canProceed"
              class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>

            <button
              v-else
              @click="createProcess"
              :disabled="!canProceed || creating"
              class="px-6 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <span v-if="creating" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Creating...
              </span>
              <span v-else>
                <SparklesIcon class="h-4 w-4 inline mr-1" />
                Create Process
              </span>
            </button>
          </div>
        </div>
      </div>

      <!-- Cancel Confirmation Dialog -->
      <ConfirmDialog
        v-if="showCancelConfirm"
        :visible="true"
        title="Cancel Wizard"
        message="Are you sure you want to cancel? Your progress will be lost."
        confirm-text="Yes, Cancel"
        variant="warning"
        @confirm="confirmCancel"
        @cancel="showCancelConfirm = false"
      />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useProcessesStore } from '../stores/processes'
import { useOnboarding } from '../composables/useOnboarding'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import ProcessFlowPreview from '../components/ProcessFlowPreview.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import api from '../api'
import {
  ArrowLeftIcon,
  CheckIcon,
  CheckCircleIcon,
  PlusIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  Squares2X2Icon,
  SparklesIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ClipboardDocumentCheckIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/vue/24/outline'

const router = useRouter()
const processesStore = useProcessesStore()
const { celebrateCompletion } = useOnboarding()

// Steps definition
const steps = [
  { title: 'Goal' },
  { title: 'Agents' },
  { title: 'Customize' },
  { title: 'Review' },
]

// Goal options with template structures
const goalOptions = [
  {
    id: 'content',
    title: 'Content Creation',
    description: 'Research, write, and review content with AI agents',
    icon: DocumentTextIcon,
    iconBg: 'bg-blue-100 dark:bg-blue-900/30',
    iconColor: 'text-blue-600 dark:text-blue-400',
    hasApproval: false,
    steps: [
      { id: 'research', name: 'Research Topic', description: 'Gather information and facts', message: 'Research the following topic thoroughly:\n\n{{input.topic}}\n\nProvide key facts, statistics, and insights.', messagePlaceholder: 'Research instructions...', timeout: '10m' },
      { id: 'write', name: 'Write Content', description: 'Create the content based on research', message: 'Write engaging content about {{input.topic}} using this research:\n\n{{steps.research.output}}', messagePlaceholder: 'Writing instructions...', timeout: '15m' },
      { id: 'review', name: 'Review & Edit', description: 'Review and improve the content', message: 'Review and improve this content:\n\n{{steps.write.output}}\n\nCheck for clarity, accuracy, and engagement.', messagePlaceholder: 'Review instructions...', timeout: '10m' },
    ],
  },
  {
    id: 'data',
    title: 'Data Processing',
    description: 'Collect, analyze, and generate reports from data',
    icon: ChartBarIcon,
    iconBg: 'bg-green-100 dark:bg-green-900/30',
    iconColor: 'text-green-600 dark:text-green-400',
    hasApproval: false,
    steps: [
      { id: 'collect', name: 'Collect Data', description: 'Gather data from sources', message: 'Collect and prepare data for analysis.\n\nData source: {{input.data_source}}\nTime range: {{input.time_range | default("last 7 days")}}', messagePlaceholder: 'Data collection instructions...', timeout: '10m' },
      { id: 'analyze', name: 'Analyze Data', description: 'Process and analyze the data', message: 'Analyze the collected data:\n\n{{steps.collect.output}}\n\nIdentify trends, patterns, and key insights.', messagePlaceholder: 'Analysis instructions...', timeout: '15m' },
      { id: 'report', name: 'Generate Report', description: 'Create a summary report', message: 'Generate a comprehensive report based on the analysis:\n\n{{steps.analyze.output}}', messagePlaceholder: 'Report generation instructions...', timeout: '10m' },
    ],
  },
  {
    id: 'approval',
    title: 'Approval Workflow',
    description: 'Request, review, and approve with human checkpoints',
    icon: ClipboardDocumentCheckIcon,
    iconBg: 'bg-amber-100 dark:bg-amber-900/30',
    iconColor: 'text-amber-600 dark:text-amber-400',
    hasApproval: true,
    steps: [
      { id: 'prepare', name: 'Prepare Request', description: 'Prepare the approval request', message: 'Prepare the following request for approval:\n\n{{input.request_details}}\n\nSummarize key points and requirements.', messagePlaceholder: 'Request preparation instructions...', timeout: '10m' },
      { id: 'review', name: 'Human Review', description: 'Await human approval', type: 'human_approval', message: '', timeout: '24h' },
      { id: 'notify', name: 'Send Notification', description: 'Notify about the decision', message: 'Send a notification about the approval decision:\n\nDecision: {{steps.review.output.decision}}\nComments: {{steps.review.output.comments}}', messagePlaceholder: 'Notification instructions...', timeout: '5m' },
    ],
  },
  {
    id: 'custom',
    title: 'Custom Workflow',
    description: 'Start from scratch with a blank template',
    icon: WrenchScrewdriverIcon,
    iconBg: 'bg-gray-100 dark:bg-gray-700',
    iconColor: 'text-gray-600 dark:text-gray-400',
    hasApproval: false,
    steps: [
      { id: 'step-1', name: 'Step 1', description: 'First step of your workflow', message: 'Your instructions here.\n\nUse {{input.variable}} to reference input data.', messagePlaceholder: 'Step instructions...', timeout: '10m' },
    ],
  },
]

// State
const currentStep = ref(0)
const creating = ref(false)
const showYamlPreview = ref(false)
const showCancelConfirm = ref(false)
const availableAgents = ref([])

const wizardState = reactive({
  selectedGoal: null,
  steps: [],
  processName: '',
  runImmediately: false,
})

// Computed
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return wizardState.selectedGoal !== null
    case 1:
      return wizardState.steps.every(s => s.agent || s.type === 'human_approval')
    case 2:
      return wizardState.steps.every(s => s.name.trim())
    case 3:
      return wizardState.processName.trim().length > 0
    default:
      return true
  }
})

const generatedYaml = computed(() => {
  return generateYamlFromWizard(wizardState)
})

// Methods
function selectGoal(goal) {
  wizardState.selectedGoal = goal
  // Clone steps with agent field
  wizardState.steps = goal.steps.map(s => ({
    ...s,
    agent: '',
  }))
  // Generate default process name
  const timestamp = Date.now().toString(36).slice(-4)
  wizardState.processName = `${goal.id}-workflow-${timestamp}`
}

function nextStep() {
  if (canProceed.value && currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function handleCancel() {
  if (wizardState.selectedGoal) {
    showCancelConfirm.value = true
  } else {
    router.push('/processes')
  }
}

function confirmCancel() {
  showCancelConfirm.value = false
  router.push('/processes')
}

function getAgentStatus(agentName) {
  const agent = availableAgents.value.find(a => a.name === agentName)
  return agent?.status || 'unknown'
}

async function loadAgents() {
  try {
    const response = await api.get('/api/agents')
    availableAgents.value = response.data || []
  } catch (error) {
    console.error('Failed to load agents:', error)
    availableAgents.value = []
  }
}

function generateYamlFromWizard(state) {
  if (!state.selectedGoal || state.steps.length === 0) {
    return '# Select a goal to generate YAML'
  }

  const lines = []
  lines.push(`name: ${state.processName || 'my-workflow'}`)
  lines.push('version: "1.0"')
  lines.push(`description: ${state.selectedGoal.title} workflow`)
  lines.push('')
  lines.push('triggers:')
  lines.push('  - type: manual')
  lines.push('    id: manual-trigger')
  lines.push('')
  lines.push('steps:')

  state.steps.forEach((step, index) => {
    lines.push(`  - id: ${step.id}`)
    lines.push(`    name: ${step.name}`)

    if (step.type === 'human_approval') {
      lines.push('    type: human_approval')
      lines.push('    title: Review Request')
      lines.push('    description: Please review and approve or reject this request')
      lines.push('    assignees:')
      lines.push('      - admin@example.com')
      if (index > 0) {
        lines.push('    depends_on:')
        lines.push(`      - ${state.steps[index - 1].id}`)
      }
    } else {
      lines.push('    type: agent_task')
      lines.push(`    agent: ${step.agent || 'your-agent'}`)
      lines.push('    message: |')
      const messageLines = (step.message || step.messagePlaceholder || 'Your instructions here.').split('\n')
      messageLines.forEach(ml => {
        lines.push(`      ${ml}`)
      })
      lines.push(`    timeout: ${step.timeout || '10m'}`)
      if (index > 0) {
        lines.push('    depends_on:')
        lines.push(`      - ${state.steps[index - 1].id}`)
      }
    }
    lines.push('')
  })

  // Add outputs
  const lastStep = state.steps[state.steps.length - 1]
  lines.push('outputs:')
  lines.push('  - name: result')
  lines.push(`    source: "{{steps.${lastStep.id}.output}}"`)

  return lines.join('\n')
}

async function createProcess() {
  if (!canProceed.value || creating.value) return

  creating.value = true
  try {
    const yaml = generatedYaml.value
    const created = await processesStore.createProcess(yaml)

    // Celebrate onboarding completion
    celebrateCompletion('createProcess')

    // Execute immediately if requested
    if (wizardState.runImmediately) {
      try {
        await api.post(`/api/processes/${created.id}/execute`, { input_data: {} })
      } catch (execError) {
        console.warn('Failed to execute immediately:', execError)
      }
    }

    // Navigate to editor
    router.push(`/processes/${created.id}`)
  } catch (error) {
    console.error('Failed to create process:', error)
    alert(error.response?.data?.detail || 'Failed to create process')
  } finally {
    creating.value = false
  }
}

// Lifecycle
onMounted(async () => {
  await loadAgents()
})
</script>

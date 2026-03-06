<template>
  <div class="process-flow-preview bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col" :style="{ height }">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 py-1.5 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
      <h3 class="text-xs font-medium text-gray-700 dark:text-gray-300">Process Flow</h3>
      <button
        @click="orientation = orientation === 'horizontal' ? 'vertical' : 'horizontal'"
        class="p-0.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded"
        :title="orientation === 'horizontal' ? 'Switch to vertical' : 'Switch to horizontal'"
      >
        <component :is="orientation === 'horizontal' ? ArrowsUpDownIcon : ArrowsRightLeftIcon" class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- Flow diagram -->
    <div class="flex-1 p-2 overflow-auto">
      <!-- Error state -->
      <div v-if="parseError" class="flex items-center gap-2 text-red-600 dark:text-red-400 text-sm">
        <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0" />
        <span>{{ parseError }}</span>
      </div>

      <!-- Empty state -->
      <div v-else-if="!steps.length" class="text-center text-gray-500 dark:text-gray-400 text-sm py-8">
        Add steps to see the flow diagram
      </div>

      <!-- Swimlane Flow diagram -->
      <div v-else class="flex flex-col items-center gap-1 w-full">
        <!-- Start node -->
        <div class="flex-shrink-0">
          <div class="w-6 h-6 rounded-full bg-green-100 dark:bg-green-900/30 border-2 border-green-500 flex items-center justify-center">
            <PlayIcon class="w-3 h-3 text-green-600 dark:text-green-400" />
          </div>
        </div>

        <!-- Levels (swimlanes) -->
        <template v-for="(levelSteps, levelIndex) in stepsByLevel" :key="levelIndex">
          <!-- Arrow down to this level -->
          <div class="flex flex-col items-center">
            <div class="w-0.5 h-2 bg-gray-300 dark:bg-gray-600"></div>
            <div class="w-0 h-0 border-l-[3px] border-r-[3px] border-t-[3px] border-l-transparent border-r-transparent border-t-gray-300 dark:border-t-gray-600"></div>
          </div>

          <!-- Swimlane container -->
          <div 
            class="relative flex items-center justify-center gap-2"
            :class="{ 
              'px-2 py-1.5 rounded-lg bg-purple-50/50 dark:bg-purple-900/10 border border-dashed border-purple-300 dark:border-purple-700': levelSteps.length > 1 
            }"
          >
            <!-- Parallel indicator (inside the container) -->
            <span v-if="levelSteps.length > 1" class="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-medium text-purple-500 dark:text-purple-400 bg-gray-50 dark:bg-gray-900 px-1 whitespace-nowrap">
              ⫘ Parallel
            </span>

            <!-- Steps in this level -->
            <div 
              v-for="step in levelSteps" 
              :key="step.id"
              class="flex-shrink-0 group relative"
              :class="{ 'ring-2 ring-red-400 rounded': hasError(step.id) }"
            >
              <div 
                class="px-2 py-1.5 rounded border-2 min-w-[80px] max-w-[110px] text-center transition-colors"
                :class="getStepClasses(step)"
              >
                <!-- Step name only (compact) -->
                <div class="text-[11px] font-medium truncate" :title="step.id">
                  {{ step.id }}
                </div>
              </div>

              <!-- Error tooltip -->
              <div
                v-if="hasError(step.id)"
                class="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10"
              >
                {{ getError(step.id) }}
              </div>
            </div>
          </div>
        </template>

        <!-- Arrow to end -->
        <div class="flex flex-col items-center">
          <div class="w-0.5 h-2 bg-gray-300 dark:bg-gray-600"></div>
          <div class="w-0 h-0 border-l-[3px] border-r-[3px] border-t-[3px] border-l-transparent border-r-transparent border-t-gray-300 dark:border-t-gray-600"></div>
        </div>

        <!-- End node -->
        <div class="flex-shrink-0">
          <div class="w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-700 border-2 border-gray-400 dark:border-gray-500 flex items-center justify-center">
            <StopIcon class="w-3 h-3 text-gray-500 dark:text-gray-400" />
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="px-3 py-1 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center gap-3 text-[10px] text-gray-500 dark:text-gray-400 flex-shrink-0">
      <div class="flex items-center gap-1">
        <div class="w-2 h-2 rounded border border-blue-500 bg-blue-50 dark:bg-blue-900/30"></div>
        <span>Agent</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-2 h-2 rounded border border-purple-500 bg-purple-50 dark:bg-purple-900/30"></div>
        <span>Approval</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-2 h-2 rounded border border-amber-500 bg-amber-50 dark:bg-amber-900/30"></div>
        <span>Gateway</span>
      </div>
      <div class="flex items-center gap-1">
        <span class="text-purple-500">⫘</span>
        <span>Parallel</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  PlayIcon,
  StopIcon,
  CpuChipIcon,
  UserIcon,
  ArrowsRightLeftIcon,
  ArrowsUpDownIcon,
  ExclamationCircleIcon,
  ClockIcon,
} from '@heroicons/vue/24/outline'
import yaml from 'js-yaml'

const props = defineProps({
  yamlContent: {
    type: String,
    default: ''
  },
  validationErrors: {
    type: Array,
    default: () => []
  },
  height: {
    type: String,
    default: '100%'
  }
})

// State
const orientation = ref('vertical')  // Default to vertical
const parseError = ref(null)
const steps = ref([])

// Parse YAML to extract steps
watch(() => props.yamlContent, (newContent) => {
  parseYaml(newContent)
}, { immediate: true })

function parseYaml(content) {
  if (!content?.trim()) {
    steps.value = []
    parseError.value = null
    return
  }

  try {
    const parsed = yaml.load(content)
    if (parsed?.steps && Array.isArray(parsed.steps)) {
      steps.value = parsed.steps.map(step => ({
        id: step.id || 'unnamed',
        type: step.type || 'unknown',
        depends_on: step.depends_on || [],
      }))
      parseError.value = null
    } else if (parsed?.steps && typeof parsed.steps === 'object') {
      // Handle object-style steps
      steps.value = Object.entries(parsed.steps).map(([id, config]) => ({
        id,
        type: config?.type || 'unknown',
        depends_on: config?.depends_on || [],
      }))
      parseError.value = null
    } else {
      steps.value = []
      parseError.value = null
    }
  } catch (e) {
    parseError.value = e.message
    steps.value = []
  }
}

// Calculate parallel levels for steps (same algorithm as backend)
const stepLevels = computed(() => {
  const levels = {}
  
  // Entry steps (no dependencies) are level 0
  for (const step of steps.value) {
    if (!step.depends_on?.length) {
      levels[step.id] = 0
    }
  }
  
  // Calculate levels for remaining steps iteratively
  let changed = true
  let iterations = 0
  const maxIterations = steps.value.length + 1
  
  while (changed && iterations < maxIterations) {
    changed = false
    iterations++
    
    for (const step of steps.value) {
      if (step.id in levels) continue
      
      // Check if all dependencies have levels
      const depLevels = []
      let allResolved = true
      
      for (const dep of (step.depends_on || [])) {
        if (dep in levels) {
          depLevels.push(levels[dep])
        } else {
          allResolved = false
          break
        }
      }
      
      if (allResolved && depLevels.length > 0) {
        levels[step.id] = Math.max(...depLevels) + 1
        changed = true
      }
    }
  }
  
  return levels
})

// Group steps by level for swimlane rendering
const stepsByLevel = computed(() => {
  const groups = {}
  
  for (const step of steps.value) {
    const level = stepLevels.value[step.id] ?? 0
    if (!groups[level]) {
      groups[level] = []
    }
    groups[level].push(step)
  }
  
  // Convert to sorted array of arrays
  const sortedLevels = Object.keys(groups)
    .map(Number)
    .sort((a, b) => a - b)
  
  return sortedLevels.map(level => groups[level])
})

// Helper functions
function getStepClasses(step) {
  const typeClasses = {
    agent_task: 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    human_approval: 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
    gateway: 'border-amber-500 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
    timer: 'border-gray-500 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
  }
  return typeClasses[step.type] || 'border-gray-400 bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
}

function getStepIcon(type) {
  const icons = {
    agent_task: CpuChipIcon,
    human_approval: UserIcon,
    gateway: ArrowsRightLeftIcon,
    timer: ClockIcon,
  }
  return icons[type] || CpuChipIcon
}

function formatType(type) {
  if (!type) return 'UNKNOWN'
  return type.replace(/_/g, ' ').substring(0, 12)
}

function hasError(stepId) {
  return props.validationErrors.some(e => 
    e.message?.includes(stepId) || e.path?.includes(stepId)
  )
}

function getError(stepId) {
  const error = props.validationErrors.find(e => 
    e.message?.includes(stepId) || e.path?.includes(stepId)
  )
  return error?.message || 'Validation error'
}
</script>

<style scoped>
.process-flow-preview {
  min-height: 150px;
}
</style>

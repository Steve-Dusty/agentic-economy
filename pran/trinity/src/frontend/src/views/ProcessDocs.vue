<template>
  <!-- Notification Toast -->
  <Teleport to="body">
    <div
      v-if="notification"
      class="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg shadow-lg text-sm font-medium transition-all duration-300"
      :class="notification.type === 'success'
        ? 'bg-green-600 text-white'
        : 'bg-indigo-600 text-white'"
    >
      {{ notification.message }}
    </div>
  </Teleport>

  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div class="flex gap-6">
        <!-- Sidebar -->
        <aside class="hidden lg:block w-64 flex-shrink-0">
          <div class="sticky top-6">
            <!-- Search (placeholder for E21-03) -->
            <div class="mb-4">
              <div class="relative">
                <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search docs..."
                  class="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  @focus="showSearchMessage"
                />
              </div>
            </div>

            <!-- Navigation Tree -->
            <nav class="space-y-1">
              <div v-for="section in docsIndex?.sections" :key="section.id" class="mb-4">
                <button
                  @click="toggleSection(section.id)"
                  class="flex items-center justify-between w-full text-left px-2 py-1.5 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md"
                >
                  <span>{{ section.title }}</span>
                  <ChevronDownIcon
                    class="h-4 w-4 transition-transform"
                    :class="{ '-rotate-90': !expandedSections.includes(section.id) }"
                  />
                </button>

                <div v-if="expandedSections.includes(section.id)" class="ml-2 mt-1 space-y-0.5">
                  <router-link
                    v-for="doc in section.docs"
                    :key="doc.slug"
                    :to="`/processes/docs/${doc.slug}`"
                    class="block px-3 py-1.5 text-sm rounded-md transition-colors"
                    :class="[
                      currentSlug === doc.slug
                        ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-medium'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                    ]"
                  >
                    {{ doc.title }}
                  </router-link>
                </div>
              </div>
            </nav>

            <!-- Restart Onboarding Section -->
            <div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <p class="text-xs text-gray-500 dark:text-gray-400 mb-2 px-2">Onboarding</p>
              <button
                v-if="!showRestartConfirm"
                @click="showRestartConfirm = true"
                class="flex items-center gap-2 w-full px-3 py-2 text-sm text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-md transition-colors font-medium"
              >
                <ArrowPathIcon class="h-4 w-4" />
                Restart Getting Started
              </button>
              <!-- Confirmation -->
              <div v-else class="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <p class="text-sm text-amber-800 dark:text-amber-200 mb-2">Reset your onboarding progress?</p>
                <div class="flex gap-2">
                  <button
                    @click="confirmRestartOnboarding"
                    class="flex-1 px-2 py-1 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded transition-colors"
                  >
                    Yes, restart
                  </button>
                  <button
                    @click="showRestartConfirm = false"
                    class="flex-1 px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- Mobile sidebar toggle -->
        <button
          @click="showMobileSidebar = true"
          class="lg:hidden fixed bottom-4 left-4 z-40 p-3 bg-indigo-600 text-white rounded-full shadow-lg"
        >
          <Bars3Icon class="h-6 w-6" />
        </button>

        <!-- Mobile sidebar overlay -->
        <div
          v-if="showMobileSidebar"
          class="lg:hidden fixed inset-0 z-50 bg-gray-900/50"
          @click="showMobileSidebar = false"
        >
          <aside class="w-72 h-full bg-white dark:bg-gray-800 p-4 overflow-y-auto" @click.stop>
            <div class="flex justify-between items-center mb-4">
              <h3 class="font-semibold text-gray-900 dark:text-white">Documentation</h3>
              <button @click="showMobileSidebar = false" class="text-gray-500">
                <XMarkIcon class="h-5 w-5" />
              </button>
            </div>

            <nav class="space-y-1">
              <div v-for="section in docsIndex?.sections" :key="section.id" class="mb-4">
                <button
                  @click="toggleSection(section.id)"
                  class="flex items-center justify-between w-full text-left px-2 py-1.5 text-sm font-semibold text-gray-700 dark:text-gray-300"
                >
                  <span>{{ section.title }}</span>
                  <ChevronDownIcon
                    class="h-4 w-4 transition-transform"
                    :class="{ '-rotate-90': !expandedSections.includes(section.id) }"
                  />
                </button>

                <div v-if="expandedSections.includes(section.id)" class="ml-2 mt-1 space-y-0.5">
                  <router-link
                    v-for="doc in section.docs"
                    :key="doc.slug"
                    :to="`/processes/docs/${doc.slug}`"
                    class="block px-3 py-1.5 text-sm rounded-md"
                    :class="[
                      currentSlug === doc.slug
                        ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-medium'
                        : 'text-gray-600 dark:text-gray-400'
                    ]"
                    @click="showMobileSidebar = false"
                  >
                    {{ doc.title }}
                  </router-link>
                </div>
              </div>
            </nav>

            <!-- Mobile: Restart Onboarding -->
            <div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                @click="confirmRestartOnboarding(); showMobileSidebar = false"
                class="flex items-center gap-2 w-full px-3 py-2 text-sm text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-md transition-colors"
              >
                <ArrowPathIcon class="h-4 w-4" />
                Restart Getting Started
              </button>
            </div>
          </aside>
        </div>

        <!-- Main Content -->
        <article class="flex-1 min-w-0">
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <!-- Loading state -->
            <div v-if="loading" class="p-8">
              <div class="animate-pulse space-y-4">
                <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/6"></div>
              </div>
            </div>

            <!-- Error state -->
            <div v-else-if="error" class="p-8 text-center">
              <ExclamationCircleIcon class="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Failed to load documentation</h3>
              <p class="text-gray-500 dark:text-gray-400 mb-4">{{ error }}</p>
              <button @click="loadContent" class="text-indigo-600 hover:underline">Try again</button>
            </div>

            <!-- Content -->
            <div v-else class="p-8">
              <!-- Breadcrumb -->
              <nav v-if="currentSlug" class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                <router-link to="/processes/docs" class="hover:text-indigo-600">Docs</router-link>
                <span class="mx-2">/</span>
                <span class="text-gray-700 dark:text-gray-300">{{ currentTitle }}</span>
              </nav>

              <!-- Rendered markdown -->
              <div
                class="prose prose-indigo dark:prose-invert max-w-none
                  prose-headings:scroll-mt-4
                  prose-h1:text-3xl prose-h1:font-bold prose-h1:mb-6
                  prose-h2:text-2xl prose-h2:font-semibold prose-h2:mt-10 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-gray-200 dark:prose-h2:border-gray-700
                  prose-h3:text-xl prose-h3:font-semibold prose-h3:mt-8 prose-h3:mb-3
                  prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-p:leading-relaxed
                  prose-a:text-indigo-600 dark:prose-a:text-indigo-400 prose-a:no-underline hover:prose-a:underline
                  prose-code:text-sm prose-code:bg-gray-100 dark:prose-code:bg-gray-900 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono
                  prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-pre:overflow-x-auto
                  prose-table:text-sm
                  prose-th:text-left prose-th:font-semibold prose-th:text-gray-900 dark:prose-th:text-gray-100 prose-th:bg-gray-50 dark:prose-th:bg-gray-800
                  prose-td:text-gray-700 dark:prose-td:text-gray-300
                  prose-ul:list-disc prose-ul:pl-5
                  prose-ol:list-decimal prose-ol:pl-5
                  prose-li:text-gray-700 dark:prose-li:text-gray-300
                "
                v-html="renderedContent"
              />
            </div>

            <!-- Footer navigation -->
            <div v-if="!loading && !error && (prevDoc || nextDoc)" class="px-8 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-between">
              <router-link
                v-if="prevDoc"
                :to="`/processes/docs/${prevDoc.slug}`"
                class="flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-indigo-600"
              >
                <ArrowLeftIcon class="h-4 w-4 mr-2" />
                {{ prevDoc.title }}
              </router-link>
              <div v-else></div>

              <router-link
                v-if="nextDoc"
                :to="`/processes/docs/${nextDoc.slug}`"
                class="flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-indigo-600"
              >
                {{ nextDoc.title }}
                <ArrowRightIcon class="h-4 w-4 ml-2" />
              </router-link>
            </div>
          </div>
        </article>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import {
  MagnifyingGlassIcon,
  ChevronDownIcon,
  Bars3Icon,
  XMarkIcon,
  ExclamationCircleIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline'
import { useOnboarding } from '../composables/useOnboarding'

const route = useRoute()
const { resetOnboarding } = useOnboarding()

// State
const loading = ref(true)
const error = ref(null)
const docsIndex = ref(null)
const markdownContent = ref('')
const expandedSections = ref(['getting-started']) // Start with first section expanded
const showMobileSidebar = ref(false)
const notification = ref(null)
const showRestartConfirm = ref(false)

// Configure marked for syntax highlighting
marked.setOptions({
  gfm: true,
  breaks: true,
})

// Computed
const currentSlug = computed(() => {
  const slug = route.params.slug
  if (Array.isArray(slug)) {
    return slug.join('/')
  }
  return slug || 'getting-started/what-are-processes' // Default doc
})

const currentTitle = computed(() => {
  if (!docsIndex.value) return ''
  for (const section of docsIndex.value.sections) {
    const doc = section.docs.find(d => d.slug === currentSlug.value)
    if (doc) return doc.title
  }
  return ''
})

const renderedContent = computed(() => {
  if (!markdownContent.value) return ''
  return marked(markdownContent.value)
})

// Navigation helpers
const allDocs = computed(() => {
  if (!docsIndex.value) return []
  return docsIndex.value.sections.flatMap(s => s.docs)
})

const currentIndex = computed(() => {
  return allDocs.value.findIndex(d => d.slug === currentSlug.value)
})

const prevDoc = computed(() => {
  if (currentIndex.value <= 0) return null
  return allDocs.value[currentIndex.value - 1]
})

const nextDoc = computed(() => {
  if (currentIndex.value < 0 || currentIndex.value >= allDocs.value.length - 1) return null
  return allDocs.value[currentIndex.value + 1]
})

// Methods
const toggleSection = (sectionId) => {
  const idx = expandedSections.value.indexOf(sectionId)
  if (idx >= 0) {
    expandedSections.value.splice(idx, 1)
  } else {
    expandedSections.value.push(sectionId)
  }
}

const showSearchMessage = () => {
  // Placeholder for E21-03 search functionality
  notification.value = { message: 'Search coming soon!', type: 'info' }
  setTimeout(() => notification.value = null, 2000)
}

const confirmRestartOnboarding = () => {
  resetOnboarding()
  showRestartConfirm.value = false
  notification.value = { message: 'Onboarding checklist has been reset!', type: 'success' }
  setTimeout(() => notification.value = null, 3000)
}

const loadIndex = async () => {
  try {
    const response = await fetch('/api/docs/index')
    if (!response.ok) throw new Error('Failed to load docs index')
    docsIndex.value = await response.json()

    // Expand section containing current doc
    if (docsIndex.value?.sections) {
      for (const section of docsIndex.value.sections) {
        if (section.docs.some(d => d.slug === currentSlug.value)) {
          if (!expandedSections.value.includes(section.id)) {
            expandedSections.value.push(section.id)
          }
        }
      }
    }
  } catch (e) {
    console.error('Failed to load docs index:', e)
    // Fallback to hardcoded index
    docsIndex.value = {
      sections: [
        {
          id: 'getting-started',
          title: 'Getting Started',
          docs: [
            { slug: 'getting-started/what-are-processes', title: 'What are Processes?' },
            { slug: 'getting-started/first-process', title: 'Your First Process' },
            { slug: 'getting-started/step-types', title: 'Understanding Step Types' }
          ]
        },
        {
          id: 'reference',
          title: 'Reference',
          docs: [
            { slug: 'reference/yaml-schema', title: 'YAML Schema' },
            { slug: 'reference/variables', title: 'Variable Interpolation' },
            { slug: 'reference/triggers', title: 'Triggers' },
            { slug: 'reference/error-handling', title: 'Error Handling' }
          ]
        },
        {
          id: 'troubleshooting',
          title: 'Troubleshooting',
          docs: [
            { slug: 'troubleshooting/common-errors', title: 'Common Errors' }
          ]
        }
      ]
    }
  }
}

const loadContent = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await fetch(`/api/docs/content/${currentSlug.value}`)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Documentation page not found')
      }
      throw new Error('Failed to load documentation')
    }
    const data = await response.json()
    markdownContent.value = data.content
  } catch (e) {
    console.error('Failed to load doc content:', e)
    error.value = e.message

    // Show placeholder content for missing docs
    if (e.message.includes('not found')) {
      markdownContent.value = `# ${currentTitle.value || 'Documentation'}

This documentation page is coming soon.

Return to [Getting Started](/processes/docs/getting-started/what-are-processes) to learn the basics.`
      error.value = null
    }
  } finally {
    loading.value = false
  }
}

// Watch for route changes
watch(() => currentSlug.value, () => {
  loadContent()
  // Expand section containing new doc
  if (docsIndex.value?.sections) {
    for (const section of docsIndex.value.sections) {
      if (section.docs.some(d => d.slug === currentSlug.value)) {
        if (!expandedSections.value.includes(section.id)) {
          expandedSections.value.push(section.id)
        }
      }
    }
  }
}, { immediate: false })

// Initialize
onMounted(async () => {
  await loadIndex()
  await loadContent()
})
</script>

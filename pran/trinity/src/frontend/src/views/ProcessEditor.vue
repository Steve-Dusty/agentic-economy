<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <NavBar />
    <ProcessSubNav />

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 sm:px-0">
        <!-- Notification Toast -->
        <div v-if="notification"
          :class="[
            'fixed top-20 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300',
            notification.type === 'success' ? 'bg-green-100 dark:bg-green-900/50 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300'
          ]"
        >
          {{ notification.message }}
        </div>

        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <div class="flex items-center gap-4">
            <router-link
              to="/processes"
              class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Back to processes"
            >
              <ArrowLeftIcon class="h-5 w-5" />
            </router-link>
            <div>
              <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                {{ isNew ? 'Create Process' : 'Edit Process' }}
              </h1>
              <p v-if="!isNew && process" class="text-sm text-gray-500 dark:text-gray-400">
                {{ process.name }} v{{ process.version }}
                <span v-if="process.status" :class="[
                  'ml-2 px-2 py-0.5 text-xs font-medium rounded-full',
                  process.status === 'published'
                    ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
                    : process.status === 'archived'
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                      : 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300'
                ]">
                  {{ process.status }}
                </span>
              </p>
            </div>
          </div>

          <!-- Action buttons (hidden during template selection) -->
          <div v-if="!isNew || !showTemplateSelector" class="flex items-center gap-3">
            <!-- Validate button -->
            <button
              @click="validateProcess"
              :disabled="saving || validating"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
            >
              <span v-if="validating" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Validating...
              </span>
              <span v-else class="flex items-center gap-2">
                <CheckCircleIcon class="h-4 w-4" />
                Validate
              </span>
            </button>

            <!-- Save button (only for new or draft) -->
            <button
              v-if="isNew || process?.status === 'draft'"
              @click="saveProcess"
              :disabled="saving || hasErrors"
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <span v-if="saving" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Saving...
              </span>
              <span v-else>Save</span>
            </button>

            <!-- Create New Version button (for published/archived) -->
            <button
              v-if="!isNew && process?.status !== 'draft'"
              @click="createNewVersion"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              title="Published processes are immutable. Create a new draft version to make changes."
            >
              <DocumentDuplicateIcon class="h-4 w-4" />
              <span v-if="saving">Creating...</span>
              <span v-else>New Version</span>
            </button>

            <!-- Publish button (only for draft) -->
            <button
              v-if="!isNew && process?.status === 'draft'"
              @click="publishProcess"
              :disabled="saving || hasErrors"
              class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Publish
            </button>

            <!-- Execute button (only for published) -->
            <button
              v-if="!isNew && process?.status === 'published'"
              @click="executeProcess"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <PlayIcon class="h-4 w-4" />
              Execute
            </button>

            <!-- Archive button (only for published) -->
            <button
              v-if="!isNew && process?.status === 'published'"
              @click="showArchiveConfirm = true"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors flex items-center gap-2"
              title="Archive this process (stops executions, preserves history)"
            >
              <ArchiveBoxIcon class="h-4 w-4" />
              Archive
            </button>

            <!-- Save as Template button (only for published) -->
            <button
              v-if="!isNew && process?.status === 'published'"
              @click="showSaveTemplateDialog = true"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/30 border border-teal-300 dark:border-teal-700 rounded-lg hover:bg-teal-100 dark:hover:bg-teal-900/50 disabled:opacity-50 transition-colors flex items-center gap-2"
              title="Save this process as a reusable template"
            >
              <DocumentDuplicateIcon class="h-4 w-4" />
              Save as Template
            </button>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="flex justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500 dark:text-gray-400">
            <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading process...</span>
          </div>
        </div>

        <!-- Template Selector (for new processes) -->
        <div v-else-if="isNew && showTemplateSelector" class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <TemplateSelector
            :selected-id="selectedTemplateId"
            @select="handleTemplateSelect"
          />

          <!-- Wizard suggestion -->
          <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                  <SparklesIcon class="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900 dark:text-white">New to processes?</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">Use our guided wizard to create your first process step-by-step</p>
                </div>
              </div>
              <router-link
                to="/processes/wizard"
                class="px-4 py-2 text-sm font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors flex items-center gap-2"
              >
                <SparklesIcon class="h-4 w-4" />
                Use Wizard
              </router-link>
            </div>
          </div>

          <div class="mt-6 flex justify-end gap-3">
            <button
              @click="proceedWithTemplate"
              :disabled="loadingTemplate"
              class="px-6 py-2.5 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <span v-if="loadingTemplate" class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Loading...
              </span>
              <span v-else>Continue</span>
            </button>
          </div>
        </div>

        <!-- Editor -->
        <div v-else class="space-y-4">
          <!-- View tabs -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <div class="border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <nav class="flex -mb-px">
                <button
                  @click="activeTab = 'chat'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5',
                    activeTab === 'chat'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
                  ]"
                >
                  <SparklesIcon class="h-4 w-4" />
                  Chat
                </button>
                <button
                  @click="activeTab = 'editor'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'editor'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
                  ]"
                >
                  Editor
                </button>
                <button
                  @click="activeTab = 'roles'"
                  :class="[
                    'px-6 py-3 text-sm font-medium border-b-2 transition-colors',
                    activeTab === 'roles'
                      ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
                  ]"
                >
                  Roles
                  <span v-if="parsedSteps.length > 0" class="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700">
                    {{ parsedSteps.length }}
                  </span>
                </button>
              </nav>
              <!-- Help panel toggle -->
              <button
                v-if="activeTab === 'editor'"
                @click="toggleHelpPanel"
                :class="[
                  'mr-3 p-2 rounded-lg transition-colors',
                  showHelpPanel
                    ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400'
                    : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                ]"
                title="Toggle help panel"
              >
                <QuestionMarkCircleIcon class="h-5 w-5" />
              </button>
            </div>
          </div>

          <!-- Chat Tab Content -->
          <div v-show="activeTab === 'chat'" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Chat Assistant -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden h-[600px]">
              <ProcessChatAssistant
                :validation-errors="validationErrors"
                :current-yaml="yamlContent"
                :selected-text="editorSelectedText"
                :process-status="process?.status || 'draft'"
                @yaml-update="handleYamlUpdate"
              />
            </div>

            <!-- Live YAML Preview -->
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
              <div class="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">YAML Preview</h3>
                <span v-if="yamlContent !== defaultYamlTemplate()" class="text-xs text-green-600 dark:text-green-400">
                  Modified
                </span>
              </div>
              <div class="p-4">
                <YamlEditor
                  v-model="yamlContent"
                  :validation-errors="validationErrors"
                  height="500px"
                  @save="saveProcess"
                  @change="handleChange"
                  @selection-change="handleEditorSelection"
                />
              </div>
            </div>
          </div>

          <!-- Editor Tab Content -->
          <div v-show="activeTab === 'editor'" class="flex gap-4">
            <!-- Main editor area -->
            <div class="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4">
              <!-- YAML Editor -->
              <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
                <div class="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                  <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">YAML Definition</h3>
                </div>
                <div class="p-4">
                  <YamlEditor
                    v-model="yamlContent"
                    :validation-errors="validationErrors"
                    height="450px"
                    @save="saveProcess"
                    @change="handleChange"
                    @cursor-context="handleCursorContext"
                  />
                </div>
              </div>

              <!-- Flow Preview -->
              <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
                <ProcessFlowPreview
                  :yaml-content="yamlContent"
                  :validation-errors="validationErrors"
                  height="450px"
                />
              </div>
            </div>

            <!-- Help Panel - Desktop (side panel) -->
            <EditorHelpPanel
              v-if="showHelpPanel"
              :visible="showHelpPanel"
              :help-content="currentHelpContent"
              @close="toggleHelpPanel"
              class="hidden xl:block"
              style="height: 530px;"
            />
          </div>

          <!-- Help Panel - Mobile (slide-over drawer) -->
          <Teleport to="body">
            <Transition name="slide-over">
              <div
                v-if="showHelpPanel"
                class="xl:hidden fixed inset-0 z-50"
              >
                <!-- Backdrop -->
                <div
                  class="absolute inset-0 bg-black/50"
                  @click="toggleHelpPanel"
                />
                <!-- Panel -->
                <div class="absolute right-0 top-0 h-full w-80 max-w-full">
                  <EditorHelpPanel
                    :visible="true"
                    :help-content="currentHelpContent"
                    @close="toggleHelpPanel"
                    class="h-full"
                  />
                </div>
              </div>
            </Transition>
          </Teleport>

          <!-- Roles Tab Content -->
          <div v-show="activeTab === 'roles'" class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden p-6">
            <RoleMatrix
              :steps="parsedSteps"
              :available-agents="availableAgents"
              :read-only="process?.status !== 'draft' && !isNew"
              @update:roles="handleRolesUpdate"
            />
          </div>

          <!-- Published/Archived notice -->
          <div v-if="!isNew && process?.status !== 'draft'" class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <div class="p-4">
              <div class="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
                <InformationCircleIcon class="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div class="text-sm text-amber-700 dark:text-amber-300">
                  <p class="font-medium mb-1">Read-Only Process</p>
                  <p class="text-xs text-amber-600 dark:text-amber-400">
                    This process is {{ process?.status }}. Published processes are immutable to ensure version consistency.
                    Click <strong>"New Version"</strong> to create a draft copy that you can edit.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Triggers section (for published processes with triggers) -->
          <div v-if="!isNew && process?.status === 'published' && parsedTriggers.length > 0" class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
              <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <LinkIcon class="h-4 w-4" />
                Triggers
              </h3>
            </div>
            <div class="p-4 space-y-3">
              <div
                v-for="trigger in parsedTriggers"
                :key="trigger.id"
                class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg"
              >
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 dark:text-white">{{ trigger.id }}</span>
                    <span
                      :class="[
                        'px-2 py-0.5 text-xs font-medium rounded-full',
                        trigger.enabled !== false
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                      ]"
                    >
                      {{ trigger.enabled !== false ? 'Enabled' : 'Disabled' }}
                    </span>
                    <span :class="[
                      'px-2 py-0.5 text-xs font-medium rounded-full',
                      trigger.type === 'schedule'
                        ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                        : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    ]">
                      {{ trigger.type || 'webhook' }}
                    </span>
                  </div>
                  <div v-if="trigger.description" class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {{ trigger.description }}
                  </div>
                  <!-- Webhook trigger details -->
                  <div v-if="!trigger.type || trigger.type === 'webhook'" class="mt-2">
                    <div class="flex items-center gap-2">
                      <code class="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded font-mono text-gray-600 dark:text-gray-300 truncate max-w-md">
                        {{ getWebhookUrl(trigger.id) }}
                      </code>
                      <button
                        @click="copyWebhookUrl(trigger.id)"
                        class="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Copy webhook URL"
                      >
                        <ClipboardDocumentIcon class="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <!-- Schedule trigger details -->
                  <div v-if="trigger.type === 'schedule'" class="mt-2 space-y-1">
                    <div class="flex items-center gap-4">
                      <div class="flex items-center gap-2">
                        <ClockIcon class="h-4 w-4 text-gray-400" />
                        <code class="text-xs bg-purple-50 dark:bg-purple-900/20 px-2 py-1 rounded font-mono text-purple-700 dark:text-purple-300">
                          {{ trigger.cron }}
                        </code>
                        <span v-if="getCronPresetLabel(trigger.cron)" class="text-xs text-gray-500 dark:text-gray-400">
                          ({{ getCronPresetLabel(trigger.cron) }})
                        </span>
                      </div>
                      <div v-if="trigger.timezone && trigger.timezone !== 'UTC'" class="text-xs text-gray-500 dark:text-gray-400">
                        {{ trigger.timezone }}
                      </div>
                    </div>
                    <div v-if="scheduleTriggerInfo[trigger.id]?.next_run_at" class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>Next run:</span>
                      <span class="text-gray-700 dark:text-gray-300">{{ formatScheduleTime(scheduleTriggerInfo[trigger.id].next_run_at) }}</span>
                    </div>
                    <div v-if="scheduleTriggerInfo[trigger.id]?.last_run_at" class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>Last run:</span>
                      <span>{{ formatScheduleTime(scheduleTriggerInfo[trigger.id].last_run_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                <span v-if="hasWebhookTriggers">Use webhook URLs to trigger this process externally via HTTP POST.</span>
                <span v-if="hasScheduleTriggers">
                  <span v-if="hasWebhookTriggers"> </span>Schedule triggers run automatically at the configured times.
                </span>
              </div>
            </div>
          </div>

          <!-- Help text -->
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            <div class="p-4">
              <div class="flex items-start gap-2 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50">
                <InformationCircleIcon class="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div class="text-sm text-blue-700 dark:text-blue-300">
                  <p class="font-medium mb-1">YAML Process Definition</p>
                  <p class="text-xs text-blue-600 dark:text-blue-400">
                    Define your process with steps, dependencies, and configurations.
                    Press <kbd class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-800 rounded text-xs">Cmd+S</kbd> to save.
                    The flow preview updates as you type.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Unsaved changes warning modal -->
        <ConfirmDialog
          v-if="showUnsavedWarning"
          :visible="true"
          title="Unsaved Changes"
          message="You have unsaved changes. Are you sure you want to leave?"
          confirm-text="Leave"
          @confirm="confirmLeave"
          @cancel="showUnsavedWarning = false"
        />

        <!-- Archive confirmation modal -->
        <ConfirmDialog
          v-if="showArchiveConfirm"
          :visible="true"
          title="Archive Process"
          :message="`Are you sure you want to archive '${process?.name}'? This will stop all scheduled executions. The process can be restored later.`"
          confirm-text="Archive"
          variant="warning"
          @confirm="archiveProcess"
          @cancel="showArchiveConfirm = false"
        />

        <!-- Execute Process Dialog -->
        <div v-if="showExecuteDialog" class="fixed inset-0 z-50 overflow-y-auto">
          <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
            <!-- Backdrop -->
            <div class="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity" @click="showExecuteDialog = false"></div>

            <!-- Dialog -->
            <div class="relative bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-lg sm:w-full">
              <div class="px-4 pt-5 pb-4 sm:p-6">
                <div class="flex items-center gap-3 mb-4">
                  <div class="flex-shrink-0 w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                    <PlayIcon class="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                      Execute Process
                    </h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400">
                      {{ process?.name }} v{{ process?.version }}
                    </p>
                  </div>
                </div>

                <!-- No inputs required -->
                <div v-if="detectedInputs.length === 0 && !showAdvancedInput" class="text-center py-6">
                  <CheckCircleIcon class="h-12 w-12 text-emerald-500 mx-auto mb-3" />
                  <p class="text-gray-600 dark:text-gray-300 font-medium">No inputs required</p>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">This process is ready to run</p>
                </div>

                <!-- Smart Input Form -->
                <div v-else-if="!showAdvancedInput" class="space-y-4">
                  <p class="text-sm text-gray-600 dark:text-gray-400">
                    This process expects the following inputs:
                  </p>
                  <div v-for="input in detectedInputs" :key="input.name" class="space-y-1">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {{ formatInputLabel(input.name) }}
                      <span v-if="input.required" class="text-red-500">*</span>
                    </label>
                    <input
                      v-if="input.type === 'text'"
                      v-model="executeInputValues[input.name]"
                      type="text"
                      :placeholder="input.placeholder"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                    <textarea
                      v-else
                      v-model="executeInputValues[input.name]"
                      :placeholder="input.placeholder"
                      rows="3"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                    <p v-if="input.usedIn" class="text-xs text-gray-400 dark:text-gray-500">
                      Used in: {{ input.usedIn }}
                    </p>
                  </div>
                </div>

                <!-- Advanced JSON Input -->
                <div v-else class="space-y-2">
                  <p class="text-sm text-gray-600 dark:text-gray-400">
                    Enter input data as JSON:
                  </p>
                  <textarea
                    v-model="executeInputJson"
                    rows="6"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    placeholder='{"field": "value"}'
                  ></textarea>
                </div>

                <!-- Toggle Advanced Mode -->
                <div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
                  <button
                    @click="showAdvancedInput = !showAdvancedInput"
                    class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
                  >
                    <CodeBracketIcon class="h-4 w-4" />
                    {{ showAdvancedInput ? 'Use form input' : 'Show as JSON (advanced)' }}
                  </button>
                </div>
              </div>

              <div class="px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse gap-3 bg-gray-50 dark:bg-gray-700/50">
                <button
                  @click="confirmExecute"
                  class="w-full sm:w-auto px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2"
                >
                  <PlayIcon class="h-4 w-4" />
                  Execute
                </button>
                <button
                  @click="showExecuteDialog = false"
                  class="mt-3 sm:mt-0 w-full sm:w-auto px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Save as Template Dialog -->
        <div v-if="showSaveTemplateDialog" class="fixed inset-0 z-50 overflow-y-auto">
          <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
            <!-- Backdrop -->
            <div class="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity" @click="showSaveTemplateDialog = false"></div>

            <!-- Dialog -->
            <div class="relative bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-lg sm:w-full">
              <div class="px-4 pt-5 pb-4 sm:p-6">
                <div class="flex items-center gap-3 mb-4">
                  <div class="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-900/30 flex items-center justify-center">
                    <DocumentDuplicateIcon class="h-6 w-6 text-teal-600 dark:text-teal-400" />
                  </div>
                  <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                    Save as Template
                  </h3>
                </div>

                <div class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Template Name <span class="text-red-500">*</span>
                    </label>
                    <input
                      v-model="templateForm.name"
                      type="text"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                      placeholder="my-workflow-template"
                    />
                    <p class="mt-1 text-xs text-gray-400">Lowercase, no spaces (used as ID)</p>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Display Name
                    </label>
                    <input
                      v-model="templateForm.displayName"
                      type="text"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                      placeholder="My Workflow Template"
                    />
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Description
                    </label>
                    <textarea
                      v-model="templateForm.description"
                      rows="2"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                      placeholder="Describe what this template does..."
                    ></textarea>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Category
                    </label>
                    <select
                      v-model="templateForm.category"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    >
                      <option value="general">General</option>
                      <option value="business">Business</option>
                      <option value="devops">DevOps</option>
                      <option value="analytics">Analytics</option>
                      <option value="support">Support</option>
                      <option value="content">Content</option>
                    </select>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Tags (comma-separated)
                    </label>
                    <input
                      v-model="templateForm.tags"
                      type="text"
                      class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                      placeholder="workflow, automation, example"
                    />
                  </div>
                </div>
              </div>
              <div class="px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse gap-3 bg-gray-50 dark:bg-gray-700/50">
                <button
                  @click="saveAsTemplate"
                  :disabled="!templateForm.name || savingTemplate"
                  class="w-full sm:w-auto px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  <svg v-if="savingTemplate" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  {{ savingTemplate ? 'Saving...' : 'Save Template' }}
                </button>
                <button
                  @click="showSaveTemplateDialog = false"
                  class="mt-3 sm:mt-0 w-full sm:w-auto px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, Teleport, Transition } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useProcessesStore } from '../stores/processes'
import NavBar from '../components/NavBar.vue'
import ProcessSubNav from '../components/ProcessSubNav.vue'
import YamlEditor from '../components/YamlEditor.vue'
import TemplateSelector from '../components/process/TemplateSelector.vue'
import RoleMatrix from '../components/process/RoleMatrix.vue'
import ProcessFlowPreview from '../components/ProcessFlowPreview.vue'
import EditorHelpPanel from '../components/EditorHelpPanel.vue'
import ProcessChatAssistant from '../components/ProcessChatAssistant.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  PlayIcon,
  DocumentDuplicateIcon,
  LinkIcon,
  ClipboardDocumentIcon,
  ClockIcon,
  QuestionMarkCircleIcon,
  CodeBracketIcon,
  ArchiveBoxIcon,
  SparklesIcon,
} from '@heroicons/vue/24/outline'
import api from '../api'
import jsyaml from 'js-yaml'
import { useOnboarding } from '../composables/useOnboarding'

const route = useRoute()
const router = useRouter()
const processesStore = useProcessesStore()
const { celebrateCompletion } = useOnboarding()

// State
const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const process = ref(null)
const yamlContent = ref(defaultYamlTemplate())
const validationErrors = ref([])
const notification = ref(null)
const hasUnsavedChanges = ref(false)
const editorSelectedText = ref('')
const showUnsavedWarning = ref(false)
const pendingNavigation = ref(null)
const showExecuteDialog = ref(false)
const executeInputJson = ref('{}')
const showAdvancedInput = ref(false)
const executeInputValues = ref({})
const detectedInputs = ref([])
const scheduleTriggerInfo = ref({})
const showSaveTemplateDialog = ref(false)
const savingTemplate = ref(false)
const showArchiveConfirm = ref(false)
const templateForm = ref({
  name: '',
  displayName: '',
  description: '',
  category: 'general',
  tags: '',
})
// Template selection for new processes
const showTemplateSelector = ref(true)
const selectedTemplateId = ref(null)
const loadingTemplate = ref(false)

// Editor tabs - default to 'chat' for new processes, 'editor' for existing
const activeTab = ref('chat')
const availableAgents = ref([])

// Help panel state
// On mobile (< xl breakpoint), default to hidden; on desktop, respect localStorage or show by default
const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 1280
const showHelpPanel = ref(isDesktop && localStorage.getItem('trinity_editor_help') !== 'hidden')
const editorHelpData = ref(null)
const currentHelpContent = ref(null)

// Computed
const isNew = computed(() => route.name === 'ProcessNew')

const hasErrors = computed(() =>
  validationErrors.value.some(e => e.level === 'error' || !e.level)
)

// Parse triggers from YAML content
const parsedTriggers = computed(() => {
  try {
    const parsed = jsyaml.load(yamlContent.value)
    return parsed?.triggers || []
  } catch {
    return []
  }
})

// Parse steps from YAML content for Role Matrix
const parsedSteps = computed(() => {
  try {
    const parsed = jsyaml.load(yamlContent.value)
    if (!parsed?.steps) return []

    return parsed.steps.map(step => ({
      id: step.id,
      name: step.name || step.id,
      type: step.type,
      agent: step.agent || null,  // Include agent for default executor
      roles: step.roles || null,
    }))
  } catch {
    return []
  }
})

// Check if we have webhook or schedule triggers
const hasWebhookTriggers = computed(() =>
  parsedTriggers.value.some(t => !t.type || t.type === 'webhook')
)

const hasScheduleTriggers = computed(() =>
  parsedTriggers.value.some(t => t.type === 'schedule')
)

// Cron preset labels
const cronPresetLabels = {
  'hourly': 'Every hour',
  'daily': 'Daily at 9 AM',
  'weekly': 'Weekly (Mondays at 9 AM)',
  'monthly': 'Monthly (1st at 9 AM)',
  'weekdays': 'Weekdays at 9 AM',
  '0 * * * *': 'Every hour',
  '0 9 * * *': 'Daily at 9 AM',
  '0 9 * * 1': 'Weekly (Mondays)',
  '0 9 1 * *': 'Monthly (1st)',
  '0 9 * * 1-5': 'Weekdays at 9 AM',
}

function getCronPresetLabel(cron) {
  return cronPresetLabels[cron] || null
}

function formatScheduleTime(isoString) {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    return date.toLocaleString()
  } catch {
    return isoString
  }
}

// Helper functions for triggers
function getWebhookUrl(triggerId) {
  const baseUrl = window.location.origin
  return `${baseUrl}/api/triggers/webhook/${triggerId}`
}

function copyWebhookUrl(triggerId) {
  const url = getWebhookUrl(triggerId)
  navigator.clipboard.writeText(url)
  showNotification('Webhook URL copied to clipboard', 'success')
}

// Default template for new processes
function defaultYamlTemplate() {
  return `# Process Definition
name: my-process
version: 1
description: Describe what this process does

steps:
  - id: step-1
    name: First Step
    type: agent_task
    agent: your-agent-name
    message: |
      Your message to the agent.
      Use {{input.variable}} to reference input data.
    timeout: 5m

# Define outputs to collect from steps
outputs:
  - name: result
    source: "{{steps.step-1.output}}"
`
}

// Quick start templates (matching ProcessList.vue)
const quickStartTemplates = {
  'content-pipeline': `name: content-pipeline
version: "1.0"
description: A content creation pipeline with research, writing, and review

triggers:
  - type: manual
    id: manual-start

steps:
  - id: research
    name: Research Topic
    type: agent_task
    agent: researcher
    message: |
      Research the following topic thoroughly:
      {{input.topic}}

      Provide key facts, statistics, and insights.
    timeout: 10m

  - id: write
    name: Write Content
    type: agent_task
    depends_on: [research]
    agent: writer
    message: |
      Write engaging content about {{input.topic}} using this research:

      {{steps.research.output}}
    timeout: 15m

  - id: review
    name: Review Content
    type: agent_task
    depends_on: [write]
    agent: editor
    message: |
      Review and improve this content:

      {{steps.write.output}}

      Check for clarity, accuracy, and engagement.
    timeout: 10m
`,
  'data-report': `name: data-report
version: "1.0"
description: Automated data analysis and reporting workflow

triggers:
  - type: manual
    id: manual-start

steps:
  - id: gather
    name: Gather Data
    type: agent_task
    agent: data-collector
    message: |
      Collect and prepare data for analysis.
      Data source: {{input.data_source}}
      Time range: {{input.time_range | default:"last 7 days"}}
    timeout: 10m

  - id: analyze
    name: Analyze Data
    type: agent_task
    depends_on: [gather]
    agent: analyst
    message: |
      Analyze the following data and identify:
      - Key trends and patterns
      - Anomalies or outliers
      - Actionable insights

      Data: {{steps.gather.output}}
    timeout: 15m

  - id: report
    name: Generate Report
    type: agent_task
    depends_on: [analyze]
    agent: writer
    message: |
      Create a professional report based on this analysis:

      {{steps.analyze.output}}

      Format: Executive summary with key findings.
    timeout: 10m
`,
  'support-escalation': `name: support-escalation
version: "1.0"
description: Customer support ticket handling with escalation and approval

triggers:
  - type: manual
    id: manual-start

steps:
  - id: triage
    name: Triage Ticket
    type: agent_task
    agent: support-ai
    message: |
      Analyze this support ticket and determine:
      - Severity (low/medium/high/critical)
      - Category
      - Suggested resolution approach

      Ticket: {{input.ticket}}
    timeout: 5m

  - id: route
    name: Route to Specialist
    type: human_approval
    depends_on: [triage]
    title: Review Triage Decision
    description: |
      Please review the AI triage decision and approve routing.

      Severity: {{steps.triage.output.severity}}
      Recommended action: {{steps.triage.output.recommendation}}
    timeout: 2h

  - id: resolve
    name: Generate Resolution
    type: agent_task
    depends_on: [route]
    agent: support-ai
    message: |
      Generate a resolution for this ticket based on the approved approach:

      Original ticket: {{input.ticket}}
      Triage: {{steps.triage.output}}

      Provide a helpful, professional response.
    timeout: 10m
`
}

// Lifecycle
onMounted(async () => {
  if (!isNew.value) {
    await loadProcess()
  } else {
    // Check for quick start template from query parameter
    const templateId = route.query.template
    if (templateId && quickStartTemplates[templateId]) {
      yamlContent.value = quickStartTemplates[templateId]
      showTemplateSelector.value = false
      showNotification(`Loaded template: ${templateId.replace('-', ' ')}`, 'success')
    }
  }
  // Fetch available agents for role matrix
  await loadAvailableAgents()

  // Load editor help data
  await loadEditorHelp()
})

// Watch for route changes (e.g., after creating a process or browser navigation)
watch(() => route.params.id, async (newId, oldId) => {
  if (newId && newId !== oldId && !process.value) {
    // Only reload if we don't already have the process data
    await loadProcess()
  }
})

async function loadAvailableAgents() {
  try {
    const response = await api.get('/api/agents')
    availableAgents.value = response.data.map(a => a.name)
  } catch (error) {
    console.warn('Failed to load agents:', error)
  }
}

// Load editor help data
async function loadEditorHelp() {
  try {
    const response = await fetch('/api/docs/content/editor-help.json')
    if (response.ok) {
      const data = await response.json()
      // JSON content is returned directly from the API
      editorHelpData.value = data
    }
  } catch (error) {
    console.warn('Failed to load editor help data:', error)
    // Fallback to default help
    editorHelpData.value = {
      default: {
        title: 'YAML Process Definition',
        description: 'Define automated workflows using YAML. Click on any field to see contextual help.',
        docs_link: '/processes/docs/getting-started/what-are-processes'
      }
    }
  }
}

// Handle cursor context changes from YamlEditor
function handleCursorContext(context) {
  if (!editorHelpData.value) return

  // Try to find help for the current path
  let helpKey = context.path
  let help = editorHelpData.value[helpKey]

  // If not found, try progressively shorter paths
  while (!help && helpKey.includes('.')) {
    helpKey = helpKey.split('.').slice(0, -1).join('.')
    help = editorHelpData.value[helpKey]
  }

  // Fall back to default
  currentHelpContent.value = help || editorHelpData.value.default || null
}

// Toggle help panel visibility
function toggleHelpPanel() {
  showHelpPanel.value = !showHelpPanel.value
  localStorage.setItem('trinity_editor_help', showHelpPanel.value ? 'visible' : 'hidden')
}

// Navigation guard for unsaved changes
onBeforeRouteLeave((to, from, next) => {
  if (hasUnsavedChanges.value) {
    pendingNavigation.value = to
    showUnsavedWarning.value = true
    next(false)
  } else {
    next()
  }
})

// Methods

// Template selection handlers
function handleTemplateSelect(templateId) {
  selectedTemplateId.value = templateId
}

async function proceedWithTemplate() {
  if (selectedTemplateId.value === null) {
    // Blank process - just hide selector
    showTemplateSelector.value = false
    return
  }

  // Load template content
  loadingTemplate.value = true
  try {
    const response = await api.get(`/api/process-templates/${selectedTemplateId.value}/preview`)
    let content = response.data.yaml_content || defaultYamlTemplate()

    // Replace template placeholders with sensible defaults
    // Generate a unique name from the template id
    const templateName = selectedTemplateId.value.split(':').pop() || 'my-process'
    const timestamp = Date.now().toString(36).slice(-4)
    const processName = `${templateName}-${timestamp}`

    // Replace {{name}} placeholder with generated name
    content = content.replace(/\{\{name\}\}/g, processName)

    yamlContent.value = content
    showTemplateSelector.value = false
    showNotification(`Loaded template: ${response.data.name}`, 'success')
  } catch (error) {
    console.error('Failed to load template:', error)
    showNotification('Failed to load template', 'error')
  } finally {
    loadingTemplate.value = false
  }
}

async function loadProcess() {
  loading.value = true
  try {
    const id = route.params.id
    const data = await processesStore.getProcess(id)
    process.value = data
    yamlContent.value = data.yaml_content || defaultYamlTemplate()
    hasUnsavedChanges.value = false

    // Switch to editor tab for existing processes
    activeTab.value = 'editor'

    // Load schedule trigger info for published processes
    if (data.status === 'published') {
      await loadScheduleTriggerInfo(id)
    }
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to load process', 'error')
    router.push('/processes')
  } finally {
    loading.value = false
  }
}

async function loadScheduleTriggerInfo(processId) {
  try {
    const response = await api.get(`/api/triggers/process/${processId}/schedules`)
    // Build a map by trigger_id for easy lookup
    const infoMap = {}
    for (const schedule of response.data) {
      infoMap[schedule.trigger_id] = schedule
    }
    scheduleTriggerInfo.value = infoMap
  } catch (error) {
    // Silently fail - schedule info is optional
    console.warn('Failed to load schedule trigger info:', error)
  }
}

function handleChange() {
  hasUnsavedChanges.value = true
  // Clear validation on edit
  validationErrors.value = []
}

// Handle YAML from chat assistant
// Handle live YAML updates from chat (auto-sync as typing)
function handleYamlUpdate(yaml) {
  yamlContent.value = yaml
  hasUnsavedChanges.value = true
}

// Handle selection changes from YAML editor
function handleEditorSelection(selection) {
  editorSelectedText.value = selection
}

async function validateProcess() {
  validating.value = true
  try {
    const result = await processesStore.validateYaml(yamlContent.value)
    validationErrors.value = result.errors || []

    if (result.is_valid) {
      showNotification('Validation passed!', 'success')
    } else {
      showNotification(`Found ${validationErrors.value.length} issue(s)`, 'error')
    }
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Validation failed', 'error')
  } finally {
    validating.value = false
  }
}

async function saveProcess() {
  // Validate first
  validating.value = true
  try {
    const result = await processesStore.validateYaml(yamlContent.value)
    validationErrors.value = result.errors || []

    if (!result.is_valid && validationErrors.value.some(e => e.level === 'error' || !e.level)) {
      showNotification('Please fix validation errors before saving', 'error')
      validating.value = false
      return
    }
  } catch (error) {
    showNotification('Validation failed', 'error')
    validating.value = false
    return
  }
  validating.value = false

  saving.value = true
  try {
    if (isNew.value) {
      const created = await processesStore.createProcess(yamlContent.value)
      showNotification('Process created successfully!', 'success')
      hasUnsavedChanges.value = false
      // Celebrate completing the "create process" onboarding step
      celebrateCompletion('createProcess')
      // Set process data before redirect so UI updates correctly
      process.value = created
      router.push(`/processes/${created.id}`)
    } else {
      await processesStore.updateProcess(route.params.id, yamlContent.value)
      showNotification('Process saved successfully!', 'success')
      hasUnsavedChanges.value = false
      await loadProcess()
    }
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to save process', 'error')
  } finally {
    saving.value = false
  }
}

async function publishProcess() {
  saving.value = true
  try {
    await processesStore.publishProcess(route.params.id)
    showNotification('Process published!', 'success')
    await loadProcess()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to publish', 'error')
  } finally {
    saving.value = false
  }
}

async function archiveProcess() {
  showArchiveConfirm.value = false
  saving.value = true
  try {
    await api.post(`/api/processes/${route.params.id}/archive`)
    showNotification('Process archived!', 'success')
    await loadProcess()
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to archive', 'error')
  } finally {
    saving.value = false
  }
}

function executeProcess() {
  // Detect input variables from YAML
  detectedInputs.value = detectInputVariables(yamlContent.value)

  // Initialize form values
  executeInputValues.value = {}
  detectedInputs.value.forEach(input => {
    executeInputValues.value[input.name] = ''
  })

  // Reset state
  executeInputJson.value = '{}'
  showAdvancedInput.value = false
  showExecuteDialog.value = true
}

// Detect {{input.xxx}} patterns in YAML
function detectInputVariables(yaml) {
  const inputs = []
  const seen = new Set()

  // Match {{input.xxx}} patterns
  const regex = /\{\{\s*input\.(\w+)\s*\}\}/g
  let match

  // Parse YAML to get step context
  let parsed = null
  try {
    parsed = jsyaml.load(yaml)
  } catch {
    // Ignore parse errors
  }

  while ((match = regex.exec(yaml)) !== null) {
    const name = match[1]
    if (!seen.has(name)) {
      seen.add(name)

      // Find which step uses this input
      let usedIn = null
      if (parsed?.steps) {
        for (const step of parsed.steps) {
          const stepStr = JSON.stringify(step)
          if (stepStr.includes(`input.${name}`)) {
            usedIn = step.name || step.id
            break
          }
        }
      }

      // Determine input type - use textarea for longer content hints
      const isLongContent = ['content', 'message', 'text', 'description', 'body', 'ticket', 'query'].some(
        hint => name.toLowerCase().includes(hint)
      )

      inputs.push({
        name,
        type: isLongContent ? 'textarea' : 'text',
        placeholder: `Enter ${formatInputLabel(name).toLowerCase()}...`,
        usedIn,
        required: true // All detected inputs are considered required
      })
    }
  }

  return inputs
}

// Format input name to human-readable label
function formatInputLabel(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, l => l.toUpperCase())
}

async function confirmExecute() {
  try {
    // Build input data
    let inputData = {}

    if (showAdvancedInput.value) {
      // Parse JSON from textarea
      try {
        inputData = JSON.parse(executeInputJson.value || '{}')
      } catch (e) {
        showNotification('Invalid JSON input', 'error')
        return
      }
    } else {
      // Build from form values
      for (const [key, value] of Object.entries(executeInputValues.value)) {
        if (value !== undefined && value !== '') {
          inputData[key] = value
        }
      }
    }

    showExecuteDialog.value = false
    const execution = await processesStore.executeProcess(route.params.id, inputData)
    showNotification('Execution started!', 'success')
    // Celebrate completing the "run execution" onboarding step
    celebrateCompletion('runExecution')
    // Navigate to execution detail
    router.push(`/executions/${execution.id}`)
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to execute', 'error')
  }
}

async function createNewVersion() {
  saving.value = true
  try {
    const newProcess = await processesStore.createNewVersion(route.params.id)
    showNotification(`New version v${newProcess.version} created as draft`, 'success')
    hasUnsavedChanges.value = false
    // Navigate to the new draft version
    router.push(`/processes/${newProcess.id}`)
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Failed to create new version', 'error')
  } finally {
    saving.value = false
  }
}

function confirmLeave() {
  hasUnsavedChanges.value = false
  showUnsavedWarning.value = false
  if (pendingNavigation.value) {
    router.push(pendingNavigation.value)
  }
}

function showNotification(message, type = 'success') {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

async function saveAsTemplate() {
  if (!templateForm.value.name) return

  savingTemplate.value = true
  try {
    // Parse tags
    const tags = templateForm.value.tags
      .split(',')
      .map(t => t.trim())
      .filter(t => t.length > 0)

    const response = await api.post('/api/process-templates', {
      name: templateForm.value.name,
      display_name: templateForm.value.displayName || templateForm.value.name,
      description: templateForm.value.description,
      category: templateForm.value.category,
      tags: tags,
      definition_yaml: yamlContent.value,
    })

    showNotification('Template saved successfully!', 'success')
    showSaveTemplateDialog.value = false

    // Reset form
    templateForm.value = {
      name: '',
      displayName: '',
      description: '',
      category: 'general',
      tags: '',
    }
  } catch (error) {
    const errorMsg = error.response?.data?.detail || 'Failed to save template'
    showNotification(errorMsg, 'error')
  } finally {
    savingTemplate.value = false
  }
}

// Handle role updates from RoleMatrix component
function handleRolesUpdate(rolesMap) {
  try {
    const parsed = jsyaml.load(yamlContent.value)
    if (!parsed?.steps) return

    // Update each step's roles
    let modified = false
    for (const step of parsed.steps) {
      const newRoles = rolesMap[step.id]
      if (newRoles) {
        // Only add roles object if there's an executor
        if (newRoles.executor) {
          step.roles = {
            executor: newRoles.executor,
          }
          if (newRoles.monitors && newRoles.monitors.length > 0) {
            step.roles.monitors = newRoles.monitors
          }
          if (newRoles.informed && newRoles.informed.length > 0) {
            step.roles.informed = newRoles.informed
          }
          modified = true
        } else if (step.roles) {
          // Remove roles if executor was cleared
          delete step.roles
          modified = true
        }
      }
    }

    if (modified) {
      // Convert back to YAML
      yamlContent.value = jsyaml.dump(parsed, {
        indent: 2,
        lineWidth: -1,
        noRefs: true,
        sortKeys: false,
      })
      hasUnsavedChanges.value = true
    }
  } catch (error) {
    console.error('Failed to update roles in YAML:', error)
    showNotification('Failed to update roles', 'error')
  }
}
</script>

<style scoped>
/* Slide-over transition for mobile help panel */
.slide-over-enter-active,
.slide-over-leave-active {
  transition: opacity 0.2s ease;
}
.slide-over-enter-active > div:last-child,
.slide-over-leave-active > div:last-child {
  transition: transform 0.3s ease;
}
.slide-over-enter-from,
.slide-over-leave-to {
  opacity: 0;
}
.slide-over-enter-from > div:last-child,
.slide-over-leave-to > div:last-child {
  transform: translateX(100%);
}
</style>

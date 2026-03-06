# Feature: Onboarding and Documentation

## Overview
Comprehensive onboarding experience for the Process Engine including a guided creation wizard, in-app documentation viewer, contextual help panel, AI chat assistant, and interactive progress checklist.

## User Story
As a new Trinity user, I want guided onboarding and in-app documentation so that I can quickly understand and start using process automation without external help.

## Entry Points
- **UI (Wizard)**: `src/frontend/src/views/ProcessWizard.vue` - Process creation wizard
- **UI (Docs)**: `src/frontend/src/views/ProcessDocs.vue` - Documentation viewer
- **UI (Checklist)**: `src/frontend/src/components/OnboardingChecklist.vue` - Progress widget
- **UI (Help Panel)**: `src/frontend/src/components/EditorHelpPanel.vue` - Contextual help
- **UI (Chat)**: `src/frontend/src/components/ProcessChatAssistant.vue` - AI assistant
- **Route (Wizard)**: `GET /processes/wizard`
- **Route (Docs)**: `GET /processes/docs` and `GET /processes/docs/:slug+`
- **API (Docs)**: `GET /api/docs/index`, `GET /api/docs/content/{slug}`

---

## Component 1: Process Creation Wizard

### Frontend Layer

#### ProcessWizard.vue
**File**: `src/frontend/src/views/ProcessWizard.vue`

The wizard provides a 4-step guided flow for creating processes:

**Step Indicator** (lines 24-54):
```vue
<div class="flex items-center gap-2">
  <template v-for="(stepInfo, index) in steps" :key="index">
    <div
      class="w-8 h-8 rounded-full flex items-center justify-center"
      :class="index < currentStep ? 'bg-indigo-600 text-white' : ..."
    >
      <CheckIcon v-if="index < currentStep" class="h-4 w-4" />
      <span v-else>{{ index + 1 }}</span>
    </div>
  </template>
</div>
```

**Steps Definition** (lines 377-384):
```javascript
const steps = [
  { title: 'Goal' },      // Select workflow type
  { title: 'Agents' },    // Assign agents to steps
  { title: 'Customize' }, // Edit step details
  { title: 'Review' },    // Preview and create
]
```

**Goal Options** (lines 386-441):
| Goal ID | Title | Description | Steps |
|---------|-------|-------------|-------|
| `content` | Content Creation | Research, write, review | 3 steps |
| `data` | Data Processing | Collect, analyze, report | 3 steps |
| `approval` | Approval Workflow | Prepare, review, notify | 3 steps + human_approval |
| `custom` | Custom Workflow | Blank template | 1 step |

**YAML Generation** (lines 530-584):
```javascript
function generateYamlFromWizard(state) {
  const lines = []
  lines.push(`name: ${state.processName || 'my-workflow'}`)
  lines.push('version: "1.0"')
  // ... generates complete process YAML
}
```

**Process Creation** (lines 586-614):
```javascript
async function createProcess() {
  const yaml = generatedYaml.value
  const created = await processesStore.createProcess(yaml)

  // Celebrate onboarding completion
  celebrateCompletion('createProcess')

  // Execute immediately if requested
  if (wizardState.runImmediately) {
    await api.post(`/api/processes/${created.id}/execute`, { input_data: {} })
  }

  router.push(`/processes/${created.id}`)
}
```

### State Management

**Wizard State** (lines 450-455):
```javascript
const wizardState = reactive({
  selectedGoal: null,
  steps: [],
  processName: '',
  runImmediately: false,
})
```

---

## Component 2: Documentation Viewer

### Frontend Layer

#### ProcessDocs.vue
**File**: `src/frontend/src/views/ProcessDocs.vue`

**Route Configuration** (`src/frontend/src/router/index.js:78-88`):
```javascript
{
  path: '/processes/docs',
  name: 'ProcessDocs',
  component: () => import('../views/ProcessDocs.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/processes/docs/:slug+',
  name: 'ProcessDocsPage',
  component: () => import('../views/ProcessDocs.vue'),
  meta: { requiresAuth: true }
}
```

**Sidebar Navigation** (lines 38-67):
```vue
<nav class="space-y-1">
  <div v-for="section in docsIndex?.sections" :key="section.id" class="mb-4">
    <button @click="toggleSection(section.id)">
      {{ section.title }}
    </button>
    <div v-if="expandedSections.includes(section.id)" class="ml-2 mt-1">
      <router-link
        v-for="doc in section.docs"
        :to="`/processes/docs/${doc.slug}`"
      >
        {{ doc.title }}
      </router-link>
    </div>
  </div>
</nav>
```

**Markdown Rendering** (lines 200-218):
```vue
<div
  class="prose prose-indigo dark:prose-invert max-w-none"
  v-html="renderedContent"
/>
```

**Content Loading** (lines 404-434):
```javascript
const loadContent = async () => {
  const response = await fetch(`/api/docs/content/${currentSlug.value}`)
  const data = await response.json()
  markdownContent.value = data.content
}
```

**Restart Onboarding** (lines 69-98):
```vue
<button @click="showRestartConfirm = true">
  <ArrowPathIcon class="h-4 w-4" />
  Restart Getting Started
</button>
```

### Backend Layer

#### docs.py Router
**File**: `src/backend/routers/docs.py`

**Documentation Index** (lines 33-48):
```python
@router.get("/index")
async def get_docs_index():
    """Get documentation index/navigation structure."""
    docs_dir = get_docs_dir()
    index_path = docs_dir / "index.json"
    with open(index_path, "r") as f:
        return json.load(f)
```

**Content Retrieval** (lines 51-99):
```python
@router.get("/content/{slug:path}")
async def get_doc_content(slug: str):
    """Get documentation content by slug."""
    # Security: Prevent path traversal
    if ".." in slug or slug.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid document path")

    doc_path = docs_dir / f"{slug}.md"
    content = doc_path.read_text(encoding="utf-8")
    return JSONResponse(content={"content": content, "slug": slug})
```

### Content Storage

**Documentation Directory**: `config/process-docs/`

```
config/process-docs/
  index.json                          # Navigation structure
  editor-help.json                    # Contextual help definitions
  getting-started/
    what-are-processes.md
    first-process.md
    step-types.md
  tutorials/
    second-process.md
    human-checkpoints.md
    complex-workflows.md
  reference/
    yaml-schema.md
    variables.md
    triggers.md
    error-handling.md
  patterns/
    sequential.md
    parallel.md
    approvals.md
  troubleshooting/
    common-errors.md
```

**Index Structure** (`config/process-docs/index.json`):
```json
{
  "sections": [
    {
      "id": "getting-started",
      "title": "Getting Started",
      "docs": [
        { "slug": "getting-started/what-are-processes", "title": "What are Processes?" },
        { "slug": "getting-started/first-process", "title": "Your First Process" }
      ]
    }
  ]
}
```

---

## Component 3: Onboarding Checklist

### Frontend Layer

#### OnboardingChecklist.vue
**File**: `src/frontend/src/components/OnboardingChecklist.vue`

**Floating Widget** (lines 26-32):
```vue
<div
  class="fixed bottom-4 right-4 z-[9999] w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl"
  :class="{ 'h-auto': !isMinimized, 'h-14': isMinimized }"
>
```

**Required Checklist Items** (lines 271-296):
```javascript
const requiredItems = computed(() => [
  {
    id: 'createProcess',
    label: 'Create your first process',
    description: 'Use the wizard to define your workflow',
    link: '/processes/wizard',
  },
  {
    id: 'runExecution',
    label: 'Run a process execution',
    description: 'Execute your process and see it in action',
    link: '/processes',
  },
  {
    id: 'monitorExecution',
    label: 'Monitor an execution',
    description: 'View progress and step outputs',
    link: '/executions',
  }
])
```

**Optional Items** (lines 298-311):
```javascript
const optionalItems = computed(() => [
  {
    id: 'setupSchedule',
    label: 'Set up a schedule',
    description: 'Automate recurring process runs',
  },
  {
    id: 'configureApproval',
    label: 'Configure human approval',
    description: 'Add approval gates to your workflow',
  }
])
```

**Celebration Animation** (lines 418-432):
```css
@keyframes celebrate {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); box-shadow: 0 25px 50px -12px rgba(74, 222, 128, 0.4); }
}
.animate-celebrate {
  animation: celebrate 0.6s ease-in-out 2;
}
```

### State Management

#### useOnboarding.js Composable
**File**: `src/frontend/src/composables/useOnboarding.js`

**State Structure** (lines 44-56):
```javascript
const getDefaultState = () => ({
  dismissed: false,
  tourCompleted: false,
  checklistMinimized: false,
  onboardingCompletedAt: null,
  checklist: {
    createProcess: false,
    runExecution: false,
    monitorExecution: false,
    setupSchedule: false,
    configureApproval: false
  }
})
```

**Progress Calculation** (lines 94-109):
```javascript
const checklistProgress = computed(() => {
  const requiredItems = ['createProcess', 'runExecution', 'monitorExecution']
  const optionalItems = ['setupSchedule', 'configureApproval']

  const requiredCompleted = requiredItems.filter(item => state.value.checklist[item]).length
  const optionalCompleted = optionalItems.filter(item => state.value.checklist[item]).length

  return {
    completed: requiredCompleted + optionalCompleted,
    total: 5,
    required: 3,
    requiredCompleted
  }
})
```

**Celebration Handler** (lines 139-159):
```javascript
const celebrateCompletion = (item) => {
  if (item in state.value.checklist && !state.value.checklist[item]) {
    state.value.checklist[item] = true
    state.value.checklistMinimized = false  // Expand checklist
    celebrateStep.value = item              // Trigger animation

    setTimeout(() => {
      celebrateStep.value = null
    }, 3000)
  }
}
```

**Data Sync** (lines 200-233):
```javascript
const syncWithData = ({ processCount, executionCount, hasSchedule, hasApproval }) => {
  // Auto-detect completion based on API data
  if (processCount > 0 && !state.value.checklist.createProcess) {
    state.value.checklist.createProcess = true
  }
  if (executionCount > 0 && state.value.checklist.createProcess) {
    state.value.checklist.runExecution = true
  }
  // ...
}
```

**Integration Points**:
- `ProcessList.vue:368` - `syncWithData()` on mount
- `ProcessWizard.vue:595` - `celebrateCompletion('createProcess')`
- `ProcessExecutionDetail.vue:389` - `markChecklistItem('monitorExecution')`
- `ProcessDocs.vue:268` - `resetOnboarding()`

---

## Component 4: Editor Help Panel

### Frontend Layer

#### EditorHelpPanel.vue
**File**: `src/frontend/src/components/EditorHelpPanel.vue`

**Contextual Help Display** (lines 23-96):
```vue
<div v-if="helpContent">
  <h4 class="text-lg font-semibold">{{ helpContent.title }}</h4>
  <p class="text-sm text-gray-600">{{ helpContent.description }}</p>

  <!-- Type, Required, Default, Options -->
  <div v-if="helpContent.type">Type: {{ helpContent.type }}</div>
  <div v-if="helpContent.options">
    <code v-for="opt in helpContent.options">{{ opt }}</code>
  </div>

  <!-- Example -->
  <div v-if="helpContent.example">
    <pre><code>{{ helpContent.example }}</code></pre>
  </div>

  <!-- Docs link -->
  <router-link v-if="helpContent.docs_link" :to="helpContent.docs_link">
    Learn more in documentation
  </router-link>
</div>
```

#### ProcessEditor.vue Integration
**File**: `src/frontend/src/views/ProcessEditor.vue`

**Help Panel Toggle** (lines 816, 1148-1150):
```javascript
const showHelpPanel = ref(isDesktop && localStorage.getItem('trinity_editor_help') !== 'hidden')

function toggleHelpPanel() {
  showHelpPanel.value = !showHelpPanel.value
  localStorage.setItem('trinity_editor_help', showHelpPanel.value ? 'visible' : 'hidden')
}
```

**Cursor-Based Help** (lines 1131-1144):
```javascript
function updateContextualHelp(cursorInfo) {
  if (!editorHelpData.value) return

  // Get help key from YAML path (e.g., "steps.0.type" -> "steps.type")
  let helpKey = cursorInfo.path
  let help = editorHelpData.value[helpKey]

  // Fallback to parent path
  if (!help && helpKey.includes('.')) {
    helpKey = helpKey.replace(/\.\d+/g, '')
    help = editorHelpData.value[helpKey]
  }

  currentHelpContent.value = help || editorHelpData.value.default || null
}
```

### Content Storage

**Editor Help Definitions** (`config/process-docs/editor-help.json`):
```json
{
  "steps.type": {
    "title": "Step Type",
    "description": "The type of step determines what action is performed.",
    "type": "string",
    "required": true,
    "options": ["agent_task", "human_approval", "gateway", "timer", "notification", "sub_process"],
    "docs_link": "/processes/docs/getting-started/step-types"
  },
  "steps.agent": {
    "title": "Agent",
    "description": "The agent (by name or ID) that will execute this task.",
    "type": "string",
    "required": true,
    "example": "content-reviewer"
  }
}
```

---

## Component 5: Process Chat Assistant

### Frontend Layer

#### ProcessChatAssistant.vue
**File**: `src/frontend/src/components/ProcessChatAssistant.vue`

**System Agent Chat** (lines 406-465):
```javascript
async function sendMessage() {
  const userMessage = inputMessage.value.trim()
  messages.value.push({ role: 'user', content: userMessage })

  // Build context for first message
  let messageToSend = userMessage
  if (messages.value.length === 1) {
    messageToSend = PROCESS_ASSISTANT_CONTEXT + userMessage
  }

  // Add process status context
  if (props.processStatus === 'published') {
    messageToSend = `[CONTEXT: PUBLISHED process - read-only]\n\n` + messageToSend
  }

  const response = await api.post('/api/agents/trinity-system/chat', {
    message: messageToSend
  })

  await typeMessage(response.data.response)
}
```

**YAML Auto-Sync** (lines 252-292):
```javascript
function extractYaml(content) {
  const match = content.match(/```ya?ml\n?([\s\S]*?)```/i)
  return match ? match[1].trim() : null
}

async function typeMessage(fullContent) {
  // Word-by-word typing animation
  for (let i = 0; i < words.length; i++) {
    typingMessage.value += words[i]

    // Live YAML updates to editor
    const yaml = extractYaml(typingMessage.value)
    if (yaml) {
      emit('yaml-update', yaml)
    }

    await new Promise(resolve => setTimeout(resolve, 30))
  }
}
```

**Validation Error Help** (lines 474-485):
```javascript
function askForHelp() {
  const errorList = props.validationErrors.join('\n- ')
  inputMessage.value = `I have validation errors. Can you help me fix them?

Errors:
- ${errorList}

Current YAML:
\`\`\`yaml
${props.currentYaml.slice(0, 500)}
\`\`\``
  sendMessage()
}
```

**Suggested Prompts** (lines 328-333):
```javascript
const suggestedPrompts = [
  "Review content before publishing",
  "Analyze data and generate reports",
  "Route support tickets to agents",
  "Automate approval workflows"
]
```

---

## Data Flow

### Wizard Flow
```
User selects goal (ProcessWizard.vue:478)
  -> Clone template steps with agent assignment
  -> generateYamlFromWizard() creates YAML (line 530)
  -> processesStore.createProcess(yaml) (line 592)
  -> POST /api/processes with yaml_content
  -> celebrateCompletion('createProcess') (line 595)
  -> OnboardingChecklist animation triggers
```

### Documentation Flow
```
User navigates to /processes/docs/:slug
  -> ProcessDocs.vue mounted
  -> loadIndex() fetches /api/docs/index (line 352)
  -> loadContent() fetches /api/docs/content/{slug} (line 404)
  -> marked() renders markdown to HTML (line 304-307)
```

### Onboarding State Flow
```
useOnboarding() composable initialized
  -> Load from localStorage: trinity_onboarding_{userId}
  -> ProcessList.vue calls syncWithData() on mount (line 396)
  -> Checks processCount, executionCount, hasSchedule
  -> Auto-marks completed checklist items
  -> State changes persist to localStorage
```

---

## Error Handling

| Error Case | Location | Handling |
|------------|----------|----------|
| No agents available | `ProcessWizard.vue:111-121` | Shows warning with link to create agent |
| Agent not running | `ProcessWizard.vue:154-157` | Shows amber warning badge |
| Docs not found | `ProcessDocs.vue:423-429` | Shows placeholder content |
| System agent offline | `ProcessChatAssistant.vue:453-459` | Shows 503 error with Settings link |
| Chat rate limited | `ProcessChatAssistant.vue:455-456` | Shows 429 "busy" message |

---

## Security Considerations

1. **Path Traversal Prevention**: Backend `docs.py:59-60` blocks `..` and absolute paths
2. **Path Validation**: `docs.py:87-90` ensures resolved path stays within docs_dir
3. **Auth Required**: All routes require authentication (`meta: { requiresAuth: true }`)
4. **Per-User State**: Onboarding state scoped by user ID in localStorage key

---

## Related Files

| File | Purpose |
|------|---------|
| `src/frontend/src/views/ProcessWizard.vue` | 4-step wizard for creating processes |
| `src/frontend/src/views/ProcessDocs.vue` | Documentation viewer with navigation |
| `src/frontend/src/components/OnboardingChecklist.vue` | Floating progress checklist |
| `src/frontend/src/components/EditorHelpPanel.vue` | Contextual YAML help |
| `src/frontend/src/components/ProcessChatAssistant.vue` | AI-powered process assistant |
| `src/frontend/src/composables/useOnboarding.js` | Onboarding state management |
| `src/backend/routers/docs.py` | Documentation API endpoints |
| `config/process-docs/` | Markdown documentation content |
| `config/process-docs/editor-help.json` | Contextual help definitions |
| `config/process-docs/index.json` | Documentation navigation structure |

---

## Dependencies

### NPM Packages
- `marked` - Markdown parsing (ProcessDocs.vue, ProcessChatAssistant.vue)
- `@heroicons/vue` - Icons throughout UI

### Trinity Dependencies
- System Agent (`trinity-system`) - Powers ProcessChatAssistant
- Processes Store - Process creation from wizard
- Auth Store - User ID for onboarding state

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-18 | Initial feature flow documentation |
| 2026-01-23 | Rebuilt with accurate line numbers and implementation details |

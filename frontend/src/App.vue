<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :projects="projects"
      :current-id="currentConvId"
      :loading="loadingConvs"
      :has-more="hasMoreConvs"
      @select="selectConversation"
      @delete="deleteConversation"
      @load-more="loadMoreConversations"
      @create-project="showCreateModal = true"
      @browse-project="browseProject"
      @create-in-project="createConversationInProject"
      @delete-project="deleteProject"
      @toggle-settings="togglePanel('settings')"
      @toggle-stats="togglePanel('stats')"
    />

    <!-- File Explorer (replaces ChatView when active) -->
    <div v-if="showFileExplorer" class="file-explorer-wrap main-panel">
      <div class="explorer-topbar">
        <div class="topbar-label">浏览文件</div>
        <div v-if="currentProject" class="topbar-project-name">{{ currentProject.name }}</div>
      </div>

      <div v-if="currentProject" class="explorer-body">
        <FileExplorer
          :project-id="currentProject.id"
          :project-name="currentProject.name"
        />
      </div>
      <div v-else class="explorer-body empty-state">
        <span v-html="icons.folderLg" style="color: var(--text-tertiary); opacity: 0.5;" />
        <p>当前对话未关联项目</p>
      </div>
    </div>

    <ChatView
      v-else
      :conversation="currentConv"
      :messages="messages"
      :streaming="streaming"
      :streaming-process-steps="streamProcessSteps"
      :model-name-map="modelNameMap"
      :has-more-messages="hasMoreMessages"
      :loading-more="loadingMessages"
      :tools-enabled="toolsEnabled"
      @send-message="sendMessage"
      @stop-streaming="stopStreaming"
      @delete-message="deleteMessage"
      @regenerate-message="regenerateMessage"
      @toggle-settings="togglePanel('settings')"
      @toggle-stats="togglePanel('stats')"
      @load-more-messages="loadMoreMessages"
      @toggle-tools="updateToolsEnabled"
    />

    <Transition name="fade">
      <div v-if="showSettings" class="modal-overlay" @click.self="showSettings = false">
        <div class="modal-content">
          <SettingsPanel
            :key="currentConvId || '__none__'"
            :visible="showSettings"
            :conversation="currentConv"
            :models="models"
            :default-model="defaultModel"
            @close="showSettings = false"
            @save="saveSettings"
          />
        </div>
      </div>
    </Transition>

    <Transition name="fade">
      <div v-if="showStats" class="modal-overlay" @click.self="showStats = false">
        <div class="modal-content">
          <StatsPanel @close="showStats = false" />
        </div>
      </div>
    </Transition>

    <!-- Create project modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="create-modal">
        <div class="modal-header">
          <h3>创建项目</h3>
          <button class="btn-close" @click="showCreateModal = false">
            <span v-html="icons.closeMd" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>项目名称</label>
            <input v-model="newProjectName" type="text" placeholder="输入项目名称" />
          </div>
          <div class="form-group">
            <label>描述（可选）</label>
            <textarea v-model="newProjectDesc" placeholder="输入项目描述" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateModal = false">取消</button>
          <button class="btn-primary" @click="createProject" :disabled="!newProjectName.trim() || creatingProject">
            {{ creatingProject ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
  <ModalDialog />
  <ToastContainer />
</template>

<script setup>
import { ref, shallowRef, computed, onMounted, defineAsyncComponent } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatView from './components/ChatView.vue'
import FileExplorer from './components/FileExplorer.vue'
import ModalDialog from './components/ModalDialog.vue'
import ToastContainer from './components/ToastContainer.vue'
import { icons } from './utils/icons'
import { useModal } from './composables/useModal'

const SettingsPanel = defineAsyncComponent(() => import('./components/SettingsPanel.vue'))
const StatsPanel = defineAsyncComponent(() => import('./components/StatsPanel.vue'))
import { conversationApi, messageApi, projectApi, modelApi } from './api'

const modal = useModal()

// -- Models state (preloaded) --
const models = ref([])
const modelNameMap = ref({})
const defaultModel = computed(() => models.value.length > 0 ? models.value[0].id : '')

async function loadModels() {
  try {
    const res = await modelApi.getCached()
    models.value = res.data || []
    const map = {}
    for (const m of models.value) {
      if (m.id && m.name) map[m.id] = m.name
    }
    modelNameMap.value = map
  } catch (e) {
    console.error('Failed to load models:', e)
  }
}

// -- Conversations state --
const conversations = shallowRef([])
const currentConvId = ref(null)
const loadingConvs = ref(false)
const hasMoreConvs = ref(false)
const nextConvCursor = ref(null)

// -- Projects state --
const projects = ref([])

// -- Messages state --
const messages = shallowRef([])
const hasMoreMessages = ref(false)
const loadingMessages = ref(false)
const nextMsgCursor = ref(null)

// -- Streaming state (per-conversation) --
// processSteps is the single source of truth for all streaming content.
// thinking/text steps are sent incrementally via process_step events and
// updated in-place by id. tool_call/tool_result steps are appended on arrival.
// On stream completion (onDone), the finalized steps are stored in the message object.
const streaming = ref(false)          // true when current conversation is actively streaming
const streamProcessSteps = shallowRef([]) // Ordered steps: thinking/text/tool_call/tool_result

// Track which conversations are currently streaming (supports multi-concurrent streams)
const streamingConvs = new Set()

// Per-conversation abort controllers (for stopping active streams)
const streamAborters = new Map()

// 保存每个对话的流式状态（切换对话时暂存）
const streamStates = new Map()

// Stop the active stream for a conversation
function stopStreaming(convId) {
  const conv = convId || currentConvId.value
  if (!conv) return
  const abort = streamAborters.get(conv)
  if (abort) {
    abort()
    streamAborters.delete(conv)
  }
  // AbortError is silently caught in createSSEStream, so clean up state here
  streamStates.delete(conv)
  streamingConvs.delete(conv)
  if (currentConvId.value === conv) {
    setStreamState(false, conv)
  }
}

function setStreamState(isActive, convId) {
  streaming.value = isActive
  if (!isActive) {
    streamProcessSteps.value = []
  }
  if (convId) {
    if (isActive) {
      streamingConvs.add(convId)
    } else {
      streamingConvs.delete(convId)
    }
  }
}

function updateStreamField(convId, field, ref, valueOrUpdater) {
  const isCurrent = currentConvId.value === convId
  const current = isCurrent ? ref.value : (streamStates.get(convId) || {})[field]
  const newVal = typeof valueOrUpdater === 'function' ? valueOrUpdater(current) : valueOrUpdater
  if (isCurrent) {
    ref.value = newVal
  } else {
    const saved = streamStates.get(convId) || {}
    streamStates.set(convId, { ...saved, [field]: newVal })
  }
}

// -- UI state --
const showSettings = ref(false)
const showStats = ref(false)
const toolsEnabled = ref(localStorage.getItem('tools_enabled') !== 'false')
const currentProject = ref(null)
const showFileExplorer = ref(false)
const showCreateModal = ref(false)
const newProjectName = ref('')
const newProjectDesc = ref('')
const creatingProject = ref(false)

function togglePanel(panel) {
  const ref = panel === 'settings' ? showSettings : showStats
  const other = panel === 'settings' ? showStats : showSettings
  ref.value = !ref.value
  if (ref.value) other.value = false
}

const currentConv = computed(() =>
  conversations.value.find(c => c.id === currentConvId.value) || null
)

// -- Load conversations (all, no project filter) --
async function loadConversations(reset = true) {
  if (loadingConvs.value) return
  loadingConvs.value = true
  try {
    const res = await conversationApi.list(reset ? null : nextConvCursor.value, 20)
    if (reset) {
      conversations.value = res.data.items
    } else {
      conversations.value = [...conversations.value, ...res.data.items]
    }
    nextConvCursor.value = res.data.next_cursor
    hasMoreConvs.value = res.data.has_more
  } catch (e) {
    console.error('Failed to load conversations:', e)
  } finally {
    loadingConvs.value = false
  }
}

function loadMoreConversations() {
  if (hasMoreConvs.value) loadConversations(false)
}

// -- Create conversation in specific project --
async function createConversationInProject(project) {
  showFileExplorer.value = false
  if (project.id) {
    currentProject.value = { id: project.id, name: project.name }
  } else {
    currentProject.value = null
  }
  try {
    const res = await conversationApi.create({
      title: '新对话',
      project_id: project.id || null,
      model: defaultModel.value || undefined,
    })
    conversations.value = [res.data, ...conversations.value]
    await selectConversation(res.data.id)
  } catch (e) {
    console.error('Failed to create conversation:', e)
  }
}


// -- Select conversation (auto-set project context) --
async function selectConversation(id) {
  showFileExplorer.value = false

  // Auto-set project context based on conversation
  const conv = conversations.value.find(c => c.id === id)
  if (conv?.project_id) {
    if (!currentProject.value || currentProject.value.id !== conv.project_id) {
      currentProject.value = { id: conv.project_id, name: conv.project_name || '' }
    }
  } else {
    currentProject.value = null
  }

  // Save current streaming state before switching
  if (currentConvId.value) {
    if (streamingConvs.has(currentConvId.value)) {
      streamStates.set(currentConvId.value, {
        streaming: true,
        streamProcessSteps: [...streamProcessSteps.value],
        messages: [...messages.value],
      })
    }
  }

  currentConvId.value = id
  nextMsgCursor.value = null
  hasMoreMessages.value = false

  // Restore streaming state for new conversation
  const savedState = streamStates.get(id)
  const isThisConvStreaming = streamingConvs.has(id)
  if (savedState && savedState.streaming) {
    streaming.value = true
    streamProcessSteps.value = savedState.streamProcessSteps
    messages.value = savedState.messages || []
  } else if (!isThisConvStreaming) {
    setStreamState(false, currentConvId.value)
    messages.value = []
  } else {
    // This conv is streaming but we don't have saved state (e.g. started from background)
    streaming.value = true
    streamProcessSteps.value = []
  }

  if (!streaming.value) {
    await loadMessages(true)
  }
}

// -- Load messages --
async function loadMessages(reset = true) {
  if (!currentConvId.value || loadingMessages.value) return
  loadingMessages.value = true
  try {
    const res = await messageApi.list(currentConvId.value, reset ? null : nextMsgCursor.value)
    if (reset) {
      messages.value = res.data.items.filter(m => m.role !== 'tool')
    } else {
      messages.value = [...res.data.items.filter(m => m.role !== 'tool'), ...messages.value]
    }
    nextMsgCursor.value = res.data.next_cursor
    hasMoreMessages.value = res.data.has_more
  } catch (e) {
    console.error('Failed to load messages:', e)
  } finally {
    loadingMessages.value = false
  }
}

function loadMoreMessages() {
  if (hasMoreMessages.value) loadMessages(false)
}

// -- Helpers: create stream callbacks for a conversation --
function createStreamCallbacks(convId, { updateConvList = true } = {}) {
  return {
    onProcessStep(step) {
      // Update or insert step by index position.
      // thinking/text steps are sent incrementally with the same id — each update
      // replaces the previous content at that index. tool_call/tool_result are appended.
      updateStreamField(convId, 'streamProcessSteps', streamProcessSteps, prev => {
        const steps = prev ? [...prev] : []
        while (steps.length <= step.index) steps.push(null)
        steps[step.index] = step
        return steps
      })
    },
    async onDone(data) {
      streamStates.delete(convId)
      streamingConvs.delete(convId)
      streamAborters.delete(convId)

      if (currentConvId.value === convId) {
        streaming.value = false

        // Build the final message object.
        // process_steps is the primary ordered data for rendering (thinking/text/tool_call/tool_result).
        // When page reloads, these steps are loaded from DB via the 'steps' field in content JSON.
        const steps = streamProcessSteps.value.filter(Boolean)
        const textSteps = steps.filter(s => s.type === 'text')
        const lastText = textSteps.length > 0 ? textSteps[textSteps.length - 1].content : ''

        // Derive legacy tool_calls from processSteps (backward compat for DB and MessageBubble fallback)
        const toolCallSteps = steps.filter(s => s && s.type === 'tool_call')
        const toolResultMap = {}
        for (const s of steps) {
          if (s && s.type === 'tool_result') toolResultMap[s.id_ref] = s.content
        }
        const legacyToolCalls = toolCallSteps.length > 0
          ? toolCallSteps.map(tc => ({
              id: tc.id_ref || tc.id,
              type: 'function',
              function: { name: tc.name, arguments: tc.arguments },
              result: toolResultMap[tc.id_ref || tc.id] || null,
            }))
          : null

        messages.value = [...messages.value, {
          id: data.message_id,
          conversation_id: convId,
          role: 'assistant',
          text: lastText,
          tool_calls: legacyToolCalls,
          process_steps: steps,
          token_count: data.token_count,
          created_at: new Date().toISOString(),
        }]
        setStreamState(false, convId)

        if (updateConvList) {
          const idx = conversations.value.findIndex(c => c.id === convId)
          if (idx >= 0) {
            const conv = conversations.value[idx]
            const updated = {
              ...conv,
              message_count: (conv.message_count || 0) + 2,
              ...(data.suggested_title ? { title: data.suggested_title } : {}),
            }
            const newList = conversations.value.filter((_, i) => i !== idx)
            conversations.value = [updated, ...newList]
          }
        }
      } else {
        try {
          const res = await messageApi.list(convId, null, 50)
          const idx = conversations.value.findIndex(c => c.id === convId)
          if (idx >= 0) {
            const conv = conversations.value[idx]
            const updates = { message_count: res.data.items.length }
            if (res.data.items.length > 0) {
              const convRes = await conversationApi.get(convId)
              if (convRes.data.title) updates.title = convRes.data.title
            }
            conversations.value = conversations.value.map((c, i) => i === idx ? { ...c, ...updates } : c)
          }
        } catch (_) {}
      }
    },
    onError(msg) {
      streamStates.delete(convId)
      streamingConvs.delete(convId)
      streamAborters.delete(convId)
      if (currentConvId.value === convId) {
        setStreamState(false, convId)
        console.error('Stream error:', msg)
      }
    },
  }
}

// -- Send message (streaming) --
async function sendMessage(data) {
  if (!currentConvId.value || streamingConvs.has(currentConvId.value)) return

  const convId = currentConvId.value
  const text = data.text || ''
  const attachments = data.attachments || null

  const userMsg = {
    id: 'temp_' + Date.now(),
    conversation_id: convId,
    role: 'user',
    text,
    attachments: attachments ? attachments.map(a => ({ name: a.name, extension: a.extension })) : null,
    token_count: 0,
    created_at: new Date().toISOString(),
  }
  messages.value = [...messages.value, userMsg]

  setStreamState(true, convId)

  const stream = messageApi.send(convId, { text, attachments, projectId: currentProject.value?.id }, {
    toolsEnabled: toolsEnabled.value,
    ...createStreamCallbacks(convId, { updateConvList: true }),
  })
  streamAborters.set(convId, () => stream.abort())
}

// -- Delete message --
async function deleteMessage(msgId) {
  if (!currentConvId.value) return
  try {
    await messageApi.delete(currentConvId.value, msgId)
    messages.value = messages.value.filter(m => m.id !== msgId)
  } catch (e) {
    console.error('Failed to delete message:', e)
  }
}

// -- Regenerate message --
async function regenerateMessage(msgId) {
  if (!currentConvId.value || streamingConvs.has(currentConvId.value)) return

  const convId = currentConvId.value
  const msgIndex = messages.value.findIndex(m => m.id === msgId)
  if (msgIndex === -1) return

  messages.value = messages.value.slice(0, msgIndex)

  setStreamState(true, convId)

  const stream = messageApi.regenerate(convId, msgId, {
    toolsEnabled: toolsEnabled.value,
    projectId: currentProject.value?.id,
    ...createStreamCallbacks(convId, { updateConvList: false }),
  })
  streamAborters.set(convId, () => stream.abort())
}

// -- Delete conversation --
async function deleteConversation(id) {
  try {
    await conversationApi.delete(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConvId.value === id) {
      currentConvId.value = conversations.value.length > 0 ? conversations.value[0].id : null
      if (currentConvId.value) {
        await selectConversation(currentConvId.value)
      } else {
        messages.value = []
        currentProject.value = null
      }
    }
  } catch (e) {
    console.error('Failed to delete conversation:', e)
  }
}

// -- Save settings --
async function saveSettings(data) {
  if (!currentConvId.value) return
  try {
    const res = await conversationApi.update(currentConvId.value, data)
    const idx = conversations.value.findIndex(c => c.id === currentConvId.value)
    if (idx !== -1) {
      conversations.value = conversations.value.map((c, i) => i === idx ? { ...c, ...res.data } : c)
    }
  } catch (e) {
    console.error('Failed to save settings:', e)
  }
}

// -- Update tools enabled --
function updateToolsEnabled(val) {
  toolsEnabled.value = val
  localStorage.setItem('tools_enabled', String(val))
}

// -- Browse project files --
function browseProject(project) {
  currentProject.value = project
  showFileExplorer.value = true
}

// -- Create project --
async function createProject() {
  if (!newProjectName.value.trim()) return
  creatingProject.value = true
  try {
    await projectApi.create({
      name: newProjectName.value.trim(),
      description: newProjectDesc.value.trim(),
    })
    showCreateModal.value = false
    newProjectName.value = ''
    newProjectDesc.value = ''
    await loadProjects()
  } catch (e) {
    console.error('Failed to create project:', e)
  } finally {
    creatingProject.value = false
  }
}

// -- Load projects --
async function loadProjects() {
  try {
    const res = await projectApi.list()
    projects.value = res.data.items || []
  } catch (e) {
    console.error('Failed to load projects:', e)
  }
}

// -- Delete project --
async function deleteProject(project) {
  const ok = await modal.confirm('删除确认', `确定删除项目「${project.name}」及其所有对话？`, { danger: true })
  if (!ok) return
  try {
    await projectApi.delete(project.id)
    // Remove conversations belonging to this project
    conversations.value = conversations.value.filter(c => c.project_id !== project.id)
    // If current conversation was in this project, switch away
    if (currentConvId.value && conversations.value.length > 0) {
      const currentConv = conversations.value.find(c => c.id === currentConvId.value)
      if (!currentConv || currentConv.project_id === project.id) {
        await selectConversation(conversations.value[0].id)
      }
    } else if (conversations.value.length === 0) {
      currentConvId.value = null
      messages.value = []
      currentProject.value = null
    }
    if (currentProject.value?.id === project.id) {
      currentProject.value = null
      showFileExplorer.value = false
    }
    await loadProjects()
  } catch (e) {
    console.error('Failed to delete project:', e)
  }
}

// -- Init --
onMounted(async () => {
  await loadModels()
  loadProjects()
  loadConversations()
})
</script>

<style>
.app {
  display: flex;
  height: 100%;
}

.file-explorer-wrap {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  min-width: 0;
}

.explorer-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.topbar-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.topbar-project-name {
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 4px 10px;
  border-radius: 6px;
}

.explorer-body {
  flex: 1;
  overflow: hidden;
  min-height: 0;
  display: flex;
}

/* explorer-empty now uses global .empty-state */

.create-modal {
  background: var(--bg-primary);
  border: 1px solid var(--border-medium);
  border-radius: 12px;
  width: 90%;
  max-width: 440px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
</style>

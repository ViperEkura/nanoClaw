<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :current-id="currentConvId"
      :loading="loadingConvs"
      :has-more="hasMoreConvs"
      :current-project="currentProject"
      @select="selectConversation"
      @create="createConversation"
      @delete="deleteConversation"
      @load-more="loadMoreConversations"
      @select-project="selectProject"
    />

    <ChatView
      :conversation="currentConv"
      :messages="messages"
      :streaming="streaming"
      :streaming-content="streamContent"
      :streaming-thinking="streamThinking"
      :streaming-tool-calls="streamToolCalls"
      :streaming-process-steps="streamProcessSteps"
      :has-more-messages="hasMoreMessages"
      :loading-more="loadingMessages"
      :tools-enabled="toolsEnabled"
      @send-message="sendMessage"
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
            :visible="showSettings"
            :conversation="currentConv"
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
  </div>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted, defineAsyncComponent } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatView from './components/ChatView.vue'

const SettingsPanel = defineAsyncComponent(() => import('./components/SettingsPanel.vue'))
const StatsPanel = defineAsyncComponent(() => import('./components/StatsPanel.vue'))
import { conversationApi, messageApi } from './api'

// -- Conversations state --
const conversations = shallowRef([])
const currentConvId = ref(null)
const loadingConvs = ref(false)
const hasMoreConvs = ref(false)
const nextConvCursor = ref(null)

// -- Messages state --
const messages = shallowRef([])
const hasMoreMessages = ref(false)
const loadingMessages = ref(false)
const nextMsgCursor = ref(null)

// -- Streaming state --
const streaming = ref(false)
const streamContent = ref('')
const streamThinking = ref('')
const streamToolCalls = shallowRef([])
const streamProcessSteps = shallowRef([])

// 保存每个对话的流式状态
const streamStates = new Map()

// 重置当前流式状态（用于 sendMessage / regenerateMessage / onError）
function resetStreamState() {
  streaming.value = false
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamProcessSteps.value = []
}

// 初始化流式状态（用于 sendMessage / regenerateMessage 开始时）
function initStreamState() {
  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamProcessSteps.value = []
}

// 辅助：更新当前对话或缓存的流式字段
// field: streamStates 中保存的字段名
// ref: 当前激活对话对应的 Vue ref
// valueOrUpdater: 静态值或 (current) => newValue
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
const toolsEnabled = ref(localStorage.getItem('tools_enabled') !== 'false') // 默认开启
const currentProject = ref(null) // Current selected project

function togglePanel(panel) {
  if (panel === 'settings') {
    showSettings.value = !showSettings.value
    if (showSettings.value) showStats.value = false
  } else {
    showStats.value = !showStats.value
    if (showStats.value) showSettings.value = false
  }
}

const currentConv = computed(() =>
  conversations.value.find(c => c.id === currentConvId.value) || null
)

// -- Load conversations --
async function loadConversations(reset = true) {
  if (loadingConvs.value) return
  loadingConvs.value = true
  try {
    const projectId = currentProject.value?.id || null
    const res = await conversationApi.list(reset ? null : nextConvCursor.value, 20, projectId)
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

// -- Create conversation --
async function createConversation() {
  try {
    const res = await conversationApi.create({
      title: '新对话',
      project_id: currentProject.value?.id || null,
    })
    conversations.value = [res.data, ...conversations.value]
    await selectConversation(res.data.id)
  } catch (e) {
    console.error('Failed to create conversation:', e)
  }
}

// -- Select conversation --
async function selectConversation(id) {
  // 保存当前对话的流式状态和消息列表（如果有）
  if (currentConvId.value && streaming.value) {
    streamStates.set(currentConvId.value, {
      streaming: true,
      streamContent: streamContent.value,
      streamThinking: streamThinking.value,
      streamToolCalls: [...streamToolCalls.value],
      streamProcessSteps: [...streamProcessSteps.value],
      messages: [...messages.value],  // 保存消息列表（包括临时用户消息）
    })
  }

  currentConvId.value = id
  nextMsgCursor.value = null
  hasMoreMessages.value = false

  // 恢复新对话的流式状态
  const savedState = streamStates.get(id)
  if (savedState && savedState.streaming) {
    streaming.value = true
    streamContent.value = savedState.streamContent
    streamThinking.value = savedState.streamThinking
    streamToolCalls.value = savedState.streamToolCalls
    streamProcessSteps.value = savedState.streamProcessSteps
    messages.value = savedState.messages || []  // 恢复消息列表
  } else {
    resetStreamState()
    messages.value = []
  }

  // 如果不是正在流式传输，从服务器加载消息
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
      // Filter out tool messages (they're merged into assistant messages)
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
    onThinkingStart() {
      updateStreamField(convId, 'streamThinking', streamThinking, '')
      updateStreamField(convId, 'streamContent', streamContent, '')
    },
    onThinking(text) {
      updateStreamField(convId, 'streamThinking', streamThinking, prev => (prev || '') + text)
    },
    onMessage(text) {
      updateStreamField(convId, 'streamContent', streamContent, prev => (prev || '') + text)
    },
    onToolCalls(calls) {
      updateStreamField(convId, 'streamToolCalls', streamToolCalls, prev => [
        ...(prev || []),
        ...calls.map(c => ({ ...c, result: null })),
      ])
    },
    onToolResult(result) {
      updateStreamField(convId, 'streamToolCalls', streamToolCalls, prev => {
        const arr = prev ? [...prev] : []
        const call = arr.find(c => c.id === result.id)
        if (call) call.result = result.content
        return arr
      })
    },
    onProcessStep(step) {
      updateStreamField(convId, 'streamProcessSteps', streamProcessSteps, prev => {
        const steps = prev ? [...prev] : []
        while (steps.length <= step.index) steps.push(null)
        steps[step.index] = step
        return steps
      })
    },
    async onDone(data) {
      streamStates.delete(convId)

      if (currentConvId.value === convId) {
        streaming.value = false
        messages.value = [...messages.value, {
          id: data.message_id,
          conversation_id: convId,
          role: 'assistant',
          text: streamContent.value,
          thinking: streamThinking.value || null,
          tool_calls: streamToolCalls.value.length > 0 ? streamToolCalls.value : null,
          process_steps: streamProcessSteps.value.filter(Boolean),
          token_count: data.token_count,
          created_at: new Date().toISOString(),
        }]
        resetStreamState()

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
      if (currentConvId.value === convId) {
        resetStreamState()
        console.error('Stream error:', msg)
      }
    },
  }
}

// -- Send message (streaming) --
async function sendMessage(data) {
  if (!currentConvId.value || streaming.value) return

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

  initStreamState()

  messageApi.send(convId, { text, attachments, projectId: currentProject.value?.id }, {
    toolsEnabled: toolsEnabled.value,
    ...createStreamCallbacks(convId, { updateConvList: true }),
  })
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
  if (!currentConvId.value || streaming.value) return

  const convId = currentConvId.value
  const msgIndex = messages.value.findIndex(m => m.id === msgId)
  if (msgIndex === -1) return

  messages.value = messages.value.slice(0, msgIndex)

  initStreamState()

  messageApi.regenerate(convId, msgId, {
    toolsEnabled: toolsEnabled.value,
    projectId: currentProject.value?.id,
    ...createStreamCallbacks(convId, { updateConvList: false }),
  })
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

// -- Select project --
function selectProject(project) {
  currentProject.value = project
  // Reload conversations filtered by the selected project
  nextConvCursor.value = null
  loadConversations(true)
}

// -- Init --
onMounted(() => {
  loadConversations()
})
</script>

<style>
.app {
  display: flex;
  height: 100%;
}

.modal-content {
  border-radius: 16px;
  width: 90%;
  max-width: 520px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 24px;
  background: color-mix(in srgb, var(--bg-primary) 75%, transparent);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid var(--border-medium);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.2);
}
</style>

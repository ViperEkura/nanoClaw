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
      @toggle-settings="showSettings = true"
      @toggle-stats="showStats = true"
      @load-more-messages="loadMoreMessages"
      @toggle-tools="updateToolsEnabled"
    />

    <SettingsPanel
      v-if="showSettings"
      :visible="showSettings"
      :conversation="currentConv"
      @close="showSettings = false"
      @save="saveSettings"
    />

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
import { ref, computed, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatView from './components/ChatView.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import StatsPanel from './components/StatsPanel.vue'
import { conversationApi, messageApi } from './api'

// -- Conversations state --
const conversations = ref([])
const currentConvId = ref(null)
const loadingConvs = ref(false)
const hasMoreConvs = ref(false)
const nextConvCursor = ref(null)

// -- Messages state --
const messages = ref([])
const hasMoreMessages = ref(false)
const loadingMessages = ref(false)
const nextMsgCursor = ref(null)

// -- Streaming state --
const streaming = ref(false)
const streamContent = ref('')
const streamThinking = ref('')
const streamToolCalls = ref([])
const streamProcessSteps = ref([])

function resetStreamState() {
  streaming.value = false
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamProcessSteps.value = []
  currentStreamPromise = null
}

// 保存每个对话的流式状态
const streamStates = new Map()

// 保存当前流式请求引用
let currentStreamPromise = null

// -- UI state --
const showSettings = ref(false)
const showStats = ref(false)
const toolsEnabled = ref(localStorage.getItem('tools_enabled') !== 'false') // 默认开启
const currentProject = ref(null) // Current selected project

const currentConv = computed(() =>
  conversations.value.find(c => c.id === currentConvId.value) || null
)

// -- Load conversations --
async function loadConversations(reset = true) {
  if (loadingConvs.value) return
  loadingConvs.value = true
  try {
    const res = await conversationApi.list(reset ? null : nextConvCursor.value)
    if (reset) {
      conversations.value = res.data.items
    } else {
      conversations.value.push(...res.data.items)
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
    const res = await conversationApi.create({ title: '新对话' })
    conversations.value.unshift(res.data)
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
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    streamProcessSteps.value = []
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
      if (currentConvId.value === convId) {
        streamThinking.value = ''
      } else {
        const saved = streamStates.get(convId) || {}
        streamStates.set(convId, { ...saved, streamThinking: '' })
      }
    },
    onThinking(text) {
      if (currentConvId.value === convId) {
        streamThinking.value += text
      } else {
        const saved = streamStates.get(convId) || { streamThinking: '' }
        streamStates.set(convId, { ...saved, streamThinking: (saved.streamThinking || '') + text })
      }
    },
    onMessage(text) {
      if (currentConvId.value === convId) {
        streamContent.value += text
      } else {
        const saved = streamStates.get(convId) || { streamContent: '' }
        streamStates.set(convId, { ...saved, streamContent: (saved.streamContent || '') + text })
      }
    },
    onToolCalls(calls) {
      if (currentConvId.value === convId) {
        streamToolCalls.value.push(...calls.map(c => ({ ...c, result: null })))
      } else {
        const saved = streamStates.get(convId) || { streamToolCalls: [] }
        const newCalls = [...(saved.streamToolCalls || []), ...calls.map(c => ({ ...c, result: null }))]
        streamStates.set(convId, { ...saved, streamToolCalls: newCalls })
      }
    },
    onToolResult(result) {
      if (currentConvId.value === convId) {
        const call = streamToolCalls.value.find(c => c.id === result.id)
        if (call) call.result = result.content
      } else {
        const saved = streamStates.get(convId) || { streamToolCalls: [] }
        const call = saved.streamToolCalls?.find(c => c.id === result.id)
        if (call) call.result = result.content
        streamStates.set(convId, { ...saved })
      }
    },
    onProcessStep(step) {
      const idx = step.index
      if (currentConvId.value === convId) {
        const newSteps = [...streamProcessSteps.value]
        while (newSteps.length <= idx) newSteps.push(null)
        newSteps[idx] = step
        streamProcessSteps.value = newSteps
      } else {
        const saved = streamStates.get(convId) || { streamProcessSteps: [] }
        const steps = [...(saved.streamProcessSteps || [])]
        while (steps.length <= idx) steps.push(null)
        steps[idx] = step
        streamStates.set(convId, { ...saved, streamProcessSteps: steps })
      }
    },
    async onDone(data) {
      streamStates.delete(convId)

      if (currentConvId.value === convId) {
        streaming.value = false
        currentStreamPromise = null
        messages.value.push({
          id: data.message_id,
          conversation_id: convId,
          role: 'assistant',
          text: streamContent.value,
          thinking: streamThinking.value || null,
          tool_calls: streamToolCalls.value.length > 0 ? streamToolCalls.value : null,
          process_steps: streamProcessSteps.value.filter(Boolean),
          token_count: data.token_count,
          created_at: new Date().toISOString(),
        })
        resetStreamState()

        if (updateConvList) {
          const idx = conversations.value.findIndex(c => c.id === convId)
          if (idx >= 0) {
            const conv = idx > 0 ? conversations.value.splice(idx, 1)[0] : conversations.value[0]
            conv.message_count = (conv.message_count || 0) + 2
            if (data.suggested_title) conv.title = data.suggested_title
            if (idx > 0) conversations.value.unshift(conv)
          }
        }
      } else {
        try {
          const res = await messageApi.list(convId, null, 50)
          const idx = conversations.value.findIndex(c => c.id === convId)
          if (idx >= 0) {
            conversations.value[idx].message_count = res.data.items.length
            if (res.data.items.length > 0) {
              const convRes = await conversationApi.get(convId)
              if (convRes.data.title) conversations.value[idx].title = convRes.data.title
            }
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
  messages.value.push(userMsg)

  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamProcessSteps.value = []

  currentStreamPromise = messageApi.send(convId, { text, attachments, projectId: currentProject.value?.id }, {
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

  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamProcessSteps.value = []

  currentStreamPromise = messageApi.regenerate(convId, msgId, {
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
      conversations.value[idx] = { ...conversations.value[idx], ...res.data }
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

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: 16px;
  width: 90%;
  max-width: 520px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 24px;
}
</style>

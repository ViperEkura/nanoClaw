<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :current-id="currentConvId"
      :loading="loadingConvs"
      :has-more="hasMoreConvs"
      @select="selectConversation"
      @create="createConversation"
      @delete="deleteConversation"
      @load-more="loadMoreConversations"
    />

    <ChatView
      ref="chatViewRef"
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
      @toggle-settings="showSettings = true"
      @load-more-messages="loadMoreMessages"
      @toggle-tools="updateToolsEnabled"
    />

    <SettingsPanel
      :visible="showSettings"
      :conversation="currentConv"
      @close="showSettings = false"
      @save="saveSettings"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatView from './components/ChatView.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import { conversationApi, messageApi } from './api'

const chatViewRef = ref(null)

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

// 保存每个对话的流式状态
const streamStates = new Map()

// 保存当前流式请求引用
let currentStreamPromise = null

// -- UI state --
const showSettings = ref(false)
const toolsEnabled = ref(localStorage.getItem('tools_enabled') !== 'false') // 默认开启

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

// -- Send message (streaming) --
async function sendMessage(content) {
  if (!currentConvId.value || streaming.value) return

  const convId = currentConvId.value  // 保存当前对话ID

  // Add user message optimistically
  const userMsg = {
    id: 'temp_' + Date.now(),
    conversation_id: convId,
    role: 'user',
    content,
    token_count: 0,
    thinking_content: null,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)

  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  streamProcessSteps.value = []

  currentStreamPromise = messageApi.send(convId, content, {
    stream: true,
    toolsEnabled: toolsEnabled.value,
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
      console.log('🔧 Tool calls received:', calls)
      if (currentConvId.value === convId) {
        streamToolCalls.value.push(...calls.map(c => ({ ...c, result: null })))
      } else {
        const saved = streamStates.get(convId) || { streamToolCalls: [] }
        const newCalls = [...(saved.streamToolCalls || []), ...calls.map(c => ({ ...c, result: null }))]
        streamStates.set(convId, { ...saved, streamToolCalls: newCalls })
      }
    },
    onToolResult(result) {
      console.log('✅ Tool result received:', result)
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
        // 创建新数组确保响应式更新
        const newSteps = [...streamProcessSteps.value]
        while (newSteps.length <= idx) {
          newSteps.push(null)
        }
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
      // 清除保存的状态
      streamStates.delete(convId)

      if (currentConvId.value === convId) {
        streaming.value = false
        currentStreamPromise = null
        // 添加助手消息（保留临时用户消息）
        messages.value.push({
          id: data.message_id,
          conversation_id: convId,
          role: 'assistant',
          content: streamContent.value,
          token_count: data.token_count,
          thinking_content: streamThinking.value || null,
          tool_calls: streamToolCalls.value.length > 0 ? streamToolCalls.value : null,
          process_steps: streamProcessSteps.value.filter(Boolean),
          created_at: new Date().toISOString(),
        })
        streamContent.value = ''
        streamThinking.value = ''
        streamToolCalls.value = []
        streamProcessSteps.value = []
        // Update conversation in list (move to top)
        const idx = conversations.value.findIndex(c => c.id === convId)
        if (idx > 0) {
          const [conv] = conversations.value.splice(idx, 1)
          conv.message_count = (conv.message_count || 0) + 2
          conversations.value.unshift(conv)
        } else if (idx === 0) {
          conversations.value[0].message_count = (conversations.value[0].message_count || 0) + 2
        }
        // Auto title: use first message if title is empty
        if (conversations.value[0] && !conversations.value[0].title) {
          try {
            await conversationApi.update(convId, { title: content.slice(0, 30) })
            conversations.value[0].title = content.slice(0, 30)
          } catch (_) {}
        }
      } else {
        // 后台完成，重新加载该对话的消息
        try {
          const res = await messageApi.list(convId, null, 50)
          // 更新对话列表中的消息计数
          const idx = conversations.value.findIndex(c => c.id === convId)
          if (idx >= 0) {
            conversations.value[idx].message_count = res.data.items.length
          }
        } catch (_) {}
      }
    },
    onError(msg) {
      streamStates.delete(convId)
      if (currentConvId.value === convId) {
        streaming.value = false
        currentStreamPromise = null
        streamContent.value = ''
        streamThinking.value = ''
        streamToolCalls.value = []
        streamProcessSteps.value = []
        console.error('Stream error:', msg)
      }
    },
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

// -- Init --
onMounted(() => {
  loadConversations()
})
</script>

<style>
:root {
  /* Light theme */
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f0f4f8;
  --bg-hover: rgba(37, 99, 235, 0.06);
  --bg-active: rgba(37, 99, 235, 0.12);
  --bg-input: #f8fafc;
  --bg-code: #f1f5f9;
  --bg-thinking: #f1f5f9;

  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;

  --border-light: rgba(0, 0, 0, 0.06);
  --border-medium: rgba(0, 0, 0, 0.08);
  --border-input: rgba(0, 0, 0, 0.08);

  --accent-primary: #2563eb;
  --accent-primary-hover: #3b82f6;
  --accent-primary-light: rgba(37, 99, 235, 0.08);
  --accent-primary-medium: rgba(37, 99, 235, 0.15);

  --success-color: #059669;
  --success-bg: rgba(16, 185, 129, 0.1);
  --danger-color: #ef4444;
  --danger-bg: rgba(239, 68, 68, 0.08);

  --scrollbar-thumb: rgba(0, 0, 0, 0.08);
  --scrollbar-thumb-sidebar: rgba(0, 0, 0, 0.1);

  --overlay-bg: rgba(0, 0, 0, 0.3);

  --avatar-gradient: linear-gradient(135deg, #3b82f6, #60a5fa);
}

[data-theme="dark"] {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #0f172a;
  --bg-hover: rgba(59, 130, 246, 0.15);
  --bg-active: rgba(59, 130, 246, 0.25);
  --bg-input: #1e293b;
  --bg-code: #1e293b;
  --bg-thinking: #1e293b;

  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-tertiary: #64748b;

  --border-light: rgba(255, 255, 255, 0.08);
  --border-medium: rgba(255, 255, 255, 0.1);
  --border-input: rgba(255, 255, 255, 0.1);

  --accent-primary: #3b82f6;
  --accent-primary-hover: #60a5fa;
  --accent-primary-light: rgba(59, 130, 246, 0.15);
  --accent-primary-medium: rgba(59, 130, 246, 0.25);

  --success-color: #34d399;
  --success-bg: rgba(52, 211, 153, 0.15);
  --danger-color: #f87171;
  --danger-bg: rgba(248, 113, 113, 0.15);

  --scrollbar-thumb: rgba(255, 255, 255, 0.1);
  --scrollbar-thumb-sidebar: rgba(255, 255, 255, 0.15);

  --overlay-bg: rgba(0, 0, 0, 0.6);

  --avatar-gradient: linear-gradient(135deg, #3b82f6, #60a5fa);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  transition: background 0.2s, color 0.2s;
}

#app {
  height: 100%;
}

.app {
  display: flex;
  height: 100%;
}
</style>

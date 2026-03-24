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
      :has-more-messages="hasMoreMessages"
      :loading-more="loadingMessages"
      @send-message="sendMessage"
      @delete-message="deleteMessage"
      @toggle-settings="showSettings = true"
      @load-more-messages="loadMoreMessages"
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

// -- UI state --
const showSettings = ref(false)

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
  currentConvId.value = id
  messages.value = []
  nextMsgCursor.value = null
  hasMoreMessages.value = false
  streamContent.value = ''
  streamThinking.value = ''
  await loadMessages(true)
}

// -- Load messages --
async function loadMessages(reset = true) {
  if (!currentConvId.value || loadingMessages.value) return
  loadingMessages.value = true
  try {
    const res = await messageApi.list(currentConvId.value, reset ? null : nextMsgCursor.value)
    if (reset) {
      messages.value = res.data.items
    } else {
      messages.value = [...res.data.items, ...messages.value]
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

  // Add user message optimistically
  const userMsg = {
    id: 'temp_' + Date.now(),
    conversation_id: currentConvId.value,
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

  await messageApi.send(currentConvId.value, content, {
    stream: true,
    onThinking(text) {
      streamThinking.value += text
    },
    onMessage(text) {
      streamContent.value += text
    },
    async onDone(data) {
      streaming.value = false
      // Replace temp message and add assistant message from server
      messages.value = messages.value.filter(m => m.id !== userMsg.id)
      messages.value.push({
        id: data.message_id,
        conversation_id: currentConvId.value,
        role: 'assistant',
        content: streamContent.value,
        token_count: data.token_count,
        thinking_content: streamThinking.value || null,
        created_at: new Date().toISOString(),
      })
      streamContent.value = ''
      streamThinking.value = ''
      // Update conversation in list (move to top)
      const idx = conversations.value.findIndex(c => c.id === currentConvId.value)
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
          await conversationApi.update(currentConvId.value, { title: content.slice(0, 30) })
          conversations.value[0].title = content.slice(0, 30)
        } catch (_) {}
      }
    },
    onError(msg) {
      streaming.value = false
      streamContent.value = ''
      streamThinking.value = ''
      console.error('Stream error:', msg)
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

// -- Init --
onMounted(() => {
  loadConversations()
})
</script>

<style>
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
  background: #0f172a;
  color: #e2e8f0;
  -webkit-font-smoothing: antialiased;
}

#app {
  height: 100%;
}

.app {
  display: flex;
  height: 100%;
}
</style>

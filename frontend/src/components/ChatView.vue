<template>
  <div class="chat-view main-panel">
    <div v-if="!conversation" class="welcome">
      <div class="welcome-icon"><svg viewBox="0 0 64 64" width="36" height="36"><rect width="64" height="64" rx="14" fill="url(#favBg)"/><defs><linearGradient id="favBg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#60a5fa"/></linearGradient></defs><text x="32" y="40" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="18" font-weight="800" fill="#fff" letter-spacing="-0.5">claw</text></svg></div>
      <h1>Chat</h1>
      <p>选择一个对话开始，或创建新对话</p>
    </div>

    <template v-else>
      <div class="chat-header">
        <div class="chat-title-area">
          <h2 class="chat-title">{{ conversation.title || '新对话' }}</h2>
          <span class="model-badge">{{ formatModelName(conversation.model) }}</span>
          <span v-if="conversation.thinking_enabled" class="thinking-badge">思考</span>
        </div>
      </div>

      <div ref="scrollContainer" class="messages-container">
          <div v-if="hasMoreMessages" class="load-more-top">
            <button @click="$emit('loadMoreMessages')" :disabled="loadingMore">
              {{ loadingMore ? '加载中...' : '加载更早的消息' }}
            </button>
          </div>

          <div class="messages-list">
            <div
              v-for="msg in messages"
              :key="msg.id"
              :data-msg-id="msg.id"
              v-memo="[msg.text, msg.tool_calls, msg.process_steps, msg.attachments]"
            >
              <MessageBubble
                :role="msg.role"
                :text="msg.text"
                :tool-calls="msg.tool_calls"
                :process-steps="msg.process_steps"
                :token-count="msg.token_count"
                :created-at="msg.created_at"
                :deletable="msg.role === 'user'"
                :attachments="msg.attachments"
                @delete="$emit('deleteMessage', msg.id)"
                @regenerate="$emit('regenerateMessage', msg.id)"
              />
            </div>

            <div v-if="streaming" class="message-bubble assistant streaming">
              <div class="avatar">claw</div>
              <div class="message-body">
                <ProcessBlock
                  :process-steps="streamingProcessSteps"
                  :streaming-content="streamingContent"
                  :streaming="streaming"
                />
              </div>
            </div>
          </div>
        </div>

        <MessageInput
          ref="inputRef"
          :disabled="streaming"
          :tools-enabled="toolsEnabled"
          @send="$emit('sendMessage', $event)"
          @toggle-tools="$emit('toggleTools', $event)"
        />
    </template>

    <MessageNav
      v-if="conversation"
      :messages="messages"
      :active-id="activeMessageId"
      @scroll-to="scrollToMessage"
    />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import MessageBubble from './MessageBubble.vue'
import MessageInput from './MessageInput.vue'
import MessageNav from './MessageNav.vue'
import ProcessBlock from './ProcessBlock.vue'
import { modelApi } from '../api'

const props = defineProps({
  conversation: { type: Object, default: null },
  messages: { type: Array, required: true },
  streaming: { type: Boolean, default: false },
  streamingContent: { type: String, default: '' },
  streamingProcessSteps: { type: Array, default: () => [] },
  hasMoreMessages: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
  toolsEnabled: { type: Boolean, default: true },
})

const emit = defineEmits(['sendMessage', 'deleteMessage', 'regenerateMessage', 'toggleSettings', 'toggleStats', 'loadMoreMessages', 'toggleTools'])

const scrollContainer = ref(null)
const inputRef = ref(null)
const modelNameMap = ref({})
const activeMessageId = ref(null)
let scrollObserver = null
const observedElements = new WeakSet()

function formatModelName(modelId) {
  return modelNameMap.value[modelId] || modelId
}

onMounted(async () => {
  try {
    const res = await modelApi.getCached()
    const map = {}
    for (const m of res.data) {
      if (m.id && m.name) map[m.id] = m.name
    }
    modelNameMap.value = map
  } catch (e) {
    console.warn('Failed to load model names:', e)
  }

  if (scrollContainer.value) {
    scrollObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            activeMessageId.value = entry.target.dataset.msgId || null
          }
        }
      },
      { root: scrollContainer.value, threshold: 0.5 }
    )
  }
})

onUnmounted(() => {
  scrollObserver?.disconnect()
})

watch(() => props.messages.length, () => {
  nextTick(() => {
    if (!scrollObserver || !scrollContainer.value) return
    const wrappers = scrollContainer.value.querySelectorAll('[data-msg-id]')
    wrappers.forEach(el => {
      if (!observedElements.has(el)) {
        scrollObserver.observe(el)
        observedElements.add(el)
      }
    })
  })
})

function scrollToMessage(msgId) {
  nextTick(() => {
    if (!scrollContainer.value) return
    const el = scrollContainer.value.querySelector(`[data-msg-id="${msgId}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      activeMessageId.value = msgId
    }
  })
}

// 流式时使用 instant 滚动，避免 smooth 动画与内容增长互相打架造成抖动
watch([() => props.messages.length, () => props.streamingContent], () => {
  nextTick(() => {
    const el = scrollContainer.value
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: props.streaming ? 'instant' : 'smooth' })
  })
})

watch(() => props.conversation?.id, () => {
  if (props.conversation) {
    nextTick(() => inputRef.value?.focus())
  }
})
</script>

<style scoped>
.chat-view {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  min-width: 0;
}

.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.welcome-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  overflow: hidden;
}

.welcome h1 {
  font-size: 24px;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.welcome p {
  font-size: 14px;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border-light);
  background: color-mix(in srgb, var(--bg-primary) 70%, transparent);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  transition: background 0.2s, border-color 0.2s;
}

.chat-title-area {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.chat-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-badge {
  background: var(--accent-primary-medium);
  color: var(--accent-primary);
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 500;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.thinking-badge {
  background: var(--success-bg);
  color: var(--success-color);
}




.messages-container {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 16px 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.messages-container::-webkit-scrollbar {
  display: none;
}

.load-more-top {
  text-align: center;
  padding: 12px 0;
}

.load-more-top button {
  background: none;
  border: 1px solid var(--border-medium);
  color: var(--text-secondary);
  padding: 6px 16px;
  border-radius: 16px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}

.load-more-top button:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.messages-list {
  width: 80%;
  margin: 0 auto;
  padding: 0 16px;
}

/* .message-bubble, .avatar, .message-body now in global.css */



</style>

<template>
  <div class="chat-view">
    <div v-if="!conversation" class="welcome">
      <div class="welcome-icon"><svg viewBox="0 0 64 64" width="36" height="36"><rect width="64" height="64" rx="14" fill="url(#favBg)"/><defs><linearGradient id="favBg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#60a5fa"/></linearGradient></defs><text x="32" y="40" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="18" font-weight="800" fill="#fff" letter-spacing="-0.5">claw</text></svg></div>
      <h1>Chat</h1>
      <p>选择一个对话开始，或创建新对话</p>
    </div>

    <template v-else>
      <div class="chat-header">
        <div class="chat-title-area">
          <h2 class="chat-title">{{ conversation.title || '新对话' }}</h2>
          <span class="model-badge">{{ conversation.model }}</span>
          <span v-if="conversation.thinking_enabled" class="thinking-badge">思考</span>
        </div>
        <div class="chat-actions">
          <button class="btn-icon" @click="$emit('toggleSettings')" title="设置">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </button>
        </div>
      </div>

      <div ref="scrollContainer" class="messages-container" @scroll="onScroll">
        <div v-if="hasMoreMessages" class="load-more-top">
          <button @click="$emit('loadMoreMessages')" :disabled="loadingMore">
            {{ loadingMore ? '加载中...' : '加载更早的消息' }}
          </button>
        </div>

        <div class="messages-list">
          <MessageBubble
            v-for="msg in messages"
            :key="msg.id"
            :role="msg.role"
            :text="msg.text"
            :thinking-content="msg.thinking"
            :tool-calls="msg.tool_calls"
            :process-steps="msg.process_steps"
            :token-count="msg.token_count"
            :created-at="msg.created_at"
            :deletable="msg.role === 'user'"
            :attachments="msg.attachments"
            @delete="$emit('deleteMessage', msg.id)"
            @regenerate="$emit('regenerateMessage', msg.id)"
          />

          <div v-if="streaming" class="message-bubble assistant streaming">
            <div class="avatar">claw</div>
            <div class="message-body">
              <ProcessBlock
                :thinking-content="streamingThinking"
                :tool-calls="streamingToolCalls"
                :process-steps="streamingProcessSteps"
                :streaming="streaming"
              />
              <div class="md-content streaming-content" v-html="renderedStreamContent || '<span class=\'placeholder\'>...</span>'"></div>
              <div class="streaming-indicator">
                <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
                <span>正在生成...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <MessageInput
        ref="inputRef"
        :disabled="streaming"
        :tools-enabled="toolsEnabled"
        @send="handleSend"
        @toggle-tools="$emit('toggleTools', $event)"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import MessageInput from './MessageInput.vue'
import ProcessBlock from './ProcessBlock.vue'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({
  conversation: { type: Object, default: null },
  messages: { type: Array, required: true },
  streaming: { type: Boolean, default: false },
  streamingContent: { type: String, default: '' },
  streamingThinking: { type: String, default: '' },
  streamingToolCalls: { type: Array, default: () => [] },
  streamingProcessSteps: { type: Array, default: () => [] },
  hasMoreMessages: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
  toolsEnabled: { type: Boolean, default: true },
})

const emit = defineEmits(['sendMessage', 'deleteMessage', 'regenerateMessage', 'toggleSettings', 'loadMoreMessages', 'toggleTools'])

const scrollContainer = ref(null)
const inputRef = ref(null)

const renderedStreamContent = computed(() => {
  if (!props.streamingContent) return ''
  return renderMarkdown(props.streamingContent)
})

function handleSend(data) {
  emit('sendMessage', data)
}

function scrollToBottom(smooth = true) {
  nextTick(() => {
    const el = scrollContainer.value
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'instant' })
    }
  })
}

function onScroll(e) {
  if (e.target.scrollTop < 50 && props.hasMoreMessages && !props.loadingMore) {
    // emit loadMore if needed
  }
}

watch(() => props.messages.length, () => {
  scrollToBottom()
})

watch(() => props.streamingContent, () => {
  scrollToBottom()
})

watch(() => props.conversation?.id, () => {
  if (props.conversation) {
    nextTick(() => inputRef.value?.focus())
  }
})

defineExpose({ scrollToBottom })
</script>

<style scoped>
.chat-view {
  flex: 1 1 auto;            /* 弹性宽度，自动填充剩余空间 */
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-secondary);
  min-width: 300px;          /* 最小宽度保证可用性 */
  overflow: hidden;
  transition: background 0.2s;
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
  background: none;
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
  background: var(--bg-primary);
  backdrop-filter: blur(8px);
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
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  flex-shrink: 0;
}

.thinking-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--success-bg);
  color: var(--success-color);
  flex-shrink: 0;
}

.chat-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: none;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-icon:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.messages-container {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 16px 0;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
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
  flex: 0 1 auto;           /* 弹性宽度 */
  width: 80%;
  margin: 0 auto;           /* 居中显示 */
  padding: 0 16px;          /* 左右内边距 */
}

.message-bubble {
  display: flex;
  gap: 12px;
  padding: 0;
  margin-bottom: 16px;
  width: 100%;
}

.message-bubble.assistant {
  width: 100%;
}

.message-bubble.assistant.streaming {
  width: 100%;
}

.message-bubble .message-container {
  display: flex;
  flex-direction: column;
  max-width: 85%;
  min-width: 200px;
}

.message-bubble.user .message-container {
  align-items: flex-end;
}

.message-bubble.assistant .message-container {
  align-items: flex-start;
}

.message-bubble .avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: -0.3px;
  flex-shrink: 0;
  background: var(--avatar-gradient);
  color: white;
}

.message-bubble .message-body {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  background: var(--bg-primary);
  transition: background 0.2s, border-color 0.2s;
}

.message-bubble.streaming .message-body {
  flex: 1;
}

.streaming-content {
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  font-size: 12px;
  color: var(--text-tertiary);
}

.streaming-content :deep(.placeholder) {
  color: var(--text-tertiary);
}

</style>

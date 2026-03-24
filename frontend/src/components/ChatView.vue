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
            :content="msg.content"
            :thinking-content="msg.thinking_content"
            :token-count="msg.token_count"
            :created-at="msg.created_at"
            :deletable="msg.role === 'user'"
            @delete="$emit('deleteMessage', msg.id)"
          />

          <div v-if="streaming" class="message-bubble assistant">
            <div class="avatar">claw</div>
            <div class="message-body">
              <div v-if="streamingThinking" class="thinking-content streaming-thinking">
                {{ streamingThinking }}
              </div>
              <div class="message-content streaming-content" v-html="renderedStreamContent || '<span class=\'placeholder\'>...</span>'"></div>
            </div>
          </div>
        </div>
      </div>

      <MessageInput
        ref="inputRef"
        :disabled="streaming"
        @send="$emit('sendMessage', $event)"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import MessageInput from './MessageInput.vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

const props = defineProps({
  conversation: { type: Object, default: null },
  messages: { type: Array, required: true },
  streaming: { type: Boolean, default: false },
  streamingContent: { type: String, default: '' },
  streamingThinking: { type: String, default: '' },
  hasMoreMessages: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
})

defineEmits(['sendMessage', 'deleteMessage', 'toggleSettings', 'loadMoreMessages'])

const scrollContainer = ref(null)
const inputRef = ref(null)

const renderedStreamContent = computed(() => {
  if (!props.streamingContent) return ''
  return marked.parse(props.streamingContent)
})

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
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f8fafc;
  min-width: 0;
}

.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
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
  color: #1e293b;
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
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
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
  color: #1e293b;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  flex-shrink: 0;
}

.thinking-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
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
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-icon:hover {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px;
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.08);
  border-radius: 3px;
}

.load-more-top {
  text-align: center;
  padding: 12px 0;
}

.load-more-top button {
  background: none;
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: #64748b;
  padding: 6px 16px;
  border-radius: 16px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}

.load-more-top button:hover {
  background: rgba(37, 99, 235, 0.06);
  color: #2563eb;
}

.messages-list {
  max-width: 800px;
  margin: 0 auto;
}

.streaming-thinking {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  white-space: pre-wrap;
  padding: 12px;
  background: #f1f5f9;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  margin-bottom: 8px;
}

.streaming-content {
  font-size: 15px;
  line-height: 1.7;
  color: #1e293b;
  word-break: break-word;
}

.streaming-content :deep(p) {
  margin: 0 0 8px;
}

.streaming-content :deep(p:last-child) {
  margin-bottom: 0;
}

.streaming-content :deep(pre) {
  background: #f1f5f9;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 8px 0;
}

.streaming-content :deep(pre code) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.streaming-content :deep(code) {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.streaming-content :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

.streaming-content :deep(ul),
.streaming-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.streaming-content :deep(blockquote) {
  border-left: 3px solid rgba(59, 130, 246, 0.4);
  padding-left: 12px;
  color: #64748b;
  margin: 8px 0;
}

.streaming-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}

.streaming-content :deep(th),
.streaming-content :deep(td) {
  border: 1px solid rgba(0, 0, 0, 0.08);
  padding: 8px 12px;
  text-align: left;
}

.streaming-content :deep(th) {
  background: #f1f5f9;
}

.streaming-content :deep(.placeholder) {
  color: #94a3b8;
}
</style>

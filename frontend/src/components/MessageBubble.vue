<template>
  <div class="message-bubble" :class="[role]">
    <div class="avatar">{{ role === 'user' ? 'U' : 'G' }}</div>
    <div class="message-body">
      <div v-if="thinkingContent" class="thinking-block">
        <button class="thinking-toggle" @click="showThinking = !showThinking">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
          </svg>
          <span>思考过程</span>
          <svg class="arrow" :class="{ open: showThinking }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        <div v-if="showThinking" class="thinking-content">{{ thinkingContent }}</div>
      </div>
      <div class="message-content" v-html="renderedContent"></div>
      <div class="message-footer">
        <span class="token-count" v-if="tokenCount">{{ tokenCount }} tokens</span>
        <span class="message-time">{{ formatTime(createdAt) }}</span>
        <button v-if="role === 'assistant'" class="btn-copy" @click="copyContent" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <button v-if="deletable" class="btn-delete-msg" @click="$emit('delete')" title="删除">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  thinkingContent: { type: String, default: '' },
  tokenCount: { type: Number, default: 0 },
  createdAt: { type: String, default: '' },
  deletable: { type: Boolean, default: false },
})

defineEmits(['delete'])

const showThinking = ref(false)

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

const renderedContent = computed(() => {
  if (!props.content) return ''
  return marked.parse(props.content)
})

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function copyContent() {
  navigator.clipboard.writeText(props.content).catch(() => {})
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  padding: 16px 0;
}

.message-bubble.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.user .avatar {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: white;
}

.assistant .avatar {
  background: linear-gradient(135deg, #0ea5e9, #06b6d4);
  color: white;
}

.message-body {
  max-width: 720px;
  min-width: 0;
}

.thinking-block {
  margin-bottom: 8px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.thinking-toggle {
  width: 100%;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: none;
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s;
}

.thinking-toggle:hover {
  background: rgba(255, 255, 255, 0.06);
}

.thinking-toggle .arrow {
  margin-left: auto;
  transition: transform 0.2s;
}

.thinking-toggle .arrow.open {
  transform: rotate(180deg);
}

.thinking-content {
  padding: 12px;
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.6;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

.message-content {
  font-size: 15px;
  line-height: 1.7;
  color: #e2e8f0;
  word-break: break-word;
}

.message-content :deep(p) {
  margin: 0 0 8px;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(pre) {
  background: #0d1117;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 8px 0;
  position: relative;
}

.message-content :deep(pre code) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.message-content :deep(code) {
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.message-content :deep(pre code) {
  background: none;
  padding: 0;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-content :deep(blockquote) {
  border-left: 3px solid rgba(59, 130, 246, 0.5);
  padding-left: 12px;
  color: #94a3b8;
  margin: 8px 0;
}

.message-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}

.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 8px 12px;
  text-align: left;
}

.message-content :deep(th) {
  background: rgba(255, 255, 255, 0.04);
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  opacity: 0;
  transition: opacity 0.15s;
}

.message-bubble:hover .message-footer {
  opacity: 1;
}

.token-count,
.message-time {
  font-size: 12px;
  color: #475569;
}

.btn-copy,
.btn-delete-msg {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.15s;
  display: flex;
  align-items: center;
}

.btn-copy:hover {
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.1);
}

.btn-delete-msg:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}
</style>

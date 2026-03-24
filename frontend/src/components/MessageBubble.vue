<template>
  <div class="message-bubble" :class="[role]">
    <div v-if="role === 'user'" class="avatar">user</div>
    <div v-else class="avatar">claw</div>
    <div class="message-body">
      <ProcessBlock
        v-if="thinkingContent || (toolCalls && toolCalls.length > 0)"
        :thinking-content="thinkingContent"
        :tool-calls="toolCalls"
      />
      <div v-if="role === 'tool'" class="tool-result-content">
        <div class="tool-badge">工具返回结果: {{ toolName }}</div>
        <pre>{{ content }}</pre>
      </div>
      <div v-else class="message-content" v-html="renderedContent"></div>
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
import { renderMarkdown } from '../utils/markdown'
import ProcessBlock from './ProcessBlock.vue'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  thinkingContent: { type: String, default: '' },
  toolCalls: { type: Array, default: () => [] },
  toolName: { type: String, default: '' },
  tokenCount: { type: Number, default: 0 },
  createdAt: { type: String, default: '' },
  deletable: { type: Boolean, default: false },
})

defineEmits(['delete'])

const renderedContent = computed(() => {
  if (!props.content) return ''
  return renderMarkdown(props.content)
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
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.user .avatar {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: white;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.assistant .avatar {
  background: var(--avatar-gradient);
  color: white;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-content {
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
}

.tool-result-content {
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 12px;
  overflow: hidden;
}

.tool-badge {
  font-size: 11px;
  color: var(--success-color);
  font-weight: 600;
  margin-bottom: 8px;
  padding: 2px 8px;
  background: var(--success-bg);
  border-radius: 4px;
  display: inline-block;
}

.tool-result-content pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-content :deep(p) {
  margin: 0 0 8px;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(pre) {
  background: var(--bg-code);
  border: 1px solid var(--border-light);
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
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.message-content :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-content :deep(blockquote) {
  border-left: 3px solid rgba(59, 130, 246, 0.4);
  padding-left: 12px;
  color: var(--text-secondary);
  margin: 8px 0;
}

.message-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}

.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid var(--border-medium);
  padding: 8px 12px;
  text-align: left;
}

.message-content :deep(th) {
  background: var(--bg-code);
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
  color: var(--text-tertiary);
}

.btn-copy,
.btn-delete-msg {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.15s;
  display: flex;
  align-items: center;
}

.btn-copy:hover {
  color: var(--accent-primary);
  background: var(--accent-primary-light);
}

.btn-delete-msg:hover {
  color: var(--danger-color);
  background: var(--danger-bg);
}

.message-content :deep(.math-block) {
  display: block;
  text-align: center;
  padding: 12px 0;
  margin: 8px 0;
  overflow-x: auto;
}
</style>

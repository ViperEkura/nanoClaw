<template>
  <div class="message-bubble" :class="[role]">
    <div v-if="role === 'user'" class="avatar">user</div>
    <div v-else class="avatar">claw</div>
    <div class="message-container">
      <!-- File attachments list -->
      <div v-if="attachments && attachments.length > 0" class="attachments-list">
        <div v-for="(file, index) in attachments" :key="index" class="attachment-item">
          <span class="attachment-icon">{{ file.extension }}</span>
          <span class="attachment-name">{{ file.name }}</span>
        </div>
      </div>
      <div ref="messageRef" class="message-body">
        <!-- Primary rendering path: processSteps contains all ordered steps -->
        <!-- (thinking, text, tool_call, tool_result) from both streaming and DB load -->
        <ProcessBlock
          v-if="processSteps && processSteps.length > 0"
          :process-steps="processSteps"
        />
        <!-- Fallback path: old messages without processSteps in DB, -->
        <!-- render toolCalls via ProcessBlock and text separately -->
        <template v-else>
          <ProcessBlock
            v-if="toolCalls && toolCalls.length > 0"
            :tool-calls="toolCalls"
          />
          <div class="md-content message-content" v-html="renderedContent"></div>
        </template>
      </div>
      <div class="message-footer">
        <span class="token-count" v-if="tokenCount">{{ tokenCount }} tokens</span>
        <span class="message-time">{{ formatTime(createdAt) }}</span>
        <button v-if="role === 'assistant'" class="btn-regenerate" @click="$emit('regenerate')" title="重新生成">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 4v6h6"/>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
        </button>
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
import { computed, ref } from 'vue'
import { renderMarkdown } from '../utils/markdown'
import { formatTime } from '../utils/format'
import { useCodeEnhancement } from '../composables/useCodeEnhancement'
import ProcessBlock from './ProcessBlock.vue'

const props = defineProps({
  role: { type: String, required: true },           // 'user' or 'assistant'
  text: { type: String, default: '' },               // Plain text content (legacy / user messages)
  toolCalls: { type: Array, default: () => [] },     // Tool calls array (legacy fallback)
  // Ordered steps array — primary rendering data source.
  // During streaming: accumulated from process_step SSE events.
  // On page load: loaded from DB via message_to_dict extracting 'steps' field.
  // Each step: { id, index, type: 'thinking'|'text'|'tool_call'|'tool_result', content, ... }
  processSteps: { type: Array, default: () => [] },
  tokenCount: { type: Number, default: 0 },
  createdAt: { type: String, default: '' },
  deletable: { type: Boolean, default: false },
  attachments: { type: Array, default: () => [] },   // User file attachments
})

defineEmits(['delete', 'regenerate'])

const messageRef = ref(null)

const renderedContent = computed(() => {
  if (!props.text) return ''
  return renderMarkdown(props.text)
})

useCodeEnhancement(messageRef, renderedContent)

function copyContent() {
  // Extract text from processSteps (preferred) or fall back to text prop
  let text = props.text || ''
  if (props.processSteps && props.processSteps.length > 0) {
    const parts = props.processSteps
      .filter(s => s && s.type === 'text')
      .map(s => s.content)
    if (parts.length > 0) text = parts.join('\n\n')
  }
  navigator.clipboard.writeText(text).catch(() => {})
}
</script>

<style scoped>
.attachments-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
  width: 100%;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.attachment-icon {
  background: var(--attachment-bg);
  color: var(--attachment-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.attachment-name {
  color: var(--text-primary);
  font-weight: 500;
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0 0;
  font-size: 12px;
}

.token-count,
.message-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.btn-regenerate,
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

.btn-regenerate:hover {
  color: var(--success-color);
  background: var(--success-bg);
}

.btn-copy:hover {
  color: var(--accent-primary);
  background: var(--accent-primary-light);
}

.btn-delete-msg:hover {
  color: var(--danger-color);
  background: var(--danger-bg);
}
</style>

<template>
  <div class="message-bubble" :class="[role]">
    <div v-if="role === 'user'" class="avatar">user</div>
    <div v-else class="avatar">claw</div>
    <div class="message-container">
      <!-- 附件列表 -->
      <div v-if="attachments && attachments.length > 0" class="attachments-list">
        <div v-for="(file, index) in attachments" :key="index" class="attachment-item">
          <span class="attachment-icon">{{ file.extension }}</span>
          <span class="attachment-name">{{ file.name }}</span>
        </div>
      </div>
      <div ref="messageRef" class="message-body">
        <!-- 新格式: processSteps 包含所有步骤（含 text），统一通过 ProcessBlock 渲染 -->
        <ProcessBlock
          v-if="processSteps && processSteps.length > 0"
          :process-steps="processSteps"
          :thinking-content="thinkingContent"
          :tool-calls="toolCalls"
        />
        <!-- 旧格式: 无 processSteps，分开渲染 ProcessBlock + 文本 -->
        <template v-else>
          <ProcessBlock
            v-if="thinkingContent || (toolCalls && toolCalls.length > 0)"
            :thinking-content="thinkingContent"
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
import { computed, watch, onMounted, ref } from 'vue'
import { renderMarkdown, enhanceCodeBlocks } from '../utils/markdown'
import ProcessBlock from './ProcessBlock.vue'

const props = defineProps({
  role: { type: String, required: true },
  text: { type: String, default: '' },
  thinkingContent: { type: String, default: '' },
  toolCalls: { type: Array, default: () => [] },
  processSteps: { type: Array, default: () => [] },
  tokenCount: { type: Number, default: 0 },
  createdAt: { type: String, default: '' },
  deletable: { type: Boolean, default: false },
  attachments: { type: Array, default: () => [] },
})

defineEmits(['delete', 'regenerate'])

const messageRef = ref(null)

const renderedContent = computed(() => {
  if (!props.text) return ''
  return renderMarkdown(props.text)
})

function enhanceCode() {
  enhanceCodeBlocks(messageRef.value)
}

watch(renderedContent, () => {
  enhanceCode()
})

onMounted(() => {
  enhanceCode()
})

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function copyContent() {
  navigator.clipboard.writeText(props.text || '').catch(() => {})
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  width: 100%;
}

.message-bubble.user {
  flex-direction: row-reverse;
}

.message-container {
  display: flex;
  flex-direction: column;
  min-width: 200px;
  width: 100%;
}

.message-bubble.user .message-container {
  align-items: flex-end;
  width: fit-content;
  max-width: 85%;
}

.message-bubble.assistant .message-container {
  align-items: flex-start;
  flex: 1 1 auto;
  min-width: 0;
}

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
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.attachment-name {
  color: var(--text-primary);
  font-weight: 500;
}

.message-bubble.assistant .message-body {
  width: 100%;
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
  font-size: 12px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.assistant .avatar {
  background: var(--avatar-gradient);
  color: white;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.message-body {
  flex: 1;
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  background: var(--bg-primary);
  transition: background 0.2s, border-color 0.2s;
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

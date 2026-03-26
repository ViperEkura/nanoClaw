<template>
  <div ref="processRef" class="process-block" :class="{ 'is-streaming': streaming }">
    <!-- 流式加载：还没有任何步骤时 -->
    <div v-if="streaming && processItems.length === 0" class="streaming-placeholder">
      <div class="streaming-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
      </div>
      <span class="streaming-text">正在思考中<span class="dots">...</span></span>
    </div>

    <!-- 按序渲染步骤 -->
    <template v-else>
      <template v-for="item in processItems" :key="item.key">
        <!-- 思考过程 -->
        <div v-if="item.type === 'thinking'" class="step-item thinking">
          <div class="step-header" @click="toggleItem(item.key)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
            <span class="step-label">思考过程</span>
            <span v-if="item.summary" class="step-brief">{{ item.summary }}</span>
            <svg class="arrow" :class="{ open: expandedKeys[item.key] }" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div v-if="expandedKeys[item.key]" class="step-content">
            <div class="thinking-text">{{ item.content }}</div>
          </div>
        </div>

        <!-- 工具调用 -->
        <div v-else-if="item.type === 'tool_call'" class="step-item tool_call" :class="{ loading: item.loading }">
          <div class="step-header" @click="toggleItem(item.key)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
            <span class="step-label">{{ item.loading ? `执行工具: ${item.toolName}` : `调用工具: ${item.toolName}` }}</span>
            <span v-if="item.summary && !item.loading" class="step-brief">{{ item.summary }}</span>
            <span v-if="item.resultSummary" class="step-badge" :class="{ success: item.isSuccess, error: !item.isSuccess }">{{ item.resultSummary }}</span>
            <span v-if="item.loading" class="loading-dots">...</span>
            <svg v-if="!item.loading" class="arrow" :class="{ open: expandedKeys[item.key] }" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div v-if="expandedKeys[item.key] && !item.loading" class="step-content">
            <div class="tool-detail" style="margin-bottom: 8px;">
              <span class="detail-label">调用参数:</span>
              <pre>{{ item.arguments }}</pre>
            </div>
            <div v-if="item.result" class="tool-detail">
              <span class="detail-label">返回结果:</span>
              <pre>{{ item.result }}</pre>
            </div>
          </div>
        </div>

        <!-- 文本内容 - 直接渲染 markdown -->
        <div v-else-if="item.type === 'text'" class="step-item text-content md-content" v-html="item.rendered"></div>
      </template>

      <!-- 流式进行中指示器 -->
      <div v-if="streaming" class="streaming-indicator">
        <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>正在生成...</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { renderMarkdown, enhanceCodeBlocks } from '../utils/markdown'

const props = defineProps({
  thinkingContent: { type: String, default: '' },
  toolCalls: { type: Array, default: () => [] },
  processSteps: { type: Array, default: () => [] },
  streamingContent: { type: String, default: '' },
  streaming: { type: Boolean, default: false }
})

const expandedKeys = ref({})

// 流式时自动展开
watch(() => props.streaming, (v) => {
  if (v) expandedKeys.value = {}
})

// 增强 processBlock 内代码块
const processRef = ref(null)

function enhanceCode() {
  enhanceCodeBlocks(processRef.value)
}

onMounted(() => {
  enhanceCode()
})

function toggleItem(key) {
  expandedKeys.value[key] = !expandedKeys.value[key]
}

function formatJson(value) {
  if (value == null) return ''
  const str = typeof value === 'string' ? value : JSON.stringify(value)
  try { return JSON.stringify(JSON.parse(str), null, 2) } catch { return str }
}

function truncate(text, max = 60) {
  if (!text) return ''
  const str = text.replace(/\s+/g, ' ').trim()
  return str.length > max ? str.slice(0, max) + '…' : str
}

function getResultSummary(result) {
  try {
    const parsed = typeof result === 'string' ? JSON.parse(result) : result
    if (parsed.success === true) return { text: '成功', success: true }
    if (parsed.success === false || parsed.error) return { text: parsed.error || '失败', success: false }
    if (parsed.results) return { text: `${parsed.results.length} 条结果`, success: true }
    return { text: '完成', success: true }
  } catch {
    return { text: '完成', success: true }
  }
}

const processItems = computed(() => {
  const items = []

  // 优先使用 processSteps（按顺序）
  if (props.processSteps && props.processSteps.length > 0) {
    for (const step of props.processSteps) {
      if (!step) continue

      if (step.type === 'thinking') {
        items.push({ type: 'thinking', content: step.content, summary: truncate(step.content), key: `thinking-${step.index}` })
      } else if (step.type === 'tool_call') {
        items.push({
          type: 'tool_call',
          toolName: step.name || '未知工具',
          arguments: formatJson(step.arguments),
          summary: truncate(step.arguments),
          id: step.id,
          key: `tool_call-${step.id || step.index}`,
          loading: false,
          result: null,
        })
      } else if (step.type === 'tool_result') {
        const summary = getResultSummary(step.content)
        const match = items.findLast(it => it.type === 'tool_call' && it.id === step.id)
        if (match) {
          match.result = formatJson(step.content)
          match.resultSummary = summary.text
          match.isSuccess = summary.success
          match.loading = false
        }
      } else if (step.type === 'text') {
        items.push({
          type: 'text',
          content: step.content,
          rendered: renderMarkdown(step.content),
          key: `text-${step.index}`,
        })
      }
    }

    // 流式中最后一个 tool_call 标记为 loading
    if (props.streaming && items.length > 0) {
      const last = items[items.length - 1]
      if (last.type === 'tool_call') {
        last.loading = true
      }
    }

    // 流式中追加正在增长的文本（仅当最后步骤不是 text 类型时）
    if (props.streaming && props.streamingContent) {
      const lastStep = items[items.length - 1]
      if (!lastStep || lastStep.type !== 'text') {
        items.push({
          type: 'text',
          content: props.streamingContent,
          rendered: renderMarkdown(props.streamingContent) || '<span class="placeholder">...</span>',
          key: 'text-streaming',
        })
      }
    }
  } else {
    // 回退逻辑：旧版 thinking + toolCalls
    if (props.thinkingContent) {
      items.push({ type: 'thinking', content: props.thinkingContent, summary: truncate(props.thinkingContent), key: 'thinking-0' })
    } else if (props.streaming && items.length === 0) {
      items.push({ type: 'thinking', content: '', key: 'thinking-loading' })
    }

    if (props.toolCalls && props.toolCalls.length > 0) {
      props.toolCalls.forEach((call, i) => {
        const toolName = call.function?.name || '未知工具'
        const result = call.result ? getResultSummary(call.result) : null
        items.push({
          type: 'tool_call',
          toolName,
          arguments: formatJson(call.function?.arguments),
          summary: truncate(call.function?.arguments),
          id: call.id,
          key: `tool_call-${call.id || i}`,
          loading: !call.result && props.streaming,
          result: call.result ? formatJson(call.result) : null,
          resultSummary: result ? result.text : null,
          isSuccess: result ? result.success : undefined,
        })
      })
    }

    // 旧模式下追加流式文本
    if (props.streaming && props.streamingContent) {
      items.push({
        type: 'text',
        content: props.streamingContent,
        rendered: renderMarkdown(props.streamingContent) || '<span class="placeholder">...</span>',
        key: 'text-streaming',
      })
    }
  }

  return items
})

watch(processItems, () => {
  nextTick(() => enhanceCode())
}, { deep: true })
</script>

<style scoped>
.process-block {
  width: 100%;
}

/* 流式占位 */
.streaming-placeholder {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-hover);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.streaming-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: #fef3c7;
  color: #f59e0b;
  display: flex;
  align-items: center;
  justify-content: center;
}

.streaming-text {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.streaming-text .dots {
  display: inline-block;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

/* 步骤通用 */
.step-item {
  margin-bottom: 8px;
}

.step-item:last-child {
  margin-bottom: 0;
}

/* 思考过程 */
.thinking .step-header,
.tool_call .step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}

.thinking .step-header:hover,
.tool_call .step-header:hover {
  background: var(--bg-hover);
}

.thinking .step-header svg:first-child {
  color: #f59e0b;
}

.tool_call .step-header svg:first-child {
  color: #a855f7;
}

.step-label {
  font-weight: 500;
  color: var(--text-primary);
  flex-shrink: 0;
  min-width: 130px;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  margin-left: auto;
  transition: transform 0.2s;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.step-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.step-badge.success {
  background: var(--success-bg);
  color: var(--success-color);
}

.step-badge.error {
  background: var(--danger-bg);
  color: var(--danger-color);
}

.step-brief {
  font-size: 11px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}


.arrow.open {
  transform: rotate(180deg);
}

.loading-dots {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent-primary);
  animation: pulse 1s ease-in-out infinite;
}

.tool_call.loading .step-header {
  background: var(--bg-hover);
}

/* 步骤展开内容 */
.step-content {
  padding: 12px;
  margin-top: 4px;
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}

.thinking-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.tool-detail {
  font-size: 13px;
}

.detail-label {
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}

.tool-detail pre {
  padding: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  border: 1px solid var(--border-light);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 文本内容直接渲染 */
.text-content {
  padding: 0;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
}

.text-content :deep(.placeholder) {
  color: var(--text-tertiary);
}

/* 流式指示器 */
.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 0 0;
  border-top: 1px solid var(--border-light);
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>

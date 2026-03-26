<template>
  <div ref="processRef" class="process-block" :class="{ 'is-streaming': streaming }">
    <!-- Render all steps in order: thinking, text, tool_call, tool_result interleaved -->
    <template v-if="processItems.length > 0">
      <template v-for="item in processItems" :key="item.key">
        <!-- Thinking block -->
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

        <!-- Tool call block -->
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

        <!-- Text content — render as markdown -->
        <div v-else-if="item.type === 'text'" class="step-item text-content md-content" v-html="item.rendered"></div>
      </template>

    </template>

    <!-- Active streaming indicator — always visible during streaming, even before any content arrives -->
    <div v-if="streaming" class="streaming-indicator">
      <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
      </svg>
      <span>正在生成...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { renderMarkdown } from '../utils/markdown'
import { formatJson, truncate } from '../utils/format'
import { useCodeEnhancement } from '../composables/useCodeEnhancement'

const props = defineProps({
  toolCalls: { type: Array, default: () => [] },
  processSteps: { type: Array, default: () => [] },
  streamingContent: { type: String, default: '' },
  streaming: { type: Boolean, default: false }
})

const expandedKeys = ref({})

// Auto-collapse all items when a new stream starts
watch(() => props.streaming, (v) => {
  if (v) expandedKeys.value = {}
})

const processRef = ref(null)

function toggleItem(key) {
  expandedKeys.value[key] = !expandedKeys.value[key]
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

// Build ordered process items from all available data (thinking, tool calls, text).
// During streaming, processSteps accumulate completed iterations while streamingContent
// represents the text being generated in the current (latest) iteration.
// When loaded from DB, steps use 'id_ref' for tool_call/tool_result matching;
// during streaming they use 'id'. Both fields are normalized here.
const processItems = computed(() => {
  const items = []

  // Build items from processSteps — finalized steps sent by backend or loaded from DB.
  // Steps are ordered: each iteration produces thinking → text → tool_call → tool_result.
  if (props.processSteps && props.processSteps.length > 0) {
    for (const step of props.processSteps) {
      if (!step) continue

      if (step.type === 'thinking') {
        items.push({
          type: 'thinking',
          content: step.content,
          summary: truncate(step.content),
          key: step.id || `thinking-${step.index}`,
        })
      } else if (step.type === 'tool_call') {
        // Normalize: DB-loaded steps use 'id_ref', streaming steps use 'id'
        const toolId = step.id_ref || step.id
        items.push({
          type: 'tool_call',
          toolName: step.name || '未知工具',
          arguments: formatJson(step.arguments),
          summary: truncate(step.arguments),
          id: toolId,
          key: step.id || `tool_call-${toolId || step.index}`,
          loading: false,
          result: null,
        })
      } else if (step.type === 'tool_result') {
        // Merge result back into its corresponding tool_call item by matching tool ID
        const toolId = step.id_ref || step.id
        const summary = getResultSummary(step.content)
        const match = items.findLast(it => it.type === 'tool_call' && it.id === toolId)
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
          key: step.id || `text-${step.index}`,
        })
      }
    }

    // Mark the last tool_call as loading if it has no result yet (still executing)
    if (props.streaming && items.length > 0) {
      const last = items[items.length - 1]
      if (last.type === 'tool_call' && !last.result) {
        last.loading = true
      }
    }

    // Append the currently streaming text as a live text item.
    // This text belongs to the latest LLM iteration that hasn't finished yet.
    if (props.streaming && props.streamingContent) {
      items.push({
        type: 'text',
        content: props.streamingContent,
        rendered: renderMarkdown(props.streamingContent) || '<span class="placeholder">...</span>',
        key: 'text-streaming',
      })
    }
  } else {
    // Fallback: legacy mode for old messages without processSteps stored in DB
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

    // Append streaming text in legacy mode
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

// Enhance code blocks inside process items (syntax highlighting, copy buttons)
const { debouncedEnhance } = useCodeEnhancement(processRef, processItems, { deep: true })

// Throttle code enhancement during streaming to reduce DOM operations
watch(() => props.streamingContent?.length, () => {
  if (props.streaming) debouncedEnhance()
})
</script>

<style scoped>
.process-block {
  width: 100%;
}

/* Step items (shared) */
.step-item {
  margin-bottom: 8px;
}

.step-item:last-child {
  margin-bottom: 0;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

/* Step header (shared by thinking and tool_call) */
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
  color: var(--tool-color);
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
  color: var(--tool-color);
  animation: pulse 1s ease-in-out infinite;
}

.tool_call.loading .step-header {
  background: var(--bg-hover);
}

/* Expandable step content panel */
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

/* Text content — rendered as markdown */
.text-content {
  padding: 0;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
  contain: layout style;
}

.text-content :deep(.placeholder) {
  color: var(--text-tertiary);
}

/* Streaming cursor indicator */
.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

/* Add separator only when there are step items above the indicator */
.process-block:has(.step-item) .streaming-indicator {
  margin-top: 8px;
  padding: 8px 0 0;
  border-top: 1px solid var(--border-light);
}
</style>

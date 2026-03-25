<template>
  <div class="process-block" :class="{ 'is-streaming': streaming }">
    <!-- 流式加载状态 -->
    <div v-if="streaming && processItems.length === 0" class="streaming-placeholder">
      <div class="streaming-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
      </div>
      <span class="streaming-text">正在思考中<span class="dots">...</span></span>
    </div>

    <!-- 正常内容 -->
    <template v-else>
      <button class="process-toggle" @click="toggleAll">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        <span>思考与工具调用过程</span>
        <span class="process-count">{{ processItems.length }} 步</span>
        <svg class="arrow" :class="{ open: allExpanded }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>

    <div v-if="allExpanded" class="process-list">
      <div v-for="item in processItems" :key="item.key" class="process-item" :class="[item.type, { loading: item.loading }]">
        <div class="process-header" @click="toggleItem(item.index)">
          <div class="process-icon">
            <svg v-if="item.type === 'thinking'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
            <svg v-else-if="item.type === 'tool_call'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
            <svg v-else-if="item.type === 'tool_result'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 11 12 14 22 4"/>
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
            </svg>
          </div>
          <span class="process-label">{{ item.label }}</span>
          <span v-if="item.loading" class="loading-dots">...</span>
          <span v-else-if="item.type === 'tool_result'" class="process-summary" :class="{ success: item.isSuccess, error: !item.isSuccess }">{{ item.summary }}</span>
          <span class="process-time">{{ item.time }}</span>
          <svg v-if="!item.loading" class="item-arrow" :class="{ open: isItemExpanded(item.index) }" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>

        <div v-if="isItemExpanded(item.index) && !item.loading" class="process-content">
          <div v-if="item.type === 'thinking'" class="thinking-text">{{ item.content }}</div>

          <div v-else-if="item.type === 'tool_call'" class="tool-call-detail">
            <div class="tool-name">
              <span class="label">工具名称:</span>
              <span class="value">{{ item.toolName }}</span>
            </div>
            <div v-if="item.arguments" class="tool-args">
              <span class="label">调用参数:</span>
              <pre>{{ item.arguments }}</pre>
            </div>
          </div>

          <div v-else-if="item.type === 'tool_result'" class="tool-result-detail">
            <div class="result-label">返回结果:</div>
            <pre>{{ item.content }}</pre>
          </div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  thinkingContent: { type: String, default: '' },
  toolCalls: { type: Array, default: () => [] },
  processSteps: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false }
})

const allExpanded = ref(false)
const itemExpanded = ref({}) // 存储每个项目的展开状态

const processItems = computed(() => {
  const items = []
  let idx = 0

  // 优先使用新的 processSteps（按顺序的步骤列表）
  if (props.processSteps && props.processSteps.length > 0) {
    props.processSteps.forEach((step, stepIdx) => {
      if (!step) return

      if (step.type === 'thinking') {
        items.push({
          type: 'thinking',
          label: '思考过程',
          content: step.content,
          time: '',
          index: idx,
          key: `thinking-${idx}`,
          loading: false
        })
        idx++
      } else if (step.type === 'tool_call') {
        items.push({
          type: 'tool_call',
          label: `调用工具: ${step.name || '未知工具'}`,
          toolName: step.name || '未知工具',
          arguments: formatArgs(step.arguments),
          id: step.id,
          index: idx,
          key: `tool_call-${step.id || idx}`,
          loading: false
        })
        idx++
      } else if (step.type === 'tool_result') {
        const resultSummary = getResultSummary(step.content)
        items.push({
          type: 'tool_result',
          label: `工具返回: ${step.name || '未知工具'}`,
          content: formatResult(step.content),
          summary: resultSummary.text,
          isSuccess: resultSummary.success,
          id: step.id,
          index: idx,
          key: `tool_result-${step.id || idx}`,
          loading: false
        })
        idx++
      }
    })

    // 如果正在流式传输，检查是否需要添加加载状态
    if (props.streaming && items.length > 0) {
      const lastItem = items[items.length - 1]
      // 最后一个工具调用还没有结果，显示执行中
      if (lastItem.type === 'tool_call') {
        lastItem.loading = true
        lastItem.label = `执行工具: ${lastItem.toolName}`
      }
    }

    return items
  }

  // 回退到旧逻辑：先添加思考过程，再添加工具调用
  if (props.thinkingContent) {
    items.push({
      type: 'thinking',
      label: '思考过程',
      content: props.thinkingContent,
      time: '',
      index: idx,
      key: `thinking-${idx}`,
      loading: false
    })
    idx++
  } else if (props.streaming && items.length === 0) {
    // 正在思考中
    items.push({
      type: 'thinking',
      label: '思考中',
      content: '',
      time: '',
      index: idx,
      key: `thinking-loading`,
      loading: true
    })
    idx++
  }

  if (props.toolCalls && props.toolCalls.length > 0) {
    props.toolCalls.forEach((call, i) => {
      items.push({
        type: 'tool_call',
        label: `调用工具: ${call.function?.name || '未知工具'}`,
        toolName: call.function?.name || '未知工具',
        arguments: formatArgs(call.function?.arguments),
        id: call.id,
        index: idx,
        key: `tool_call-${call.id || idx}`,
        loading: false
      })
      idx++

      if (call.result) {
        const resultSummary = getResultSummary(call.result)
        items.push({
          type: 'tool_result',
          label: `工具返回: ${call.function?.name || '未知工具'}`,
          content: formatResult(call.result),
          summary: resultSummary.text,
          isSuccess: resultSummary.success,
          id: call.id,
          index: idx,
          key: `tool_result-${call.id || idx}`,
          loading: false
        })
        idx++
      } else if (props.streaming) {
        // 工具正在执行中
        items[items.length - 1].loading = true
        items[items.length - 1].label = `执行工具: ${call.function?.name || '未知工具'}`
      }
    })
  }

  return items
})

function isItemExpanded(index) {
  return itemExpanded.value[index] || false
}

function toggleItem(index) {
  itemExpanded.value[index] = !isItemExpanded(index)
}

function formatArgs(args) {
  if (!args) return ''
  try {
    const parsed = JSON.parse(args)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return args
  }
}

function formatResult(result) {
  if (typeof result === 'string') {
    try {
      const parsed = JSON.parse(result)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return result
    }
  }
  return JSON.stringify(result, null, 2)
}

function getResultSummary(result) {
  try {
    const parsed = typeof result === 'string' ? JSON.parse(result) : result
    if (parsed.success === true) {
      return { text: '成功', success: true }
    } else if (parsed.success === false || parsed.error) {
      return { text: parsed.error || '失败', success: false }
    } else if (parsed.results) {
      return { text: `${parsed.results.length} 条结果`, success: true }
    }
    return { text: '完成', success: true }
  } catch {
    return { text: '完成', success: true }
  }
}

function toggleAll() {
  allExpanded.value = !allExpanded.value
}

// 自动展开流式内容（只展开外层面板，不展开内部项目）
watch(() => props.streaming, (streaming) => {
  if (streaming) {
    allExpanded.value = true
  }
})
</script>

<style scoped>
.process-block {
  margin-bottom: 8px;
  border-radius: 8px;
  border: 1px solid var(--border-light);
  overflow: hidden;
  background: var(--bg-secondary);
  max-width: 100%;
}

.streaming-placeholder {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-hover);
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

.process-toggle {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s;
}

.process-toggle:hover {
  background: var(--bg-code);
}

.process-count {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  background: var(--accent-primary-light);
  color: var(--accent-primary);
  border-radius: 10px;
}

.arrow {
  margin-left: 8px;
  transition: transform 0.2s;
}

.arrow.open {
  transform: rotate(180deg);
}

.process-list {
  border-top: 1px solid var(--border-light);
}

.process-item {
  border-bottom: 1px solid var(--border-light);
}

.process-item:last-child {
  border-bottom: none;
}

.process-header {
  padding: 8px 12px;
  background: var(--bg-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s;
  font-size: 13px;
}

.process-header:hover {
  background: var(--bg-hover);
}

.process-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thinking .process-icon {
  background: #fef3c7;
  color: #f59e0b;
}

.tool_call .process-icon {
  background: #f3e8ff;
  color: #a855f7;
}

.tool_result .process-icon {
  background: var(--success-bg);
  color: var(--success-color);
}

.process-label {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
}

.process-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.process-summary {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.process-summary.success {
  background: var(--success-bg);
  color: var(--success-color);
}

.process-summary.error {
  background: var(--danger-bg);
  color: var(--danger-color);
}

.item-arrow {
  transition: transform 0.2s;
}

.item-arrow.open {
  transform: rotate(180deg);
}

.loading-dots {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent-primary);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.process-item.loading .process-header {
  background: var(--bg-hover);
}

.process-content {
  padding: 12px;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-light);
  overflow: hidden;
}

.thinking-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.tool-call-detail,
.tool-result-detail {
  font-size: 13px;
}

.tool-name,
.tool-args {
  margin-bottom: 8px;
}

.tool-name:last-child,
.tool-args:last-child {
  margin-bottom: 0;
}

.label {
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 600;
  margin-right: 8px;
}

.value {
  color: var(--accent-primary);
  font-weight: 500;
}

.tool-args pre,
.tool-result-detail pre {
  margin-top: 4px;
  padding: 8px;
  background: var(--bg-code);
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  overflow-x: auto;
  border: 1px solid var(--border-light);
  white-space: pre-wrap;
  word-break: break-word;
}

.result-label {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 600;
  margin-bottom: 4px;
}
</style>

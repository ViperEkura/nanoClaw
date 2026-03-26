<template>
  <div class="stats-panel">
    <div class="stats-header">
      <div class="stats-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 20V10"/>
          <path d="M12 20V4"/>
          <path d="M6 20v-6"/>
        </svg>
        <h4>使用统计</h4>
      </div>
      <div class="header-actions">
        <div class="period-tabs">
          <button
            v-for="p in periods"
            :key="p.value"
            :class="['tab', { active: period === p.value }]"
            @click="changePeriod(p.value)"
          >
            {{ p.label }}
          </button>
        </div>
        <CloseButton @click="$emit('close')" />
      </div>
    </div>

    <div v-if="loading" class="stats-loading">
      <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
      </svg>
      加载中...
    </div>

    <template v-else-if="stats">
      <!-- 统计卡片 -->
      <div class="stats-summary">
        <div class="stat-card">
          <div class="stat-icon input-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.375 2.625a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z"/>
            </svg>
          </div>
          <div class="stat-info">
            <span class="stat-label">输入</span>
            <span class="stat-value">{{ formatNumber(stats.prompt_tokens) }}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon output-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <div class="stat-info">
            <span class="stat-label">输出</span>
            <span class="stat-value">{{ formatNumber(stats.completion_tokens) }}</span>
          </div>
        </div>
        <div class="stat-card total">
          <div class="stat-icon total-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div class="stat-info">
            <span class="stat-label">总计</span>
            <span class="stat-value">{{ formatNumber(stats.total_tokens) }}</span>
          </div>
        </div>
      </div>

      <!-- 趋势图 -->
      <div v-if="period !== 'daily' && stats.daily && chartData.length > 0" class="stats-chart">
        <div class="chart-title">每日趋势</div>
        <div class="chart-container">
          <svg class="line-chart" :viewBox="`0 0 ${chartWidth} ${chartHeight}`">
            <defs>
              <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" :stop-color="accentColor" stop-opacity="0.25"/>
                <stop offset="100%" :stop-color="accentColor" stop-opacity="0.02"/>
              </linearGradient>
            </defs>
            <!-- 网格线 -->
            <line
              v-for="i in 4"
              :key="'grid-' + i"
              :x1="padding"
              :y1="padding + (chartHeight - 2 * padding) * (i - 1) / 3"
              :x2="chartWidth - padding"
              :y2="padding + (chartHeight - 2 * padding) * (i - 1) / 3"
              stroke="var(--border-light)"
              stroke-dasharray="3,3"
            />
            <!-- Y轴标签 -->
            <text
              v-for="i in 4"
              :key="'yl-' + i"
              :x="padding - 4"
              :y="padding + (chartHeight - 2 * padding) * (i - 1) / 3 + 3"
              text-anchor="end"
              class="y-label"
            >{{ formatNumber(maxValue - (maxValue * (i - 1)) / 3) }}</text>
            <!-- 填充区域 -->
            <path :d="areaPath" fill="url(#areaGradient)"/>
            <!-- 折线 -->
            <path
              :d="linePath"
              fill="none"
              :stroke="accentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <!-- 数据点 -->
            <circle
              v-for="(point, idx) in chartPoints"
              :key="idx"
              :cx="point.x"
              :cy="point.y"
              r="3"
              :fill="accentColor"
              stroke="var(--bg-primary)"
              stroke-width="2"
              class="data-point"
              @mouseenter="hoveredPoint = idx"
              @mouseleave="hoveredPoint = null"
            />
            <!-- 竖线指示 -->
            <line
              v-if="hoveredPoint !== null && chartPoints[hoveredPoint]"
              :x1="chartPoints[hoveredPoint].x"
              :y1="padding"
              :x2="chartPoints[hoveredPoint].x"
              :y2="chartHeight - padding"
              stroke="var(--border-medium)"
              stroke-dasharray="3,3"
            />
          </svg>

          <!-- X轴标签 -->
          <div class="x-labels">
            <span
              v-for="(point, idx) in chartPoints"
              :key="idx"
              class="x-label"
              :class="{ active: hoveredPoint === idx }"
            >
              {{ formatDateLabel(point.date) }}
            </span>
          </div>

          <!-- 悬浮提示 -->
          <Transition name="fade">
            <div
              v-if="hoveredPoint !== null && chartPoints[hoveredPoint]"
              class="tooltip"
              :style="{
                left: chartPoints[hoveredPoint].x + 'px',
                top: (chartPoints[hoveredPoint].y - 52) + 'px'
              }"
            >
              <div class="tooltip-date">{{ formatFullDate(chartPoints[hoveredPoint].date) }}</div>
              <div class="tooltip-row">
                <span class="tooltip-dot prompt"></span>
                输入 {{ formatNumber(chartPoints[hoveredPoint].prompt) }}
              </div>
              <div class="tooltip-row">
                <span class="tooltip-dot completion"></span>
                输出 {{ formatNumber(chartPoints[hoveredPoint].completion) }}
              </div>
              <div class="tooltip-total">{{ formatNumber(chartPoints[hoveredPoint].value) }} tokens</div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- 按模型分布 -->
      <div v-if="stats.by_model" class="stats-by-model">
        <div class="model-title">模型分布</div>
        <div class="model-list">
          <div
            v-for="(data, model) in stats.by_model"
            :key="model"
            class="model-row"
          >
            <div class="model-info">
              <span class="model-name">{{ model }}</span>
              <span class="model-value">{{ formatNumber(data.total) }} <span class="model-unit">tokens</span></span>
            </div>
            <div class="model-bar-bg">
              <div
                class="model-bar-fill"
                :style="{ width: (data.total / maxModelTokens * 100) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!stats.total_tokens" class="stats-empty">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M18 20V10"/>
          <path d="M12 20V4"/>
          <path d="M6 20v-6"/>
        </svg>
        <span>暂无使用数据</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statsApi } from '../api'
import { useTheme } from '../composables/useTheme'
import { formatNumber } from '../utils/format'
import CloseButton from './CloseButton.vue'

defineEmits(['close'])

const { isDark } = useTheme()

const periods = [
  { value: 'daily', label: '今日' },
  { value: 'weekly', label: '本周' },
  { value: 'monthly', label: '本月' },
]

const period = ref('daily')
const stats = ref(null)
const loading = ref(false)
const hoveredPoint = ref(null)

const accentColor = computed(() => isDark.value ? '#60a5fa' : '#2563eb')

const chartWidth = 320
const chartHeight = 140
const padding = 32

const sortedDaily = computed(() => {
  if (!stats.value?.daily) return {}
  const entries = Object.entries(stats.value.daily)
  entries.sort((a, b) => a[0].localeCompare(b[0]))
  return Object.fromEntries(entries)
})

const chartData = computed(() => {
  const data = sortedDaily.value
  return Object.entries(data).map(([date, val]) => ({
    date,
    value: val.total,
    prompt: val.prompt || 0,
    completion: val.completion || 0,
  }))
})

const maxValue = computed(() => {
  if (chartData.value.length === 0) return 100
  return Math.max(100, ...chartData.value.map(d => d.value))
})

const maxModelTokens = computed(() => {
  if (!stats.value?.by_model) return 1
  return Math.max(1, ...Object.values(stats.value.by_model).map(d => d.total))
})

const chartPoints = computed(() => {
  const data = chartData.value
  if (data.length === 0) return []

  const xRange = chartWidth - 2 * padding
  const yRange = chartHeight - 2 * padding

  return data.map((d, i) => ({
    x: data.length === 1
      ? chartWidth / 2
      : padding + (i / Math.max(1, data.length - 1)) * xRange,
    y: chartHeight - padding - (d.value / maxValue.value) * yRange,
    date: d.date,
    value: d.value,
    prompt: d.prompt,
    completion: d.completion,
  }))
})

const linePath = computed(() => {
  const points = chartPoints.value
  if (points.length === 0) return ''
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
})

const areaPath = computed(() => {
  const points = chartPoints.value
  if (points.length === 0) return ''

  const baseY = chartHeight - padding

  let path = `M ${points[0].x} ${baseY} `
  path += points.map(p => `L ${p.x} ${p.y}`).join(' ')
  path += ` L ${points[points.length - 1].x} ${baseY} Z`

  return path
})

function formatDateLabel(dateStr) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatFullDate(dateStr) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

async function loadStats() {
  loading.value = true
  try {
    const res = await statsApi.getTokens(period.value)
    stats.value = res.data
  } catch (e) {
    console.error('Failed to load stats:', e)
  } finally {
    loading.value = false
  }
}

function changePeriod(p) {
  period.value = p
  hoveredPoint.value = null
  loadStats()
}

onMounted(loadStats)
</script>

<style scoped>
.stats-panel {
  padding: 0;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.stats-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.stats-title svg {
  color: var(--text-tertiary);
}

.stats-title h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* tab styles now in global.css */

.stats-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* 统计卡片 */
.stats-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 12px;
  transition: border-color 0.2s;
}

.stat-card:hover {
  border-color: var(--border-medium);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.input-icon {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.output-icon {
  background: rgba(168, 85, 247, 0.1);
  color: #a855f7;
}

.total-icon {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.stat-card.total {
  background: var(--accent-primary-light);
  border-color: rgba(37, 99, 235, 0.15);
}

.stat-card.total .total-icon {
  background: rgba(37, 99, 235, 0.15);
  color: var(--accent-primary);
}

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.3;
}

/* 趋势图 */
.stats-chart {
  margin-bottom: 16px;
}

.chart-title,
.model-title {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-bottom: 10px;
}

.chart-container {
  background: var(--bg-input);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 12px 8px 8px 8px;
  position: relative;
  overflow: hidden;
}

.line-chart {
  width: 100%;
  height: 140px;
}

.y-label {
  fill: var(--text-tertiary);
  font-size: 9px;
}

.data-point {
  cursor: pointer;
  transition: r 0.15s;
}

.data-point:hover {
  r: 5;
}

.x-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  padding: 0 28px 0 32px;
}

.x-label {
  font-size: 10px;
  color: var(--text-tertiary);
  transition: color 0.15s;
}

.x-label.active {
  color: var(--text-primary);
  font-weight: 500;
}

/* 提示框 */
.tooltip {
  position: absolute;
  background: var(--bg-primary);
  border: 1px solid var(--border-medium);
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 11px;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateX(-50%);
  z-index: 10;
  min-width: 120px;
}

.tooltip-date {
  color: var(--text-tertiary);
  font-size: 10px;
  margin-bottom: 4px;
}

.tooltip-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.tooltip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tooltip-dot.prompt {
  background: #3b82f6;
}

.tooltip-dot.completion {
  background: #a855f7;
}

.tooltip-total {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid var(--border-light);
  font-weight: 600;
  color: var(--text-primary);
  font-size: 12px;
}

/* 模型分布 */
.stats-by-model {
  margin-bottom: 4px;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-info {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.model-name {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}

.model-value {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.model-unit {
  font-weight: 400;
  color: var(--text-tertiary);
}

.model-bar-bg {
  width: 100%;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.model-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), #a855f7);
  border-radius: 3px;
  transition: width 0.5s ease;
  min-width: 4px;
}

/* 空状态 */
.stats-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-tertiary);
  font-size: 13px;
}
</style>

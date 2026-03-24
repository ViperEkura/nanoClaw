<template>
  <div class="stats-panel">
    <div class="stats-header">
      <h4>Token 使用统计</h4>
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
    </div>

    <div v-if="loading" class="stats-loading">加载中...</div>

    <template v-else-if="stats">
      <div class="stats-summary">
        <div class="stat-card">
          <div class="stat-label">输入 Token</div>
          <div class="stat-value">{{ formatNumber(stats.prompt_tokens) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">输出 Token</div>
          <div class="stat-value">{{ formatNumber(stats.completion_tokens) }}</div>
        </div>
        <div class="stat-card highlight">
          <div class="stat-label">总计</div>
          <div class="stat-value">{{ formatNumber(stats.total_tokens) }}</div>
        </div>
      </div>

      <div v-if="period !== 'daily' && stats.daily" class="stats-chart">
        <div class="chart-title">每日使用趋势</div>
        <div class="chart-container">
          <svg class="line-chart" :viewBox="`0 0 ${chartWidth} ${chartHeight}`">
            <!-- 网格线 -->
            <g class="grid-lines">
              <line
                v-for="i in 4"
                :key="'grid-' + i"
                :x1="padding"
                :y1="padding + (chartHeight - 2 * padding) * (i - 1) / 4"
                :x2="chartWidth - padding"
                :y2="padding + (chartHeight - 2 * padding) * (i - 1) / 4"
                stroke="var(--border-light)"
                stroke-dasharray="4,4"
              />
            </g>
            
            <!-- 填充区域 -->
            <path
              :d="areaPath"
              fill="url(#gradient)"
              opacity="0.3"
            />
            
            <!-- 折线 -->
            <path
              :d="linePath"
              fill="none"
              stroke="var(--accent-primary)"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            
            <!-- 数据点 -->
            <g class="data-points">
              <circle
                v-for="(point, idx) in chartPoints"
                :key="idx"
                :cx="point.x"
                :cy="point.y"
                r="4"
                fill="var(--accent-primary)"
                stroke="var(--bg-primary)"
                stroke-width="2"
                class="data-point"
                @mouseenter="hoveredPoint = idx"
                @mouseleave="hoveredPoint = null"
              />
            </g>
            
            <!-- 渐变定义 -->
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="var(--accent-primary)" />
                <stop offset="100%" stop-color="var(--accent-primary)" stop-opacity="0" />
              </linearGradient>
            </defs>
          </svg>
          
          <!-- X轴标签 -->
          <div class="x-labels">
            <span
              v-for="(data, date) in sortedDaily"
              :key="date"
              class="x-label"
            >
              {{ formatDateLabel(date) }}
            </span>
          </div>
          
          <!-- 悬浮提示 -->
          <div
            v-if="hoveredPoint !== null && chartPoints[hoveredPoint]"
            class="tooltip"
            :style="{ left: chartPoints[hoveredPoint].x + 'px', top: (chartPoints[hoveredPoint].y - 40) + 'px' }"
          >
            <div class="tooltip-date">{{ chartPoints[hoveredPoint].date }}</div>
            <div class="tooltip-value">{{ formatNumber(chartPoints[hoveredPoint].value) }} tokens</div>
          </div>
        </div>
      </div>

      <div v-if="period === 'daily' && stats.by_model" class="stats-by-model">
        <div class="model-title">按模型分布</div>
        <div v-for="(data, model) in stats.by_model" :key="model" class="model-row">
          <span class="model-name">{{ model }}</span>
          <span class="model-value">{{ formatNumber(data.total) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statsApi } from '../api'

const periods = [
  { value: 'daily', label: '今日' },
  { value: 'weekly', label: '本周' },
  { value: 'monthly', label: '本月' },
]

const period = ref('daily')
const stats = ref(null)
const loading = ref(false)
const hoveredPoint = ref(null)

const chartWidth = 320
const chartHeight = 160
const padding = 20

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
    prompt: val.prompt,
    completion: val.completion,
  }))
})

const maxValue = computed(() => {
  if (chartData.value.length === 0) return 100
  return Math.max(100, ...chartData.value.map(d => d.value))
})

const chartPoints = computed(() => {
  const data = chartData.value
  if (data.length === 0) return []
  
  const xRange = chartWidth - 2 * padding
  const yRange = chartHeight - 2 * padding
  
  return data.map((d, i) => ({
    x: padding + (i / Math.max(1, data.length - 1)) * xRange,
    y: chartHeight - padding - (d.value / maxValue.value) * yRange,
    date: d.date,
    value: d.value,
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
  
  const xRange = chartWidth - 2 * padding
  const startX = padding
  const endX = chartWidth - padding
  const baseY = chartHeight - padding
  
  let path = `M ${startX} ${baseY} `
  path += points.map(p => `L ${p.x} ${p.y}`).join(' ')
  path += ` L ${endX} ${baseY} Z`
  
  return path
})

function formatDateLabel(dateStr) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
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
  loadStats()
}

onMounted(loadStats)
</script>

<style scoped>
.stats-panel {
  padding: 16px 0;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.stats-header h4 {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

.period-tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-input);
  padding: 3px;
  border-radius: 8px;
}

.tab {
  padding: 4px 12px;
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.tab.active {
  background: var(--accent-primary);
  color: white;
}

.stats-loading {
  text-align: center;
  padding: 20px;
  color: var(--text-tertiary);
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-input);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.stat-card.highlight {
  background: var(--accent-primary-light);
}

.stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-card.highlight .stat-value {
  color: var(--accent-primary);
}

.stats-chart {
  margin-top: 16px;
}

.chart-title,
.model-title {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.chart-container {
  background: var(--bg-input);
  border-radius: 8px;
  padding: 16px;
  position: relative;
}

.line-chart {
  width: 100%;
  height: 160px;
}

.data-point {
  cursor: pointer;
  transition: r 0.15s;
}

.data-point:hover {
  r: 6;
}

.x-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  padding: 0 20px;
}

.x-label {
  font-size: 10px;
  color: var(--text-tertiary);
}

.tooltip {
  position: absolute;
  background: var(--bg-primary);
  color: var(--text-primary);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transform: translateX(-50%);
  z-index: 10;
}

.tooltip-date {
  color: var(--text-tertiary);
  font-size: 10px;
}

.tooltip-value {
  font-weight: 600;
  color: var(--accent-primary);
}

.stats-by-model {
  margin-top: 16px;
}

.model-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-input);
  border-radius: 6px;
  margin-bottom: 6px;
}

.model-name {
  font-size: 12px;
  color: var(--text-secondary);
}

.model-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}
</style>

<template>
  <div class="stats-panel">
    <div class="panel-header">
      <div class="panel-title">
        <span v-html="icons.stats" />
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
        <button class="btn-close" @click="$emit('close')">
          <span v-html="icons.closeMd" />
        </button>
      </div>
    </div>

    <div v-if="loading" class="stats-loading">
      <span class="spinner" v-html="icons.spinnerMd" />
      加载中...
    </div>

    <template v-else-if="stats">
      <!-- 统计卡片 -->
      <div class="stats-summary">
        <div class="stat-card">
          <div class="stat-icon input-icon">
            <span v-html="icons.edit" />
          </div>
          <div class="stat-info">
            <span class="stat-label">输入</span>
            <span class="stat-value">{{ formatNumber(stats.prompt_tokens) }}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon output-icon">
            <span v-html="icons.file" />
          </div>
          <div class="stat-info">
            <span class="stat-label">输出</span>
            <span class="stat-value">{{ formatNumber(stats.completion_tokens) }}</span>
          </div>
        </div>
        <div class="stat-card total">
          <div class="stat-icon total-icon">
            <span v-html="icons.trendUp" />
          </div>
          <div class="stat-info">
            <span class="stat-label">总计</span>
            <span class="stat-value">{{ formatNumber(stats.total_tokens) }}</span>
          </div>
        </div>
      </div>

      <!-- 趋势图 -->
      <div v-if="chartData.length > 0" class="stats-chart">
        <div class="chart-title">{{ period === 'daily' ? '今日趋势' : '每日趋势' }}</div>
        <div class="chart-container">
          <canvas ref="chartCanvas"></canvas>
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
        <span v-html="icons.stats" style="opacity: 0.5;" />
        <span>暂无使用数据</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import { statsApi } from '../api'
import { formatNumber } from '../utils/format'
import { icons } from '../utils/icons'

Chart.register(...registerables)

defineEmits(['close'])

const periods = [
  { value: 'daily', label: '今日' },
  { value: 'weekly', label: '本周' },
  { value: 'monthly', label: '本月' },
]

const period = ref('daily')
const stats = ref(null)
const loading = ref(false)
const chartCanvas = ref(null)
let chartInstance = null

const sortedDaily = computed(() => {
  if (!stats.value?.daily) return {}
  const entries = Object.entries(stats.value.daily)
  entries.sort((a, b) => a[0].localeCompare(b[0]))
  return Object.fromEntries(entries)
})

const chartData = computed(() => {
  if (period.value === 'daily' && stats.value?.hourly) {
    const hourly = stats.value.hourly
    // Backend returns UTC hours — convert to local timezone for display.
    const offset = -new Date().getTimezoneOffset() / 60  // e.g. +8 for UTC+8
    const localHourly = {}
    for (const [utcH, val] of Object.entries(hourly)) {
      const localH = ((parseInt(utcH) + offset) % 24 + 24) % 24
      localHourly[localH] = val
    }
    let minH = 24, maxH = -1
    for (const h of Object.keys(localHourly)) {
      const hour = parseInt(h)
      if (hour < minH) minH = hour
      if (hour > maxH) maxH = hour
    }
    if (minH > maxH) return []
    const start = Math.max(0, minH)
    const end = Math.min(23, maxH)
    return Array.from({ length: end - start + 1 }, (_, i) => {
      const h = start + i
      return {
        label: `${h}:00`,
        value: localHourly[String(h)]?.total || 0,
      }
    })
  }

  const data = sortedDaily.value
  return Object.entries(data).map(([date, val]) => {
    // date is "YYYY-MM-DD" from backend — parse directly to avoid
    // new Date() timezone shift (parsed as UTC midnight then
    // getMonth/getDate applies local offset, potentially off by one day).
    const [year, month, day] = date.split('-')
    return {
      label: `${parseInt(month)}/${parseInt(day)}`,
      value: val.total,
      prompt: val.prompt || 0,
      completion: val.completion || 0,
    }
  })
})

const maxModelTokens = computed(() => {
  if (!stats.value?.by_model) return 1
  return Math.max(1, ...Object.values(stats.value.by_model).map(d => d.total))
})

function getAccentColor() {
  return getComputedStyle(document.documentElement).getPropertyValue('--accent-primary').trim() || '#2563eb'
}

function getTextColor(alpha = 1) {
  const c = getComputedStyle(document.documentElement).getPropertyValue('--text-tertiary').trim() || '#888'
  if (alpha === 1) return c
  // Convert hex to rgba
  if (c.startsWith('#')) {
    const r = parseInt(c.slice(1, 3), 16)
    const g = parseInt(c.slice(3, 5), 16)
    const b = parseInt(c.slice(5, 7), 16)
    return `rgba(${r},${g},${b},${alpha})`
  }
  return c
}

function destroyChart() {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
}

function buildChart() {
  if (!chartCanvas.value || chartData.value.length === 0) return

  destroyChart()

  const accent = getAccentColor()
  const ctx = chartCanvas.value.getContext('2d')

  // Gradient fill
  const gradient = ctx.createLinearGradient(0, 0, 0, 200)
  gradient.addColorStop(0, accent + '40')
  gradient.addColorStop(1, accent + '05')

  const labels = chartData.value.map(d => d.label)
  const values = chartData.value.map(d => d.value)

  // Determine max ticks for x-axis
  const maxTicks = chartData.value.length <= 8 ? chartData.value.length : 6

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data: values,
        borderColor: accent,
        backgroundColor: gradient,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: accent,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
        fill: true,
        tension: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      layout: {
        padding: { top: 4, right: 4, bottom: 0, left: 0 },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: getTextColor(),
            font: { size: 10 },
            maxTicksLimit: maxTicks,
            maxRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: getTextColor(0.15),
            drawBorder: false,
          },
          border: { display: false },
          ticks: {
            color: getTextColor(),
            font: { size: 9 },
            maxTicksLimit: 4,
            callback: (v) => formatNumber(v),
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(0,0,0,0.8)',
          titleColor: '#fff',
          bodyColor: '#ccc',
          titleFont: { size: 11, weight: '500' },
          bodyFont: { size: 11 },
          padding: 8,
          cornerRadius: 6,
          displayColors: false,
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex
              const d = chartData.value[idx]
              if (period.value === 'daily') {
                return `${d.label} - ${parseInt(d.label) + 1}:00`
              }
              return d.label
            },
            label: (item) => `${formatNumber(item.raw)} tokens`,
          },
        },
      },
      interaction: {
        mode: 'index',
        intersect: false,
      },
    },
  })
}

watch(chartData, () => {
  nextTick(buildChart)
})

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
onBeforeUnmount(destroyChart)
</script>

<style scoped>
.stats-panel {
  padding: 0;
}

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
  padding: 10px;
  position: relative;
  height: 180px;
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

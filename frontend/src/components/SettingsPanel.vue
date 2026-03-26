<template>
  <div class="settings-panel">
    <div class="settings-header">
      <div class="settings-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        <h4>会话设置</h4>
      </div>
      <div class="header-actions">
        <div class="period-tabs">
          <button
            v-for="t in tabs"
            :key="t.value"
            :class="['tab', { active: activeTab === t.value }]"
            @click="activeTab = t.value"
          >
            {{ t.label }}
          </button>
        </div>
        <button class="btn-close" @click="$emit('close')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <div class="settings-body">
      <!-- 基本设置 -->
      <template v-if="activeTab === 'basic'">
        <div class="form-group">
          <label>会话标题</label>
          <input v-model="form.title" type="text" placeholder="输入标题..." />
        </div>
        <div class="form-group">
          <label>模型</label>
          <select v-model="form.model">
            <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>系统提示词</label>
          <textarea
            v-model="form.system_prompt"
            rows="4"
            placeholder="设置 AI 的角色和行为..."
          ></textarea>
        </div>
      </template>

      <!-- 模型参数 -->
      <template v-if="activeTab === 'params'">
        <div class="form-group">
          <label>
            温度
            <span class="value-display">{{ form.temperature.toFixed(1) }}</span>
          </label>
          <input
            v-model.number="form.temperature"
            type="range"
            min="0"
            max="2"
            step="0.1"
          />
          <div class="range-labels">
            <span>精确</span>
            <span>创意</span>
          </div>
        </div>
        <div class="form-group">
          <label>
            最大 Token
            <span class="value-display">{{ form.max_tokens.toLocaleString() }}</span>
          </label>
          <input
            v-model.number="form.max_tokens"
            type="range"
            min="256"
            max="65536"
            step="256"
          />
          <div class="range-labels">
            <span>256</span>
            <span>65,536</span>
          </div>
        </div>
      </template>

      <!-- 偏好设置 -->
      <template v-if="activeTab === 'prefs'">
        <div class="setting-row">
          <div class="setting-info">
            <span class="setting-label">启用思维链</span>
            <span class="setting-desc">让模型展示推理过程</span>
          </div>
          <button
            class="toggle"
            :class="{ on: form.thinking_enabled }"
            @click="form.thinking_enabled = !form.thinking_enabled"
          >
            <span class="toggle-thumb"></span>
          </button>
        </div>
        <div class="setting-row">
          <div class="setting-info">
            <span class="setting-label">夜间模式</span>
            <span class="setting-desc">切换深色外观主题</span>
          </div>
          <button
            class="toggle"
            :class="{ on: isDark }"
            @click="toggleTheme"
          >
            <span class="toggle-thumb"></span>
          </button>
        </div>
      </template>

      <div class="auto-save-hint">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
        </svg>
        <span>修改自动保存</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from 'vue'
import { modelApi, conversationApi } from '../api'
import { useTheme } from '../composables/useTheme'

const props = defineProps({
  visible: { type: Boolean, default: false },
  conversation: { type: Object, default: null },
})

const emit = defineEmits(['close', 'save'])

const { isDark, toggleTheme } = useTheme()
const models = ref([])

const tabs = [
  { value: 'basic', label: '基本' },
  { value: 'params', label: '参数' },
  { value: 'prefs', label: '偏好' },
]

const activeTab = ref('basic')

const form = reactive({
  title: '',
  model: '',
  system_prompt: '',
  temperature: 1.0,
  max_tokens: 65536,
  thinking_enabled: false,
})

async function loadModels() {
  try {
    const res = await modelApi.getCached()
    models.value = res.data || []
  } catch (e) {
    console.error('Failed to load models:', e)
  }
}

function syncFormFromConversation() {
  if (props.conversation) {
    form.title = props.conversation.title || ''
    form.system_prompt = props.conversation.system_prompt || ''
    form.temperature = props.conversation.temperature ?? 1.0
    form.max_tokens = props.conversation.max_tokens ?? 65536
    form.thinking_enabled = props.conversation.thinking_enabled ?? false
    // model: 优先使用 conversation 的值，其次 models 列表第一个
    if (props.conversation.model) {
      form.model = props.conversation.model
    } else if (models.value.length > 0) {
      form.model = models.value[0].id
    }
  }
}

// Sync form when panel opens or conversation changes
watch([() => props.visible, () => props.conversation, models], () => {
  if (props.visible) {
    activeTab.value = 'basic'
    syncFormFromConversation()
  }
}, { deep: true })

// Auto-save with debounce when form changes
let saveTimer = null
watch(form, () => {
  if (props.visible && props.conversation) {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(saveChanges, 500)
  }
}, { deep: true })

async function saveChanges() {
  if (!props.conversation) return
  try {
    const res = await conversationApi.update(props.conversation.id, { ...form })
    emit('save', res.data)
  } catch (e) {
    console.error('Failed to save settings:', e)
  }
}

onMounted(loadModels)
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.settings-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.settings-title svg {
  color: var(--text-tertiary);
}

.settings-title h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.period-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg-input);
  padding: 3px;
  border-radius: 8px;
}

.tab {
  padding: 4px 12px;
  border: none;
  background: none;
  color: var(--text-tertiary);
  font-size: 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--text-secondary);
}

.tab.active {
  background: var(--accent-primary);
  color: white;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3);
}

.settings-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---- Value display ---- */
.value-display {
  float: right;
  color: var(--accent-primary);
  font-weight: 600;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

/* ---- Range labels ---- */
.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

/* ---- Setting row (toggle items) ---- */
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0;
}

.setting-row + .setting-row {
  margin-top: 4px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.setting-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.setting-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ---- Toggle ---- */
.toggle {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  border: none;
  background: var(--bg-code);
  cursor: pointer;
  position: relative;
  transition: background 0.25s ease;
  padding: 0;
  flex-shrink: 0;
}

.toggle.on {
  background: var(--accent-primary);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.toggle.on .toggle-thumb {
  transform: translateX(20px);
}

/* ---- Auto-save hint ---- */
.auto-save-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 0 4px;
  font-size: 12px;
  color: var(--text-tertiary);
  opacity: 0.7;
}
</style>

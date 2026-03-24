<template>
  <Transition name="slide">
    <div v-if="visible" class="settings-overlay" @click.self="$emit('close')">
      <div class="settings-panel">
        <div class="settings-header">
          <h3>会话设置</h3>
          <button class="btn-close" @click="$emit('close')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="settings-body">
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

          <div class="form-row">
            <div class="form-group flex-1">
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

            <div class="form-group flex-1">
              <label>
                最大 Token
                <span class="value-display">{{ form.max_tokens }}</span>
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
                <span>65536</span>
              </div>
            </div>
          </div>

          <div class="form-group toggle-group">
            <label>启用思维链</label>
            <button
              class="toggle"
              :class="{ on: form.thinking_enabled }"
              @click="form.thinking_enabled = !form.thinking_enabled"
            >
              <span class="toggle-thumb"></span>
            </button>
          </div>

          <div class="settings-divider"></div>

          <div class="form-group toggle-group">
            <label>夜间模式</label>
            <button
              class="toggle"
              :class="{ on: isDark }"
              @click="toggleTheme"
            >
              <span class="toggle-thumb"></span>
            </button>
          </div>
        </div>

        <div class="settings-footer">
          <button class="btn-cancel" @click="$emit('close')">取消</button>
          <button class="btn-save" @click="save">保存</button>
        </div>

        <div class="settings-stats">
          <StatsPanel />
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from 'vue'
import { modelApi } from '../api'
import { useTheme } from '../composables/useTheme'
import StatsPanel from './StatsPanel.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  conversation: { type: Object, default: null },
})

const emit = defineEmits(['close', 'save'])

const { isDark, toggleTheme } = useTheme()
const models = ref([])

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
    const res = await modelApi.list()
    models.value = res.data || []
  } catch (e) {
    console.error('Failed to load models:', e)
  }
}

watch(() => props.visible, (val) => {
  if (val && props.conversation) {
    form.title = props.conversation.title || ''
    form.model = props.conversation.model || ''
    form.system_prompt = props.conversation.system_prompt || ''
    form.temperature = props.conversation.temperature ?? 1.0
    form.max_tokens = props.conversation.max_tokens ?? 65536
    form.thinking_enabled = props.conversation.thinking_enabled ?? false
  }
})

onMounted(loadModels)

function save() {
  emit('save', { ...form })
  emit('close')
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
  transition: background 0.2s;
}

.settings-panel {
  width: 380px;
  height: 100vh;
  background: var(--bg-primary);
  border-left: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  transition: background 0.2s, border-color 0.2s;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
}

.settings-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.15s;
}

.btn-close:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.settings-body {
  flex: 1;
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-weight: 500;
}

.value-display {
  float: right;
  color: var(--accent-primary);
  font-weight: 600;
}

.form-group input[type="text"],
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
  box-sizing: border-box;
}

.form-group input[type="text"]:focus,
.form-group textarea:focus,
.form-group select:focus {
  border-color: var(--accent-primary);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-group select {
  cursor: pointer;
}

.form-group select option {
  background: var(--bg-primary);
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.form-group input[type="range"] {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--bg-code);
  border-radius: 2px;
  outline: none;
}

.form-group input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent-primary);
  cursor: pointer;
  border: 2px solid var(--bg-primary);
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.toggle-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toggle-group label {
  margin-bottom: 0;
}

.toggle {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  border: none;
  background: var(--bg-code);
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
  padding: 0;
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
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.toggle.on .toggle-thumb {
  transform: translateX(20px);
}

.settings-divider {
  height: 1px;
  background: var(--border-light);
  margin: 24px 0;
}

.settings-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-cancel {
  padding: 8px 20px;
  border-radius: 8px;
  border: 1px solid var(--border-medium);
  background: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-cancel:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-save {
  padding: 8px 20px;
  border-radius: 8px;
  border: none;
  background: var(--accent-primary);
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-save:hover {
  background: var(--accent-primary-hover);
}

.settings-stats {
  padding: 16px 24px 24px;
  border-top: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s ease;
}

.slide-enter-active .settings-panel,
.slide-leave-active .settings-panel {
  transition: transform 0.25s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}

.slide-enter-from .settings-panel,
.slide-leave-to .settings-panel {
  transform: translateX(100%);
}
</style>

<template>
  <div class="message-input">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="text"
        placeholder="输入消息... (Shift+Enter 换行)"
        rows="1"
        @input="autoResize"
        @keydown="onKeydown"
        :disabled="disabled"
      ></textarea>
      <div class="input-actions">
        <button
          class="btn-send"
          :class="{ active: text.trim() && !disabled }"
          :disabled="!text.trim() || disabled"
          @click="send"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
    <div class="input-hint">AI 助手回复内容仅供参考</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])
const text = ref('')
const textareaRef = ref(null)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function send() {
  const content = text.value.trim()
  if (!content || props.disabled) return
  emit('send', content)
  text.value = ''
  nextTick(() => {
    autoResize()
  })
}

function focus() {
  textareaRef.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped>
.message-input {
  padding: 16px 24px 12px;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-light);
  transition: background 0.2s, border-color 0.2s;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color 0.2s, background 0.2s;
}

.input-wrapper:focus-within {
  border-color: var(--accent-primary);
}

textarea {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  outline: none;
  font-family: inherit;
  max-height: 200px;
}

textarea::placeholder {
  color: var(--text-tertiary);
}

textarea:disabled {
  opacity: 0.5;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 8px;
}

.btn-send {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: var(--bg-code);
  color: var(--text-tertiary);
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-send.active {
  background: var(--accent-primary);
  color: white;
  cursor: pointer;
}

.btn-send.active:hover {
  background: var(--accent-primary-hover);
}

.input-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 8px;
}
</style>

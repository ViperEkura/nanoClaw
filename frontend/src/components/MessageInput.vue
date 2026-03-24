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
    <div class="input-hint">基于 GLM 大语言模型，回复内容仅供参考</div>
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
  background: #16213e;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  background: #1a1a2e;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: rgba(79, 70, 229, 0.5);
}

textarea {
  flex: 1;
  background: none;
  border: none;
  color: #e2e8f0;
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  outline: none;
  font-family: inherit;
  max-height: 200px;
}

textarea::placeholder {
  color: #475569;
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
  background: rgba(255, 255, 255, 0.06);
  color: #475569;
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-send.active {
  background: #4f46e5;
  color: white;
  cursor: pointer;
}

.btn-send.active:hover {
  background: #6366f1;
}

.input-hint {
  text-align: center;
  font-size: 12px;
  color: #374151;
  margin-top: 8px;
}
</style>

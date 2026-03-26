<template>
  <div class="message-input">
    <!-- 文件列表 -->
    <div v-if="uploadedFiles.length > 0" class="file-list">
      <div v-for="(file, index) in uploadedFiles" :key="index" class="file-item">
        <span class="file-icon">{{ getFileIcon(file.extension) }}</span>
        <span class="file-name">{{ file.name }}</span>
        <button class="btn-remove-file" @click="removeFile(index)" title="移除">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <div class="input-container">
      <textarea
        ref="textareaRef"
        v-model="text"
        :placeholder="disabled ? 'AI 正在回复中...' : '输入消息... (Shift+Enter 换行)'"
        rows="1"
        @input="autoResize"
        @keydown="onKeydown"
      ></textarea>
      <div class="input-footer">
        <input
          ref="fileInputRef"
          type="file"
          accept=".txt,.md,.json,.xml,.html,.css,.js,.ts,.jsx,.tsx,.py,.java,.c,.cpp,.h,.hpp,.yaml,.yml,.toml,.ini,.csv,.sql,.sh,.bat,.log,.vue,.svelte,.go,.rs,.rb,.php,.swift,.kt,.scala,.lua,.r,.dart,.scala"
          @change="handleFileUpload"
          style="display: none"
        />
        <div class="input-actions">
          <button
            class="btn-tool"
            :class="{ active: toolsEnabled }"
            :disabled="disabled"
            @click="toggleTools"
            :title="toolsEnabled ? '工具调用: 已开启' : '工具调用: 已关闭'"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
          </button>
          <button
            class="btn-upload"
            :disabled="disabled"
            @click="triggerFileUpload"
            title="上传文件"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <button
            class="btn-send"
            :class="{ active: canSend }"
            :disabled="!canSend || disabled"
            @click="send"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div class="input-hint">AI 助手回复内容仅供参考</div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  toolsEnabled: { type: Boolean, default: true },
})

const emit = defineEmits(['send', 'toggleTools'])
const text = ref('')
const textareaRef = ref(null)
const fileInputRef = ref(null)
const uploadedFiles = ref([])

const canSend = computed(() => text.value.trim() || uploadedFiles.value.length > 0)

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
  if (props.disabled || !canSend.value) return

  const messageText = text.value.trim()

  // 发送内容和附件
  emit('send', {
    text: messageText,
    attachments: uploadedFiles.value.length > 0 ? uploadedFiles.value.map(f => ({
      name: f.name,
      extension: f.extension,
      content: f.content,
    })) : null,
  })

  // 清空
  text.value = ''
  uploadedFiles.value = []
  nextTick(() => {
    autoResize()
  })
}

function toggleTools() {
  emit('toggleTools', !props.toolsEnabled)
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target?.result
    if (typeof content === 'string') {
      const extension = file.name.split('.').pop()?.toLowerCase() || ''
      uploadedFiles.value.push({
        name: file.name,
        content,
        extension,
      })
    }
  }
  reader.onerror = () => {
    console.error('文件读取失败')
  }
  reader.readAsText(file)

  // 清空 input 以便重复上传同一文件
  event.target.value = ''
}

function removeFile(index) {
  uploadedFiles.value.splice(index, 1)
}

function getFileIcon(extension) {
  return `.${extension}`
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

.file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 0 24px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px 6px 8px;
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.file-item:hover {
  border-color: var(--border-medium);
  background: var(--bg-hover);
}

.file-icon {
  font-size: 14px;
  line-height: 1;
}

.file-name {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-weight: 500;
}

.btn-remove-file {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  padding: 0;
}

.btn-remove-file:hover {
  background: var(--danger-bg);
  color: var(--danger-color);
}

.input-container {
  display: flex;
  flex-direction: column;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: 12px;
  padding: 12px;
  transition: border-color 0.2s, background 0.2s;
}

.input-container:focus-within {
  border-color: var(--accent-primary);
}

textarea {
  width: 100%;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  outline: none;
  font-family: inherit;
  min-height: 36px;
  max-height: 200px;
  padding: 0;
}

textarea::placeholder {
  color: var(--text-tertiary);
}

.input-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
  margin-top: 4px;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-tool,
.btn-send {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: var(--bg-code);
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.btn-upload {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: rgba(139, 92, 246, 0.12);
  color: #8b5cf6;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.btn-tool:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.btn-tool.active {
  background: var(--success-bg);
  color: var(--success-color);
}

.btn-tool.active:hover:not(:disabled) {
  background: var(--success-color);
  color: white;
}

.btn-upload:hover:not(:disabled) {
  background: #8b5cf6;
  color: white;
  transform: translateY(-1px);
}

.btn-upload:active:not(:disabled) {
  background: #7c3aed;
  transform: translateY(0);
}

.btn-tool:disabled,
.btn-upload:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-send {
  cursor: not-allowed;
}

.btn-send.active {
  background: var(--accent-primary);
  color: white;
  cursor: pointer;
}

.btn-send.active:hover {
  background: var(--accent-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}

.btn-send.active:active {
  transform: translateY(0);
  box-shadow: none;
}

.input-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 8px;
}
</style>

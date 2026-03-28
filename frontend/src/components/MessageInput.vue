<template>
  <div class="message-input">
    <!-- 文件列表 -->
    <div v-if="uploadedFiles.length > 0" class="file-list">
      <div v-for="(file, index) in uploadedFiles" :key="index" class="file-item">
        <span class="file-icon">{{ getFileIcon(file.extension) }}</span>
        <span class="file-name">{{ file.name }}</span>
        <button class="ghost-btn danger btn-remove-file" @click="removeFile(index)" title="移除">
          <span v-html="icons.close" />
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
          accept=ALLOWED_UPLOAD_EXTENSIONS
          @change="handleFileUpload"
          style="display: none"
        />
        <div class="input-actions">
          <button
            class="btn-upload"
            :class="{ active: uploadedFiles.length > 0 }"
            :disabled="disabled"
            @click="triggerFileUpload"
            :title="uploadedFiles.length > 0 ? `已上传 ${uploadedFiles.length} 个文件` : '上传文件'"
          >
            <span v-html="icons.upload" />
          </button>
          <button
            class="btn-tool"
            :class="{ active: toolsEnabled }"
            :disabled="disabled"
            @click="toggleTools"
            :title="toolsEnabled ? '工具调用: 已开启' : '工具调用: 已关闭'"
          >
            <span v-html="icons.wrench" />
          </button>
          <button
            class="btn-send"
            :class="{ active: canSend }"
            :disabled="!canSend || disabled"
            @click="send"
          >
            <span v-html="icons.send" />
          </button>
        </div>
      </div>
    </div>
    <div class="input-hint">AI 助手回复内容仅供参考</div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { icons } from '../utils/icons'
import { TEXTAREA_MAX_HEIGHT_PX, ALLOWED_UPLOAD_EXTENSIONS } from '../constants'

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
  el.style.height = Math.min(el.scrollHeight, TEXTAREA_MAX_HEIGHT_PX) + 'px'
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
  width: 18px;
  height: 18px;
  padding: 0;
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
.btn-upload {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.15s ease;
}

.btn-tool::before,
.btn-upload::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0.20;
  transition: opacity 0.15s ease;
}

.btn-upload::before {
  background: var(--attachment-color);
}

.btn-tool::before {
  background: var(--tool-color);
}

.btn-upload {
  color: var(--attachment-color);
}

.btn-tool {
  color: var(--tool-color);
}

.btn-tool:hover:not(:disabled)::before,
.btn-upload:hover:not(:disabled)::before {
  opacity: 0.7;
}

.btn-upload.active::before {
  opacity: 0.5;
}

.btn-upload.active:hover:not(:disabled)::before {
  opacity: 0.7;
}

.btn-tool.active::before {
  opacity: 0.5;
}

.btn-tool.active:hover:not(:disabled)::before {
  opacity: 0.7;
}

.btn-tool:disabled,
.btn-upload:disabled {
  cursor: not-allowed;
}

.btn-tool:disabled::before,
.btn-upload:disabled::before {
  opacity: 0.20;
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
  transition: all 0.15s ease;
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

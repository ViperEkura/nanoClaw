<template>
  <div class="file-explorer">
    <!-- File tree sidebar -->
    <div class="explorer-sidebar">
      <div class="explorer-header">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
        <span class="explorer-title">{{ projectName }}</span>
        <div class="explorer-actions">
          <button class="btn-icon-sm" @click="createNewFile" title="新建文件">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="11" x2="12" y2="17"/>
              <line x1="9" y1="14" x2="15" y2="14"/>
            </svg>
          </button>
          <button class="btn-icon-sm" @click="createNewFolder" title="新建文件夹">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              <line x1="12" y1="11" x2="12" y2="17"/>
              <line x1="9" y1="14" x2="15" y2="14"/>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="loadingTree" class="explorer-loading">
        <svg class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
      </div>

      <div v-else-if="treeItems.length === 0" class="explorer-empty">
        空项目
      </div>

      <div v-else class="tree-container">
        <FileTreeItem
          v-for="item in treeItems"
          :key="item.path"
          :item="item"
          :active-path="activeFile"
          :depth="0"
          :project-id="projectId"
          @select="openFile"
          @refresh="loadTree"
        />
      </div>
    </div>

    <!-- File viewer panel -->
    <div v-if="activeFile" class="file-viewer">
      <div class="viewer-header">
        <div class="viewer-breadcrumb">
          <span v-for="(seg, i) in breadcrumbSegments" :key="i" class="breadcrumb-seg">
            {{ seg }}
            <span v-if="i < breadcrumbSegments.length - 1" class="breadcrumb-sep">/</span>
          </span>
        </div>
        <div class="viewer-actions">
          <button class="btn-icon-sm save" @click="saveFile" title="保存 (Ctrl+S)" :disabled="saving">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
          </button>
          <button class="btn-icon-sm danger" @click="deleteFile" title="删除文件">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
          <button class="btn-icon-sm" @click="activeFile = null" title="关闭">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="loadingFile" class="viewer-loading">
        <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        加载中...
      </div>

      <div v-else-if="fileError" class="viewer-error">
        <span>{{ fileError }}</span>
      </div>

      <!-- Text / code editor (all non-image files including .md) -->
      <div v-else-if="fileType !== 'image'" class="code-pane">
        <CodeEditor
          v-model="editContent"
          :filename="activeFile"
          :dark="isDark"
          @save="saveFile"
        />
      </div>

      <!-- Image viewer -->
      <div v-else class="image-viewer">
        <img :src="imageUrl" :alt="activeFile" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="viewer-placeholder">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="color: var(--text-tertiary); opacity: 0.5;">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
      <span>选择文件以预览</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { projectApi } from '../api'
import FileTreeItem from './FileTreeItem.vue'
import CodeEditor from './CodeEditor.vue'
import { normalizeFileTree } from '../utils/fileTree'
import { useTheme } from '../composables/useTheme'

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico'])

const props = defineProps({
  projectId: { type: String, required: true },
  projectName: { type: String, default: '' },
})

const { isDark } = useTheme()

// -- Tree state --
const treeItems = ref([])
const loadingTree = ref(false)

// -- Viewer state --
const activeFile = ref(null)
const fileError = ref('')
const loadingFile = ref(false)
const editContent = ref('')
const saving = ref(false)
const imageUrl = ref('')

function releaseImageUrl() {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = ''
  }
}

const fileExt = computed(() => {
  if (!activeFile.value) return ''
  const parts = activeFile.value.split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
})

const breadcrumbSegments = computed(() => {
  if (!activeFile.value) return []
  return activeFile.value.split('/')
})

const fileType = computed(() => {
  if (IMAGE_EXTS.has(fileExt.value)) return 'image'
  return 'text'
})

async function loadTree(path = '') {
  loadingTree.value = true
  try {
    const res = await projectApi.listFiles(props.projectId, path)
    treeItems.value = normalizeFileTree(res.data, { expanded: false })
  } catch (e) {
    console.error('Failed to load tree:', e)
  } finally {
    loadingTree.value = false
  }
}

async function openFile(filepath) {
  activeFile.value = filepath
  fileError.value = ''
  editContent.value = ''
  releaseImageUrl()
  loadingFile.value = true

  const ext = filepath.split('.').pop().toLowerCase()
  if (IMAGE_EXTS.has(ext)) {
    try {
      const res = await projectApi.readFileRaw(props.projectId, filepath)
      const blob = await res.blob()
      imageUrl.value = URL.createObjectURL(blob)
    } catch (e) {
      fileError.value = '加载图片失败: ' + (e.message || '')
    } finally {
      loadingFile.value = false
    }
    return
  }

  try {
    const res = await projectApi.readFile(props.projectId, filepath)
    editContent.value = res.data.content
  } catch (e) {
    fileError.value = e.message || '加载文件失败'
  } finally {
    loadingFile.value = false
  }
}

async function saveFile() {
  if (!activeFile.value || saving.value) return
  saving.value = true
  try {
    await projectApi.writeFile(props.projectId, activeFile.value, editContent.value)
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

function deleteFile() {
  if (!activeFile.value) return
  const name = activeFile.value.split('/').pop()
  if (!confirm(`确定要删除 ${name} 吗？`)) return

  projectApi.deleteFile(props.projectId, activeFile.value).then(() => {
    activeFile.value = null
    loadTree()
  }).catch(e => {
    alert('删除失败: ' + e.message)
  })
}

async function createNewFile() {
  const name = prompt('文件名（例如 utils.py）')
  if (!name?.trim()) return
  const path = name.trim()
  try {
    await projectApi.writeFile(props.projectId, path, '')
    await loadTree()
    openFile(path)
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}

async function createNewFolder() {
  const name = prompt('文件夹名称')
  if (!name?.trim()) return
  try {
    await projectApi.mkdir(props.projectId, name.trim())
    await loadTree()
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}

// Ctrl+S global shortcut
function onGlobalKeydown(e) {
  if (e.key === 's' && (e.ctrlKey || e.metaKey) && activeFile.value) {
    e.preventDefault()
    saveFile()
  }
}

watch(() => props.projectId, () => {
  activeFile.value = null
  editContent.value = ''
  releaseImageUrl()
  loadTree()
})

onMounted(() => {
  loadTree()
  document.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
  releaseImageUrl()
})
</script>

<style scoped>
.file-explorer {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* -- Sidebar -- */
.explorer-sidebar {
  width: 20%;
  min-width: 140px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.explorer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

.explorer-header svg:first-child {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.explorer-title {
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.explorer-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.btn-icon-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
}

.btn-icon-sm:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-icon-sm.save:hover {
  background: var(--success-bg);
  color: var(--success-color);
}

.btn-icon-sm.danger:hover {
  background: var(--danger-bg);
  color: var(--danger-color);
}

.tree-container {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.tree-container::-webkit-scrollbar {
  width: 4px;
}

.tree-container::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 2px;
}

.explorer-loading,
.explorer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* -- Viewer -- */
.file-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-secondary);
  gap: 8px;
}

.viewer-breadcrumb {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumb-seg {
  flex-shrink: 0;
}

.breadcrumb-sep {
  margin: 0 2px;
  color: var(--text-tertiary);
}

.viewer-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
  align-items: center;
}

.viewer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.viewer-error {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--danger-color);
  font-size: 13px;
}

.viewer-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* -- Code pane -- */
.code-pane {
  flex: 1;
  overflow: hidden;
}

/* -- Image viewer -- */
.image-viewer {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: var(--bg-code);
  overflow: auto;
}

.image-viewer img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
}
</style>

<template>
  <div class="file-explorer">
    <!-- File tree sidebar -->
    <div class="explorer-sidebar">
      <div class="explorer-header">
        <span v-html="icons.folder" />
        <span class="explorer-title">{{ projectName }}</span>
        <div class="explorer-actions">
          <button class="btn-icon-sm" @click="createNewFile" title="新建文件">
            <span v-html="icons.fileNew" />
          </button>
          <button class="btn-icon-sm" @click="createNewFolder" title="新建文件夹">
            <span v-html="icons.folderNew" />
          </button>
        </div>
      </div>

      <div v-if="loadingTree" class="explorer-loading">
        <span class="spinner" v-html="icons.spinnerMd" />
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
          @move="moveItem"
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
          <button class="btn-icon-sm" @click="activeFile = null" title="关闭">
            <span v-html="icons.close" />
          </button>
        </div>
      </div>

      <div v-if="loadingFile" class="viewer-loading">
        <span class="spinner" v-html="icons.spinnerMd" />
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
      <span v-html="icons.fileLg" style="color: var(--text-tertiary); opacity: 0.5;" />
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
import { useModal } from '../composables/useModal'
import { useToast } from '../composables/useToast'
import { icons } from '../utils/icons'
import { getFileExtension, isImageFile } from '../utils/fileUtils'

const props = defineProps({
  projectId: { type: String, required: true },
  projectName: { type: String, default: '' },
})

const { isDark } = useTheme()
const modal = useModal()
const toast = useToast()

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

const fileExt = computed(() => getFileExtension(activeFile.value))

const breadcrumbSegments = computed(() => {
  if (!activeFile.value) return []
  return activeFile.value.split('/')
})

const fileType = computed(() => isImageFile(activeFile.value) ? 'image' : 'text')

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
  if (isImageFile(filepath)) {
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
    toast.success('已保存')
  } catch (e) {
    toast.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}


async function createNewFile() {
  const name = await modal.prompt('新建文件', '请输入文件名（例如 utils.py）')
  if (!name) return
  try {
    await projectApi.writeFile(props.projectId, name, '')
    toast.success(`已创建「${name}」`)
    await loadTree()
    openFile(name)
  } catch (e) {
    toast.error('创建失败: ' + e.message)
  }
}

async function createNewFolder() {
  const name = await modal.prompt('新建文件夹', '请输入文件夹名称')
  if (!name) return
  try {
    await projectApi.mkdir(props.projectId, name)
    toast.success(`已创建文件夹「${name}」`)
    await loadTree()
  } catch (e) {
    toast.error('创建失败: ' + e.message)
  }
}

async function moveItem({ srcPath, destDir, name }) {
  const newPath = `${destDir}/${name}`
  try {
    await projectApi.renameFile(props.projectId, srcPath, newPath)
    toast.success(`已移动「${name}」到 ${destDir}`)
    // Update active file path if it was moved
    if (activeFile.value && activeFile.value === srcPath) {
      activeFile.value = newPath
    } else if (activeFile.value && activeFile.value.startsWith(srcPath + '/')) {
      activeFile.value = newPath + activeFile.value.slice(srcPath.length)
    }
    await loadTree()
  } catch (e) {
    toast.error('移动失败: ' + e.message)
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

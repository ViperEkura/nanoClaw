<template>
  <div class="tree-node" @mouseenter="hovered = true" @mouseleave="onMouseLeave">
    <div class="tree-item" :class="{ active: isActive }" @click="onClick">
      <span class="tree-indent" :style="{ width: depth * 16 + 'px' }"></span>

      <span v-if="item.type === 'dir'" class="tree-arrow" :class="{ open: expanded }">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </span>
      <span v-else class="tree-arrow-placeholder"></span>

      <!-- File icon -->
      <span v-if="item.type === 'file'" class="tree-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" :stroke="iconColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
      </span>
      <span v-else class="tree-icon folder-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
      </span>

      <!-- Rename input or name -->
      <input
        v-if="renaming"
        ref="renameInput"
        v-model="renameName"
        class="tree-rename-input"
        @keydown.enter="confirmRename"
        @keydown.escape="cancelRename"
        @blur="confirmRename"
      />
      <span v-else class="tree-name" :title="item.path">{{ item.name }}</span>
    </div>

    <!-- Hover action buttons -->
    <div v-show="hovered && !renaming" class="tree-actions">
      <!-- Folder: new file/folder dropdown -->
      <div v-if="item.type === 'dir'" class="tree-action-dropdown">
        <button class="btn-icon-sm" @click.stop="showCreateMenu = !showCreateMenu" title="新建">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
        <!-- Dropdown menu -->
        <div v-if="showCreateMenu" class="tree-create-menu" @mouseenter="hovered = true" @mouseleave="onMouseLeave">
          <button @click="createNewFile">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            新建文件
          </button>
          <button @click="createNewFolder">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            新建文件夹
          </button>
        </div>
      </div>
      <!-- Rename -->
      <button class="btn-icon-sm" @click.stop="startRename" title="重命名">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
      </button>
      <!-- Delete -->
      <button class="btn-icon-sm danger" @click.stop="deleteItem" title="删除">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
      </button>
    </div>
  </div>

  <!-- Children -->
  <div v-if="item.type === 'dir' && expanded" class="tree-children">
    <div v-if="loading" class="tree-loading">
      <svg class="spinner" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
      </svg>
    </div>
    <FileTreeItem
      v-for="child in item.children"
      :key="child.path"
      :item="child"
      :active-path="activePath"
      :depth="depth + 1"
      :project-id="projectId"
      @select="$emit('select', $event)"
      @refresh="$emit('refresh')"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { projectApi } from '../api'
import { normalizeFileTree } from '../utils/fileTree'

const props = defineProps({
  item: { type: Object, required: true },
  activePath: { type: String, default: null },
  depth: { type: Number, default: 0 },
  projectId: { type: String, required: true },
})

const emit = defineEmits(['select', 'refresh'])

const expanded = ref(false)
const loading = ref(false)
const hovered = ref(false)
const renaming = ref(false)
const renameName = ref('')
const showCreateMenu = ref(false)
const renameInput = ref(null)

const isActive = computed(() => props.activePath === props.item.path)

const iconColor = computed(() => {
  const ext = props.item.extension?.toLowerCase() || ''
  const colorMap = {
    '.py': '#3572A5', '.js': '#f1e05a', '.ts': '#3178c6', '.vue': '#41b883',
    '.html': '#e34c26', '.css': '#563d7c', '.json': '#292929', '.md': '#083fa1',
    '.yml': '#cb171e', '.yaml': '#cb171e', '.toml': '#9c4221', '.sql': '#e38c00',
    '.sh': '#89e051', '.java': '#b07219', '.go': '#00ADD8', '.rs': '#dea584',
  }
  return colorMap[ext] || 'var(--text-tertiary)'
})

function onMouseLeave() {
  if (!showCreateMenu.value) {
    hovered.value = false
  }
}

function onDocumentClick() {
  if (showCreateMenu.value) showCreateMenu.value = false
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onUnmounted(() => document.removeEventListener('click', onDocumentClick))

async function onClick() {
  if (props.item.type === 'dir') {
    expanded.value = !expanded.value
    if (expanded.value && props.item.children.length === 0) {
      loading.value = true
      try {
        const res = await projectApi.listFiles(props.projectId, props.item.path)
        props.item.children = normalizeFileTree(res.data)
      } catch (e) {
        console.error('Failed to load dir:', e)
      } finally {
        loading.value = false
      }
    }
  } else {
    emit('select', props.item.path)
  }
}

// -- Rename --
function startRename() {
  renaming.value = true
  renameName.value = props.item.name
  nextTick(() => {
    renameInput.value?.focus()
    const dot = renameName.value.lastIndexOf('.')
    if (dot > 0) renameInput.value?.setSelectionRange(0, dot)
    else renameInput.value?.select()
  })
}

async function confirmRename() {
  if (!renaming.value) return
  renaming.value = false
  const newName = renameName.value.trim()
  if (!newName || newName === props.item.name) return

  const parentDir = props.item.path.includes('/')
    ? props.item.path.substring(0, props.item.path.lastIndexOf('/'))
    : ''
  const newPath = parentDir ? `${parentDir}/${newName}` : newName

  try {
    await projectApi.renameFile(props.projectId, props.item.path, newPath)
    emit('refresh')
  } catch (e) {
    alert('重命名失败: ' + e.message)
  }
}

function cancelRename() {
  renaming.value = false
}

// -- Delete --
async function deleteItem() {
  const type = props.item.type === 'dir' ? '文件夹' : '文件'
  if (!confirm(`确定要删除${type}「${props.item.name}」吗？`)) return

  try {
    await projectApi.deleteFile(props.projectId, props.item.path)
    emit('refresh')
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

// -- Create (in folder) --
async function createNewFile() {
  showCreateMenu.value = false
  const name = prompt('文件名（例如 utils.py）')
  if (!name?.trim()) return
  const path = props.item.path ? `${props.item.path}/${name.trim()}` : name.trim()
  try {
    await projectApi.writeFile(props.projectId, path, '')
    emit('refresh')
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}

async function createNewFolder() {
  showCreateMenu.value = false
  const name = prompt('文件夹名称')
  if (!name?.trim()) return
  const path = props.item.path ? `${props.item.path}/${name.trim()}` : name.trim()
  try {
    await projectApi.mkdir(props.projectId, path)
    emit('refresh')
  } catch (e) {
    alert('创建失败: ' + e.message)
  }
}
</script>

<style scoped>
.tree-node {
  position: relative;
}

.tree-item {
  display: flex;
  align-items: center;
  padding: 3px 8px 3px 0;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
  transition: background 0.1s;
  user-select: none;
  white-space: nowrap;
}

.tree-item:hover {
  background: var(--bg-hover);
}

.tree-item.active {
  background: var(--accent-primary-light);
  color: var(--accent-primary);
}

.tree-indent {
  flex-shrink: 0;
  display: inline-block;
}

.tree-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  transition: transform 0.15s;
}

.tree-arrow.open {
  transform: rotate(90deg);
}

.tree-arrow svg {
  color: var(--text-tertiary);
}

.tree-arrow-placeholder {
  width: 16px;
  flex-shrink: 0;
}

.tree-icon {
  display: flex;
  align-items: center;
  margin-right: 4px;
  flex-shrink: 0;
}

.folder-icon svg {
  color: #f59e0b;
}

.tree-name {
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

/* -- Inline rename input -- */
.tree-rename-input {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-family: inherit;
  padding: 0 4px;
  border: 1px solid var(--accent-primary);
  border-radius: 3px;
  outline: none;
  background: var(--bg-primary);
  color: var(--text-primary);
  height: 20px;
  line-height: 20px;
}

/* -- Hover action buttons -- */
.tree-actions {
  position: absolute;
  right: 4px;
  top: 0;
  height: 26px;
  display: flex;
  align-items: center;
  gap: 1px;
  z-index: 10;
  background: linear-gradient(to right, transparent 4px, var(--bg-secondary) 12px);
  padding-left: 16px;
  padding-right: 2px;
  border-radius: 4px;
}

.btn-icon-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  flex-shrink: 0;
}

.btn-icon-sm:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-icon-sm.danger:hover {
  background: var(--danger-bg);
  color: var(--danger-color);
}

/* -- Create dropdown -- */
.tree-action-dropdown {
  position: relative;
}

.tree-create-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 2px;
  z-index: 100;
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  padding: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 130px;
}

.tree-create-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  border-radius: 4px;
  white-space: nowrap;
}

.tree-create-menu button:hover {
  background: var(--bg-hover);
}

.tree-create-menu button svg {
  flex-shrink: 0;
  color: var(--text-tertiary);
}

/* -- Children & loading -- */
.tree-children {
  /* no additional styles needed */
}

.tree-loading {
  padding: 4px 0 4px 40px;
  color: var(--text-tertiary);
}
</style>

<template>
  <div
    class="tree-node"
    :class="{ 'drag-over': isDragOver }"
    @mouseenter="hovered = true"
    @mouseleave="onMouseLeave"
    @dragover.prevent="onDragOver"
    @dragenter.prevent="onDragEnter"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <div
      class="tree-item"
      :class="{ active: isActive }"
      :draggable="true"
      @click="onClick"
      @dragstart="onDragStart"
      @dragend="onDragEnd"
    >
      <span class="tree-indent" :style="{ width: depth * 16 + 'px' }"></span>

      <span v-if="item.type === 'dir'" class="tree-arrow" :class="{ open: expanded }">
        <span v-html="icons.chevronRight" />
      </span>
      <span v-else class="tree-arrow-placeholder"></span>

      <!-- File icon -->
      <span v-if="item.type === 'file'" class="tree-icon" :style="{ color: iconColor }">
        <span v-html="icons.file" />
      </span>
      <span v-else class="tree-icon folder-icon">
        <span v-html="icons.folder" />
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
          <span v-html="icons.plus" />
        </button>
        <!-- Dropdown menu -->
        <div v-if="showCreateMenu" class="tree-create-menu" @mouseenter="hovered = true" @mouseleave="onMouseLeave">
          <button @click="createNewFile">
            <span v-html="icons.file" />
            新建文件
          </button>
          <button @click="createNewFolder">
            <span v-html="icons.folder" />
            新建文件夹
          </button>
        </div>
      </div>
      <!-- Rename -->
      <button class="btn-icon-sm" @click.stop="startRename" title="重命名">
        <span v-html="icons.edit" />
      </button>
      <!-- Delete -->
      <button class="btn-icon-sm danger" @click.stop="deleteItem" title="删除">
        <span v-html="icons.trash" />
      </button>
    </div>
  </div>

  <!-- Children -->
  <div v-if="item.type === 'dir' && expanded" class="tree-children">
    <div v-if="loading" class="tree-loading">
      <span class="spinner" v-html="icons.spinner" />
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
      @move="$emit('move', $event)"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { projectApi } from '../api'
import { normalizeFileTree } from '../utils/fileTree'
import { useModal } from '../composables/useModal'
import { useToast } from '../composables/useToast'
import { icons } from '../utils/icons'
import { getFileIconColor } from '../utils/fileUtils'

const props = defineProps({
  item: { type: Object, required: true },
  activePath: { type: String, default: null },
  depth: { type: Number, default: 0 },
  projectId: { type: String, required: true },
})

const emit = defineEmits(['select', 'refresh', 'move'])

const modal = useModal()
const toast = useToast()

const expanded = ref(false)
const loading = ref(false)
const hovered = ref(false)
const renaming = ref(false)
const renameName = ref('')
const showCreateMenu = ref(false)
const renameInput = ref(null)

const isActive = computed(() => props.activePath === props.item.path)

const iconColor = computed(() => {
  const ext = props.item.extension?.replace(/^\./, '').toLowerCase() || ''
  return getFileIconColor(ext)
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
    toast.success(`已重命名为「${newName}」`)
    emit('refresh')
  } catch (e) {
    toast.error('重命名失败: ' + e.message)
  }
}

function cancelRename() {
  renaming.value = false
}

// -- Delete --
async function deleteItem() {
  const type = props.item.type === 'dir' ? '文件夹' : '文件'
  const ok = await modal.confirm('删除确认', `确定要删除${type}「${props.item.name}」吗？`, { danger: true })
  if (!ok) return

  try {
    await projectApi.deleteFile(props.projectId, props.item.path)
    toast.success(`已删除「${props.item.name}」`)
    emit('refresh')
  } catch (e) {
    toast.error('删除失败: ' + e.message)
  }
}

// -- Create (in folder) --
async function createNewFile() {
  showCreateMenu.value = false
  const name = await modal.prompt('新建文件', '请输入文件名（例如 utils.py）')
  if (!name) return
  const path = props.item.path ? `${props.item.path}/${name}` : name
  try {
    await projectApi.writeFile(props.projectId, path, '')
    toast.success(`已创建「${name}」`)
    emit('refresh')
  } catch (e) {
    toast.error('创建失败: ' + e.message)
  }
}

async function createNewFolder() {
  showCreateMenu.value = false
  const name = await modal.prompt('新建文件夹', '请输入文件夹名称')
  if (!name) return
  const path = props.item.path ? `${props.item.path}/${name}` : name
  try {
    await projectApi.mkdir(props.projectId, path)
    toast.success(`已创建文件夹「${name}」`)
    emit('refresh')
  } catch (e) {
    toast.error('创建失败: ' + e.message)
  }
}

// -- Drag & Drop (move file/folder) --
const isDragOver = ref(false)
let dragCounter = 0

function onDragStart(e) {
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('application/json', JSON.stringify({
    path: props.item.path,
    name: props.item.name,
    type: props.item.type,
  }))
}

function onDragEnd() {
  isDragOver.value = false
  dragCounter = 0
}

function onDragOver(e) {
  if (props.item.type !== 'dir') return
  e.dataTransfer.dropEffect = 'move'
}

function onDragEnter() {
  if (props.item.type !== 'dir') return
  dragCounter++
  isDragOver.value = true
}

function onDragLeave() {
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragOver.value = false
  }
}

function onDrop(e) {
  isDragOver.value = false
  dragCounter = 0
  if (props.item.type !== 'dir') return

  try {
    const data = JSON.parse(e.dataTransfer.getData('application/json'))
    if (!data.path || data.path === props.item.path) return

    // Prevent moving a parent into its own child
    if (props.item.path.startsWith(data.path + '/')) {
      toast.error('不能将文件夹移动到其子文件夹内')
      return
    }

    emit('move', { srcPath: data.path, destDir: props.item.path, name: data.name })
  } catch (_) {}
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
.tree-loading {
  padding: 4px 0 4px 40px;
  color: var(--text-tertiary);
}

/* -- Drag & Drop -- */
.tree-node.drag-over > .tree-item {
  background: var(--accent-primary-light);
  outline: 2px dashed var(--accent-primary);
  outline-offset: -2px;
  border-radius: 4px;
}

.tree-item[draggable="true"] {
  cursor: grab;
}

.tree-item[draggable="true"]:active {
  cursor: grabbing;
}
</style>

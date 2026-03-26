<template>
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

    <span class="tree-name" :title="item.name">{{ item.name }}</span>
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
import { ref, computed } from 'vue'
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
</script>

<style scoped>
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
}

.tree-children {
  /* no extra indent, tree-item handles it via tree-indent */
}

.tree-loading {
  padding: 4px 0 4px 40px;
  color: var(--text-tertiary);
}
</style>

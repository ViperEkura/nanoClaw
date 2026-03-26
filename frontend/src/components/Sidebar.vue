<template>
  <aside class="sidebar">
    <!-- Project Selector -->
    <div class="project-section">
      <div class="project-selector" @click="showProjects = !showProjects">
        <div class="project-current">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>{{ currentProject?.name || '全部对话' }}</span>
        </div>
        <div class="project-selector-actions">
          <button
            v-if="currentProject"
            class="btn-clear-project"
            @click.stop="$emit('selectProject', null)"
            title="显示全部对话"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
          <svg 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            stroke-width="2"
            :style="{ transform: showProjects ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
    </div>

    <!-- Project Manager Panel -->
    <div v-if="showProjects" class="project-panel">
      <ProjectManager
        ref="projectManagerRef"
        :current-project="currentProject"
        @select="selectProject"
        @created="onProjectCreated"
        @deleted="onProjectDeleted"
      />
    </div>

    <div class="sidebar-header">
      <button class="btn-new" @click="$emit('create')">
        <span class="icon">+</span>
        <span>新对话</span>
      </button>
    </div>

    <div class="conversation-list" @scroll="onScroll">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: conv.id === currentId }"
        @click="$emit('select', conv.id)"
      >
        <div class="conv-info">
          <div class="conv-title">{{ conv.title || '新对话' }}</div>
          <div class="conv-meta">
            <span>{{ conv.message_count || 0 }} 条消息 · {{ formatTime(conv.updated_at) }}</span>
            <span v-if="!currentProject && conv.project_name" class="conv-project-badge">{{ conv.project_name }}</span>
          </div>
        </div>
        <button class="btn-delete" @click.stop="$emit('delete', conv.id)" title="删除">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>

      <div v-if="loading" class="loading-more">加载中...</div>
      <div v-if="!loading && conversations.length === 0" class="empty-hint">
        {{ currentProject ? '该项目暂无对话' : '暂无对话' }}
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { formatTime } from '../utils/format'
import ProjectManager from './ProjectManager.vue'

const props = defineProps({
  conversations: { type: Array, required: true },
  currentId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
  currentProject: { type: Object, default: null },
})

const emit = defineEmits(['select', 'create', 'delete', 'loadMore', 'selectProject'])

const showProjects = ref(false)
const projectManagerRef = ref(null)

function selectProject(project) {
  emit('selectProject', project)
  showProjects.value = false
}

function onProjectCreated(project) {
  // Auto-select newly created project
  emit('selectProject', project)
}

function onProjectDeleted(projectId) {
  // If deleted project is current, clear selection
  if (props.currentProject?.id === projectId) {
    emit('selectProject', null)
  }
}

function onScroll(e) {
  const el = e.target
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
    emit('loadMore')
  }
}
</script>

<style scoped>
.sidebar {
  width: 20%;
  min-width: 220px;
  max-width: 320px;
  flex-shrink: 0;
  background: color-mix(in srgb, var(--bg-primary) 75%, transparent);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border-right: 1px solid var(--border-medium);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.project-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
}

.project-selector {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.project-selector:hover {
  background: var(--bg-hover);
  border-color: var(--accent-primary);
}

.project-current {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 0;
}

.project-current span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-selector-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-clear-project {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
}

.btn-clear-project:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.project-panel {
  max-height: 300px;
  overflow-y: auto;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.sidebar-header {
  padding: 16px;
}

.btn-new {
  width: 100%;
  padding: 10px 16px;
  background: var(--accent-primary-light);
  border: 1px dashed var(--accent-primary);
  border-radius: 10px;
  color: var(--accent-primary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-new:hover {
  background: var(--accent-primary-medium);
  border-color: var(--accent-primary);
}

.btn-new .icon {
  font-size: 18px;
  font-weight: 300;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 16px;
}

.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb-sidebar);
  border-radius: 2px;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.conversation-item:hover {
  background: var(--bg-hover);
}

.conversation-item.active {
  background: var(--bg-active);
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.conv-project-badge {
  font-size: 11px;
  color: var(--accent-primary);
  opacity: 0.8;
  flex-shrink: 0;
  margin-left: 8px;
}

.btn-delete {
  opacity: 0;
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.15s;
  flex-shrink: 0;
}

.conversation-item:hover .btn-delete {
  opacity: 1;
}

.btn-delete:hover {
  color: var(--danger-color);
  background: var(--danger-bg);
}

.loading-more,
.empty-hint {
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 20px;
}
</style>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <button class="btn-new-project" @click="$emit('createProject')">
        <span class="icon">+</span>
        <span>新建项目</span>
      </button>
    </div>

    <div class="conversation-list" @scroll="onScroll">
      <!-- Project groups -->
      <div v-for="group in groupedData.groups" :key="group.id" class="project-group">
        <div class="project-header" @click="toggleGroup(group.id)">
          <svg class="chevron" :class="{ collapsed: !expandedGroups[group.id] }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
          <span class="project-name">{{ group.name }}</span>
          <span class="conv-count">{{ group.conversations.length }}</span>
          <button
            class="btn-group-action"
            title="新建对话"
            @click.stop="$emit('createInProject', { id: group.id, name: group.name })"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
          <button
            class="btn-group-action"
            title="浏览文件"
            @click.stop="$emit('browseProject', { id: group.id, name: group.name })"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </button>
          <button
            class="btn-group-action btn-delete-project"
            title="删除项目"
            @click.stop="$emit('deleteProject', { id: group.id, name: group.name })"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
        <div v-show="expandedGroups[group.id]">
          <div
            v-for="conv in group.conversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: conv.id === currentId }"
            @click="$emit('select', conv.id)"
          >
            <div class="conv-info">
              <div class="conv-title">{{ conv.title || '新对话' }}</div>
              <div class="conv-meta">
                <span>{{ conv.message_count || 0 }} 条消息 · {{ formatTime(conv.updated_at) }}</span>
              </div>
            </div>
            <button class="btn-delete" @click.stop="$emit('delete', conv.id)" title="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Standalone conversations (always visible) -->
      <div class="project-group">
        <div class="project-header" @click="toggleGroup('__standalone__')">
          <svg class="chevron" :class="{ collapsed: !expandedGroups['__standalone__'] }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
          <svg class="standalone-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span class="conv-count">{{ groupedData.standalone.length }}</span>
          <button
            class="btn-group-action"
            title="新建对话"
            @click.stop="$emit('createInProject', { id: null, name: null })"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
          <span class="btn-placeholder"></span>
          <span class="btn-placeholder"></span>
        </div>
        <div v-show="expandedGroups['__standalone__']">
          <div
            v-for="conv in groupedData.standalone"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: conv.id === currentId }"
            @click="$emit('select', conv.id)"
          >
            <div class="conv-info">
              <div class="conv-title">{{ conv.title || '新对话' }}</div>
              <div class="conv-meta">
                <span>{{ conv.message_count || 0 }} 条消息 · {{ formatTime(conv.updated_at) }}</span>
              </div>
            </div>
            <button class="btn-delete" @click.stop="$emit('delete', conv.id)" title="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="loading" class="loading-more">加载中...</div>
      <div v-if="!loading && conversations.length === 0" class="empty-hint">暂无对话</div>
    </div>

    <div class="sidebar-footer">
      <button class="btn-footer" title="使用统计" @click="$emit('toggleStats')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 20V10"/>
          <path d="M12 20V4"/>
          <path d="M6 20v-6"/>
        </svg>
      </button>
      <button class="btn-footer" title="设置" @click="$emit('toggleSettings')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { formatTime } from '../utils/format'

const props = defineProps({
  conversations: { type: Array, required: true },
  projects: { type: Array, default: () => [] },
  currentId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'delete', 'loadMore', 'createProject', 'browseProject', 'createInProject', 'toggleSettings', 'toggleStats', 'deleteProject'])

const expandedGroups = reactive({})

const groupedData = computed(() => {
  const groups = {}
  const standalone = []

  // First, initialize groups from projects list (includes projects with 0 conversations)
  for (const p of props.projects) {
    groups[p.id] = {
      id: p.id,
      name: p.name,
      conversations: [],
    }
  }

  // Then merge conversations into groups
  for (const conv of props.conversations) {
    if (conv.project_id) {
      if (!groups[conv.project_id]) {
        groups[conv.project_id] = {
          id: conv.project_id,
          name: conv.project_name || '未知项目',
          conversations: [],
        }
      }
      groups[conv.project_id].conversations.push(conv)
    } else {
      standalone.push(conv)
    }
  }

  for (const id of Object.keys(groups)) {
    if (!(id in expandedGroups)) expandedGroups[id] = true
  }
  if (!('__standalone__' in expandedGroups)) {
    expandedGroups['__standalone__'] = true
  }

  return { groups: Object.values(groups), standalone }
})

function toggleGroup(id) {
  expandedGroups[id] = !expandedGroups[id]
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

.sidebar-header {
  padding: 16px;
}

.btn-new-project {
  width: 100%;
  padding: 10px 16px;
  background: var(--accent-primary-light);
  border: 1px solid var(--accent-primary);
  border-radius: 10px;
  color: var(--accent-primary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-new-project:hover {
  background: var(--accent-primary-medium);
}

.btn-new-project .icon {
  font-size: 18px;
  font-weight: 300;
}




.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px 16px;
}

.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb-sidebar);
  border-radius: 2px;
}

.project-group {
  margin-bottom: 4px;
}

.project-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  border-radius: 10px;
  user-select: none;
  transition: background 0.15s;
}

.project-header:hover {
  background: var(--bg-hover);
}

.chevron {
  flex-shrink: 0;
  transition: transform 0.2s ease;
  color: var(--text-secondary);
}

.chevron.collapsed {
  transform: rotate(-90deg);
}

.project-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.standalone-icon {
  flex-shrink: 0;
  color: var(--text-secondary);
}

.btn-placeholder { width: 24px; flex-shrink: 0; }

.conv-count {
  font-size: 11px;
  color: var(--text-tertiary);
  flex-shrink: 0;
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
}

.btn-group-action {
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
  flex-shrink: 0;
  transition: all 0.15s;
  opacity: 0.5;
}

.project-header:hover .btn-group-action {
  opacity: 1;
}

.btn-group-action:hover {
  color: var(--accent-primary);
  background: var(--accent-primary-light);
  opacity: 1;
}

.btn-delete-project:hover {
  color: var(--danger-color);
  background: var(--danger-bg);
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 8px 12px 8px 36px;
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
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.btn-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s;
}

.btn-footer:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
</style>

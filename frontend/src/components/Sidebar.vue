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
          <span class="chevron" :class="{ collapsed: !expandedGroups[group.id] }" v-html="icons.chevronDown" />
          <span class="project-name">{{ group.name }}</span>
          <span class="conv-count">{{ group.conversations.length }}</span>
          <button
            class="ghost-btn"
            title="新建对话"
            @click.stop="$emit('createInProject', { id: group.id, name: group.name })"
          >
            <span v-html="icons.plus" />
          </button>
          <button
            class="ghost-btn"
            title="浏览文件"
            @click.stop="$emit('browseProject', { id: group.id, name: group.name })"
          >
            <span v-html="icons.folder" />
          </button>
          <button
            class="ghost-btn danger btn-delete-project"
            title="删除项目"
            @click.stop="$emit('deleteProject', { id: group.id, name: group.name })"
          >
            <span v-html="icons.trashSm" />
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
            <button class="ghost-btn danger btn-delete" @click.stop="$emit('delete', conv.id)" title="删除">
              <span v-html="icons.trash" />
            </button>
          </div>
        </div>
      </div>

      <!-- Standalone conversations (always visible) -->
      <div class="project-group">
        <div class="project-header" @click="toggleGroup('__standalone__')">
          <span class="chevron" :class="{ collapsed: !expandedGroups['__standalone__'] }" v-html="icons.chevronDown" />
          <span class="standalone-icon" v-html="icons.chat" />
          <span class="conv-count">{{ groupedData.standalone.length }}</span>
          <button
            class="ghost-btn"
            title="新建对话"
            @click.stop="$emit('createInProject', { id: null, name: null })"
          >
            <span v-html="icons.plus" />
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
            <button class="ghost-btn danger btn-delete" @click.stop="$emit('delete', conv.id)" title="删除">
              <span v-html="icons.trash" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="loading" class="loading-more">加载中...</div>
      <div v-if="!loading && conversations.length === 0" class="empty-hint">暂无对话</div>
    </div>

    <div class="sidebar-footer">
      <button class="btn-footer" title="使用统计" @click="$emit('toggleStats')">
        <span v-html="icons.stats" />
      </button>
      <button class="btn-footer" title="设置" @click="$emit('toggleSettings')">
        <span v-html="icons.settings" />
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { formatTime } from '../utils/format'
import { icons } from '../utils/icons'
import { INFINITE_SCROLL_THRESHOLD_PX } from '../constants'

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
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - INFINITE_SCROLL_THRESHOLD_PX) {
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
  line-height: 1;
  color: var(--text-tertiary);
  flex-shrink: 0;
  background: var(--bg-secondary);
  padding: 3px 6px;
  border-radius: 10px;
  margin-left: auto;
}

.btn-group-action {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  transition: all 0.15s;
  opacity: 0.5;
}

.project-header:hover .btn-group-action {
  opacity: 1;
}

.btn-delete-project:hover {
  color: var(--danger-color);
  background: var(--danger-bg);
  opacity: 1;
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
}

.conversation-item:hover .btn-delete {
  opacity: 1;
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
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: none;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-footer:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
</style>

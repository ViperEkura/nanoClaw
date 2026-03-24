<template>
  <aside class="sidebar">
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
        @contextmenu.prevent="onContextMenu($event, conv)"
      >
        <div class="conv-info">
          <div class="conv-title">{{ conv.title || '新对话' }}</div>
          <div class="conv-meta">
            {{ conv.message_count || 0 }} 条消息 · {{ formatTime(conv.updated_at) }}
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
        暂无对话
      </div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  conversations: { type: Array, required: true },
  currentId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'create', 'delete', 'loadMore'])

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function onScroll(e) {
  const el = e.target
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
    emit('loadMore')
  }
}

function onContextMenu(e, conv) {
  // right-click to delete
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  min-width: 280px;
  background: #1a1a2e;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.sidebar-header {
  padding: 16px;
}

.btn-new {
  width: 100%;
  padding: 10px 16px;
  background: rgba(79, 70, 229, 0.15);
  border: 1px dashed rgba(79, 70, 229, 0.4);
  border-radius: 10px;
  color: #a5b4fc;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-new:hover {
  background: rgba(79, 70, 229, 0.25);
  border-color: rgba(79, 70, 229, 0.6);
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
  background: rgba(255, 255, 255, 0.1);
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
  background: rgba(255, 255, 255, 0.05);
}

.conversation-item.active {
  background: rgba(79, 70, 229, 0.2);
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 14px;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.btn-delete {
  opacity: 0;
  background: none;
  border: none;
  color: #64748b;
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
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.loading-more,
.empty-hint {
  text-align: center;
  color: #475569;
  font-size: 13px;
  padding: 20px;
}
</style>

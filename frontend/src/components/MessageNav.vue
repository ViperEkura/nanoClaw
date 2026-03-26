<template>
  <Teleport to="body">
    <div v-if="messages.length > 0" class="bookmark-rail">
      <div
        v-for="(msg, idx) in messages"
        :key="msg.id"
        class="bookmark"
        :class="{ active: activeId === msg.id, user: msg.role === 'user' }"
        @click="$emit('scrollTo', msg.id)"
      >
        <div class="bookmark-dot"></div>
        <div class="bookmark-label">{{ msg.role === 'user' ? '用户' : 'Claw' }} · {{ preview(msg) }}</div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  messages: { type: Array, required: true },
  activeId: { type: String, default: null },
})

defineEmits(['scrollTo'])

function preview(msg) {
  if (!msg.text) return '...'
  const clean = msg.text.replace(/[#*`~>\-\[\]()]/g, '').replace(/\s+/g, ' ').trim()
  return clean.length > 60 ? clean.slice(0, 60) + '...' : clean
}
</script>

<style scoped>
.bookmark-rail {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 10px;
  height: 70vh;
  max-height: 400px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 0;
  transition: width 0.25s ease;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.bookmark-rail::-webkit-scrollbar {
  display: none;
}

.bookmark-rail:hover {
  width: 10vw;
  max-width: 160px;
}

.bookmark {
  position: relative;
  display: flex;
  align-items: center;
  padding: 5px 6px;
  cursor: pointer;
  border-radius: 0;
  white-space: nowrap;
  overflow: hidden;
  background: transparent;
  transition: background 0.15s;
}

.bookmark:hover {
  background: var(--bg-hover);
  border-radius: 6px 0 0 6px;
}

.bookmark.active {
  background: var(--bg-active);
  border-radius: 6px 0 0 6px;
}

.bookmark-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--text-tertiary);
  opacity: 0.35;
  transition: all 0.2s ease;
}

.bookmark.user .bookmark-dot {
  background: #3b82f6;
}

.bookmark.active .bookmark-dot,
.bookmark-rail:hover .bookmark-dot {
  opacity: 1;
  width: 6px;
  height: 6px;
}

.bookmark-label {
  margin-left: 8px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-secondary);
  opacity: 0;
  transform: translateX(8px);
  transition: all 0.2s ease;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bookmark-rail:hover .bookmark-label {
  opacity: 1;
  transform: translateX(0);
}

.bookmark.active .bookmark-label {
  color: var(--text-primary);
}
</style>

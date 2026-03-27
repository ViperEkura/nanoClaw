<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast-slide">
        <div v-for="t in toasts" :key="t.id" class="toast-item" :class="t.type">
          <span class="toast-icon" v-html="iconMap[t.type]" />
          <span class="toast-msg">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '../composables/useToast'
import { icons } from '../utils/icons'

const { toasts } = useToast()

const iconMap = {
  success: icons.check,
  error: icons.error,
  info: icons.info,
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  pointer-events: auto;
  border-left: 3px solid var(--border-light);
}

.toast-item.success { border-left-color: var(--success-color); }
.toast-item.error { border-left-color: var(--danger-color); }
.toast-item.info { border-left-color: var(--accent-primary); }

.toast-item.success .toast-icon { color: var(--success-color); }
.toast-item.error .toast-icon { color: var(--danger-color); }
.toast-item.info .toast-icon { color: var(--accent-primary); }

.toast-msg {
  color: var(--text-primary);
  line-height: 1.4;
}

.toast-slide-enter-active { transition: all 0.25s ease-out; }
.toast-slide-leave-active { transition: all 0.2s ease-in; }
.toast-slide-enter-from { transform: translateX(100%); opacity: 0; }
.toast-slide-leave-to { transform: translateX(60%); opacity: 0; }
</style>

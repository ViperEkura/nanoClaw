<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="state.visible" class="modal-overlay" @click.self="onCancel" @keydown.escape="onCancel">
        <div class="modal-dialog" role="dialog" :aria-modal="true">
          <h3 class="modal-title">{{ state.title }}</h3>
          <p class="modal-message">{{ state.message }}</p>

          <input
            v-if="state.type === 'prompt'"
            ref="inputRef"
            v-model="state.inputValue"
            class="modal-input"
            @keydown.enter="onOk"
            @keydown.escape="onCancel"
          />

          <div class="modal-actions">
            <button class="modal-btn" @click="onCancel">取消</button>
            <button
              class="modal-btn"
              :class="{ danger: state.danger }"
              @click="onOk"
            >确认</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useModal } from '../composables/useModal'

const { state, onOk, onCancel } = useModal()
const inputRef = ref(null)

watch(() => state.visible, (v) => {
  if (v) {
    nextTick(() => inputRef.value?.focus())
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-dialog {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 24px;
  width: 380px;
  max-width: 90vw;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}

.modal-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-message {
  margin: 0 0 16px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.modal-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-secondary);
  color: var(--text-primary);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.modal-input:focus {
  border-color: var(--accent-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.modal-btn {
  padding: 6px 16px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  background: var(--bg-secondary);
  color: var(--text-primary);
  transition: all 0.15s;
}

.modal-btn:hover {
  background: var(--bg-hover);
}

.modal-btn.danger {
  background: var(--danger-color);
  border-color: var(--danger-color);
  color: #fff;
}

.modal-btn.danger:hover {
  opacity: 0.85;
}



</style>

import { reactive } from 'vue'
import { TOAST_DEFAULT_DURATION } from '../constants'

const state = reactive({
  toasts: [],
  _id: 0,
})

export function useToast() {
  function add(type, message, duration = TOAST_DEFAULT_DURATION) {
    const id = ++state._id
    state.toasts.push({ id, type, message })
    setTimeout(() => {
      const idx = state.toasts.findIndex(t => t.id === id)
      if (idx !== -1) state.toasts.splice(idx, 1)
    }, duration)
  }

  return {
    toasts: state.toasts,
    success: (msg, dur) => add('success', msg, dur),
    error: (msg, dur) => add('error', msg, dur),
    info: (msg, dur) => add('info', msg, dur),
  }
}

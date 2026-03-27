import { reactive } from 'vue'

const state = reactive({
  visible: false,
  title: '',
  message: '',
  type: 'confirm', // 'confirm' | 'prompt'
  danger: false,
  inputValue: '',
  _resolve: null,
})

export function useModal() {
  function confirm(title, message, options = {}) {
    state.title = title
    state.message = message
    state.type = 'confirm'
    state.danger = options.danger || false
    state.visible = true
    return new Promise(resolve => { state._resolve = resolve })
  }

  function prompt(title, message, defaultValue = '') {
    state.title = title
    state.message = message
    state.type = 'prompt'
    state.danger = false
    state.inputValue = defaultValue
    state.visible = true
    return new Promise(resolve => { state._resolve = resolve })
  }

  function onOk() {
    if (state.type === 'prompt') {
      state._resolve?.(state.inputValue.trim())
    } else {
      state._resolve?.(true)
    }
    state.visible = false
  }

  function onCancel() {
    state._resolve?.(state.type === 'prompt' ? null : false)
    state.visible = false
  }

  return { state, confirm, prompt, onOk, onCancel }
}

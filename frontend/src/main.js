import { createApp } from 'vue'
import App from './App.vue'
import './styles/global.css'
import './styles/highlight.css'
import 'katex/dist/katex.min.css'
import { LS_KEY_THEME } from './constants'

// Initialize theme before app mounts to avoid flash when lazy-loading useTheme
const savedTheme = localStorage.getItem(LS_KEY_THEME)
if (savedTheme === 'dark' || savedTheme === 'light') {
  document.documentElement.setAttribute('data-theme', savedTheme)
}

createApp(App).mount('#app')

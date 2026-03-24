import { ref, watch } from 'vue'

const isDark = ref(false)

// 初始化时从 localStorage 读取
if (typeof window !== 'undefined') {
  const saved = localStorage.getItem('theme')
  isDark.value = saved === 'dark'
  applyTheme()
}

function applyTheme() {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  }
}

export function useTheme() {
  watch(isDark, (val) => {
    localStorage.setItem('theme', val ? 'dark' : 'light')
    applyTheme()
  })

  function toggleTheme() {
    isDark.value = !isDark.value
  }

  return {
    isDark,
    toggleTheme,
  }
}

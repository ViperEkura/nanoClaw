import { ref, watch } from 'vue'

const isDark = ref(false)

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

watch(isDark, (val) => {
  localStorage.setItem('theme', val ? 'dark' : 'light')
  applyTheme()
})

export function useTheme() {
  function toggleTheme() {
    isDark.value = !isDark.value
  }
  return { isDark, toggleTheme }
}

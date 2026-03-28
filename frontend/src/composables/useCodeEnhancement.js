import { watch, onMounted, nextTick, onUnmounted } from 'vue'
import { enhanceCodeBlocks } from '../utils/markdown'
import { CODE_ENHANCE_DEBOUNCE_MS } from '../constants'

/**
 * Composable for enhancing code blocks in a container element.
 * Automatically runs enhanceCodeBlocks on mount and when the dependency changes.
 *
 * @param {import('vue').Ref<HTMLElement|null>} templateRef - The ref to the container element
 * @param {import('vue').Ref<any>} [dep] - Optional reactive dependency to trigger re-enhancement
 * @param {import('vue').WatchOptions} [watchOpts] - Optional watch options (e.g. { deep: true })
 */
export function useCodeEnhancement(templateRef, dep, watchOpts) {
  let debounceTimer = null

  function enhance() {
    enhanceCodeBlocks(templateRef.value)
  }

  function debouncedEnhance() {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => nextTick(enhance), CODE_ENHANCE_DEBOUNCE_MS)
  }

  onMounted(enhance)
  onUnmounted(() => {
    if (debounceTimer) clearTimeout(debounceTimer)
  })

  if (dep) {
    watch(dep, () => nextTick(enhance), watchOpts)
  }

  return { enhance, debouncedEnhance }
}

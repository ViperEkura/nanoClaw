import { watch, onMounted, nextTick } from 'vue'
import { enhanceCodeBlocks } from '../utils/markdown'

/**
 * Composable for enhancing code blocks in a container element.
 * Automatically runs enhanceCodeBlocks on mount and when the dependency changes.
 *
 * @param {import('vue').Ref<HTMLElement|null>} templateRef - The ref to the container element
 * @param {import('vue').Ref<any>} [dep] - Optional reactive dependency to trigger re-enhancement
 * @param {import('vue').WatchOptions} [watchOpts] - Optional watch options (e.g. { deep: true })
 */
export function useCodeEnhancement(templateRef, dep, watchOpts) {
  function enhance() {
    enhanceCodeBlocks(templateRef.value)
  }

  onMounted(enhance)

  if (dep) {
    watch(dep, () => nextTick(enhance), watchOpts)
  }

  return { enhance }
}

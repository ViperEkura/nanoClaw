/**
 * File utility functions shared across FileExplorer, FileTreeItem, CodeEditor, etc.
 */

/** Common image extensions */
export const IMAGE_EXTS = new Set([
  'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico',
])

/**
 * Extract file extension from a path (without dot).
 * Returns '' if no extension found.
 */
export function getFileExtension(filepath) {
  if (!filepath) return ''
  const parts = filepath.split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
}

/** Check if a path has an image extension */
export function isImageFile(filepath) {
  return IMAGE_EXTS.has(getFileExtension(filepath))
}

/**
 * File icon color based on extension.
 * Returns a CSS color string.
 */
export function getFileIconColor(extension) {
  if (!extension) return 'var(--text-tertiary)'
  const colorMap = {
    py: '#3572A5', js: '#f1e05a', ts: '#3178c6', vue: '#41b883',
    html: '#e34c26', css: '#563d7c', json: '#292929', md: '#083fa1',
    yml: '#cb171e', yaml: '#cb171e', toml: '#9c4221', sql: '#e38c00',
    sh: '#89e051', java: '#b07219', go: '#00ADD8', rs: '#dea584',
  }
  return colorMap[extension.toLowerCase()] || 'var(--text-tertiary)'
}

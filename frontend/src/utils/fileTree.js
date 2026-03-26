/**
 * Normalize API listFiles response into a sorted tree item array.
 * Directories first, then files, alphabetically within each group.
 */
export function normalizeFileTree(data, { expanded = false } = {}) {
  const items = []
  for (const d of (data.directories || [])) {
    items.push({ name: d.name, path: d.path, type: 'dir', children: [], expanded })
  }
  for (const f of (data.files || [])) {
    items.push({ name: f.name, path: f.path, type: 'file', size: f.size, extension: f.extension })
  }
  items.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'dir' ? -1 : 1
    return a.name.localeCompare(b.name)
  })
  return items
}

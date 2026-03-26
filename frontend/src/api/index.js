const BASE = '/api'

// Cache for models list
let modelsCache = null

function buildQueryParams(params) {
  const sp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== '') sp.set(key, value)
  }
  const qs = sp.toString()
  return qs ? `?${qs}` : ''
}

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || 'Request failed')
  }
  return data
}

/**
 * Shared SSE stream processor - parses SSE events and dispatches to callbacks
 * @param {string} url - API URL (without BASE prefix)
 * @param {object} body - Request body
 * @param {object} callbacks - Event handlers: { onThinkingStart, onThinking, onMessage, onToolCalls, onToolResult, onProcessStep, onDone, onError }
 * @returns {{ abort: () => void }}
 */
function createSSEStream(url, body, { onThinkingStart, onThinking, onMessage, onToolCalls, onToolResult, onProcessStep, onDone, onError }) {
  const controller = new AbortController()

  const promise = (async () => {
    try {
      const res = await fetch(`${BASE}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.message || `HTTP ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            if (currentEvent === 'thinking_start' && onThinkingStart) {
              onThinkingStart()
            } else if (currentEvent === 'thinking' && onThinking) {
              onThinking(data.content)
            } else if (currentEvent === 'message' && onMessage) {
              onMessage(data.content)
            } else if (currentEvent === 'tool_calls' && onToolCalls) {
              onToolCalls(data.calls)
            } else if (currentEvent === 'tool_result' && onToolResult) {
              onToolResult(data)
            } else if (currentEvent === 'process_step' && onProcessStep) {
              onProcessStep(data)
            } else if (currentEvent === 'done' && onDone) {
              onDone(data)
            } else if (currentEvent === 'error' && onError) {
              onError(data.content)
            }
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError' && onError) {
        onError(e.message)
      }
    }
  })()

  promise.abort = () => controller.abort()
  return promise
}

export const modelApi = {
  list() {
    return request('/models')
  },

  // Get cached models or fetch from server
  async getCached() {
    if (modelsCache) {
      return { data: modelsCache }
    }

    // Try localStorage cache first
    const cached = localStorage.getItem('models_cache')
    if (cached) {
      try {
        modelsCache = JSON.parse(cached)
        return { data: modelsCache }
      } catch (_) {}
    }

    // Fetch from server
    const res = await this.list()
    modelsCache = res.data
    localStorage.setItem('models_cache', JSON.stringify(modelsCache))
    return res
  },

  // Clear cache (e.g., when models changed on server)
  clearCache() {
    modelsCache = null
    localStorage.removeItem('models_cache')
  }
}

export const statsApi = {
  getTokens(period = 'daily') {
    return request(`/stats/tokens${buildQueryParams({ period })}`)
  },
}

export const conversationApi = {
  list(cursor, limit = 20, projectId = null) {
    return request(`/conversations${buildQueryParams({ cursor, limit, project_id: projectId })}`)
  },

  create(payload = {}) {
    return request('/conversations', {
      method: 'POST',
      body: payload,
    })
  },

  get(id) {
    return request(`/conversations/${id}`)
  },

  update(id, payload) {
    return request(`/conversations/${id}`, {
      method: 'PATCH',
      body: payload,
    })
  },

  delete(id) {
    return request(`/conversations/${id}`, { method: 'DELETE' })
  },
}

export const messageApi = {
  list(convId, cursor, limit = 50) {
    return request(`/conversations/${convId}/messages${buildQueryParams({ cursor, limit })}`)
  },

  send(convId, data, callbacks) {
    return createSSEStream(`/conversations/${convId}/messages`, {
      text: data.text,
      attachments: data.attachments,
      stream: true,
      tools_enabled: callbacks.toolsEnabled !== false,
      project_id: data.projectId,
    }, callbacks)
  },

  delete(convId, msgId) {
    return request(`/conversations/${convId}/messages/${msgId}`, { method: 'DELETE' })
  },

  regenerate(convId, msgId, callbacks) {
    return createSSEStream(`/conversations/${convId}/regenerate/${msgId}`, {
      tools_enabled: callbacks.toolsEnabled !== false,
      project_id: callbacks.projectId,
    }, callbacks)
  },
}

export const projectApi = {
  list() {
    return request('/projects')
  },

  create(data) {
    return request('/projects', {
      method: 'POST',
      body: data,
    })
  },

  delete(projectId) {
    return request(`/projects/${projectId}`, { method: 'DELETE' })
  },

  uploadFolder(data) {
    const formData = new FormData()
    formData.append('name', data.name || '')
    formData.append('description', data.description || '')
    for (const file of data.files) {
      formData.append('files', file, file.webkitRelativePath)
    }
    return fetch(`${BASE}/projects/upload`, {
      method: 'POST',
      body: formData,
    }).then(async res => {
      let json
      try {
        json = await res.json()
      } catch (_) {
        throw new Error(`服务器错误 (${res.status})，请确认后端已重启`)
      }
      if (json.code !== 0) {
        throw new Error(json.message || 'Request failed')
      }
      return json
    })
  },

  listFiles(projectId, path = '') {
    return request(`/projects/${projectId}/files${buildQueryParams({ path })}`)
  },

  readFile(projectId, filepath) {
    return request(`/projects/${projectId}/files/${filepath}`)
  },

  readFileRaw(projectId, filepath) {
    return fetch(`${BASE}/projects/${projectId}/files/${filepath}`).then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res
    })
  },

  writeFile(projectId, filepath, content) {
    return request(`/projects/${projectId}/files/${filepath}`, {
      method: 'PUT',
      body: { content },
    })
  },

  deleteFile(projectId, filepath) {
    return request(`/projects/${projectId}/files/${filepath}`, { method: 'DELETE' })
  },

  mkdir(projectId, dirPath) {
    return request(`/projects/${projectId}/files/mkdir`, {
      method: 'POST',
      body: { path: dirPath },
    })
  },

  search(projectId, query, options = {}) {
    return request(`/projects/${projectId}/search`, {
      method: 'POST',
      body: { query, ...options },
    })
  },
}

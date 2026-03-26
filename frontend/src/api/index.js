const BASE = '/api'

// Cache for models list
let modelsCache = null

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
    return request(`/stats/tokens?period=${period}`)
  },
}

export const conversationApi = {
  list(cursor, limit = 20) {
    const params = new URLSearchParams()
    if (cursor) params.set('cursor', cursor)
    if (limit) params.set('limit', limit)
    return request(`/conversations?${params}`)
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
    const params = new URLSearchParams()
    if (cursor) params.set('cursor', cursor)
    if (limit) params.set('limit', limit)
    return request(`/conversations/${convId}/messages?${params}`)
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
  list(userId) {
    return request(`/projects?user_id=${userId}`)
  },

  create(data) {
    return request('/projects', {
      method: 'POST',
      body: data,
    })
  },

  get(projectId) {
    return request(`/projects/${projectId}`)
  },

  update(projectId, data) {
    return request(`/projects/${projectId}`, {
      method: 'PUT',
      body: data,
    })
  },

  delete(projectId) {
    return request(`/projects/${projectId}`, { method: 'DELETE' })
  },

  uploadFolder(data) {
    return request('/projects/upload', {
      method: 'POST',
      body: data,
    })
  },

  listFiles(projectId, path = '') {
    const params = path ? `?path=${encodeURIComponent(path)}` : ''
    return request(`/projects/${projectId}/files${params}`)
  },
}

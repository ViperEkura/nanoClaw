const BASE = '/api'

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

export const modelApi = {
  list() {
    return request('/models')
  },
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

  send(convId, content, { stream = true, onThinking, onMessage, onDone, onError } = {}) {
    if (!stream) {
      return request(`/conversations/${convId}/messages`, {
        method: 'POST',
        body: { content, stream: false },
      })
    }

    const controller = new AbortController()

    const promise = (async () => {
      try {
        const res = await fetch(`${BASE}/conversations/${convId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, stream: true }),
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
              if (currentEvent === 'thinking' && onThinking) {
                onThinking(data.content)
              } else if (currentEvent === 'message' && onMessage) {
                onMessage(data.content)
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
  },

  delete(convId, msgId) {
    return request(`/conversations/${convId}/messages/${msgId}`, { method: 'DELETE' })
  },
}

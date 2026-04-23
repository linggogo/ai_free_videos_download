import { getToken } from '../stores/user.js'

const API_BASE = '/api'

/** 构造带 Token 的请求头 */
function jsonHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * 解析视频链接
 * @param {string} url - 视频链接
 * @returns {Promise<Object>} 视频信息
 */
export async function parseVideo(url) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 65000) // 65s 客户端超时

  try {
    const res = await fetch(`${API_BASE}/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '解析失败' }))
      // 兼容 Pydantic 验证错误格式 (detail 可能是数组)
      const detail = Array.isArray(err.detail)
        ? err.detail.map(e => e.msg?.replace('Value error, ', '') || e.msg).join('; ')
        : err.detail
      throw new Error(detail || '解析失败，请检查链接是否正确')
    }
    return res.json()
  } catch (e) {
    clearTimeout(timeoutId)
    if (e.name === 'AbortError') {
      throw new Error('解析超时，请检查链接是否有效或稍后重试')
    }
    throw e
  }
}

/**
 * 开始下载视频
 * @param {string} url - 视频链接
 * @param {string} formatId - 格式 ID
 * @returns {Promise<Object>} { task_id, status }
 */
export async function startDownload(url, formatId) {
  const res = await fetch(`${API_BASE}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, format_id: formatId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '下载请求失败' }))
    throw new Error(err.detail || '下载请求失败')
  }
  return res.json()
}

/**
 * 监听下载进度 (SSE) - 支持自动重连
 * @param {string} taskId
 * @param {Function} onProgress - ({ progress, status, speed, eta }) => void
 * @param {Function} onComplete - () => void
 * @param {Function} onError - (error) => void
 * @returns {{ close: Function }} 可手动关闭
 */
export function watchProgress(taskId, onProgress, onComplete, onError) {
  let retries = 0
  const maxRetries = 3
  let evtSource = null
  let closed = false

  function connect() {
    if (closed) return
    evtSource = new EventSource(`${API_BASE}/progress/${taskId}`)

    evtSource.onmessage = (event) => {
      retries = 0 // 收到消息重置重试计数
      try {
        const data = JSON.parse(event.data)
        if (data.status === 'complete') {
          onComplete()
          evtSource.close()
          closed = true
        } else if (data.status === 'error') {
          onError(new Error(data.error || data.message || '下载出错'))
          evtSource.close()
          closed = true
        } else {
          onProgress(data)
        }
      } catch (e) {
        // ignore parse errors
      }
    }

    evtSource.onerror = () => {
      evtSource.close()
      if (closed) return
      if (retries < maxRetries) {
        retries++
        // 指数退避重连: 1s, 2s, 4s
        setTimeout(connect, 1000 * Math.pow(2, retries - 1))
      } else {
        onError(new Error('连接断开，请刷新页面重试'))
        closed = true
      }
    }
  }

  connect()

  return {
    close() {
      closed = true
      if (evtSource) evtSource.close()
    }
  }
}

/**
 * 获取文件下载 URL
 * @param {string} taskId
 * @returns {string}
 */
export function getFileUrl(taskId) {
  return `${API_BASE}/file/${taskId}`
}

/**
 * 提取视频字幕
 * @param {string} url - 视频链接
 * @returns {Promise<Object>} { available, language, source, segments, full_text }
 */
export async function fetchSubtitle(url) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 65000)

  try {
    const res = await fetch(`${API_BASE}/subtitle`, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ url }),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '字幕提取失败' }))
      // 创建错误对象并保留 detail 信息用于前端判断
      const error = new Error(typeof err.detail === 'object' ? err.detail.message || '字幕提取失败' : (err.detail || '字幕提取失败'))
      error.detail = err.detail
      throw error
    }
    return res.json()
  } catch (e) {
    clearTimeout(timeoutId)
    if (e.name === 'AbortError') {
      throw new Error('字幕提取超时，请稍后重试')
    }
    throw e
  }
}

/**
 * AI 视频总结（SSE 流式）
 * @param {string} title - 视频标题
 * @param {string} subtitleText - 字幕全文
 * @param {Function} onChunk - (text) => void 每次收到文本块
 * @param {Function} onDone - () => void 完成回调
 * @param {Function} onError - (error) => void 错误回调
 * @returns {{ close: Function }} 可手动关闭
 */
export function streamSummary(title, subtitleText, onChunk, onDone, onError) {
  let closed = false
  const controller = new AbortController()

  async function run() {
    try {
      const res = await fetch(`${API_BASE}/summarize`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({ title, subtitle_text: subtitleText }),
        signal: controller.signal,
      })

      if (!res.ok) {
        let errMsg = 'AI 总结失败'
        try {
          const err = await res.json()
          if (err.detail) {
            if (typeof err.detail === 'object') {
              errMsg = err.detail.message || 'AI 总结失败'
            } else {
              errMsg = err.detail
            }
          }
        } catch (_) {}
        const error = new Error(errMsg)
        error.detail = err?.detail
        throw error
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (!closed) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk') {
              onChunk(data.content)
            } else if (data.type === 'done') {
              if (onDone) onDone()
            } else if (data.type === 'error') {
              if (onError) onError(new Error(data.message))
            }
          } catch (_) { /* ignore parse errors */ }
        }
      }
    } catch (e) {
      if (!closed && onError) {
        onError(e)
      }
    }
  }

  run()

  return {
    close() {
      closed = true
      controller.abort()
    }
  }
}

/**
 * AI 视频问答（SSE 流式）
 * @param {string} title
 * @param {string} subtitleText
 * @param {Array} history - [{ role, content }]
 * @param {string} question
 * @param {Function} onChunk
 * @param {Function} onDone
 * @param {Function} onError
 * @returns {{ close: Function }}
 */
export function streamChat(title, subtitleText, history, question, onChunk, onDone, onError) {
  let closed = false
  const controller = new AbortController()

  async function run() {
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({
          title,
          subtitle_text: subtitleText,
          history,
          question,
        }),
        signal: controller.signal,
      })

      if (!res.ok) {
        let errMsg = 'AI 问答失败'
        try {
          const err = await res.json()
          if (err.detail) {
            if (typeof err.detail === 'object') {
              errMsg = err.detail.message || 'AI 问答失败'
            } else {
              errMsg = err.detail
            }
          }
        } catch (_) {}
        const error = new Error(errMsg)
        error.detail = err?.detail
        throw error
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (!closed) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk') {
              onChunk(data.content)
            } else if (data.type === 'done') {
              if (onDone) onDone()
            } else if (data.type === 'error') {
              if (onError) onError(new Error(data.message))
            }
          } catch (_) { /* ignore parse errors */ }
        }
      }
    } catch (e) {
      if (!closed && onError) {
        onError(e)
      }
    }
  }

  run()

  return {
    close() {
      closed = true
      controller.abort()
    }
  }
}

/**
 * 获取 AI 功能使用状态
 * @returns {Promise<Object>} { subtitle, summarize, chat, is_vip }
 */
export async function getUsageStatus() {
  const res = await fetch(`${API_BASE}/usage`, {
    method: 'GET',
    headers: jsonHeaders(),
  })
  if (!res.ok) {
    throw new Error('获取使用状态失败')
  }
  return res.json()
}

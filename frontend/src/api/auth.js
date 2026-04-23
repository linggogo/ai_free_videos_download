/**
 * 认证 API 封装
 */
import { getToken } from '../stores/user.js'

const API_BASE = '/api'

/**
 * 带 Token 的请求头
 */
function authHeaders() {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * 注册
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{token: string, user: object}>}
 */
export async function register(email, password) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '注册失败' }))
    const detail = Array.isArray(err.detail)
      ? err.detail.map(e => e.msg?.replace('Value error, ', '') || e.msg).join('; ')
      : err.detail
    throw new Error(detail || '注册失败')
  }
  return res.json()
}

/**
 * 登录
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{token: string, user: object}>}
 */
export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '登录失败' }))
    throw new Error(err.detail || '登录失败')
  }
  return res.json()
}

/**
 * 获取当前用户信息
 * @returns {Promise<{user: object, ai_usage: object}>}
 */
export async function getMe() {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    throw new Error('获取用户信息失败')
  }
  return res.json()
}

/**
 * 支付 API 封装
 */
import { getToken } from '../stores/user.js'

const API_BASE = '/api'

function authHeaders() {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  }
}

/**
 * 创建 Stripe Checkout Session
 * @returns {Promise<{checkout_url: string}>}
 */
export async function createCheckoutSession() {
  const res = await fetch(`${API_BASE}/payment/create-checkout-session`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '创建支付会话失败' }))
    throw new Error(err.detail || '创建支付会话失败')
  }
  return res.json()
}

/**
 * 创建 Stripe 客户门户 Session
 * @returns {Promise<{portal_url: string}>}
 */
export async function createPortalSession() {
  const res = await fetch(`${API_BASE}/payment/create-portal-session`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '创建门户会话失败' }))
    throw new Error(err.detail || '创建门户会话失败')
  }
  return res.json()
}

/**
 * 获取支付配置（价格信息等）
 * @returns {Promise<{publishable_key: string, price: string, currency: string, period: string}>}
 */
export async function getPaymentConfig() {
  const res = await fetch(`${API_BASE}/payment/config`)
  if (!res.ok) {
    throw new Error('获取支付配置失败')
  }
  return res.json()
}

/**
 * 验证 Checkout Session 支付状态并激活会员
 * @param {string} sessionId - Stripe Checkout Session ID
 * @returns {Promise<{activated: boolean, reason: string}>}
 */
export async function verifySession(sessionId) {
  const res = await fetch(`${API_BASE}/payment/verify-session`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ session_id: sessionId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '验证支付失败' }))
    throw new Error(err.detail || '验证支付失败')
  }
  return res.json()
}

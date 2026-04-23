/**
 * 用户状态管理（Vue3 reactive）
 * 全局单例，所有组件共享
 */
import { reactive, computed } from 'vue'

const TOKEN_KEY = 'saveany_token'

const state = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: null,       // { id, email, subscription_status, subscription_end_date, created_at }
  aiUsage: null,    // { used, limit, is_vip }
  loading: false,
})

// 计算属性
export const isLoggedIn = computed(() => !!state.token && !!state.user)
export const isVip = computed(() => state.user?.subscription_status === 'active')
export const userEmail = computed(() => state.user?.email || '')
export const aiUsage = computed(() => state.aiUsage)
export const userLoading = computed(() => state.loading)

/**
 * 设置 Token 并持久化
 */
export function setToken(token) {
  state.token = token
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

/**
 * 设置用户信息
 */
export function setUser(user, aiUsageData = null) {
  state.user = user
  if (aiUsageData) {
    state.aiUsage = aiUsageData
  }
}

/**
 * 登出
 */
export function logout() {
  state.token = ''
  state.user = null
  state.aiUsage = null
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 获取当前 Token（用于 API 请求）
 */
export function getToken() {
  return state.token
}

/**
 * 设置加载状态
 */
export function setLoading(val) {
  state.loading = val
}

/**
 * 更新 AI 使用量
 */
export function updateAiUsage(usage) {
  state.aiUsage = usage
}

export default state

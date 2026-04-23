<script setup>
import { ref, watch } from 'vue'
import { register, login } from '../api/auth.js'
import { setToken, setUser } from '../stores/user.js'

const props = defineProps({
  show: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'success'])

const mode = ref('login') // 'login' | 'register'
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

// 重置表单
watch(() => props.show, (val) => {
  if (val) {
    error.value = ''
    email.value = ''
    password.value = ''
    confirmPassword.value = ''
  }
})

async function handleSubmit() {
  error.value = ''

  // 前端校验
  if (!email.value.trim()) {
    error.value = '请输入邮箱'
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    error.value = '邮箱格式不正确'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码长度至少 6 位'
    return
  }
  if (mode.value === 'register' && password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    let data
    if (mode.value === 'register') {
      data = await register(email.value.trim(), password.value)
    } else {
      data = await login(email.value.trim(), password.value)
    }
    setToken(data.token)
    setUser(data.user)
    emit('success', data.user)
    emit('close')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="show" class="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')"></div>

        <!-- Modal -->
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div v-if="show" class="relative w-full max-w-md bg-dark-card border border-dark-border rounded-2xl shadow-2xl shadow-black/40 p-6 sm:p-8">
            <!-- Close button -->
            <button @click="$emit('close')" class="absolute top-4 right-4 text-text-muted hover:text-text-primary transition-colors cursor-pointer">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <!-- Title -->
            <div class="text-center mb-6">
              <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center mx-auto mb-4">
                <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0" />
                </svg>
              </div>
              <h2 class="text-xl font-bold text-text-primary">
                {{ mode === 'login' ? '欢迎回来' : '创建账号' }}
              </h2>
              <p class="text-sm text-text-secondary mt-1">
                {{ mode === 'login' ? '登录后畅享所有功能' : '注册即享每日 3 次免费 AI 功能' }}
              </p>
            </div>

            <!-- Tab Switch -->
            <div class="flex bg-dark-bg rounded-xl p-1 mb-6">
              <button
                @click="mode = 'login'; error = ''"
                class="flex-1 py-2 text-sm font-medium rounded-lg transition-all cursor-pointer"
                :class="mode === 'login' ? 'bg-dark-card text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'"
              >
                登录
              </button>
              <button
                @click="mode = 'register'; error = ''"
                class="flex-1 py-2 text-sm font-medium rounded-lg transition-all cursor-pointer"
                :class="mode === 'register' ? 'bg-dark-card text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'"
              >
                注册
              </button>
            </div>

            <!-- Form -->
            <form @submit.prevent="handleSubmit" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-text-secondary mb-1.5">邮箱</label>
                <input
                  v-model="email"
                  type="email"
                  placeholder="your@email.com"
                  class="w-full px-4 py-3 bg-dark-bg border border-dark-border rounded-xl text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent-blue/50 transition-colors"
                  :disabled="loading"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-text-secondary mb-1.5">密码</label>
                <input
                  v-model="password"
                  type="password"
                  placeholder="至少 6 位密码"
                  class="w-full px-4 py-3 bg-dark-bg border border-dark-border rounded-xl text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent-blue/50 transition-colors"
                  :disabled="loading"
                />
              </div>

              <div v-if="mode === 'register'">
                <label class="block text-sm font-medium text-text-secondary mb-1.5">确认密码</label>
                <input
                  v-model="confirmPassword"
                  type="password"
                  placeholder="再次输入密码"
                  class="w-full px-4 py-3 bg-dark-bg border border-dark-border rounded-xl text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent-blue/50 transition-colors"
                  :disabled="loading"
                />
              </div>

              <!-- Error -->
              <div v-if="error" class="flex items-center gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
                <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
                {{ error }}
              </div>

              <!-- Submit -->
              <button
                type="submit"
                :disabled="loading"
                class="w-full py-3 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-accent-blue to-accent-purple hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
              >
                <span v-if="loading" class="flex items-center justify-center gap-2">
                  <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  {{ mode === 'login' ? '登录中...' : '注册中...' }}
                </span>
                <span v-else>{{ mode === 'login' ? '登录' : '注册' }}</span>
              </button>
            </form>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

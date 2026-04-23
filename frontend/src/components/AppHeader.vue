<script setup>
import { ref } from 'vue'
import { isLoggedIn, isVip, userEmail, logout } from '../stores/user.js'
import { createCheckoutSession, createPortalSession } from '../api/payment.js'

const emit = defineEmits(['showAuth'])

const mobileMenuOpen = ref(false)
const upgradeLoading = ref(false)

const navItems = [
  { label: '功能特性', href: '#features' },
  { label: '套餐价格', href: '#pricing' },
  { label: '支持平台', href: '#platforms' },
]

async function handleUpgrade() {
  if (!isLoggedIn.value) {
    emit('showAuth')
    return
  }
  upgradeLoading.value = true
  try {
    const { checkout_url } = await createCheckoutSession()
    window.location.href = checkout_url
  } catch (e) {
    alert(e.message)
  } finally {
    upgradeLoading.value = false
  }
}

async function handleManageSubscription() {
  try {
    const { portal_url } = await createPortalSession()
    window.location.href = portal_url
  } catch (e) {
    alert(e.message)
  }
}

function handleLogout() {
  logout()
}
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 border-b border-dark-border/50 backdrop-blur-xl bg-dark-bg/80">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </div>
          <span class="text-xl font-bold text-text-primary">SaveAny</span>
          <span class="hidden sm:inline-block text-xs px-2 py-0.5 rounded-full bg-accent-blue/10 text-accent-blue border border-accent-blue/20">万能视频下载</span>
        </div>

        <!-- Desktop Nav -->
        <nav class="hidden md:flex items-center gap-8" aria-label="主导航">
          <a v-for="item in navItems" :key="item.label" :href="item.href"
             class="text-sm text-text-secondary hover:text-text-primary transition-colors">
            {{ item.label }}
          </a>
        </nav>

        <!-- CTA / User Area -->
        <div class="hidden md:flex items-center gap-3">
          <template v-if="!isLoggedIn">
            <button
              @click="$emit('showAuth')"
              class="px-4 py-2 rounded-full text-sm font-medium text-text-secondary hover:text-text-primary border border-dark-border hover:border-accent-blue/30 transition-all cursor-pointer"
            >
              登录
            </button>
            <button
              @click="handleUpgrade"
              class="px-5 py-2 rounded-full text-sm font-medium border border-accent-purple/40 text-accent-purple hover:bg-accent-purple/10 transition-all cursor-pointer"
            >
              ☆ 开通 VIP
            </button>
          </template>
          <template v-else-if="isVip">
            <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 text-xs font-semibold text-amber-400">
              <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
              VIP
            </span>
            <button
              @click="handleManageSubscription"
              class="text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
            >
              管理订阅
            </button>
            <button
              @click="handleLogout"
              class="text-sm text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
              title="登出"
            >
              {{ userEmail.split('@')[0] }}
            </button>
          </template>
          <template v-else>
            <button
              @click="handleUpgrade"
              :disabled="upgradeLoading"
              class="px-5 py-2 rounded-full text-sm font-medium border border-accent-purple/40 text-accent-purple hover:bg-accent-purple/10 transition-all cursor-pointer disabled:opacity-50"
            >
              {{ upgradeLoading ? '跳转中...' : '☆ 升级 VIP' }}
            </button>
            <button
              @click="handleLogout"
              class="text-sm text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
              title="登出"
            >
              {{ userEmail.split('@')[0] }}
            </button>
          </template>
        </div>

        <!-- Mobile Menu Button -->
        <button @click="mobileMenuOpen = !mobileMenuOpen" class="md:hidden p-2 text-text-secondary">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path v-if="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Menu -->
    <div v-if="mobileMenuOpen" class="md:hidden border-t border-dark-border/50 bg-dark-bg/95 backdrop-blur-xl">
      <div class="px-4 py-4 space-y-3">
        <a v-for="item in navItems" :key="item.label" :href="item.href"
           class="block text-sm text-text-secondary hover:text-text-primary py-2">
          {{ item.label }}
        </a>
        <div class="pt-3 border-t border-dark-border/50 space-y-2">
          <template v-if="!isLoggedIn">
            <button @click="$emit('showAuth'); mobileMenuOpen = false" class="block w-full text-left text-sm text-text-secondary hover:text-text-primary py-2 cursor-pointer">
              登录 / 注册
            </button>
          </template>
          <template v-else>
            <div class="text-sm text-text-muted py-1">{{ userEmail }}</div>
            <button v-if="isVip" @click="handleManageSubscription" class="block text-sm text-amber-400 py-2 cursor-pointer">管理订阅</button>
            <button v-else @click="handleUpgrade" class="block text-sm text-accent-purple py-2 cursor-pointer">升级 VIP</button>
            <button @click="handleLogout; mobileMenuOpen = false" class="block text-sm text-red-400 py-2 cursor-pointer">退出登录</button>
          </template>
        </div>
      </div>
    </div>
  </header>
</template>

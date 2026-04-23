<script setup>
import { ref } from 'vue'
import { isLoggedIn, isVip } from '../stores/user.js'
import { createCheckoutSession } from '../api/payment.js'

const emit = defineEmits(['showAuth'])
const upgradeLoading = ref(false)

const plans = [
  {
    name: '免费版',
    price: '¥0',
    unit: '',
    desc: '基础功能，轻松体验',
    featured: false,
    ctaFree: true,
    features: [
      { text: '视频下载无限制', included: true },
      { text: '支持全部平台', included: true },
      { text: 'AI 总结每日 3 次', included: true },
      { text: 'AI 问答每日 10 次', included: true },
      { text: '字幕提取每日 3 次', included: true },
      { text: 'AI 思维导图每日 3 次', included: true },
    ]
  },
  {
    name: '专业版',
    price: '¥19.9',
    unit: '/月',
    desc: '所有功能，无限使用',
    featured: true,
    ctaFree: false,
    features: [
      { text: '视频下载无限制', included: true },
      { text: '支持全部平台', included: true },
      { text: 'AI 总结无限使用', included: true },
      { text: 'AI 问答无限使用', included: true },
      { text: '字幕提取无限使用', included: true },
      { text: 'AI 思维导图无限使用', included: true },
    ]
  }
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
</script>

<template>
  <section id="pricing" class="py-20 px-4" aria-labelledby="pricing-heading">
    <div class="max-w-4xl mx-auto">
      <div class="text-center mb-14">
        <h2 id="pricing-heading" class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">简单透明的 <span class="gradient-text">定价</span></h2>
        <p class="text-text-secondary">免费体验核心功能，升级解锁无限可能</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
        <div v-for="(plan, i) in plans" :key="i"
             class="relative p-8 rounded-2xl border transition-all"
             :class="plan.featured
               ? 'bg-gradient-to-b from-accent-blue/10 to-dark-card border-accent-blue/40 scale-[1.02]'
               : 'bg-dark-card border-dark-border hover:border-dark-border'">
          <!-- Popular Badge -->
          <div v-if="plan.featured" class="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-accent-blue to-accent-purple rounded-full text-xs font-semibold text-white">
            最受欢迎
          </div>

          <div class="text-center mb-6">
            <h3 class="text-lg font-bold text-text-primary mb-2">{{ plan.name }}</h3>
            <div class="flex items-baseline justify-center gap-1">
              <span class="text-4xl font-black" :class="plan.featured ? 'gradient-text' : 'text-text-primary'">{{ plan.price }}</span>
              <span v-if="plan.unit" class="text-sm text-text-muted">{{ plan.unit }}</span>
            </div>
            <p class="text-sm text-text-secondary mt-2">{{ plan.desc }}</p>
          </div>

          <ul class="space-y-3 mb-8">
            <li v-for="(feat, j) in plan.features" :key="j" class="flex items-center gap-2 text-sm">
              <svg class="w-4 h-4 shrink-0 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <span class="text-text-secondary">{{ feat.text }}</span>
            </li>
          </ul>

          <!-- 免费版按钮 -->
          <button v-if="plan.ctaFree"
            class="w-full py-3 rounded-xl text-sm font-semibold transition-all bg-dark-hover border border-dark-border text-text-secondary"
            disabled>
            {{ isVip ? '已是会员' : isLoggedIn ? '当前使用中' : '免费使用' }}
          </button>
          <!-- 专业版按钮 -->
          <button v-else
            @click="handleUpgrade"
            :disabled="upgradeLoading || isVip"
            class="w-full py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            :class="isVip
              ? 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400'
              : 'bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:from-blue-500 hover:to-purple-500'">
            {{ isVip ? '✓ 已是会员' : upgradeLoading ? '跳转中...' : '立即升级' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

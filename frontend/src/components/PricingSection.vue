<template>
  <section id="pricing" class="py-20 px-4">
    <div class="max-w-5xl mx-auto">
      <div class="text-center mb-14">
        <h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">简单透明的 <span class="gradient-text">定价</span></h2>
        <p class="text-text-secondary">免费体验核心功能，升级解锁无限可能</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div v-for="(plan, i) in plans" :key="i"
             class="relative p-6 rounded-2xl border transition-all"
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
              <svg class="w-4 h-4 shrink-0" :class="feat.included ? 'text-emerald-400' : 'text-text-muted'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path v-if="feat.included" stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                <path v-else stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span :class="feat.included ? 'text-text-secondary' : 'text-text-muted'">{{ feat.text }}</span>
            </li>
          </ul>

          <button
            class="w-full py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer"
            :class="plan.featured
              ? 'bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:from-blue-500 hover:to-purple-500'
              : 'bg-dark-hover border border-dark-border text-text-secondary hover:text-text-primary'">
            {{ plan.cta }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const plans = [
  {
    name: '免费版',
    price: '¥0',
    unit: '',
    desc: '基础下载，轻松体验',
    featured: false,
    cta: '当前使用中',
    features: [
      { text: '每日 5 次下载', included: true },
      { text: '最高 720p 清晰度', included: true },
      { text: '支持主流平台', included: true },
      { text: '批量下载', included: false },
      { text: 'AI 视频总结', included: false },
      { text: '字幕翻译', included: false },
    ]
  },
  {
    name: '专业版',
    price: '¥29',
    unit: '/月',
    desc: '解锁高清，无限下载',
    featured: true,
    cta: '立即升级',
    features: [
      { text: '无限次下载', included: true },
      { text: '最高 4K 清晰度', included: true },
      { text: '支持全部平台', included: true },
      { text: '批量下载 (最多10个)', included: true },
      { text: 'AI 视频总结', included: true },
      { text: '字幕翻译', included: false },
    ]
  },
  {
    name: '旗舰版',
    price: '¥69',
    unit: '/月',
    desc: '全部功能，极致体验',
    featured: false,
    cta: '联系我们',
    features: [
      { text: '无限次下载', included: true },
      { text: '最高 8K 清晰度', included: true },
      { text: '支持全部平台', included: true },
      { text: '无限批量下载', included: true },
      { text: 'AI 视频总结', included: true },
      { text: '字幕翻译', included: true },
    ]
  }
]
</script>

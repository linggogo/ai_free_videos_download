<script setup>
defineProps({
  loading: { type: Boolean, default: false }
})
</script>

<template>
  <section class="pt-32 pb-16 px-4 relative overflow-hidden">
    <!-- Background glow orbs -->
    <div class="absolute top-20 left-1/4 w-96 h-96 bg-accent-blue/5 rounded-full blur-3xl"></div>
    <div class="absolute top-40 right-1/4 w-80 h-80 bg-accent-purple/5 rounded-full blur-3xl"></div>

    <div class="max-w-4xl mx-auto text-center relative z-10">
      <!-- Badge -->
      <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent-blue/10 border border-accent-blue/20 mb-8">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-glow"></span>
        <span class="text-sm text-accent-blue font-medium">支持 1800+ 平台，AI 视频总结，永久免费使用</span>
      </div>

      <!-- Title -->
      <h1 class="text-4xl sm:text-5xl lg:text-6xl font-black leading-tight mb-6">
        <span class="text-text-primary">万能视频下载器，</span>
        <span class="gradient-text">一键下载 · AI 总结</span>
      </h1>

      <!-- Subtitle -->
      <p class="text-base sm:text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed mb-10">
        粘贴视频链接，智能解析下载，AI 自动总结视频内容。YouTube、Bilibili、抖音、TikTok...
        <br class="hidden sm:block" />
        视频下载 + AI 总结 + 字幕提取，一个工具全搞定
      </p>

      <!-- URL Input slot -->
      <slot />
    </div>
  </section>
</template>

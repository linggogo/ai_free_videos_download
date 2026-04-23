<template>
  <section id="faq" class="py-20 px-4" aria-labelledby="faq-heading">
    <div class="max-w-4xl mx-auto">
      <!-- Section Title -->
      <div class="text-center mb-14">
        <h2 id="faq-heading" class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">常见问题</h2>
        <p class="text-text-secondary max-w-xl mx-auto">关于 SaveAny 万能视频下载器的常见问题解答</p>
      </div>

      <!-- FAQ List -->
      <div class="space-y-4" role="list">
        <details
          v-for="(item, i) in faqs"
          :key="i"
          class="group rounded-2xl bg-dark-card border border-dark-border hover:border-accent-blue/30 transition-all duration-300"
          role="listitem"
        >
          <summary class="flex items-center justify-between gap-4 px-6 py-5 cursor-pointer select-none list-none">
            <h3 class="text-base font-semibold text-text-primary text-left">{{ item.q }}</h3>
            <svg
              class="w-5 h-5 shrink-0 text-text-muted transition-transform duration-300 group-open:rotate-180"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </summary>
          <div class="px-6 pb-5 pt-0">
            <p class="text-sm text-text-secondary leading-relaxed">{{ item.a }}</p>
          </div>
        </details>
      </div>
    </div>
  </section>
</template>

<script setup>
const faqs = [
  {
    q: '如何免费下载 YouTube 视频？',
    a: '打开 SaveAny 网站（saveany.com），在输入框中粘贴 YouTube 视频链接，点击解析按钮，系统会自动获取视频信息并展示所有可用的下载格式（4K/1080p/720p 等），选择需要的格式点击下载即可。全程免费，无需注册。'
  },
  {
    q: 'SaveAny 支持哪些视频平台？',
    a: 'SaveAny 基于 yt-dlp 开源引擎，支持 YouTube、Bilibili（B站）、抖音、TikTok、Twitter/X、Instagram、Twitch、快手、Vimeo、小红书等 1800+ 视频平台，几乎涵盖全球所有主流视频网站。'
  },
  {
    q: '如何使用 AI 视频总结功能？',
    a: '解析视频后，在视频信息下方会出现 AI 分析面板，点击"总结摘要"标签页，系统会自动提取视频字幕并调用 AI 生成结构化总结，包括视频概述、内容大纲、关键要点和一句话总结。'
  },
  {
    q: 'SaveAny 和其他视频下载工具有什么区别？',
    a: 'SaveAny 最大的差异化优势是集成了 AI 能力。除了视频下载外，还提供 AI 视频总结、思维导图生成、字幕提取和 AI 问答功能。用户不仅可以下载视频，还能快速了解视频内容、生成学习笔记。同时支持 1800+ 平台，覆盖范围远超同类工具。'
  },
  {
    q: '下载的视频支持哪些格式和分辨率？',
    a: '支持 MP4 视频和 MP3 音频格式。分辨率最高支持 4K（2160p），同时提供 1080p、720p、480p 等多种选择，还支持"最佳画质"合并下载模式（自动合并最高质量的视频流和音频流）。'
  },
  {
    q: '手机上可以使用 SaveAny 吗？',
    a: '可以。SaveAny 采用响应式设计，在手机、平板、电脑上都可以正常使用。无需安装任何 APP，直接在手机浏览器中打开 saveany.com 即可使用全部功能。'
  },
  {
    q: 'SaveAny 是否需要注册或付费？',
    a: '不需要。SaveAny 基础功能完全免费，无需注册账号、无需登录、无需付费。打开网页即可直接使用视频下载、AI 总结、字幕提取等全部功能。'
  },
  {
    q: '如何提取视频字幕？',
    a: '解析视频后，在 AI 分析面板中点击"字幕文本"标签页，系统会自动提取视频字幕。支持人工字幕和 AI 自动字幕两种类型，字幕带时间戳展示，方便定位视频内容。'
  }
]
</script>

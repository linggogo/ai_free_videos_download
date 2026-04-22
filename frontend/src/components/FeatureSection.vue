<template>
  <section id="features" class="py-20 px-4" aria-labelledby="features-heading">
    <div class="max-w-6xl mx-auto">
      <!-- Section Title -->
      <div class="text-center mb-14">
        <h2 id="features-heading" class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">为什么选择 <span class="gradient-text">SaveAny</span></h2>
        <p class="text-text-secondary max-w-xl mx-auto">极速、安全、无限制，一个工具搞定所有平台视频下载与 AI 总结</p>
      </div>

      <!-- Feature Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" role="list">
        <article v-for="(feature, i) in features" :key="i"
             class="group p-6 rounded-2xl bg-dark-card border border-dark-border hover:border-accent-blue/30 transition-all duration-300"
             role="listitem"
             :aria-label="feature.title + ' - ' + feature.desc">
          <div class="w-12 h-12 rounded-xl mb-4 flex items-center justify-center text-2xl"
               :class="feature.bgClass"
               role="img"
               :aria-label="feature.iconLabel">
            {{ feature.icon }}
          </div>
          <h3 class="text-lg font-semibold text-text-primary mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-text-secondary leading-relaxed">{{ feature.desc }}</p>
        </article>
      </div>

      <!-- Supported Platforms -->
      <div id="platforms" class="mt-20 text-center" aria-labelledby="platforms-heading">
        <h3 id="platforms-heading" class="text-xl font-bold text-text-primary mb-8">支持的视频平台</h3>
        <div class="flex flex-wrap justify-center gap-4" role="list">
          <div v-for="platform in platforms" :key="platform.name"
               class="flex items-center gap-2 px-5 py-2.5 rounded-full bg-dark-card border border-dark-border text-sm text-text-secondary hover:border-accent-blue/30 hover:text-text-primary transition-all"
               role="listitem">
            <span class="text-lg" role="img" :aria-label="platform.name + '图标'">{{ platform.icon }}</span>
            {{ platform.name }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const features = [
  { icon: '⚡', iconLabel: '快速解析', title: '极速解析', desc: '粘贴链接，秒级获取视频信息和所有可用格式，无需等待', bgClass: 'bg-amber-500/10' },
  { icon: '🎬', iconLabel: '多清晰度下载', title: '多清晰度下载', desc: '支持 4K、1080p、720p 等多种分辨率视频下载，自由选择画质', bgClass: 'bg-blue-500/10' },
  { icon: '🌍', iconLabel: '多平台支持', title: '1800+ 平台', desc: '覆盖全球主流视频平台，YouTube、B站、抖音、TikTok 一网打尽', bgClass: 'bg-emerald-500/10' },
  { icon: '🤖', iconLabel: 'AI视频总结', title: 'AI 视频总结', desc: 'AI 自动提取字幕并生成结构化总结、思维导图，快速掌握视频要点', bgClass: 'bg-violet-500/10' },
  { icon: '📱', iconLabel: '移动端适配', title: '移动端适配', desc: '响应式设计，手机、平板随时随地下载视频，无需安装 APP', bgClass: 'bg-purple-500/10' },
  { icon: '🎵', iconLabel: '音频提取', title: '音频提取', desc: '支持提取视频音轨，MP3 格式直接保存，追歌利器', bgClass: 'bg-pink-500/10' },
  { icon: '📝', iconLabel: '字幕提取', title: '字幕提取', desc: '自动提取视频字幕，支持人工字幕和 AI 自动字幕，带时间戳展示', bgClass: 'bg-teal-500/10' },
  { icon: '🔒', iconLabel: '安全隐私', title: '安全隐私', desc: '不存储任何用户数据和下载记录，文件自动定期清理', bgClass: 'bg-cyan-500/10' },
]

const platforms = [
  { icon: '▶️', name: 'YouTube' },
  { icon: '📺', name: 'Bilibili' },
  { icon: '🎵', name: '抖音' },
  { icon: '🎶', name: 'TikTok' },
  { icon: '🐦', name: 'Twitter/X' },
  { icon: '📷', name: 'Instagram' },
  { icon: '🎮', name: 'Twitch' },
  { icon: '📌', name: '快手' },
  { icon: '🎥', name: 'Vimeo' },
  { icon: '📰', name: '小红书' },
]
</script>

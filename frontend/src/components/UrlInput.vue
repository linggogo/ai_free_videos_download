<script setup>
const emit = defineEmits(['submit'])
const props = defineProps({
  loading: { type: Boolean, default: false }
})

import { ref } from 'vue'
const url = ref('')

const quickLinks = [
  { label: 'YouTube', placeholder: 'youtube.com/watch?v=...' },
  { label: 'Bilibili', placeholder: 'bilibili.com/video/BV...' },
  { label: 'Twitter/X', placeholder: 'x.com/.../status/...' },
  { label: '抖音', placeholder: 'douyin.com/video/...' },
]

function handleSubmit() {
  if (url.value.trim()) {
    emit('submit', url.value.trim())
  }
}

function fillExample(placeholder) {
  url.value = 'https://' + placeholder
}
</script>

<template>
  <div class="w-full max-w-3xl mx-auto">
    <!-- Input Bar -->
    <form @submit.prevent="handleSubmit" class="relative group">
      <!-- Glow effect behind -->
      <div class="absolute -inset-1 bg-gradient-to-r from-accent-blue/20 via-accent-purple/20 to-accent-cyan/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

      <div class="relative flex items-center bg-dark-card border border-dark-border rounded-2xl px-4 py-2 focus-within:border-accent-blue/50 transition-colors">
        <!-- Link Icon -->
        <svg class="w-5 h-5 text-text-muted mr-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m9.86-2.052a4.5 4.5 0 00-1.242-7.244l-4.5-4.5a4.5 4.5 0 00-6.364 6.364L4.34 8.586" />
        </svg>

        <input
          v-model="url"
          type="text"
          placeholder="粘贴视频链接，支持 YouTube、B站、抖音、TikTok..."
          aria-label="输入视频链接进行解析下载"
          class="flex-1 bg-transparent text-text-primary placeholder-text-muted text-sm sm:text-base outline-none py-2"
          :disabled="loading"
        />

        <button
          type="submit"
          :disabled="!url.trim() || loading"
          class="ml-2 sm:ml-3 px-4 sm:px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-accent-blue to-accent-purple hover:from-blue-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0 cursor-pointer"
        >
          <span v-if="loading" class="flex items-center gap-2">
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            解析中...
          </span>
          <span v-else class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            解析视频
          </span>
        </button>
      </div>
    </form>

    <!-- Quick Links -->
    <div class="flex items-center justify-center gap-2 mt-4 flex-wrap">
      <span class="text-xs text-text-muted">试试：</span>
      <button
        v-for="link in quickLinks"
        :key="link.label"
        @click="fillExample(link.placeholder)"
        class="text-xs px-3 py-1 rounded-full border border-dark-border text-text-secondary hover:text-accent-blue hover:border-accent-blue/30 transition-colors cursor-pointer"
      >
        {{ link.label }}
      </button>
    </div>
  </div>
</template>

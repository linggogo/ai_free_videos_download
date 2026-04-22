<script setup>
import { ref } from 'vue'

const mobileMenuOpen = ref(false)

const navItems = [
  { label: '功能特性', href: '#features' },
  { label: '套餐价格', href: '#pricing' },
  { label: '支持平台', href: '#platforms' },
]
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
        <nav class="hidden md:flex items-center gap-8">
          <a v-for="item in navItems" :key="item.label" :href="item.href"
             class="text-sm text-text-secondary hover:text-text-primary transition-colors">
            {{ item.label }}
          </a>
        </nav>

        <!-- CTA -->
        <div class="hidden md:flex items-center gap-3">
          <button class="px-5 py-2 rounded-full text-sm font-medium border border-accent-purple/40 text-accent-purple hover:bg-accent-purple/10 transition-all cursor-pointer">
            ☆ 开通 VIP
          </button>
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
        <button class="w-full px-5 py-2.5 rounded-full text-sm font-medium border border-accent-purple/40 text-accent-purple">
          ☆ 开通 VIP
        </button>
      </div>
    </div>
  </header>
</template>

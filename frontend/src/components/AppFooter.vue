<template>
  <footer class="border-t border-dark-border/50 py-10 px-4">
    <div class="max-w-6xl mx-auto">
      <div class="flex flex-col md:flex-row items-center justify-between gap-6">
        <!-- Logo -->
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
            <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </div>
          <span class="text-sm font-semibold text-text-secondary">SaveAny</span>
        </div>

        <!-- Disclaimer -->
        <p class="text-xs text-text-muted text-center max-w-lg">
          免责声明：本站仅提供技术工具服务，请尊重版权，仅供个人学习使用。下载内容的版权归原作者所有，请勿用于商业用途。
        </p>

        <!-- Copyright -->
        <p class="text-xs text-text-muted">
          &copy; {{ new Date().getFullYear() }} SaveAny. All rights reserved.
        </p>
      </div>
    </div>
  </footer>
</template>

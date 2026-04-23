<script setup>
import { ref, nextTick, onMounted } from 'vue'
import AppHeader from './components/AppHeader.vue'
import HeroSection from './components/HeroSection.vue'
import UrlInput from './components/UrlInput.vue'
import VideoResult from './components/VideoResult.vue'
import VideoAI from './components/VideoAI.vue'
import FeatureSection from './components/FeatureSection.vue'
import PricingSection from './components/PricingSection.vue'
import FaqSection from './components/FaqSection.vue'
import AppFooter from './components/AppFooter.vue'
import AuthModal from './components/AuthModal.vue'
import { parseVideo, startDownload, watchProgress, getFileUrl } from './api/video.js'
import { getMe } from './api/auth.js'
import { verifySession } from './api/payment.js'
import { getToken, setUser, setToken, isLoggedIn } from './stores/user.js'

const loading = ref(false)
const videoInfo = ref(null)
const error = ref('')
const currentUrl = ref('')
const showAuthModal = ref(false)
const paymentSuccess = ref(false)

// Download state
const downloading = ref(false)
const downloadComplete = ref(false)
const progress = ref(0)
const progressStatus = ref('')
const progressEta = ref('')
const lastTaskId = ref('')

// SSE connection ref
let progressWatcher = null

async function handleParse(url) {
  // 未登录时要求先登录
  if (!isLoggedIn.value) {
    showAuthModal.value = true
    return
  }

  // 清理上一次状态
  loading.value = true
  error.value = ''
  videoInfo.value = null
  currentUrl.value = url
  downloading.value = false
  downloadComplete.value = false
  progress.value = 0

  try {
    const data = await parseVideo(url)
    videoInfo.value = data
    // 解析成功后滚动到结果区域
    await nextTick()
    document.getElementById('video-result')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  } catch (e) {
    error.value = e.message || '解析失败，请检查链接'
  } finally {
    loading.value = false
  }
}

async function handleDownload(formatId) {
  // 关闭上一次的 SSE 连接
  if (progressWatcher) {
    progressWatcher.close()
    progressWatcher = null
  }

  downloading.value = true
  downloadComplete.value = false
  progress.value = 0
  progressStatus.value = '准备下载...'
  progressEta.value = ''
  error.value = ''

  try {
    const { task_id } = await startDownload(currentUrl.value, formatId)
    lastTaskId.value = task_id

    progressWatcher = watchProgress(
      task_id,
      (data) => {
        progress.value = data.progress || 0
        progressEta.value = data.eta || ''
        if (data.speed) {
          progressStatus.value = `下载中 - ${data.speed}`
        } else {
          progressStatus.value = '下载中...'
        }
      },
      () => {
        progress.value = 100
        progressStatus.value = '下载完成！正在保存文件...'
        downloading.value = false
        downloadComplete.value = true
        progressEta.value = ''
        // Trigger file download
        const a = document.createElement('a')
        a.href = getFileUrl(task_id)
        a.download = ''
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      },
      (err) => {
        error.value = err.message || '下载失败'
        downloading.value = false
        progressEta.value = ''
      }
    )
  } catch (e) {
    error.value = e.message
    downloading.value = false
  }
}

function handleRedownload() {
  downloadComplete.value = false
  downloading.value = false
  progress.value = 0
  progressStatus.value = ''
}

// 页面加载时恢复登录态 & 处理支付回调
onMounted(async () => {
  // 检查 URL 中的支付成功参数
  const url = new URL(window.location.href)
  const isPaymentSuccess = url.searchParams.get('payment') === 'success'
  const sessionId = url.searchParams.get('session_id') || ''

  if (isPaymentSuccess) {
    paymentSuccess.value = true
    // 清除 URL 参数
    url.searchParams.delete('payment')
    url.searchParams.delete('session_id')
    window.history.replaceState({}, '', url.pathname + url.search)
    // 5 秒后自动隐藏
    setTimeout(() => { paymentSuccess.value = false }, 5000)
  }

  // 恢复登录态
  const token = getToken()
  if (token) {
    try {
      // 支付成功回跳 + 有 session_id → 主动验证并激活会员
      if (isPaymentSuccess && sessionId) {
        await verifySession(sessionId)
      }

      // 获取最新用户信息
      const data = await getMe()
      setUser(data.user, data.ai_usage)
    } catch {
      // Token 过期或无效，清除
      setToken('')
    }
  }
})
</script>

<template>
  <div class="min-h-screen bg-dark-bg font-sans">
    <AppHeader @showAuth="showAuthModal = true" />

    <!-- 支付成功提示 -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="paymentSuccess" class="fixed top-20 left-1/2 -translate-x-1/2 z-50">
        <div class="flex items-center gap-3 px-6 py-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-sm text-emerald-400 shadow-lg backdrop-blur-md">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          🎉 订阅成功！您已成为 VIP 会员，所有功能已解锁
          <button @click="paymentSuccess = false" class="ml-2 text-emerald-400/60 hover:text-emerald-400 cursor-pointer">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>

    <main>
      <HeroSection>
        <UrlInput :loading="loading" @submit="handleParse" />

        <!-- Error Toast -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0 translate-y-2"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 translate-y-2"
        >
          <div v-if="error" class="mt-6 max-w-2xl mx-auto">
            <div class="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
              <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              {{ error }}
              <button @click="error = ''" class="ml-auto text-red-400/60 hover:text-red-400 cursor-pointer">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </Transition>
      </HeroSection>

      <!-- Skeleton Loading -->
      <div v-if="loading" id="video-result" class="w-full max-w-5xl mx-auto mt-10 px-4">
        <div class="bg-dark-card border border-dark-border rounded-2xl overflow-hidden animate-pulse">
          <div class="flex flex-col lg:flex-row">
            <div class="lg:w-2/5">
              <div class="aspect-video bg-dark-hover"></div>
            </div>
            <div class="lg:w-3/5 p-6 space-y-4">
              <div class="h-6 bg-dark-hover rounded-lg w-3/4"></div>
              <div class="h-4 bg-dark-hover rounded-lg w-1/2"></div>
              <div class="space-y-3 mt-6">
                <div class="h-12 bg-dark-hover rounded-xl"></div>
                <div class="h-12 bg-dark-hover rounded-xl"></div>
                <div class="h-12 bg-dark-hover rounded-xl"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Video Result -->
      <div id="video-result">
        <VideoResult
          :videoInfo="videoInfo"
          :downloading="downloading"
          :downloadComplete="downloadComplete"
          :progress="progress"
          :progressStatus="progressStatus"
          :progressEta="progressEta"
          @download="handleDownload"
          @redownload="handleRedownload"
        />
      </div>

      <!-- AI 分析面板 -->
      <VideoAI
        :videoInfo="videoInfo"
        :url="currentUrl"
        @showAuth="showAuthModal = true"
      />

      <FeatureSection />
      <PricingSection @showAuth="showAuthModal = true" />
      <FaqSection />
    </main>

    <AppFooter />

    <!-- 登录/注册弹窗 -->
    <AuthModal :show="showAuthModal" @close="showAuthModal = false" />
  </div>
</template>

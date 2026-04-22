<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  videoInfo: { type: Object, default: null },
  downloading: { type: Boolean, default: false },
  downloadComplete: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  progressStatus: { type: String, default: '' },
  progressEta: { type: String, default: '' },
})

const emit = defineEmits(['download', 'redownload'])
const selectedFormat = ref(null)

/** 通过后端代理加载缩略图，绕过防盗链 */
const thumbnailUrl = computed(() => {
  if (!props.videoInfo?.thumbnail) return ''
  return `/api/thumbnail?url=${encodeURIComponent(props.videoInfo.thumbnail)}`
})

const sortedFormats = computed(() => {
  if (!props.videoInfo?.formats) return []
  return [...props.videoInfo.formats].sort((a, b) => (b.height || 0) - (a.height || 0))
})

function formatFileSize(bytes) {
  if (!bytes) return '未知大小'
  const mb = bytes / (1024 * 1024)
  if (mb > 1024) return (mb / 1024).toFixed(1) + ' GB'
  return mb.toFixed(1) + ' MB'
}

function formatDuration(seconds) {
  if (!seconds) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function selectAndDownload(format) {
  selectedFormat.value = format.format_id
  emit('download', format.format_id)
}

function getCategoryIcon(category) {
  if (category === 'best') return '🏆'
  if (category === 'merged') return '🎬'
  if (category === 'video') return '🎥'
  if (category === 'audio') return '🎵'
  return '📁'
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-500 ease-out"
    enter-from-class="opacity-0 translate-y-4 scale-[0.98]"
    enter-to-class="opacity-100 translate-y-0 scale-100"
  >
    <div v-if="videoInfo" class="w-full max-w-5xl mx-auto mt-10 px-4">
      <div class="bg-dark-card border border-dark-border rounded-2xl overflow-hidden shadow-2xl shadow-black/20">
        <div class="flex flex-col lg:flex-row">
          <!-- Thumbnail -->
          <div class="lg:w-2/5 relative group">
            <div class="aspect-video lg:aspect-auto lg:h-full relative overflow-hidden">
              <img
                :src="thumbnailUrl"
                :alt="videoInfo.title"
                class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                @error="$event.target.src = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 400 225%22><rect fill=%22%2312121a%22 width=%22400%22 height=%22225%22/><text x=%2250%%22 y=%2250%%22 fill=%22%2364748b%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2216%22>无封面</text></svg>'"
              />
              <!-- Duration overlay -->
              <div class="absolute bottom-3 right-3 px-2 py-1 bg-black/70 rounded-md text-xs text-white font-medium backdrop-blur-sm">
                {{ formatDuration(videoInfo.duration) }}
              </div>
              <!-- Platform overlay -->
              <div v-if="videoInfo.platform" class="absolute top-3 left-3 px-2.5 py-1 bg-black/50 backdrop-blur-sm rounded-lg text-xs text-white font-medium uppercase tracking-wide">
                {{ videoInfo.platform }}
              </div>
            </div>
          </div>

          <!-- Info -->
          <div class="lg:w-3/5 p-4 sm:p-6">
            <h3 class="text-base sm:text-lg font-bold text-text-primary line-clamp-2 mb-3">{{ videoInfo.title }}</h3>

            <div class="flex items-center gap-3 mb-5 text-sm text-text-secondary flex-wrap">
              <span v-if="videoInfo.uploader" class="flex items-center gap-1.5">
                <svg class="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0" />
                </svg>
                {{ videoInfo.uploader }}
              </span>
              <span v-if="videoInfo.duration_string" class="flex items-center gap-1.5 text-text-muted">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {{ videoInfo.duration_string }}
              </span>
            </div>

            <!-- Download Complete State -->
            <div v-if="downloadComplete" class="mb-5">
              <div class="flex items-center gap-3 px-4 py-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                <svg class="w-6 h-6 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div class="flex-1">
                  <p class="text-sm font-medium text-emerald-400">下载完成</p>
                  <p class="text-xs text-emerald-400/60 mt-0.5">文件已开始保存，如未弹出下载请检查浏览器设置</p>
                </div>
              </div>
              <button
                @click="$emit('redownload')"
                class="mt-3 w-full py-2.5 rounded-xl text-sm font-medium border border-dark-border text-text-secondary hover:text-text-primary hover:border-accent-blue/30 transition-all cursor-pointer"
              >
                选择其他格式重新下载
              </button>
            </div>

            <!-- Download Progress -->
            <div v-else-if="downloading" class="mb-5">
              <div class="flex items-center justify-between text-sm mb-2">
                <span class="text-text-secondary">{{ progressStatus || '下载中...' }}</span>
                <div class="flex items-center gap-3">
                  <span v-if="progressEta" class="text-text-muted text-xs">剩余 {{ progressEta }}</span>
                  <span class="text-accent-blue font-semibold tabular-nums">{{ Math.round(progress) }}%</span>
                </div>
              </div>
              <div class="h-2.5 bg-dark-border rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-accent-blue to-accent-purple rounded-full transition-all duration-300 relative progress-shine"
                  :style="{ width: progress + '%' }"
                ></div>
              </div>
              <p class="text-xs text-text-muted mt-2">下载过程中请勿关闭页面</p>
            </div>

            <!-- Format Selection -->
            <div v-else>
              <p class="text-xs text-text-muted mb-3">选择清晰度和格式开始下载</p>
              <div class="space-y-2 max-h-56 overflow-y-auto pr-1 custom-scrollbar">
                <button
                  v-for="fmt in sortedFormats"
                  :key="fmt.format_id"
                  @click="selectAndDownload(fmt)"
                  class="w-full flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer group/fmt"
                  :class="selectedFormat === fmt.format_id
                    ? 'border-accent-blue/50 bg-accent-blue/10'
                    : 'border-dark-border hover:border-accent-blue/20 hover:bg-dark-hover'"
                >
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-lg flex items-center justify-center text-base shrink-0"
                         :class="fmt.category === 'best' ? 'bg-amber-500/10' : fmt.category === 'video' ? 'bg-emerald-500/10' : fmt.category === 'audio' ? 'bg-pink-500/10' : 'bg-accent-blue/10'">
                      {{ getCategoryIcon(fmt.category) }}
                    </div>
                    <div class="text-left min-w-0">
                      <div class="text-sm font-medium text-text-primary truncate">
                        {{ fmt.note || fmt.resolution || 'Audio' }}
                      </div>
                      <div class="text-xs text-text-muted">
                        {{ fmt.ext?.toUpperCase() }} · {{ formatFileSize(fmt.filesize || fmt.filesize_approx) }}
                      </div>
                    </div>
                  </div>
                  <svg class="w-5 h-5 text-text-muted group-hover/fmt:text-accent-blue transition-colors shrink-0 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch, nextTick, onUnmounted, computed } from 'vue'
import { fetchSubtitle, streamSummary, streamChat } from '../api/video.js'
import { Markmap } from 'markmap-view'
import { Transformer } from 'markmap-lib'
import { marked } from 'marked'

const props = defineProps({
  videoInfo: { type: Object, default: null },
  url: { type: String, default: '' },
})

// Tab 状态
const activeTab = ref('summary')
const tabs = [
  { id: 'summary', label: '总结摘要', icon: '📋' },
  { id: 'subtitle', label: '字幕文本', icon: '📝' },
  { id: 'mindmap', label: '思维导图', icon: '🧠' },
  { id: 'chat', label: 'AI 问答', icon: '💬' },
]

// 字幕状态
const subtitleData = ref(null)
const subtitleLoading = ref(false)
const subtitleError = ref('')

// AI 总结状态
const summaryText = ref('')
const summaryLoading = ref(false)
const summaryDone = ref(false)
const summaryError = ref('')
let summaryStream = null

// 思维导图
const markmapContainer = ref(null)
let markmapInstance = null

// AI 问答状态
const chatMessages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatError = ref('')
const chatListRef = ref(null)
let chatStream = null

// 计算属性：渲染 Markdown 为 HTML
const summaryHtml = computed(() => {
  if (!summaryText.value) return ''
  return marked(summaryText.value)
})

// 监听 videoInfo 变化，自动触发字幕提取和 AI 总结
watch(() => props.videoInfo, async (newInfo) => {
  if (!newInfo) return
  // 重置状态
  resetAll()
  // 自动提取字幕
  await loadSubtitle()
  // 如果有字幕，自动生成总结
  if (subtitleData.value?.available && subtitleData.value?.full_text) {
    loadSummary()
  }
}, { immediate: true })

function resetAll() {
  subtitleData.value = null
  subtitleLoading.value = false
  subtitleError.value = ''
  summaryText.value = ''
  summaryLoading.value = false
  summaryDone.value = false
  summaryError.value = ''
  chatMessages.value = []
  chatInput.value = ''
  chatLoading.value = false
  chatError.value = ''
  activeTab.value = 'summary'
  if (summaryStream) { summaryStream.close(); summaryStream = null }
  if (chatStream) { chatStream.close(); chatStream = null }
}

async function loadSubtitle() {
  if (!props.url) return
  subtitleLoading.value = true
  subtitleError.value = ''
  try {
    subtitleData.value = await fetchSubtitle(props.url)
  } catch (e) {
    subtitleError.value = e.message
    subtitleData.value = { available: false, segments: [], full_text: '', message: e.message }
  } finally {
    subtitleLoading.value = false
  }
}

function loadSummary() {
  if (summaryStream) { summaryStream.close() }
  summaryText.value = ''
  summaryLoading.value = true
  summaryDone.value = false
  summaryError.value = ''

  const title = props.videoInfo?.title || ''
  const text = subtitleData.value?.full_text || ''

  summaryStream = streamSummary(
    title,
    text,
    (chunk) => { summaryText.value += chunk },
    () => { summaryLoading.value = false; summaryDone.value = true },
    (err) => { summaryError.value = err.message; summaryLoading.value = false },
  )
}

// 思维导图渲染
watch([activeTab, summaryDone], async () => {
  if (activeTab.value === 'mindmap' && summaryText.value) {
    await nextTick()
    renderMindmap()
  }
})

function renderMindmap() {
  const el = markmapContainer.value
  if (!el) return

  // 清除之前的内容
  el.innerHTML = '<svg></svg>'
  const svg = el.querySelector('svg')
  svg.style.width = '100%'
  svg.style.height = '500px'

  try {
    const transformer = new Transformer()
    const { root } = transformer.transform(summaryText.value)
    markmapInstance = Markmap.create(svg, {
      colorFreezeLevel: 2,
      duration: 300,
      maxWidth: 300,
    }, root)
  } catch (e) {
    console.error('Mindmap render error:', e)
  }
}

// AI 问答
async function sendChatMessage() {
  const question = chatInput.value.trim()
  if (!question || chatLoading.value) return

  chatInput.value = ''
  chatError.value = ''

  // 添加用户消息
  chatMessages.value.push({ role: 'user', content: question })
  // 添加空的 AI 回复占位
  chatMessages.value.push({ role: 'assistant', content: '' })
  chatLoading.value = true

  await nextTick()
  scrollChatToBottom()

  const title = props.videoInfo?.title || ''
  const text = subtitleData.value?.full_text || ''
  // 构建历史（不包含最后的空 assistant 消息）
  const history = chatMessages.value.slice(0, -1).map(m => ({
    role: m.role,
    content: m.content,
  }))

  const msgIndex = chatMessages.value.length - 1

  if (chatStream) { chatStream.close() }
  chatStream = streamChat(
    title, text, history, question,
    (chunk) => {
      chatMessages.value[msgIndex].content += chunk
      scrollChatToBottom()
    },
    () => { chatLoading.value = false },
    (err) => {
      chatError.value = err.message
      chatLoading.value = false
      // 移除空的 AI 回复
      if (!chatMessages.value[msgIndex].content) {
        chatMessages.value.pop()
      }
    },
  )
}

function scrollChatToBottom() {
  nextTick(() => {
    const el = chatListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function formatTime(seconds) {
  if (seconds == null) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function renderChatMd(text) {
  return marked(text || '')
}

onUnmounted(() => {
  if (summaryStream) summaryStream.close()
  if (chatStream) chatStream.close()
})
</script>

<template>
  <Transition
    enter-active-class="transition duration-500 ease-out"
    enter-from-class="opacity-0 translate-y-4"
    enter-to-class="opacity-100 translate-y-0"
  >
    <div v-if="videoInfo" class="w-full max-w-5xl mx-auto mt-6 px-4">
      <div class="bg-dark-card border border-dark-border rounded-2xl overflow-hidden shadow-2xl shadow-black/20">
        <!-- Tab Navigation -->
        <div class="flex border-b border-dark-border overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-all whitespace-nowrap cursor-pointer"
            :class="activeTab === tab.id
              ? 'text-accent-blue border-b-2 border-accent-blue bg-accent-blue/5'
              : 'text-text-secondary hover:text-text-primary hover:bg-dark-hover'"
          >
            <span class="text-base">{{ tab.icon }}</span>
            {{ tab.label }}
          </button>
        </div>

        <!-- Tab Content -->
        <div class="p-5 sm:p-6 min-h-[300px]">

          <!-- Tab: 总结摘要 -->
          <div v-if="activeTab === 'summary'">
            <!-- 加载中 -->
            <div v-if="subtitleLoading" class="flex items-center gap-3 text-text-secondary">
              <svg class="animate-spin w-5 h-5 text-accent-blue" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              正在提取视频字幕...
            </div>
            <div v-else-if="summaryLoading && !summaryText" class="flex items-center gap-3 text-text-secondary">
              <svg class="animate-spin w-5 h-5 text-accent-purple" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              AI 正在生成视频总结...
            </div>

            <!-- 无字幕提示 -->
            <div v-else-if="subtitleData && !subtitleData.available && !subtitleLoading" class="text-center py-10">
              <div class="text-4xl mb-4">📭</div>
              <p class="text-text-secondary mb-2">{{ subtitleData.message || '该视频没有可用的字幕' }}</p>
              <p class="text-text-muted text-sm">AI 总结需要字幕内容作为输入，暂时无法为此视频生成总结</p>
            </div>

            <!-- 总结内容 -->
            <div v-else-if="summaryText" class="prose-content">
              <div v-html="summaryHtml" class="text-text-secondary text-sm leading-relaxed"></div>
              <div v-if="summaryLoading" class="inline-block w-2 h-4 bg-accent-blue animate-pulse ml-1 rounded-sm"></div>
            </div>

            <!-- 总结错误 -->
            <div v-if="summaryError" class="mt-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
              {{ summaryError }}
              <button @click="loadSummary()" class="ml-3 text-red-300 underline cursor-pointer">重试</button>
            </div>
          </div>

          <!-- Tab: 字幕文本 -->
          <div v-if="activeTab === 'subtitle'">
            <div v-if="subtitleLoading" class="flex items-center gap-3 text-text-secondary">
              <svg class="animate-spin w-5 h-5 text-accent-blue" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              正在提取字幕...
            </div>

            <div v-else-if="subtitleData && !subtitleData.available" class="text-center py-10">
              <div class="text-4xl mb-4">📭</div>
              <p class="text-text-secondary">{{ subtitleData.message || '该视频没有可用的字幕' }}</p>
            </div>

            <div v-else-if="subtitleData?.segments?.length" class="space-y-0.5 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
              <div v-if="subtitleData.language" class="mb-3 flex items-center gap-2">
                <span class="text-xs px-2.5 py-1 rounded-full bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
                  {{ subtitleData.source === 'auto' ? '自动字幕' : '人工字幕' }} · {{ subtitleData.language }}
                </span>
              </div>
              <div
                v-for="(seg, i) in subtitleData.segments"
                :key="i"
                class="flex gap-3 py-2 px-3 rounded-lg hover:bg-dark-hover transition-colors group"
              >
                <span class="text-xs text-accent-blue font-mono shrink-0 pt-0.5 tabular-nums">
                  {{ formatTime(seg.start) }}
                </span>
                <span class="text-sm text-text-secondary leading-relaxed">{{ seg.text }}</span>
              </div>
            </div>
          </div>

          <!-- Tab: 思维导图 -->
          <div v-if="activeTab === 'mindmap'">
            <div v-if="!summaryDone && summaryLoading" class="flex items-center gap-3 text-text-secondary">
              <svg class="animate-spin w-5 h-5 text-accent-purple" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              等待 AI 总结完成后生成思维导图...
            </div>

            <div v-else-if="!summaryText" class="text-center py-10">
              <div class="text-4xl mb-4">🧠</div>
              <p class="text-text-secondary">暂无可用的总结内容来生成思维导图</p>
            </div>

            <div v-else ref="markmapContainer" class="w-full bg-dark-bg rounded-xl overflow-hidden border border-dark-border">
              <!-- markmap SVG will be injected here -->
            </div>
          </div>

          <!-- Tab: AI 问答 -->
          <div v-if="activeTab === 'chat'" class="flex flex-col h-[400px]">
            <!-- 需要字幕 -->
            <div v-if="subtitleData && !subtitleData.available && !subtitleLoading" class="text-center py-10 flex-1">
              <div class="text-4xl mb-4">💬</div>
              <p class="text-text-secondary">AI 问答需要字幕内容，该视频暂不支持</p>
            </div>

            <template v-else>
              <!-- 消息列表 -->
              <div ref="chatListRef" class="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-4 mb-4">
                <!-- 欢迎消息 -->
                <div v-if="!chatMessages.length" class="text-center py-10">
                  <div class="text-4xl mb-4">💬</div>
                  <p class="text-text-secondary mb-2">针对视频内容提问</p>
                  <p class="text-text-muted text-sm">试试问: "这个视频的核心观点是什么？"</p>
                  <div class="flex flex-wrap gap-2 justify-center mt-4">
                    <button
                      v-for="q in ['这个视频讲了什么？', '核心观点是什么？', '有哪些关键知识点？']"
                      :key="q"
                      @click="chatInput = q; sendChatMessage()"
                      class="text-xs px-3 py-1.5 rounded-full border border-dark-border text-text-secondary hover:text-accent-blue hover:border-accent-blue/30 transition-colors cursor-pointer"
                    >
                      {{ q }}
                    </button>
                  </div>
                </div>

                <!-- 消息列表 -->
                <div v-for="(msg, i) in chatMessages" :key="i">
                  <!-- 用户消息 -->
                  <div v-if="msg.role === 'user'" class="flex justify-end">
                    <div class="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-br-md bg-accent-blue/20 text-text-primary text-sm">
                      {{ msg.content }}
                    </div>
                  </div>
                  <!-- AI 回复 -->
                  <div v-else class="flex justify-start">
                    <div class="max-w-[85%]">
                      <div class="flex items-center gap-2 mb-1">
                        <span class="text-xs text-accent-purple font-medium">AI 助手</span>
                      </div>
                      <div class="px-4 py-2.5 rounded-2xl rounded-bl-md bg-dark-hover text-sm">
                        <div v-if="msg.content" v-html="renderChatMd(msg.content)" class="prose-content text-text-secondary leading-relaxed"></div>
                        <div v-else class="flex items-center gap-2 text-text-muted">
                          <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                          </svg>
                          思考中...
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 问答错误 -->
              <div v-if="chatError" class="mb-3 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
                {{ chatError }}
              </div>

              <!-- 输入框 -->
              <form @submit.prevent="sendChatMessage" class="flex items-center gap-2">
                <input
                  v-model="chatInput"
                  type="text"
                  placeholder="输入你的问题..."
                  class="flex-1 bg-dark-bg border border-dark-border rounded-xl px-4 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent-blue/50 transition-colors"
                  :disabled="chatLoading || (subtitleData && !subtitleData.available)"
                />
                <button
                  type="submit"
                  :disabled="!chatInput.trim() || chatLoading || (subtitleData && !subtitleData.available)"
                  class="px-4 py-2.5 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-accent-blue to-accent-purple hover:from-blue-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer shrink-0"
                >
                  <svg v-if="chatLoading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                  </svg>
                </button>
              </form>
            </template>
          </div>

        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Markdown 内容渲染样式 */
.prose-content :deep(h2) {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
}
.prose-content :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-top: 1rem;
  margin-bottom: 0.375rem;
}
.prose-content :deep(p) {
  margin-bottom: 0.5rem;
  line-height: 1.7;
}
.prose-content :deep(ul),
.prose-content :deep(ol) {
  padding-left: 1.25rem;
  margin-bottom: 0.5rem;
}
.prose-content :deep(li) {
  margin-bottom: 0.25rem;
  line-height: 1.6;
}
.prose-content :deep(strong) {
  color: var(--color-text-primary);
  font-weight: 600;
}
.prose-content :deep(code) {
  background: var(--color-dark-hover);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.85em;
}
.prose-content :deep(blockquote) {
  border-left: 3px solid var(--color-accent-blue);
  padding-left: 0.75rem;
  color: var(--color-text-muted);
  margin: 0.5rem 0;
}
</style>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NButton, NTag, NSpin, NEmpty, NSpace, NProgress, NModal, NGrid, NGridItem,
  NTabs, NTabPane, useMessage, NAlert
} from 'naive-ui'
import { SoundOutlined, AudioOutlined, ArrowLeftOutlined } from '@vicons/antd'
import {
  getPronunciationExercises,
  getPronunciationProgress,
  scorePronunciation,
  type PhonemeGroup,
  type PhonemeSentence,
  type PronunciationScoreResult,
  type PronunciationProgress,
} from '../api'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const router = useRouter()
const msg = useMessage()

const loading = ref(true)
const exercises = ref<PhonemeGroup[]>([])
const freePractice = ref<PhonemeSentence[]>([])
const progress = ref<PronunciationProgress | null>(null)
const activeTab = ref<'free' | 'phoneme' | 'history'>('free')

// Recording / scoring state
const selectedSentence = ref('')
const isRecording = ref(false)
const recordingTime = ref(0)
const scoring = ref(false)
const lastResult = ref<PronunciationScoreResult | null>(null)

// Audio recording internals
const SAMPLE_RATE = 16000
let stream: MediaStream | null = null
let audioContext: AudioContext | null = null
let scriptNode: ScriptProcessorNode | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let samples: Float32Array[] = []
let recordTimer: number | null = null
let timeTimer: number | null = null

// ---------------------------------------------------------------------------
// Load data
// ---------------------------------------------------------------------------

onMounted(async () => {
  try {
    const [exData, progData] = await Promise.all([
      getPronunciationExercises(),
      getPronunciationProgress(20),
    ])
    exercises.value = exData.phoneme_exercises
    freePractice.value = exData.free_practice
    progress.value = progData
  } catch (e: any) {
    msg.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
})

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const allPracticeSentences = computed(() => {
  const out: { text: string; difficulty: string; phoneme: string }[] = []
  for (const s of freePractice.value) {
    out.push({ text: s.text, difficulty: s.difficulty, phoneme: '' })
  }
  for (const g of exercises.value) {
    for (const s of g.sentences) {
      out.push({ text: s.text, difficulty: s.difficulty, phoneme: g.phoneme })
    }
  }
  return out
})

const scoreColor = computed(() => {
  const s = lastResult.value?.overall_score ?? 0
  if (s >= 8) return '#18a058'
  if (s >= 6) return '#f0a020'
  return '#d03050'
})

const scoreLabel = computed(() => {
  const s = lastResult.value?.overall_score ?? 0
  if (s >= 9) return '优秀！发音非常标准'
  if (s >= 8) return '很好！继续保持'
  if (s >= 6) return '不错，还有提升空间'
  if (s >= 4) return '需要多加练习'
  return '差距较大，加油！'
})

// ---------------------------------------------------------------------------
// Speech synthesis (browser built-in)
// ---------------------------------------------------------------------------

function playTTS(text: string) {
  if (!('speechSynthesis' in window)) {
    msg.warning('浏览器不支持语音合成')
    return
  }
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = 'en-US'
  utter.rate = 0.85
  // Try to find an English voice
  const voices = window.speechSynthesis.getVoices()
  const enVoice = voices.find(v => v.lang.startsWith('en'))
  if (enVoice) utter.voice = enVoice
  window.speechSynthesis.speak(utter)
}

// ---------------------------------------------------------------------------
// Recording (in-page, same pattern as AudioRecorder.vue)
// ---------------------------------------------------------------------------

function cleanup() {
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (timeTimer) { clearInterval(timeTimer); timeTimer = null }
  if (scriptNode) { scriptNode.disconnect(); scriptNode = null }
  if (sourceNode) { sourceNode.disconnect(); sourceNode = null }
  if (audioContext && audioContext.state !== 'closed') { audioContext.close(); audioContext = null }
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null }
  samples = []
}

function encodeWav(sampleArrays: Float32Array[]): Blob {
  const totalLen = sampleArrays.reduce((sum, a) => sum + a.length, 0)
  const buffer = new ArrayBuffer(44 + totalLen * 2)
  const view = new DataView(buffer)
  const ws = (off: number, str: string) => { for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i)) }
  ws(0, 'RIFF'); view.setUint32(4, 36 + totalLen * 2, true); ws(8, 'WAVE')
  ws(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true)
  view.setUint16(22, 1, true); view.setUint32(24, SAMPLE_RATE, true)
  view.setUint32(28, SAMPLE_RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  ws(36, 'data'); view.setUint32(40, totalLen * 2, true)
  let off = 44
  for (const arr of sampleArrays) {
    for (let i = 0; i < arr.length; i++) {
      const s = Math.max(-1, Math.min(1, arr[i]))
      view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
      off += 2
    }
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

async function startRecording() {
  if (isRecording.value) return
  samples = []; recordingTime.value = 0
  lastResult.value = null

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: SAMPLE_RATE, channelCount: 1 } })
    audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })
    sourceNode = audioContext.createMediaStreamSource(stream)
    scriptNode = audioContext.createScriptProcessor(4096, 1, 1)
    scriptNode.onaudioprocess = (event) => {
      samples.push(new Float32Array(event.inputBuffer.getChannelData(0)))
    }
    sourceNode.connect(scriptNode); scriptNode.connect(audioContext.destination)
    isRecording.value = true
    timeTimer = window.setInterval(() => { recordingTime.value++ }, 1000)
    recordTimer = window.setTimeout(() => { stopRecording() }, 30000)
  } catch {
    msg.error('无法访问麦克风')
  }
}

async function stopRecording() {
  if (!isRecording.value) return
  isRecording.value = false
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (timeTimer) { clearInterval(timeTimer); timeTimer = null }
  if (scriptNode) { scriptNode.disconnect(); scriptNode = null }
  if (sourceNode) { sourceNode.disconnect(); sourceNode = null }
  if (audioContext && audioContext.state !== 'closed') { audioContext.close(); audioContext = null }
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null }

  if (samples.length > 0 && selectedSentence.value) {
    const wavBlob = encodeWav(samples)
    await submitScore(wavBlob)
  }
  samples = []
}

async function submitScore(audioBlob: Blob) {
  scoring.value = true
  try {
    const result = await scorePronunciation(selectedSentence.value, audioBlob)
    lastResult.value = result
    // Refresh progress
    progress.value = await getPronunciationProgress(20)
  } catch (e: any) {
    msg.error(e.message || '评分失败')
  } finally {
    scoring.value = false
  }
}

function selectSentence(text: string) {
  selectedSentence.value = text
  lastResult.value = null
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function wordScoreColor(s: number): string {
  if (s >= 0.8) return '#18a058'
  if (s >= 0.4) return '#f0a020'
  return '#d03050'
}
</script>

<template>
  <div style="max-width:900px;margin:0 auto;padding:24px 16px">
    <!-- Header -->
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px">
      <NButton text @click="router.back()">
        <template #icon><ArrowLeftOutlined /></template>
      </NButton>
      <h2 style="margin:0">🎤 发音练习</h2>
    </div>

    <NSpin :show="loading">
      <NTabs v-model:value="activeTab" type="line" animated>
        <!-- ============================================================ -->
        <!-- Tab 1: Free Practice -->
        <!-- ============================================================ -->
        <NTabPane name="free" tab="自由跟读">
          <NCard v-if="!selectedSentence" title="选择一句开始练习" size="small">
            <div style="display:flex;flex-direction:column;gap:8px">
              <NCard
                v-for="(s, i) in freePractice"
                :key="i"
                size="small"
                hoverable
                style="cursor:pointer"
                @click="selectSentence(s.text)"
              >
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <span style="font-size:16px;line-height:1.5">{{ s.text }}</span>
                  <NSpace :size="4">
                    <NTag size="tiny" :type="s.difficulty === 'easy' ? 'success' : s.difficulty === 'medium' ? 'warning' : 'error'">
                      {{ s.difficulty === 'easy' ? '简单' : s.difficulty === 'medium' ? '中等' : '困难' }}
                    </NTag>
                    <NButton size="tiny" text @click.stop="playTTS(s.text)">
                      <template #icon><SoundOutlined /></template>
                    </NButton>
                  </NSpace>
                </div>
              </NCard>
            </div>
          </NCard>

          <!-- Practice area -->
          <div v-if="selectedSentence" style="display:flex;flex-direction:column;gap:16px">
            <NButton size="small" text @click="selectedSentence = ''">← 返回选择</NButton>

            <!-- Target sentence card -->
            <NCard size="small" style="background:#f0f7ff">
              <div style="font-size:14px;color:#999;margin-bottom:8px">🎯 跟读以下句子：</div>
              <div style="font-size:20px;font-weight:600;line-height:1.6;margin-bottom:12px">
                {{ selectedSentence }}
              </div>
              <NButton size="small" @click="playTTS(selectedSentence)">
                <template #icon><SoundOutlined /></template>
                播放标准发音
              </NButton>
            </NCard>

            <!-- Record button -->
            <NCard size="small" style="text-align:center">
              <div style="margin-bottom:12px;font-size:14px;color:#666">
                {{ isRecording ? `录音中... ${recordingTime}s` : '按住按钮开始录音' }}
              </div>
              <NButton
                :type="isRecording ? 'error' : 'primary'"
                size="large"
                circle
                :style="isRecording ? 'animation:pulse 1s infinite' : ''"
                @mousedown.prevent="startRecording"
                @mouseup.prevent="stopRecording"
                @mouseleave="isRecording ? stopRecording() : undefined"
                @touchstart.prevent="startRecording"
                @touchend.prevent="stopRecording"
              >
                <template #icon><AudioOutlined /></template>
              </NButton>
              <div style="font-size:12px;color:#999;margin-top:8px">最长 30 秒</div>
            </NCard>

            <!-- Scoring result -->
            <NCard v-if="scoring" size="small" style="text-align:center">
              <NSpin :show="true" /><div style="margin-top:8px">评分中...</div>
            </NCard>

            <NCard v-if="lastResult && !scoring" size="small">
              <div style="text-align:center;margin-bottom:16px">
                <div
                  style="display:inline-flex;align-items:center;justify-content:center;
                  width:100px;height:100px;border-radius:50%;
                  border:5px solid currentColor;background:#f9f9f9"
                  :style="{ color: scoreColor }"
                >
                  <div>
                    <div style="font-size:32px;font-weight:700" :style="{color: scoreColor}">
                      {{ lastResult.overall_score }}
                    </div>
                    <div style="font-size:11px;color:#999">/ 10</div>
                  </div>
                </div>
                <div style="margin-top:8px;font-weight:500" :style="{color: scoreColor}">
                  {{ scoreLabel }}
                </div>
                <div style="font-size:12px;color:#999;margin-top:4px">
                  准确率 {{ (lastResult.accuracy * 100).toFixed(0) }}%
                </div>
              </div>

              <!-- Transcription -->
              <div style="margin-bottom:12px">
                <div style="font-size:12px;color:#999;margin-bottom:4px">📝 识别文本：</div>
                <div style="font-size:15px;background:#fafafa;padding:8px 12px;border-radius:6px">
                  {{ lastResult.transcription || '(未识别到语音)' }}
                </div>
              </div>

              <!-- Word scores -->
              <div v-if="lastResult.word_scores.length" style="display:flex;flex-wrap:wrap;gap:6px">
                <NTag
                  v-for="(ws, i) in lastResult.word_scores"
                  :key="i"
                  size="small"
                  :type="ws.match ? 'success' : ws.score >= 0.4 ? 'warning' : 'error'"
                >
                  {{ ws.word }}
                </NTag>
              </div>
            </NCard>
          </div>
        </NTabPane>

        <!-- ============================================================ -->
        <!-- Tab 2: Phoneme Exercises -->
        <!-- ============================================================ -->
        <NTabPane name="phoneme" tab="音素专项">
          <div v-if="!selectedSentence">
            <p style="color:#666;margin-bottom:16px">
              选择需要练习的音素，系统会提供针对该音素的句子。适合攻克中国学习者常见发音难点。
            </p>

            <div style="display:flex;flex-direction:column;gap:16px">
              <NCard v-for="group in exercises" :key="group.phoneme" size="small">
                <template #header>
                  <div style="display:flex;align-items:center;gap:8px">
                    <NTag type="info" size="medium">{{ group.phoneme }}</NTag>
                    <strong>{{ group.title }}</strong>
                  </div>
                </template>

                <div style="font-size:13px;color:#888;margin-bottom:12px">{{ group.description }}</div>

                <div style="display:flex;flex-direction:column;gap:8px">
                  <NCard
                    v-for="(s, si) in group.sentences"
                    :key="si"
                    size="small"
                    hoverable
                    style="cursor:pointer"
                    @click="selectSentence(s.text)"
                  >
                    <div style="display:flex;justify-content:space-between;align-items:center">
                      <span style="font-size:15px;line-height:1.5">{{ s.text }}</span>
                      <NSpace :size="4">
                        <NTag size="tiny" :type="s.difficulty === 'easy' ? 'success' : s.difficulty === 'medium' ? 'warning' : 'error'">
                          {{ s.difficulty === 'easy' ? '简单' : s.difficulty === 'medium' ? '中等' : '困难' }}
                        </NTag>
                        <NButton size="tiny" text @click.stop="playTTS(s.text)">
                          <template #icon><SoundOutlined /></template>
                        </NButton>
                      </NSpace>
                    </div>
                  </NCard>
                </div>
              </NCard>
            </div>
          </div>

          <!-- Same practice area when sentence selected -->
          <div v-if="selectedSentence" style="display:flex;flex-direction:column;gap:16px">
            <NButton size="small" text @click="selectedSentence = ''">← 返回音素列表</NButton>

            <NCard size="small" style="background:#f0f7ff">
              <div style="font-size:14px;color:#999;margin-bottom:8px">🎯 跟读以下句子：</div>
              <div style="font-size:20px;font-weight:600;line-height:1.6;margin-bottom:12px">
                {{ selectedSentence }}
              </div>
              <NButton size="small" @click="playTTS(selectedSentence)">
                <template #icon><SoundOutlined /></template>
                播放标准发音
              </NButton>
            </NCard>

            <NCard size="small" style="text-align:center">
              <div style="margin-bottom:12px;font-size:14px;color:#666">
                {{ isRecording ? `录音中... ${recordingTime}s` : '按住按钮开始录音' }}
              </div>
              <NButton
                :type="isRecording ? 'error' : 'primary'"
                size="large"
                circle
                :style="isRecording ? 'animation:pulse 1s infinite' : ''"
                @mousedown.prevent="startRecording"
                @mouseup.prevent="stopRecording"
                @mouseleave="isRecording ? stopRecording() : undefined"
                @touchstart.prevent="startRecording"
                @touchend.prevent="stopRecording"
              >
                <template #icon><AudioOutlined /></template>
              </NButton>
            </NCard>

            <NCard v-if="scoring" size="small" style="text-align:center">
              <NSpin :show="true" /><div style="margin-top:8px">评分中...</div>
            </NCard>

            <NCard v-if="lastResult && !scoring" size="small">
              <div style="text-align:center;margin-bottom:16px">
                <div
                  style="display:inline-flex;align-items:center;justify-content:center;
                  width:100px;height:100px;border-radius:50%;
                  border:5px solid currentColor;background:#f9f9f9"
                  :style="{ color: scoreColor }"
                >
                  <div>
                    <div style="font-size:32px;font-weight:700" :style="{color: scoreColor}">
                      {{ lastResult.overall_score }}
                    </div>
                    <div style="font-size:11px;color:#999">/ 10</div>
                  </div>
                </div>
                <div style="margin-top:8px;font-weight:500" :style="{color: scoreColor}">
                  {{ scoreLabel }}
                </div>
                <div style="font-size:12px;color:#999;margin-top:4px">
                  准确率 {{ (lastResult.accuracy * 100).toFixed(0) }}%
                </div>
              </div>

              <div style="margin-bottom:12px">
                <div style="font-size:12px;color:#999;margin-bottom:4px">📝 识别文本：</div>
                <div style="font-size:15px;background:#fafafa;padding:8px 12px;border-radius:6px">
                  {{ lastResult.transcription || '(未识别到语音)' }}
                </div>
              </div>

              <div v-if="lastResult.word_scores.length" style="display:flex;flex-wrap:wrap;gap:6px">
                <NTag
                  v-for="(ws, i) in lastResult.word_scores"
                  :key="i"
                  size="small"
                  :type="ws.match ? 'success' : ws.score >= 0.4 ? 'warning' : 'error'"
                >
                  {{ ws.word }}
                </NTag>
              </div>
            </NCard>
          </div>
        </NTabPane>

        <!-- ============================================================ -->
        <!-- Tab 3: History -->
        <!-- ============================================================ -->
        <NTabPane name="history" tab="练习记录">
          <NEmpty
            v-if="!progress || !progress.attempts.length"
            description="还没有发音练习记录"
          />

          <template v-if="progress && progress.attempts.length">
            <!-- Stats -->
            <NGrid :cols="3" :x-gap="12" style="margin-bottom:16px">
              <NGridItem>
                <NCard size="small" style="text-align:center">
                  <div style="font-size:22px;font-weight:700;color:#2080f0">{{ progress.total_attempts }}</div>
                  <div style="font-size:12px;color:#999">总练习次数</div>
                </NCard>
              </NGridItem>
              <NGridItem>
                <NCard size="small" style="text-align:center">
                  <div style="font-size:22px;font-weight:700;color:#18a058">{{ progress.avg_score }}</div>
                  <div style="font-size:12px;color:#999">平均得分</div>
                </NCard>
              </NGridItem>
              <NGridItem>
                <NCard size="small" style="text-align:center">
                  <div style="font-size:22px;font-weight:700;color:#f0a020">{{ (progress.avg_accuracy * 100).toFixed(0) }}%</div>
                  <div style="font-size:12px;color:#999">平均准确率</div>
                </NCard>
              </NGridItem>
            </NGrid>

            <!-- Attempts list -->
            <div style="display:flex;flex-direction:column;gap:8px">
              <NCard v-for="a in progress.attempts" :key="a.id" size="small">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
                  <div style="flex:1;min-width:200px">
                    <div style="font-size:14px;font-weight:500;margin-bottom:4px">🎯 {{ a.target_text }}</div>
                    <div style="font-size:12px;color:#999;margin-bottom:4px">
                      📝 {{ a.user_transcription || '(未识别)' }}
                    </div>
                    <div style="font-size:12px;color:#999">{{ formatDate(a.created_at) }}</div>
                  </div>
                  <div style="text-align:center;min-width:60px">
                    <div style="font-size:20px;font-weight:700" :style="{color: a.overall_score >= 8 ? '#18a058' : a.overall_score >= 6 ? '#f0a020' : '#d03050'}">
                      {{ a.overall_score }}
                    </div>
                    <div style="font-size:11px;color:#999">{{ (a.accuracy * 100).toFixed(0) }}%</div>
                  </div>
                </div>
              </NCard>
            </div>
          </template>
        </NTabPane>
      </NTabs>
    </NSpin>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(208,48,80,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(208,48,80,0); }
}
</style>

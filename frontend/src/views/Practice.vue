<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton, NInput, NSpace, NSpin, NTag, NAlert, NPopconfirm,
  NDivider, NTooltip, useMessage
} from 'naive-ui'
import { SendOutlined, ArrowLeftOutlined, CheckCircleOutlined, SoundOutlined } from '@vicons/antd'
import {
  createConversation,
  getConversation,
  sendMessage,
  sendMessageStream,
  type ConversationRecord,
  type Correction,
  type PronunciationScore,
} from '../api'
import ChatBubble from '../components/ChatBubble.vue'
import AudioRecorder from '../components/AudioRecorder.vue'

const route = useRoute()
const router = useRouter()
const msg = useMessage()

// --- State ---
const sceneId = route.params.sceneId as string
const sessionId = ref((route.query.session as string) || '')
const sceneName = ref('')
const messages = ref<MessageItem[]>([])
const textInput = ref('')
const loading = ref(false)
const error = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const ttsEnabled = ref(localStorage.getItem('ttsEnabled') !== 'false')
watch(ttsEnabled, (v) => localStorage.setItem('ttsEnabled', String(v)))

// --- Types ---
interface MessageItem {
  id: string
  role: 'user' | 'ai' | 'system'
  text: string
  correctedText?: string
  corrections?: Correction[]
  pronunciationScore?: PronunciationScore | null
  audioBase64?: string
}

// --- Init ---
onMounted(async () => {
  if (sessionId.value) {
    await loadHistory()
  } else {
    await startNewConversation()
  }
})

async function startNewConversation() {
  loading.value = true
  try {
    const conv = await createConversation(sceneId)
    sessionId.value = conv.session_id
    sceneName.value = conv.scene.name
    router.replace({
      name: 'practice',
      params: { sceneId },
      query: { session: conv.session_id },
    })
    messages.value.push({
      id: 'greeting',
      role: 'ai',
      text: conv.greeting.text,
    })
  } catch (e: any) {
    error.value = e.message || 'Failed to start'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function loadHistory() {
  loading.value = true
  try {
    const doc = await getConversation(sessionId.value)
    sceneName.value = ''
    messages.value = doc.messages
      .filter((m: any) => m.ai_text || m.user_text)
      .flatMap((m: any) => {
        const items: MessageItem[] = []
        if (m.user_text) {
          items.push({
            id: `u${m.turn}`,
            role: 'user',
            text: m.user_text,
            correctedText: m.corrected_text || undefined,
            corrections: m.corrections || [],
            pronunciationScore: m.pronunciation_score,
          })
        }
        if (m.ai_text) {
          items.push({
            id: `a${m.turn}`,
            role: 'ai',
            text: m.ai_text,
          })
        }
        return items
      })
    if (doc.ended_at) {
      msg.warning('This conversation has ended. Redirecting to summary...')
      router.replace({ name: 'summary', params: { sessionId: sessionId.value } })
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load conversation'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// --- Actions ---
async function handleSendText() {
  const text = textInput.value.trim()
  if (!text || loading.value) return
  textInput.value = ''

  // Echo user message
  const userMsg: MessageItem = { id: `u${Date.now()}`, role: 'user', text }
  messages.value.push(userMsg)

  // Empty AI bubble that gets updated during streaming
  const aiId = `a${Date.now()}`
  const aiMsg: MessageItem = { id: aiId, role: 'ai', text: '' }
  messages.value.push(aiMsg)

  loading.value = true
  try {
    for await (const event of sendMessageStream(sessionId.value, { text, ttsEnabled: ttsEnabled.value })) {
      if (event.type === 'text_delta') {
        // Update the AI bubble in-place
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], text: messages.value[idx].text + (event.content || '') }
        }
      } else if (event.type === 'corrections' && event.data) {
        // Update user message with corrections
        const uIdx = messages.value.findIndex(m => m.id === userMsg.id)
        if (uIdx >= 0 && event.data.length) {
          let corrected = userMsg.text
          for (const c of event.data) {
            corrected = corrected.replace(c.original || '', c.corrected || '')
          }
          messages.value[uIdx] = {
            ...messages.value[uIdx],
            correctedText: corrected,
            corrections: event.data,
          }
        }
      } else if (event.type === 'audio' && event.data) {
        // Update AI bubble with audio — only auto-play if TTS is enabled
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], audioBase64: event.data }
        }
        if (ttsEnabled.value) playAudio(event.data)
      }
      scrollToBottom()
    }
  } catch (e: any) {
    // Fallback: use non-streaming endpoint
    messages.value = messages.value.filter(m => m.id !== aiId)  // remove empty AI bubble
    try {
      const resp = await sendMessage(sessionId.value, { text })
      processResponse(resp)
    } catch (e2: any) {
      error.value = e2.message || 'Send failed'
    }
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function handleSendAudio(audioBlob: Blob) {
  if (loading.value) return
  loading.value = true

  const aiId = `a${Date.now()}`
  messages.value.push({ id: aiId, role: 'ai', text: '' })

  try {
    for await (const event of sendMessageStream(sessionId.value, { audio: audioBlob, filename: 'recording.wav', ttsEnabled: ttsEnabled.value })) {
      if (event.type === 'text_delta') {
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], text: messages.value[idx].text + (event.content || '') }
        }
      } else if (event.type === 'corrections' && event.data) {
        const doc = await getConversation(sessionId.value)
        const lastTurn = doc.messages[doc.messages.length - 1]
        if (lastTurn && lastTurn.user_text) {
          messages.value.splice(messages.value.length - 1, 0, {
            id: `u${Date.now()}`,
            role: 'user',
            text: lastTurn.user_text,
            correctedText: lastTurn.corrected_text || undefined,
            corrections: lastTurn.corrections || event.data,
            pronunciationScore: lastTurn.pronunciation_score,
          })
        }
      } else if (event.type === 'audio' && event.data) {
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) messages.value[idx] = { ...messages.value[idx], audioBase64: event.data }
        if (ttsEnabled.value) playAudio(event.data)
      }
      scrollToBottom()
    }
  } catch (e: any) {
    messages.value = messages.value.filter(m => m.id !== aiId)
    try {
      const resp = await sendMessage(sessionId.value, { audio: audioBlob, filename: 'recording.wav' })
      messages.value.push({ id: `u${Date.now()}`, role: 'user', text: resp.user_text, correctedText: resp.corrected_text || undefined, corrections: resp.corrections, pronunciationScore: resp.pronunciation_score })
      processResponse(resp)
    } catch (e2: any) {
      error.value = e2.message || 'Send failed'
    }
  } finally {
    loading.value = false; scrollToBottom()
  }
}

function processResponse(resp: any) {
  const msgItem: MessageItem = {
    id: `a${Date.now()}`,
    role: 'ai',
    text: resp.ai_reply.text,
    audioBase64: resp.ai_reply.audio_base64 || undefined,
  }
  messages.value.push(msgItem)

  if (resp.ai_reply.audio_base64 && ttsEnabled.value) {
    playAudio(resp.ai_reply.audio_base64)
  }
}

function playAudio(base64: string) {
  try {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: 'audio/mp3' })
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audio.play().catch(() => {})
    audio.onended = () => URL.revokeObjectURL(url)
  } catch {
    // Audio playback failure is non-critical
  }
}

async function handleEnd() {
  router.push({ name: 'summary', params: { sessionId: sessionId.value } })
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}
</script>

<template>
  <div style="display:flex;flex-direction:column;height:calc(100vh - 56px);max-width:720px;margin:0 auto">
    <!-- Header bar -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #eee">
      <NSpace align="center">
        <NButton text @click="router.push({name:'home'})">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </NButton>
        <span style="font-weight:600">{{ sceneName || '对话练习' }}</span>
      </NSpace>
      <NSpace align="center" :size="8">
        <NTooltip>
          <template #trigger>
            <NButton size="small" @click="ttsEnabled = !ttsEnabled" :type="ttsEnabled ? 'primary' : 'default'" :ghost="!ttsEnabled">
              <template #icon><SoundOutlined /></template>
              {{ ttsEnabled ? '🔊' : '🔇' }}
            </NButton>
          </template>
          {{ ttsEnabled ? '播报已开启' : '播报已关闭' }}
        </NTooltip>
        <NPopconfirm @positive-click="handleEnd">
          <template #trigger>
            <NButton size="small" type="warning" :disabled="!messages.length">
              <template #icon><CheckCircleOutlined /></template>
              结束对话
            </NButton>
          </template>
          确定要结束本次练习吗？结束后可在总结页查看报告。
      </NPopconfirm>
      </NSpace>
    </div>

    <!-- Error -->
    <NAlert v-if="error" type="error" :title="error" closable @close="error=''" style="margin:8px 16px" />

    <!-- Messages -->
    <div ref="chatContainer" style="flex:1;overflow-y:auto;padding:16px">
      <TransitionGroup name="msg" tag="div">
        <div v-for="m in messages" :key="m.id" style="margin-bottom:8px">
          <ChatBubble
            :role="m.role"
            :text="m.text"
            :corrected-text="m.correctedText"
            :corrections="m.corrections"
            :pronunciation-score="m.pronunciationScore"
            :audio-base64="m.audioBase64"
          />
        </div>
      </TransitionGroup>

      <!-- Loading indicator -->
      <div v-if="loading" style="text-align:center;padding:16px">
        <NSpace align="center" justify="center">
          <NSpin size="small" />
          <span style="color:#999">AI 正在回复...</span>
        </NSpace>
      </div>
    </div>

    <!-- Input area -->
    <div style="padding:12px 16px;border-top:1px solid #eee;background:#fafafa">
      <NSpace align="end" style="width:100%">
        <NInput
          v-model:value="textInput"
          type="textarea"
          placeholder="输入英语内容，或点击右侧麦克风语音输入..."
          :autosize="{ minRows: 1, maxRows: 3 }"
          :disabled="loading"
          style="flex:1"
          @keydown.enter.exact.prevent="handleSendText"
        />
        <AudioRecorder
          :disabled="loading"
          @audio-ready="handleSendAudio"
        />
        <NButton
          type="primary"
          :disabled="!textInput.trim() || loading"
          @click="handleSendText"
        >
          <template #icon><SendOutlined /></template>
        </NButton>
      </NSpace>
    </div>
  </div>
</template>

<style scoped>
.msg-enter-active {
  transition: all 0.3s ease;
}
.msg-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
</style>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton, NInput, NSpace, NSpin, NTag, NAlert, NPopconfirm,
  NDivider, useMessage
} from 'naive-ui'
import { SendOutlined, ArrowLeftOutlined, CheckCircleOutlined, ArrowDownOutlined } from '@vicons/antd'
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
import TypingBubble from '../components/chat/TypingBubble.vue'
import TimeSeparator from '../components/chat/TimeSeparator.vue'
import QuickReplies from '../components/chat/QuickReplies.vue'
import { useScrollAnchor } from '../composables/useScrollAnchor'

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

// --- Scroll anchor ---
const { showScrollButton, onScroll, scrollToBottom, smartScrollToBottom } = useScrollAnchor(chatContainer)

// --- Avatar map for scene characters ---
const avatarMap: Record<string, string> = {
  'coffee-shop': '👨‍🍳',
  'hotel-checkin': '🏨',
  'restaurant': '🍽️',
  'shopping': '🛍️',
  'doctor-visit': '👨‍⚕️',
  'job-interview': '💼',
  'academic-discussion': '👨‍🏫',
  'apartment-viewing': '🏠',
  'debate-competition': '👨‍⚖️',
}
const sceneAvatar = computed(() => avatarMap[sceneId] || '🤖')

// --- Quick reply suggestions ---
const quickSuggestions = ref<string[]>([])

// --- Types ---
interface MessageItem {
  id: string
  role: 'user' | 'ai' | 'system'
  text: string
  correctedText?: string
  corrections?: Correction[]
  pronunciationScore?: PronunciationScore | null
  audioBase64?: string
  audioUrl?: string       // URL to user's voice recording
  timestamp?: string   // ISO timestamp for time separation
  prevTimestamp?: string
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
    const now = new Date().toISOString()
    messages.value.push({
      id: 'greeting',
      role: 'ai',
      text: conv.greeting.text,
      timestamp: now,
      prevTimestamp: now,
    })
    // Set default quick replies for greeting
    quickSuggestions.value = getDefaultSuggestions()
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
    let prevTs: string | undefined
    messages.value = doc.messages
      .filter((m: any) => m.ai_text || m.user_text)
      .flatMap((m: any) => {
        const items: MessageItem[] = []
        const ts = doc.created_at // Use conversation created_at as reference
        if (m.user_text) {
          items.push({
            id: `u${m.turn}`,
            role: 'user',
            text: m.user_text,
            correctedText: m.corrected_text || undefined,
            corrections: m.corrections || [],
            pronunciationScore: m.pronunciation_score,
            audioUrl: m.audio_url || undefined,
            timestamp: ts,
            prevTimestamp: prevTs,
          })
          prevTs = ts
        }
        if (m.ai_text) {
          items.push({
            id: `a${m.turn}`,
            role: 'ai',
            text: m.ai_text,
            timestamp: ts,
            prevTimestamp: prevTs,
          })
          prevTs = ts
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

// --- Default quick suggestions ---
function getDefaultSuggestions(): string[] {
  const defaults: Record<string, string[]> = {
    'coffee-shop': ['I\'d like a latte, please', 'What do you recommend?', 'How much is it?'],
    'hotel-checkin': ['I have a reservation', 'What time is check-out?', 'Is breakfast included?'],
    'restaurant': ['Can I see the menu?', 'What\'s today\'s special?', 'I\'d like to order'],
    'shopping': ['How much is this?', 'Do you have a larger size?', 'Can I try it on?'],
    'doctor-visit': ['I have a headache', 'How should I take this medicine?', 'I feel better now'],
    'job-interview': ['I have experience in...', 'What does this role involve?', 'Thank you for your time'],
    'academic-discussion': ['In my opinion...', 'The evidence suggests that...', 'Could you elaborate on that?'],
    'apartment-viewing': ['How much is the rent?', 'Is it furnished?', 'How long is the lease?'],
    'debate-competition': ['I strongly believe that...', 'That argument fails to consider...', 'Let me present my case...'],
  }
  return defaults[sceneId] || ['Tell me more', 'Can you repeat that?', 'I understand']
}

// --- Check if time separator needed ---
function showTimeSeparator(msg: MessageItem): boolean {
  if (!msg.timestamp || !msg.prevTimestamp) return false
  const t1 = new Date(msg.prevTimestamp).getTime()
  const t2 = new Date(msg.timestamp).getTime()
  return (t2 - t1) > 5 * 60 * 1000 // 5 minutes
}

// --- Actions ---
async function handleSendText(textToSend?: string) {
  const text = (textToSend || textInput.value).trim()
  if (!text || loading.value) return
  textInput.value = ''
  quickSuggestions.value = []

  const now = new Date().toISOString()
  const prevTs = messages.value.length > 0
    ? messages.value[messages.value.length - 1].timestamp
    : now

  // Echo user message
  const userMsg: MessageItem = {
    id: `u${Date.now()}`, role: 'user', text,
    timestamp: now, prevTimestamp: prevTs,
  }
  messages.value.push(userMsg)

  // Empty AI bubble
  const aiId = `a${Date.now()}`
  const aiMsg: MessageItem = {
    id: aiId, role: 'ai', text: '',
    timestamp: now, prevTimestamp: now,
  }
  messages.value.push(aiMsg)

  loading.value = true
  try {
    for await (const event of sendMessageStream(sessionId.value, { text })) {
      if (event.type === 'text_delta') {
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], text: messages.value[idx].text + (event.content || '') }
        }
      } else if (event.type === 'corrections' && event.data) {
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
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], audioBase64: event.data }
        }
        playAudio(event.data)
      }
      smartScrollToBottom()
    }
    // After streaming done, set new suggestions
    quickSuggestions.value = getDefaultSuggestions()
  } catch (e: any) {
    messages.value = messages.value.filter(m => m.id !== aiId)
    try {
      const resp = await sendMessage(sessionId.value, { text })
      processResponse(resp)
    } catch (e2: any) {
      error.value = e2.message || 'Send failed'
    }
  } finally {
    loading.value = false
    smartScrollToBottom()
  }
}

async function handleSendAudio(audioBlob: Blob) {
  if (loading.value) return
  loading.value = true

  const now = new Date().toISOString()
  const aiId = `a${Date.now()}`
  messages.value.push({ id: aiId, role: 'ai', text: '', timestamp: now, prevTimestamp: now })

  try {
    for await (const event of sendMessageStream(sessionId.value, { audio: audioBlob, filename: 'recording.wav' })) {
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
            timestamp: now, prevTimestamp: now,
          })
        }
      } else if (event.type === 'audio' && event.data) {
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) messages.value[idx] = { ...messages.value[idx], audioBase64: event.data }
        playAudio(event.data)
      }
      smartScrollToBottom()
    }
  } catch (e: any) {
    messages.value = messages.value.filter(m => m.id !== aiId)
    try {
      const resp = await sendMessage(sessionId.value, { audio: audioBlob, filename: 'recording.wav' })
      messages.value.push({ id: `u${Date.now()}`, role: 'user', text: resp.user_text, correctedText: resp.corrected_text || undefined, corrections: resp.corrections, pronunciationScore: resp.pronunciation_score, timestamp: now, prevTimestamp: now })
      processResponse(resp)
    } catch (e2: any) {
      error.value = e2.message || 'Send failed'
    }
  } finally {
    loading.value = false; smartScrollToBottom()
  }
}

function processResponse(resp: any) {
  const now = new Date().toISOString()
  const msgItem: MessageItem = {
    id: `a${Date.now()}`,
    role: 'ai',
    text: resp.ai_reply.text,
    audioBase64: resp.ai_reply.audio_base64 || undefined,
    timestamp: now,
    prevTimestamp: now,
  }
  messages.value.push(msgItem)

  if (resp.ai_reply.audio_base64) {
    playAudio(resp.ai_reply.audio_base64)
  }
  quickSuggestions.value = getDefaultSuggestions()
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

// --- Regenerate last AI message ---
async function handleRegenerate() {
  // Remove the last AI message
  const lastAiIdx = [...messages.value].reverse().findIndex(m => m.role === 'ai')
  if (lastAiIdx < 0) return
  const actualIdx = messages.value.length - 1 - lastAiIdx
  const lastUserMsg = [...messages.value].slice(0, actualIdx).reverse().find(m => m.role === 'user')
  if (!lastUserMsg) return

  messages.value.splice(actualIdx, 1)
  quickSuggestions.value = []

  const now = new Date().toISOString()
  const aiId = `a${Date.now()}`
  messages.value.push({ id: aiId, role: 'ai', text: '', timestamp: now, prevTimestamp: now })

  loading.value = true
  try {
    for await (const event of sendMessageStream(sessionId.value, { text: lastUserMsg.text })) {
      if (event.type === 'text_delta') {
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) {
          messages.value[idx] = { ...messages.value[idx], text: messages.value[idx].text + (event.content || '') }
        }
      } else if (event.type === 'audio' && event.data) {
        const idx = messages.value.findIndex(m => m.id === aiId)
        if (idx >= 0) messages.value[idx] = { ...messages.value[idx], audioBase64: event.data }
        playAudio(event.data)
      }
      smartScrollToBottom()
    }
    quickSuggestions.value = getDefaultSuggestions()
  } catch (e: any) {
    error.value = e.message || 'Regenerate failed'
  } finally {
    loading.value = false
    smartScrollToBottom()
  }
}
</script>

<template>
  <div style="display:flex;flex-direction:column;height:calc(100vh - var(--header-height));max-width:var(--max-width-chat);margin:0 auto">
    <!-- Header bar -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--color-border)">
      <NSpace align="center">
        <NButton text @click="router.push({name:'home'})">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </NButton>
        <span style="font-weight:600;font-size:var(--font-size-body)">{{ sceneName || '对话练习' }}</span>
      </NSpace>
      <NPopconfirm @positive-click="handleEnd">
        <template #trigger>
          <NButton size="small" type="warning" :disabled="!messages.length">
            <template #icon><CheckCircleOutlined /></template>
            结束对话
          </NButton>
        </template>
        确定要结束本次练习吗？结束后可在总结页查看报告。
      </NPopconfirm>
    </div>

    <!-- Error -->
    <NAlert v-if="error" type="error" :title="error" closable @close="error=''" style="margin:8px 16px" />

    <!-- Messages -->
    <div
      ref="chatContainer"
      style="flex:1;overflow-y:auto;padding:16px;position:relative"
      @scroll="onScroll"
    >
      <TransitionGroup name="msg" tag="div">
        <template v-for="m in messages" :key="m.id">
          <!-- Time separator -->
          <TimeSeparator v-if="showTimeSeparator(m)" :time="m.timestamp!" />

          <div style="margin-bottom:4px">
            <ChatBubble
              :role="m.role"
              :text="m.text"
              :avatar="m.role === 'ai' ? sceneAvatar : undefined"
              :corrected-text="m.correctedText"
              :corrections="m.corrections"
              :pronunciation-score="m.pronunciationScore"
              :audio-base64="m.audioBase64"
              :audio-url="m.audioUrl"
              @regenerate="handleRegenerate"
            />
          </div>
        </template>
      </TransitionGroup>

      <!-- Typing indicator (replaces old NSpin + text) -->
      <TypingBubble v-if="loading" />

      <!-- Floating "New messages" button -->
      <transition name="scroll-btn">
        <div
          v-if="showScrollButton"
          :style="{
            position: 'sticky',
            bottom: '12px',
            display: 'flex',
            justifyContent: 'center',
            pointerEvents: 'none',
          }"
        >
          <NButton
            circle
            type="primary"
            size="small"
            :style="{ pointerEvents: 'auto', boxShadow: 'var(--shadow-md)' }"
            @click="scrollToBottom"
          >
            <template #icon><ArrowDownOutlined /></template>
          </NButton>
        </div>
      </transition>
    </div>

    <!-- Input area -->
    <div style="padding:12px 16px;border-top:1px solid var(--color-border);background:var(--color-bg-card)">
      <!-- Quick replies -->
      <QuickReplies
        :suggestions="quickSuggestions"
        @select="handleSendText"
      />

      <NSpace align="end" style="width:100%">
        <NInput
          v-model:value="textInput"
          type="textarea"
          placeholder="输入英语内容，或点击右侧麦克风语音输入..."
          :autosize="{ minRows: 1, maxRows: 3 }"
          :disabled="loading"
          style="flex:1"
          @keydown.enter.exact.prevent="handleSendText()"
        />
        <AudioRecorder
          :disabled="loading"
          @audio-ready="handleSendAudio"
        />
        <NButton
          type="primary"
          :disabled="!textInput.trim() || loading"
          @click="handleSendText()"
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

.scroll-btn-enter-active,
.scroll-btn-leave-active {
  transition: all 0.3s ease;
}
.scroll-btn-enter-from,
.scroll-btn-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>

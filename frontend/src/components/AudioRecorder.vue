<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import { AudioOutlined, PauseOutlined } from '@vicons/antd'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ 'text-ready': [text: string] }>()

const isRecording = ref(false)
const isSupported = ref(true)
const recordingTime = ref(0)

let recognition: any = null
let recordTimer: number | null = null
let timeTimer: number | null = null

// Check SpeechRecognition support
const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
if (!SpeechRecognitionAPI) {
  isSupported.value = false
}

function cleanup() {
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (timeTimer) { clearInterval(timeTimer); timeTimer = null }
  if (recognition) {
    try { recognition.stop() } catch {}
    recognition = null
  }
  isRecording.value = false
}

onBeforeUnmount(cleanup)

function startRecording() {
  if (props.disabled || isRecording.value || !isSupported.value) return

  try {
    recognition = new SpeechRecognitionAPI()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.continuous = false
    recognition.maxAlternatives = 1

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript?.trim()
      if (text) {
        emit('text-ready', text)
      }
    }

    recognition.onerror = (event: any) => {
      // 'no-speech' is not really an error — user just didn't speak
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        console.error('Speech recognition error:', event.error)
      }
      cleanup()
    }

    recognition.onend = () => {
      cleanup()
    }

    recognition.start()
    isRecording.value = true
    recordingTime.value = 0

    timeTimer = window.setInterval(() => {
      recordingTime.value++
    }, 1000)

    // Auto-stop after 30 seconds
    recordTimer = window.setTimeout(() => {
      stopRecording()
    }, 30000)
  } catch (e) {
    isSupported.value = false
    console.error('Speech recognition failed:', e)
  }
}

function stopRecording() {
  if (!isRecording.value) return
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (timeTimer) { clearInterval(timeTimer); timeTimer = null }

  if (recognition) {
    try { recognition.stop() } catch {}
    recognition = null
  }
  isRecording.value = false
}
</script>

<template>
  <div style="display:flex;align-items:center;gap:4px">
    <NButton
      v-if="isSupported"
      :type="isRecording ? 'error' : 'default'"
      :disabled="disabled"
      circle
      size="large"
      @mousedown.prevent="startRecording"
      @mouseup.prevent="stopRecording"
      @mouseleave="isRecording ? stopRecording() : undefined"
      @touchstart.prevent="startRecording"
      @touchend.prevent="stopRecording"
      :style="isRecording ? 'animation:pulse 1s infinite' : ''"
    >
      <template #icon>
        <AudioOutlined v-if="!isRecording" />
        <PauseOutlined v-else />
      </template>
    </NButton>
    <span v-if="!isSupported" style="font-size:12px;color:#999" title="浏览器不支持语音识别，请使用Chrome或Edge">
      麦克风不可用
    </span>
    <span v-if="isRecording" style="font-size:12px;color:#d03050;min-width:36px">
      {{ recordingTime }}s
    </span>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(208,48,80,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(208,48,80,0); }
}
</style>

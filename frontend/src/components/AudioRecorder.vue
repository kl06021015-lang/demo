<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import { AudioOutlined, PauseOutlined } from '@vicons/antd'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ 'audio-ready': [blob: Blob] }>()

const isRecording = ref(false)
const isSupported = ref(true)
let mediaRecorder: MediaRecorder | null = null
let stream: MediaStream | null = null
let chunks: Blob[] = []
let recordTimer: number | null = null

function cleanup() {
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  if (stream) {
    stream.getTracks().forEach(t => t.stop())
    stream = null
  }
  mediaRecorder = null
  chunks = []
}

onBeforeUnmount(cleanup)

async function startRecording() {
  if (props.disabled || isRecording.value) return
  chunks = []

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'

    mediaRecorder = new MediaRecorder(stream, { mimeType })
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }
    mediaRecorder.onstop = () => {
      if (chunks.length > 0) {
        const blob = new Blob(chunks, { type: mimeType })
        emit('audio-ready', blob)
      }
      cleanup()
    }

    mediaRecorder.start()
    isRecording.value = true

    // Auto-stop after 30 seconds
    recordTimer = window.setTimeout(() => {
      stopRecording()
    }, 30000)
  } catch (e) {
    isSupported.value = false
    console.error('Microphone access denied:', e)
  }
}

function stopRecording() {
  if (!isRecording.value) return
  isRecording.value = false
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  } else {
    cleanup()
  }
}
</script>

<template>
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
  <span v-else style="font-size:12px;color:#999">麦克风不可用</span>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(208,48,80,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(208,48,80,0); }
}
</style>

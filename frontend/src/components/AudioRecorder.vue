<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import { AudioOutlined, PauseOutlined } from '@vicons/antd'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ 'audio-ready': [blob: Blob] }>()

const SAMPLE_RATE = 16000

const isRecording = ref(false)
const isSupported = ref(true)
const recordingTime = ref(0)

let stream: MediaStream | null = null
let audioContext: AudioContext | null = null
let scriptNode: ScriptProcessorNode | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let samples: Float32Array[] = []
let recordTimer: number | null = null
let timeTimer: number | null = null

function cleanup() {
  if (recordTimer) { clearTimeout(recordTimer); recordTimer = null }
  if (timeTimer) { clearInterval(timeTimer); timeTimer = null }
  if (scriptNode) {
    scriptNode.disconnect()
    scriptNode = null
  }
  if (sourceNode) {
    sourceNode.disconnect()
    sourceNode = null
  }
  if (audioContext && audioContext.state !== 'closed') {
    audioContext.close()
    audioContext = null
  }
  if (stream) {
    stream.getTracks().forEach(t => t.stop())
    stream = null
  }
  samples = []
}

onBeforeUnmount(cleanup)

function encodeWav(sampleArrays: Float32Array[]): Blob {
  // Flatten all sample chunks
  const totalLen = sampleArrays.reduce((sum, a) => sum + a.length, 0)
  const buffer = new ArrayBuffer(44 + totalLen * 2)
  const view = new DataView(buffer)

  function writeStr(offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  // RIFF header
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + totalLen * 2, true)  // file size - 8
  writeStr(8, 'WAVE')

  // fmt chunk
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)       // chunk size
  view.setUint16(20, 1, true)        // PCM format
  view.setUint16(22, 1, true)        // mono
  view.setUint32(24, SAMPLE_RATE, true)
  view.setUint32(28, SAMPLE_RATE * 2, true)  // byte rate
  view.setUint16(32, 2, true)        // block align
  view.setUint16(34, 16, true)       // bits per sample

  // data chunk
  writeStr(36, 'data')
  view.setUint32(40, totalLen * 2, true)

  // PCM samples (Float32 [-1,1] → Int16)
  let offset = 44
  for (const arr of sampleArrays) {
    for (let i = 0; i < arr.length; i++) {
      // Clamp to [-1, 1]
      const s = Math.max(-1, Math.min(1, arr[i]))
      // Convert to int16
      const int16 = s < 0 ? s * 0x8000 : s * 0x7FFF
      view.setInt16(offset, int16, true)
      offset += 2
    }
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

async function startRecording() {
  if (props.disabled || isRecording.value) return
  samples = []
  recordingTime.value = 0

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true }
    })

    audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })
    sourceNode = audioContext.createMediaStreamSource(stream)

    // ScriptProcessorNode for raw PCM capture
    scriptNode = audioContext.createScriptProcessor(4096, 1, 1)
    scriptNode.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0)
      // Copy the Float32Array (it's reused by the browser)
      samples.push(new Float32Array(input))
    }

    sourceNode.connect(scriptNode)
    scriptNode.connect(audioContext.destination)

    isRecording.value = true

    // Timer display
    timeTimer = window.setInterval(() => {
      recordingTime.value++
    }, 1000)

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
  if (timeTimer) { clearInterval(timeTimer); timeTimer = null }

  // Disconnect audio nodes
  if (scriptNode) {
    scriptNode.disconnect()
    scriptNode.onaudioprocess = null
    scriptNode = null
  }
  if (sourceNode) {
    sourceNode.disconnect()
    sourceNode = null
  }

  if (samples.length > 0) {
    const wav = encodeWav(samples)
    emit('audio-ready', wav)
  }

  // Close audio context and stream
  if (audioContext && audioContext.state !== 'closed') {
    audioContext.close()
    audioContext = null
  }
  if (stream) {
    stream.getTracks().forEach(t => t.stop())
    stream = null
  }
  samples = []
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
    <span v-if="!isSupported" style="font-size:12px;color:#999">麦克风不可用</span>
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

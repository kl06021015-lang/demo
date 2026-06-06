<script setup lang="ts">
import { ref } from 'vue'
import { NSpace, NTag, NButton, NPopover, NIcon, NTooltip } from 'naive-ui'
import { SoundOutlined, ExclamationCircleOutlined, CheckCircleOutlined } from '@vicons/antd'
import type { Correction, PronunciationScore } from '../api'

const props = defineProps<{
  role: 'user' | 'ai' | 'system'
  text: string
  correctedText?: string
  corrections?: Correction[]
  pronunciationScore?: PronunciationScore | null
  audioBase64?: string
}>()

const audioPlaying = ref(false)

function playAudio() {
  if (!props.audioBase64 || audioPlaying.value) return
  try {
    const binary = atob(props.audioBase64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: 'audio/mp3' })
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audioPlaying.value = true
    audio.play().catch(() => {})
    audio.onended = () => {
      audioPlaying.value = false
      URL.revokeObjectURL(url)
    }
  } catch { audioPlaying.value = false }
}

function correctionTypeColor(t: string) {
  const map: Record<string, string> = {
    grammar: '#d03050',
    word_choice: '#f0a020',
    politeness: '#2080f0',
    other: '#999',
  }
  return map[t] || '#999'
}
</script>

<template>
  <div
    :style="{
      display: 'flex',
      flexDirection: 'column',
      alignItems: role === 'user' ? 'flex-end' : 'flex-start',
      marginBottom: '16px',
    }"
  >
    <!-- AI audio playback -->
    <div v-if="role === 'ai' && audioBase64" style="margin-bottom:4px">
      <NTooltip>
        <template #trigger>
          <NButton size="tiny" circle :type="audioPlaying ? 'primary' : 'default'" @click="playAudio">
            <template #icon><SoundOutlined /></template>
          </NButton>
        </template>
        {{ audioPlaying ? '播放中...' : '点击播放' }}
      </NTooltip>
    </div>

    <!-- Bubble -->
    <div
      :style="{
        maxWidth: '75%',
        padding: '10px 16px',
        borderRadius: '16px',
        background: role === 'user' ? '#2080f0' : role === 'system' ? '#f6f6f6' : '#f0f7ff',
        color: role === 'user' ? '#fff' : '#333',
        fontSize: '15px',
        lineHeight: '1.6',
        wordBreak: 'break-word',
        position: 'relative',
      }"
    >
      <!-- Corrected text hint for user messages -->
      <div v-if="correctedText && correctedText !== text" style="margin-bottom:6px;font-size:13px;opacity:0.85">
        💡 {{ correctedText }}
      </div>

      {{ text }}
    </div>

    <!-- Corrections (user messages only) -->
    <div v-if="role === 'user' && corrections?.length" style="margin-top:8px;max-width:75%">
      <NSpace vertical :size="6">
        <div
          v-for="(c, i) in corrections"
          :key="i"
          :style="{
            padding: '6px 10px',
            borderRadius: '8px',
            background: '#fff8f0',
            border: '1px solid #fedcbd',
            fontSize: '13px',
          }"
        >
          <div style="margin-bottom:2px">
            <NTag :color="{color:correctionTypeColor(c.type),textColor:'#fff'}" size="tiny">{{ c.type }}</NTag>
            <span style="text-decoration:line-through;color:#d03050;margin-left:4px">{{ c.original }}</span>
            <span style="color:#333"> → </span>
            <span style="color:#18a058;font-weight:500">{{ c.corrected }}</span>
          </div>
          <div style="color:#666;font-size:12px">{{ c.explanation }}</div>
        </div>
      </NSpace>
    </div>

    <!-- Pronunciation score (user messages only) -->
    <div v-if="role === 'user' && pronunciationScore" style="margin-top:4px">
      <NTag :type="pronunciationScore.overall >= 7 ? 'success' : pronunciationScore.overall >= 5 ? 'warning' : 'error'" size="small" round>
        🎤 发音 {{ pronunciationScore.overall.toFixed(1) }}
      </NTag>
    </div>
  </div>
</template>

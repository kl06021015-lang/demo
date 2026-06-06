<script setup lang="ts">
import { ref, computed } from 'vue'
import { NSpace, NTag, NButton, NIcon, NTooltip, useMessage } from 'naive-ui'
import { SoundOutlined, CopyOutlined, ReloadOutlined } from '@vicons/antd'
import type { Correction, PronunciationScore } from '../api'

const props = defineProps<{
  role: 'user' | 'ai' | 'system'
  text: string
  avatar?: string               // emoji avatar for AI messages
  correctedText?: string
  corrections?: Correction[]
  pronunciationScore?: PronunciationScore | null
  audioBase64?: string
  timestamp?: string             // ISO timestamp for time separators
}>()

const emit = defineEmits<{
  regenerate: []
}>()

const msg = useMessage()
const audioPlaying = ref(false)

// ---------------------------------------------------------------------------
// Audio playback
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Copy to clipboard
// ---------------------------------------------------------------------------
async function copyText() {
  try {
    await navigator.clipboard.writeText(props.text)
    msg.success('已复制到剪贴板')
  } catch {
    msg.error('复制失败')
  }
}

// ---------------------------------------------------------------------------
// Correction type color
// ---------------------------------------------------------------------------
function correctionTypeColor(t: string) {
  const map: Record<string, string> = {
    grammar: 'var(--color-error)',
    word_choice: 'var(--color-warning)',
    politeness: 'var(--color-primary)',
    other: 'var(--color-text-tertiary)',
  }
  return map[t] || 'var(--color-text-tertiary)'
}

// ---------------------------------------------------------------------------
// Avatar emoji map (fallback)
// ---------------------------------------------------------------------------
const defaultAvatar = computed(() => {
  if (props.role !== 'ai') return ''
  return props.avatar || '🤖'
})
</script>

<template>
  <div
    :style="{
      display: 'flex',
      flexDirection: 'column',
      alignItems: role === 'user' ? 'flex-end' : 'flex-start',
      marginBottom: 'var(--spacing-md)',
    }"
  >
    <!-- AI Avatar + Name row -->
    <div
      v-if="role === 'ai' && avatar"
      :style="{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '6px',
        marginLeft: '4px',
      }"
    >
      <span :style="{ fontSize: '22px' }">{{ avatar }}</span>
    </div>

    <!-- AI audio playback (above bubble) -->
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
        borderRadius: 'var(--radius-lg)',
        borderBottomRightRadius: role === 'user' ? '4px' : undefined,
        borderBottomLeftRadius: role === 'ai' ? '4px' : undefined,
        background: role === 'user'
          ? 'linear-gradient(135deg, var(--color-primary), var(--color-primary-active))'
          : role === 'system'
            ? 'var(--color-bg-input)'
            : 'var(--color-bg-card)',
        color: role === 'user'
          ? 'var(--color-text-inverse)'
          : 'var(--color-text-primary)',
        fontSize: 'var(--font-size-body)',
        lineHeight: 'var(--line-height-tight)',
        wordBreak: 'break-word',
        position: 'relative',
        boxShadow: 'var(--shadow-xs)',
      }"
    >
      <!-- Corrected text hint for user messages -->
      <div v-if="correctedText && correctedText !== text" style="margin-bottom:6px;font-size:var(--font-size-small);opacity:0.85">
        💡 {{ correctedText }}
      </div>

      {{ text }}
    </div>

    <!-- Message actions (AI messages only) -->
    <div
      v-if="role === 'ai' && text"
      :style="{
        display: 'flex',
        gap: '4px',
        marginTop: '4px',
        marginLeft: '4px',
      }"
    >
      <NButton size="tiny" text @click="playAudio" :disabled="!audioBase64" :style="{ fontSize: 'var(--font-size-caption)' }">
        🔊 朗读
      </NButton>
      <NButton size="tiny" text @click="copyText" :style="{ fontSize: 'var(--font-size-caption)' }">
        📋 复制
      </NButton>
      <NButton size="tiny" text @click="emit('regenerate')" :style="{ fontSize: 'var(--font-size-caption)' }">
        🔄 重新生成
      </NButton>
    </div>

    <!-- Corrections (user messages only) -->
    <div v-if="role === 'user' && corrections?.length" style="margin-top:var(--spacing-sm);max-width:75%">
      <NSpace vertical :size="6">
        <div
          v-for="(c, i) in corrections"
          :key="i"
          :style="{
            padding: '6px 10px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--color-bg-correction)',
            border: '1px solid var(--color-border-correction)',
            fontSize: 'var(--font-size-small)',
          }"
        >
          <div style="margin-bottom:2px">
            <NTag :color="{color:correctionTypeColor(c.type),textColor:'#fff'}" size="tiny">{{ c.type }}</NTag>
            <span style="text-decoration:line-through;color:var(--color-error);margin-left:4px">{{ c.original }}</span>
            <span style="color:var(--color-text-primary)"> → </span>
            <span style="color:var(--color-success);font-weight:500">{{ c.corrected }}</span>
          </div>
          <div style="color:var(--color-text-secondary);font-size:var(--font-size-caption)">{{ c.explanation }}</div>
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

<style scoped>
/* Action buttons show subtle hover */
:deep(.n-button--text) {
  opacity: 0.6;
  transition: opacity var(--transition-fast);
}
:deep(.n-button--text:hover) {
  opacity: 1;
}
</style>

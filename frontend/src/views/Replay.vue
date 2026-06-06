<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NCard, NButton, NTag, NSpace, NSpin, NAlert, useMessage } from 'naive-ui'
import { ArrowLeftOutlined, SoundOutlined } from '@vicons/antd'
import { getConversation, type TurnData } from '../api'

const route = useRoute()
const router = useRouter()
const msg = useMessage()

const sessionId = route.params.sessionId as string
const loading = ref(true)
const error = ref('')
const sceneName = ref('')
const turns = ref<TurnData[]>([])

onMounted(async () => {
  try {
    const doc = await getConversation(sessionId)
    sceneName.value = doc.scene_id
    turns.value = doc.messages.filter((m: TurnData) => m.user_text || m.ai_text)
  } catch (e: any) {
    error.value = e.message || 'Failed to load conversation'
  } finally {
    loading.value = false
  }
})

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
  } catch { /* silent */ }
}

function wpmLabel(wpm: number): string {
  if (!wpm) return ''
  if (wpm < 80) return '偏慢'
  if (wpm <= 150) return '正常'
  return '偏快'
}
</script>

<template>
  <div style="max-width:720px;margin:0 auto;padding:24px 16px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px">
      <NButton text @click="router.back()">
        <template #icon><ArrowLeftOutlined /></template>
      </NButton>
      <h2 style="margin:0">🔄 对话回放</h2>
      <NTag size="small">{{ sceneName }}</NTag>
    </div>

    <NSpin :show="loading">
      <NAlert v-if="error" type="error" :title="error" style="margin-bottom:16px" />

      <div v-if="!loading && turns.length" style="display:flex;flex-direction:column;gap:16px">
        <NCard v-for="(t, idx) in turns" :key="idx" size="small"
               :style="{background: t.user_text ? '#fafafa' : '#f0f7ff'}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
            <div style="flex:1">
              <div style="font-size:12px;color:#999;margin-bottom:4px">
                {{ t.user_text ? '👤 你' : '🤖 AI' }} · 第 {{ t.turn }} 轮
                <NTag v-if="(t as any).speaking_wpm" size="tiny" style="margin-left:4px">
                  🗣️ {{ (t as any).speaking_wpm }} WPM {{ wpmLabel((t as any).speaking_wpm) }}
                </NTag>
              </div>
              <div style="font-size:15px;line-height:1.6;white-space:pre-wrap">{{ t.user_text || t.ai_text }}</div>

              <!-- Corrections -->
              <div v-if="t.corrections?.length" style="margin-top:8px">
                <div v-for="(c, ci) in t.corrections" :key="ci"
                     style="padding:4px 8px;margin-bottom:4px;background:#fff8f0;border-radius:4px;font-size:12px">
                  <span style="text-decoration:line-through;color:#d03050">{{ c.original }}</span>
                  <span> → </span>
                  <span style="color:#18a058;font-weight:500">{{ c.corrected }}</span>
                  <span style="color:#888;margin-left:4px">{{ c.explanation }}</span>
                </div>
              </div>
            </div>

            <!-- Play audio button for AI turns with audio stored -->
            <NButton v-if="!t.user_text" size="tiny" circle @click="playAudio((t as any).audio_base64)"
                     :disabled="!(t as any).audio_base64">
              <template #icon><SoundOutlined /></template>
            </NButton>
          </div>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

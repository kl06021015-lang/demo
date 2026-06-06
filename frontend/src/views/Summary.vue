<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NCard, NButton, NTag, NSpin, NAlert, NSpace, NDivider } from 'naive-ui'
import { endConversation, getConversation, type ConversationSummary, type SummaryData } from '../api'

const route = useRoute()
const router = useRouter()

const sessionId = route.params.sessionId as string
const loading = ref(true)
const error = ref('')
const summary = ref<ConversationSummary | null>(null)

onMounted(async () => {
  try {
    const conv = await getConversation(sessionId)
    if (conv.ended_at) {
      // Already ended — use existing summary from the stored conversation
      const msgs = conv.messages.filter((m: any) => m.user_text)
      summary.value = {
        session_id: conv.session_id,
        duration_minutes: msgs.length * 0.5,
        total_turns: msgs.length,
        summary: conv.summary?.overall_score != null ? conv.summary : {
          overall_score: 0,
          grammar_highlights: [],
          pronunciation_highlights: [],
          vocabulary_used: [],
          strengths: [],
          suggestions: [],
          encouragement: "No summary available",
        },
      }
    } else {
      // End it now to generate summary
      const result = await endConversation(sessionId)
      summary.value = result
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load summary'
  } finally {
    loading.value = false
  }
})

function goHome() {
  router.push({ name: 'home' })
}

async function exportReport() {
  try {
    const resp = await fetch(`/api/conversations/${sessionId}/export`)
    if (!resp.ok) throw new Error('Export failed')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `english-practice-report-${sessionId}.html`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // silently fail — the button will just do nothing
  }
}

function scoreColor(s: number): string {
  if (s >= 8) return '#18a058'
  if (s >= 6) return '#f0a020'
  return '#d03050'
}
</script>

<template>
  <div style="max-width:800px;margin:0 auto;padding:32px 16px">
    <NSpin :show="loading">
      <NAlert v-if="error" type="error" :title="error" style="margin-bottom:16px" />

      <template v-if="summary">
        <!-- Overall Score -->
        <NCard style="text-align:center;margin-bottom:24px">
          <h2 style="margin-bottom:16px">📊 课后总结</h2>
          <div style="font-size:14px;color:#666;margin-bottom:8px">
            场景：{{ summary.summary.vocabulary_used?.length || 0 }} 个词汇 ·
            {{ summary.total_turns }} 轮对话 ·
            {{ summary.duration_minutes }} 分钟
          </div>
          <div style="margin:16px auto;text-align:center">
            <div
              style="display:inline-flex;align-items:center;justify-content:center;
              width:120px;height:120px;border-radius:50%;
              border:6px solid currentColor;
              background:#f9f9f9"
              :style="{ color: scoreColor(summary.summary.overall_score ?? 0) }"
            >
              <div>
                <div style="font-size:36px;font-weight:700" :style="{color:scoreColor(summary.summary.overall_score ?? 0)}">
                  {{ (summary.summary.overall_score ?? 0).toFixed(1) }}
                </div>
                <div style="font-size:12px;color:#999;margin-top:2px">综合评分</div>
              </div>
            </div>
          </div>
        </NCard>

        <!-- Strengths -->
        <NCard v-if="summary.summary.strengths?.length" title="✅ 表现亮点" style="margin-bottom:16px">
          <ul style="padding-left:20px">
            <li v-for="s in summary.summary.strengths" :key="s" style="margin-bottom:4px;line-height:1.6">{{ s }}</li>
          </ul>
        </NCard>

        <!-- Grammar Highlights -->
        <NCard v-if="summary.summary.grammar_highlights?.length" title="📝 语法薄弱点" style="margin-bottom:16px">
          <div v-for="(g, i) in summary.summary.grammar_highlights" :key="i" style="margin-bottom:12px">
            <NSpace align="center" style="margin-bottom:4px">
              <NTag type="error" size="small">{{ g.count }}次</NTag>
              <strong>{{ g.pattern }}</strong>
            </NSpace>
            <div style="color:#666;font-size:13px;margin-bottom:4px">{{ g.suggestion }}</div>
            <NSpace v-if="g.examples?.length" :size="4" wrap>
              <NTag v-for="ex in g.examples" :key="ex" size="tiny" type="warning">"{{ ex }}"</NTag>
            </NSpace>
          </div>
        </NCard>

        <!-- Pronunciation Highlights -->
        <NCard v-if="summary.summary.pronunciation_highlights?.length" title="🔊 发音重点" style="margin-bottom:16px">
          <div v-for="(p, i) in summary.summary.pronunciation_highlights" :key="i" style="margin-bottom:12px">
            <div style="font-weight:600;margin-bottom:4px">
              音素 <NTag type="info" size="small">{{ p.phoneme }}</NTag>
            </div>
            <div style="color:#666;font-size:13px;margin-bottom:4px">问题：{{ p.issue }}</div>
            <NSpace :size="4" wrap>
              <NTag v-for="w in p.practice_words" :key="w" size="tiny" type="success">练习：{{ w }}</NTag>
            </NSpace>
          </div>
        </NCard>

        <!-- Suggestions -->
        <NCard v-if="summary.summary.suggestions?.length" title="💡 改进建议" style="margin-bottom:16px">
          <ul style="padding-left:20px">
            <li v-for="s in summary.summary.suggestions" :key="s" style="margin-bottom:6px;line-height:1.6">{{ s }}</li>
          </ul>
        </NCard>

        <!-- Encouragement -->
        <NCard v-if="summary.summary.encouragement" style="text-align:center;background:#f0f9ff;margin-bottom:24px">
          <div style="font-size:16px;line-height:1.8;color:#2080f0">
            {{ summary.summary.encouragement }}
          </div>
        </NCard>

        <!-- Actions -->
        <div style="text-align:center">
          <NSpace justify="center" :size="12">
            <NButton type="primary" size="large" @click="goHome">
              再练一次
            </NButton>
            <NButton size="large" @click="exportReport">
              📥 导出报告 (HTML)
            </NButton>
          </NSpace>
        </div>
      </template>
    </NSpin>
  </div>
</template>

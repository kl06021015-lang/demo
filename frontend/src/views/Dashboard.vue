<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NTag, NSpin, NEmpty, NGrid, NGridItem, NProgress, NSpace } from 'naive-ui'
import { getDashboard, getScenes, type DashboardData, type Scene } from '../api'

const router = useRouter()
const loading = ref(true)
const data = ref<DashboardData | null>(null)
const sceneMap = ref<Record<string, string>>({})

onMounted(async () => {
  try {
    const [dash, scenes] = await Promise.all([getDashboard(), getScenes()])
    data.value = dash
    // Build scene id -> name map
    for (const s of scenes.scenes) {
      sceneMap.value[s.id] = s.name
    }
  } catch {
    // silently handle
  } finally {
    loading.value = false
  }
})

function sceneName(id: string): string {
  return sceneMap.value[id] || id
}

function scoreColor(s: number): string {
  if (s >= 8) return '#18a058'
  if (s >= 6) return '#f0a020'
  return '#d03050'
}

const hasData = computed(() => data.value && data.value.total_sessions > 0)
const completionRate = computed(() => {
  if (!data.value || data.value.total_sessions === 0) return 0
  return Math.round((data.value.completed_sessions / data.value.total_sessions) * 100)
})
</script>

<template>
  <div style="max-width:900px;margin:0 auto;padding:32px 16px">
    <h2 style="margin-bottom:24px">📊 学习报告</h2>

    <NSpin :show="loading">
      <NEmpty v-if="!loading && !hasData" description="还没有学习数据，快去开始练习吧！">
        <template #extra>
          <NButton type="primary" @click="router.push({name:'home'})">去练习</NButton>
        </template>
      </NEmpty>

      <template v-if="hasData && data">
        <!-- Stats Row -->
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" style="margin-bottom:24px">
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700;color:#2080f0">{{ data.total_sessions }}</div>
              <div style="font-size:13px;color:#999">总练习次数</div>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700;color:#18a058">{{ data.total_minutes }}</div>
              <div style="font-size:13px;color:#999">练习时长 (分钟)</div>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700" :style="{color: scoreColor(data.average_score)}">{{ data.average_score }}</div>
              <div style="font-size:13px;color:#999">平均评分</div>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700;color:#f0a020">{{ completionRate }}%</div>
              <div style="font-size:13px;color:#999">完成率</div>
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- Scene Breakdown -->
        <NCard v-if="data.scenes_practiced.length" title="🎬 各场景练习统计" style="margin-bottom:24px">
          <div v-for="(s, i) in data.scenes_practiced" :key="s.scene_id" style="margin-bottom:16px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <span style="font-weight:500">{{ sceneName(s.scene_id) }}</span>
              <NSpace :size="8" align="center">
                <NTag size="small">{{ s.count }} 次</NTag>
                <NTag size="small" :type="s.avg_score >= 7 ? 'success' : s.avg_score >= 5 ? 'warning' : 'error'">
                  均分 {{ s.avg_score }}
                </NTag>
              </NSpace>
            </div>
            <NProgress
              :percentage="Math.round(s.avg_score * 10)"
              :color="scoreColor(s.avg_score)"
              :height="8"
              :border-radius="4"
              :show-indicator="false"
            />
          </div>
        </NCard>

        <!-- Summary -->
        <NCard style="text-align:center;background:#f0f9ff">
          <div style="font-size:15px;line-height:1.8;color:#2080f0">
            {{ data.completed_sessions > 0
                ? `你已完成 ${data.completed_sessions} 次练习，累计 ${data.total_minutes} 分钟。继续加油！💪`
                : '开始你的第一次练习吧！🎯'
            }}
          </div>
        </NCard>
      </template>
    </NSpin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NGrid, NGridItem, NTag, NButton, NSpin, NSpace, NIcon,
  NEmpty, NAlert, NProgress, NTabs, NTabPane, useMessage
} from 'naive-ui'
import { ThunderboltOutlined, BulbOutlined } from '@vicons/antd'
import { getScenes, createConversation, getDashboard, type Scene, type SceneStats } from '../api'

const router = useRouter()
const message = useMessage()

const scenes = ref<Scene[]>([])
const sceneStats = ref<Map<string, SceneStats>>(new Map())
const loading = ref(true)
const creating = ref<string | null>(null)
const error = ref('')
const activeFilter = ref('全部')

// Scene icon mapping
const iconMap: Record<string, string> = {
  'coffee-shop': '☕',
  'hotel-checkin': '🏨',
  'restaurant': '🍽️',
  'shopping': '🛍️',
  'doctor-visit': '🏥',
  'job-interview': '💼',
  'academic-discussion': '🎓',
  'apartment-viewing': '🏠',
  'debate-competition': '🎤',
}

// Practice time estimates by difficulty
const timeEstimates: Record<string, string> = {
  'beginner': '约 3 分钟',
  'intermediate': '约 5 分钟',
  'advanced': '约 8 分钟',
}

onMounted(async () => {
  try {
    const [scenesData, dashData] = await Promise.all([getScenes(), getDashboard()])
    scenes.value = scenesData.scenes
    const statsMap = new Map<string, SceneStats>()
    for (const s of dashData.scenes_practiced) {
      statsMap.set(s.scene_id, s)
    }
    sceneStats.value = statsMap
  } catch (e: any) {
    error.value = e.message || 'Failed to load scenes'
  } finally {
    loading.value = false
  }
})

// Filtered scenes
const filteredScenes = computed(() => {
  if (activeFilter.value === '全部') return scenes.value
  const diffMap: Record<string, string> = {
    '初级': 'beginner',
    '中级': 'intermediate',
    '高级': 'advanced',
  }
  return scenes.value.filter(s => s.difficulty === diffMap[activeFilter.value])
})

const filterTabs = ['全部', '初级', '中级', '高级']

async function startPractice(scene: Scene) {
  creating.value = scene.id
  try {
    const conv = await createConversation(scene.id)
    router.push({
      name: 'practice',
      params: { sceneId: scene.id },
      query: { session: conv.session_id },
    })
  } catch (e: any) {
    message.error(e.message || 'Failed to start conversation')
  } finally {
    creating.value = null
  }
}

function difficultyLabel(d: string) {
  return d === 'beginner' ? '初级' : d === 'intermediate' ? '中级' : '高级'
}

function difficultyColor(d: string) {
  return d === 'beginner' ? 'success' : d === 'intermediate' ? 'warning' : 'error'
}

function getPracticeCount(sceneId: string): number {
  return sceneStats.value.get(sceneId)?.count ?? 0
}

function getProgress(sceneId: string): number {
  const count = getPracticeCount(sceneId)
  return Math.min(100, count * 25) // 4 practices = 100% "mastered"
}

function isMastered(sceneId: string): boolean {
  return getPracticeCount(sceneId) >= 4
}
</script>

<template>
  <div style="max-width:var(--max-width-wide);margin:0 auto;padding:var(--spacing-xl) var(--spacing-md)">
    <!-- Header -->
    <div style="text-align:center;margin-bottom:var(--spacing-2xl)">
      <h2 style="font-size:var(--font-size-title);margin-bottom:var(--spacing-sm);font-weight:var(--font-weight-bold)">
        🎯 选择练习场景
      </h2>
      <p style="color:var(--color-text-secondary);font-size:var(--font-size-body)">
        选择一个场景开始英语对话练习，AI 会扮演对应角色与你互动
      </p>
    </div>

    <!-- Difficulty filter tabs -->
    <div style="display:flex;justify-content:center;margin-bottom:var(--spacing-xl)">
      <NTabs
        v-model:value="activeFilter"
        type="segment"
        size="large"
        animated
      >
        <NTabPane v-for="tab in filterTabs" :key="tab" :name="tab" :tab="tab" />
      </NTabs>
    </div>

    <NSpin :show="loading">
      <NAlert v-if="error" type="error" :title="error" style="margin-bottom:var(--spacing-md)" />

      <!-- Scene cards -->
      <NGrid v-if="filteredScenes.length" cols="1 s:2 m:3" :x-gap="20" :y-gap="20" responsive="screen">
        <NGridItem v-for="scene in filteredScenes" :key="scene.id">
          <NCard
            hoverable
            style="cursor:pointer;height:100%;border-radius:var(--radius-lg);overflow:hidden;transition:all var(--transition-base)"
            :style="{
              borderColor: isMastered(scene.id) ? 'var(--color-primary)' : undefined,
            }"
            @click="startPractice(scene)"
          >
            <!-- Scene icon -->
            <div style="text-align:center;margin-bottom:var(--spacing-md)">
              <div
                :style="{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  background: 'var(--color-primary-light)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '32px',
                }"
              >
                {{ iconMap[scene.id] || '🎯' }}
              </div>
            </div>

            <!-- Scene name + difficulty -->
            <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:var(--spacing-sm)">
              <h3 style="font-size:var(--font-size-heading);font-weight:var(--font-weight-semibold);margin:0">
                {{ scene.name }}
              </h3>
              <NTag :type="difficultyColor(scene.difficulty)" size="small" :bordered="false">
                {{ difficultyLabel(scene.difficulty) }}
              </NTag>
              <!-- Mastered badge -->
              <span v-if="isMastered(scene.id)" style="font-size:20px" title="已掌握">✅</span>
            </div>

            <!-- Description -->
            <p style="color:var(--color-text-secondary);min-height:40px;margin-bottom:var(--spacing-md);font-size:var(--font-size-small);text-align:center">
              {{ scene.description }}
            </p>

            <!-- Practice info -->
            <div style="text-align:center;margin-bottom:var(--spacing-sm)">
              <span style="font-size:var(--font-size-caption);color:var(--color-text-tertiary)">
                ⏱ {{ timeEstimates[scene.difficulty] || '约 5 分钟' }}
                <span v-if="getPracticeCount(scene.id) > 0">
                  · 已练习 {{ getPracticeCount(scene.id) }} 次
                </span>
              </span>
            </div>

            <!-- Progress bar -->
            <div v-if="getPracticeCount(scene.id) > 0" style="margin-bottom:var(--spacing-md)">
              <NProgress
                :percentage="getProgress(scene.id)"
                :height="6"
                :border-radius="3"
                :color="isMastered(scene.id) ? 'var(--color-success)' : 'var(--color-primary)'"
                :show-indicator="false"
              />
            </div>

            <!-- Vocabulary tags -->
            <div v-if="scene.suggested_vocabulary?.length" style="margin-bottom:var(--spacing-sm)">
              <NSpace :size="4" wrap justify="center">
                <NTag v-for="w in scene.suggested_vocabulary.slice(0, 3)" :key="w" size="tiny" :bordered="false">
                  {{ w }}
                </NTag>
                <span v-if="scene.suggested_vocabulary.length > 3" style="font-size:var(--font-size-caption);color:var(--color-text-tertiary)">
                  +{{ scene.suggested_vocabulary.length - 3 }}
                </span>
              </NSpace>
            </div>

            <!-- Grammar tags -->
            <div v-if="scene.grammar_focus?.length" style="margin-bottom:var(--spacing-md)">
              <NSpace :size="4" wrap justify="center">
                <NTag v-for="g in scene.grammar_focus.slice(0, 2)" :key="g" size="tiny" type="info" :bordered="false">
                  {{ g }}
                </NTag>
                <span v-if="scene.grammar_focus.length > 2" style="font-size:var(--font-size-caption);color:var(--color-text-tertiary)">
                  +{{ scene.grammar_focus.length - 2 }}
                </span>
              </NSpace>
            </div>

            <!-- Action button -->
            <template #footer>
              <NButton
                type="primary"
                block
                :loading="creating === scene.id"
                @click.stop="startPractice(scene)"
                :style="{
                  borderRadius: 'var(--radius-sm)',
                  fontWeight: 'var(--font-weight-semibold)',
                }"
              >
                {{ creating === scene.id ? '正在创建...' : isMastered(scene.id) ? '再来一次 🎯' : '开始练习' }}
              </NButton>
            </template>
          </NCard>
        </NGridItem>
      </NGrid>

      <NEmpty v-if="!loading && !filteredScenes.length && !error" description="暂无可用的练习场景" />
    </NSpin>
  </div>
</template>

<style scoped>
/* Card hover lift effect (Spotify style) */
:deep(.n-card) {
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
:deep(.n-card:hover) {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg) !important;
}
</style>

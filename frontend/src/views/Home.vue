<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NGrid, NGridItem, NTag, NButton, NSpin, NSpace, NIcon,
  NEmpty, NAlert, useMessage
} from 'naive-ui'
import { ThunderboltOutlined, BulbOutlined } from '@vicons/antd'
import { getScenes, createConversation, type Scene } from '../api'

const router = useRouter()
const message = useMessage()

const scenes = ref<Scene[]>([])
const loading = ref(true)
const creating = ref<string | null>(null)  // sceneId being created
const error = ref('')

onMounted(async () => {
  try {
    const data = await getScenes()
    scenes.value = data.scenes
  } catch (e: any) {
    error.value = e.message || 'Failed to load scenes'
  } finally {
    loading.value = false
  }
})

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

function difficultyColor(d: string) {
  return d === 'beginner' ? 'success' : d === 'intermediate' ? 'warning' : 'error'
}
function difficultyLabel(d: string) {
  return d === 'beginner' ? '初级' : d === 'intermediate' ? '中级' : '高级'
}
</script>

<template>
  <div style="max-width:1000px;margin:0 auto;padding:32px 16px">
    <div style="text-align:center;margin-bottom:32px">
      <h2 style="font-size:28px;margin-bottom:8px">选择练习场景</h2>
      <p style="color:#666">选择一个场景开始英语对话练习，AI 会扮演对应角色与你互动</p>
    </div>

    <NSpin :show="loading">
      <NAlert v-if="error" type="error" :title="error" style="margin-bottom:16px" />

      <NGrid v-if="scenes.length" cols="1 s:2 m:3" :x-gap="16" :y-gap="16" responsive="screen">
        <NGridItem v-for="scene in scenes" :key="scene.id">
          <NCard
            hoverable
            :title="scene.name"
            style="cursor:pointer;height:100%"
            @click="startPractice(scene)"
          >
            <template #header-extra>
              <NTag :type="difficultyColor(scene.difficulty)" size="small">
                {{ difficultyLabel(scene.difficulty) }}
              </NTag>
            </template>

            <p style="color:#555;min-height:44px;margin-bottom:12px">{{ scene.description }}</p>

            <NSpace vertical :size="8">
              <div v-if="scene.suggested_vocabulary?.length">
                <span style="font-size:12px;color:#999">核心词汇：</span>
                <NSpace :size="4" wrap>
                  <NTag v-for="w in scene.suggested_vocabulary" :key="w" size="tiny" :bordered="false">
                    {{ w }}
                  </NTag>
                </NSpace>
              </div>
              <div v-if="scene.grammar_focus?.length">
                <span style="font-size:12px;color:#999">语法重点：</span>
                <NSpace :size="4" wrap>
                  <NTag v-for="g in scene.grammar_focus" :key="g" size="tiny" type="info" :bordered="false">
                    {{ g }}
                  </NTag>
                </NSpace>
              </div>
            </NSpace>

            <template #footer>
              <NButton
                type="primary"
                block
                :loading="creating === scene.id"
                @click.stop="startPractice(scene)"
              >
                {{ creating === scene.id ? '正在创建...' : '开始练习' }}
              </NButton>
            </template>
          </NCard>
        </NGridItem>
      </NGrid>

      <NEmpty v-if="!loading && !scenes.length && !error" description="暂无可用的练习场景" />
    </NSpin>
  </div>
</template>

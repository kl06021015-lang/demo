<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NTag, NSpin, NEmpty, NSpace } from 'naive-ui'
import { getConversationList, type ConversationListItem } from '../api'

const router = useRouter()
const loading = ref(true)
const items = ref<ConversationListItem[]>([])

onMounted(async () => {
  try {
    const data = await getConversationList(50)
    items.value = data.conversations
  } catch (e) {
    // Silently handle — show empty state
  } finally {
    loading.value = false
  }
})

function formatDate(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function goTo(item: ConversationListItem) {
  if (item.ended_at) {
    router.push({ name: 'summary', params: { sessionId: item.session_id } })
  } else {
    router.push({ name: 'practice', params: { sceneId: item.scene_id }, query: { session: item.session_id } })
  }
}
</script>

<template>
  <div style="max-width:800px;margin:0 auto;padding:32px 16px">
    <h2 style="margin-bottom:24px">📋 练习记录</h2>

    <NSpin :show="loading">
      <NEmpty v-if="!loading && items.length === 0" description="还没有练习记录，快去开始练习吧！">
        <template #extra>
          <NButton type="primary" @click="router.push({name:'home'})">去练习</NButton>
        </template>
      </NEmpty>

      <div v-else style="display:flex;flex-direction:column;gap:12px">
        <NCard
          v-for="item in items"
          :key="item.session_id"
          hoverable
          style="cursor:pointer"
          @click="goTo(item)"
        >
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <div style="flex:1;min-width:200px">
              <div style="font-weight:600;font-size:15px;margin-bottom:4px">{{ item.scene_name }}</div>
              <div style="font-size:12px;color:#999">
                🕐 {{ formatDate(item.created_at) }}
              </div>
            </div>
            <NSpace align="center" :size="8" wrap>
              <NTag size="small" :bordered="false">💬 {{ item.turn_count }} 轮</NTag>
              <NTag v-if="item.ended_at" type="success" size="small" :bordered="false">已完成</NTag>
              <NTag v-else type="warning" size="small" :bordered="false">进行中</NTag>
              <NButton size="small" :type="item.ended_at ? 'primary' : 'warning'" :ghost="!item.ended_at">
                {{ item.ended_at ? '查看总结' : '继续练习' }}
              </NButton>
            </NSpace>
          </div>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

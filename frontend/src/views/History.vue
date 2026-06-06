<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NTag, NSpin, NEmpty, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import { getConversationList, deleteConversation, type ConversationListItem } from '../api'

const router = useRouter()
const msg = useMessage()
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

async function handleDelete(item: ConversationListItem) {
  try {
    await deleteConversation(item.session_id)
    items.value = items.value.filter(i => i.session_id !== item.session_id)
    msg.success('已删除')
  } catch (e: any) {
    msg.error(e.message || '删除失败')
  }
}
</script>

<template>
  <div style="max-width:var(--max-width-narrow);margin:0 auto;padding:var(--spacing-xl) var(--spacing-md)">
    <h2 style="margin-bottom:var(--spacing-lg);font-size:var(--font-size-heading)">📋 练习记录</h2>

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
              <div style="font-size:var(--font-size-caption);color:var(--color-text-tertiary)">
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
              <NPopconfirm @positive-click="() => handleDelete(item)">
                <template #trigger>
                  <NButton size="small" type="error" ghost @click.stop>删除</NButton>
                </template>
                确定要删除这条练习记录吗？删除后不可恢复。
              </NPopconfirm>
            </NSpace>
          </div>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

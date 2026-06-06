<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NInput, NSpace, NTag, NSpin, NEmpty, NPopconfirm, NModal, NTooltip, useMessage } from 'naive-ui'
import { PlusOutlined, ArrowLeftOutlined, CheckOutlined, CloseOutlined } from '@vicons/antd'
import {
  getVocabulary, addVocabulary, toggleWordMastered, deleteVocabulary,
  type VocabWord, type VocabStats
} from '../api'

const router = useRouter()
const msg = useMessage()

const loading = ref(true)
const words = ref<VocabWord[]>([])
const stats = ref<VocabStats>({ total: 0, mastered: 0, learning: 0 })
const showAdd = ref(false)
const filter = ref<'all' | 'learning' | 'mastered'>('all')
const newWord = ref({ word: '', meaning: '', context: '' })

async function load() {
  loading.value = true
  try {
    const mastered = filter.value === 'all' ? undefined : filter.value === 'mastered'
    const data = await getVocabulary(100, mastered)
    words.value = data.words
    stats.value = data.stats
  } catch { /* silent */ }
  finally { loading.value = false }
}

onMounted(load)

async function handleAdd() {
  const w = newWord.value.word.trim()
  if (!w) { msg.warning('请输入单词'); return }
  try {
    await addVocabulary(w, newWord.value.meaning, newWord.value.context)
    newWord.value = { word: '', meaning: '', context: '' }
    showAdd.value = false
    msg.success('已添加')
    await load()
  } catch (e: any) { msg.error(e.message || '添加失败') }
}

async function handleToggle(word: VocabWord) {
  try {
    await toggleWordMastered(word.id)
    await load()
  } catch { /* silent */ }
}

async function handleDelete(word: VocabWord) {
  try {
    await deleteVocabulary(word.id)
    await load()
    msg.success('已删除')
  } catch { /* silent */ }
}
</script>

<template>
  <div style="max-width:800px;margin:0 auto;padding:24px 16px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
      <NSpace align="center">
        <NButton text @click="router.push({name:'home'})">
          <template #icon><ArrowLeftOutlined /></template>
        </NButton>
        <h2 style="margin:0">📖 生词本</h2>
      </NSpace>
      <NButton type="primary" @click="showAdd = true">
        <template #icon><PlusOutlined /></template>
        添加单词
      </NButton>
    </div>

    <!-- Stats -->
    <div style="display:flex;gap:12px;margin-bottom:20px">
      <NCard size="small" style="flex:1;text-align:center">
        <div style="font-size:24px;font-weight:700">{{ stats.total }}</div>
        <div style="font-size:12px;color:#999">总计</div>
      </NCard>
      <NCard size="small" style="flex:1;text-align:center">
        <div style="font-size:24px;font-weight:700;color:#18a058">{{ stats.mastered }}</div>
        <div style="font-size:12px;color:#999">已掌握</div>
      </NCard>
      <NCard size="small" style="flex:1;text-align:center">
        <div style="font-size:24px;font-weight:700;color:#f0a020">{{ stats.learning }}</div>
        <div style="font-size:12px;color:#999">学习中</div>
      </NCard>
    </div>

    <!-- Filter -->
    <NSpace style="margin-bottom:16px">
      <NButton size="small" :type="filter === 'all' ? 'primary' : 'default'" @click="filter = 'all'; load()">全部</NButton>
      <NButton size="small" :type="filter === 'learning' ? 'primary' : 'default'" @click="filter = 'learning'; load()">学习中</NButton>
      <NButton size="small" :type="filter === 'mastered' ? 'primary' : 'default'" @click="filter = 'mastered'; load()">已掌握</NButton>
    </NSpace>

    <NSpin :show="loading">
      <NEmpty v-if="!loading && !words.length" description="生词本还是空的，快去练习对话吧！">
        <template #extra>
          <NButton type="primary" @click="router.push({name:'home'})">去练习</NButton>
        </template>
      </NEmpty>

      <div v-else style="display:flex;flex-direction:column;gap:8px">
        <NCard v-for="w in words" :key="w.id" size="small" :style="{opacity: w.mastered ? 0.6 : 1}">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <div style="flex:1;min-width:150px">
              <div style="display:flex;align-items:center;gap:8px">
                <span style="font-size:16px;font-weight:600">{{ w.word }}</span>
                <NTag v-if="w.mastered" type="success" size="tiny">已掌握</NTag>
              </div>
              <div v-if="w.meaning" style="color:#666;font-size:13px;margin-top:4px">{{ w.meaning }}</div>
              <div v-if="w.context" style="color:#999;font-size:12px;margin-top:2px">📝 {{ w.context }}</div>
            </div>
            <NSpace :size="6">
              <NTooltip>
                <template #trigger>
                  <NButton size="tiny" circle @click="handleToggle(w)" :type="w.mastered ? 'warning' : 'success'">
                    <template #icon>
                      <CheckOutlined v-if="!w.mastered" />
                      <CloseOutlined v-else />
                    </template>
                  </NButton>
                </template>
                {{ w.mastered ? '标记为学习中' : '标记为已掌握' }}
              </NTooltip>
              <NPopconfirm @positive-click="() => handleDelete(w)">
                <template #trigger>
                  <NButton size="tiny" type="error" ghost>删除</NButton>
                </template>
                确定删除这个单词吗？
              </NPopconfirm>
            </NSpace>
          </div>
        </NCard>
      </div>
    </NSpin>

    <!-- Add modal -->
    <NModal v-model:show="showAdd" title="添加单词">
      <NCard style="width:400px;max-width:90vw" title="添加新单词" closable @close="showAdd = false">
        <NSpace vertical style="width:100%">
          <NInput v-model:value="newWord.word" placeholder="单词 *" />
          <NInput v-model:value="newWord.meaning" placeholder="中文释义" />
          <NInput v-model:value="newWord.context" type="textarea" placeholder="例句或上下文（可选）" :autosize="{minRows:2,maxRows:4}" />
          <NButton type="primary" block @click="handleAdd">确认添加</NButton>
        </NSpace>
      </NCard>
    </NModal>
  </div>
</template>

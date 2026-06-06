<script setup lang="ts">
import { NMessageProvider, NButton, NSpace } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <NMessageProvider>
    <div style="display:flex;flex-direction:column;height:100vh">
      <div style="flex-shrink:0;height:56px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #eee;background:#fff">
        <div style="font-size:18px;font-weight:700;color:#2080f0">
          🎯 AI 英语口语练习
        </div>
        <NSpace>
          <NButton text @click="router.push({name:'home'})">场景选择</NButton>
          <NButton text @click="router.push({name:'history'})">练习记录</NButton>
        </NSpace>
      </div>
      <div style="flex:1;overflow-y:auto">
        <router-view />
      </div>
    </div>
  </NMessageProvider>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NMessageProvider, NConfigProvider, NButton, NSpace, darkTheme, NIcon } from 'naive-ui'
import { useRouter } from 'vue-router'
import { BulbOutlined } from '@vicons/antd'

const router = useRouter()
const isDark = ref(false)

// Persist theme preference
try {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark') isDark.value = true
} catch {}

function toggleTheme() {
  isDark.value = !isDark.value
  try { localStorage.setItem('theme', isDark.value ? 'dark' : 'light') } catch {}
}

const theme = computed(() => isDark.value ? darkTheme : null)

// Theme-aware header styles
const headerBg = computed(() => isDark.value ? 'rgb(36,36,36)' : '#fff')
const headerBorder = computed(() => isDark.value ? '1px solid rgb(51,51,51)' : '1px solid #eee')
</script>

<template>
  <NConfigProvider :theme="theme">
    <NMessageProvider>
      <div style="display:flex;flex-direction:column;height:100vh">
        <div :style="{
          flexShrink:0, height:'56px', padding:'0 24px',
          display:'flex', alignItems:'center', justifyContent:'space-between',
          borderBottom: headerBorder, background: headerBg
        }">
          <div style="font-size:18px;font-weight:700;color:#2080f0">
            🎯 AI 英语口语练习
          </div>
          <NSpace>
            <NButton text @click="router.push({name:'home'})">场景选择</NButton>
            <NButton text @click="router.push({name:'history'})">练习记录</NButton>
            <NButton text @click="router.push({name:'dashboard'})">学习报告</NButton>
            <NButton text @click="toggleTheme">
              <template #icon>
                <NIcon><BulbOutlined /></NIcon>
              </template>
            </NButton>
          </NSpace>
        </div>
        <div style="flex:1;overflow-y:auto">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" v-if="Component" />
            </transition>
          </router-view>
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

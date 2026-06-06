<script setup lang="ts">
import { ref } from 'vue'
import { NMessageProvider, NConfigProvider, NButton, NSpace, NIcon } from 'naive-ui'
import { useRouter } from 'vue-router'
import { BulbOutlined, HomeOutlined, HistoryOutlined, BarChartOutlined } from '@vicons/antd'
import { useTheme } from './composables/useTheme'

const router = useRouter()
const { isDark, themeClass, naiveTheme, naiveThemeOverrides, toggleTheme } = useTheme()

// Track navigation direction for slide transitions
const transitionName = ref('slide-left')

router.beforeEach((to, from) => {
  // Determine transition direction based on route order
  const routeOrder = ['home', 'history', 'dashboard']
  const toIdx = routeOrder.indexOf(String(to.name))
  const fromIdx = routeOrder.indexOf(String(from.name))
  if (toIdx === -1 || fromIdx === -1) {
    transitionName.value = toIdx === -1 ? 'slide-left' : 'slide-right'
  } else {
    transitionName.value = toIdx > fromIdx ? 'slide-left' : 'slide-right'
  }
})
</script>

<template>
  <NConfigProvider :theme="naiveTheme" :theme-overrides="naiveThemeOverrides">
    <NMessageProvider>
      <div
        :data-theme="themeClass"
        style="display:flex;flex-direction:column;height:100vh;background:var(--color-bg-page)"
      >
        <!-- Header -->
        <div
          :style="{
            flexShrink:0, height:'56px', padding:'0 24px',
            display:'flex', alignItems:'center', justifyContent:'space-between',
            borderBottom: '1px solid ' + 'var(--color-border)',
            background: 'var(--color-bg)',
            zIndex: 100,
          }"
        >
          <div
            :style="{
              fontSize:'18px', fontWeight:700,
              color: 'var(--color-primary)',
              display:'flex', alignItems:'center', gap:'8px',
            }"
          >
            <span style="font-size:22px">🎯</span>
            <span>AI 英语口语练习</span>
          </div>
          <NSpace :size="4">
            <NButton text @click="router.push({name:'home'})">
              <template #icon><NIcon><HomeOutlined /></NIcon></template>
              场景选择
            </NButton>
            <NButton text @click="router.push({name:'history'})">
              <template #icon><NIcon><HistoryOutlined /></NIcon></template>
              练习记录
            </NButton>
            <NButton text @click="router.push({name:'dashboard'})">
              <template #icon><NIcon><BarChartOutlined /></NIcon></template>
              学习报告
            </NButton>
            <NButton text @click="toggleTheme" style="margin-left:8px">
              <template #icon>
                <NIcon><BulbOutlined /></NIcon>
              </template>
            </NButton>
          </NSpace>
        </div>

        <!-- Content -->
        <div style="flex:1;overflow-y:auto;overflow-x:hidden">
          <router-view v-slot="{ Component }">
            <transition :name="transitionName" mode="out-in">
              <component :is="Component" v-if="Component" />
            </transition>
          </router-view>
        </div>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
/* Page slide transitions */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}
.slide-left-enter-from {
  transform: translateX(60px);
  opacity: 0;
}
.slide-left-leave-to {
  transform: translateX(-30px);
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}
.slide-right-enter-from {
  transform: translateX(-60px);
  opacity: 0;
}
.slide-right-leave-to {
  transform: translateX(30px);
  opacity: 0;
}
</style>

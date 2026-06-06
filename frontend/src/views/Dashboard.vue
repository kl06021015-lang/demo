<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NButton, NTag, NSpin, NEmpty, NGrid, NGridItem, NProgress, NSpace,
  NModal, NInputNumber, NSelect, useMessage, NPopover
} from 'naive-ui'
import {
  getDashboard, getScenes, setGoal, createCheckin, getGoals,
  type DashboardData, type Scene, type Goal,
} from '../api'

const router = useRouter()
const msg = useMessage()

const loading = ref(true)
const data = ref<DashboardData | null>(null)
const sceneMap = ref<Record<string, string>>({})

// Goal editing modal
const showGoalModal = ref(false)
const editingGoalType = ref<'daily' | 'weekly'>('daily')
const editingTargetMinutes = ref(10)
const savingGoal = ref(false)

onMounted(async () => {
  try {
    const [dash, scenes] = await Promise.all([getDashboard(), getScenes()])
    data.value = dash
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

// Goal progress
const dailyGoal = computed(() => data.value?.goal)
const weeklyGoal = computed(() => data.value?.weekly_goal)
const weeklyMinutes = computed(() => data.value?.weekly_minutes ?? 0)

const dailyProgress = computed(() => {
  if (!dailyGoal.value) return 0
  // Today's minutes from check-ins where checkin_date = today
  const today = new Date().toISOString().slice(0, 10)
  const todayCheckin = data.value?.weekly_checkins?.find(c => c.checkin_date === today)
  const todayMinutes = todayCheckin?.minutes_practiced ?? 0
  return Math.min(100, Math.round((todayMinutes / dailyGoal.value.target_minutes) * 100))
})

const weeklyProgress = computed(() => {
  if (!weeklyGoal.value || weeklyGoal.value.target_minutes === 0) return 0
  return Math.min(100, Math.round((weeklyMinutes.value / weeklyGoal.value.target_minutes) * 100))
})

// Weekly heatmap dates
const weekDays = computed(() => {
  const days: { date: string; label: string; minutes: number; checked: boolean }[] = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const ds = d.toISOString().slice(0, 10)
    const checkin = data.value?.weekly_checkins?.find(c => c.checkin_date === ds)
    days.push({
      date: ds,
      label: d.toLocaleDateString('zh-CN', { weekday: 'short' }),
      minutes: checkin?.minutes_practiced ?? 0,
      checked: !!checkin,
    })
  }
  return days
})

// Streak
const streak = computed(() => data.value?.streak ?? { current_streak: 0, longest_streak: 0, total_checkins: 0 })

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function openGoalModal(type: 'daily' | 'weekly') {
  editingGoalType.value = type
  const goal = type === 'daily' ? data.value?.goal : data.value?.weekly_goal
  editingTargetMinutes.value = goal?.target_minutes ?? (type === 'daily' ? 10 : 60)
  showGoalModal.value = true
}

async function saveGoal() {
  savingGoal.value = true
  try {
    await setGoal(editingGoalType.value, editingTargetMinutes.value)
    showGoalModal.value = false
    msg.success('目标已更新')
    // Refresh
    data.value = await getDashboard()
  } catch (e: any) {
    msg.error(e.message || '保存失败')
  } finally {
    savingGoal.value = false
  }
}

async function handleCheckin() {
  try {
    await createCheckin()
    msg.success('打卡成功！🎉')
    data.value = await getDashboard()
  } catch (e: any) {
    msg.error(e.message || '打卡失败')
  }
}

function formatDateShort(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
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

      <template v-if="data">
        <!-- ================================================================ -->
        <!-- Goal + Streak Row -->
        <!-- ================================================================ -->
        <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" style="margin-bottom:16px">
          <!-- Daily Goal Card -->
          <NGridItem :span="1">
            <NCard size="small" style="text-align:center">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:600">📅 今日目标</span>
                <NButton size="tiny" text type="primary" @click="openGoalModal('daily')">
                  {{ dailyGoal ? '修改' : '设定' }}
                </NButton>
              </div>
              <template v-if="dailyGoal">
                <NProgress
                  type="circle"
                  :percentage="dailyProgress"
                  :color="dailyProgress >= 100 ? '#18a058' : '#2080f0'"
                  :stroke-width="8"
                  :width="80"
                />
                <div style="margin-top:8px;font-size:13px;color:#666">
                  目标 {{ dailyGoal.target_minutes }} 分钟/天
                </div>
              </template>
              <div v-else style="padding:16px 0;color:#999;font-size:13px">
                尚未设置每日目标
              </div>
            </NCard>
          </NGridItem>

          <!-- Weekly Goal + Streak Card -->
          <NGridItem :span="1">
            <NCard size="small">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:600">📈 本周进度</span>
                <NButton size="tiny" text type="primary" @click="openGoalModal('weekly')">
                  {{ weeklyGoal ? '修改' : '设定' }}
                </NButton>
              </div>
              <template v-if="weeklyGoal">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                  <NProgress
                    :percentage="weeklyProgress"
                    :color="weeklyProgress >= 100 ? '#18a058' : '#f0a020'"
                    :height="12"
                    :border-radius="6"
                    style="flex:1"
                  />
                  <span style="font-size:12px;color:#999;white-space:nowrap">{{ weeklyMinutes }}/{{ weeklyGoal.target_minutes }} 分钟</span>
                </div>
              </template>
              <div v-else style="margin-bottom:8px;font-size:13px;color:#999">
                尚未设置每周目标
              </div>
              <!-- Streak -->
              <div style="display:flex;gap:16px;margin-top:8px;font-size:13px">
                <div>
                  <span style="color:#999">当前连续：</span>
                  <strong :style="{color: streak.current_streak >= 3 ? '#18a058' : '#f0a020'}">
                    🔥 {{ streak.current_streak }} 天
                  </strong>
                </div>
                <div>
                  <span style="color:#999">最长：</span>
                  <strong>⭐ {{ streak.longest_streak }} 天</strong>
                </div>
                <div>
                  <span style="color:#999">总打卡：</span>
                  <strong>{{ streak.total_checkins }} 次</strong>
                </div>
              </div>
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- Weekly Checkin Calendar -->
        <NCard size="small" title="📅 本周打卡" style="margin-bottom:16px">
          <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
            <div
              v-for="day in weekDays"
              :key="day.date"
              style="width:80px;text-align:center"
            >
              <div style="font-size:11px;color:#999;margin-bottom:4px">{{ day.label }}</div>
              <div
                :style="{
                  width:'48px', height:'48px', borderRadius:'50%', margin:'0 auto',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  fontSize:'20px',
                  background: day.checked ? (day.minutes >= (dailyGoal?.target_minutes ?? 10) ? '#e8f5e9' : '#fff3e0') : '#f5f5f5',
                  border: day.checked ? '2px solid ' + (day.minutes >= (dailyGoal?.target_minutes ?? 10) ? '#18a058' : '#f0a020') : '2px solid #eee',
                }"
              >
                {{ day.checked ? (day.minutes >= (dailyGoal?.target_minutes ?? 10) ? '✅' : '🟡') : '·' }}
              </div>
              <div v-if="day.checked" style="font-size:10px;color:#666;margin-top:2px">
                {{ day.minutes }} 分钟
              </div>
            </div>
          </div>
          <div style="text-align:center;margin-top:12px">
            <NButton size="small" @click="handleCheckin">✍️ 手动打卡</NButton>
          </div>
        </NCard>

        <!-- Badges -->
        <NCard v-if="data.badges?.length" size="small" title="🏅 成就徽章" style="margin-bottom:16px">
          <NSpace :size="8" wrap>
            <NPopover v-for="b in data.badges" :key="b.id" trigger="hover">
              <template #trigger>
                <NTag size="medium" round :bordered="false" style="cursor:pointer;padding:4px 12px;font-size:14px">
                  {{ b.icon }} {{ b.name }}
                </NTag>
              </template>
              <span>{{ b.description }}</span>
            </NPopover>
          </NSpace>
        </NCard>

        <!-- Stats Row -->
        <NGrid v-if="hasData" :cols="4" :x-gap="16" :y-gap="16" responsive="screen" style="margin-bottom:16px">
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
        <NCard v-if="data.scenes_practiced.length" title="🎬 各场景练习统计" style="margin-bottom:16px">
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
            {{ streak.current_streak >= 7
                ? `🔥 连续打卡 ${streak.current_streak} 天！你太棒了！累计 ${data.total_minutes} 分钟练习。继续加油！`
                : data.completed_sessions > 0
                  ? `你已完成 ${data.completed_sessions} 次练习，累计 ${data.total_minutes} 分钟。连续打卡 ${streak.current_streak} 天。继续加油！💪`
                  : '开始你的第一次练习吧！🎯'
            }}
          </div>
        </NCard>
      </template>
    </NSpin>

    <!-- ================================================================ -->
    <!-- Goal Edit Modal -->
    <!-- ================================================================ -->
    <NModal v-model:show="showGoalModal" title="设定学习目标">
      <NCard style="width:400px" title="设定学习目标" :bordered="false" size="small">
        <div style="margin-bottom:16px">
          <div style="font-size:13px;color:#666;margin-bottom:4px">目标类型</div>
          <NSelect
            v-model:value="editingGoalType"
            :options="[
              { label: '每日目标', value: 'daily' },
              { label: '每周目标', value: 'weekly' },
            ]"
          />
        </div>
        <div style="margin-bottom:16px">
          <div style="font-size:13px;color:#666;margin-bottom:4px">
            目标时长（分钟）
          </div>
          <NInputNumber
            v-model:value="editingTargetMinutes"
            :min="1"
            :max="600"
            :step="5"
            style="width:100%"
          />
        </div>
        <div style="font-size:13px;color:#999;margin-bottom:16px">
          {{ editingGoalType === 'daily'
              ? `每天练习 ${editingTargetMinutes} 分钟`
              : `每周练习 ${editingTargetMinutes} 分钟`
          }}
        </div>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <NButton @click="showGoalModal = false">取消</NButton>
          <NButton type="primary" :loading="savingGoal" @click="saveGoal">保存目标</NButton>
        </div>
      </NCard>
    </NModal>
  </div>
</template>

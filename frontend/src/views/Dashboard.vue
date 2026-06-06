<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NButton, NTag, NSpin, NEmpty, NGrid, NGridItem, NProgress, NSpace,
  NModal, NInputNumber, NSelect, useMessage, NPopover
} from 'naive-ui'
import {
  getDashboard, getScenes, setGoal, createCheckin, getGoals, getCheckins,
  type DashboardData, type Scene, type Goal, type CheckinRecord,
} from '../api'
import HeatmapChart from '../components/dashboard/HeatmapChart.vue'
import ScoreTrendChart from '../components/dashboard/ScoreTrendChart.vue'
import FlameAnimation from '../components/animations/FlameAnimation.vue'

const router = useRouter()
const msg = useMessage()

const loading = ref(true)
const data = ref<DashboardData | null>(null)
const sceneMap = ref<Record<string, string>>({})
const yearCheckins = ref<CheckinRecord[]>([])

// Goal editing modal
const showGoalModal = ref(false)
const editingGoalType = ref<'daily' | 'weekly'>('daily')
const editingTargetMinutes = ref(10)
const savingGoal = ref(false)

onMounted(async () => {
  try {
    const [dash, scenes, cks] = await Promise.all([getDashboard(), getScenes(), getCheckins(365)])
    data.value = dash
    yearCheckins.value = cks.checkins
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
  if (s >= 8) return 'var(--color-success)'
  if (s >= 6) return 'var(--color-warning)'
  return 'var(--color-error)'
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

// XP & Level
const xp = computed(() => data.value?.xp ?? 0)
const level = computed(() => data.value?.level ?? 1)
const xpForNext = computed(() => data.value?.xp_for_next ?? 100)
const xpProgress = computed(() => {
  if (!data.value) return 0
  const prevLevel = Math.max(1, data.value.level - 1)
  const prevXp = prevLevel ** 2 * 100
  const currentXp = data.value.xp
  const needed = data.value.xp_for_next - prevXp
  return Math.min(100, Math.round(((currentXp - prevXp) / needed) * 100))
})

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
  <div style="max-width:var(--max-width-content);margin:0 auto;padding:var(--spacing-xl) var(--spacing-md)">
    <h2 style="margin-bottom:var(--spacing-lg);font-size:var(--font-size-heading)">📊 学习报告</h2>

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
                  :color="dailyProgress >= 100 ? 'var(--color-success)' : 'var(--color-primary)'"
                  :stroke-width="8"
                  :width="80"
                />
                <div style="margin-top:8px;font-size:var(--font-size-small);color:var(--color-text-secondary)">
                  目标 {{ dailyGoal.target_minutes }} 分钟/天
                </div>
              </template>
              <div v-else style="padding:16px 0;color:var(--color-text-tertiary);font-size:var(--font-size-small)">
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
                    :color="weeklyProgress >= 100 ? 'var(--color-success)' : 'var(--color-warning)'"
                    :height="12"
                    :border-radius="6"
                    style="flex:1"
                  />
                  <span style="font-size:var(--font-size-caption);color:var(--color-text-tertiary);white-space:nowrap">{{ weeklyMinutes }}/{{ weeklyGoal.target_minutes }} 分钟</span>
                </div>
              </template>
              <div v-else style="margin-bottom:8px;font-size:var(--font-size-small);color:var(--color-text-tertiary)">
                尚未设置每周目标
              </div>
              <!-- Streak -->
              <div style="display:flex;gap:16px;margin-top:8px;font-size:var(--font-size-small)">
                <div>
                  <span style="color:var(--color-text-tertiary)">当前连续：</span>
                  <FlameAnimation :streak="streak.current_streak" :animate="true" />
                  <strong :style="{color: streak.current_streak >= 3 ? 'var(--color-success)' : 'var(--color-warning)'}">
                    {{ streak.current_streak }} 天
                  </strong>
                </div>
                <div>
                  <span style="color:var(--color-text-tertiary)">最长：</span>
                  <strong>⭐ {{ streak.longest_streak }} 天</strong>
                </div>
                <div>
                  <span style="color:var(--color-text-tertiary)">总打卡：</span>
                  <strong>{{ streak.total_checkins }} 次</strong>
                </div>
              </div>
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- XP / Level Card -->
        <NCard size="small" style="text-align:center;margin-bottom:16px">
          <div style="display:flex;align-items:center;justify-content:center;gap:24px;flex-wrap:wrap">
            <div>
              <div style="font-size:var(--font-size-caption);color:var(--color-text-tertiary);margin-bottom:4px">
                当前等级
              </div>
              <div style="font-size:36px;font-weight:700;color:var(--color-accent)">
                {{ level }}
              </div>
            </div>
            <div style="flex:1;min-width:200px;max-width:400px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-size:var(--font-size-caption);color:var(--color-text-secondary)">
                  ⚡ {{ xp }} XP
                </span>
                <span style="font-size:var(--font-size-caption);color:var(--color-text-tertiary)">
                  升级还需 {{ xpForNext - xp }} XP
                </span>
              </div>
              <NProgress
                :percentage="xpProgress"
                :height="10"
                :border-radius="5"
                color="var(--color-accent)"
                :show-indicator="false"
              />
            </div>
          </div>
        </NCard>

        <!-- Learning Heatmap -->
        <NCard v-if="yearCheckins.length" size="small" title="📊 学习热力图" style="margin-bottom:16px">
          <HeatmapChart :checkins="yearCheckins" />
        </NCard>

        <!-- Score Trend Chart -->
        <NCard v-if="data.daily_scores?.length" size="small" title="📈 评分趋势（30天）" style="margin-bottom:16px">
          <ScoreTrendChart :scores="data.daily_scores" />
        </NCard>

        <!-- Weekly Checkin Calendar -->
        <NCard size="small" title="📅 本周打卡" style="margin-bottom:16px">
          <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
            <div
              v-for="day in weekDays"
              :key="day.date"
              style="width:80px;text-align:center"
            >
              <div style="font-size:var(--font-size-caption);color:var(--color-text-tertiary);margin-bottom:4px">{{ day.label }}</div>
              <div
                :style="{
                  width:'48px', height:'48px', borderRadius:'50%', margin:'0 auto',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  fontSize:'20px',
                  background: day.checked ? (day.minutes >= (dailyGoal?.target_minutes ?? 10) ? 'var(--color-success-light)' : 'var(--color-warning-light)') : 'var(--color-bg-input)',
                  border: day.checked ? '2px solid ' + (day.minutes >= (dailyGoal?.target_minutes ?? 10) ? 'var(--color-success)' : 'var(--color-warning)') : '2px solid var(--color-border)',
                }"
              >
                {{ day.checked ? (day.minutes >= (dailyGoal?.target_minutes ?? 10) ? '✅' : '🟡') : '·' }}
              </div>
              <div v-if="day.checked" style="font-size:var(--font-size-caption);color:var(--color-text-secondary);margin-top:2px">
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
                <NTag size="medium" round :bordered="false" style="cursor:pointer;padding:4px 12px;font-size:var(--font-size-small)">
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
              <div style="font-size:28px;font-weight:700;color:var(--color-primary)">{{ data.total_sessions }}</div>
              <div style="font-size:var(--font-size-small);color:var(--color-text-tertiary)">总练习次数</div>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700;color:var(--color-success)">{{ data.total_minutes }}</div>
              <div style="font-size:var(--font-size-small);color:var(--color-text-tertiary)">练习时长 (分钟)</div>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700" :style="{color: scoreColor(data.average_score)}">{{ data.average_score }}</div>
              <div style="font-size:var(--font-size-small);color:var(--color-text-tertiary)">平均评分</div>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small" style="text-align:center">
              <div style="font-size:28px;font-weight:700;color:var(--color-accent)">{{ completionRate }}%</div>
              <div style="font-size:var(--font-size-small);color:var(--color-text-tertiary)">完成率</div>
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
        <NCard style="text-align:center;background:var(--color-bg-encourage)">
          <div style="font-size:var(--font-size-body);line-height:var(--line-height);color:var(--color-primary)">
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
          <div style="font-size:var(--font-size-small);color:var(--color-text-secondary);margin-bottom:4px">目标类型</div>
          <NSelect
            v-model:value="editingGoalType"
            :options="[
              { label: '每日目标', value: 'daily' },
              { label: '每周目标', value: 'weekly' },
            ]"
          />
        </div>
        <div style="margin-bottom:16px">
          <div style="font-size:var(--font-size-small);color:var(--color-text-secondary);margin-bottom:4px">
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
        <div style="font-size:var(--font-size-small);color:var(--color-text-tertiary);margin-bottom:16px">
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

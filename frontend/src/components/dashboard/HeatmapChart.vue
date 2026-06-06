<!--
  HeatmapChart.vue — GitHub-style contribution heatmap
  Shows practice activity over the past year (7 rows x 52 cols)
-->
<script setup lang="ts">
import { computed } from 'vue'
import { NTooltip } from 'naive-ui'
import type { CheckinRecord } from '../../api'

const props = defineProps<{ checkins: CheckinRecord[] }>()

// Build a map of date -> minutes
const minuteMap = computed(() => {
  const m: Record<string, number> = {}
  for (const c of props.checkins) {
    m[c.checkin_date] = c.minutes_practiced
  }
  return m
})

// Generate 52 weeks x 7 days grid
interface Cell {
  date: string
  minutes: number
  level: number  // 0-4
  label: string
}

const grid = computed(() => {
  const cells: Cell[][] = []
  const today = new Date()
  // Find the Sunday of the current week
  const endDate = new Date(today)
  // Go back 52 weeks
  const startDate = new Date(endDate)
  startDate.setDate(startDate.getDate() - 52 * 7 + 1)
  // Align to Monday
  const dayOfWeek = startDate.getDay()
  const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  startDate.setDate(startDate.getDate() + diff)

  const dateStr = (d: Date) => d.toISOString().slice(0, 10)

  // 7 rows (Mon-Sun), each with 52 cells
  for (let row = 0; row < 7; row++) {
    const weekCells: Cell[] = []
    for (let col = 0; col < 52; col++) {
      const d = new Date(startDate)
      d.setDate(d.getDate() + col * 7 + row)
      const ds = dateStr(d)
      const minutes = minuteMap.value[ds] || 0
      let level = 0
      if (minutes > 0) level = 1
      if (minutes >= 10) level = 2
      if (minutes >= 20) level = 3
      if (minutes >= 30) level = 4
      weekCells.push({
        date: ds,
        minutes,
        level,
        label: `${ds}: ${minutes} 分钟`,
      })
    }
    cells.push(weekCells)
  }
  return cells
})

// Color levels (from light to dark green)
const levelColors = [
  'var(--color-bg-card)',
  'var(--color-primary-bg)',
  '#8ED45A',
  '#58CC02',
  '#3D8B00',
]

// Day labels
const dayLabels = ['一', '二', '三', '四', '五', '六', '日']

// Month labels (derived from grid)
const monthLabels = computed(() => {
  const labels: { col: number; label: string }[] = []
  const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
  for (let col = 0; col < 52; col++) {
    const d = new Date(grid.value[0][col].date)
    if (d.getDate() <= 7) {
      labels.push({ col, label: months[d.getMonth()] })
    }
  }
  return labels
})
</script>

<template>
  <div :style="{ overflowX: 'auto', paddingBottom: '8px' }">
    <!-- Month labels -->
    <div :style="{ display: 'flex', marginLeft: '28px', marginBottom: '4px' }">
      <span
        v-for="(ml, i) in monthLabels"
        :key="i"
        :style="{
          fontSize: 'var(--font-size-caption)',
          color: 'var(--color-text-tertiary)',
          position: 'absolute',
          marginLeft: `${ml.col * 14}px`,
        }"
      >
        {{ ml.label }}
      </span>
    </div>
    <div style="position:relative;margin-top:14px">
      <div :style="{ display: 'flex' }">
        <!-- Day labels -->
        <div :style="{ display: 'flex', flexDirection: 'column', marginRight: '4px', gap: '2px' }">
          <span
            v-for="(dl, i) in dayLabels"
            :key="i"
            :style="{
              fontSize: '9px',
              color: 'var(--color-text-tertiary)',
              height: '12px',
              lineHeight: '12px',
              visibility: i % 2 === 0 ? 'visible' : 'hidden',
            }"
          >
            {{ dl }}
          </span>
        </div>
        <!-- Cell grid -->
        <div :style="{ display: 'flex', gap: '2px' }">
          <div
            v-for="(col, colIdx) in grid[0]"
            :key="colIdx"
            :style="{ display: 'flex', flexDirection: 'column', gap: '2px' }"
          >
            <NTooltip v-for="(row, rowIdx) in grid" :key="rowIdx">
              <template #trigger>
                <div
                  :style="{
                    width: '12px',
                    height: '12px',
                    borderRadius: '2px',
                    background: levelColors[row[colIdx].level],
                    cursor: 'pointer',
                  }"
                />
              </template>
              {{ row[colIdx].label }}
            </NTooltip>
          </div>
        </div>
      </div>
      <!-- Legend -->
      <div :style="{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '8px', fontSize: 'var(--font-size-caption)', color: 'var(--color-text-tertiary)' }">
        <span>Less</span>
        <div v-for="lvl in 5" :key="lvl" :style="{ width: '12px', height: '12px', borderRadius: '2px', background: levelColors[lvl - 1] }" />
        <span>More</span>
      </div>
    </div>
  </div>
</template>

<!--
  ScoreTrendChart.vue — 30-day score trend line chart (pure SVG)
  Shows daily average score over the past month
-->
<script setup lang="ts">
import { computed } from 'vue'

interface DailyScore {
  date: string
  avg_score: number
  sessions: number
}

const props = defineProps<{ scores: DailyScore[] }>()

const WIDTH = 600
const HEIGHT = 200
const PADDING = { top: 20, right: 20, bottom: 30, left: 40 }

const chartData = computed(() => {
  if (!props.scores.length) return null

  const scores = props.scores.slice(-30) // Last 30 days
  const maxScore = Math.max(10, ...scores.map(s => s.avg_score))
  const minScore = Math.min(0, ...scores.map(s => s.avg_score))
  const range = maxScore - minScore || 1

  const plotW = WIDTH - PADDING.left - PADDING.right
  const plotH = HEIGHT - PADDING.top - PADDING.bottom

  const points = scores.map((s, i) => {
    const x = PADDING.left + (i / (scores.length - 1 || 1)) * plotW
    const y = PADDING.top + plotH - ((s.avg_score - minScore) / range) * plotH
    return { x, y, ...s }
  })

  const pathD = points.length > 0
    ? 'M' + points.map(p => `${p.x},${p.y}`).join(' L')
    : ''

  // Area fill path
  const areaD = points.length > 0
    ? pathD + ` L${points[points.length - 1].x},${PADDING.top + plotH} L${points[0].x},${PADDING.top + plotH} Z`
    : ''

  // Y-axis labels
  const yLabels: number[] = []
  for (let i = 0; i <= 4; i++) {
    yLabels.push(Math.round((minScore + (range * i) / 4) * 10) / 10)
  }

  return { points, pathD, areaD, yLabels, maxScore, minScore }
})
</script>

<template>
  <div v-if="chartData" style="overflow-x:auto">
    <svg :viewBox="`0 0 ${WIDTH} ${HEIGHT}`" style="width:100%;max-width:600px">
      <!-- Grid lines -->
      <line
        v-for="(_, i) in [...Array(5)]"
        :key="i"
        :x1="PADDING.left"
        :y1="PADDING.top + ((HEIGHT - PADDING.top - PADDING.bottom) * i) / 4"
        :x2="WIDTH - PADDING.right"
        :y2="PADDING.top + ((HEIGHT - PADDING.top - PADDING.bottom) * i) / 4"
        stroke="var(--color-border-light)"
        stroke-width="1"
      />
      <!-- Area fill -->
      <path
        v-if="chartData.areaD"
        :d="chartData.areaD"
        fill="var(--color-primary-light)"
        opacity="0.4"
      />
      <!-- Line -->
      <path
        v-if="chartData.pathD"
        :d="chartData.pathD"
        fill="none"
        stroke="var(--color-primary)"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- Data points -->
      <circle
        v-for="(p, i) in chartData.points"
        :key="i"
        :cx="p.x"
        :cy="p.y"
        r="3"
        fill="var(--color-primary)"
        stroke="var(--color-bg)"
        stroke-width="2"
      />
      <!-- Y-axis labels -->
      <text
        v-for="(label, i) in chartData.yLabels"
        :key="i"
        :x="PADDING.left - 8"
        :y="PADDING.top + ((HEIGHT - PADDING.top - PADDING.bottom) * i) / 4 + 4"
        text-anchor="end"
        :style="{ fontSize: '10px', fill: 'var(--color-text-tertiary)' }"
      >
        {{ label }}
      </text>
    </svg>
    <div v-if="!props.scores.length" :style="{ textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: 'var(--font-size-small)', padding: '20px' }">
      暂无趋势数据，完成更多对话后查看
    </div>
  </div>
  <div v-else :style="{ textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: 'var(--font-size-small)', padding: '20px' }">
    暂无趋势数据
  </div>
</template>

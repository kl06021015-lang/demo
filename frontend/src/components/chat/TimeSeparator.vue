<!--
  TimeSeparator.vue — Time divider between message groups
  Inspired by iMessage time stamps
-->
<script setup lang="ts">
defineProps<{ time: string }>()

function formatLabel(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')

  const isToday = d.toDateString() === now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = d.toDateString() === yesterday.toDateString()

  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`

  if (isToday) return `今天 ${time}`
  if (isYesterday) return `昨天 ${time}`

  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
  return `${months[d.getMonth()]}${d.getDate()}日 ${time}`
}
</script>

<template>
  <div
    :style="{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      margin: '16px 0',
      gap: '12px',
    }"
  >
    <div :style="{ flex: 1, height: '1px', background: 'var(--color-border)' }" />
    <span
      :style="{
        fontSize: 'var(--font-size-caption)',
        color: 'var(--color-text-disabled)',
        whiteSpace: 'nowrap',
      }"
    >
      {{ formatLabel(time) }}
    </span>
    <div :style="{ flex: 1, height: '1px', background: 'var(--color-border)' }" />
  </div>
</template>

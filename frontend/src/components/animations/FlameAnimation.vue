<!--
  FlameAnimation.vue — Animated flame icon for streak display
  Bouncing flame with "ding" sound support
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  streak: number
  animate?: boolean
}>()

const bouncing = ref(false)

watch(() => props.streak, (newVal, oldVal) => {
  if (props.animate && newVal > (oldVal || 0)) {
    bouncing.value = true
    playDing()
    setTimeout(() => { bouncing.value = false }, 600)
  }
})

function playDing() {
  try {
    const ctx = new AudioContext()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.type = 'sine'
    osc.frequency.setValueAtTime(880, ctx.currentTime)
    osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.1)
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
    osc.start()
    osc.stop(ctx.currentTime + 0.3)
  } catch {
    // Audio not critical
  }
}
</script>

<template>
  <span
    :style="{
      display: 'inline-block',
      fontSize: '22px',
      animation: bouncing ? 'flame-bounce 0.6s ease' : 'none',
    }"
  >
    {{ streak >= 7 ? '⭐' : streak >= 3 ? '🔥' : '🕯️' }}
  </span>
</template>

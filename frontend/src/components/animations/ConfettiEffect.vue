<!--
  ConfettiEffect.vue — Canvas confetti / celebration animation
  Inspired by Duolingo's completion celebration
-->
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = withDefaults(defineProps<{
  particleCount?: number
  duration?: number
}>(), {
  particleCount: 80,
  duration: 3000,
})

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animFrame = 0
let startTime = 0

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  rotation: number
  rotationSpeed: number
}

const COLORS = ['#58CC02', '#FF9600', '#FFD700', '#FF6B6B', '#4ECDC4', '#A78BFA']

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.parentElement?.getBoundingClientRect()
  const w = rect?.width || window.innerWidth
  const h = rect?.height || 400

  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const particles: Particle[] = []
  for (let i = 0; i < props.particleCount; i++) {
    particles.push({
      x: Math.random() * w,
      y: h * 0.3 + Math.random() * h * 0.2,
      vx: (Math.random() - 0.5) * 8,
      vy: Math.random() * -8 - 3,
      size: 4 + Math.random() * 8,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      rotation: Math.random() * 360,
      rotationSpeed: (Math.random() - 0.5) * 10,
    })
  }

  const gravity = 0.15
  startTime = performance.now()

  function animate(now: number) {
    const elapsed = now - startTime
    if (elapsed > props.duration) {
      ctx!.clearRect(0, 0, w, h)
      return
    }

    ctx!.clearRect(0, 0, w, h)
    const progress = elapsed / props.duration
    const opacity = progress > 0.8 ? 1 - (progress - 0.8) / 0.2 : 1

    for (const p of particles) {
      p.vy += gravity
      p.x += p.vx
      p.y += p.vy
      p.rotation += p.rotationSpeed
      p.vx *= 0.99

      ctx!.save()
      ctx!.globalAlpha = opacity
      ctx!.translate(p.x, p.y)
      ctx!.rotate((p.rotation * Math.PI) / 180)
      ctx!.fillStyle = p.color
      ctx!.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2)
      ctx!.restore()
    }

    animFrame = requestAnimationFrame(animate)
  }

  animFrame = requestAnimationFrame(animate)
})

onBeforeUnmount(() => {
  if (animFrame) cancelAnimationFrame(animFrame)
})
</script>

<template>
  <canvas
    ref="canvasRef"
    :style="{
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      pointerEvents: 'none',
      zIndex: 999,
    }"
  />
</template>

<!--
  TypingBubble.vue — Three bouncing dots animation replacing "AI is replying..." text
  Inspired by ChatGPT's typing indicator
-->
<script setup lang="ts">
// Pure presentation component — no props needed
</script>

<template>
  <div
    :style="{
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      padding: '8px 0',
      marginBottom: '8px',
    }"
  >
    <span
      v-for="n in 3"
      :key="n"
      :style="{
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        background: 'var(--color-text-tertiary)',
        display: 'inline-block',
        animation: `bounce-dot 1.4s infinite ease-in-out`,
        animationDelay: `${(n - 1) * 0.2}s`,
      }"
    />
  </div>
</template>

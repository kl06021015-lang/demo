<!--
  QuickReplies.vue — Quick reply suggestion buttons above the input area
  Inspired by iMessage quick reply / chatbot suggestions
-->
<script setup lang="ts">
defineProps<{ suggestions: string[] }>()
const emit = defineEmits<{ select: [text: string] }>()
</script>

<template>
  <div
    v-if="suggestions.length"
    :style="{
      display: 'flex',
      gap: '8px',
      padding: '8px 0',
      flexWrap: 'wrap',
      justifyContent: 'flex-start',
    }"
  >
    <button
      v-for="(s, i) in suggestions"
      :key="i"
      :style="{
        padding: '6px 14px',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--color-primary)',
        background: 'transparent',
        color: 'var(--color-primary)',
        fontSize: 'var(--font-size-small)',
        cursor: 'pointer',
        transition: 'all var(--transition-fast)',
        fontFamily: 'var(--font-family)',
        whiteSpace: 'nowrap',
      }"
      @click="emit('select', s)"
      @mouseenter="(e) => {
        const t = e.target as HTMLElement
        t.style.background = 'var(--color-primary)'
        t.style.color = 'var(--color-text-inverse)'
      }"
      @mouseleave="(e) => {
        const t = e.target as HTMLElement
        t.style.background = 'transparent'
        t.style.color = 'var(--color-primary)'
      }"
    >
      {{ s }}
    </button>
  </div>
</template>

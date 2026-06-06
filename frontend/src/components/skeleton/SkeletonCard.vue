<!-- SkeletonCard.vue — Card-shaped shimmer placeholder -->
<script setup lang="ts">
defineProps<{ lines?: number }>()
</script>

<template>
  <div
    class="skeleton"
    :style="{
      borderRadius: 'var(--radius-lg)',
      padding: 'var(--spacing-lg)',
      height: '200px',
    }"
  >
    <div
      v-for="n in (lines || 4)"
      :key="n"
      class="skeleton"
      :style="{
        height: '14px',
        marginBottom: '12px',
        borderRadius: '4px',
        width: n === (lines || 4) ? '60%' : '100%',
      }"
    />
  </div>
</template>

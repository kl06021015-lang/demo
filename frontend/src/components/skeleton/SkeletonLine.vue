<!-- SkeletonLine.vue — Text line shimmer placeholder -->
<script setup lang="ts">
defineProps<{ width?: string; count?: number }>()
</script>

<template>
  <div>
    <div
      v-for="n in (count || 1)"
      :key="n"
      class="skeleton"
      :style="{
        height: '12px',
        marginBottom: '8px',
        borderRadius: '4px',
        width: n === (count || 1) && width ? width : '100%',
      }"
    />
  </div>
</template>

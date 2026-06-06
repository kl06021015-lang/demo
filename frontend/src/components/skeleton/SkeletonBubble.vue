<!-- SkeletonBubble.vue — Chat bubble-shaped shimmer placeholder -->
<script setup lang="ts">
defineProps<{ count?: number }>()
</script>

<template>
  <div :style="{ padding: 'var(--spacing-md)' }">
    <div v-for="n in (count || 3)" :key="n" :style="{ marginBottom: '20px' }">
      <!-- AI bubble (left aligned) -->
      <div
        v-if="n % 2 === 1"
        class="skeleton"
        :style="{
          width: '65%',
          height: '40px',
          borderRadius: 'var(--radius-lg)',
          borderBottomLeftRadius: '4px',
          marginBottom: '8px',
        }"
      />
      <!-- User bubble (right aligned) -->
      <div
        v-else
        :style="{ display: 'flex', justifyContent: 'flex-end' }"
      >
        <div
          class="skeleton"
          :style="{
            width: '55%',
            height: '32px',
            borderRadius: 'var(--radius-lg)',
            borderBottomRightRadius: '4px',
          }"
        />
      </div>
    </div>
  </div>
</template>

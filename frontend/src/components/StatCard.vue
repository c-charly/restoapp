<template>
  <div class="stat-card" :class="[`accent-${accent}`]">
    <div class="stat-header">
      <span class="stat-label">{{ label }}</span>
      <div class="stat-icon">
        <slot name="icon" />
      </div>
    </div>
    <div class="stat-value">{{ formattedValue }}</div>
    <div v-if="sub" class="stat-sub">{{ sub }}</div>
    <div v-if="trend !== undefined" class="stat-trend" :class="trend >= 0 ? 'up' : 'down'">
      <span>{{ trend >= 0 ? '↑' : '↓' }} {{ Math.abs(trend) }}%</span>
      <span class="trend-label">vs période préc.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: number | string
  sub?: string
  trend?: number
  accent?: 'amber' | 'emerald' | 'blue' | 'violet' | 'red'
  format?: 'number' | 'currency' | 'percent' | 'raw'
}>(), {
  accent: 'amber',
  format: 'raw'
})

const formattedValue = computed(() => {
  const v = Number(props.value)
  if (props.format === 'currency') return new Intl.NumberFormat('fr-FR').format(v) + ' XAF'
  if (props.format === 'number')   return new Intl.NumberFormat('fr-FR').format(v)
  if (props.format === 'percent')  return v.toFixed(1) + '%'
  return props.value
})
</script>

<style scoped>
.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s, transform 0.2s;
}
.stat-card:hover { transform: translateY(-1px); }

.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
}
.accent-amber::before  { background: var(--color-amber); }
.accent-emerald::before{ background: var(--color-emerald); }
.accent-blue::before   { background: var(--color-blue); }
.accent-violet::before { background: var(--color-violet); }
.accent-red::before    { background: var(--color-red); }

.stat-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.stat-label  { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-text-secondary); font-family: var(--font-mono); }
.stat-icon   { color: var(--color-text-muted); }
.accent-amber  .stat-icon { color: var(--color-amber); }
.accent-emerald.stat-icon { color: var(--color-emerald); }

.stat-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 6px;
  letter-spacing: -0.5px;
}
.stat-sub { font-size: 12px; color: var(--color-text-muted); margin-bottom: 8px; }
.stat-trend { display: flex; align-items: center; gap: 8px; font-size: 12px; font-family: var(--font-mono); }
.up   { color: var(--color-emerald); }
.down { color: var(--color-red); }
.trend-label { color: var(--color-text-muted); font-size: 11px; }
</style>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">Redis Live - Temps Réel</h2>
        <p class="page-sub">Compteurs événements 24h depuis Redis · auto-actualisation {{ autoRefresh ? 'ON' : 'OFF' }}</p>
      </div>
      <div class="header-actions">
        <div class="live-indicator" :class="{ active: autoRefresh }">
          <span class="live-dot"></span>
          <span>LIVE</span>
        </div>
        <label class="toggle-label">
          <input type="checkbox" v-model="autoRefresh"/>
          <span class="toggle-track"><span class="toggle-thumb"></span></span>
          <span class="toggle-text">Auto 30s</span>
        </label>
        <button class="btn-refresh" @click="load" :disabled="store.loadingRealtime">
          <RefreshCw :size="13" :class="{'animate-spin-slow': store.loadingRealtime}"/> Actualiser
        </button>
      </div>
    </div>

    <!-- Last update -->
    <div class="last-update" v-if="lastUpdate">
      <Clock :size="11"/> Dernière actualisation : <strong>{{ lastUpdate }}</strong>
      · Depuis <span class="src-tag redis">Redis</span>
    </div>

    <div v-if="store.loadingRealtime && !d" class="loading-row">
      <div class="loader-dots"><span></span><span></span><span></span></div>
    </div>

    <template v-else-if="d">
      <!-- System status -->
      <div class="sys-status-grid">
        <div class="sys-card active-drivers">
          <Truck :size="20"/>
          <div>
            <span class="sys-val">{{ d.active_drivers }}</span>
            <span class="sys-label">Livreurs actifs</span>
          </div>
          <div class="sys-detail">Clé Redis : <code>driver:*:available</code></div>
        </div>
        <div class="sys-card active-orders">
          <ShoppingBag :size="20"/>
          <div>
            <span class="sys-val">{{ d.active_orders_in_cache }}</span>
            <span class="sys-label">Commandes en cache</span>
          </div>
          <div class="sys-detail">Clé Redis : <code>order:*:status</code></div>
        </div>
        <div class="sys-card total-events">
          <Activity :size="20"/>
          <div>
            <span class="sys-val">{{ totalEvents24h }}</span>
            <span class="sys-label">Événements 24h</span>
          </div>
          <div class="sys-detail">Compteurs horaires Redis</div>
        </div>
        <div class="sys-card peak-hour">
          <BarChart2 :size="20"/>
          <div>
            <span class="sys-val">{{ peakHour }}</span>
            <span class="sys-label">Heure de pointe</span>
          </div>
          <div class="sys-detail">Basé sur page_view 24h</div>
        </div>
      </div>

      <!-- Per-event sparklines -->
      <div class="events-grid">
        <div v-for="(evKey, label) in eventLabels" :key="evKey" class="event-panel">
          <div class="ep-header">
            <div class="ep-left">
              <span class="ep-icon">{{ eventIcons[evKey] }}</span>
              <div>
                <p class="ep-name">{{ label }}</p>
                <p class="ep-total">{{ d.event_counters_24h[evKey]?.total_24h ?? 0 }} / 24h</p>
              </div>
            </div>
            <div :class="['ep-trend', getTrend(evKey) >= 0 ? 'up' : 'down']">
              <TrendingUp v-if="getTrend(evKey) >= 0" :size="12"/>
              <TrendingDown v-else :size="12"/>
              <span>{{ Math.abs(getTrend(evKey)) }}%</span>
            </div>
          </div>
          <!-- Sparkline bars -->
          <div class="sparkline">
            <div v-for="(h, hk) in getHourlyData(evKey)" :key="hk"
              class="spark-bar"
              :style="{ height: `${getBarPct(evKey, h)}%` }"
              :title="`${hk} : ${h}`">
            </div>
          </div>
          <div class="ep-footer">
            <span class="ep-key mono">{{ `analytics:events:${evKey}:YYYYMMDDH` }}</span>
          </div>
        </div>
      </div>

      <!-- Hourly breakdown chart (page_view) -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>Activité page_view - heure par heure (24h)</h3>
          <div class="chart-actions">
            <select v-model="selectedEvent" class="event-select">
              <option v-for="(evKey, label) in eventLabels" :key="evKey" :value="evKey">{{ label }}</option>
            </select>
          </div>
        </div>
        <Bar v-if="hourlyChart.labels.length" :data="hourlyChart" :options="chartOptions" style="max-height:220px"/>
        <div v-else class="chart-empty">Aucune donnée horaire pour cet événement</div>
      </div>

      <!-- Redis keys reference -->
      <div class="redis-ref-card">
        <div class="ref-header">
          <Zap :size="13" class="amber-icon"/>
          <h3>Structure des clés Redis utilisées</h3>
        </div>
        <div class="redis-keys-table">
          <div class="rkt-header">
            <span>Clé Redis</span><span>Type</span><span>TTL</span><span>Usage</span>
          </div>
          <div v-for="key in redisKeys" :key="key.pattern" class="rkt-row">
            <code class="rk-pattern">{{ key.pattern }}</code>
            <span :class="['rk-type', key.type.toLowerCase()]">{{ key.type }}</span>
            <span class="rk-ttl mono">{{ key.ttl }}</span>
            <span class="rk-usage">{{ key.usage }}</span>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Zap :size="40"/>
      <p>Données Redis non disponibles</p>
      <p class="empty-sub">Vérifiez <code>/api/v1/analytics/platform/realtime/</code></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import {
  RefreshCw, Clock, Truck, ShoppingBag, Activity, BarChart2,
  TrendingUp, TrendingDown, Zap
} from 'lucide-vue-next'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { format } from 'date-fns'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const store = useAnalyticsStore()
const d = computed(() => store.realtime)
const autoRefresh = ref(true)
const lastUpdate = ref('')
const selectedEvent = ref('page_view')
let interval: ReturnType<typeof setInterval> | null = null

const eventLabels: Record<string, string> = {
  page_view:       'Vues de pages',
  order_confirmed: 'Commandes confirmées',
  payment_success: 'Paiements réussis',
  payment_failed:  'Paiements échoués',
  search:          'Recherches',
  login:           'Connexions',
  register:        'Inscriptions',
  cart_abandoned:  'Paniers abandonnés',
}

const eventIcons: Record<string, string> = {
  page_view: '👁', order_confirmed: '✅', payment_success: '💳',
  payment_failed: '❌', search: '🔍', login: '🔑', register: '🆕', cart_abandoned: '🛒',
}

const eventColors: Record<string, string> = {
  page_view: '#3b82f6', order_confirmed: '#10b981', payment_success: '#10b981',
  payment_failed: '#ef4444', search: '#8b5cf6', login: '#f59e0b',
  register: '#14b8a6', cart_abandoned: '#f59e0b',
}

const totalEvents24h = computed(() => {
  if (!d.value) return 0
  return Object.values(d.value.event_counters_24h).reduce((s, e) => s + (e.total_24h ?? 0), 0)
})

const peakHour = computed(() => {
  if (!d.value?.event_counters_24h.page_view) return '-'
  const byHour = d.value.event_counters_24h.page_view.by_hour
  let max = 0; let peak = '-'
  for (const [h, c] of Object.entries(byHour)) {
    if (c > max) { max = c; peak = h }
  }
  return peak || '-'
})

function getHourlyData(evKey: string): Record<string, number> {
  return d.value?.event_counters_24h[evKey]?.by_hour ?? {}
}

function getBarPct(evKey: string, val: number) {
  const vals = Object.values(getHourlyData(evKey))
  const max = Math.max(...vals, 1)
  return Math.round((val / max) * 100)
}

function getTrend(evKey: string) {
  const byHour = getHourlyData(evKey)
  const vals = Object.values(byHour)
  if (vals.length < 4) return 0
  const recent = vals.slice(-4).reduce((s, v) => s + v, 0)
  const prev   = vals.slice(-8, -4).reduce((s, v) => s + v, 0) || 1
  return Math.round(((recent - prev) / prev) * 100)
}

const hourlyChart = computed(() => {
  const byHour = getHourlyData(selectedEvent.value)
  const sorted = Object.entries(byHour).sort(([a], [b]) => a.localeCompare(b))
  const color = eventColors[selectedEvent.value] || '#f59e0b'
  return {
    labels: sorted.map(([h]) => h),
    datasets: [{
      label: eventLabels[selectedEvent.value] || selectedEvent.value,
      data: sorted.map(([, v]) => v),
      backgroundColor: color + 'bb',
      borderColor: color,
      borderWidth: 1,
      borderRadius: 4,
    }]
  }
})

const chartOptions = {
  responsive: true,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#1e2330' } },
    y: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#1e2330' }, beginAtZero: true },
  }
}

const redisKeys = [
  { pattern: 'analytics:events:{type}:{YYYYMMDDHH}', type: 'STRING', ttl: '7 jours', usage: 'Compteur événement par heure' },
  { pattern: 'analytics:events:total:{type}',        type: 'STRING', ttl: 'Sans TTL', usage: 'Compteur global cumulatif' },
  { pattern: 'driver:*:available',                   type: 'STRING', ttl: '30s',    usage: 'Heartbeat disponibilité livreur' },
  { pattern: 'order:*:status',                       type: 'STRING', ttl: '1h',     usage: 'Statut commande en cache' },
  { pattern: 'menu:{restaurant_id}',                 type: 'STRING', ttl: '10 min', usage: 'Cache menu restaurant (JSON)' },
  { pattern: 'drivers:positions',                    type: 'GEO',    ttl: 'Sans TTL', usage: 'GeoSet positions GPS livreurs' },
  { pattern: 'channel:order:{id}',                   type: 'PUBSUB', ttl: '-',      usage: 'Canal temps réel suivi commande' },
  { pattern: 'channel:driver:{id}',                  type: 'PUBSUB', ttl: '-',      usage: 'Canal temps réel position GPS' },
]

async function load() {
  await store.fetchRealtime()
  lastUpdate.value = format(new Date(), 'HH:mm:ss')
}

watch(autoRefresh, (on) => {
  if (on) {
    interval = setInterval(load, 30_000)
  } else {
    if (interval) clearInterval(interval)
  }
})

onMounted(async () => {
  await load()
  if (autoRefresh.value) interval = setInterval(load, 30_000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.page-title  { font-family: var(--font-display); font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.page-sub    { font-size: 12px; color: var(--color-text-muted); margin: 0; font-family: var(--font-mono); }
.header-actions { display: flex; align-items: center; gap: 12px; }
.live-indicator { display: flex; align-items: center; gap: 7px; font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 8px; padding: 7px 12px; }
.live-indicator.active { color: var(--color-emerald); border-color: rgba(16,185,129,.4); }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-text-muted); }
.live-indicator.active .live-dot { background: var(--color-emerald); animation: pulse-amber 1.5s infinite; }
.toggle-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; color: var(--color-text-secondary); }
.toggle-label input { display: none; }
.toggle-track { width: 36px; height: 20px; background: var(--color-border); border-radius: 999px; position: relative; transition: background .2s; }
.toggle-label input:checked + .toggle-track { background: var(--color-amber); }
.toggle-thumb { position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; background: #fff; border-radius: 50%; transition: left .2s; }
.toggle-label input:checked + .toggle-track .toggle-thumb { left: 19px; }
.toggle-text { white-space: nowrap; }
.btn-refresh { display: flex; align-items: center; gap: 7px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-secondary); font-size: 13px; padding: 8px 14px; cursor: pointer; transition: all .15s; }
.btn-refresh:hover:not(:disabled) { border-color: var(--color-amber); color: var(--color-amber); }
.btn-refresh:disabled { opacity: .5; }

.last-update { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--color-text-muted); font-family: var(--font-mono); }
.last-update strong { color: var(--color-text-primary); }
.src-tag { border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 700; }
.src-tag.redis { background: rgba(245,158,11,.12); color: #fbbf24; border: 1px solid rgba(245,158,11,.25); }

.loading-row { display: flex; justify-content: center; padding: 40px; }
.loader-dots { display: flex; gap: 6px; }
.loader-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--color-amber); animation: bounce 1.2s infinite; }
.loader-dots span:nth-child(2) { animation-delay: .2s; }
.loader-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }

.sys-status-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }
@media (max-width: 900px) { .sys-status-grid { grid-template-columns: repeat(2,1fr); } }
.sys-card { display: flex; align-items: center; gap: 14px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 16px 18px; position: relative; overflow: hidden; }
.sys-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--color-amber); }
.sys-card.active-drivers::before  { background: var(--color-emerald); }
.sys-card.active-orders::before   { background: var(--color-blue); }
.sys-card.total-events::before    { background: var(--color-violet); }
.sys-card.peak-hour::before       { background: var(--color-amber); }
.sys-card svg { color: var(--color-text-muted); flex-shrink: 0; }
.sys-val   { display: block; font-family: var(--font-display); font-size: 26px; font-weight: 800; }
.sys-label { font-size: 11px; color: var(--color-text-muted); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: .06em; }
.sys-detail { position: absolute; bottom: 8px; right: 12px; font-size: 10px; color: var(--color-text-muted); font-family: var(--font-mono); }
.sys-detail code { background: var(--color-surface-2); padding: 1px 5px; border-radius: 3px; }

.events-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }
@media (max-width: 1200px) { .events-grid { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 700px)  { .events-grid { grid-template-columns: 1fr; } }
.event-panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.ep-header { display: flex; align-items: flex-start; justify-content: space-between; }
.ep-left { display: flex; align-items: center; gap: 10px; }
.ep-icon { font-size: 20px; }
.ep-name  { font-size: 13px; font-weight: 600; margin: 0 0 3px; }
.ep-total { font-family: var(--font-mono); font-size: 18px; font-weight: 800; margin: 0; color: var(--color-amber); }
.ep-trend { display: flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-size: 11px; font-weight: 700; }
.ep-trend.up   { color: var(--color-emerald); }
.ep-trend.down { color: var(--color-red); }

.sparkline { display: flex; align-items: flex-end; gap: 2px; height: 48px; }
.spark-bar { flex: 1; background: var(--color-amber); border-radius: 2px 2px 0 0; min-height: 2px; transition: height .3s; opacity: .75; }

.ep-footer { border-top: 1px solid var(--color-border); padding-top: 8px; }
.ep-key { font-size: 9px; color: var(--color-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
.mono { font-family: var(--font-mono); }

.chart-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 20px; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.chart-actions { display: flex; gap: 8px; }
.event-select { background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: 7px; color: var(--color-text-primary); font-size: 12px; padding: 6px 10px; outline: none; }
.event-select option { background: var(--color-surface-2); }
.chart-empty { text-align: center; padding: 32px; color: var(--color-text-muted); font-size: 12px; }

.redis-ref-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 20px; }
.ref-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.ref-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.amber-icon { color: var(--color-amber); }
.redis-keys-table { overflow-x: auto; }
.rkt-header { display: grid; grid-template-columns: 2fr 80px 90px 1fr; gap: 12px; padding: 8px 0; font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--color-text-muted); border-bottom: 1px solid var(--color-border); }
.rkt-row { display: grid; grid-template-columns: 2fr 80px 90px 1fr; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--color-border); align-items: center; font-size: 12px; }
.rkt-row:last-child { border: none; }
.rk-pattern { font-family: var(--font-mono); font-size: 11px; color: var(--color-emerald); background: rgba(16,185,129,.06); padding: 2px 7px; border-radius: 4px; }
.rk-type { font-family: var(--font-mono); font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; text-transform: uppercase; }
.rk-type.string { background: rgba(59,130,246,.1); color: #60a5fa; }
.rk-type.geo    { background: rgba(245,158,11,.1); color: #fbbf24; }
.rk-type.pubsub { background: rgba(139,92,246,.1); color: #a78bfa; }
.rk-ttl { font-size: 12px; color: var(--color-text-muted); }
.rk-usage { font-size: 12px; color: var(--color-text-secondary); }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 80px; color: var(--color-text-muted); text-align: center; }
.empty-state p { margin: 0; font-size: 14px; }
.empty-sub { font-size: 12px !important; font-family: var(--font-mono); }
.empty-sub code { background: var(--color-surface-2); padding: 1px 6px; border-radius: 4px; }
</style>

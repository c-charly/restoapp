<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">Funnel de Conversion</h2>
        <p class="page-sub">Parcours utilisateur de la vue restaurant jusqu'à la commande confirmée</p>
      </div>
      <div class="header-actions">
        <div class="period-group">
          <button v-for="p in periods" :key="p.v" :class="['period-btn',{active:days===p.v}]" @click="days=p.v;load()">{{ p.l }}</button>
        </div>
        <button class="btn-refresh" @click="load" :disabled="loading">
          <RefreshCw :size="13" :class="{'animate-spin-slow':loading}"/> Actualiser
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-row"><div class="loader-dots"><span></span><span></span><span></span></div></div>

    <template v-else-if="data">
      <!-- Summary chips -->
      <div class="summary-grid">
        <div class="sum-card amber">
          <span class="sum-val">{{ data.total_funnels }}</span>
          <span class="sum-label">Funnels totaux</span>
        </div>
        <div class="sum-card emerald">
          <span class="sum-val">{{ data.conversion_rate_pct?.toFixed(1) }}%</span>
          <span class="sum-label">Taux de conversion</span>
        </div>
        <div class="sum-card blue">
          <span class="sum-val">{{ fmtDuration(data.avg_time_to_convert_seconds) }}</span>
          <span class="sum-label">Temps moy. de conversion</span>
        </div>
        <div class="sum-card red">
          <span class="sum-val">{{ data.total_funnels - Math.round(data.total_funnels * data.conversion_rate_pct / 100) }}</span>
          <span class="sum-label">Funnels abandonnés</span>
        </div>
      </div>

      <!-- Funnel visualization -->
      <div class="funnel-card">
        <div class="funnel-card-header">
          <h3>Entonnoir étape par étape</h3>
          <span class="src-badge pg">PostgreSQL ConversionFunnel</span>
        </div>
        <div class="funnel-viz">
          <div v-for="(step, i) in data.funnel_steps" :key="step.step" class="funnel-step-row">
            <div class="step-info">
              <span class="step-num">{{ i + 1 }}</span>
              <span class="step-name">{{ stepLabel(step.step) }}</span>
            </div>
            <div class="step-bar-wrap">
              <div class="step-bar" :style="{ width: `${100 - step.drop_off_pct}%`, background: stepColor(i) }"></div>
              <div class="step-bar-ghost" :style="{ width: `${step.drop_off_pct}%` }"></div>
            </div>
            <div class="step-metrics">
              <span class="step-reached">{{ step.users_reached }} utilisateurs</span>
              <span :class="['step-drop', step.drop_off_pct > 30 ? 'high-drop':'']">
                {{ step.drop_off_pct.toFixed(1) }}% abandon
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts row -->
      <div class="charts-row">
        <!-- Abandon by step -->
        <div class="chart-card">
          <div class="chart-header"><h3>Abandons par étape</h3></div>
          <Bar v-if="abandonChart.labels.length" :data="abandonChart" :options="barOpts" style="max-height:250px"/>
          <div v-else class="chart-empty">Aucun abandon enregistré</div>
        </div>

        <!-- Conversion rate donut -->
        <div class="chart-card">
          <div class="chart-header"><h3>Conversion vs Abandon</h3></div>
          <Doughnut v-if="conversionDonut.labels?.length" :data="conversionDonut" :options="donutOpts"/>
        </div>

        <!-- Top abandoned restaurants -->
        <div class="chart-card">
          <div class="chart-header"><h3>Restaurants avec plus d'abandons</h3></div>
          <div v-if="data.top_abandoned_restaurants?.length" class="abandoned-list">
            <div v-for="(r, i) in data.top_abandoned_restaurants" :key="r.restaurant_name" class="ab-row">
              <span class="ab-rank">{{ i+1 }}</span>
              <span class="ab-name">{{ r.restaurant_name }}</span>
              <div class="ab-bar-bg">
                <div class="ab-bar" :style="{ width: `${(r.cnt / data.top_abandoned_restaurants[0].cnt) * 100}%` }"></div>
              </div>
              <span class="ab-count mono">{{ r.cnt }}</span>
            </div>
          </div>
          <div v-else class="chart-empty">Aucun abandon par restaurant</div>
        </div>
      </div>

      <!-- Conversion rate timeline (simulated from period) -->
      <div class="insight-card">
        <div class="insight-header">
          <Lightbulb :size="14" class="amber-icon"/>
          <h3>Insights clés</h3>
        </div>
        <div class="insights-grid">
          <div class="insight-item">
            <span class="insight-icon">🎯</span>
            <div>
              <p class="insight-title">Taux de conversion</p>
              <p class="insight-val">{{ data.conversion_rate_pct?.toFixed(1) }}% des funnels aboutissent à une commande</p>
            </div>
          </div>
          <div class="insight-item" v-if="worstStep">
            <span class="insight-icon">⚠️</span>
            <div>
              <p class="insight-title">Étape la plus problématique</p>
              <p class="insight-val">{{ stepLabel(worstStep.step) }} - {{ worstStep.drop_off_pct?.toFixed(1) }}% d'abandon</p>
            </div>
          </div>
          <div class="insight-item">
            <span class="insight-icon">⏱️</span>
            <div>
              <p class="insight-title">Temps de décision</p>
              <p class="insight-val">Un client met en moyenne {{ fmtDuration(data.avg_time_to_convert_seconds) }} pour convertir</p>
            </div>
          </div>
          <div class="insight-item" v-if="data.top_abandoned_restaurants?.length">
            <span class="insight-icon">🍽️</span>
            <div>
              <p class="insight-title">Restaurant le plus abandonné</p>
              <p class="insight-val">{{ data.top_abandoned_restaurants[0]?.restaurant_name }} ({{ data.top_abandoned_restaurants[0].cnt }} abandons)</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Filter :size="40"/>
      <p>Données funnel non disponibles</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import { RefreshCw, Lightbulb, Filter } from 'lucide-vue-next'
import { analyticsService } from '@/services/analytics.service'
import type { FunnelAnalysis } from '@/types/analytics'

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const loading = ref(false)
const data = ref<FunnelAnalysis | null>(null)
const days = ref(30)
const periods = [{ v: 7, l: '7j' }, { v: 30, l: '30j' }, { v: 90, l: '90j' }]

const stepLabels: Record<string, string> = {
  restaurant_viewed: '👁 Restaurant consulté',
  menu_opened: '📋 Menu ouvert',
  item_added_to_cart: '🛒 Item ajouté au panier',
  order_started: '▶️ Commande démarrée',
  payment_initiated: '💳 Paiement initié',
  order_confirmed: '✅ Commande confirmée',
}
const stepColors = ['#8b5cf6','#3b82f6','#f59e0b','#fbbf24','#10b981','#34d399']

function stepLabel(s: string) { return stepLabels[s] || s.replace(/_/g,' ') }
function stepColor(i: number) { return stepColors[i % stepColors.length] }
function fmtDuration(s: number) {
  if (!s) return '-'
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`
}

const worstStep = computed(() => {
  if (!data.value) return null
  return data.value.funnel_steps?.reduce((w, s) => s.drop_off_pct > (w?.drop_off_pct ?? 0) ? s : w, null as any)
})

const abandonChart = computed(() => {
  if (!data.value) return { labels: [], datasets: [] }
  const entries = Object.entries(data.value.abandon_by_step ?? {})
  return {
    labels: entries.map(([k]) => `Étape ${k}`),
    datasets: [{ label: 'Abandons', data: entries.map(([,v]) => v), backgroundColor: '#ef4444', borderRadius: 5 }]
  }
})

const conversionDonut = computed(() => {
  if (!data.value) return { labels: [], datasets: [] }
  const converted = Math.round(data.value.total_funnels * data.value.conversion_rate_pct / 100)
  const abandoned = data.value.total_funnels - converted
  return {
    labels: ['Convertis', 'Abandonnés'],
    datasets: [{ data: [converted, abandoned], backgroundColor: ['#10b981','#ef4444'], borderColor: '#111318', borderWidth: 3 }]
  }
})

const barOpts = { responsive: true, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#1e2330' } }, y: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#1e2330' }, beginAtZero: true } } }
const donutOpts = { responsive: true, cutout: '60%', plugins: { legend: { position: 'bottom' as const, labels: { color: '#8892a4', font: { size: 10 }, boxWidth: 10, padding: 8 } } } }

async function load() {
  loading.value = true
  try { data.value = await analyticsService.getFunnelAnalysis(days.value) }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.page{display:flex;flex-direction:column;gap:20px}
.page-header{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px}
.page-title{font-family:var(--font-display);font-size:22px;font-weight:700;margin:0 0 4px}
.page-sub{font-size:12px;color:var(--color-text-muted);margin:0;font-family:var(--font-mono)}
.header-actions{display:flex;align-items:center;gap:10px}
.period-group{display:flex;background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;overflow:hidden}
.period-btn{background:none;border:none;padding:7px 14px;font-size:12px;cursor:pointer;color:var(--color-text-secondary);transition:all .15s}
.period-btn.active{background:var(--color-amber);color:#000;font-weight:700}
.btn-refresh{display:flex;align-items:center;gap:7px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;color:var(--color-text-secondary);font-size:13px;padding:8px 14px;cursor:pointer;transition:all .15s}
.btn-refresh:hover:not(:disabled){border-color:var(--color-amber);color:var(--color-amber)}
.btn-refresh:disabled{opacity:.5}
.loading-row{display:flex;justify-content:center;padding:40px}
.loader-dots{display:flex;gap:6px}
.loader-dots span{width:10px;height:10px;border-radius:50%;background:var(--color-amber);animation:bounce 1.2s infinite}
.loader-dots span:nth-child(2){animation-delay:.2s}
.loader-dots span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-8px)}}
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:900px){.summary-grid{grid-template-columns:repeat(2,1fr)}}
.sum-card{background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:6px;position:relative;overflow:hidden}
.sum-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.sum-card.amber::before{background:var(--color-amber)}
.sum-card.emerald::before{background:var(--color-emerald)}
.sum-card.blue::before{background:var(--color-blue)}
.sum-card.red::before{background:var(--color-red)}
.sum-card.amber .sum-val{color:var(--color-amber)}
.sum-card.emerald .sum-val{color:var(--color-emerald)}
.sum-card.blue .sum-val{color:var(--color-blue)}
.sum-card.red .sum-val{color:var(--color-red)}
.sum-val{font-family:var(--font-display);font-size:26px;font-weight:800}
.sum-label{font-size:11px;color:var(--color-text-muted);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.06em}
.funnel-card{background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px;overflow:hidden}
.funnel-card-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--color-border)}
.funnel-card-header h3{font-family:var(--font-display);font-size:14px;font-weight:700;margin:0}
.src-badge{font-family:var(--font-mono);font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;background:rgba(59,130,246,.12);color:#60a5fa;border:1px solid rgba(59,130,246,.25)}
.funnel-viz{padding:20px;display:flex;flex-direction:column;gap:12px}
.funnel-step-row{display:flex;align-items:center;gap:14px}
.step-info{display:flex;align-items:center;gap:10px;min-width:240px}
.step-num{width:24px;height:24px;border-radius:50%;background:var(--color-surface-2);border:1px solid var(--color-border);display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:11px;font-weight:700;flex-shrink:0}
.step-name{font-size:13px;font-weight:500}
.step-bar-wrap{flex:1;height:20px;display:flex;border-radius:4px;overflow:hidden}
.step-bar{height:100%;transition:width .6s;border-radius:4px 0 0 4px}
.step-bar-ghost{height:100%;background:rgba(239,68,68,.12);border-radius:0 4px 4px 0}
.step-metrics{display:flex;flex-direction:column;gap:2px;min-width:160px;text-align:right}
.step-reached{font-size:12px;font-weight:600;font-family:var(--font-mono)}
.step-drop{font-size:11px;color:var(--color-text-muted);font-family:var(--font-mono)}
.step-drop.high-drop{color:var(--color-red);font-weight:700}
.charts-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:1000px){.charts-row{grid-template-columns:1fr}}
.chart-card{background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px;padding:20px}
.chart-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.chart-header h3{font-family:var(--font-display);font-size:14px;font-weight:700;margin:0}
.chart-empty{text-align:center;padding:32px;color:var(--color-text-muted);font-size:12px}
.abandoned-list{display:flex;flex-direction:column;gap:8px}
.ab-row{display:flex;align-items:center;gap:8px;font-size:13px}
.ab-rank{font-family:var(--font-mono);font-size:12px;color:var(--color-text-muted);min-width:16px}
.ab-name{width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.ab-bar-bg{flex:1;height:6px;background:var(--color-surface-2);border-radius:3px;overflow:hidden}
.ab-bar{height:100%;background:var(--color-red);border-radius:3px;transition:width .5s}
.ab-count{font-family:var(--font-mono);font-size:11px;color:var(--color-text-muted)}
.mono{font-family:var(--font-mono)}
.insight-card{background:var(--color-surface);border:1px solid var(--color-border);border-radius:12px;padding:20px}
.insight-header{display:flex;align-items:center;gap:8px;margin-bottom:16px}
.insight-header h3{font-family:var(--font-display);font-size:14px;font-weight:700;margin:0}
.amber-icon{color:var(--color-amber)}
.insights-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
@media(max-width:800px){.insights-grid{grid-template-columns:1fr}}
.insight-item{display:flex;align-items:flex-start;gap:12px;background:var(--color-surface-2);border-radius:10px;padding:14px}
.insight-icon{font-size:20px;flex-shrink:0}
.insight-title{font-size:12px;font-weight:700;color:var(--color-text-muted);margin:0 0 4px;text-transform:uppercase;letter-spacing:.06em;font-family:var(--font-mono)}
.insight-val{font-size:13px;margin:0;color:var(--color-text-primary)}
.empty-state{display:flex;flex-direction:column;align-items:center;gap:12px;padding:80px;color:var(--color-text-muted);text-align:center}
.empty-state p{margin:0}
</style>

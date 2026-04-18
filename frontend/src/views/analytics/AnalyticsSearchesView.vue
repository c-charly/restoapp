<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">Analyse des Recherches</h2>
        <p class="page-sub">Ce que les utilisateurs cherchent · Lacunes catalogue - <span class="src-tag pg">PostgreSQL SearchQuery</span></p>
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

    <div v-if="loading" class="loading-row">
      <div class="loader-dots"><span></span><span></span><span></span></div>
    </div>

    <template v-else-if="data">
      <!-- Summary -->
      <div class="summary-chips">
        <div class="schip amber"><Search :size="11"/> {{ data.top_searches.length }} requêtes uniques</div>
        <div class="schip"><TrendingUp :size="11"/> Total : {{ totalSearches }} recherches</div>
        <div class="schip red"><AlertCircle :size="11"/> {{ data.searches_with_no_results.length }} requêtes sans résultat</div>
        <div class="schip blue"><BarChart3 :size="11"/> Taux sans résultat : {{ noResultRate.toFixed(1) }}%</div>
      </div>

      <!-- Two column layout: top searches + visual cloud -->
      <div class="main-row">
        <!-- Top searches table -->
        <div class="section-card">
          <div class="section-header">
            <h3>Top requêtes</h3>
            <input v-model="searchFilter" class="search-input" placeholder="Filtrer..."/>
          </div>
          <div class="searches-table">
            <div class="st-header">
              <span>#</span>
              <span>Requête</span>
              <span class="center">Recherches</span>
              <span class="center">Moy. résultats</span>
              <span class="center">Sans résultat</span>
              <span class="center">Barre</span>
            </div>
            <div v-for="(s, i) in filteredSearches" :key="s.query_normalized" class="st-row">
              <span class="rank">{{ i + 1 }}</span>
              <span class="query-text">"{{ s.query_normalized }}"</span>
              <span class="center mono bold">{{ s.cnt }}</span>
              <span class="center mono" :class="s.avg_results < 1 ? 'red-text':''">
                {{ s.avg_results.toFixed(1) }}
              </span>
              <span class="center mono" :class="s.zero_results > 0 ? 'warn-text':''">
                {{ s.zero_results > 0 ? s.zero_results : '-' }}
              </span>
              <div class="search-bar-bg">
                <div class="search-bar" :style="{width:`${(s.cnt / maxCnt) * 100}%`}"></div>
              </div>
            </div>
            <div v-if="filteredSearches.length === 0" class="empty-row">Aucune recherche trouvée</div>
          </div>
        </div>

        <!-- Visual word cloud (CSS-based) -->
        <div class="cloud-card">
          <div class="card-header-simple"><h3>Nuage de mots</h3></div>
          <div class="word-cloud">
            <span v-for="s in topForCloud" :key="s.query_normalized"
              class="cloud-word"
              :style="{
                fontSize: `${wordSize(s.cnt)}px`,
                color: wordColor(s.cnt),
                opacity: 0.5 + (s.cnt / maxCnt) * 0.5,
              }"
              :title="`${s.cnt} recherches`">
              {{ s.query_normalized }}
            </span>
          </div>
        </div>
      </div>

      <!-- Zero result searches - catalog gaps -->
      <div class="section-card danger-section">
        <div class="section-header">
          <div class="sh-left">
            <AlertCircle :size="14" class="red-icon"/>
            <h3>Recherches sans résultat - Lacunes du catalogue</h3>
          </div>
          <span class="badge-count red-badge">{{ data.searches_with_no_results.length }}</span>
        </div>
        <div v-if="data.searches_with_no_results.length" class="zero-grid">
          <div v-for="s in data.searches_with_no_results" :key="s.query_normalized" class="zero-item">
            <span class="zi-query">"{{ s.query_normalized }}"</span>
            <span class="zi-cnt">{{ s.cnt }}x</span>
          </div>
        </div>
        <div v-else class="chart-empty">✅ Toutes les recherches retournent des résultats</div>
        <div v-if="data.searches_with_no_results.length" class="catalog-tip">
          <Lightbulb :size="12" class="amber-icon"/>
          <span>Ces termes sont recherchés mais inexistants dans votre catalogue. Considérez l'ajout de ces items dans vos menus.</span>
        </div>
      </div>

      <!-- Trend chart: top 8 queries as bar -->
      <div class="chart-card-wide">
        <div class="chart-header">
          <h3>Volume des top 10 requêtes</h3>
          <span class="src-badge pg">PostgreSQL</span>
        </div>
        <Bar v-if="searchChart.labels.length" :data="searchChart" :options="barOpts" style="max-height:220px"/>
        <div v-else class="chart-empty">-</div>
      </div>
    </template>

    <div v-else class="empty-state">
      <Search :size="40"/>
      <p>Données recherches non disponibles</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import { RefreshCw, Search, TrendingUp, AlertCircle, BarChart3, Lightbulb } from 'lucide-vue-next'
import { analyticsService } from '@/services/analytics.service'
import type { TopSearchesResponse } from '@/types/analytics'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const loading = ref(false)
const data = ref<TopSearchesResponse | null>(null)
const days = ref(30)
const searchFilter = ref('')
const periods = [{ v: 7, l: '7j' }, { v: 30, l: '30j' }, { v: 90, l: '90j' }]

const maxCnt = computed(() => data.value?.top_searches[0]?.cnt ?? 1)

const filteredSearches = computed(() => {
  if (!data.value) return []
  const q = searchFilter.value.toLowerCase()
  return data.value.top_searches.filter(s => !q || s.query_normalized.includes(q))
})

const topForCloud = computed(() => data.value?.top_searches.slice(0, 40) ?? [])

const totalSearches = computed(() => data.value?.top_searches.reduce((s, r) => s + r.cnt, 0) ?? 0)
const noResultRate = computed(() => {
  if (!data.value || !totalSearches.value) return 0
  const total0 = data.value.searches_with_no_results.reduce((s, r) => s + r.cnt, 0)
  return (total0 / totalSearches.value) * 100
})

function wordSize(cnt: number) {
  const min = 11, max = 32
  return Math.round(min + ((cnt / maxCnt.value) * (max - min)))
}
function wordColor(cnt: number) {
  const ratio = cnt / maxCnt.value
  if (ratio > 0.7) return '#f59e0b'
  if (ratio > 0.4) return '#3b82f6'
  if (ratio > 0.2) return '#10b981'
  return '#8892a4'
}

const searchChart = computed(() => {
  const top = data.value?.top_searches.slice(0, 10) ?? []
  return {
    labels: top.map(s => `"${s.query_normalized}"`),
    datasets: [{
      label: 'Recherches',
      data: top.map(s => s.cnt),
      backgroundColor: top.map(s => s.zero_results > 0 ? 'rgba(239,68,68,0.7)' : 'rgba(59,130,246,0.7)'),
      borderRadius: 5,
    }]
  }
})

const barOpts = {
  responsive: true,
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c: any) => ` ${c.raw} recherches` } } },
  scales: {
    x: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#1e2330' } },
    y: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: '#1e2330' }, beginAtZero: true }
  }
}

async function load() {
  loading.value = true
  try { data.value = await analyticsService.getTopSearches(days.value) }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.page-title { font-family: var(--font-display); font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.page-sub { font-size: 12px; color: var(--color-text-muted); margin: 0; font-family: var(--font-mono); }
.src-tag { border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 700; background: rgba(59,130,246,.12); color: #60a5fa; border: 1px solid rgba(59,130,246,.25); }
.header-actions { display: flex; align-items: center; gap: 10px; }
.period-group { display: flex; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; }
.period-btn { background: none; border: none; padding: 7px 14px; font-size: 12px; cursor: pointer; color: var(--color-text-secondary); transition: all .15s; }
.period-btn.active { background: var(--color-amber); color: #000; font-weight: 700; }
.btn-refresh { display: flex; align-items: center; gap: 7px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-secondary); font-size: 13px; padding: 8px 14px; cursor: pointer; transition: all .15s; }
.btn-refresh:hover:not(:disabled) { border-color: var(--color-amber); color: var(--color-amber); }
.btn-refresh:disabled { opacity: .5; }
.loading-row { display: flex; justify-content: center; padding: 40px; }
.loader-dots { display: flex; gap: 6px; }
.loader-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--color-amber); animation: bounce 1.2s infinite; }
.loader-dots span:nth-child(2) { animation-delay: .2s; }
.loader-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }
.summary-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.schip { display: flex; align-items: center; gap: 6px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 7px 12px; font-size: 12px; color: var(--color-text-secondary); }
.schip.amber { border-color: rgba(245,158,11,.3); color: var(--color-amber); }
.schip.red   { border-color: rgba(239,68,68,.3);  color: var(--color-red); }
.schip.blue  { border-color: rgba(59,130,246,.3);  color: #60a5fa; }
.main-row { display: grid; grid-template-columns: 1fr 340px; gap: 14px; }
@media (max-width: 1000px) { .main-row { grid-template-columns: 1fr; } }
.section-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }
.section-card.danger-section { border-color: rgba(239,68,68,.2); }
.section-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid var(--color-border); gap: 12px; }
.section-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.sh-left { display: flex; align-items: center; gap: 8px; }
.red-icon { color: var(--color-red); }
.search-input { background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: 7px; color: var(--color-text-primary); font-size: 12px; padding: 6px 12px; outline: none; width: 180px; }
.search-input:focus { border-color: var(--color-amber); }
.badge-count { font-family: var(--font-mono); font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 700; flex-shrink: 0; }
.red-badge { background: rgba(239,68,68,.15); color: var(--color-red); border: 1px solid rgba(239,68,68,.3); }
.searches-table { overflow-x: auto; }
.st-header { display: grid; grid-template-columns: 30px 1fr 90px 100px 100px 100px; gap: 8px; padding: 10px 20px; font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); border-bottom: 1px solid var(--color-border); }
.st-row { display: grid; grid-template-columns: 30px 1fr 90px 100px 100px 100px; gap: 8px; padding: 10px 20px; border-bottom: 1px solid var(--color-border); align-items: center; font-size: 13px; transition: background .15s; }
.st-row:last-child { border: none; }
.st-row:hover { background: var(--color-surface-2); }
.rank { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-muted); }
.query-text { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.center { text-align: center; }
.mono { font-family: var(--font-mono); font-size: 12px; }
.bold { font-weight: 700; }
.red-text { color: var(--color-red) !important; }
.warn-text { color: var(--color-amber) !important; }
.search-bar-bg { height: 5px; background: var(--color-surface-2); border-radius: 3px; overflow: hidden; }
.search-bar { height: 100%; background: var(--color-blue); border-radius: 3px; }
.empty-row { text-align: center; padding: 20px; color: var(--color-text-muted); font-size: 12px; }
.cloud-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }
.card-header-simple { padding: 14px 20px; border-bottom: 1px solid var(--color-border); }
.card-header-simple h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.word-cloud { padding: 20px; display: flex; flex-wrap: wrap; gap: 10px 14px; align-items: center; justify-content: center; min-height: 220px; }
.cloud-word { font-weight: 700; font-family: var(--font-display); cursor: default; transition: opacity .2s, transform .2s; line-height: 1.2; }
.cloud-word:hover { opacity: 1 !important; transform: scale(1.1); }
.zero-grid { display: flex; flex-wrap: wrap; gap: 8px; padding: 16px 20px; }
.zero-item { display: flex; align-items: center; gap: 7px; background: rgba(239,68,68,.06); border: 1px solid rgba(239,68,68,.2); border-radius: 8px; padding: 6px 12px; }
.zi-query { font-size: 13px; font-weight: 500; color: var(--color-text-primary); }
.zi-cnt { font-family: var(--font-mono); font-size: 11px; color: var(--color-red); font-weight: 700; }
.catalog-tip { display: flex; align-items: flex-start; gap: 8px; padding: 12px 20px; background: rgba(245,158,11,.06); border-top: 1px solid rgba(245,158,11,.2); font-size: 12px; color: var(--color-text-secondary); }
.amber-icon { color: var(--color-amber); flex-shrink: 0; margin-top: 1px; }
.chart-card-wide { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 20px; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.src-badge { font-family: var(--font-mono); font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: rgba(59,130,246,.12); color: #60a5fa; border: 1px solid rgba(59,130,246,.25); }
.chart-empty { text-align: center; padding: 32px; color: var(--color-text-muted); font-size: 12px; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 80px; color: var(--color-text-muted); text-align: center; }
.empty-state p { margin: 0; }
</style>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Doughnut, Bar } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import { RefreshCw, Globe, TrendingUp, AlertTriangle, Zap, Search } from 'lucide-vue-next'
import { analyticsService } from '@/services/analytics.service'
import type { TopPagesResponse } from '@/types/analytics'
import { format } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import CopyToCliboard from '@/components/util/CopyToCliboard.vue'

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const loading = ref(false)
const data = ref<TopPagesResponse | null>(null)
const days = ref('30')
const methodFilter = ref('')
const searchPath = ref('')
const periods = [{ v: '7', l: '7j' }, { v: '30', l: '30j' }, { v: '90', l: '90j' }]

function fmtNum(v: number) { return new Intl.NumberFormat('fr-FR').format(v) }
function fmtDate(v: string) { try { return format(new Date(v), 'dd/MM HH:mm') } catch { return v } }
function responseColor(ms: number) {
  if (ms > 500) return 'text-red-500'
  if (ms > 200) return 'text-amber-500'
  return 'text-emerald-500'
}
function methodBadgeClass(method: string) {
  return {
    GET:    'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
    POST:   'bg-blue-500/10 text-blue-400 border-blue-500/25',
    PATCH:  'bg-amber-500/10 text-amber-400 border-amber-500/25',
    PUT:    'bg-violet-500/10 text-violet-400 border-violet-500/25',
    DELETE: 'bg-red-500/10 text-red-400 border-red-500/25',
  }[method] ?? 'bg-muted text-muted-foreground border-border'
}

const filteredPages = computed(() => {
  if (!data.value) return []
  return data.value.top_pages.filter(p => {
    const matchPath = !searchPath.value || p.path.toLowerCase().includes(searchPath.value.toLowerCase())
    const matchMethod = !methodFilter.value || p.method === methodFilter.value
    return matchPath && matchMethod
  })
})

const maxHits     = computed(() => Math.max(...(data.value?.top_pages.map(p => p.hits) ?? [1])))
const maxSlowMs   = computed(() => Math.max(...(data.value?.slowest_endpoints.map(s => s.avg_ms) ?? [1])))
const totalErrors = computed(() => data.value?.frequent_errors.reduce((s, e) => s + e.cnt, 0) ?? 0)
const total5xx    = computed(() => data.value?.frequent_errors.filter(e => e.http_status >= 500).reduce((s, e) => s + e.cnt, 0) ?? 0)
const slowestEndpoint = computed(() => data.value?.slowest_endpoints[0]?.path ?? '-')

const methodDonut = computed(() => {
  if (!data.value) return { labels: [], datasets: [] }
  const counts: Record<string, number> = {}
  data.value.top_pages.forEach(p => { counts[p.method] = (counts[p.method] || 0) + p.hits })
  const colorMap: Record<string, string> = { GET: '#10b981', POST: '#3b82f6', PUT: '#8b5cf6', PATCH: '#f59e0b', DELETE: '#ef4444' }
  const entries = Object.entries(counts)
  return {
    labels: entries.map(([k]) => k),
    datasets: [{ data: entries.map(([, v]) => v), backgroundColor: entries.map(([k]) => colorMap[k] || '#6b7280'), borderWidth: 0 }]
  }
})

const responseTimeChart = computed(() => {
  if (!data.value) return { labels: [], datasets: [] }
  const top = data.value.top_pages.slice(0, 12)
  return {
    labels: top.map(p => p.path.replace('/api/v1/', '')),
    datasets: [{
      label: 'Reponse moy. (ms)',
      data: top.map(p => Math.round(p.avg_response_ms)),
      backgroundColor: top.map(p => p.avg_response_ms > 300 ? 'rgba(239,68,68,0.75)' : p.avg_response_ms > 100 ? 'rgba(245,158,11,0.75)' : 'rgba(16,185,129,0.75)'),
      borderRadius: 5,
    }]
  }
})

const donutOpts = {
  responsive: true, cutout: '60%',
  plugins: { legend: { position: 'bottom' as const, labels: { color: '#8892a4', font: { size: 10 }, boxWidth: 10, padding: 8 } } }
}
const barOpts = {
  responsive: true,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#8892a4', font: { size: 9 } }, grid: { display: false } },
    y: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { color: 'oklch(0.922 0 0)' }, beginAtZero: true }
  }
}

async function load() {
  loading.value = true
  try { data.value = await analyticsService.getTopPages(Number(days.value), methodFilter.value === 'tous' ? '' : methodFilter.value) }
  catch (e) { console.error(e) }
  finally { loading.value = false 
    console.log(data.value)
  }
}
onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6 overscroll-none">
    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Pages & Endpoints API</h1>
        <span class="text-xs font-mono text-muted-foreground">Performance · Erreurs · Frequentation</span>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- Period toggle -->
        <div class="flex rounded-lg border overflow-hidden">
          <button
            v-for="p in periods" :key="p.v"
            :class="['px-3.5 py-1.5 text-xs font-semibold transition-colors', days === p.v ? 'bg-primary text-primary-foreground' : 'bg-background text-muted-foreground hover:text-foreground']"
            @click="days = p.v; load()"
          >{{ p.l }}</button>
        </div>
        <Select v-model="methodFilter" @update:model-value="load">
          <SelectTrigger class="w-36 h-8 text-xs">
            <SelectValue placeholder="Toutes methodes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tous">Toutes methodes</SelectItem>
            <SelectItem v-for="m in ['GET','POST','PUT','PATCH','DELETE']" :key="m" :value="m">{{ m }}</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" @click="load" :disabled="loading">
          <RefreshCw class="size-3.5" :class="{ 'animate-spin': loading }" />Actualiser
        </Button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && !data" class="space-y-3">
      <div class="flex gap-2">
        <Skeleton v-for="i in 5" :key="i" class="h-9 w-36 rounded-lg" />
      </div>
      <Skeleton class="h-64 w-full rounded-xl" />
    </div>

    <template v-else-if="data">
      <!-- KPI chips -->
      <div class="flex flex-wrap gap-2">
        <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-amber-500/30 text-amber-500 bg-amber-500/5">
          <Globe class="size-3" />{{ data.top_pages.length }} endpoints uniques
        </div>
        <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-blue-500/30 text-blue-400 bg-blue-500/5">
          <TrendingUp class="size-3" />Trafic analysé sur {{ data.period_days }} jours
        </div>
        <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-amber-500/30 text-amber-500 bg-amber-500/5">
          <AlertTriangle class="size-3" />{{ totalErrors }} erreurs 4xx
        </div>
        <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-red-500/30 text-red-500 bg-red-500/5">
          <AlertTriangle class="size-3" />{{ total5xx }} erreurs 5xx
        </div>
        <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 text-muted-foreground">
          <Zap class="size-3" />Endpoint le + lent : <strong class="ml-1 text-foreground font-mono text-[10px]">{{ slowestEndpoint }}</strong>
        </div>
      </div>

      <!-- Top pages table -->
      <Card class="">
        <CardHeader class="pb-3 flex flex-row items-center justify-between gap-3 flex-wrap">
          <CardTitle class="text-sm">Top endpoints - frequentation</CardTitle>
          <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <Input v-model="searchPath" placeholder="Filtrer par path..." class="pl-8 h-8 text-xs w-52" />
          </div>
        </CardHeader>
        <CardContent>
          <div class="max-h-72 overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Methode + Path</TableHead>
                  <TableHead class="text-right">Hits</TableHead>
                  <TableHead class="text-right">Utilisateurs</TableHead>
                  <TableHead class="text-right">Reponse moy.</TableHead>
                  <TableHead class="text-right">Erreurs</TableHead>
                  <TableHead class="text-right">Dernier acces</TableHead>
                  <TableHead class="w-24">Barre</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-if="!filteredPages.length">
                  <TableCell colspan="7" class="text-center py-8 text-muted-foreground text-sm">Aucun endpoint correspondant</TableCell>
                </TableRow>
                <TableRow v-for="p in filteredPages" :key="p.path + p.method" class="hover:bg-muted/40">
                  <TableCell>
                    <div class="flex items-center gap-2 overflow-hidden">
                      <span :class="['text-[9px] font-bold font-mono px-1.5 py-0.5 rounded border shrink-0', methodBadgeClass(p.method)]">{{ p.method }}</span>
                      <CopyToCliboard :value="p.path" />
                    </div>
                  </TableCell>
                  <TableCell class="text-right font-mono text-sm font-bold">{{ fmtNum(p.hits) }}</TableCell>
                  <TableCell class="text-right font-mono text-sm">{{ fmtNum(p.unique_users) }}</TableCell>
                  <TableCell :class="['text-right font-mono text-sm', responseColor(p.avg_response_ms)]">{{ Math.round(p.avg_response_ms) }} ms</TableCell>
                  <TableCell :class="['text-right font-mono text-sm', p.errors > 0 ? 'text-red-500' : 'text-muted-foreground']">
                    {{ p.errors > 0 ? p.errors : '-' }}
                  </TableCell>
                  <TableCell class="text-right font-mono text-xs text-muted-foreground">{{ p.last_accessed ? fmtDate(p.last_accessed) : '-' }}</TableCell>
                  <TableCell>
                    <div class="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div class="h-full bg-amber-500 rounded-full" :style="{ width: `${(p.hits / maxHits) * 100}%` }"></div>
                    </div>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <!-- Charts 3 cols -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Frequent errors -->
        <Card>
          <CardHeader class="pb-3 flex flex-row items-center justify-between">
            <CardTitle class="text-sm">Erreurs frequentes</CardTitle>
            <Badge variant="destructive" class="text-xs font-mono">{{ data.frequent_errors.length }}</Badge>
          </CardHeader>
          <CardContent>
            <div v-if="data.frequent_errors.length" class="space-y-2 max-h-72 overflow-y-auto">
              <div v-for="e in data.frequent_errors" :key="e.path + e.http_status"
                class="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                <span :class="['text-[11px] font-bold font-mono px-1.5 py-0.5 rounded border shrink-0', e.http_status >= 500 ? 'bg-red-500/10 text-red-400 border-red-500/25' : 'bg-amber-500/10 text-amber-400 border-amber-500/25']">
                  {{ e.http_status }}
                </span>
                <code class="flex-1 text-[11px] font-mono text-muted-foreground truncate">{{ e.path }}</code>
                <span class="font-mono text-xs text-muted-foreground shrink-0">{{ e.cnt }}x</span>
              </div>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-6">Aucune erreur enregistree</p>
          </CardContent>
        </Card>

        <!-- Slowest endpoints -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Endpoints les plus lents</CardTitle></CardHeader>
          <CardContent>
            <div v-if="data.slowest_endpoints.length" class="space-y-3">
              <div v-for="s in data.slowest_endpoints" :key="s.path" class="flex items-center gap-2">
                <code class="text-[10px] font-mono text-muted-foreground w-36 shrink-0 truncate">{{ s.path }}</code>
                <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-500"
                    :style="{ width: `${(s.avg_ms / maxSlowMs) * 100}%`, background: s.avg_ms > 500 ? '#ef4444' : s.avg_ms > 200 ? '#f59e0b' : '#10b981' }">
                  </div>
                </div>
                <span :class="['font-mono text-xs min-w-14 text-right', responseColor(s.avg_ms)]">{{ Math.round(s.avg_ms) }} ms</span>
              </div>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-6">Aucune donnee</p>
          </CardContent>
        </Card>

        <!-- Method donut -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Repartition par methode HTTP</CardTitle></CardHeader>
          <CardContent>
            <div class="h-48">
              <Doughnut v-if="methodDonut.labels.length" :data="methodDonut" :options="donutOpts" />
              <p v-else class="text-sm text-muted-foreground text-center py-8">-</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Response time bar chart -->
      <Card>
        <CardHeader class="pb-3 flex flex-row items-center justify-between flex-wrap gap-2">
          <CardTitle class="text-sm">Distribution des temps de reponse</CardTitle>
          <div class="flex items-center gap-4 flex-wrap">
            <span class="text-xs font-mono text-emerald-500">- &lt;100ms (rapide)</span>
            <span class="text-xs font-mono text-amber-500">- 100-300ms (correct)</span>
            <span class="text-xs font-mono text-red-500">- &gt;300ms (lent)</span>
          </div>
        </CardHeader>
        <CardContent>
          <div class="h-64s">
            <Bar v-if="responseTimeChart.labels.length" :data="responseTimeChart" :options="barOpts" />
            <p v-else class="text-sm text-muted-foreground text-center py-8">-</p>
          </div>
        </CardContent>
      </Card>
    </template>

    <!-- Empty state -->
    <div v-else class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
      <Globe class="size-10 opacity-40" />
      <p class="text-sm">Donnees pages non disponibles</p>
      <code class="text-xs bg-muted px-2 py-1 rounded font-mono">/api/v1/analytics/platform/top-pages/</code>
    </div>
  </div>
</template>
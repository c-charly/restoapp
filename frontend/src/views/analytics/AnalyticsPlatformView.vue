<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-2">
        <h2 class="text-2xl font-semibold tracking-tight">Vue d'ensemble plateforme</h2>
        <p class="text-sm text-muted-foreground">Agrégations des donnees</p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div class="inline-flex rounded-full border border-border bg-background p-1">
          <Button
            v-for="p in periods"
            :key="p.v"
            variant="ghost"
            size="sm"
            class="rounded-full px-3 text-xs font-semibold"
            :class="store.days === p.v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'"
            @click="changePeriod(p.v)">
            {{ p.l }}
          </Button>
        </div>

        <Button variant="outline" size="sm" class="gap-2" @click="load" :disabled="store.loadingOverview">
          <RefreshCw class="size-4" :class="store.loadingOverview ? 'animate-spin' : ''" />
          Actualiser
        </Button>
      </div>
    </div>

    <div v-if="store.loadingOverview && !d" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="rounded-3xl border border-border bg-card p-4">
        <Skeleton class="h-4 w-24 rounded-full" />
        <Skeleton class="mt-4 h-10 w-full rounded-2xl" />
      </div>
    </div>

    <template v-else-if="d">
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard label="Sessions totales" :value="d.sessions.total" format="number" accent="amber">
          <template #icon><Monitor :size="16" /></template>
        </StatCard>
        <StatCard label="Utilisateurs uniques" :value="d.sessions.unique_users" format="number" accent="blue">
          <template #icon><Users :size="16" /></template>
        </StatCard>
        <StatCard label="Page views" :value="d.page_views.total" format="number" accent="violet">
          <template #icon><Eye :size="16" /></template>
        </StatCard>
        <StatCard label="Revenus" :value="d.orders.revenue_xaf" format="currency" accent="emerald">
          <template #icon><TrendingUp :size="16" /></template>
        </StatCard>
        <StatCard label="Taux de conversion" :value="d.conversion.rate_pct" format="percent" accent="amber">
          <template #icon><Target :size="16" /></template>
        </StatCard>
        <StatCard label="Taux de rebond" :value="d.sessions.bounce_rate_pct" format="percent" accent="red">
          <template #icon><MousePointerClick :size="16" /></template>
        </StatCard>
      </div>

      <div class="flex flex-wrap gap-3">
        <div class="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
          <Clock :size="11" />
          <span>Durée moy. :</span>
          <span class="font-semibold text-foreground">{{ fmtDuration(d.sessions.avg_duration_seconds) }}</span>
        </div>

        <div class="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
          <Zap :size="11" />
          <span>Réponse API :</span>
          <span class="font-semibold text-foreground">{{ d.page_views.avg_ms }} ms</span>
        </div>

        <div class="inline-flex items-center gap-2 rounded-2xl border border-border bg-amber-50 px-4 py-2 text-sm text-amber-700">
          <AlertTriangle :size="11" />
          <span>Erreurs 4xx :</span>
          <span class="font-semibold">{{ d.page_views.errors_4xx }}</span>
        </div>

        <div class="inline-flex items-center gap-2 rounded-2xl border border-border bg-rose-50 px-4 py-2 text-sm text-rose-700">
          <AlertTriangle :size="11" />
          <span>Erreurs 5xx :</span>
          <span class="font-semibold">{{ d.page_views.errors_5xx }}</span>
        </div>

        <div class="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
          <UserPlus :size="11" />
          <span>Nouveaux users :</span>
          <span class="font-semibold text-foreground">{{ d.users.new }}</span>
          <span>/ {{ d.users.total }}</span>
        </div>

        <div class="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
          <ShoppingBag :size="11" />
          <span>Commandes :</span>
          <span class="font-semibold text-foreground">{{ d.orders.total }}</span>
          <span class="text-muted-foreground">•</span>
          <span class="font-semibold text-rose-600">Annulées : {{ d.orders.cancelled }}</span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-4">
        <Card class="overflow-hidden border border-border bg-card p-0">
          <CardHeader class="flex items-center justify-between gap-3 p-4">
            <CardTitle class="text-sm font-semibold">Activité horaire - 24h</CardTitle>
          </CardHeader>
          <div class="p-4">
            <Bar v-if="hourlyChart.labels.length" :data="hourlyChart" :options="barOpts" class="max-h-45" />
            <div v-else class="flex min-h-45 items-center justify-center text-sm text-muted-foreground">Aucune activité horaire</div>
          </div>
        </Card>

        <Card class="overflow-hidden border border-border bg-card p-0">
          <CardHeader class="flex items-center justify-between gap-3 p-4">
            <CardTitle class="text-sm font-semibold">Devices</CardTitle>
          </CardHeader>
          <div class="p-4">
            <Doughnut v-if="deviceChart.labels.length" :data="deviceChart" :options="donutOpts" class="max-h-45" />
            <div v-else class="flex min-h-49 items-center justify-center text-sm text-muted-foreground">-</div>
          </div>
        </Card>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-4">
        <Card class="overflow-hidden border border-border bg-card p-0">
          <CardHeader class="flex items-center justify-between gap-3 p-4">
            <CardTitle class="text-sm font-semibold">Top événements</CardTitle>
            <Badge variant="outline" class="">UserEvent</Badge>
          </CardHeader>
          <div class="p-4">
            <Bar v-if="eventsChart.labels.length" :data="eventsChart" :options="hBarOpts" class="max-h-65" />
            <div v-else class="flex min-h-65 items-center justify-center text-sm text-muted-foreground">-</div>
          </div>
        </Card>

        <Card class="overflow-hidden border border-border bg-card p-0">
          <CardHeader class="flex items-center justify-between gap-3 p-4">
            <CardTitle class="text-sm font-semibold">Résumé commandes</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4 p-4">
            <div class="space-y-3">
              <div class="flex items-center justify-between text-sm text-muted-foreground">
                <span>Total commandes</span>
                <span class="font-semibold text-foreground">{{ d.orders.total }}</span>
              </div>
              <div class="flex items-center justify-between text-sm text-muted-foreground">
                <span>Revenus</span>
                <span class="font-mono font-semibold text-amber-600">{{ fmtXAF(d.orders.revenue_xaf) }}</span>
              </div>
              <div class="flex items-center justify-between text-sm text-muted-foreground">
                <span>Valeur moyenne</span>
                <span class="font-semibold text-foreground">{{ fmtXAF(d.orders.avg_value_xaf) }}</span>
              </div>
              <div class="flex items-center justify-between text-sm text-muted-foreground">
                <span>Livrées</span>
                <span class="font-semibold text-emerald-600">{{ d.orders.delivered }}</span>
              </div>
              <div class="flex items-center justify-between text-sm text-muted-foreground">
                <span>Annulées</span>
                <span class="font-semibold text-rose-600">{{ d.orders.cancelled }}</span>
              </div>
              <div class="flex items-center justify-between text-sm text-muted-foreground">
                <span>Conversion</span>
                <span class="font-mono font-semibold text-foreground">
                  {{ d.conversion.rate_pct.toFixed(1) }}% <span class="text-xs text-muted-foreground">({{ d.conversion.funnels_converted }}/{{ d.conversion.funnels_total }})</span>
                </span>
              </div>
            </div>

            <div class="flex flex-wrap gap-2 pt-2 text-sm">
              <!-- <RouterLink to="/analytics/funnel" class="text-amber-500 hover:text-amber-600 font-semibold">Funnel -></RouterLink> -->
              <RouterLink to="/analytics/segmentation" class="text-amber-500 hover:text-amber-600 font-semibold">Segmentation -></RouterLink>
              <!-- <RouterLink to="/analytics/alerts" class="text-amber-500 hover:text-amber-600 font-semibold">Alertes -></RouterLink> -->
            </div>
          </CardContent>
        </Card>
      </div>

      <Card class="overflow-hidden border border-border bg-card p-0">
        <CardHeader class="flex items-center justify-between p-4">
          <CardTitle class="text-sm font-semibold">Top endpoints - {{ store.days }} jours</CardTitle>
          <RouterLink to="/analytics/pages" class="text-sm font-semibold text-amber-500 hover:text-amber-600">Analyse complète -></RouterLink>
        </CardHeader>

        <div class="divide-y divide-border">
          <div class="grid grid-cols-[1fr_80px_90px_80px] gap-3 px-4 py-3 text-xs uppercase tracking-[0.16em] font-medium font-mono text-muted-foreground">
            <span>Endpoint</span>
            <span>Hits</span>
            <span>Moy. ms</span>
            <span>Erreurs</span>
          </div>

          <div
            v-for="p in d.page_views.top_pages.slice(0,8)"
            :key="p.path"
            class="grid grid-cols-[1fr_80px_90px_80px] gap-3 px-4 py-3 items-center text-sm text-foreground">
            <div class="flex items-center gap-2 overflow-hidden">
              <span
                :class="[
                  'rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase',
                  p.method?.toLowerCase() === 'get' ? 'bg-emerald-100 text-emerald-700' :
                  p.method?.toLowerCase() === 'post' ? 'bg-sky-100 text-sky-700' :
                  p.method?.toLowerCase() === 'patch' ? 'bg-amber-100 text-amber-700' :
                  p.method?.toLowerCase() === 'put' ? 'bg-violet-100 text-violet-700' :
                  p.method?.toLowerCase() === 'delete' ? 'bg-rose-100 text-rose-700' :
                  'bg-slate-100 text-slate-700'
                ]"
              >
                {{ p.method }}
              </span>
              <code class="truncate font-mono text-xs text-muted-foreground">{{ p.path }}</code>
            </div>
            <span class="font-mono">{{ p.hits }}</span>
            <span :class="['font-mono', p.avg_ms > 300 ? 'text-amber-600' : 'text-foreground']">{{ Math.round(p.avg_ms) }} ms</span>
            <span :class="['font-mono', p.errors > 0 ? 'text-rose-600' : 'text-muted-foreground']">{{ p.errors }}</span>
          </div>
        </div>
      </Card>
    </template>

    <div v-else class="flex flex-col items-center justify-center gap-4 rounded-3xl border border-border bg-card p-10 text-center text-muted-foreground">
      <BarChart3 :size="40" class="text-muted-foreground/60" />
      <p class="text-lg font-semibold text-foreground">Données non disponibles</p>
      <p class="text-sm text-muted-foreground">Vérifiez <code class="rounded bg-muted px-1.5 py-0.5 text-[11px]">/api/v1/analytics/platform/overview/</code></p>
      <Button variant="outline" size="sm" @click="load">Réessayer</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Bar, Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import { RefreshCw, Monitor, Users, Eye, TrendingUp, Target, MousePointerClick, Clock, Zap, AlertTriangle, UserPlus, ShoppingBag, BarChart3 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAnalyticsStore } from '@/stores/analytics.store'
import StatCard from '@/components/StatCard.vue'

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const store = useAnalyticsStore()
const d = computed(() => store.overview)
const periods = [{ v: 7, l: '7j' }, { v: 30, l: '30j' }, { v: 90, l: '90j' }]

function changePeriod(v: number) {
  store.days = v
  load()
}

function fmtXAF(v: number) {
  return new Intl.NumberFormat('fr-FR').format(Math.round(v)) + ' XAF'
}

function fmtDuration(s: number) {
  const m = Math.floor(s / 60)
  return s < 60 ? `${s}s` : `${m}m ${s % 60}s`
}

const hourlyChart = computed(() => {
  const items = (d.value?.hourly_activity_24h ?? []) as Array<{ hour: string; hits: number }>
  return {
    labels: items.map(h => h.hour.slice(11, 16)),
    datasets: [{ label: 'Hits', data: items.map(h => h.hits), backgroundColor: 'rgba(245,158,11,0.7)', borderColor: '#f59e0b', borderWidth: 1, borderRadius: 4 }]
  }
})

const deviceChart = computed(() => {
  const items = (d.value?.device_breakdown ?? []) as Array<{ device_type: string; cnt: number }>
  const colors = ['#f59e0b', '#3b82f6', '#10b981', '#8b5cf6']
  return {
    labels: items.map(x => x.device_type),
    datasets: [{ data: items.map(x => x.cnt), backgroundColor: colors, borderColor: '#111318', borderWidth: 1 }]
  }
})

const eventsChart = computed(() => {
  const items = (d.value?.top_events ?? []) as Array<{ event_type: string; cnt: number }>
  return {
    labels: items.map(e => e.event_type.replace(/_/g, ' ')),
    datasets: [{ label: 'Occ.', data: items.map(e => e.cnt), backgroundColor: items.map((_: any, i: number) => `hsl(${30 + i * 18},80%,55%)`), borderRadius: 4 }]
  }
})

const tickColor = '#222222'
const baseOpts = {
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: tickColor, font: { size: 10 } }},
    y: { ticks: { color: tickColor, font: { size: 10 } }, beginAtZero: true }
  }
}
const barOpts = { responsive: true, ...baseOpts }
const hBarOpts = { responsive: true, indexAxis: 'y' as const, ...baseOpts }
const donutOpts = {
  responsive: true,
  cutout: '60%',
  plugins: {
    legend: { position: 'bottom' as const, labels: { color: tickColor, font: { size: 10 }, boxWidth: 10, padding: 8 } }
  }
}

async function load() {
  await store.fetchOverview()
}

onMounted(load)
</script>

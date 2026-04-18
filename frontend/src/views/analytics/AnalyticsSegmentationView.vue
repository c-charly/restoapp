<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { RefreshCw, Users, AlertTriangle, Clock, Star, MapPin, PieChart } from 'lucide-vue-next'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'

ChartJS.register(ArcElement, Tooltip, Legend)

const store = useAnalyticsStore()
const d = computed(() => store.segmentation)

function fmtXAF(v: number) { return new Intl.NumberFormat('fr-FR').format(Math.round(v)) + ' XAF' }
function deviceLabel(d: string) { return { mobile: 'Mobile', desktop: 'Desktop', tablet: 'Tablette', unknown: 'Inconnu' }[d] ?? d }
function tierLabel(t: string) { return { platinum: 'Platine', gold: 'Or', silver: 'Argent', bronze: 'Bronze', new: 'Nouveau' }[t] ?? t }
function tierClass(t: string) {
  return {
    platinum: 'bg-violet-500/10 text-violet-400 border-violet-500/25',
    gold:     'bg-amber-500/10 text-amber-400 border-amber-500/25',
    silver:   'bg-slate-400/10 text-slate-400 border-slate-400/25',
    bronze:   'bg-orange-700/10 text-orange-500 border-orange-700/25',
    new:      'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  }[t] ?? 'bg-muted text-muted-foreground border-border'
}

const premiumCount = computed(() => {
  if (!d.value) return 0
  return (d.value.by_loyalty_tier['gold'] ?? 0) + (d.value.by_loyalty_tier['platinum'] ?? 0)
})

const tierConfig = [
  { key: 'platinum', name: 'Platine',  color: '#8b5cf6' },
  { key: 'gold',     name: 'Or',       color: '#f59e0b' },
  { key: 'silver',   name: 'Argent',   color: '#94a3b8' },
  { key: 'bronze',   name: 'Bronze',   color: '#d97706' },
  { key: 'new',      name: 'Nouveau',  color: '#10b981' },
]
const tierData = computed(() => {
  if (!d.value) return []
  const total = d.value.total_profiles || 1
  return tierConfig.map(t => ({
    ...t,
    count: d.value!.by_loyalty_tier[t.key] ?? 0,
    pct: ((d.value!.by_loyalty_tier[t.key] ?? 0) / total) * 100,
  }))
})
const tierDonut = computed(() => ({
  labels: tierData.value.map(t => t.name),
  datasets: [{ data: tierData.value.map(t => t.count), backgroundColor: tierData.value.map(t => t.color), borderWidth: 0 }]
}))

const engageData = computed(() => {
  if (!d.value) return []
  const ed = d.value.engagement_distribution
  const total = Object.values(ed).reduce((s: number, v: any) => s + v, 0) || 1
  return [
    { label: '0-25 Faible',     count: ed['0-25 (faible)']  ?? 0, color: '#ef4444', pct: ((ed['0-25 (faible)']  ?? 0) / total) * 100 },
    { label: '26-50 Moyen',     count: ed['26-50 (moyen)']  ?? 0, color: '#f59e0b', pct: ((ed['26-50 (moyen)']  ?? 0) / total) * 100 },
    { label: '51-75 Bon',       count: ed['51-75 (bon)']    ?? 0, color: '#3b82f6', pct: ((ed['51-75 (bon)']    ?? 0) / total) * 100 },
    { label: '76-100 Excellent',count: ed['76-100 (excellent)'] ?? 0, color: '#10b981', pct: ((ed['76-100 (excellent)'] ?? 0) / total) * 100 },
  ]
})

const deviceEntries = computed(() => Object.entries(d.value?.by_device ?? {}).sort((a, b) => (b[1] as number) - (a[1] as number)))
const maxDevice = computed(() => Math.max(...deviceEntries.value.map(([, v]) => v as number), 1))
const deviceColors = ['#f59e0b', '#3b82f6', '#10b981', '#8b5cf6']
const deviceDonut = computed(() => ({
  labels: deviceEntries.value.map(([k]) => k),
  datasets: [{ data: deviceEntries.value.map(([, v]) => v), backgroundColor: deviceColors, borderWidth: 0 }]
}))

const rfmSegments = computed(() => {
  const total = d.value?.total_profiles || 1
  return [
    { label: 'Champions',   color: '#f59e0b', count: d.value?.by_loyalty_tier['platinum'] ?? 0, pct: ((d.value?.by_loyalty_tier['platinum'] ?? 0) / total) * 100, desc: 'Achats frequents, eleves, recents' },
    { label: 'Loyaux',      color: '#3b82f6', count: d.value?.by_loyalty_tier['gold'] ?? 0,      pct: ((d.value?.by_loyalty_tier['gold'] ?? 0) / total) * 100,     desc: 'Valeur elevee, engagement soutenu' },
    { label: 'Prometteurs', color: '#10b981', count: d.value?.by_loyalty_tier['new'] ?? 0,       pct: ((d.value?.by_loyalty_tier['new'] ?? 0) / total) * 100,      desc: "Recents, encore peu d'historique" },
    { label: 'A risque',    color: '#ef4444', count: d.value?.churn_risk.count ?? 0,             pct: d.value?.churn_risk.pct ?? 0,                                desc: 'Inactivite detectee, risque de perte' },
    { label: 'Dormants',    color: '#6b7280', count: d.value?.dormant_users_30d ?? 0,            pct: ((d.value?.dormant_users_30d ?? 0) / total) * 100,           desc: '30+ jours sans activite' },
  ]
})

const donutOpts = {
  responsive: true, cutout: '55%',
  plugins: { legend: { position: 'bottom' as const, labels: { color: '#8892a4', font: { size: 10 }, boxWidth: 10, padding: 8 } } }
}

async function load() { await store.fetchSegmentation() }
onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Segmentation Utilisateurs</h1>
          <span class="text-xs font-mono text-muted-foreground mt-1">Fidelite · Devices · Villes · Risque de depart</span>
      </div>
      <Button variant="outline" size="sm" @click="load" :disabled="store.loadingSegmentation">
        <RefreshCw class="size-3.5" :class="{ 'animate-spin': store.loadingSegmentation }" />Actualiser
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="store.loadingSegmentation && !d" class="space-y-4">
      <div class="grid grid-cols-4 gap-3"><Skeleton v-for="i in 4" :key="i" class="h-28 rounded-xl" /></div>
      <div class="grid grid-cols-3 gap-4"><Skeleton v-for="i in 6" :key="i" class="h-56 rounded-xl" /></div>
    </div>

    <template v-else-if="d">
      <!-- KPI row -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card>
          <CardContent class="p-5">
            <Users class="size-5 text-amber-500 mb-3" />
            <p class="text-3xl font-bold">{{ d.total_profiles }}</p>
            <p class="text-xs font-mono uppercase tracking-wider text-muted-foreground mt-1">Profils totaux</p>
          </CardContent>
        </Card>
        <Card class="border-red-500/20">
          <CardContent class="p-5">
            <AlertTriangle class="size-5 text-red-500 mb-3" />
            <p class="text-3xl font-bold">{{ d.churn_risk.count }}</p>
            <p class="text-xs text-muted-foreground">{{ d.churn_risk.pct.toFixed(1) }}% du total</p>
            <p class="text-xs font-mono uppercase tracking-wider text-muted-foreground mt-1">Risque de depart</p>
          </CardContent>
        </Card>
        <Card class="border-blue-500/20">
          <CardContent class="p-5">
            <Clock class="size-5 text-blue-400 mb-3" />
            <p class="text-3xl font-bold">{{ d.dormant_users_30d }}</p>
            <p class="text-xs font-mono uppercase tracking-wider text-muted-foreground mt-1">Dormants 30j+</p>
          </CardContent>
        </Card>
        <Card class="border-emerald-500/20">
          <CardContent class="p-5">
            <Star class="size-5 text-emerald-500 mb-3" />
            <p class="text-3xl font-bold">{{ premiumCount }}</p>
            <p class="text-xs text-muted-foreground">Gold + Platinum</p>
            <p class="text-xs font-mono uppercase tracking-wider text-muted-foreground mt-1">Clients premium</p>
          </CardContent>
        </Card>
      </div>

      <!-- Main 3 cols -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Loyalty tiers -->
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="text-sm">Tiers de fidelite</CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div v-for="tier in tierData" :key="tier.name" class="flex items-center gap-2">
              <span class="text-xs font-medium w-16 shrink-0">{{ tier.name }}</span>
              <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500" :style="{ width: `${tier.pct}%`, background: tier.color }"></div>
              </div>
              <div class="flex flex-col items-end min-w-12">
                <span class="text-xs font-bold font-mono">{{ tier.count }}</span>
                <span class="text-[10px] text-muted-foreground font-mono">{{ tier.pct.toFixed(1) }}%</span>
              </div>
            </div>
            <div class="h-44 mt-2">
              <Doughnut v-if="tierDonut.labels.length" :data="tierDonut" :options="donutOpts" />
            </div>
          </CardContent>
        </Card>

        <!-- Engagement distribution -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Distribution engagement (0-100)</CardTitle></CardHeader>
          <CardContent class="space-y-3">
            <div v-for="e in engageData" :key="e.label" class="flex items-center gap-2">
              <span class="text-xs w-28 shrink-0 font-medium">{{ e.label }}</span>
              <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500" :style="{ width: `${e.pct}%`, background: e.color }"></div>
              </div>
              <div class="flex flex-col items-end min-w-12">
                <span class="text-xs font-bold font-mono">{{ e.count }}</span>
                <span class="text-[10px] text-muted-foreground font-mono">{{ e.pct.toFixed(0) }}%</span>
              </div>
            </div>

            <Separator class="my-2" />
            <!-- Churn gauge -->
            <div>
              <p class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold mb-2">Risque de depart global</p>
              <div class="flex items-center gap-2">
                <div class="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-500"
                    style="background: linear-gradient(90deg, #f59e0b, #ef4444)"
                    :style="{ width: `${d.churn_risk.pct}%` }">
                  </div>
                </div>
                <span class="text-base font-bold text-red-500 min-w-12 text-right font-mono">{{ d.churn_risk.pct.toFixed(1) }}%</span>
              </div>
              <p class="text-xs text-muted-foreground mt-1.5">{{ d.churn_risk.count }} utilisateurs avec score churn ≥ 50</p>
            </div>
          </CardContent>
        </Card>

        <!-- Devices -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Devices preferes</CardTitle></CardHeader>
          <CardContent class="space-y-3">
            <div v-if="deviceEntries.length">
              <div v-for="([device, cnt], i) in deviceEntries" :key="device" class="flex items-center gap-2">
                <span class="text-sm shrink-0">{{ { mobile: '📱', desktop: '🖥️', tablet: '📲', unknown: '❓' }[device] ?? '-' }}</span>
                <span class="text-xs w-16 shrink-0">{{ deviceLabel(device) }}</span>
                <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                  <div class="h-full rounded-full bg-blue-500 transition-all" :style="{ width: `${((cnt as number) / maxDevice) * 100}%` }"></div>
                </div>
                <span class="font-mono text-xs text-muted-foreground min-w-8 text-right">{{ cnt }}</span>
              </div>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-4">Aucune donnee device</p>
            <div class="h-36 mt-2">
              <Doughnut v-if="deviceDonut.labels.length" :data="deviceDonut" :options="donutOpts" />
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Bottom row: cities + spenders + RFM -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Cities -->
        <Card>
          <CardHeader class="pb-3 flex flex-row items-center justify-between">
            <CardTitle class="text-sm">Repartition geographique</CardTitle>
            <MapPin class="size-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div v-if="d.by_city.length" class="space-y-2.5">
              <div v-for="(c, i) in d.by_city" :key="c.primary_city" class="flex items-center gap-2">
                <span class="font-mono text-xs text-muted-foreground w-4 shrink-0">{{ i + 1 }}</span>
                <span class="text-sm font-medium w-24 shrink-0 truncate">{{ c.primary_city }}</span>
                <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div class="h-full bg-violet-500 rounded-full" :style="{ width: `${(c.cnt / d.by_city[0].cnt) * 100}%` }"></div>
                </div>
                <span class="font-mono text-xs text-muted-foreground min-w-8 text-right">{{ c.cnt }}</span>
              </div>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-6">Aucune ville enregistree</p>
          </CardContent>
        </Card>

        <!-- Top spenders -->
        <Card>
          <CardHeader class="pb-3 flex flex-row items-center justify-between">
            <CardTitle class="text-sm">Top depensiers</CardTitle>
            <RouterLink to="/analytics/users" class="text-xs font-semibold text-amber-500 hover:text-amber-400 transition-colors">
              Tous les profils
            </RouterLink>
          </CardHeader>
          <CardContent class="space-y-2">
            <div v-if="d.top_spenders.length" class="space-y-2">
              <div v-for="(s, i) in d.top_spenders" :key="s.user__email"
                class="flex items-center gap-2.5 p-2 bg-muted/50 rounded-lg">
                <span class="text-base min-w-6">{{ ['🥇','🥈','🥉'][i] ?? (i + 1) }}</span>
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-semibold truncate">{{ s.user__email }}</p>
                  <span :class="['text-[10px] px-1.5 py-0.5 rounded border font-semibold', tierClass(s.loyalty_tier)]">
                    {{ tierLabel(s.loyalty_tier) }}
                  </span>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-xs font-bold font-mono text-amber-500">{{ fmtXAF(s.total_spent_xaf) }}</p>
                  <p class="text-[10px] font-mono text-muted-foreground">{{ s.total_orders }} cmd</p>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-6">Aucun spender</p>
          </CardContent>
        </Card>

        <!-- RFM segments -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Segments RFM estimes</CardTitle></CardHeader>
          <CardContent class="space-y-4">
            <div v-for="seg in rfmSegments" :key="seg.label" class="space-y-1.5">
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-semibold">{{ seg.label }}</span>
                <span class="font-mono text-xs text-muted-foreground">{{ seg.count }} users</span>
              </div>
              <div class="h-1.5 bg-muted rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500" :style="{ width: `${seg.pct}%`, background: seg.color }"></div>
              </div>
              <p class="text-xs text-muted-foreground">{{ seg.desc }}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </template>

    <!-- Empty -->
    <div v-else class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
      <PieChart class="size-10 opacity-40" />
      <p class="text-sm">Donnees segmentation non disponibles</p>
    </div>
  </div>
</template>
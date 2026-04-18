<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RefreshCw, User, Clock, Utensils, Smartphone, MapPin, Search } from 'lucide-vue-next'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { analyticsService } from '@/services/analytics.service'
import { useAuthStore } from '@/stores/auth.store'
import type { SessionItem } from '@/types/analytics'
import { format, formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'

const store = useAnalyticsStore()
const authStore = useAuthStore()
const p = computed(() => store.myProfile)
const mySessions = ref<SessionItem[]>([])

const engageDash = computed(() => p.value?.engagement_score ?? '0')
const churnDash  = computed(() => p.value?.churn_risk_score ?? '0')

function tierLabel(t: string) {
  return { platinum: 'Platine', gold: 'Or', silver: 'Argent', bronze: 'Bronze', new: 'Nouveau' }[t] ?? t
}
function tierVariant(t: string): 'default' | 'secondary' | 'outline' | 'destructive' {
  return { platinum: 'default', gold: 'default', silver: 'secondary', bronze: 'outline', new: 'secondary' }[t] as any ?? 'secondary'
}
function nextTierInfo(tier: string, spent: number) {
  const thresholds: Record<string, number> = { new: 15_000, bronze: 75_000, silver: 200_000, gold: 500_000 }
  const next = thresholds[tier]
  if (!next) return 'Niveau maximum atteint'
  const remaining = Math.max(0, next - spent)
  const labels = ['new','bronze','silver','gold','platinum']
  const nextLabel = tierLabel(labels[labels.indexOf(tier) + 1] ?? 'platinum')
  return `${new Intl.NumberFormat('fr-FR').format(remaining)} XAF pour ${nextLabel}`
}
function dayName(d: number | null) {
  if (d === null || d === undefined) return '-'
  return ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'][d] ?? '-'
}
function deviceLabel(d: string) { return { mobile: 'Mobile', desktop: 'Desktop', tablet: 'Tablette', unknown: 'Inconnu' }[d] ?? d }
function fmtXAF(v: number) { return new Intl.NumberFormat('fr-FR').format(Math.round(v)) + ' XAF' }
function fmtDuration(s: number) { const m = Math.floor(s / 60); return s < 60 ? `${s}s` : `${m}m ${s % 60}s` }
function fmtDateShort(v: string) { try { return format(new Date(v), 'dd/MM HH:mm') } catch { return v } }
function relDate(v: string) { try { return formatDistanceToNow(new Date(v), { locale: fr, addSuffix: true }) } catch { return v } }

const hourData = computed(() => {
  const h = p.value?.orders_by_hour ?? {}
  return Array.from({ length: 24 }, (_, i) => Number(h[String(i)] ?? 0))
})
const maxHour = computed(() => Math.max(...hourData.value, 1))
function hourPct(h: number) { return Math.round((hourData.value[h] / maxHour.value) * 100) }

async function load() {
  await store.fetchMyProfile()
  try { mySessions.value = await analyticsService.getMySessions() } catch {}
}
onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Mon Profil Analytics</h1>
        <span class="text-xs font-mono text-muted-foreground">Vos statistiques personnelles</span>
      </div>
      <Button variant="outline" size="sm" @click="load" :disabled="store.loadingMyProfile">
        <RefreshCw class="size-3.5" :class="{ 'animate-spin': store.loadingMyProfile }" />
        Actualiser
      </Button>
    </div>

    <!-- Loading skeletons -->
    <div v-if="store.loadingMyProfile && !p" class="space-y-4">
      <Skeleton class="h-32 w-full rounded-xl" />
      <div class="grid grid-cols-6 gap-2">
        <Skeleton v-for="i in 12" :key="i" class="h-16 rounded-lg" />
      </div>
    </div>

    <template v-else-if="p">
      <!-- Hero card -->
      <Card>
        <CardContent class="p-6 flex items-center gap-6 flex-wrap">
          <!-- Avatar + info -->
          <div class="flex items-center gap-4 flex-1 min-w-52">
            <div class="size-16 rounded-2xl bg-amber-500/10 border-2 border-amber-500/50 text-amber-500 text-2xl font-bold flex items-center justify-center shrink-0">
              {{ authStore.user?.email?.[0].toUpperCase() ?? '?' }}
            </div>
            <div>
              <p class="font-semibold text-base">{{ authStore.user?.email }}</p>
              <p class="text-xs font-mono text-muted-foreground mt-0.5">Membre {{ p.first_seen_at ? relDate(p.first_seen_at) : '-' }}</p>
              <p class="text-xs font-mono text-muted-foreground">Derniere visite {{ p.last_seen_at ? relDate(p.last_seen_at) : '-' }}</p>
            </div>
          </div>

          <!-- Tier -->
          <div class="flex items-center gap-3">
            <div>
              <Badge :variant="tierVariant(p.loyalty_tier)" class="text-sm px-3 py-1">
                {{ tierLabel(p.loyalty_tier) }}
              </Badge>
              <p class="text-xs text-muted-foreground font-mono mt-1.5">{{ nextTierInfo(p.loyalty_tier, p.total_spent_xaf) }}</p>
            </div>
          </div>

          <Separator orientation="vertical" class="h-16 hidden sm:block" />

          <!-- Score gauges -->
          <div class="flex gap-6">
            <div class="flex flex-col items-center gap-1.5">
              <div class="relative size-16">
                <svg viewBox="0 0 36 36" class="size-full -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3" class="text-muted" />
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3" class="text-emerald-500"
                    :stroke-dasharray="`${engageDash} 100`" stroke-linecap="round" />
                </svg>
                <span class="absolute inset-0 flex items-center justify-center text-sm font-bold">{{ p.engagement_score }}</span>
              </div>
              <span class="text-xs font-mono uppercase tracking-wider text-muted-foreground">Engagement</span>
            </div>
            <div class="flex flex-col items-center gap-1.5">
              <div class="relative size-16">
                <svg viewBox="0 0 36 36" class="size-full -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3" class="text-muted" />
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3" class="text-red-500"
                    :stroke-dasharray="`${churnDash} 100`" stroke-linecap="round" />
                </svg>
                <span class="absolute inset-0 flex items-center justify-center text-sm font-bold">{{ p.churn_risk_score }}</span>
              </div>
              <span class="text-xs font-mono uppercase tracking-wider text-muted-foreground">Churn Risk</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- KPI grid -->
      <div class="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2.5">
        <Card v-for="kpi in [
          { val: p.total_sessions,       label: 'Sessions',            color: '' },
          { val: p.total_page_views,     label: 'Pages vues',          color: '' },
          { val: p.total_events,         label: 'Evenements',          color: '' },
          { val: fmtXAF(p.total_spent_xaf), label: 'Depenses totales',color: 'text-amber-500' },
          { val: p.total_orders,         label: 'Commandes',           color: '' },
          { val: fmtXAF(p.avg_order_value_xaf), label: 'Panier moyen',color: '' },
          { val: p.orders_delivered,     label: 'Livrees',             color: 'text-emerald-500' },
          { val: p.orders_cancelled,     label: 'Annulees',            color: 'text-red-500' },
          { val: p.cart_abandonments,    label: 'Paniers abandonnes',  color: '' },
          { val: p.total_reviews,        label: 'Reviews',             color: '' },
          { val: p.avg_rating_given > 0 ? '★ ' + p.avg_rating_given : '-', label: 'Note moy. donnee', color: '' },
          { val: fmtDuration(p.avg_session_duration_seconds), label: 'Duree moy. session', color: '' },
        ]" :key="kpi.label">
          <CardContent class="p-3.5 flex flex-col gap-1">
            <span :class="['text-lg font-bold leading-tight', kpi.color]">{{ kpi.val }}</span>
            <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground leading-tight">{{ kpi.label }}</span>
          </CardContent>
        </Card>
      </div>

      <!-- Insights row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Habitudes -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm flex items-center gap-2"><User class="size-4" />Vos habitudes</CardTitle></CardHeader>
          <CardContent class="space-y-4">
            <div v-for="habit in [
              { icon: Utensils, title: 'Restaurant favori', val: p.favorite_restaurant_name || '-', sub: p.favorite_restaurant_orders + ' commandes' },
              { icon: Clock, title: 'Heure preferee', val: p.most_active_hour !== null ? p.most_active_hour + 'h00' : '-', sub: '' },
              { icon: Clock, title: 'Jour favori', val: dayName(p.most_active_day), sub: '' },
              { icon: Smartphone, title: 'Appareil prefere', val: deviceLabel(p.preferred_device) + ' · ' + (p.preferred_os || '-'), sub: '' },
            ]" :key="habit.title" class="flex items-start gap-3">
              <div class="size-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                <component :is="habit.icon" class="size-4 text-muted-foreground" />
              </div>
              <div>
                <p class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{{ habit.title }}</p>
                <p class="text-sm font-semibold mt-0.5">{{ habit.val }}</p>
                <p v-if="habit.sub" class="text-xs text-muted-foreground">{{ habit.sub }}</p>
              </div>
            </div>
            <div v-if="p.primary_city" class="flex items-start gap-3">
              <div class="size-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                <MapPin class="size-4 text-muted-foreground" />
              </div>
              <div>
                <p class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Ville principale</p>
                <p class="text-sm font-semibold mt-0.5">{{ p.primary_city }}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Commandes par heure -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Commandes par heure</CardTitle></CardHeader>
          <CardContent>

            <div class="flex items-end gap-0.5 h-24 mb-5">
              <div v-for="h in 24" :key="h - 1" class="flex-1 h-full flex flex-col items-end justify-end relative">

                <div 
                  class="w-full min-h-0.5 rounded-t-sm transition-all duration-300"
                  :class="hourPct(h - 1) > 0 ? 'bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.4)]' : 'bg-border'"
                  :style="{ height: `${hourPct(h - 1)}%` }" :title="`${hourData[h-1]} cmd`"></div>
                <span v-if="(h - 1) % 6 === 0" class="absolute -bottom-6 text-[9px] font-mono text-muted-foreground whitespace-nowrap">{{ h - 1 }}h</span>

              </div>
            </div>

            <div class="flex items-center gap-2 mt-1">
              <div class="size-2 rounded-sm bg-amber-500"></div>
              <span class="text-xs text-muted-foreground">Heure la plus active</span>
            </div>
          </CardContent>
        </Card>

        <!-- Recherches -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm flex items-center gap-2"><Search class="size-4" />Recherches frequentes</CardTitle></CardHeader>
          <CardContent class="space-y-3">
            <div v-if="p.top_search_queries.length" class="space-y-2">
              <div v-for="q in p.top_search_queries" :key="q.query" class="flex items-center gap-2 text-xs">
                <span class="font-medium truncate min-w-0 flex-shrink" style="max-width:100px">"{{ q.query }}"</span>
                <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div class="h-full bg-violet-500 rounded-full" :style="{ width: `${(q.count / p.top_search_queries[0].count) * 100}%` }"></div>
                </div>
                <span class="font-mono text-muted-foreground shrink-0">{{ q.count }}x</span>
              </div>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-3">Aucune recherche enregistree</p>

            <template v-if="p.top_visited_paths.length">
              <Separator />
              <p class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold">Top pages</p>
              <div v-for="path in p.top_visited_paths.slice(0, 5)" :key="path.path" class="flex items-center justify-between gap-2 text-xs border-b border-border pb-1.5 last:border-0">
                <code class="text-emerald-500 font-mono text-[10px] truncate">{{ path.path }}</code>
                <span class="font-mono text-muted-foreground shrink-0">{{ path.count }}</span>
              </div>
            </template>
          </CardContent>
        </Card>
      </div>

      <!-- Sessions -->
      <Card v-if="mySessions.length">
        <CardHeader class="pb-3 flex flex-row items-center justify-between">
          <CardTitle class="text-sm">Mes dernieres sessions</CardTitle>
          <span class="text-xs font-mono text-muted-foreground">{{ mySessions.length }} sessions recentes</span>
        </CardHeader>
        <CardContent class="p-0">
          <div class="divide-y">
            <div v-for="s in mySessions.slice(0, 10)" :key="s.id" class="flex items-center gap-3 px-4 py-3 flex-wrap text-xs">
              <span class="text-base shrink-0">{{ { mobile: '📱', desktop: '🖥️', tablet: '📲', unknown: '❓' }[s.device_type] ?? '❓' }}</span>
              <span class="text-muted-foreground min-w-20">{{ s.browser || s.os || '-' }}</span>
              <span class="font-mono text-muted-foreground">{{ fmtDateShort(s.started_at) }}</span>
              <span class="font-mono text-amber-500">{{ s.duration_seconds ? fmtDuration(s.duration_seconds) : '…' }}</span>
              <div class="flex items-center gap-3 text-muted-foreground">
                <span>{{ s.page_views_count }} vues</span>
                <span>{{ s.events_count }} evt.</span>
                <span>{{ s.orders_count }} cmd.</span>
              </div>
              <Badge v-if="s.is_bounce" variant="destructive" class="text-[10px] h-4 px-1.5">rebond</Badge>
              <Badge v-if="s.city" variant="secondary" class="text-[10px] h-4 px-1.5">{{ s.city }}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </template>

    <!-- Empty -->
    <div v-else class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
      <User class="size-10 opacity-40" />
      <p class="text-sm">Profil analytique non disponible</p>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, Zap, Eye, MousePointer, ShoppingBag, AlertCircle, Monitor, Search, Globe } from 'lucide-vue-next'
import { analyticsService } from '@/services/analytics.service'
import type { UserFullReport } from '@/types/analytics'
import { format, formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table'

const route = useRoute()
const loading = ref(false)
const report = ref<UserFullReport | null>(null)

function tierLabel(t: string) { return { platinum: 'Platine', gold: 'Or', silver: 'Argent', bronze: 'Bronze', new: 'Nouveau' }[t] ?? t }
function tierClass(t: string) {
  return {
    platinum: 'bg-violet-500/10 text-violet-400 border border-violet-500/25',
    gold:     'bg-amber-500/10 text-amber-400 border border-amber-500/25',
    silver:   'bg-slate-400/10 text-slate-400 border border-slate-400/25',
    bronze:   'bg-orange-700/10 text-orange-500 border border-orange-700/25',
    new:      'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25',
  }[t] ?? 'bg-muted text-muted-foreground'
}
function deviceLabel(d: string) { return { mobile: 'Mobile', desktop: 'Desktop', tablet: 'Tablette', unknown: 'Inconnu' }[d] ?? d }
function fmtXAF(v: number) { return new Intl.NumberFormat('fr-FR').format(Math.round(v)) + ' XAF' }
function fmtDate(v: string) { try { return format(new Date(v), 'dd/MM/yyyy') } catch { return v } }
function fmtDateShort(v: string) { try { return format(new Date(v), 'dd/MM HH:mm') } catch { return v } }
function relTime(v: string) { try { return formatDistanceToNow(new Date(v), { locale: fr, addSuffix: true }) } catch { return v } }
function fmtDuration(s: number) { const m = Math.floor(s / 60); return s < 60 ? `${s}s` : `${m}m ${s % 60}s` }
function dayLabel(d: number | null) {
  if (d === null || d === undefined) return '-'
  return ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'][d] ?? String(d)
}
function eventColorClass(t: string) {
  if (t.includes('payment')) return 'bg-emerald-500/10 text-emerald-400'
  if (t.includes('order'))   return 'bg-amber-500/10 text-amber-400'
  if (t.includes('cart'))    return 'bg-violet-500/10 text-violet-400'
  if (t.includes('login') || t.includes('register')) return 'bg-blue-500/10 text-blue-400'
  return 'bg-muted text-muted-foreground'
}

const kpiItems = computed(() => {
  const summary = report.value?.profile_summary
  if (!summary) return []

  const items = [
    { val: summary.total_sessions,       label: 'Sessions',            color: '' },
    { val: summary.total_page_views,     label: 'Pages vues',          color: '' },
    { val: summary.total_events,         label: 'Événements',          color: '' },
    { val: summary.total_orders,         label: 'Commandes',           color: '' },
    { val: fmtXAF(summary.total_spent_xaf), label: 'Dépenses totales', color: 'text-amber-500' },
    { val: fmtXAF(summary.avg_order_value_xaf), label: 'Panier moyen', color: '' },
    { val: summary.orders_delivered,     label: 'Livrées',             color: 'text-emerald-500' },
    { val: summary.orders_cancelled,     label: 'Annulées',            color: 'text-red-500' },
    { val: summary.cart_abandonments,    label: 'Paniers abandonnés',  color: '' },
    { val: summary.total_reviews,        label: 'Reviews',             color: '' },
    { val: summary.avg_rating_given > 0 ? '★ ' + summary.avg_rating_given.toFixed(1) : '-', label: 'Note moy.', color: '' },
    { val: summary.avg_session_duration_seconds !== undefined ? fmtDuration(summary.avg_session_duration_seconds) : '-', label: 'Durée moy. session', color: '' },
  ]

  return items.filter(item => item.val !== undefined && item.val !== null)
})

const ordersByHour = computed(() => {
  const h = report.value?.behavioral_patterns.orders_by_hour ?? {}
  return Array.from({ length: 24 }, (_, i) => h[String(i)] ?? 0)
})
const maxHourVal = computed(() => Math.max(...ordersByHour.value, 1))

const dayData = computed(() => {
  const map = report.value?.behavioral_patterns.orders_by_day ?? {}
  const names = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
  const vals = Array.from({ length: 7 }, (_, i) => map[String(i + 1)] ?? 0)
  const max = Math.max(...vals, 1)
  return names.map((name, i) => ({ name, count: vals[i], pct: (vals[i] / max) * 100 }))
})

const engagePct = computed(() => report.value?.profile_summary.engagement_score ?? 0)
const churnPct  = computed(() => report.value?.profile_summary.churn_risk_score ?? 0)

onMounted(async () => {
  loading.value = true
  try { report.value = await analyticsService.getUserDetail(route.params.userId as string) }
  catch (e) { console.error(e) }
  finally { loading.value = false }
})
</script>

<template>
  <div class="flex flex-col gap-6 max-w-7xl">
    <!-- Back -->
    <RouterLink to="/analytics/users" class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit">
      <ArrowLeft class="size-4" />Utilisateurs Analytics
    </RouterLink>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-32 w-full rounded-xl" />
      <div class="grid grid-cols-6 gap-2"><Skeleton v-for="i in 12" :key="i" class="h-16 rounded-lg" /></div>
    </div>

    <template v-else-if="report">
      <!-- Profile header -->
      <Card>
        <CardContent class="p-6 flex items-center gap-5 flex-wrap">
          <!-- Avatar -->
          <div class="size-16 rounded-2xl bg-amber-500/10 border-2 border-amber-500/50 text-amber-500 text-2xl font-bold flex items-center justify-center shrink-0">
            {{ report.user.email[0].toUpperCase() }}
          </div>
          <!-- Info -->
          <div class="flex-1 min-w-48">
            <h2 class="text-xl font-semibold">{{ report.user.email }}</h2>
            <div class="flex items-center gap-2 mt-2 flex-wrap">
              <Badge variant="outline" class="text-xs capitalize">{{ report.user.role }}</Badge>
              <span :class="['text-xs px-2 py-0.5 rounded font-semibold', tierClass(report.profile_summary.loyalty_tier)]">
                {{ tierLabel(report.profile_summary.loyalty_tier) }}
              </span>
              <span class="text-xs font-mono text-muted-foreground">Depuis {{ fmtDate(report.user.created_at) }}</span>
            </div>
          </div>

          <Separator orientation="vertical" class="h-16 hidden sm:block" />

          <!-- Score rings -->
          <div class="flex flex-col items-center gap-1.5">
            <div class="relative size-16">
              <svg viewBox="0 0 36 36" class="size-full -rotate-90">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3" class="text-muted" />
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#10b981" stroke-width="3"
                  :stroke-dasharray="`${engagePct.toFixed(0)} 100`" stroke-linecap="round" />
              </svg>
              <span class="absolute inset-0 flex items-center justify-center text-sm font-bold">{{ engagePct.toFixed(0) }}</span>
            </div>
            <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Engagement</span>
          </div>
          <div class="flex flex-col items-center gap-1.5">
            <div class="relative size-16">
              <svg viewBox="0 0 36 36" class="size-full -rotate-90">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3" class="text-muted" />
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#ef4444" stroke-width="3"
                  :stroke-dasharray="`${churnPct.toFixed(0)} 100`" stroke-linecap="round" />
              </svg>
              <span class="absolute inset-0 flex items-center justify-center text-sm font-bold">{{ churnPct.toFixed(0) }}</span>
            </div>
            <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Churn Risk</span>
          </div>
        </CardContent>
      </Card>

      <!-- KPIs -->
      <div class="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2.5">
        <Card v-for="kpi in kpiItems" :key="kpi.label">
          <CardContent class="p-3.5 flex flex-col gap-1">
            <span :class="['text-lg font-bold leading-tight', kpi.color]">{{ kpi.val }}</span>
            <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground leading-tight">{{ kpi.label }}</span>
          </CardContent>
        </Card>
      </div>

      <!-- Detail row: info + charts -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Info card -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Informations profil</CardTitle></CardHeader>
          <CardContent>
            <div class="space-y-0 divide-y">
              <div v-for="row in [
                { label: 'Premiere visite', val: report.profile_summary.first_seen_at ? fmtDate(report.profile_summary.first_seen_at) : '-', mono: true },
                { label: 'Derniere visite', val: report.profile_summary.last_seen_at ? relTime(report.profile_summary.last_seen_at) : '-', mono: true },
                { label: 'Device prefere', val: deviceLabel(report.profile_summary.preferred_device), mono: false },
                { label: 'OS prefere', val: report.profile_summary.preferred_os || '-', mono: false },
                { label: 'Ville principale', val: report.profile_summary.primary_city || '-', mono: false },
                { label: 'Restaurant favori', val: report.profile_summary.favorite_restaurant || '-', mono: false },
                { label: 'Heure + active', val: report.profile_summary.most_active_hour !== null ? report.profile_summary.most_active_hour + 'h' : '-', mono: true },
                { label: 'Jour + actif', val: dayLabel(report.profile_summary.most_active_day), mono: false },
              ]" :key="row.label" class="flex items-center justify-between py-2 text-xs">
                <span class="text-muted-foreground">{{ row.label }}</span>
                <span :class="['font-semibold', row.mono ? 'font-mono' : '']">{{ row.val }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Hours chart -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Heures de commande</CardTitle></CardHeader>
          <CardContent>
            <div class="flex items-end gap-0.5 h-24 mb-5">
              <div v-for="h in 24" :key="h - 1" class="flex-1 h-full flex flex-col items-end justify-end relative">
                <div class="w-full bg-amber-500 rounded-t-sm transition-all duration-300"
                  :style="{ height: `${((ordersByHour[h - 1] ?? 0) / maxHourVal) * 100}%` }"></div>
                <span v-if="(h - 1) % 6 === 0" class="absolute -bottom-6 text-[9px] font-mono text-muted-foreground whitespace-nowrap">{{ h - 1 }}h</span>
                <span class="text-[8px] font-mono text-muted-foreground mt-1">{{ ordersByHour[h - 1] ?? 0 }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Days chart -->
        <Card>
          <CardHeader class="pb-3"><CardTitle class="text-sm">Jours de commande</CardTitle></CardHeader>
          <CardContent class="space-y-2.5">
            <div v-for="d in dayData" :key="d.name" class="flex items-center gap-2 text-xs">
              <span class="font-mono text-muted-foreground w-7 shrink-0">{{ d.name }}</span>
              <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 rounded-full transition-all duration-500" :style="{ width: `${d.pct}%` }"></div>
              </div>
              <span class="font-mono text-muted-foreground min-w-5 text-right">{{ d.count }}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Tabs -->
      <Card>
        <Tabs default-value="sessions">
          <div class="border-b overflow-x-auto">
            <TabsList class="h-auto rounded-none border-b-0 bg-transparent p-0 w-full justify-start">
              <TabsTrigger
                v-for="tab in [
                  { id: 'sessions', label: 'Sessions',   count: report.sessions.length },
                  { id: 'events',   label: 'Evenements', count: report.recent_events.length },
                  { id: 'orders',   label: 'Commandes',  count: report.orders_timeline.length },
                  { id: 'searches', label: 'Recherches', count: report.recent_searches.length },
                  { id: 'alerts',   label: 'Alertes',    count: report.active_alerts.length },
                  { id: 'ips',      label: 'IPs connues',count: report.behavioral_patterns.known_ips.length },
                ]" :key="tab.id" :value="tab.id"
                class="rounded-lg border border-transparent data-[state=active]:border-muted data-[state=active]:bg-transparent data-[state=active]:shadow-xl py-3 px-4 m-1 text-xs font-semibold whitespace-nowrap"
              >
                {{ tab.label }}
                <span v-if="tab.count" class="ml-1.5 bg-muted rounded-full px-1.5 py-0.5 text-[10px] font-mono">{{ tab.count }}</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <!-- Sessions -->
          <TabsContent value="sessions" class="m-0">
            <div class="max-h-96 overflow-y-auto divide-y">
              <div v-if="!report.sessions.length" class="text-center py-8 text-sm text-muted-foreground">Aucune session</div>
              <div v-for="s in report.sessions.slice(0, 20)" :key="s.id"
                class="flex items-center gap-3 px-4 py-3 flex-wrap text-xs hover:bg-muted/30">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <Badge variant="outline" class="text-[10px] h-5">{{ s.device_type }}</Badge>
                  <Badge variant="outline" class="text-[10px] h-5">{{ s.os }}</Badge>
                  <Badge v-if="s.browser" variant="outline" class="text-[10px] h-5">{{ s.browser }}</Badge>
                </div>
                <span class="font-mono text-muted-foreground">{{ fmtDateShort(s.started_at) }}</span>
                <span class="font-mono text-amber-500">{{ s.duration_seconds ? fmtDuration(s.duration_seconds) : 'Active' }}</span>
                <div class="flex items-center gap-3 text-muted-foreground">
                  <span class="flex items-center gap-1"><Eye class="size-3" />{{ s.page_views_count }}</span>
                  <span class="flex items-center gap-1"><MousePointer class="size-3" />{{ s.events_count }}</span>
                  <span class="flex items-center gap-1"><ShoppingBag class="size-3" />{{ s.orders_count }}</span>
                </div>
                <Badge v-if="s.is_bounce" variant="destructive" class="text-[10px] h-4 px-1.5">rebond</Badge>
                <Badge v-if="s.city" variant="secondary" class="text-[10px] h-4 px-1.5">{{ s.city }}</Badge>
                <code class="font-mono text-[10px] text-muted-foreground ml-auto">{{ s.ip_address || '-' }}</code>
              </div>
            </div>
          </TabsContent>

          <!-- Events -->
          <TabsContent value="events" class="m-0">
            <div class="max-h-96 overflow-y-auto divide-y">
              <div v-if="!report.recent_events.length" class="text-center py-8 text-sm text-muted-foreground">Aucun evenement</div>
              <div v-for="e in report.recent_events.slice(0, 40)" :key="e.timestamp"
                class="flex items-center gap-3 px-4 py-2.5 flex-wrap text-xs hover:bg-muted/30">
                <span class="font-mono text-muted-foreground min-w-24">{{ fmtDateShort(e.timestamp) }}</span>
                <span :class="['font-mono text-[11px] font-bold px-2 py-0.5 rounded', eventColorClass(e.event_type)]">
                  {{ e.event_type.replace(/_/g, ' ') }}
                </span>
                <span v-if="e.object_type" class="text-muted-foreground">{{ e.object_type }}</span>
                <code v-if="e.object_id" class="font-mono text-[10px] text-muted-foreground">{{ e.object_id.slice(0, 8) }}...</code>
                <span v-if="Object.keys(e.properties).length" class="text-muted-foreground truncate max-w-48 text-[10px]">
                  {{ JSON.stringify(e.properties).slice(0, 60) }}
                </span>
              </div>
            </div>
          </TabsContent>

          <!-- Orders -->
          <TabsContent value="orders" class="m-0">
            <div class="max-h-96 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Statut</TableHead>
                    <TableHead>Restaurant</TableHead>
                    <TableHead class="text-right">Total</TableHead>
                    <TableHead class="text-right">Date</TableHead>
                    <TableHead class="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-if="!report.orders_timeline.length">
                    <TableCell colspan="5" class="text-center py-8 text-muted-foreground text-sm">Aucune commande</TableCell>
                  </TableRow>
                  <TableRow v-for="o in report.orders_timeline" :key="o.id">
                    <TableCell><Badge variant="outline" class="text-xs capitalize">{{ o.status }}</Badge></TableCell>
                    <TableCell class="text-sm">{{ o['restaurant__name'] }}</TableCell>
                    <TableCell class="text-right font-mono text-xs text-amber-500 font-semibold">{{ fmtXAF(parseFloat(o.total_price)) }}</TableCell>
                    <TableCell class="text-right font-mono text-xs text-muted-foreground">{{ fmtDateShort(o.created_at) }}</TableCell>
                    <TableCell>
                      <RouterLink :to="`/orders/${o.id}`"
                        class="size-6 flex items-center justify-center rounded border border-border text-muted-foreground hover:border-amber-500 hover:text-amber-500 transition-colors">
                        <Eye class="size-3" />
                      </RouterLink>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <!-- Searches -->
          <TabsContent value="searches" class="m-0">
            <div class="max-h-96 overflow-y-auto divide-y">
              <div v-if="!report.recent_searches.length" class="text-center py-8 text-sm text-muted-foreground">Aucune recherche</div>
              <div v-for="s in report.recent_searches" :key="s.timestamp"
                class="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted/30">
                <span class="flex-1 font-medium">"{{ s.query }}"</span>
                <span :class="['font-mono text-xs', s.results_count === 0 ? 'text-red-500' : 'text-muted-foreground']">
                  {{ s.results_count }} resultats
                </span>
                <span class="font-mono text-xs text-muted-foreground">{{ fmtDateShort(s.timestamp) }}</span>
              </div>
            </div>
            <div v-if="report.behavioral_patterns.top_search_queries.length" class="px-4 py-4 border-t space-y-3">
              <p class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold">Top requetes</p>
              <div v-for="q in report.behavioral_patterns.top_search_queries" :key="q.query" class="flex items-center gap-2 text-xs">
                <span class="font-medium min-w-28 truncate">"{{ q.query }}"</span>
                <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div class="h-full bg-violet-500 rounded-full" :style="{ width: `${(q.count / report.behavioral_patterns.top_search_queries[0].count) * 100}%` }"></div>
                </div>
                <span class="font-mono text-muted-foreground min-w-8 text-right">{{ q.count }}x</span>
              </div>
            </div>
          </TabsContent>

          <!-- Alerts -->
          <TabsContent value="alerts" class="m-0">
            <div class="max-h-96 overflow-y-auto p-4 space-y-2">
              <div v-if="!report.active_alerts.length" class="text-center py-8 text-sm text-muted-foreground">Aucune alerte active</div>
              <div v-for="a in report.active_alerts" :key="a.alert_type"
                :class="['flex items-start gap-3 p-3 rounded-lg border', a.severity === 'critical' ? 'border-red-500/30 bg-red-500/5' : a.severity === 'warning' ? 'border-amber-500/30 bg-amber-500/5' : 'border-border bg-muted/30']">
                <div :class="['size-2 rounded-full mt-1.5 shrink-0', a.severity === 'critical' ? 'bg-red-500' : a.severity === 'warning' ? 'bg-amber-500' : 'bg-blue-500']"></div>
                <div class="flex-1">
                  <p class="text-sm font-semibold capitalize">{{ a.alert_type.replace(/_/g, ' ') }}</p>
                  <p class="text-xs text-muted-foreground mt-0.5">{{ a.message }}</p>
                </div>
                <Badge :variant="a.severity === 'critical' ? 'destructive' : 'outline'" class="text-[10px] shrink-0 capitalize">{{ a.severity }}</Badge>
              </div>
            </div>
          </TabsContent>

          <!-- IPs -->
          <TabsContent value="ips" class="m-0 p-4">
            <div v-if="report.behavioral_patterns.known_ips.length" class="flex flex-wrap gap-2">
              <code v-for="ip in report.behavioral_patterns.known_ips" :key="ip"
                class="font-mono text-xs bg-muted border border-border rounded-lg px-2.5 py-1.5 text-muted-foreground">
                {{ ip }}
              </code>
            </div>
            <p v-else class="text-sm text-muted-foreground text-center py-8">Aucune IP connue</p>
          </TabsContent>
        </Tabs>
      </Card>
    </template>

    <!-- Empty -->
    <div v-else class="flex flex-col items-center gap-3 py-20 text-muted-foreground">
      <AlertCircle class="size-10 opacity-40" />
      <p class="text-sm">Profil introuvable</p>
      <RouterLink to="/analytics/users" class="text-sm text-amber-500 hover:text-amber-400 transition-colors">Retour</RouterLink>
    </div>
  </div>
</template>
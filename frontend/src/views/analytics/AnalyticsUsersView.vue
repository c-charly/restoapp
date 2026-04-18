<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { RefreshCw, X, Star, AlertTriangle, Clock, TrendingUp, Eye } from 'lucide-vue-next'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'

const store = useAnalyticsStore()
const users = computed(() => store.usersList?.users ?? [])

const filters = reactive({
  role: 'tous', loyalty_tier: 'tous', min_engagement: undefined as number | undefined,
  churn_risk: false, order_by: '-analytics_profile__engagement_score'
})

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
function fmtXAF(v: number) { return new Intl.NumberFormat('fr-FR').format(Math.round(v)) + ' XAF' }
function relTime(v: string) { try { return formatDistanceToNow(new Date(v), { locale: fr, addSuffix: true }) } catch { return v } }

function tierCount(t: string) { return users.value.filter(u => u.loyalty_tier === t).length }
const churnCount    = computed(() => users.value.filter(u => u.churn_risk_score >= 50).length)
const dormantCount  = computed(() => users.value.filter(u => {
  if (!u.last_seen_at) return true
  return (Date.now() - new Date(u.last_seen_at).getTime()) > 30 * 24 * 3600 * 1000
}).length)
const avgEngagement = computed(() => {
  if (!users.value.length) return 0
  return users.value.reduce((s, u) => s + u.engagement_score, 0) / users.value.length
})

async function load() {
  const params: Record<string, any> = { order_by: filters.order_by }
  if (filters.role && filters.role !== 'tous') params.role = filters.role
  if (filters.loyalty_tier && filters.loyalty_tier !== 'tous') params.loyalty_tier = filters.loyalty_tier
  if (filters.min_engagement !== undefined && filters.min_engagement > 0) params.min_engagement = filters.min_engagement
  if (filters.churn_risk) params.churn_risk = true
  await store.fetchUsers(params)
}

function resetFilters() {
  filters.role = 'tous'; filters.loyalty_tier = 'tous'; filters.min_engagement = undefined
  filters.churn_risk = false; filters.order_by = '-analytics_profile__engagement_score'
  load()
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Utilisateurs Analytics</h1>
        <p class="text-sm text-muted-foreground font-mono mt-0.5">Scores d'engagement · Fidelite · Risque de depart</p>
      </div>
      <Button variant="outline" size="sm" @click="load" :disabled="store.loadingUsers">
        <RefreshCw class="size-3.5" :class="{ 'animate-spin': store.loadingUsers }" />Actualiser
      </Button>
    </div>

    <!-- Filters -->
    <Card>
      <CardContent class="p-4 flex items-end gap-4 flex-wrap">
        <div class="space-y-1.5">
          <Label class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Role</Label>
          <Select v-model="filters.role" @update:model-value="load">
            <SelectTrigger class="h-8 w-32 text-xs"><SelectValue placeholder="Tous" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="tous">Tous</SelectItem>
              <SelectItem value="client">Client</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Fidelite</Label>
          <Select v-model="filters.loyalty_tier" @update:model-value="load">
            <SelectTrigger class="h-8 w-32 text-xs"><SelectValue placeholder="Tous" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="tous">Tous</SelectItem>
              <SelectItem value="new">Nouveau</SelectItem>
              <SelectItem value="bronze">Bronze</SelectItem>
              <SelectItem value="silver">Argent</SelectItem>
              <SelectItem value="gold">Or</SelectItem>
              <SelectItem value="platinum">Platine</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Engagement min.</Label>
          <Input v-model.number="filters.min_engagement" type="number" min="0" max="100" placeholder="0" class="h-8 w-24 text-xs" @change="load" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Churn risk ≥50%</Label>
          <div class="flex items-center gap-2 h-8">
            <Switch v-model:checked="filters.churn_risk" @update:checked="load" />
          </div>
        </div>
        <div class="space-y-1.5">
          <Label class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Trier par</Label>
          <Select v-model="filters.order_by" @update:model-value="load">
            <SelectTrigger class="h-8 w-44 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="-analytics_profile__engagement_score">Engagement (desc)</SelectItem>
              <SelectItem value="analytics_profile__engagement_score">Engagement (asc)</SelectItem>
              <SelectItem value="-analytics_profile__churn_risk_score">Churn risk (desc)</SelectItem>
              <SelectItem value="-analytics_profile__total_spent_xaf">Depenses (desc)</SelectItem>
              <SelectItem value="-analytics_profile__last_seen_at">Recence (desc)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" size="sm" class="h-8 text-muted-foreground hover:text-destructive hover:border-destructive" @click="resetFilters">
          <X class="size-3.5" />Reinitialiser
        </Button>
      </CardContent>
    </Card>

    <!-- Summary chips -->
    <div v-if="users.length" class="flex flex-wrap gap-2">
      <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-amber-500/30 text-amber-500 bg-amber-500/5">
        <Star class="size-3" />{{ tierCount('platinum') + tierCount('gold') }} premium
      </div>
      <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-red-500/30 text-red-500 bg-red-500/5">
        <AlertTriangle class="size-3" />{{ churnCount }} a risque
      </div>
      <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-blue-500/30 text-blue-400 bg-blue-500/5">
        <Clock class="size-3" />{{ dormantCount }} dormants
      </div>
      <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 border-emerald-500/30 text-emerald-500 bg-emerald-500/5">
        <TrendingUp class="size-3" />Engagement moy. : {{ avgEngagement.toFixed(1) }}
      </div>
      <div class="flex items-center gap-1.5 text-xs border rounded-lg px-3 py-1.5 text-muted-foreground">
        Total : <strong class="ml-1 text-foreground">{{ store.usersList?.count ?? 0 }}</strong>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loadingUsers" class="space-y-2">
      <Skeleton v-for="i in 10" :key="i" class="h-14 w-full rounded-lg" />
    </div>

    <!-- Table -->
    <Card v-else>
      <div class="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Utilisateur</TableHead>
              <TableHead class="w-36">Engagement</TableHead>
              <TableHead class="w-36">Churn Risk</TableHead>
              <TableHead>Fidelite</TableHead>
              <TableHead class="text-right">Commandes</TableHead>
              <TableHead class="text-right">Depenses</TableHead>
              <TableHead class="text-right">Vu en dernier</TableHead>
              <TableHead class="text-center w-16">Device</TableHead>
              <TableHead>Ville</TableHead>
              <TableHead class="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="!users.length && !store.loadingUsers">
              <TableCell colspan="10" class="text-center py-10 text-muted-foreground">Aucun utilisateur correspondant aux filtres</TableCell>
            </TableRow>
            <TableRow v-for="u in users" :key="u.id" class="hover:bg-muted/40">
              <!-- User -->
              <TableCell>
                <div class="flex items-center gap-2.5">
                  <div class="size-8 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-500 text-xs font-bold flex items-center justify-center shrink-0">
                    {{ u.email[0].toUpperCase() }}
                  </div>
                  <div>
                    <p class="text-xs font-semibold truncate max-w-44">{{ u.email }}</p>
                    <Badge variant="outline" class="text-[10px] h-4 px-1.5 mt-0.5 capitalize">{{ u.role }}</Badge>
                  </div>
                </div>
              </TableCell>

              <!-- Engagement bar -->
              <TableCell>
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden min-w-16">
                    <div class="h-full rounded-full" style="background: linear-gradient(90deg,#3b82f6,#10b981)" :style="{ width: `${u.engagement_score}%` }"></div>
                  </div>
                  <span class="font-mono text-[11px] font-bold min-w-7 text-right">{{ u.engagement_score?.toFixed(0) }}</span>
                </div>
              </TableCell>

              <!-- Churn bar -->
              <TableCell>
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden min-w-16">
                    <div class="h-full rounded-full" style="background: linear-gradient(90deg,#f59e0b,#ef4444)" :style="{ width: `${u.churn_risk_score}%` }"></div>
                  </div>
                  <span :class="['font-mono text-[11px] font-bold min-w-7 text-right', u.churn_risk_score >= 50 ? 'text-red-500' : '']">{{ u.churn_risk_score?.toFixed(0) }}</span>
                </div>
              </TableCell>

              <!-- Loyalty -->
              <TableCell>
                <span :class="['text-[11px] px-2 py-0.5 rounded font-semibold whitespace-nowrap', tierClass(u.loyalty_tier)]">
                  {{ tierLabel(u.loyalty_tier) }}
                </span>
              </TableCell>

              <!-- Orders -->
              <TableCell class="text-right font-mono text-xs">{{ u.total_orders }}</TableCell>

              <!-- Spent -->
              <TableCell class="text-right font-mono text-xs text-amber-500 font-semibold">{{ fmtXAF(u.total_spent_xaf) }}</TableCell>

              <!-- Last seen -->
              <TableCell class="text-right font-mono text-xs text-muted-foreground">{{ u.last_seen_at ? relTime(u.last_seen_at) : '-' }}</TableCell>

              <!-- Device -->
              <TableCell class="text-center text-base">
                {{ { mobile: '📱', desktop: '🖥️', tablet: '📲', unknown: '❓' }[u.preferred_device] ?? '-' }}
              </TableCell>

              <!-- City -->
              <TableCell class="text-xs text-muted-foreground truncate max-w-24">{{ u.primary_city || '-' }}</TableCell>

              <!-- Action -->
              <TableCell>
                <RouterLink :to="`/analytics/users/${u.id}`"
                  class="size-7 flex items-center justify-center rounded border border-border text-muted-foreground hover:border-amber-500 hover:text-amber-500 transition-colors">
                  <Eye class="size-3.5" />
                </RouterLink>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </Card>
  </div>
</template>
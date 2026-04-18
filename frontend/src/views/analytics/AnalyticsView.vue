<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>Analyse Globale</h2>
        <p class="sub">PostgreSQL + MongoDB + Redis - Vue d'ensemble complète</p>
      </div>
      <button class="btn-refresh" @click="refresh" :disabled="loading">
        <RefreshCw :size="13" :class="{ 'animate-spin-slow': loading }" /> Actualiser
      </button>
    </div>

    <div class="kpi-grid">
      <StatCard label="Commandes totales"  :value="stats.total_orders"              format="number"   accent="amber">  <template #icon><ShoppingBag :size="16"/></template></StatCard>
      <StatCard label="Revenus totaux"     :value="stats.total_revenue"             format="currency" accent="emerald"><template #icon><TrendingUp  :size="16"/></template></StatCard>
      <StatCard label="Panier moyen"       :value="stats.avg_order_value.toFixed(0)" format="currency" accent="blue">  <template #icon><CreditCard  :size="16"/></template></StatCard>
      <StatCard label="Livrées"            :value="stats.delivered_orders"          format="number"   accent="emerald"><template #icon><CheckCircle :size="16"/></template></StatCard>
      <StatCard label="En attente"         :value="stats.pending_orders"            format="number"   accent="amber">  <template #icon><Clock       :size="16"/></template></StatCard>
      <StatCard label="Taux d'annulation"  :value="cancelRate"                      format="percent"  accent="red">    <template #icon><XCircle     :size="16"/></template></StatCard>
    </div>

    <!-- Revenue timeline + status donut -->
    <div class="two-col">
      <div class="chart-card flex2">
        <div class="chart-header">
          <h3>Revenus & volume dans le temps</h3>
          <div class="legend-chips">
            <span class="lchip amber">Revenus</span>
            <span class="lchip blue">Commandes</span>
          </div>
        </div>
        <Bar v-if="timelineData.labels.length" :data="timelineData" :options="barOptions" style="max-height:220px"/>
        <div v-else class="chart-empty">Aucune donnée</div>
      </div>
      <div class="chart-card">
        <div class="chart-header"><h3>Statuts</h3></div>
        <Doughnut v-if="statusData.labels.length" :data="statusData" :options="doughnutOpts" style="max-height:200px"/>
        <div v-else class="chart-empty">-</div>
      </div>
    </div>

    <!-- Ranking + Hourly -->
    <div class="two-col">
      <div class="chart-card">
        <div class="chart-header"><h3>Top restaurants - revenus</h3></div>
        <div class="ranking">
          <div v-for="(r,i) in ordersStore.revenueByRestaurant.slice(0,6)" :key="r.restaurant" class="rank-row">
            <span class="rank-n" :class="['n'+Math.min(i+1,4)]">#{{ i+1 }}</span>
            <div class="rank-mid">
              <p class="rank-name">{{ r.restaurant }}</p>
              <div class="rank-track"><div class="rank-fill" :style="`width:${Math.max(4,(r.revenue/maxRev)*100)}%`"/></div>
            </div>
            <div class="rank-right">
              <span class="rank-val">{{ formatXAF(r.revenue) }}</span>
              <span class="rank-sub">{{ r.orders }} cmd</span>
            </div>
          </div>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-header"><h3>Volume par heure</h3></div>
        <Bar v-if="hourlyData.labels.length" :data="hourlyData" :options="hourlyOpts" style="max-height:200px"/>
        <div v-else class="chart-empty">-</div>
      </div>
    </div>

    <!-- Funnel + Top clients + Roles -->
    <div class="three-col">
      <div class="chart-card">
        <div class="chart-header"><h3>Entonnoir de conversion</h3></div>
        <div class="funnel">
          <div v-for="step in funnel" :key="step.label" class="funnel-row">
            <div class="f-track"><div class="f-fill" :style="`width:${step.pct}%`" :class="step.cls"/></div>
            <div class="f-meta">
              <span class="f-label">{{ step.label }}</span>
              <span class="f-count">{{ step.count }}</span>
              <span class="f-pct">{{ step.pct }}%</span>
            </div>
          </div>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-header"><h3>Top clients</h3></div>
        <div class="top-list">
          <div v-for="(c,i) in topClients" :key="c.email" class="top-row">
            <span class="top-n">{{ i+1 }}</span>
            <div class="top-mid">
              <p class="top-email">{{ c.email }}</p>
              <div class="top-track"><div class="top-fill" :style="`width:${(c.total/topClients[0].total)*100}%`"/></div>
            </div>
            <span class="top-val">{{ formatXAF(c.total) }}</span>
          </div>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-header"><h3>Répartition rôles</h3></div>
        <PolarArea v-if="roleData.labels.length" :data="roleData" :options="polarOpts" style="max-height:200px"/>
      </div>
    </div>

    <!-- Full orders table -->
    <div class="section-card">
      <div class="section-header">
        <h3>Toutes les commandes</h3>
        <RouterLink to="/orders" class="see-all">Gestion -></RouterLink>
      </div>
      <DataTable :columns="orderCols" :rows="ordersStore.orders" :loading="loading" searchable :page-size="10">
        <template #cell-status="{ value }">
          <span :class="['badge',`badge-${value}`]">{{ SL[value]||value }}</span>
        </template>
        <template #cell-total_price="{ value }">
          <strong class="mono">{{ formatXAF(value) }}</strong>
        </template>
        <template #cell-created_at="{ value }">
          <span class="mono muted">{{ fmtDate(value) }}</span>
        </template>
        <template #actions="{ row }">
          <RouterLink :to="`/orders/${row.id}`" class="icon-btn"><Eye :size="13"/></RouterLink>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Bar, Doughnut, PolarArea } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, RadialLinearScale, Tooltip, Legend } from 'chart.js'
import { ShoppingBag, TrendingUp, CreditCard, CheckCircle, Clock, XCircle, RefreshCw, Eye } from 'lucide-vue-next'
import { useOrdersStore } from '@/stores/orders.store'
import StatCard from '@/components/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import { format, parseISO, getHours } from 'date-fns'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, RadialLinearScale, Tooltip, Legend)

const ordersStore = useOrdersStore()
const loading = computed(() => ordersStore.loading)
const stats = computed(() => ordersStore.stats)
const cancelRate = computed(() => stats.value.total_orders ? (stats.value.cancelled_orders/stats.value.total_orders)*100 : 0)
const maxRev = computed(() => ordersStore.revenueByRestaurant[0]?.revenue || 1)

const SL: Record<string,string> = { pending:'Attente', confirmed:'Confirmée', preparing:'Préparation', picked_up:'Récupérée', delivering:'Livraison', delivered:'Livrée', cancelled:'Annulée' }
const SC: Record<string,string> = { pending:'#f59e0b', confirmed:'#3b82f6', preparing:'#8b5cf6', picked_up:'#14b8a6', delivering:'#fbbf24', delivered:'#10b981', cancelled:'#ef4444' }

const timelineData = computed(() => {
  const map = new Map<string,{rev:number;cnt:number}>()
  ordersStore.orders.forEach(o => { const d=format(parseISO(o.created_at),'dd/MM'); const c=map.get(d)||{rev:0,cnt:0}; map.set(d,{rev:c.rev+parseFloat(o.total_price),cnt:c.cnt+1}) })
  const sorted = [...map.entries()].sort((a,b)=>a[0].localeCompare(b[0]))
  return { labels:sorted.map(e=>e[0]), datasets:[
    { label:'Revenus XAF', data:sorted.map(e=>e[1].rev), backgroundColor:'rgba(245,158,11,0.8)', borderColor:'#f59e0b', borderWidth:1, borderRadius:4, yAxisID:'y' },
    { label:'Commandes',   data:sorted.map(e=>e[1].cnt), backgroundColor:'rgba(59,130,246,0.6)',  borderColor:'#3b82f6', borderWidth:1, borderRadius:4, yAxisID:'y1' },
  ]}
})
const barOptions = { responsive:true, plugins:{legend:{labels:{color:'#8892a4',font:{size:10},boxWidth:10}}}, scales:{ x:{ticks:{color:'#8892a4',font:{size:10}},grid:{color:'#1e2330'}}, y:{position:'left' as const,ticks:{color:'#8892a4',font:{size:10},callback:(v:any)=>(v/1000).toFixed(0)+'k'},grid:{color:'#1e2330'}}, y1:{position:'right' as const,ticks:{color:'#8892a4',font:{size:10}},grid:{display:false}} } }

const statusData = computed(() => {
  const rows = ordersStore.ordersByStatus.filter(r=>r.count>0)
  return { labels:rows.map(r=>SL[r.status]||r.status), datasets:[{ data:rows.map(r=>r.count), backgroundColor:rows.map(r=>SC[r.status]), borderColor:'#111318', borderWidth:3 }] }
})
const doughnutOpts = { responsive:true, cutout:'60%', plugins:{ legend:{ position:'bottom' as const, labels:{color:'#8892a4',font:{size:10},padding:8,boxWidth:10} } } }

const hourlyData = computed(() => {
  const c = Array(24).fill(0); ordersStore.orders.forEach(o=>c[getHours(parseISO(o.created_at))]++)
  return { labels:Array.from({length:24},(_,i)=>`${i}h`), datasets:[{ label:'Commandes', data:c, backgroundColor:'rgba(245,158,11,0.7)', borderColor:'#f59e0b', borderWidth:1, borderRadius:3 }] }
})
const hourlyOpts = { responsive:true, plugins:{legend:{display:false}}, scales:{ x:{ticks:{color:'#8892a4',font:{size:9}},grid:{color:'#1e2330'}}, y:{ticks:{color:'#8892a4',font:{size:10}},grid:{color:'#1e2330'}} } }

const funnel = computed(() => {
  const t = stats.value.total_orders || 1
  const cnt = (s:string) => ordersStore.ordersByStatus.find(x=>x.status===s)?.count||0
  return [
    { label:'Créées',        count:t,                              pct:100,                            cls:'amber'   },
    { label:'Confirmées',    count:cnt('confirmed'),               pct:Math.round(cnt('confirmed')/t*100), cls:'blue'    },
    { label:'En préparation',count:cnt('preparing'),               pct:Math.round(cnt('preparing')/t*100), cls:'violet'  },
    { label:'En livraison',  count:cnt('delivering'),              pct:Math.round(cnt('delivering')/t*100),cls:'teal'    },
    { label:'Livrées ✅',     count:stats.value.delivered_orders,  pct:Math.round(stats.value.delivered_orders/t*100),cls:'emerald'},
    { label:'Annulées ❌',    count:stats.value.cancelled_orders,  pct:Math.round(stats.value.cancelled_orders/t*100), cls:'red'    },
  ]
})

const topClients = computed(() => {
  const map = new Map<string,number>(); ordersStore.orders.forEach(o=>map.set(o.client_email,(map.get(o.client_email)||0)+parseFloat(o.total_price)))
  return [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,5).map(([email,total])=>({email,total}))
})
const roleData = computed(() => ({ labels:['Clients','Livreurs','Admins'], datasets:[{ data:[10,3,2], backgroundColor:['rgba(59,130,246,0.7)','rgba(245,158,11,0.7)','rgba(139,92,246,0.7)'], borderColor:'#111318', borderWidth:2 }] }))
const polarOpts = { responsive:true, plugins:{legend:{position:'bottom' as const,labels:{color:'#8892a4',font:{size:10},padding:8,boxWidth:10}}}, scales:{r:{ticks:{display:false},grid:{color:'#1e2330'}}} }

const orderCols = [
  {key:'client_email',label:'Client',sortable:true},{key:'restaurant_name',label:'Restaurant',sortable:true},
  {key:'status',label:'Statut',sortable:true},{key:'total_price',label:'Montant',sortable:true},{key:'created_at',label:'Date',sortable:true}
]
function formatXAF(v:any){ return new Intl.NumberFormat('fr-FR').format(Math.round(Number(v)))+' XAF' }
function fmtDate(v:string){ return format(parseISO(v),'dd/MM HH:mm') }
async function refresh(){ await ordersStore.fetch() }
onMounted(refresh)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 24px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-header h2 { font-family: var(--font-display); font-size: 20px; font-weight: 700; margin: 0 0 4px; }
.sub { font-size: 12px; color: var(--color-text-muted); margin: 0; font-family: var(--font-mono); }
.btn-refresh { display: flex; align-items: center; gap: 7px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-secondary); font-size: 13px; padding: 8px 14px; cursor: pointer; transition: all 0.15s; }
.btn-refresh:hover { border-color: var(--color-amber); color: var(--color-amber); }
.kpi-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; }
.two-col   { display: grid; grid-template-columns: 1fr 280px; gap: 14px; }
.three-col { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; }
.chart-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 20px; }
.chart-card.flex2 { }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.chart-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.chart-empty { text-align: center; padding: 40px; color: var(--color-text-muted); font-size: 13px; }
.legend-chips { display: flex; gap: 6px; }
.lchip { font-size: 10px; font-family: var(--font-mono); padding: 2px 8px; border-radius: 4px; }
.lchip.amber { background: rgba(245,158,11,0.15); color: var(--color-amber); border: 1px solid rgba(245,158,11,0.3); }
.lchip.blue  { background: rgba(59,130,246,0.15);  color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }

.ranking { display: flex; flex-direction: column; gap: 10px; }
.rank-row { display: flex; align-items: center; gap: 10px; }
.rank-n { font-family: var(--font-mono); font-size: 11px; font-weight: 700; width: 24px; }
.n1{color:#fbbf24}.n2{color:#9ca3af}.n3{color:#b45309}.n4{color:var(--color-text-muted)}
.rank-mid { flex: 1; }
.rank-name { font-size: 12px; font-weight: 600; margin: 0 0 3px; }
.rank-track { height: 4px; background: var(--color-border); border-radius: 2px; }
.rank-fill  { height: 100%; background: var(--color-amber); border-radius: 2px; }
.rank-right { text-align: right; }
.rank-val { display: block; font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--color-amber); }
.rank-sub { font-size: 10px; color: var(--color-text-muted); font-family: var(--font-mono); }

.funnel { display: flex; flex-direction: column; gap: 10px; }
.funnel-row { display: flex; flex-direction: column; gap: 4px; }
.f-track { height: 6px; background: var(--color-border); border-radius: 3px; }
.f-fill  { height: 100%; border-radius: 3px; }
.f-fill.amber  { background: var(--color-amber); }
.f-fill.blue   { background: var(--color-blue); }
.f-fill.violet { background: var(--color-violet); }
.f-fill.teal   { background: #14b8a6; }
.f-fill.emerald{ background: var(--color-emerald); }
.f-fill.red    { background: var(--color-red); }
.f-meta { display: flex; align-items: center; gap: 6px; }
.f-label { font-size: 11px; flex: 1; }
.f-count { font-family: var(--font-mono); font-size: 11px; font-weight: 700; }
.f-pct   { font-family: var(--font-mono); font-size: 10px; color: var(--color-text-muted); width: 30px; text-align: right; }

.top-list { display: flex; flex-direction: column; gap: 10px; }
.top-row { display: flex; align-items: center; gap: 10px; }
.top-n { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-muted); width: 14px; }
.top-mid { flex: 1; }
.top-email { font-size: 11px; margin: 0 0 3px; font-family: var(--font-mono); }
.top-track { height: 3px; background: var(--color-border); border-radius: 2px; }
.top-fill  { height: 100%; background: var(--color-emerald); border-radius: 2px; }
.top-val { font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--color-emerald); }

.section-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }
.section-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.section-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.see-all { font-size: 12px; color: var(--color-amber); text-decoration: none; font-weight: 600; }
.mono { font-family: var(--font-mono); font-size: 12px; }
.muted { color: var(--color-text-muted) !important; }
.icon-btn { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 6px; border: 1px solid var(--color-border); background: none; color: var(--color-text-muted); cursor: pointer; text-decoration: none; transition: all 0.15s; }
.icon-btn:hover { border-color: var(--color-amber); color: var(--color-amber); }
</style>

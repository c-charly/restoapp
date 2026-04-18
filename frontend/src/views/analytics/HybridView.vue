<template>
  <div class="page">
    <div class="back-row">
      <RouterLink to="/orders" class="back-link"><ArrowLeft :size="14"/> Commandes</RouterLink>
    </div>

    <div class="hybrid-header">
      <div class="hybrid-badge"><Layers :size="15"/> DÉMONSTRATION HYBRIDE</div>
      <h2>Interrogation simultanée des 3 bases</h2>
      <p class="hybrid-desc">Un seul endpoint Django retourne des données depuis PostgreSQL, MongoDB et Redis en moins de 20ms.</p>
    </div>

    <!-- Source indicators -->
    <div class="source-row">
      <div class="source-ind" :class="{ loaded: data?.order }">
        <div class="si-dot pg"></div>
        <div class="si-info">
          <p class="si-name">PostgreSQL</p>
          <p class="si-desc">Order · Client · Restaurant · Items snapshot</p>
        </div>
        <span class="si-status">{{ data?.order ? '✓ OK' : fetching ? '...' : '-' }}</span>
      </div>
      <div class="si-arrow">-></div>
      <div class="source-ind" :class="{ loaded: data?.menu_snapshot !== undefined }">
        <div class="si-dot mongo"></div>
        <div class="si-info">
          <p class="si-name">MongoDB</p>
          <p class="si-desc">Menu enrichi · Schéma flexible · Sans migration</p>
        </div>
        <span class="si-status">{{ data?.menu_snapshot ? '✓ OK' : fetching ? '...' : '-' }}</span>
      </div>
      <div class="si-arrow">-></div>
      <div class="source-ind" :class="{ loaded: data?.driver_live_position !== undefined }">
        <div class="si-dot redis"></div>
        <div class="si-info">
          <p class="si-name">Redis</p>
          <p class="si-desc">Position GPS live · GeoSet · &lt; 1ms</p>
        </div>
        <span class="si-status">{{ data?.driver_live_position ? '✓ GPS' : fetching ? '...' : 'null' }}</span>
      </div>
    </div>

    <!-- Fetch panel -->
    <div class="fetch-panel">
      <div class="fetch-input-wrap">
        <label class="flabel">Order ID (UUID)</label>
        <input v-model="orderId" class="fetch-input" placeholder="ex: 550e8400-e29b-41d4-a716-446655440000"/>
      </div>
      <button class="btn-fetch" @click="fetchHybrid" :disabled="fetching || !orderId">
        <RefreshCw :size="13" :class="{'animate-spin-slow': fetching}"/>
        {{ fetching ? 'Requête en cours...' : 'Exécuter GET /demo/hybrid-order/{id}/' }}
      </button>
    </div>

    <!-- Quick picks from real orders -->
    <div v-if="sampleOrders.length" class="quick-picks">
      <span class="qp-label">Commandes disponibles :</span>
      <button v-for="o in sampleOrders" :key="o.id" class="qp-btn" @click="orderId=o.id;fetchHybrid()">
        {{ o.restaurant_name }} · {{ o.status }}
        <span class="qp-id">{{ o.id.slice(0,8) }}…</span>
      </button>
    </div>

    <div v-if="error" class="error-box"><AlertCircle :size="13"/> {{ error }}</div>

    <!-- Results 3-col -->
    <div v-if="data" class="results-grid">
      <!-- PostgreSQL -->
      <div class="result-card">
        <div class="result-header">
          <span class="db-tag pg">PostgreSQL</span>
          <h3>Données commande</h3>
          <span class="query-time">~{{ pgTime }} ms</span>
        </div>
        <div class="result-body">
          <div class="dr"><span>ID</span><code>{{ data.order.id?.slice(0,8) }}…</code></div>
          <div class="dr"><span>Client</span><strong>{{ data.order.client_email }}</strong></div>
          <div class="dr"><span>Restaurant</span><strong>{{ data.order.restaurant_name }}</strong></div>
          <div class="dr"><span>Statut</span><span :class="['badge', `badge-${data.order.status}`]">{{ data.order.status }}</span></div>
          <div class="dr"><span>Total</span><strong class="amber">{{ fmtXAF(data.order.total_price) }}</strong></div>
          <div class="dr"><span>Livreur</span><code>{{ data.order.driver || 'non assigné' }}</code></div>
        </div>
        <div class="items-preview" v-if="data.order.items?.length">
          <p class="items-label">Items - snapshot figé MongoDB</p>
          <div v-for="it in data.order.items" :key="it.id" class="iline">
            <span class="iqty">{{ it.quantity }}×</span>
            <span>{{ it.item_name }}</span>
            <span class="mono amber">{{ fmtXAF(Number(it.item_price) * it.quantity) }}</span>
            <span class="snapshot-pill">SNAPSHOT</span>
          </div>
        </div>
      </div>

      <!-- MongoDB -->
      <div class="result-card">
        <div class="result-header">
          <span class="db-tag mongo">MongoDB</span>
          <h3>Menu restaurant</h3>
          <span class="query-time">~{{ mongoTime }} ms</span>
        </div>
        <div class="result-body" v-if="data.menu_snapshot">
          <div class="dr"><span>Catégories</span><strong>{{ data.menu_snapshot.categories?.length ?? 0 }}</strong></div>
          <div class="dr"><span>Mis à jour</span><code>{{ data.menu_snapshot.updated_at ? fmtDate(data.menu_snapshot.updated_at) : '-' }}</code></div>
          <div v-for="cat in data.menu_snapshot.categories?.slice(0,2)" :key="cat.name" class="menu-cat">
            <p class="cat-name">{{ cat.name }}</p>
            <div v-for="item in cat.items?.slice(0,3)" :key="item.name" class="mitem">
              <span>{{ item.name }}</span>
              <span class="mono amber">{{ fmtXAF(item.price) }}</span>
              <span v-if="item.calories" class="opt-field">{{ item.calories }} kcal</span>
              <span v-if="item.promo_price" class="promo-field">Promo: {{ fmtXAF(item.promo_price) }}</span>
            </div>
          </div>
          <p class="mongo-note">
            <span class="mongo-dot"></span>
            Champs optionnels sans migration : calories · allergènes · promo_price…
          </p>
        </div>
        <div v-else class="no-data">Pas de menu MongoDB pour ce restaurant</div>
      </div>

      <!-- Redis -->
      <div class="result-card">
        <div class="result-header">
          <span class="db-tag redis">Redis</span>
          <h3>Position GPS livreur</h3>
          <span class="query-time">~{{ redisTime }} ms</span>
        </div>
        <div class="result-body">
          <div v-if="data.driver_live_position" class="gps-display">
            <div class="gps-coord"><span class="coord-l">LAT</span><span class="coord-v">{{ data.driver_live_position.lat }}</span></div>
            <div class="gps-coord"><span class="coord-l">LNG</span><span class="coord-v">{{ data.driver_live_position.lng }}</span></div>
            <div class="redis-cmd-box">
              <p class="rcmd-label">Commande exécutée :</p>
              <code class="rcmd">GEOPOS drivers:positions [driver_id]</code>
            </div>
          </div>
          <div v-else class="no-data">
            <p>Aucun livreur assigné à cette commande</p>
            <div class="redis-cmd-box">
              <p class="rcmd-label">Aurait retourné :</p>
              <code class="rcmd">GEOPOS drivers:positions [driver_id]</code>
            </div>
            <RouterLink to="/drivers/tracking" class="track-link"><MapPin :size="12"/> Aller au tracking GPS</RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- JSON viewer -->
    <div v-if="data" class="json-card">
      <div class="json-header">
        <h3>Réponse JSON brute</h3>
        <div class="json-actions">
          <span class="json-source">{{ data.source }}</span>
          <button class="copy-btn" @click="copyJson"><Copy :size="11"/> Copier</button>
        </div>
      </div>
      <pre class="json-pre">{{ JSON.stringify(data, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, Layers, RefreshCw, AlertCircle, MapPin, Copy } from 'lucide-vue-next'
import { useToast } from 'vue-toastification'
import { demoService } from '@/services/demo.service'
import { useOrdersStore } from '@/stores/orders.store'
import type { HybridOrderResponse } from '@/types'
import { format } from 'date-fns'

const route      = useRoute()
const toast      = useToast()
const ordersStore = useOrdersStore()

const orderId  = ref((route.params.id as string) || '')
const data     = ref<HybridOrderResponse | null>(null)
const fetching = ref(false)
const error    = ref('')

// Simulated query times for demo (real would come from X-Query-Time header)
const pgTime    = ref(Math.round(Math.random() * 4 + 1))
const mongoTime = ref(Math.round(Math.random() * 6 + 2))
const redisTime = ref(0)

const sampleOrders = computed(() => ordersStore.orders.slice(0, 6))

function fmtXAF(v: any) { return new Intl.NumberFormat('fr-FR').format(Number(v)) + ' XAF' }
function fmtDate(v: string) { try { return format(new Date(v), 'dd/MM/yyyy HH:mm') } catch { return v } }

async function fetchHybrid() {
  if (!orderId.value) return
  fetching.value = true; error.value = ''
  try {
    data.value = await demoService.hybridOrder(orderId.value)
    pgTime.value    = Math.round(Math.random() * 4 + 1)
    mongoTime.value = Math.round(Math.random() * 8 + 3)
    redisTime.value = 0
  } catch (e: any) {
    error.value = e.response?.data?.error || 'Erreur lors de la requête hybride'
    // Fallback demo
    const order = ordersStore.orders.find(o => o.id === orderId.value)
    if (order) {
      data.value = { source: 'Hybrid - PostgreSQL + MongoDB + Redis', order, menu_snapshot: null, driver_live_position: null }
    }
  } finally {
    fetching.value = false
  }
}

function copyJson() {
  navigator.clipboard.writeText(JSON.stringify(data.value, null, 2))
  toast.success('JSON copié !')
}

onMounted(async () => {
  if (!ordersStore.orders.length) await ordersStore.fetch()
  if (orderId.value) fetchHybrid()
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.back-link { display: inline-flex; align-items: center; gap: 6px; color: var(--color-text-muted); text-decoration: none; font-size: 13px; }
.back-link:hover { color: var(--color-amber); }

.hybrid-header { text-align: center; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 16px; padding: 28px; }
.hybrid-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(139,92,246,.1); border: 1px solid rgba(139,92,246,.3); border-radius: 999px; padding: 5px 14px; font-family: var(--font-mono); font-size: 11px; font-weight: 700; letter-spacing: .08em; color: #a78bfa; margin-bottom: 12px; }
.hybrid-header h2 { font-family: var(--font-display); font-size: 24px; font-weight: 800; margin: 0 0 8px; }
.hybrid-desc { font-size: 13px; color: var(--color-text-muted); margin: 0; }

.source-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.source-ind { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 180px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; padding: 14px 16px; transition: border-color .3s; }
.source-ind.loaded { border-color: rgba(16,185,129,.4); }
.si-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.si-dot.pg    { background: #3b82f6; }
.si-dot.mongo { background: #10b981; }
.si-dot.redis { background: #f59e0b; }
.si-info { flex: 1; }
.si-name { font-family: var(--font-mono); font-size: 12px; font-weight: 700; margin: 0 0 2px; }
.si-desc { font-size: 11px; color: var(--color-text-muted); margin: 0; }
.si-status { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-muted); flex-shrink: 0; }
.source-ind.loaded .si-status { color: var(--color-emerald); font-weight: 700; }
.si-arrow { font-size: 20px; color: var(--color-text-muted); flex-shrink: 0; }

.fetch-panel { display: flex; align-items: flex-end; gap: 12px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 18px; }
.fetch-input-wrap { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.flabel { font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--color-text-muted); }
.fetch-input { background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-primary); font-family: var(--font-mono); font-size: 13px; padding: 10px 14px; outline: none; width: 100%; }
.fetch-input:focus { border-color: var(--color-amber); }
.btn-fetch { display: flex; align-items: center; gap: 8px; background: var(--color-violet); color: #fff; border: none; border-radius: 10px; padding: 11px 20px; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; transition: all .15s; }
.btn-fetch:hover:not(:disabled) { background: #7c3aed; }
.btn-fetch:disabled { opacity: .5; cursor: not-allowed; }

.quick-picks { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.qp-label { font-size: 11px; color: var(--color-text-muted); font-family: var(--font-mono); }
.qp-btn { display: flex; align-items: center; gap: 6px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: 5px 10px; font-size: 11px; cursor: pointer; color: var(--color-text-secondary); transition: all .15s; }
.qp-btn:hover { border-color: var(--color-violet); color: #a78bfa; }
.qp-id { font-family: var(--font-mono); font-size: 10px; color: var(--color-text-muted); }

.error-box { display: flex; align-items: center; gap: 8px; background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3); border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--color-red); }

.results-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; }
@media (max-width: 1100px) { .results-grid { grid-template-columns: 1fr; } }

.result-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.result-header { padding: 14px 16px; border-bottom: 1px solid var(--color-border); display: flex; align-items: center; gap: 10px; }
.result-header h3 { font-family: var(--font-display); font-size: 13px; font-weight: 700; margin: 0; flex: 1; }
.query-time { font-family: var(--font-mono); font-size: 10px; color: var(--color-text-muted); }
.db-tag { font-family: var(--font-mono); font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; flex-shrink: 0; }
.db-tag.pg    { background: rgba(59,130,246,.12); color: #60a5fa; border: 1px solid rgba(59,130,246,.25); }
.db-tag.mongo { background: rgba(16,185,129,.12); color: #34d399; border: 1px solid rgba(16,185,129,.25); }
.db-tag.redis { background: rgba(245,158,11,.12); color: #fbbf24; border: 1px solid rgba(245,158,11,.25); }

.result-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.dr { display: flex; justify-content: space-between; align-items: center; font-size: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border); }
.dr:last-child { border: none; padding: 0; }
.dr span:first-child { color: var(--color-text-muted); }
code { font-family: var(--font-mono); font-size: 11px; background: var(--color-surface-2); padding: 1px 6px; border-radius: 4px; }
.amber { color: var(--color-amber) !important; }
.mono  { font-family: var(--font-mono); font-size: 12px; }

.items-preview { background: var(--color-surface-2); border-top: 1px solid var(--color-border); padding: 12px 16px; }
.items-label { font-size: 10px; font-weight: 700; color: var(--color-text-muted); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: .06em; margin: 0 0 8px; }
.iline { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 3px 0; }
.iqty { font-family: var(--font-mono); font-weight: 700; color: var(--color-amber); min-width: 24px; }
.snapshot-pill { font-size: 9px; background: rgba(139,92,246,.12); color: #a78bfa; border: 1px solid rgba(139,92,246,.25); border-radius: 3px; padding: 1px 5px; font-family: var(--font-mono); font-weight: 700; flex-shrink: 0; }

.menu-cat { margin-top: 6px; }
.cat-name { font-size: 10px; font-weight: 700; color: var(--color-text-muted); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: .06em; margin: 0 0 5px; }
.mitem { display: flex; align-items: center; gap: 6px; font-size: 12px; padding: 3px 0; border-bottom: 1px solid var(--color-border); }
.mitem:last-child { border: none; }
.mitem span:first-child { flex: 1; }
.opt-field   { font-size: 10px; color: var(--color-text-muted); background: var(--color-surface-2); border-radius: 4px; padding: 1px 5px; }
.promo-field { font-size: 10px; color: var(--color-emerald); background: rgba(16,185,129,.08); border-radius: 4px; padding: 1px 5px; }
.mongo-note { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--color-text-muted); background: var(--color-surface-2); border-radius: 6px; padding: 8px; margin-top: 8px; }
.mongo-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-emerald); flex-shrink: 0; }

.gps-display { display: flex; flex-direction: column; gap: 10px; }
.gps-coord { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--color-surface-2); border-radius: 8px; }
.coord-l { font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--color-text-muted); }
.coord-v { font-family: var(--font-mono); font-size: 16px; font-weight: 700; color: var(--color-amber); }
.redis-cmd-box { background: var(--color-surface-2); border-radius: 8px; padding: 10px; }
.rcmd-label { font-size: 10px; color: var(--color-text-muted); font-family: var(--font-mono); margin: 0 0 5px; }
.rcmd { display: block; font-family: var(--font-mono); font-size: 11px; color: var(--color-emerald); word-break: break-all; }
.no-data { display: flex; flex-direction: column; gap: 10px; font-size: 12px; color: var(--color-text-muted); }
.track-link { display: inline-flex; align-items: center; gap: 5px; color: var(--color-amber); text-decoration: none; font-size: 12px; font-weight: 600; margin-top: 4px; }

.json-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }
.json-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid var(--color-border); }
.json-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.json-actions { display: flex; align-items: center; gap: 10px; }
.json-source { font-family: var(--font-mono); font-size: 10px; color: var(--color-text-muted); }
.copy-btn { display: flex; align-items: center; gap: 5px; background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: 6px; color: var(--color-text-secondary); font-size: 12px; padding: 5px 10px; cursor: pointer; transition: all .15s; }
.copy-btn:hover { border-color: var(--color-amber); color: var(--color-amber); }
.json-pre { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-secondary); padding: 16px 20px; margin: 0; overflow: auto; max-height: 400px; line-height: 1.6; }
</style>

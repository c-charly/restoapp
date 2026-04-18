<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">Alertes Comportementales</h2>
        <p class="page-sub">Anomalies détectées automatiquement - <span class="src-tag pg">PostgreSQL BehavioralAlert</span></p>
      </div>
      <div class="header-actions">
        <button class="btn-detect" @click="triggerDetection" :disabled="detecting">
          <Radar :size="13" :class="{'animate-spin-slow': detecting}"/>
          {{ detecting ? 'Analyse en cours...' : 'Lancer la détection' }}
        </button>
        <button class="btn-refresh" @click="load" :disabled="store.loadingAlerts">
          <RefreshCw :size="13" :class="{'animate-spin-slow': store.loadingAlerts}"/>
        </button>
      </div>
    </div>

    <!-- Stats band -->
    <div class="stats-band" v-if="store.alerts">
      <div class="sband-item critical">
        <AlertOctagon :size="16"/>
        <span class="sband-val">{{ countBySeverity('critical') }}</span>
        <span class="sband-label">Critiques</span>
      </div>
      <div class="sband-item warning">
        <AlertTriangle :size="16"/>
        <span class="sband-val">{{ countBySeverity('warning') }}</span>
        <span class="sband-label">Avertissements</span>
      </div>
      <div class="sband-item info">
        <Info :size="16"/>
        <span class="sband-val">{{ countBySeverity('info') }}</span>
        <span class="sband-label">Infos</span>
      </div>
      <div class="sband-item neutral">
        <ShieldCheck :size="16"/>
        <span class="sband-val">{{ store.alerts.total_unresolved }}</span>
        <span class="sband-label">Non résolues</span>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <label class="flabel">Sévérité</label>
        <div class="filter-btns">
          <button v-for="s in severities" :key="s.v"
            :class="['fsev-btn', `sev-${s.v}`, { active: filters.severity === s.v }]"
            @click="filters.severity = filters.severity === s.v ? '' : s.v; load()">
            <component :is="s.icon" :size="11"/>
            {{ s.label }}
          </button>
        </div>
      </div>
      <div class="filter-group">
        <label class="flabel">Type d'alerte</label>
        <select v-model="filters.alert_type" class="filter-select" @change="load">
          <option value="">Tous les types</option>
          <option v-for="t in alertTypes" :key="t.v" :value="t.v">{{ t.label }}</option>
        </select>
      </div>
      <button class="btn-reset" @click="resetFilters">
        <X :size="11"/> Réinitialiser
      </button>
    </div>

    <!-- Detection result toast -->
    <div v-if="detectionResult !== null" class="detection-banner">
      <Radar :size="14"/>
      <span>Détection terminée - <strong>{{ detectionResult }}</strong> alerte{{ detectionResult !== 1 ? 's' : '' }} levée{{ detectionResult !== 1 ? 's' : '' }}</span>
      <button class="close-banner" @click="detectionResult = null"><X :size="12"/></button>
    </div>

    <!-- Loading -->
    <div v-if="store.loadingAlerts" class="loading-row">
      <div class="loader-dots"><span></span><span></span><span></span></div>
    </div>

    <!-- Alerts list -->
    <div v-else-if="alerts.length" class="alerts-list">
      <TransitionGroup name="alert-item">
        <div v-for="alert in alerts" :key="alert.id"
          :class="['alert-card', `sev-${alert.severity}`, { resolved: alert.is_resolved }]">

          <!-- Left: severity indicator -->
          <div :class="['alert-severity-bar', `bar-${alert.severity}`]"></div>

          <!-- Content -->
          <div class="alert-content">
            <div class="alert-top">
              <div class="alert-type-row">
                <span :class="['sev-pill', `pill-${alert.severity}`]">
                  <component :is="sevIcon(alert.severity)" :size="10"/>
                  {{ alert.severity.toUpperCase() }}
                </span>
                <span class="alert-type-label">{{ formatAlertType(alert.alert_type) }}</span>
              </div>
              <div class="alert-meta">
                <span class="alert-time">{{ fmtDate(alert.created_at) }}</span>
                <span v-if="alert.is_resolved" class="resolved-chip">✓ Résolue</span>
              </div>
            </div>

            <p class="alert-message">{{ alert.message }}</p>

            <div class="alert-user">
              <User :size="11"/>
              <span>{{ alert.user_email }}</span>
            </div>

            <!-- Details if any -->
            <div v-if="Object.keys(alert.details).length" class="alert-details">
              <span v-for="(v, k) in alert.details" :key="k" class="detail-chip">
                <span class="dk">{{ k }}</span> : <span class="dv">{{ v }}</span>
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="alert-actions">
            <RouterLink v-if="alert.user_email" :to="userAnalyticsLink(alert)" class="icon-btn" title="Voir utilisateur">
              <Eye :size="12"/>
            </RouterLink>
            <button v-if="!alert.is_resolved" class="btn-resolve" @click="resolve(alert.id)" :disabled="resolving === alert.id">
              <Check :size="12"/>
              {{ resolving === alert.id ? '...' : 'Résoudre' }}
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <div v-else-if="!store.loadingAlerts" class="empty-state">
      <ShieldCheck :size="48" class="emerald-icon"/>
      <p>Aucune alerte active</p>
      <p class="empty-sub">Tous les comportements semblent normaux</p>
      <button class="btn-detect" @click="triggerDetection">Lancer la détection automatique</button>
    </div>

    <!-- Alert types reference -->
    <div class="reference-card">
      <div class="ref-header">
        <BookOpen :size="13" class="amber-icon"/>
        <h3>Types d'alertes disponibles</h3>
      </div>
      <div class="ref-grid">
        <div v-for="t in alertTypes" :key="t.v" class="ref-item">
          <span class="ref-icon">{{ t.icon }}</span>
          <div>
            <p class="ref-name">{{ t.label }}</p>
            <p class="ref-desc">{{ t.desc }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  RefreshCw, Radar, AlertOctagon, AlertTriangle, Info, ShieldCheck,
  X, User, Eye, Check, BookOpen
} from 'lucide-vue-next'
import { useToast } from 'vue-toastification'
import { useAnalyticsStore } from '@/stores/analytics.store'
import { analyticsService } from '@/services/analytics.service'
import type { BehavioralAlert } from '@/types/analytics'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const store = useAnalyticsStore()
const toast = useToast()
const detecting = ref(false)
const resolving = ref<string | null>(null)
const detectionResult = ref<number | null>(null)

const filters = ref({ severity: '', alert_type: '' })

const severities = [
  { v: 'critical', label: 'Critique',       icon: AlertOctagon },
  { v: 'warning',  label: 'Avertissement',  icon: AlertTriangle },
  { v: 'info',     label: 'Info',           icon: Info },
]

const alertTypes = [
  { v: 'multiple_failed_payments',   label: 'Paiements échoués',           icon: '💳', desc: 'Plusieurs tentatives de paiement échouées' },
  { v: 'unusual_location',           label: 'Localisation inhabituelle',    icon: '📍', desc: 'Connexion depuis un emplacement inconnu' },
  { v: 'high_cart_abandonment',      label: 'Abandon panier élevé',        icon: '🛒', desc: 'Taux d\'abandon du panier anormalement élevé' },
  { v: 'inactive_user',              label: 'Utilisateur inactif',         icon: '😴', desc: 'Aucune activité depuis 30+ jours' },
  { v: 'high_cancellation_rate',     label: 'Taux d\'annulation élevé',    icon: '❌', desc: 'Nombreuses commandes annulées' },
  { v: 'suspicious_activity',        label: 'Activité suspecte',           icon: '🚨', desc: 'Trop de requêtes en peu de temps' },
  { v: 'multiple_accounts_same_ip',  label: 'Multi-comptes même IP',       icon: '👥', desc: 'Plusieurs comptes créés depuis la même adresse IP' },
  { v: 'churn_risk',                 label: 'Risque de départ',            icon: '⚠️', desc: 'Profil indiquant un risque de churn élevé' },
]

const alerts = computed(() => store.alerts?.alerts ?? [])
function countBySeverity(s: string) { return alerts.value.filter(a => a.severity === s && !a.is_resolved).length }
function formatAlertType(t: string) { return alertTypes.find(a => a.v === t)?.label ?? t.replace(/_/g, ' ') }
function fmtDate(v: string) { try { return format(new Date(v), "d MMM yyyy 'à' HH:mm", { locale: fr }) } catch { return v } }
function sevIcon(s: string) { return s === 'critical' ? AlertOctagon : s === 'warning' ? AlertTriangle : Info }

function userAnalyticsLink(alert: BehavioralAlert) {
  // In real app, look up user ID from email. For now link to users list filtered.
  return `/analytics/users`
}

async function load() {
  const params: Record<string, string> = {}
  if (filters.value.severity)   params.severity   = filters.value.severity
  if (filters.value.alert_type) params.alert_type = filters.value.alert_type
  await store.fetchAlerts(params)
}

function resetFilters() {
  filters.value = { severity: '', alert_type: '' }
  load()
}

async function resolve(id: string) {
  resolving.value = id
  try {
    await store.resolveAlert(id)
    toast.success('Alerte résolue ✓')
  } catch {
    toast.error('Erreur lors de la résolution')
  } finally {
    resolving.value = null
  }
}

async function triggerDetection() {
  detecting.value = true
  try {
    const result = await analyticsService.triggerAnomalyDetection()
    detectionResult.value = result.alerts_raised
    toast.success(`${result.alerts_raised} alerte(s) levée(s)`)
    await load()
  } catch {
    toast.error('Erreur lors de la détection')
  } finally {
    detecting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.page-title { font-family: var(--font-display); font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.page-sub   { font-size: 12px; color: var(--color-text-muted); margin: 0; font-family: var(--font-mono); }
.src-tag    { font-size: 10px; font-weight: 700; background: rgba(59,130,246,.12); color: #60a5fa; border: 1px solid rgba(59,130,246,.25); border-radius: 4px; padding: 1px 6px; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.btn-detect  { display: flex; align-items: center; gap: 7px; background: var(--color-amber); color: #000; border: none; border-radius: 8px; padding: 9px 16px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all .15s; }
.btn-detect:hover:not(:disabled) { background: var(--color-amber-bright); }
.btn-detect:disabled { opacity: .6; cursor: not-allowed; }
.btn-refresh { display: flex; align-items: center; gap: 7px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-secondary); padding: 9px 12px; cursor: pointer; transition: all .15s; }
.btn-refresh:hover:not(:disabled) { border-color: var(--color-amber); color: var(--color-amber); }
.btn-refresh:disabled { opacity: .5; }

.stats-band { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
@media (max-width: 800px) { .stats-band { grid-template-columns: repeat(2,1fr); } }
.sband-item { display: flex; align-items: center; gap: 10px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; padding: 14px 16px; }
.sband-item.critical { border-color: rgba(239,68,68,.4); }
.sband-item.warning  { border-color: rgba(245,158,11,.4); }
.sband-item.info     { border-color: rgba(59,130,246,.4); }
.sband-item.critical svg { color: var(--color-red); }
.sband-item.warning  svg { color: var(--color-amber); }
.sband-item.info     svg { color: var(--color-blue); }
.sband-item.neutral  svg { color: var(--color-emerald); }
.sband-val   { font-family: var(--font-display); font-size: 22px; font-weight: 800; }
.sband-label { font-size: 11px; color: var(--color-text-muted); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: .06em; }

.filters-bar { display: flex; align-items: flex-end; gap: 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; padding: 14px 18px; flex-wrap: wrap; }
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.flabel { font-family: var(--font-mono); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--color-text-muted); }
.filter-btns { display: flex; gap: 6px; }
.fsev-btn { display: flex; align-items: center; gap: 5px; border: 1px solid var(--color-border); border-radius: 6px; background: none; color: var(--color-text-secondary); padding: 6px 12px; font-size: 12px; cursor: pointer; transition: all .15s; }
.fsev-btn.sev-critical.active { background: rgba(239,68,68,.15); border-color: rgba(239,68,68,.5); color: var(--color-red); font-weight: 700; }
.fsev-btn.sev-warning.active  { background: rgba(245,158,11,.15); border-color: rgba(245,158,11,.5); color: var(--color-amber); font-weight: 700; }
.fsev-btn.sev-info.active     { background: rgba(59,130,246,.15); border-color: rgba(59,130,246,.5); color: #60a5fa; font-weight: 700; }
.fsev-btn:hover { border-color: var(--color-amber); color: var(--color-amber); }
.filter-select { background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: 7px; color: var(--color-text-primary); font-size: 12px; padding: 7px 10px; outline: none; min-width: 200px; }
.filter-select option { background: var(--color-surface-2); }
.btn-reset { display: flex; align-items: center; gap: 5px; background: none; border: 1px solid var(--color-border); border-radius: 7px; color: var(--color-text-muted); font-size: 12px; padding: 7px 12px; cursor: pointer; transition: all .15s; margin-top: 16px; }
.btn-reset:hover { border-color: var(--color-red); color: var(--color-red); }

.detection-banner { display: flex; align-items: center; gap: 10px; background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.3); border-radius: 8px; padding: 12px 16px; color: var(--color-amber); font-size: 13px; }
.detection-banner svg { flex-shrink: 0; }
.detection-banner strong { color: var(--color-amber-bright); }
.close-banner { background: none; border: none; color: var(--color-amber); cursor: pointer; margin-left: auto; display: flex; }

.loading-row { display: flex; justify-content: center; padding: 40px; }
.loader-dots { display: flex; gap: 6px; }
.loader-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--color-amber); animation: bounce 1.2s infinite; }
.loader-dots span:nth-child(2) { animation-delay: .2s; }
.loader-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }

.alerts-list { display: flex; flex-direction: column; gap: 10px; }
.alert-card { display: flex; align-items: stretch; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; transition: opacity .3s, transform .3s; }
.alert-card.resolved { opacity: .45; }
.alert-card.sev-critical { border-color: rgba(239,68,68,.35); }
.alert-card.sev-warning  { border-color: rgba(245,158,11,.35); }

.alert-severity-bar { width: 4px; flex-shrink: 0; }
.bar-critical { background: var(--color-red); }
.bar-warning  { background: var(--color-amber); }
.bar-info     { background: var(--color-blue); }

.alert-content { flex: 1; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
.alert-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.alert-type-row { display: flex; align-items: center; gap: 8px; }
.sev-pill { display: flex; align-items: center; gap: 4px; font-family: var(--font-mono); font-size: 9px; font-weight: 700; letter-spacing: .08em; padding: 2px 7px; border-radius: 4px; }
.pill-critical { background: rgba(239,68,68,.15); color: var(--color-red); border: 1px solid rgba(239,68,68,.3); }
.pill-warning  { background: rgba(245,158,11,.15); color: var(--color-amber); border: 1px solid rgba(245,158,11,.3); }
.pill-info     { background: rgba(59,130,246,.15); color: #60a5fa; border: 1px solid rgba(59,130,246,.3); }
.alert-type-label { font-size: 14px; font-weight: 600; }
.alert-meta { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.alert-time { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-muted); }
.resolved-chip { font-size: 11px; background: rgba(16,185,129,.1); color: var(--color-emerald); border: 1px solid rgba(16,185,129,.25); border-radius: 4px; padding: 1px 7px; font-family: var(--font-mono); }

.alert-message { font-size: 13px; color: var(--color-text-secondary); margin: 0; line-height: 1.5; }
.alert-user { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-text-muted); font-family: var(--font-mono); }
.alert-details { display: flex; flex-wrap: wrap; gap: 6px; }
.detail-chip { font-size: 11px; background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: 4px; padding: 2px 8px; }
.dk { color: var(--color-text-muted); }
.dv { color: var(--color-text-primary); font-weight: 600; }

.alert-actions { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 14px; border-left: 1px solid var(--color-border); }
.icon-btn { display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 7px; border: 1px solid var(--color-border); background: none; color: var(--color-text-muted); cursor: pointer; text-decoration: none; transition: all .15s; }
.icon-btn:hover { border-color: var(--color-amber); color: var(--color-amber); }
.btn-resolve { display: flex; align-items: center; gap: 5px; background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); border-radius: 7px; color: var(--color-emerald); font-size: 12px; font-weight: 600; padding: 7px 12px; cursor: pointer; white-space: nowrap; transition: all .15s; }
.btn-resolve:hover:not(:disabled) { background: rgba(16,185,129,.2); }
.btn-resolve:disabled { opacity: .6; cursor: not-allowed; }

/* Alert item transition */
.alert-item-enter-active, .alert-item-leave-active { transition: all .3s; }
.alert-item-enter-from, .alert-item-leave-to { opacity: 0; transform: translateX(-12px); }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px; color: var(--color-text-muted); text-align: center; }
.empty-state p { margin: 0; font-size: 14px; }
.empty-sub { font-size: 12px !important; }
.emerald-icon { color: var(--color-emerald); }

.reference-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 20px; }
.ref-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.ref-header h3 { font-family: var(--font-display); font-size: 14px; font-weight: 700; margin: 0; }
.amber-icon { color: var(--color-amber); }
.ref-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px,1fr)); gap: 10px; }
.ref-item { display: flex; align-items: flex-start; gap: 10px; background: var(--color-surface-2); border-radius: 8px; padding: 12px; }
.ref-icon { font-size: 20px; flex-shrink: 0; }
.ref-name { font-size: 13px; font-weight: 600; margin: 0 0 3px; }
.ref-desc { font-size: 11px; color: var(--color-text-muted); margin: 0; line-height: 1.4; }
</style>

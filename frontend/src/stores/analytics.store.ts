import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analyticsService } from '@/services/analytics.service'
import type {
  PlatformOverview, RealtimeStats, UserAnalyticsList,
  AlertsResponse, SegmentationResponse, MyAnalyticsProfile
} from '@/types/analytics'

export const useAnalyticsStore = defineStore('analytics', () => {
  const overview     = ref<PlatformOverview | null>(null)
  const realtime     = ref<RealtimeStats | null>(null)
  const segmentation = ref<SegmentationResponse | null>(null)
  const usersList    = ref<UserAnalyticsList | null>(null)
  const alerts       = ref<AlertsResponse | null>(null)
  const myProfile    = ref<MyAnalyticsProfile | null>(null)

  const loadingOverview     = ref(false)
  const loadingRealtime     = ref(false)
  const loadingUsers        = ref(false)
  const loadingAlerts       = ref(false)
  const loadingSegmentation = ref(false)
  const loadingMyProfile    = ref(false)

  const days = ref(30)

  const criticalAlertsCount = computed(() =>
    alerts.value?.alerts.filter(a => a.severity === 'critical' && !a.is_resolved).length ?? 0
  )
  const unresolvedAlertsCount = computed(() => alerts.value?.total_unresolved ?? 0)

  async function fetchOverview() {
    loadingOverview.value = true
    try { overview.value = await analyticsService.getPlatformOverview(days.value) }
    catch (e) { console.warn('overview unavailable', e) }
    finally { loadingOverview.value = false }
  }
  async function fetchRealtime() {
    loadingRealtime.value = true
    try { realtime.value = await analyticsService.getPlatformRealtime() }
    catch (e) { console.warn('realtime unavailable', e) }
    finally { loadingRealtime.value = false }
  }
  async function fetchSegmentation() {
    loadingSegmentation.value = true
    try { segmentation.value = await analyticsService.getUserSegmentation() }
    catch (e) { console.warn('segmentation unavailable', e) }
    finally { loadingSegmentation.value = false }
  }
  async function fetchUsers(params = {}) {
    loadingUsers.value = true
    try { usersList.value = await analyticsService.getUsersList(params) }
    catch (e) { console.warn('users unavailable', e) }
    finally { loadingUsers.value = false }
  }
  async function fetchAlerts(params = {}) {
    loadingAlerts.value = true
    try { alerts.value = await analyticsService.getAlerts(params) }
    catch (e) { console.warn('alerts unavailable', e) }
    finally { loadingAlerts.value = false }
  }
  async function fetchMyProfile() {
    loadingMyProfile.value = true
    try { myProfile.value = await analyticsService.getMyProfile() }
    catch (e) { console.warn('my profile unavailable', e) }
    finally { loadingMyProfile.value = false }
  }
  async function resolveAlert(id: string) {
    await analyticsService.resolveAlert(id)
    if (alerts.value) {
      const a = alerts.value.alerts.find(a => a.id === id)
      if (a) { a.is_resolved = true; alerts.value.total_unresolved = Math.max(0, alerts.value.total_unresolved - 1) }
    }
  }

  return {
    overview, realtime, segmentation, usersList, alerts, myProfile,
    loadingOverview, loadingRealtime, loadingUsers, loadingAlerts,
    loadingSegmentation, loadingMyProfile,
    days, criticalAlertsCount, unresolvedAlertsCount,
    fetchOverview, fetchRealtime, fetchSegmentation,
    fetchUsers, fetchAlerts, fetchMyProfile, resolveAlert,
  }
})

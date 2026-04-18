import http from './http'
import type {
  PlatformOverview, RealtimeStats, UserAnalyticsList, UserFullReport,
  FunnelAnalysis, AlertsResponse, TopPagesResponse, TopSearchesResponse,
  SegmentationResponse, MyAnalyticsProfile, SessionItem, EventItem
} from '@/types/analytics'

export const analyticsService = {
  async trackEvent(payload: {
    event_type: string
    object_type?: string
    object_id?: string
    properties?: Record<string, unknown>
  }) {
    try {
      await http.post('/analytics/track/event/', payload)
    } catch { /* silently fail */ }
  },

  async trackSearch(query: string, resultsCount: number = 0) {
    try {
      await http.post('/analytics/track/search/', { query, results_count: resultsCount })
    } catch { /* silently fail */ }
  },

  async trackInteraction(payload: {
    item_id: string
    item_name: string
    restaurant_id: string
    interaction_type: string
    item_tags?: string[]
    item_price?: number
  }) {
    try {
      await http.post('/analytics/track/interaction/', payload)
    } catch { /* silently fail */ }
  },

  // Mon profil
  async getMyProfile(): Promise<MyAnalyticsProfile> {
    const { data } = await http.get('/analytics/me/')
    return data
  },
  async getMySessions(): Promise<SessionItem[]> {
    const { data } = await http.get('/analytics/me/sessions/')
    return data
  },
  async getMyEvents(): Promise<EventItem[]> {
    const { data } = await http.get('/analytics/me/events/')
    return data
  },

  async getMyTasteProfile() {
    const { data } = await http.get('/analytics/me/taste/')
    return data
  },

  // Admin
  async getPlatformOverview(days = 30): Promise<PlatformOverview> {
    const { data } = await http.get('/analytics/platform/overview/', { params: { days } })
    return data
  },
  async getPlatformRealtime(): Promise<RealtimeStats> {
    const { data } = await http.get('/analytics/platform/realtime/')
    return data
  },
  async getTopPages(days = 30, method?: string): Promise<TopPagesResponse> {
    const { data } = await http.get('/analytics/platform/top-pages/', { params: { days, method } })
    return data
  },
  async getFunnelAnalysis(days = 30): Promise<FunnelAnalysis> {
    const { data } = await http.get('/analytics/platform/funnel/', { params: { days } })
    return data
  },
  async getTopSearches(days = 30): Promise<TopSearchesResponse> {
    const { data } = await http.get('/analytics/platform/top-searches/', { params: { days } })
    return data
  },
  async getUserSegmentation(): Promise<SegmentationResponse> {
    const { data } = await http.get('/analytics/platform/segmentation/')
    return data
  },

  async getGlobalItemInteractions() {
    const { data } = await http.get('/analytics/platform/item-interactions/')
    return data
  },

  async getUsersList(params: { role?: string; loyalty_tier?: string; min_engagement?: number; churn_risk?: boolean; order_by?: string } = {}): Promise<UserAnalyticsList> {
    const { data } = await http.get('/analytics/users/', { params })
    return data
  },

  async getUserDetail(userId: string): Promise<UserFullReport> {
    const { data } = await http.get(`/analytics/users/${userId}/`)
    return data
  },
  async getUserSessions(userId: string): Promise<SessionItem[]> {
    const { data } = await http.get(`/analytics/users/${userId}/sessions/`)
    return data
  },
  async getUserEvents(userId: string): Promise<EventItem[]> {
    const { data } = await http.get(`/analytics/users/${userId}/events/`)
    return data
  },

  async getAlerts(params: { severity?: string; alert_type?: string } = {}): Promise<AlertsResponse> {
    const { data } = await http.get('/analytics/alerts/', { params })
    return data
  },
  async resolveAlert(alertId: string): Promise<{ resolved: boolean }> {
    const { data } = await http.patch(`/analytics/alerts/${alertId}/resolve/`)
    return data
  },
  async triggerAnomalyDetection(): Promise<{ alerts_raised: number }> {
    const { data } = await http.post('/analytics/alerts/')
    return data
  },
}

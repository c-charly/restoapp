
export interface PlatformOverview {
  period_days: number
  sessions: {
    total: number
    unique_users: number
    avg_duration_seconds: number
    bounce_rate_pct: number
  }
  page_views: {
    total: number
    avg_ms: number
    errors_4xx: number
    errors_5xx: number
    top_pages: TopPage[]
  }
  orders: {
    total: number
    revenue_xaf: number
    avg_value_xaf: number
    cancelled: number
    delivered: number
  }
  users: { new: number; total: number }
  conversion: {
    rate_pct: number
    funnels_total: number
    funnels_converted: number
  }
  top_events: TopEvent[]
  device_breakdown: DeviceBreakdown[]
  hourly_activity_24h: HourlyActivity[]
}

export interface TopPage {
  path: string
  method: string
  hits: number
  unique_users: number
  avg_ms: number
  avg_response_ms: number
  errors: number
  last_accessed?: string
}

export interface TopEvent {
  event_type: string
  cnt: number
}

export interface DeviceBreakdown {
  device_type: string
  cnt: number
}

export interface HourlyActivity {
  hour: string
  hits: number
}

// Realtime
export interface RealtimeStats {
  source: string
  active_drivers: number
  active_orders_in_cache: number
  event_counters_24h: Record<string, { total_24h: number; by_hour: Record<string, number> }>
}

// User Analytics List
export interface UserAnalyticsItem {
  id: string
  email: string
  role: string
  created_at: string
  loyalty_tier: string
  engagement_score: number
  churn_risk_score: number
  total_orders: number
  total_spent_xaf: number
  last_seen_at: string | null
  preferred_device: string
  primary_city: string
}

export interface UserAnalyticsList {
  count: number
  users: UserAnalyticsItem[]
}

// User Detail / Full Report
export interface UserFullReport {
  user: { id: string; email: string; role: string; created_at: string }
  profile_summary: ProfileSummary
  sessions: SessionItem[]
  top_visited_pages: TopPage[]
  recent_events: EventItem[]
  orders_timeline: OrderTimelineItem[]
  funnel_history: FunnelItem[]
  recent_searches: SearchItem[]
  reviews: ReviewItem[]
  active_alerts: AlertItem[]
  redis_live: { driver_available: boolean; active_order_count: number }
  behavioral_patterns: BehavioralPatterns
}

export interface ProfileSummary {
  loyalty_tier: string
  engagement_score: number
  churn_risk_score: number
  total_sessions: number
  total_orders: number
  total_spent_xaf: number
  avg_order_value_xaf: number
  first_seen_at: string | null
  last_seen_at: string | null
  preferred_device: string
  preferred_os: string
  primary_city: string
  most_active_hour: number | null
  most_active_day: number | null
  favorite_restaurant: string
  cart_abandonments: number
  total_reviews: number
  avg_rating_given: number
}

export interface SessionItem {
  id: string
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  ip_address: string | null
  country: string
  city: string
  device_type: string
  os: string
  browser: string
  page_views_count: number
  events_count: number
  orders_count: number
  is_bounce: boolean
  referrer: string
}

export interface EventItem {
  event_type: string
  object_type: string
  object_id: string
  properties: Record<string, unknown>
  timestamp: string
}

export interface OrderTimelineItem {
  id: string
  status: string
  total_price: string
  created_at: string
  restaurant__name: string
  delivery_address: string
}

export interface FunnelItem {
  restaurant_name: string
  last_step_name: string
  converted: boolean
  order_total: number | null
  time_to_convert_seconds: number | null
  abandoned_at_step: number | null
  started_at: string
}

export interface SearchItem {
  query: string
  results_count: number
  timestamp: string
  filters_applied: Record<string, unknown>
}

export interface ReviewItem {
  order_id: string
  restaurant_id: string
  rating: number
  comment: string
  created_at: string
}

export interface AlertItem {
  id?: string
  alert_type: string
  severity: string
  message: string
  created_at?: string
}

export interface BehavioralPatterns {
  orders_by_hour: Record<string, number>
  orders_by_day: Record<string, number>
  top_search_queries: Array<{ query: string; count: number }>
  top_visited_paths: Array<{ path: string; count: number }>
  known_ips: string[]
}

// Funnel Analysis
export interface FunnelAnalysis {
  period_days: number
  total_funnels: number
  conversion_rate_pct: number
  avg_time_to_convert_seconds: number
  funnel_steps: FunnelStep[]
  abandon_by_step: Record<string, number>
  top_abandoned_restaurants: Array<{ restaurant_name: string; cnt: number }>
}

export interface FunnelStep {
  step: string
  users_reached: number
  drop_off_pct: number
}

// Alerts
export interface BehavioralAlert {
  id: string
  user_email: string
  alert_type: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  details: Record<string, unknown>
  is_resolved: boolean
  resolved_at: string | null
  created_at: string
}

export interface AlertsResponse {
  total_unresolved: number
  alerts: BehavioralAlert[]
}

// Top Pages
export interface TopPagesResponse {
  period_days: number
  top_pages: TopPage[]
  frequent_errors: Array<{ path: string; http_status: number; cnt: number }>
  slowest_endpoints: Array<{ path: string; avg_ms: number }>
}

// Searches
export interface TopSearchesResponse {
  period_days: number
  top_searches: Array<{ query_normalized: string; cnt: number; avg_results: number; zero_results: number }>
  searches_with_no_results: Array<{ query_normalized: string; cnt: number }>
}

// Segmentation
export interface SegmentationResponse {
  total_profiles: number
  by_loyalty_tier: Record<string, number>
  by_device: Record<string, number>
  by_city: Array<{ primary_city: string; cnt: number }>
  engagement_distribution: Record<string, number>
  churn_risk: { count: number; pct: number }
  dormant_users_30d: number
  top_spenders: Array<{ user__email: string; total_spent_xaf: number; total_orders: number; loyalty_tier: string }>
}

// My Analytics
export interface MyAnalyticsProfile {
  user_email: string
  total_sessions: number
  total_page_views: number
  total_events: number
  avg_session_duration_seconds: number
  avg_pages_per_session: number
  first_seen_at: string | null
  last_seen_at: string | null
  last_device: string
  total_orders: number
  total_spent_xaf: number
  avg_order_value_xaf: number
  orders_cancelled: number
  orders_delivered: number
  cart_abandonments: number
  favorite_restaurant_name: string
  favorite_restaurant_orders: number
  most_active_hour: number | null
  most_active_day: number | null
  preferred_device: string
  preferred_os: string
  primary_city: string
  primary_country: string
  engagement_score: number
  churn_risk_score: number
  loyalty_tier: string
  total_reviews: number
  avg_rating_given: number
  orders_by_hour: Record<string, number>
  orders_by_day: Record<string, number>
  top_search_queries: Array<{ query: string; count: number }>
  top_visited_paths: Array<{ path: string; count: number }>
  updated_at: string
}

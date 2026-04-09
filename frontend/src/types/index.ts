export interface User {
  id: string
  email: string
  phone: string
  first_name: string
  last_name: string
  role: 'client' | 'admin'
  created_at: string
}

export interface Wallet {
  id: string
  balance: string
  updated_at: string
}

export interface MeResponse {
  user: User
  wallet: Wallet
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface Restaurant {
  id: string
  name: string
  address: string
  latitude: string | null
  longitude: string | null
  is_active: boolean
  created_at: string
}

export interface MenuItemOption {
  label: string
  price: number
}

export interface MenuItem {
  id?: string
  name: string
  price: number
  description?: string
  photos?: string[]
  options?: MenuItemOption[]
  tags?: string[]
  available?: boolean
  calories?: number
  allergenes?: string[]
  promo_price?: number
  promo_ends_at?: string
}

export interface MenuCategory {
  name: string
  items: MenuItem[]
}

export interface Menu {
  restaurant_id: string
  updated_at?: string
  categories: MenuCategory[]
  _cache?: string
  _id?: string
}

export interface OrderItem {
  id: string
  item_name: string
  item_price: string
  quantity: number
  snapshot_data: Record<string, unknown>
}

export type OrderStatus =
  | 'pending'
  | 'confirmed'
  | 'preparing'
  | 'picked_up'
  | 'delivering'
  | 'delivered'
  | 'cancelled'

export interface Order {
  id: string
  client_email: string
  restaurant_name: string
  driver: string | null
  status: OrderStatus
  total_price: string
  delivery_address: string
  items: OrderItem[]
  created_at: string
}

export interface Driver {
  id: string
  email: string
  vehicle_type: 'moto' | 'velo' | 'voiture' | 'pied'
  is_available: boolean
  created_at: string
}

export interface NearbyDriver {
  driver_id: string
  distance_km: number
  lat: number
  lng: number
}

export interface NearbyDriversResponse {
  source: string
  search: { lat: number; lng: number; radius_km: number }
  drivers_found: number
  drivers: NearbyDriver[]
}

export interface HybridOrderResponse {
  source: string
  order: Order
  menu_snapshot: Menu | null
  driver_live_position: { lat: number; lng: number } | null
}

export interface ActivityLog {
  _id: string
  user_id: string
  action: string
  metadata: Record<string, unknown>
  timestamp: string
}

export interface Review {
  _id: string
  order_id: string
  client_id: string
  restaurant_id: string
  rating: number
  comment: string
  photos: string[]
  created_at: string
}

export interface WalletTransaction {
  id: string
  amount: string
  type: 'debit' | 'credit'
  order: string | null
  description: string
  created_at: string
}

// Analytics computed types
export interface DashboardStats {
  total_orders: number
  total_revenue: number
  total_users: number
  total_restaurants: number
  pending_orders: number
  delivered_orders: number
  cancelled_orders: number
  avg_order_value: number
}

export interface OrdersByStatus {
  status: OrderStatus
  count: number
}

export interface RevenueByRestaurant {
  restaurant: string
  revenue: number
  orders: number
}

export interface Pagination<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

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
  avg_rating?: number
  total_ratings?: number
  ratings_distribution?: Record<string, number>
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
  avg_rating?: number
  total_ratings?: number
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

export interface Address {
  id: string
  label: string
  latitude: string
  longitude: string
  is_default: boolean
}
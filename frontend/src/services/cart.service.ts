import http from './http'

export interface CartSession {
  id: string
  restaurant_name: string
  status: string
  subtotal: string
  items_count: number
  items: CartItem[]
  created_at: string
  updated_at: string
}

export interface CartItem {
  id: string
  item_id: string
  item_name: string
  base_price: string
  quantity: number
  selected_options: { label: string; price: string }[]
  options_extra_price: string
  line_total: string
  special_instructions: string
  item_snapshot: Record<string, unknown>
  added_at: string
}

export interface AddToCartPayload {
  restaurant_id: string
  item_id: string
  quantity: number
  selected_options?: { label: string; price: number }[]
  special_instructions?: string
}

export interface ItemRating {
  id: string
  user_email: string
  item_id: string
  item_name: string
  rating: number
  comment: string
  photos: string[]
  order_id: string
  created_at: string
}

export const cartService = {
  async get(): Promise<CartSession> {
    const { data } = await http.get<{cart : CartSession}>('/cart/')
    return data.cart
  },

  async add(payload: AddToCartPayload): Promise<CartSession> {
    const { data } = await http.post<{cart : CartSession}>('/cart/add/', payload)
    return data.cart
  },

  async updateItem(itemId: string, quantity: number): Promise<CartSession> {
    const { data } = await http.patch<{cart : CartSession}>(`/cart/item/${itemId}/`, { quantity })
    return data.cart
  },

  async removeItem(itemId: string): Promise<CartSession> {
    const { data } = await http.delete<{cart : CartSession}>(`/cart/item/${itemId}/`)
    return data.cart
  },

  async abandon(): Promise<void> {
    await http.delete('/cart/abandon/')
  },

  async checkout(deliveryAddress?: string): Promise<{ order_id: string }> {
    const { data } = await http.post('/cart/checkout/', { delivery_address: deliveryAddress || '' })
    return data
  },

  async rateItem(payload: {
    item_id: string
    item_name: string
    rating: number
    comment?: string
    order_id: string
  }): Promise<ItemRating> {
    const { data } = await http.post<ItemRating>('/cart/rate/', payload)
    return data
  },

  async getRestaurantRating(restaurantId: string) {
    const { data } = await http.get(`/cart/restaurant/${restaurantId}/rating/`)
    return data
  },

  async getItemRatings(itemId: string): Promise<ItemRating[]> {
    const { data } = await http.get<ItemRating[]>(`/cart/item/${itemId}/ratings/`)
    return data
  }
}

import http from './http'

export interface Order {
  id: string
  client_email: string
  restaurant_name: string
  status: string
  total_price: string
  delivery_address: string
  items: OrderItem[]
  created_at: string
  updated_at: string
}

export interface OrderItem {
  id: string
  item_name: string
  item_price: string
  quantity: number
  snapshot_data: Record<string, unknown>
}

export const ordersService = {
  async list(params?: { status?: string; restaurant_id?: string }): Promise<Order[]> {
    const { data } = await http.get<Order[]>('/orders/list/', { params })
    return data
  },

  async get(id: string): Promise<Order> {
    const { data } = await http.get<Order>(`/orders/${id}/`)
    return data
  },

  async updateStatus(id: string, status: string): Promise<Order> {
    const { data } = await http.patch<Order>(`/orders/${id}/status/`, { status })
    return data
  },

  async cancel(id: string): Promise<Order> {
    const { data } = await http.post<Order>(`/orders/${id}/cancel/`)
    return data
  }
}

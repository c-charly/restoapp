import http from './http'
import type { Restaurant, Menu } from '@/types'

export const restaurantService = {
  async list(): Promise<Restaurant[]> {
    const { data } = await http.get<Restaurant[]>('/restaurants/')
    return data
  },

  async get(id: string): Promise<Restaurant> {
    const { data } = await http.get<Restaurant>(`/restaurants/${id}/`)
    return data
  },

  async create(resto: Restaurant): Promise<Restaurant> {
    const { data } = await http.post<Restaurant>(`/restaurants/`, resto)
    return data
  },

  async update(resto: Restaurant): Promise<Restaurant> {
    const { data } = await http.patch<Restaurant>(`/restaurants/${resto.id}/`)
    return data
  },

  async getMenu(id: string): Promise<Menu> {
    const { data } = await http.get<Menu>(`/restaurants/${id}/menu/`)
    return data
  },

  async updateMenu(id: string, menu: Partial<Menu>): Promise<{ status: string }> {
    const { data } = await http.put(`/restaurants/${id}/menu/`, menu)
    return data
  }
}

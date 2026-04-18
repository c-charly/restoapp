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

  async create(payload: Omit<Restaurant, 'id' | 'created_at'>): Promise<Restaurant> {
    const { data } = await http.post<Restaurant>('/restaurants/', payload)
    return data
  },

  async update(resto: Partial<Restaurant> & { id: string }): Promise<Restaurant> {
    const { data } = await http.patch<Restaurant>(`/restaurants/${resto.id}/`, resto)
    return data
  },

  async delete(id: string): Promise<void> {
    await http.delete(`/restaurants/${id}/`)
  },

  async getMenu(id: string): Promise<Menu> {
    const { data } = await http.get<Menu>(`/restaurants/${id}/menu/`)
    return data
  },

  async updateMenu(id: string, menu: Partial<Menu>): Promise<{ status: string }> {
    const { data } = await http.put(`/restaurants/${id}/menu/`, menu)
    return data
  },

  async uploadItemImages(restaurantId: string, itemId: string, files: File[]): Promise<string[]> {
    const formData = new FormData()
    files.forEach(file => formData.append('images', file))
    console.log('formData:', formData.getAll('images'))
    const { data } = await http.post<{ photos: string[] }>(
      `/restaurants/${restaurantId}/menu/items/${itemId}/images/`,
      formData
    )
    return data.photos
  }
}
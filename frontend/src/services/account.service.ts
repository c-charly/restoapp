import http from './http'

export interface WalletTransaction {
  id: string
  amount: string
  type: 'debit' | 'credit'
  order: string | null
  description: string
  created_at: string
}

export const walletService = {
  async get() {
    const { data } = await http.get('/auth/wallet/')
    return data
  },

  async topup(amount: number, description?: string) {
    const { data } = await http.post('/auth/wallet/topup/', {
      amount,
      description: description || 'Recharge manuelle'
    })
    return data
  },

  async transactions(): Promise<WalletTransaction[]> {
    const { data } = await http.get<WalletTransaction[]>('/auth/wallet/transactions/')
    return data
  }
}

export const addressService = {
  async list() {
    const { data } = await http.get('/auth/addresses/')
    return data
  },

  async create(payload: { label: string; latitude: number; longitude: number }) {
    const { data } = await http.post('/auth/addresses/', payload)
    return data
  },

  async update(id: string, payload: { label: string; latitude: number; longitude: number }) {
    const { data } = await http.patch(`/auth/addresses/${id}/`, payload)
    return data
  },

  async delete(id: string) {
    await http.delete(`/auth/addresses/${id}/`)
  },

  async setDefault(id: string) {
    const { data } = await http.patch(`/auth/addresses/${id}/default/`)
    return data
  }
}

export const adminUserService = {
  async list() {
    const { data } = await http.get('/auth/users/')
    return data
  },

  async get(id: string) {
    const { data } = await http.get(`/auth/users/${id}/`)
    return data
  },

  async update(id: string, payload: Record<string, unknown>) {
    const { data } = await http.patch(`/auth/users/${id}/`, payload)
    return data
  }
}

import http from './http'
import type { AuthTokens, MeResponse, User } from '@/types'

export const authService = {
  async login(email: string, password: string): Promise<AuthTokens> {
    const { data } = await http.post<AuthTokens>('/auth/token/', { email, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    return data
  },

  async register(payload: {
    email: string
    password: string
    first_name: string
    last_name: string
    phone: string
    role: string
  }): Promise<User> {
    const { data } = await http.post<User>('/auth/register/', payload)
    return data
  },

  async me(): Promise<MeResponse> {
    const { data } = await http.get<MeResponse>('/auth/me/')
    return data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token')
  }
}

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '@/services/auth.service'
import type { User, Wallet } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const wallet = ref<Wallet | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => authService.isAuthenticated() && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(email: string, password: string) {
    loading.value = true
    try {
      await authService.login(email, password)
      await fetchMe()
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    const data = await authService.me()
    user.value = data.user
    wallet.value = data.wallet
  }

  function logout() {
    authService.logout()
    user.value = null
    wallet.value = null
  }

  async function init() {
    if (authService.isAuthenticated() && !user.value) {
      try { await fetchMe() } catch { logout() }
    }
  }

  return { user, wallet, loading, isAuthenticated, isAdmin, login, logout, init, fetchMe }
})
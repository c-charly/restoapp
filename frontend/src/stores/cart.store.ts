import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cartService, type CartSession } from '@/services/cart.service'

export const useCartStore = defineStore('cart', () => {
  const cart = ref<CartSession | null>(null)
  const loading = ref(false)
  const checkoutLoading = ref(false)

  const itemsCount = computed(() => cart.value?.items_count ?? 0)
  const subtotal = computed(() => cart.value?.subtotal ?? '0.00')
  const restaurantName = computed(() => cart.value?.restaurant_name ?? '')

  async function fetchCart() {
    try {
      loading.value = true
      cart.value = await cartService.get()
    } catch {
      cart.value = null
    } finally {
      loading.value = false
    }
  }

  async function addItem(payload: Parameters<typeof cartService.add>[0]) {
    cart.value = await cartService.add(payload)
  }

  async function updateItem(itemId: string, quantity: number) {
    cart.value = await cartService.updateItem(itemId, quantity)
    console.log(cart.value)
  }

  async function removeItem(itemId: string) {
    cart.value = await cartService.removeItem(itemId)
  }

  async function abandon() {
    await cartService.abandon()
    cart.value = null
  }

  async function checkout(deliveryAddress?: string) {
    checkoutLoading.value = true
    try {
      const result = await cartService.checkout(deliveryAddress)
      cart.value = null
      return result
    } finally {
      checkoutLoading.value = false
    }
  }

  return {
    cart, loading, checkoutLoading,
    itemsCount, subtotal, restaurantName,
    fetchCart, addItem, updateItem, removeItem, abandon, checkout
  }
})

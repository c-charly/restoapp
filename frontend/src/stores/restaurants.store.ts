import { defineStore } from 'pinia'
import { ref } from 'vue'
import { restaurantService } from '@/services/restaurant.service'
import type { Restaurant } from '@/types'

export const useRestaurantsStore = defineStore('restaurants', () => {
  const restaurants = ref<Restaurant[]>([])
  const loading = ref(false)
  const ratingLabel = [
    { icon: "😠", label: "Tres Movais", value: "1" },
    { icon: "🙁", label: "Movais", value: "2" },
    { icon: "😐", label: "Neutre", value: "3" },
    { icon: "🙂", label: "Heureux", value: "4" },
    { icon: "😀", label: "Super Heureux", value: "5" },
  ];

  async function fetch() {
    loading.value = true
    try { restaurants.value = await restaurantService.list() }
    finally { loading.value = false }
  }

  return { restaurants, loading, ratingLabel, fetch }
})

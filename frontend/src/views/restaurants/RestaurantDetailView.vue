<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { restaurantService } from '@/services/restaurant.service'
import { cartService } from '@/services/cart.service'
import type { Restaurant } from '@/types'
import { useAuthStore } from '@/stores/auth.store'
import {
  ArrowLeft, MapPin, Star, Utensils, ChevronRight,
  BarChart2, Clock, Users
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const restaurant = ref<any>(null)
const rating = ref<any>(null)
const loading = ref(true)
const id = route.params.id as string

async function load() {
  try {
    loading.value = true
    const [r, rt] = await Promise.all([
      restaurantService.get(id),
      cartService.getRestaurantRating(id).catch(() => null)
    ])
    restaurant.value = r
    rating.value = rt
  } finally {
    loading.value = false
  }
}

function ratingBarWidth(count: number, total: number) {
  if (!total) return 0
  return Math.round((count / total) * 100)
}

onMounted(load)
</script>

<template>
  <div class="space-y-6 max-w-3xl">
    <Button variant="ghost" size="sm" class="-ml-2" @click="router.back()">
      <ArrowLeft class="size-4" />Retour
    </Button>

    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-8 w-64" />
      <Skeleton class="h-4 w-48" />
      <Skeleton class="h-48 w-full rounded-xl" />
    </div>

    <template v-else-if="restaurant">
      <!-- Header -->
      <div class="space-y-2">
        <div class="flex items-start justify-between gap-4">
          <h1 class="text-2xl font-semibold tracking-tight">{{ restaurant.name }}</h1>
          <Badge :variant="restaurant.is_active ? 'default' : 'secondary'">
            {{ restaurant.is_active ? 'Ouvert' : 'Ferme' }}
          </Badge>
        </div>
        <div class="flex items-center gap-1.5 text-muted-foreground">
          <MapPin class="size-4" />
          <span class="text-sm">{{ restaurant.address }}</span>
        </div>
        <p class="text-xs text-muted-foreground">
          Cree le {{ new Date(restaurant.created_at).toLocaleDateString('fr-FR', { dateStyle: 'long' }) }}
        </p>
      </div>

      <!-- Stats row -->
      <div class="grid grid-cols-3 gap-3">
        <Card>
          <CardContent class="p-4 text-center space-y-1">
            <Star class="size-5 mx-auto text-yellow-500" />
            <p class="text-xl font-bold">{{ restaurant.avg_rating > 0 ? Number(restaurant.avg_rating).toFixed(1) : '-' }}</p>
            <p class="text-xs text-muted-foreground">Note moyenne</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center space-y-1">
            <Users class="size-5 mx-auto text-blue-500" />
            <p class="text-xl font-bold">{{ restaurant.total_ratings || 0 }}</p>
            <p class="text-xs text-muted-foreground">Avis clients</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4 text-center space-y-1">
            <Utensils class="size-5 mx-auto text-green-500" />
            <p class="text-xl font-bold">-</p>
            <p class="text-xs text-muted-foreground">Commandes</p>
          </CardContent>
        </Card>
      </div>

      <!-- Ratings distribution -->
      <Card v-if="restaurant.total_ratings > 0">
        <CardHeader class="pb-3">
          <CardTitle class="text-base flex items-center gap-2">
            <BarChart2 class="size-4" />Distribution des notes
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-2.5">
          <div
            v-for="star in [5, 4, 3, 2, 1]" :key="star"
            class="flex items-center gap-3"
          >
            <div class="flex items-center gap-1 w-12 shrink-0">
              <Star class="size-3 text-yellow-500 fill-yellow-500" />
              <span class="text-xs">{{ star }}</span>
            </div>
            <Progress
              :model-value="ratingBarWidth(restaurant.ratings_distribution?.[star] || 0, restaurant.total_ratings)"
              class="h-2 flex-1"
            />
            <span class="text-xs text-muted-foreground w-6 text-right">
              {{ restaurant.ratings_distribution?.[star] || 0 }}
            </span>
          </div>
        </CardContent>
      </Card>

      <!-- CTA -->
      <div class="flex gap-3">
        <Button class="flex-1" @click="router.push({ name: 'restaurant-menu', params: { id: restaurant.id } })">
          <Utensils class="size-4" />Voir le menu
          <ChevronRight class="size-4" />
        </Button>
      </div>
    </template>
  </div>
</template>

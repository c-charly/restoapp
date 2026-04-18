<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { useCartStore } from '@/stores/cart.store'
import { analyticsService } from '@/services/analytics.service'
import http, { backendUrl } from '@/services/http'
import { Utensils, Star, ShoppingCart, MapPin, Flame } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from 'vue-toastification'

const toast = useToast()
const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()
const feed = ref<any>({})
const loading = ref(true)
const error = ref('')

async function loadFeed() {
  try {
    loading.value = true
    const { data } = await http.get('/core/homepage/')
    feed.value = data
  } catch {
    error.value = 'Impossible de charger le feed'
  } finally {
    loading.value = false
  }
}

async function addToCart(item: any) {
  try {
    await cartStore.addItem({ restaurant_id: item.restaurant_id, item_id: item.item_id, quantity: 1 })
    toast.success('Plat ajouté au panier !')
  } catch { toast.error('Erreur lors de l\'ajout du plat au panier') }
}

function goToMenu(restaurantId: string) {
  router.push({ name: 'restaurant-menu', params: { id: restaurantId } })
}

function formatPrice(price: number) {
  return new Intl.NumberFormat('fr-FR').format(price) + ' XAF'
}

onMounted(() => { loadFeed(); cartStore.fetchCart() })
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">
          Bonjour{{ authStore.user ? `, ${authStore.user.first_name || authStore.user.email.split('@')[0]}` : '' }}
        </h1>
        <p class="text-muted-foreground text-sm mt-1">Que souhaitez-vous commander aujourd'hui ?</p>
      </div>
      <Button v-if="cartStore.itemsCount > 0" variant="outline" size="sm" @click="router.push({ name: 'cart' })">
        <ShoppingCart class="size-4" />
        {{ cartStore.itemsCount }} article{{ cartStore.itemsCount > 1 ? 's' : '' }}
      </Button>
    </div>

    <div v-if="loading" class="space-y-6">
      <div v-for="i in 3" :key="i" class="space-y-4">
        <Skeleton class="h-6 w-48" />
        <Skeleton class="h-4 w-64" />
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="j in 3" :key="j" class="space-y-3">
            <Skeleton class="h-44 w-full rounded-xl" />
            <Skeleton class="h-4 w-3/4" />
            <Skeleton class="h-4 w-1/2" />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="error" class="text-center py-12 text-muted-foreground">
      <Utensils class="size-12 mx-auto mb-3 opacity-40" />
      <p>{{ error }}</p>
      <Button variant="outline" class="mt-4" @click="loadFeed">Reessayer</Button>
    </div>

    <div v-else-if="!feed.sections || feed.sections.length === 0" class="text-center py-12">
      <Utensils class="size-12 mx-auto mb-3 opacity-40" />
      <p class="text-muted-foreground">Aucun plat disponible</p>
      <Button class="mt-4" @click="router.push({ name: 'restaurants' })">Voir les restaurants</Button>
    </div>

    <div v-else class="space-y-8">
      <div v-for="section in feed.sections" :key="section.title" class="space-y-4">
        <div>
          <h2 class="text-xl font-semibold">{{ section.title}}</h2>
          <p class="text-sm text-muted-foreground">{{ section.reason }}</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card
            v-for="item in section.items" :key="item.item_id"
            class="overflow-hidden group cursor-pointer hover:shadow-md transition-shadow p-0"
            @click="goToMenu(item.restaurant_id)"
          >
            <div class="relative bg-muted overflow-hidden h-44">
              <img v-if="item.photos?.length" :src="backendUrl + item.photos[0]" :alt="item.name"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              <div v-else class="w-full h-full flex items-center justify-center">
                <Utensils class="size-10 text-muted-foreground/40" />
              </div>
              <div class="absolute top-2 left-2 flex gap-1.5">
                <Badge v-if="section.title.includes('Recommandés')" class="bg-primary text-primary-foreground border-0 text-xs">Pour vous</Badge>
                <Badge v-if="section.title.includes('En ce moment')" class="bg-orange-500 text-white border-0 text-xs">
                  <Flame class="size-3 mr-1" />Tendance
                </Badge>
                <Badge v-if="section.title.includes('Les incontournables')" class="bg-yellow-500 text-white border-0 text-xs">
                  <Star class="size-3 mr-1" />Top note
                </Badge>
                <Badge v-if="section.title.includes('Chez')" class="bg-green-500 text-white border-0 text-xs">Favori</Badge>
              </div>
              <div v-if="item.promo_price" class="absolute top-2 right-2">
                <Badge class="bg-red-500 text-white border-0 text-xs">Promo</Badge>
              </div>
            </div>
            <CardContent class="p-4 space-y-3">
              <div class="flex items-start justify-between gap-2">
                <h3 class="font-medium text-sm leading-tight">{{ item.name }}</h3>
                <div v-if="item.avg_rating > 0" class="flex items-center gap-0.5 shrink-0">
                  <Star class="size-3 text-yellow-500 fill-yellow-500" />
                  <span class="text-xs text-muted-foreground">{{ Number(item.avg_rating).toFixed(1) }}</span>
                </div>
              </div>
              <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
                <MapPin class="size-3" />
                <span class="truncate">{{ item.restaurant_name }}</span>
              </div>
              <div class="flex items-center justify-between pt-1">
                <div>
                  <span v-if="item.promo_price" class="text-xs line-through text-muted-foreground mr-1">{{ formatPrice(item.price) }}</span>
                  <span class="font-semibold text-sm">{{ formatPrice(item.promo_price || item.price) }}</span>
                </div>
                <Button size="sm" variant="outline" class="h-7 text-xs" @click.stop="addToCart(item)">
                  <ShoppingCart class="size-3" />Ajouter
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

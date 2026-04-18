<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ordersService, type Order } from '@/services/orders.service'
import { cartService } from '@/services/cart.service'
import { useAuthStore } from '@/stores/auth.store'
import { useRestaurantsStore } from '@/stores/restaurants.store'
import {
  ArrowLeft, Package, MapPin, Clock, CheckCircle, XCircle,
  Truck, ChefHat, Star, Send, AlertCircle, Tag
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { useToast } from 'vue-toastification'
import { backendUrl } from '@/services/http'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const restaurantsStore = useRestaurantsStore()
const toast = useToast()

const id = route.params.id as string
const order = ref<Order | null>(null)
const loading = ref(true)
const cancelling = ref(false)
const updatingStatus = ref(false)
const newStatus = ref('')
const showReviewDialog = ref(false)
const reviewItem = ref<any>(null)
const reviewRating = ref(5)
const reviewComment = ref('')
const submittingReview = ref(false)

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  confirmed: 'Confirmee',
  preparing: 'En preparation',
  picked_up: 'Recuperee',
  delivering: 'En livraison',
  delivered: 'Livree',
  cancelled: 'Annulee'
}

const ADMIN_STATUSES = ['pending', 'confirmed', 'preparing', 'picked_up', 'delivering', 'delivered', 'cancelled']

const canCancel = computed(() => {
  return order.value && ['pending', 'confirmed'].includes(order.value.status)
})

const canReview = computed(() => order.value?.status === 'delivered')

const orderSteps = computed(() => {
  const steps = ['pending', 'confirmed', 'preparing', 'picked_up', 'delivering', 'delivered']
  const current = steps.indexOf(order.value?.status || '')
  return steps.map((s, i) => ({ key: s, label: STATUS_LABELS[s], done: i <= current, active: i === current }))
})

async function load() {
  try {
    loading.value = true
    order.value = await ordersService.get(id)
    newStatus.value = order.value.status
  } finally {
    loading.value = false
  }
}

async function cancel() {
  cancelling.value = true
  try {
    order.value = await ordersService.cancel(id)
    toast.success('Commande annulee')
  } catch (e: any) {
    toast.error(e.response?.data?.error || 'Impossible d\'annuler')
  } finally {
    cancelling.value = false
  }
}

async function updateStatus() {
  if (!newStatus.value || newStatus.value === order.value?.status) return
  updatingStatus.value = true
  try {
    order.value = await ordersService.updateStatus(id, newStatus.value)
    toast.success('Statut mis a jour')
  } catch (e: any) {
    toast.error('Erreur lors de la mise a jour')
  } finally {
    updatingStatus.value = false
  }
}

function openReview(item: any) {
  reviewItem.value = item
  reviewRating.value = 5
  reviewComment.value = ''
  showReviewDialog.value = true
}

async function submitReview() {
  if (!reviewItem.value) return
  submittingReview.value = true
  try {
    await cartService.rateItem({
      item_id: reviewItem.value.snapshot_data?.id || reviewItem.value.id,
      item_name: reviewItem.value.item_name,
      rating: reviewRating.value,
      comment: reviewComment.value,
      order_id: id
    })
    toast.success('Avis soumis, merci !')
    showReviewDialog.value = false
  } catch (e: any) {
    toast.error(e.response?.data?.error || 'Erreur lors de la soumission')
  } finally {
    submittingReview.value = false
  }
}

function formatPrice(p: string | number) {
  return new Intl.NumberFormat('fr-FR').format(Number(p)) + ' XAF'
}

function formatDate(d: string) {
  return new Date(d)?.toLocaleDateString('fr-FR', { dateStyle: 'full' })
}

onMounted(load)
</script>

<template>
  <div class="space-y-6 max-w-2xl">
    <Button variant="ghost" size="sm" class="-ml-2" @click="router.back()">
      <ArrowLeft class="size-4" />Retour
    </Button>

    <div v-if="loading" class="text-center py-16 text-muted-foreground">Chargement...</div>

    <template v-else-if="order">
      <!-- Header -->
      <div class="flex items-start justify-between gap-4">
        <div>
          <h1 class="text-xl font-semibold">Commande #{{ order.id.slice(0, 8) }}</h1>
          <p class="text-sm text-muted-foreground">{{ order.restaurant_name }}</p>
          <p class="text-xs text-muted-foreground">{{ formatDate(order.created_at) }}</p>
        </div>
        <Badge variant="outline" class="text-sm px-3 py-1">
          {{ STATUS_LABELS[order.status] || order.status }}
        </Badge>
      </div>

      <!-- Progress tracker (non-cancelled) -->
      <Card v-if="order.status !== 'cancelled'">
        <CardContent class="p-4">
          <div class="flex items-center justify-between relative">
            <div class="absolute left-0 right-0 top-4 h-0.5 bg-border mx-5"></div>
            <template v-for="(step, i) in orderSteps.slice(0, 6)" :key="step.key">
              <div class="flex flex-col items-center gap-1.5 relative z-10">
                <div :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors',
                  step.done ? 'bg-primary border-primary text-primary-foreground' : 'bg-background border-border text-muted-foreground'
                ]">
                  <CheckCircle v-if="step.done && !step.active" class="size-4" />
                  <div v-else-if="step.active" class="w-2.5 h-2.5 rounded-full bg-current"></div>
                  <div v-else class="w-2 h-2 rounded-full bg-border"></div>
                </div>
                <span class="text-xs text-center hidden sm:block text-muted-foreground max-w-14 leading-tight">
                  {{ step.label }}
                </span>
              </div>
            </template>
          </div>
        </CardContent>
      </Card>

      <!-- Cancelled state -->
      <Card v-else class="border-destructive/30 bg-destructive/5">
        <CardContent class="p-4 flex items-center gap-3">
          <XCircle class="size-5 text-destructive shrink-0" />
          <p class="text-sm text-destructive">Cette commande a ete annulee</p>
        </CardContent>
      </Card>

      <!-- Admin status update -->
      <Card v-if="authStore.isAdmin">
        <CardHeader class="pb-3">
          <CardTitle class="text-sm">Mettre a jour le statut</CardTitle>
        </CardHeader>
        <CardContent class="flex gap-3">
          <Select v-model="newStatus" class="flex-1">
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="s in ADMIN_STATUSES" :key="s" :value="s">
                {{ STATUS_LABELS[s] }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Button :disabled="updatingStatus || newStatus === order.status" @click="updateStatus">
            {{ updatingStatus ? '...' : 'Valider' }}
          </Button>
        </CardContent>
      </Card>

      <!-- Items -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base">Articles commandés</CardTitle>
        </CardHeader>
        <div class="divide-y">
          <div v-for="item in order.items" :key="item.id" class="flex items-center justify-between px-4 py-3">
            <div class="flex items-center gap-3">
              <!-- Photo -->
              <div class="w-20 h-20 rounded-lg bg-muted overflow-hidden shrink-0">
                <img v-if="item.snapshot_data.photos?.length" :src="backendUrl + item.snapshot_data.photos[0]"
                  :alt="item.item_name" class="w-full h-full object-cover" />
                <div v-else class="w-full h-full flex items-center justify-center text-muted-foreground/40">
                  <Tag class="size-6" />
                </div>
              </div>

              <div>
                <p class="font-medium text-sm">{{ item.item_name }}</p>
                <p class="text-xs text-muted-foreground">{{ item.quantity }} x {{ formatPrice(item.item_price) }}</p>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <p class="font-semibold text-sm">{{ formatPrice(Number(item.item_price) * item.quantity) }}</p>
              <Button v-if="canReview" size="sm" variant="outline" class="h-7 text-xs" @click="openReview(item)">
                <Star class="size-3" />Noter
              </Button>
            </div>
          </div>

        </div>
        <Separator />
        <div class="flex items-center justify-between px-4 py-3">
          <span class="font-semibold">Total</span>
          <span class="font-bold text-lg">{{ formatPrice(order.total_price) }}</span>
        </div>
      </Card>

      <!-- Delivery address -->
      <Card v-if="order.delivery_address">
        <CardContent class="p-4 flex items-center gap-3">
          <MapPin class="size-5 text-muted-foreground shrink-0" />
          <div>
            <p class="text-sm font-medium">Adresse de livraison</p>
            <p class="text-xs text-muted-foreground">{{ order.delivery_address }}</p>
          </div>
        </CardContent>
      </Card>

      <!-- Cancel button -->
      <Button v-if="canCancel && !authStore.isAdmin" variant="destructive" class="w-full" :disabled="cancelling"
        @click="cancel">
        <XCircle class="size-4" />
        {{ cancelling ? 'Annulation...' : 'Annuler la commande' }}
      </Button>
    </template>

    <!-- Review dialog -->
    <Dialog v-model:open="showReviewDialog">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>Noter "{{ reviewItem?.item_name }}"</DialogTitle>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>Note</Label>

            <div class="flex gap-2 justify-center">
              <button v-for="n in restaurantsStore.ratingLabel" :key="n.value" @click="reviewRating = n.value" class="focus:outline-none cursor-pointer">
                <div class="p-2 rounded-full flex items-center justify-center transition-colors duration-200"
                  :class="n.value == reviewRating ? 'bg-yellow-500/30' : ''">
                  <span class="text-3xl">{{ n.icon }}</span>
                </div>
              </button>
            </div>

          </div>
          <div class="space-y-1.5">
            <Label>Commentaire (optionnel)</Label>
            <Textarea v-model="reviewComment" placeholder="Partagez votre experience..." rows="3" />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="showReviewDialog = false">Annuler</Button>
          <Button @click="submitReview" :disabled="submittingReview">
            <Send class="size-4" />
            {{ submittingReview ? 'Envoi...' : 'Soumettre' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

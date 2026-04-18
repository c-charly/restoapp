<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ordersService, type Order } from '@/services/orders.service'
import { useAuthStore } from '@/stores/auth.store'
import {
  Package, ChevronRight, Clock, CheckCircle, XCircle,
  Truck, ChefHat, Filter
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'

const router = useRouter()
const authStore = useAuthStore()

const orders = ref<Order[]>([])
const loading = ref(true)
const statusFilter = ref('all')

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  confirmed: 'Confirmee',
  preparing: 'En preparation',
  picked_up: 'Recuperee',
  delivering: 'En livraison',
  delivered: 'Livree',
  cancelled: 'Annulee'
}

const STATUS_VARIANT: Record<string, string> = {
  pending: 'secondary',
  confirmed: 'outline',
  preparing: 'outline',
  picked_up: 'outline',
  delivering: 'outline',
  delivered: 'default',
  cancelled: 'destructive'
}

const filtered = computed(() => {
  if (statusFilter.value === 'all') return orders.value
  return orders.value.filter(o => o.status === statusFilter.value)
})

async function load() {
  try {
    loading.value = true
    orders.value = await ordersService.list()
  } finally {
    loading.value = false
  }
}

function statusIcon(status: string) {
  const map: Record<string, any> = {
    pending: Clock,
    confirmed: CheckCircle,
    preparing: ChefHat,
    picked_up: Package,
    delivering: Truck,
    delivered: CheckCircle,
    cancelled: XCircle
  }
  return map[status] || Package
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatPrice(p: string | number) {
  return new Intl.NumberFormat('fr-FR').format(Number(p)) + ' XAF'
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Commandes</h1>
        <p class="text-muted-foreground text-sm mt-0.5">{{ filtered.length }} commande{{ filtered.length > 1 ? 's' : '' }}</p>
      </div>
      <Select v-model="statusFilter">
        <SelectTrigger class="w-44">
          <Filter class="size-3.5 mr-2" />
          <SelectValue placeholder="Filtrer par statut" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Tous les statuts</SelectItem>
          <SelectItem v-for="(label, val) in STATUS_LABELS" :key="val" :value="val">{{ label }}</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-2">
      <Skeleton v-for="i in 6" :key="i" class="h-16 w-full rounded-lg" />
    </div>

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="text-center py-16">
      <Package class="size-14 mx-auto mb-4 text-muted-foreground/40" />
      <p class="text-muted-foreground">Aucune commande</p>
      <Button class="mt-4" @click="router.push({ name: 'restaurants' })">
        Commander maintenant
      </Button>
    </div>

    <!-- Table (admin) or Cards (client) -->
    <template v-else-if="authStore.isAdmin">
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Client</TableHead>
              <TableHead>Restaurant</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Date</TableHead>
              <TableHead class="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="order in filtered" :key="order.id"
              class="cursor-pointer hover:bg-muted/50"
              @click="router.push({ name: 'order-detail', params: { id: order.id } })"
            >
              <TableCell class="font-mono text-xs text-muted-foreground">{{ order.id.slice(0, 8) }}...</TableCell>
              <TableCell class="text-sm">{{ order.client_email }}</TableCell>
              <TableCell class="text-sm">{{ order.restaurant_name }}</TableCell>
              <TableCell>
                <Badge :variant="(STATUS_VARIANT[order.status] as any) || 'secondary'" class="text-xs">
                  {{ STATUS_LABELS[order.status] || order.status }}
                </Badge>
              </TableCell>
              <TableCell class="font-semibold text-sm">{{ formatPrice(order.total_price) }}</TableCell>
              <TableCell class="text-xs text-muted-foreground">{{ formatDate(order.created_at) }}</TableCell>
              <TableCell><ChevronRight class="size-4 text-muted-foreground" /></TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </template>

    <div v-else class="space-y-3">
      <Card
        v-for="order in filtered" :key="order.id"
        class="cursor-pointer hover:shadow-md transition-shadow"
        @click="router.push({ name: 'order-detail', params: { id: order.id } })"
      >
        <CardContent class="p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl bg-muted flex items-center justify-center shrink-0">
                <component :is="statusIcon(order.status)" class="size-5 text-muted-foreground" />
              </div>
              <div>
                <p class="font-medium text-sm">{{ order.restaurant_name }}</p>
                <p class="text-xs text-muted-foreground">{{ order.items?.length || 0 }} article{{ (order.items?.length || 0) > 1 ? 's' : '' }}</p>
                <p class="text-xs text-muted-foreground">{{ formatDate(order.created_at) }}</p>
              </div>
            </div>
            <div class="text-right shrink-0 space-y-1">
              <p class="font-bold text-sm">{{ formatPrice(order.total_price) }}</p>
              <Badge :variant="(STATUS_VARIANT[order.status] as any) || 'secondary'" class="text-xs">
                {{ STATUS_LABELS[order.status] || order.status }}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

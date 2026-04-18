<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart.store'
import { useAuthStore } from '@/stores/auth.store'
import { addressService } from '@/services/account.service'
import {
  ShoppingCart, Minus, Plus, Trash2, MapPin, CreditCard,
  ArrowLeft, Package, ChevronRight
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import { useToast } from 'vue-toastification'

const router = useRouter()
const cartStore = useCartStore()
const authStore = useAuthStore()
const toast = useToast()

const addresses = ref<any[]>([])
const selectedAddress = ref('')
const manualAddress = ref('')
const checkingOut = ref(false)

const deliveryAddress = computed(() => {
  if (selectedAddress.value === '__manual__') return manualAddress.value
  const a = addresses.value.find(a => a.id === selectedAddress.value)
  return a ? a.label : ''
})

async function loadAddresses() {
  try {
    addresses.value = await addressService.list()
    const def = addresses.value.find(a => a.is_default)
    if (def) selectedAddress.value = def.id
  } catch { /* ignore */ }
}

async function updateQty(itemId: string, qty: number) {
  try {
    if (qty === 0) await cartStore.removeItem(itemId)
    else await cartStore.updateItem(itemId, qty)
  } catch (e: any) {
    toast.error(e.response?.data?.error || 'Erreur')
  }
}

async function checkout() {
  checkingOut.value = true
  try {
    const result = await cartStore.checkout(deliveryAddress.value)
    toast.success('Commande passee avec succes !')
    router.push({ name: 'orders' })
  } catch (e: any) {
    const code = e.response?.data?.code
    if (code === 'INSUFFICIENT_FUNDS') {
      toast.error('Solde insuffisant. Rechargez votre wallet.')
    } else {
      toast.error(e.response?.data?.error || 'Erreur lors du checkout')
    }
  } finally {
    checkingOut.value = false
  }
}

async function abandonCart() {
  await cartStore.abandon()
  toast.info('Panier vide')
}

function formatPrice(p: string | number) {
  return new Intl.NumberFormat('fr-FR').format(Number(p)) + ' XAF'
}

onMounted(async () => {
  await cartStore.fetchCart()
  await loadAddresses()
})
</script>

<template>
  <div class="space-y-6 max-w-2xl">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="icon" class="size-9" @click="router.back()">
        <ArrowLeft class="size-4" />
      </Button>
      <div>
        <h1 class="text-xl font-semibold">Mon panier</h1>
        <p class="text-sm text-muted-foreground">{{ cartStore.cart?.restaurant_name }}</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cartStore.loading" class="text-center py-16 text-muted-foreground">
      Chargement...
    </div>

    <!-- Empty -->
    <div v-else-if="!cartStore.cart || !cartStore.cart.items?.length" class="text-center py-16">
      <ShoppingCart class="size-16 mx-auto mb-4 text-muted-foreground/40" />
      <p class="text-muted-foreground mb-4">Votre panier est vide</p>
      <Button @click="router.push({ name: 'restaurants' })">
        Voir les restaurants
      </Button>
    </div>

    <template v-else>
      <!-- Items -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base">Articles</CardTitle>
        </CardHeader>
        <div class="divide-y">
          <div v-for="item in cartStore.cart.items" :key="item.id" class="flex items-start gap-4 px-4 py-3">
            <div class="flex-1 min-w-0">
              <p class="font-medium text-sm">{{ item.item_name }}</p>
              <p v-if="item.selected_options?.length" class="text-xs text-muted-foreground">
                {{ item.selected_options.map((o: any) => o.label).join(', ') }}
              </p>
              <p v-if="item.special_instructions" class="text-xs text-muted-foreground italic">
                "{{ item.special_instructions }}"
              </p>
              <p class="text-xs text-muted-foreground mt-0.5">{{ formatPrice(item.base_price) }} / unite</p>
            </div>
            <div class="flex items-center gap-2">
              <Button size="icon" variant="outline" class="size-7" @click="updateQty(item.item_id, item.quantity - 1)">
                <Minus class="size-3" />
              </Button>
              <span class="w-6 text-center text-sm font-medium">{{ item.quantity }}</span>
              <Button size="icon" variant="outline" class="size-7" @click="updateQty(item.item_id, item.quantity + 1)">
                <Plus class="size-3" />
              </Button>
            </div>
            <div class="text-right shrink-0">
              <p class="font-semibold text-sm">{{ formatPrice(item.line_total) }}</p>
              <Button size="icon" variant="ghost" class="size-6 mt-1 text-destructive hover:text-destructive" @click="updateQty(item.item_id, 0)">
                <Trash2 class="size-3" />
              </Button>
            </div>
          </div>
        </div>
        <Separator />
        <div class="flex items-center justify-between px-4 py-3">
          <span class="font-semibold">Sous-total</span>
          <span class="font-bold text-lg">{{ formatPrice(cartStore.subtotal) }}</span>
        </div>
      </Card>

      <!-- Livraison -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base flex items-center gap-2">
            <MapPin class="size-4" />Adresse de livraison
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div v-if="addresses.length">
            <Select v-model="selectedAddress">
              <SelectTrigger>
                <SelectValue placeholder="Choisir une adresse" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="a in addresses" :key="a.id" :value="a.id">
                  {{ a.label }}{{ a.is_default ? ' (defaut)' : '' }}
                </SelectItem>
                <SelectItem value="__manual__">Saisir une adresse manuellement</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Input
            v-if="!addresses.length || selectedAddress === '__manual__'"
            v-model="manualAddress"
            placeholder="Ex: Quartier Bastos, Yaounde"
          />
        </CardContent>
      </Card>

      <!-- Wallet -->
      <Card>
        <CardContent class="p-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <CreditCard class="size-5 text-muted-foreground" />
            <div>
              <p class="text-sm font-medium">Wallet</p>
              <p class="text-xs text-muted-foreground">Solde disponible</p>
            </div>
          </div>
          <div class="text-right">
            <p class="font-semibold">{{ formatPrice(authStore.wallet?.balance || 0) }}</p>
            <Button variant="link" size="sm" class="h-auto p-0 text-xs" @click="router.push({ name: 'profile' })">
              Recharger
            </Button>
          </div>
        </CardContent>
      </Card>

      <!-- Actions -->
      <div class="flex gap-3">
        <Button variant="outline" @click="abandonCart">
          <Trash2 class="size-4" />Vider
        </Button>
        <Button class="flex-1" :disabled="checkingOut" @click="checkout">
          <Package class="size-4" />
          {{ checkingOut ? 'Traitement...' : `Commander - ${formatPrice(cartStore.subtotal)}` }}
        </Button>
      </div>
    </template>
  </div>
</template>

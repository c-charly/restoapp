<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.store'
import { walletService, addressService } from '@/services/account.service'
import { authService } from '@/services/auth.service'
import http from '@/services/http'
import {
  User, CreditCard, MapPin, Plus, Trash2, Star,
  TrendingUp, Check, ArrowUpRight, ArrowDownLeft, Pencil
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { useToast } from 'vue-toastification'

const authStore = useAuthStore()
const toast = useToast()

const transactions = ref<any[]>([])
const addresses = ref<any[]>([])
const analyticsProfile = ref<any>(null)
const topupAmount = ref<number>(1000)
const topupLoading = ref(false)
const showAddressDialog = ref(false)
const editingAddress = ref<any>(null)
const addressForm = ref({ label: '', latitude: '', longitude: '' })
const savingProfile = ref(false)
const profileForm = ref({ first_name: '', last_name: '', phone: '' })

const LOYALTY_COLORS: Record<string, string> = {
  new: 'secondary',
  bronze: 'outline',
  silver: 'secondary',
  gold: 'default',
  platinum: 'default'
}

async function loadAll() {
  const [txs, addrs] = await Promise.all([
    walletService.transactions().catch(() => []),
    addressService.list().catch(() => []),
  ])
  transactions.value = txs
  addresses.value = addrs

  try {
    const { data } = await http.get('/analytics/me/')
    analyticsProfile.value = data
  } catch { /* ignore */ }

  if (authStore.user) {
    profileForm.value = {
      first_name: authStore.user.first_name,
      last_name: authStore.user.last_name,
      phone: authStore.user.phone
    }
  }
}

async function topup() {
  if (!topupAmount.value || topupAmount.value < 100) {
    toast.error('Montant minimum: 100 XAF')
    return
  }
  topupLoading.value = true
  try {
    await walletService.topup(topupAmount.value)
    await authStore.fetchMe()
    await walletService.transactions().then(t => transactions.value = t)
    toast.success(`${topupAmount.value} XAF credite`)
  } catch (e: any) {
    toast.error(e.response?.data?.error || 'Erreur de recharge')
  } finally {
    topupLoading.value = false
  }
}

function openAddAddress() {
  editingAddress.value = null
  addressForm.value = { label: '', latitude: '', longitude: '' }
  showAddressDialog.value = true
}

function openEditAddress(addr: any) {
  editingAddress.value = addr
  addressForm.value = { label: addr.label, latitude: String(addr.latitude), longitude: String(addr.longitude) }
  showAddressDialog.value = true
}

async function saveAddress() {
  if (!addressForm.value.label) { toast.error('Label requis'); return }
  try {
    const payload = {
      label: addressForm.value.label,
      latitude: parseFloat(addressForm.value.latitude) || 0,
      longitude: parseFloat(addressForm.value.longitude) || 0
    }
    if (editingAddress.value) {
      await addressService.update(editingAddress.value.id, payload)
    } else {
      await addressService.create(payload)
    }
    addresses.value = await addressService.list()
    showAddressDialog.value = false
    toast.success('Adresse enregistree')
  } catch (e: any) {
    toast.error('Erreur')
  }
}

async function deleteAddress(id: string) {
  await addressService.delete(id)
  addresses.value = addresses.value.filter(a => a.id !== id)
  toast.info('Adresse supprimee')
}

async function setDefault(id: string) {
  await addressService.setDefault(id)
  addresses.value = await addressService.list()
  toast.success('Adresse par defaut definie')
}

async function saveProfile() {
  savingProfile.value = true
  try {
    const { data } = await http.patch('/auth/me/', profileForm.value)
    authStore.user = data.user || data
    toast.success('Profil mis a jour')
  } catch {
    toast.error('Erreur')
  } finally {
    savingProfile.value = false
  }
}

function formatPrice(p: string | number) {
  return new Intl.NumberFormat('fr-FR').format(Number(p)) + ' XAF'
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

onMounted(loadAll)
</script>

<template>
  <div class="space-y-6 max-w-3xl">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Mon profil</h1>
      <p class="text-muted-foreground text-sm mt-0.5">{{ authStore.user?.email }}</p>
    </div>

    <Tabs default-value="profile">
      <TabsList class="grid grid-cols-4 w-full">
        <TabsTrigger value="profile"><User class="size-4 mr-1.5" />Profil</TabsTrigger>
        <TabsTrigger value="wallet"><CreditCard class="size-4 mr-1.5" />Wallet</TabsTrigger>
        <TabsTrigger value="addresses"><MapPin class="size-4 mr-1.5" />Adresses</TabsTrigger>
        <TabsTrigger value="stats"><TrendingUp class="size-4 mr-1.5" />Stats</TabsTrigger>
      </TabsList>

      <!-- Profil -->
      <TabsContent value="profile" class="mt-4">
        <Card>
          <CardHeader><CardTitle class="text-base">Informations personnelles</CardTitle></CardHeader>
          <CardContent class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1.5">
                <Label>Prenom</Label>
                <Input v-model="profileForm.first_name" placeholder="Jean" />
              </div>
              <div class="space-y-1.5">
                <Label>Nom</Label>
                <Input v-model="profileForm.last_name" placeholder="Dupont" />
              </div>
              <div class="col-span-2 space-y-1.5">
                <Label>Telephone</Label>
                <Input v-model="profileForm.phone" placeholder="+237 6XX XXX XXX" />
              </div>
              <div class="col-span-2 space-y-1.5">
                <Label>Email</Label>
                <Input :value="authStore.user?.email" disabled class="opacity-60" />
              </div>
            </div>
            <Button @click="saveProfile" :disabled="savingProfile">
              {{ savingProfile ? 'Enregistrement...' : 'Sauvegarder' }}
            </Button>
          </CardContent>
        </Card>
      </TabsContent>

      <!-- Wallet -->
      <TabsContent value="wallet" class="mt-4 space-y-4">
        <!-- Balance -->
        <Card class="bg-primary text-primary-foreground">
          <CardContent class="p-6">
            <p class="text-sm opacity-80">Solde disponible</p>
            <p class="text-4xl font-bold mt-1">{{ formatPrice(authStore.wallet?.balance || 0) }}</p>
            <p class="text-xs opacity-60 mt-2">Mis a jour {{ authStore.wallet ? formatDate(authStore.wallet.updated_at) : '-' }}</p>
          </CardContent>
        </Card>

        <!-- Topup -->
        <Card>
          <CardHeader><CardTitle class="text-base">Recharger mon wallet</CardTitle></CardHeader>
          <CardContent class="flex gap-3">
            <Input v-model="topupAmount" type="number" placeholder="Montant (min 100 XAF)" class="flex-1" min="100" />
            <Button :disabled="topupLoading" @click="topup">
              {{ topupLoading ? 'Traitement...' : 'Recharger' }}
            </Button>
          </CardContent>
        </Card>

        <!-- Transactions -->
        <Card>
          <CardHeader><CardTitle class="text-base">Historique des transactions</CardTitle></CardHeader>
          <div v-if="!transactions.length" class="px-4 pb-4 text-sm text-muted-foreground">Aucune transaction</div>
          <div v-else class="divide-y">
            <div v-for="tx in transactions" :key="tx.id" class="flex items-center justify-between px-4 py-3">
              <div class="flex items-center gap-3">
                <div :class="['w-8 h-8 rounded-full flex items-center justify-center', tx.type === 'credit' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600']">
                  <component :is="tx.type === 'credit' ? ArrowDownLeft : ArrowUpRight" class="size-4" />
                </div>
                <div>
                  <p class="text-sm font-medium">{{ tx.description || (tx.type === 'credit' ? 'Recharge' : 'Paiement') }}</p>
                  <p class="text-xs text-muted-foreground">{{ formatDate(tx.created_at) }}</p>
                </div>
              </div>
              <p :class="['font-semibold text-sm', tx.type === 'credit' ? 'text-green-600' : 'text-red-600']">
                {{ tx.type === 'credit' ? '+' : '-' }}{{ formatPrice(tx.amount) }}
              </p>
            </div>
          </div>
        </Card>
      </TabsContent>

      <!-- Adresses -->
      <TabsContent value="addresses" class="mt-4">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between pb-3">
            <CardTitle class="text-base">Mes adresses</CardTitle>
            <Button size="sm" variant="outline" @click="openAddAddress">
              <Plus class="size-3.5" />Ajouter
            </Button>
          </CardHeader>
          <div v-if="!addresses.length" class="px-4 pb-4 text-sm text-muted-foreground">Aucune adresse enregistree</div>
          <div v-else class="divide-y">
            <div v-for="addr in addresses" :key="addr.id" class="flex items-center justify-between px-4 py-3">
              <div class="flex items-center gap-3">
                <MapPin class="size-4 text-muted-foreground shrink-0" />
                <div>
                  <p class="text-sm font-medium">{{ addr.label }}</p>
                  <p class="text-xs text-muted-foreground">{{ addr.latitude }}, {{ addr.longitude }}</p>
                </div>
                <Badge v-if="addr.is_default" variant="secondary" class="text-xs">Defaut</Badge>
              </div>
              <div class="flex items-center gap-1">
                <Button v-if="!addr.is_default" size="sm" variant="ghost" class="h-7 text-xs" @click="setDefault(addr.id)">
                  <Check class="size-3" />Defaut
                </Button>
                <Button size="icon" variant="ghost" class="size-7" @click="openEditAddress(addr)">
                  <Pencil class="size-3" />
                </Button>
                <Button size="icon" variant="ghost" class="size-7 text-destructive hover:text-destructive" @click="deleteAddress(addr.id)">
                  <Trash2 class="size-3" />
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </TabsContent>

      <!-- Stats perso -->
      <TabsContent value="stats" class="mt-4 space-y-4">
        <div v-if="!analyticsProfile" class="text-center py-8 text-muted-foreground text-sm">
          Chargement des statistiques...
        </div>
        <template v-else>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card>
              <CardContent class="p-4 text-center">
                <p class="text-2xl font-bold">{{ analyticsProfile.total_orders }}</p>
                <p class="text-xs text-muted-foreground mt-1">Commandes</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4 text-center">
                <p class="text-2xl font-bold">{{ formatPrice(analyticsProfile.total_spent_xaf) }}</p>
                <p class="text-xs text-muted-foreground mt-1">Depense total</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4 text-center">
                <p class="text-2xl font-bold">{{ analyticsProfile.total_sessions }}</p>
                <p class="text-xs text-muted-foreground mt-1">Sessions</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4 text-center">
                <Badge :variant="(LOYALTY_COLORS[analyticsProfile.loyalty_tier] as any) || 'secondary'" class="text-sm px-3 py-1 mt-1">
                  {{ analyticsProfile.loyalty_tier }}
                </Badge>
                <p class="text-xs text-muted-foreground mt-1">Tier</p>
              </CardContent>
            </Card>
          </div>
          <Card v-if="analyticsProfile.favorite_restaurant_name">
            <CardContent class="p-4 flex items-center gap-3">
              <Star class="size-5 text-yellow-500 fill-yellow-500" />
              <div>
                <p class="text-sm font-medium">Restaurant favori</p>
                <p class="text-xs text-muted-foreground">{{ analyticsProfile.favorite_restaurant_name }} - {{ analyticsProfile.favorite_restaurant_orders }} commandes</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle class="text-sm">Score d'engagement</CardTitle></CardHeader>
            <CardContent>
              <div class="flex items-center gap-3">
                <div class="flex-1 bg-muted rounded-full h-2.5 overflow-hidden">
                  <div class="h-full bg-primary rounded-full transition-all" :style="{ width: `${analyticsProfile.engagement_score}%` }"></div>
                </div>
                <span class="text-sm font-bold w-12 text-right">{{ analyticsProfile.engagement_score }}/100</span>
              </div>
              <div class="flex items-center gap-3 mt-3">
                <div class="flex-1 bg-muted rounded-full h-2.5 overflow-hidden">
                  <div class="h-full bg-destructive rounded-full transition-all" :style="{ width: `${analyticsProfile.churn_risk_score}%` }"></div>
                </div>
                <span class="text-xs text-muted-foreground w-12 text-right">Risque de depart</span>
              </div>
            </CardContent>
          </Card>
        </template>
      </TabsContent>
    </Tabs>

    <!-- Address Dialog -->
    <Dialog v-model:open="showAddressDialog">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ editingAddress ? 'Modifier l\'adresse' : 'Nouvelle adresse' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-3 py-2">
          <div class="space-y-1.5">
            <Label>Label (ex: Domicile, Bureau)</Label>
            <Input v-model="addressForm.label" placeholder="Domicile" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1.5">
              <Label>Latitude</Label>
              <Input v-model="addressForm.latitude" type="number" step="any" placeholder="3.848" />
            </div>
            <div class="space-y-1.5">
              <Label>Longitude</Label>
              <Input v-model="addressForm.longitude" type="number" step="any" placeholder="11.502" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showAddressDialog = false">Annuler</Button>
          <Button @click="saveAddress">Enregistrer</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

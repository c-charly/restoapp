<template>
  <div class="">
    <div class="flex items-center justify-between mb-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Restaurants</h1>
        <p class="text-muted-foreground text-sm mt-0.5">{{ restaurants.length }} restaurant{{ restaurants.length > 1 ? 's' : '' }} au total</p>
      </div>
      <Button v-if="authStore.isAdmin" @click="showCreate = true">
        <Plus class="size-4" />Ajouter
      </Button>
    </div>

    <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-3">
      <Skeleton v-for="i in 4" class="h-[200px] w-[400px]f" />
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-3">
      <Card v-for="resto in restaurants" class="rounded-2xl py-4">
        <CardHeader class="flex flex-row items-center justify-between px-4">
          <Badge :variant="resto.is_active ? 'secondary' : 'destructive'">
            <BadgeCheck v-if="resto.is_active" class="size-3" data-icon="inline-start" />
            <BadgeAlert v-else class="size-3" data-icon="inline-start" />
            {{ resto.is_active ? 'Active' : 'No Active' }}
          </Badge>

          <CopyToCliboard :value="resto.id" />
        </CardHeader>

        <CardContent class="flex flex-col gap-4 px-4">
          <div class="flex flex-col gap-3 border-b border-dashed pb-4">
            <div class="flex items-baseline gap-2">
              <span class="text-[14px] font-medium">Enregistrer le </span>
              <time class="text-muted-foreground text-xs font-medium tracking-widest">{{ fmtDate(resto.created_at)
              }}</time>
            </div>

            <h3 class="text-2xl/none font-semibold">{{ resto.name }}</h3>

            <div class="flex items-center gap-2">
              <Badge variant="secondary"><MapPin class="size-3.5 shrink-0" /> {{ resto.address }}</Badge>
              <Badge variant="secondary">Latitude : {{ resto.latitude }}</Badge>
              <Badge variant="secondary">Longitude : {{ resto.longitude }}</Badge>
            </div>
          </div>

          <div class="flex items-center justify-between gap-2">
            <div class="flex gap-1">
              <div v-for="rating in restorantStore.ratingLabel" class="flex flex-col gap-0.5 items-center">
                <span class="text-2xl">{{ rating.icon }}</span>
                <span class="text-xs opacity-80">{{ resto.ratings_distribution[rating.value] }}</span>
              </div>

              <div class="flex gap-1 h-fit">
                <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-8" />
                <span class="text-[14px] items-center flex">{{ resto.avg_rating }} / {{ resto.total_ratings}} Personnes</span>
              </div>

            </div>

            <div class="flex gap-2 items-center">
              <TooltipProvider>
                <Tooltip :delay-duration="0">
                  <TooltipTrigger as-child>
                    <Button variant="outline" class="p-0 px-2">
                      <RouterLink :to="`/restaurants/${resto.id}`">
                        <Eye :size="13" />
                      </RouterLink>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent class="px-2 py-1 text-xs">Détail</TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider>
                <Tooltip :delay-duration="0">
                  <TooltipTrigger as-child>
                    <Button variant="outline" class="p-0 px-2">
                      <RouterLink :to="`/restaurants/${resto.id}/menu`">
                        <UtensilsCrossed :size="13" />
                      </RouterLink>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent class="px-2 py-1 text-xs">Menus</TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider v-if="authStore.isAdmin">
                <Tooltip :delay-duration="0">
                  <TooltipTrigger as-child>
                    <Button variant="outline" class="p-0 py-1" @click="openEdit(resto)">
                      <Pencil :size="13" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent class="px-2 py-1 text-xs">Modifier</TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <!-- <TooltipProvider>
                <Tooltip :delay-duration="0">
                  <TooltipTrigger as-child>
                    <Button :variant="resto.is_active ? 'destructive' : 'secondary'" class="p-0 px-2"
                      @click="toggleActive(resto)">
                      <component :is="resto.is_active ? EyeOff : Eye" :size="13" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent class="px-2 py-1 text-xs">{{ resto.is_active ? 'Désactiver' : 'Activer' }}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider> -->
            </div>
          </div>
        </CardContent>
      </Card>
    </div>


    <Dialog v-model:open="showCreate">
      <DialogContent>
        <div class="flex flex-col items-center gap-2">
          <div class="flex size-11 shrink-0 items-center justify-center rounded-full border" aria-hidden="true">
            <UtensilsCrossed />
          </div>
          <DialogHeader>
            <DialogTitle class="sm:text-center">{{ editing ? 'Modifier le restaurant' : 'Nouveau restaurant' }}
            </DialogTitle>
            <DialogDescription class="sm:text-center">
              Enter les informations pour ce Restaurant.
            </DialogDescription>
          </DialogHeader>
        </div>

        <form @submit.prevent="handleSave" class="space-y-5">
          <div class="space-y-4">
            <div class="*:not-first:mt-2">
              <Label :for="`${id}-name`">Nom du restaurant</Label>
              <Input v-model="form.name" :id="`${id}-name`" placeholder="Restorant lulu" type="text" required />
            </div>
            <div class="*:not-first:mt-2">
              <Label :for="`${id}-address`">Adresse</Label>
              <Input v-model="form.address" placeholder="Akwa, Douala" required :id="`${id}-address`" />
            </div>

            <div class="flex items-center gap-2">

              <div class="*:not-first:mt-2">
                <Label :for="`${id}-latitude`">Latitude</Label>
                <Input :id="`${id}-latitude`" v-model="form.latitude" type="number" placeholder="4.0511" />
              </div>
              <div class="*:not-first:mt-2">
                <Label :for="`${id}-longitude`">Longitude</Label>
                <Input v-model="form.longitude" type="number" placeholder="9.7049" :id="`${id}-longitude`" />
              </div>

            </div>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox v-model="form.is_active" :id="`${id}-active`" />
            <Label :for="`${id}-active`" class="font-normal">
              {{ form.is_active ? 'Actif' : 'Inactif' }}
            </Label>
          </div>

          <DialogFooter>
            <DialogClose as-child>
              <Button variant="outline">
                Annuler
              </Button>
            </DialogClose>
            <Button type="submit" :disabled="saving">
              <Spinner v-if="saving" />
              {{ saving ? 'Enregistrement...' : (editing ? 'Mettre à jour' : 'Créer') }}
            </Button>
          </DialogFooter>

        </form>
      </DialogContent>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, useId } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Plus, Eye, Pencil, UtensilsCrossed, BadgeCheck,
  BadgeAlert, MapPin
} from 'lucide-vue-next'
import { useToast } from 'vue-toastification'

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Spinner } from '@/components/ui/spinner'

import CopyToCliboard from '@/components/util/CopyToCliboard.vue';
import { restaurantService } from '@/services/restaurant.service'
import { useRestaurantsStore } from '@/stores/restaurants.store';
import { useAuthStore } from '@/stores/auth.store'
import type { Restaurant } from '@/types'
import { format } from 'date-fns'


const id = useId()

const toast = useToast()
const restorantStore = useRestaurantsStore()
const authStore = useAuthStore()

const restaurants = ref<Restaurant[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreate = ref(false)
const editing = ref<Restaurant | null>(null)

const form = reactive({ name: '', address: '', latitude: '', longitude: '', is_active: true })

function fmtDate(v: string) { return format(new Date(v), 'dd/MM/yyyy') }

function openEdit(row: Restaurant) {
  editing.value = row
  form.name = row.name; form.address = row.address
  form.latitude = row.latitude || ''; form.longitude = row.longitude || ''
  form.is_active = row.is_active
  showCreate.value = true
}

// function toggleActive(row: Restaurant) {
//   row.is_active = !row.is_active
//   toast.success(`Restaurant ${row.is_active ? 'activé' : 'désactivé'}`)
// }

async function handleSave() {
  saving.value = true
  try {
    
    if (!editing.value) {
      try {
        const data = await restaurantService.create(form)
        restaurants.value.unshift(data)
        toast.success('Restaurant créé !')
      }
      catch { toast.error("Impossible d'enregistrer un nouveaux restaurants") }
      finally { saving.value = false }
    } else {

      try {
        Object.assign(editing.value, {...form})
        const data = await restaurantService.update(editing.value)
        const idx = restaurants.value.findIndex(r => r.id === editing.value!.id)
        if (idx !== -1) Object.assign(restaurants.value[idx], { name: form.name, address: form.address, is_active: form.is_active })
        toast.success('Restaurant mis à jour !')
      }
      catch { toast.error('Impossible de mettre a jour le restaurants') }
      finally { saving.value = false }
    }

    showCreate.value = false
    editing.value = null
    Object.assign(form, { name: '', address: '', latitude: '', longitude: '', is_active: true })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try { restaurants.value = await restaurantService.list() }
  catch { toast.error('Impossible de charger les restaurants') }
  finally { loading.value = false }
})
</script>

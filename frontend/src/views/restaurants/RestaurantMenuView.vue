<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { restaurantService } from '@/services/restaurant.service'
import { useCartStore } from '@/stores/cart.store'
import { useAuthStore } from '@/stores/auth.store'
import type { Menu, MenuCategory, MenuItem } from '@/types'
import {
  ArrowLeft, Plus, Pencil, Trash2, ShoppingCart, Star,
  ChevronDown, ChevronUp, X, Check, Upload, GripVertical, Tag
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from 'vue-toastification'
import { backendUrl } from '@/services/http'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const authStore = useAuthStore()
const toast = useToast()

const id = route.params.id as string
const menu = ref<Menu | null>(null)
const restaurant = ref<any>(null)
const loading = ref(true)
const saving = ref(false)

// Dialog states
const showItemDialog = ref(false)
const showCategoryDialog = ref(false)
const showConfirmDialog = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmAction = ref<() => Promise<void> | void>(() => {})
const editingCategory = ref<{ index: number; name: string } | null>(null)
const editingItem = ref<{ catIndex: number; itemIndex: number | null } | null>(null)
const newCategoryName = ref('')
const expandedCats = ref<Set<number>>(new Set())

const selectedImages = ref<File[]>([])
const imageInput = ref<HTMLInputElement | null>(null)
const uploadingImages = ref(false)

// Item form
const itemForm = ref({
  name: '', price: 0, description: '', available: true,
  tags: '' as string, calories: '' as string | number,
  options: [] as { label: string; price: number }[]
})

const currentItem = computed(() => {
  if (!menu.value || !editingItem.value) return null
  const { catIndex, itemIndex } = editingItem.value
  if (itemIndex === null) return null
  return menu.value.categories[catIndex].items[itemIndex] as MenuItem
})

const hasExistingItem = computed(() => !!currentItem.value?.id)

// Cart add
const addingToCart = ref<Record<string, boolean>>({})
const selectedOptions = ref<Record<string, { label: string; price: number }[]>>({})

async function load() {
  try {
    loading.value = true
    const [r, m] = await Promise.all([
      restaurantService.get(id),
      restaurantService.getMenu(id).catch(() => ({ restaurant_id: id, categories: [] } as Menu))
    ])
    restaurant.value = r
    menu.value = m
    // Expand all categories by default
    m.categories?.forEach((_: any, i: number) => expandedCats.value.add(i))
  } finally {
    loading.value = false
  }
}

async function saveMenu() {
  if (!menu.value) return
  saving.value = true
  try {
    await restaurantService.updateMenu(id, menu.value)
    toast.success('Menu sauvegarde')
  } catch {
    toast.error('Erreur lors de la sauvegarde')
  } finally {
    saving.value = false
  }
}

function openAddCategory() {
  editingCategory.value = null
  newCategoryName.value = ''
  showCategoryDialog.value = true
}

function openEditCategory(index: number) {
  editingCategory.value = { index, name: menu.value!.categories[index].name }
  newCategoryName.value = menu.value!.categories[index].name
  showCategoryDialog.value = true
}

function saveCategory() {
  if (!newCategoryName.value.trim() || !menu.value) return
  if (editingCategory.value !== null) {
    menu.value.categories[editingCategory.value.index].name = newCategoryName.value.trim()
  } else {
    if (!menu.value.categories) menu.value.categories = []
    menu.value.categories.push({ name: newCategoryName.value.trim(), items: [] })
    expandedCats.value.add(menu.value.categories.length - 1)
  }
  showCategoryDialog.value = false
  saveMenu()
}

function deleteCategory(index: number) {
  menu.value!.categories.splice(index, 1)
  saveMenu()
}

function openAddItem(catIndex: number) {
  editingItem.value = { catIndex, itemIndex: null }
  itemForm.value = { name: '', price: 0, description: '', available: true, tags: '', calories: '', options: [] }
  selectedImages.value = []
  showItemDialog.value = true
}

function openEditItem(catIndex: number, itemIndex: number) {
  editingItem.value = { catIndex, itemIndex }
  const item = menu.value!.categories[catIndex].items[itemIndex]
  itemForm.value = {
    name: item.name,
    price: item.price,
    description: item.description || '',
    available: item.available !== false,
    tags: (item.tags || []).join(', '),
    calories: item.calories || '',
    options: [...(item.options || [])]
  }
  selectedImages.value = []
  showItemDialog.value = true
}

function saveItem() {
  if (!itemForm.value.name || !menu.value) return
  const { catIndex, itemIndex } = editingItem.value!
  const item: MenuItem = {
    name: itemForm.value.name,
    price: Number(itemForm.value.price),
    description: itemForm.value.description,
    available: itemForm.value.available,
    tags: itemForm.value.tags ? itemForm.value.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    calories: itemForm.value.calories ? Number(itemForm.value.calories) : undefined,
    options: itemForm.value.options
  }
  if (itemIndex !== null) {
    const existing = menu.value.categories[catIndex].items[itemIndex]
    menu.value.categories[catIndex].items[itemIndex] = { ...existing, ...item }
  } else {
    menu.value.categories[catIndex].items.push(item)
  }
  selectedImages.value = []
  showItemDialog.value = false
  saveMenu()
}

function confirmDeleteItem(catIndex: number, itemIndex: number) {
  const item = menu.value!.categories[catIndex].items[itemIndex]
  confirmTitle.value = 'Supprimer le plat'
  confirmMessage.value = `Voulez-vous vraiment supprimer "${item.name}" ?`
  confirmAction.value = async () => {
    menu.value!.categories[catIndex].items.splice(itemIndex, 1)
    await saveMenu()
    showConfirmDialog.value = false
  }
  showConfirmDialog.value = true
}

function confirmDeleteCategory(index: number) {
  const category = menu.value!.categories[index]
  confirmTitle.value = 'Supprimer la catégorie'
  confirmMessage.value = `Voulez-vous vraiment supprimer la catégorie "${category.name}" et tous ses plats ?`
  confirmAction.value = async () => {
    menu.value!.categories.splice(index, 1)
    await saveMenu()
    showConfirmDialog.value = false
  }
  showConfirmDialog.value = true
}

function addOption() {
  itemForm.value.options.push({ label: '', price: 0 })
}

function removeOption(i: number) {
  itemForm.value.options.splice(i, 1)
}

function onSelectImages(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files) return
  selectedImages.value = Array.from(target.files)
}

function removeSelectedImage(index: number) {
  selectedImages.value.splice(index, 1)
}

function triggerImageInput() {
  imageInput.value?.click()
}

async function uploadImages() {
  if (!currentItem.value?.id || selectedImages.value.length === 0) return
  uploadingImages.value = true
  try {
    const photos = await restaurantService.uploadItemImages(id, currentItem.value.id, selectedImages.value)
    currentItem.value.photos = photos
    toast.success('Images téléchargées')
    selectedImages.value = []
  } catch {
    toast.error('Impossible de télécharger les images')
  } finally {
    uploadingImages.value = false
  }
}

function getUrlImage(image: File) {
  return URL.createObjectURL(image)
}

function toggleCat(i: number) {
  if (expandedCats.value.has(i)) expandedCats.value.delete(i)
  else expandedCats.value.add(i)
}

async function addToCart(item: MenuItem, catIndex: number, itemIndex: number) {
  const key = `${catIndex}-${itemIndex}`
  addingToCart.value[key] = true
  try {
    await cartStore.addItem({
      restaurant_id: id,
      item_id: item.id || `${catIndex}-${itemIndex}`,
      quantity: 1,
      selected_options: selectedOptions.value[key] || []
    })
    toast.success(`${item.name} ajouté au panier`)
  } catch (e: any) {
    toast.error(e.response?.data?.error || 'Erreur')
  } finally {
    addingToCart.value[key] = false
  }
}

function formatPrice(p: number) {
  return new Intl.NumberFormat('fr-FR').format(p) + ' XAF'
}

onMounted(load)
</script>

<template>
  <div class="space-y-6 max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <Button variant="ghost" size="icon" class="size-9" @click="router.back()">
          <ArrowLeft class="size-4" />
        </Button>
        <div>
          <h1 class="text-xl font-semibold">{{ restaurant?.name || 'Menu' }}</h1>
          <p class="text-sm text-muted-foreground">{{ menu?.categories?.length || 0 }} categorie{{ (menu?.categories?.length || 0) > 1 ? 's' : '' }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button v-if="cartStore.itemsCount > 0" variant="outline" size="sm" @click="router.push({ name: 'cart' })">
          <ShoppingCart class="size-4" />{{ cartStore.itemsCount }}
        </Button>
        <Button v-if="authStore.isAdmin" size="sm" @click="openAddCategory">
          <Plus class="size-4" />Categorie
        </Button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <Skeleton v-for="i in 3" :key="i" class="h-40 w-full rounded-xl" />
    </div>

    <!-- Empty -->
    <div v-else-if="!menu?.categories?.length" class="text-center py-16">
      <div class="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-4">
        <ShoppingCart class="size-8 text-muted-foreground" />
      </div>
      <p class="text-muted-foreground">Menu vide</p>
      <Button v-if="authStore.isAdmin" class="mt-4" @click="openAddCategory">
        <Plus class="size-4" />Ajouter une categorie
      </Button>
    </div>

    <!-- Categories -->
    <div v-else class="space-y-4">
      <Card v-for="(cat, catIndex) in menu.categories" :key="catIndex" class="rounded-[28px] border border-slate-200/70 shadow-sm overflow-hidden">
        <!-- Category header -->
        <div
          class="flex items-center justify-between gap-2 bg-slate-50 px-4 py-3 cursor-pointer transition-colors"
          @click="toggleCat(catIndex)"
        >
          <div class="flex items-center gap-2">
            <component :is="expandedCats.has(catIndex) ? ChevronUp : ChevronDown" class="size-4 text-muted-foreground" />
            <h2 class="font-semibold">{{ cat.name }}</h2>
            <Badge variant="secondary" class="text-xs">{{ cat.items.length }} plat{{ cat.items.length > 1 ? 's' : '' }}</Badge>
          </div>
          <div v-if="authStore.isAdmin" class="flex items-center gap-1" @click.stop>
            <Button size="icon" variant="ghost" class="size-7" @click="openEditCategory(catIndex)">
              <Pencil class="size-3" />
            </Button>
            <Button size="icon" variant="ghost" class="size-7 text-destructive hover:text-destructive" @click="confirmDeleteCategory(catIndex)">
              <Trash2 class="size-3" />
            </Button>
            <Button size="sm" variant="outline" class="h-7 text-xs ml-1" @click="openAddItem(catIndex)">
              <Plus class="size-3" />Plat
            </Button>
          </div>
        </div>

        <Separator />

        <!-- Items -->
        <div v-if="expandedCats.has(catIndex)" class="divide-y">
          <div v-if="!cat.items.length" class="px-4 py-6 text-center text-sm text-muted-foreground">
            Aucun plat dans cette categorie
          </div>
          <div
            v-for="(item, itemIndex) in cat.items" :key="item.id || itemIndex"
            class="flex items-start gap-4 p-4 hover:bg-muted/20 transition-colors"
          >
            <!-- Photo -->
            <div class="w-20 h-20 rounded-lg bg-muted overflow-hidden shrink-0">
              <img v-if="item.photos?.length" :src="backendUrl + item.photos[0]" :alt="item.name" class="w-full h-full object-cover" />
              <div v-else class="w-full h-full flex items-center justify-center text-muted-foreground/40">
                <Tag class="size-6" />
              </div>
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0 space-y-1">
              <div class="flex items-center gap-2">
                <h3 class="font-medium text-sm">{{ item.name }}</h3>
                <Badge v-if="item.available === false" variant="destructive" class="text-xs">Indisponible</Badge>
                <div v-if="(item as any).avg_rating > 0" class="flex items-center gap-0.5">
                  <Star class="size-3 text-yellow-500 fill-yellow-500" />
                  <span class="text-xs text-muted-foreground">{{ Number((item as any).avg_rating).toFixed(1) }}</span>
                </div>
              </div>
              <p v-if="item.description" class="text-xs text-muted-foreground line-clamp-2">{{ item.description }}</p>
              <div v-if="item.tags?.length" class="flex flex-wrap gap-1">
                <Badge v-for="tag in item.tags" :key="tag" variant="outline" class="text-xs h-4 px-1.5">{{ tag }}</Badge>
              </div>
              <div v-if="item.options?.length" class="text-xs text-muted-foreground">
                Options: {{ item.options.map(o => o.label).join(', ') }}
              </div>
            </div>

            <!-- Price + actions -->
            <div class="flex flex-col items-end gap-2 shrink-0">
              <div class="text-right">
                <div v-if="item.promo_price" class="text-xs line-through text-muted-foreground">{{ formatPrice(item.price) }}</div>
                <div class="font-semibold text-sm">{{ formatPrice(item.promo_price || item.price) }}</div>
                <div v-if="item.calories" class="text-xs text-muted-foreground">{{ item.calories }} kcal</div>
              </div>

              <template v-if="authStore.isAdmin">
                <div class="flex gap-1">
                  <Button size="icon" variant="ghost" class="size-7" @click="openEditItem(catIndex, itemIndex)">
                    <Pencil class="size-3" />
                  </Button>
                  <Button size="icon" variant="ghost" class="size-7 text-destructive hover:text-destructive" @click="confirmDeleteItem(catIndex, itemIndex)">
                    <Trash2 class="size-3" />
                  </Button>
                </div>
              </template>
              <template v-else>
                <Button
                  size="sm" class="h-8 text-xs"
                  :disabled="item.available === false || addingToCart[`${catIndex}-${itemIndex}`]"
                  @click="addToCart(item, catIndex, itemIndex)"
                >
                  <ShoppingCart class="size-3" />Ajouter
                </Button>
              </template>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <!-- Dialog: categorie -->
    <Dialog v-model:open="showCategoryDialog">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ editingCategory ? 'Modifier la categorie' : 'Nouvelle categorie' }}</DialogTitle>
        </DialogHeader>
        <div class="py-2">
          <Label>Nom de la categorie</Label>
          <Input v-model="newCategoryName" placeholder="Ex: Plats principaux" class="mt-1.5" @keyup.enter="saveCategory" />
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showCategoryDialog = false">Annuler</Button>
          <Button @click="saveCategory">Enregistrer</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Dialog: plat -->
    <Dialog v-model:open="showItemDialog">
      <DialogContent class="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{{ editingItem?.itemIndex !== null ? 'Modifier le plat' : 'Nouveau plat' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2 space-y-1.5">
              <Label>Nom *</Label>
              <Input v-model="itemForm.name" placeholder="Poulet DG" />
            </div>
            <div class="space-y-1.5">
              <Label>Prix (XAF) *</Label>
              <Input v-model="itemForm.price" type="number" placeholder="3500" />
            </div>
            <div class="space-y-1.5">
              <Label>Calories</Label>
              <Input v-model="itemForm.calories" type="number" placeholder="450" />
            </div>
            <div class="col-span-2 space-y-1.5">
              <Label>Description</Label>
              <Textarea v-model="itemForm.description" placeholder="Description du plat..." rows="2" />
            </div>
            <div class="col-span-2 space-y-1.5">
              <Label>Tags (separés par virgule)</Label>
              <Input v-model="itemForm.tags" placeholder="grille, epice, populaire" />
            </div>
          </div>

          <!-- Image upload -->
          <div class="grid grid-cols-1 gap-4">
            <div class="rounded-2xl border border-slate-200/70 bg-slate-50 p-4">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium">Images du plat</p>
                </div>
                <Button size="sm" variant="outline" class="h-9 text-xs" @click="triggerImageInput">
                  <Upload class="size-4" /> Choisir
                </Button>
              </div>
              <input ref="imageInput" type="file" multiple accept="image/*" class="hidden" @change="onSelectImages" />
              <div class="mt-3 space-y-3">
                <div v-if="selectedImages.length" class="grid grid-cols-3 gap-2">
                  <div v-for="(image, idx) in selectedImages" :key="idx" class="group relative overflow-hidden rounded-2xl border border-slate-200">
                    <img :src="getUrlImage(image)" class="h-24 w-full object-cover" />
                    <Button size="icon" variant="ghost" class="absolute top-2 right-2" @click.prevent="removeSelectedImage(idx)">
                      <X class="size-3" />
                    </Button>
                  </div>
                </div>
                <div v-else class="text-xs text-slate-500">Aucune image sélectionnée.</div>
                <div class="flex flex-wrap gap-2">
                  <span v-if="currentItem?.photos?.length" class="text-xs text-slate-600">Images déjà enregistrées :</span>
                  <img v-for="photo in currentItem?.photos || []" :key="photo" :src="backendUrl + photo" class="h-16 w-16 rounded-xl object-cover border border-slate-200" />
                </div>
                <Button
                  v-if="selectedImages.length"
                  size="sm"
                  variant="secondary"
                  class="h-9 text-xs"
                  :disabled="uploadingImages || !hasExistingItem"
                  @click.prevent="uploadImages"
                >
                  {{ uploadingImages ? 'Téléversement...' : 'Téléverser les images' }}
                </Button>
                <p v-if="selectedImages.length && !hasExistingItem" class="text-xs text-slate-500">Enregistrez le plat d'abord, puis téléchargez les images depuis l'édition.</p>
              </div>
            </div>
          </div>

          <!-- Options -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <Label>Options</Label>
              <Button size="sm" variant="outline" class="h-7 text-xs" @click="addOption">
                <Plus class="size-3" />Option
              </Button>
            </div>
            <div v-for="(opt, i) in itemForm.options" :key="i" class="flex gap-2 items-center">
              <Input v-model="opt.label" placeholder="Ex: Extra sauce" class="flex-1" />
              <Input v-model="opt.price" type="number" placeholder="200" class="w-24" />
              <Button size="icon" variant="ghost" class="size-8 shrink-0" @click="removeOption(i)">
                <X class="size-3" />
              </Button>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <Switch v-model:checked="itemForm.available" />
            <Label>Disponible</Label>
          </div>
        </div>
        <DialogFooter class="flex flex-wrap gap-2 justify-end">
          <Button variant="outline" @click="showItemDialog = false">Annuler</Button>
          <Button @click="saveItem" :disabled="!itemForm.name">Enregistrer</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="showConfirmDialog">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>{{ confirmTitle }}</DialogTitle>
        </DialogHeader>
        <div class="py-3 space-y-3 text-sm text-slate-600">
          <p>{{ confirmMessage }}</p>
        </div>
        <DialogFooter class="flex justify-end gap-2">
          <Button variant="outline" @click="showConfirmDialog = false">Annuler</Button>
          <Button variant="destructive" @click="confirmAction">Supprimer</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

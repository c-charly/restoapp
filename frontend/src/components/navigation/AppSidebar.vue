<script setup lang="ts">
import type { SidebarProps } from '@/components/ui/sidebar'
import {
  Home, UtensilsCrossed, ShoppingCart, ClipboardList,
  User, BarChart3, UserCheck, PieChart, Filter, Search, Globe, Zap, Bell,
  BarChart2
} from 'lucide-vue-next'
import NavMenus from '@/components/navigation/NavMenus.vue'
import NavUser from '@/components/navigation/NavUser.vue'
import {
  Sidebar, SidebarContent, SidebarFooter,
  SidebarHeader, SidebarRail, useSidebar
} from '@/components/ui/sidebar'
import { useAuthStore } from '@/stores/auth.store'
import { useCartStore } from '@/stores/cart.store'
import { computed } from 'vue'

const props = withDefaults(defineProps<SidebarProps>(), { collapsible: 'icon' })
const { open } = useSidebar()
const authStore = useAuthStore()
const cartStore = useCartStore()

const baseMenus = [
  { name: 'Accueil',      url: '/',            icon: Home },
  { name: 'Restaurants',  url: '/restaurants', icon: UtensilsCrossed },
  { name: 'Panier',       url: '/cart',        icon: ShoppingCart },
  { name: 'Commandes',    url: '/orders',      icon: ClipboardList },
  { name: 'Mon profil',   url: '/profile',     icon: User },
  { name: 'Mes Statistiques',   url: '/analytics/me',     icon: BarChart2 },
]

const menus = computed(() => {
  const list = [...baseMenus]
  if (authStore.isAdmin) {
    list.push(
      { name: 'Analytics', url: '/analytics', icon: BarChart3 },
      { name: 'Utilisateurs', url: '/analytics/users', icon: UserCheck },
      { name: 'Segmentation', url: '/analytics/segmentation', icon: PieChart },
      // { name: 'Funnel', url: '/analytics/funnel', icon: Filter },
      // { name: 'Recherches', url: '/analytics/searches', icon: Search },
      { name: 'Pages', url: '/analytics/pages', icon: Globe },
      // { name: 'Live', url: '/analytics/realtime', icon: Zap },
      // { name: 'Alertes', url: '/analytics/alerts', icon: Bell }
    )
  }
  return list
})

const navUser = computed(() => ({
  name: authStore.user ? `${authStore.user.first_name || ''} ${authStore.user.last_name || ''}`.trim() || authStore.user.email : '',
  email: authStore.user?.email || '',
  avatar: '',
}))
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <div class="flex gap-3 items-center px-1">
        <img src="@/assets/logo.png" alt="logo" class="h-8 shrink-0" />
        <span :class="!open ? 'hidden' : ''" class="truncate font-medium text-xs px-1 py-0.5 border border-primary rounded-md">
          Resto App
        </span>
      </div>
    </SidebarHeader>
    <SidebarContent>
      <NavMenus :menus="menus" />
    </SidebarContent>
    <SidebarFooter>
      <NavUser :user="navUser" />
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/navigation/AppSidebar.vue'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { useRoute, RouterView } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

const breadcrumb = computed(() => {
  const map: Record<string, string> = {
    home: 'Accueil',
    restaurants: 'Restaurants',
    'restaurant-detail': 'Detail',
    'restaurant-menu': 'Menu',
    cart: 'Panier',
    orders: 'Commandes',
    'order-detail': 'Commande',
    profile: 'Mon profil',
    analytics: 'Analytics',
  }
  return map[String(route.name)] || ''
})
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset>
      <header class="flex h-14 shrink-0 items-center gap-2 border-b px-4">
        <SidebarTrigger class="-ml-1" />
        <Separator orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4" />
        <span class="text-sm text-muted-foreground">{{ breadcrumb }}</span>
      </header>
      <main class="flex-1 p-6">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>

<style scoped>
.page-enter-active, .page-leave-active { transition: opacity 0.18s, transform 0.18s; }
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
<script setup lang="ts">
import type { LucideIcon } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import {
  SidebarGroup, SidebarGroupLabel, SidebarMenu,
  SidebarMenuButton, SidebarMenuItem, useSidebar,
} from '@/components/ui/sidebar'

const props = defineProps<{
  menus: { name: string; url: string; icon: LucideIcon }[]
}>()

const route = useRoute()
const { isMobile } = useSidebar()

function isActive(url: string) {
  if (url === '/') return route.path === '/'
  return route.path.startsWith(url)
}
</script>

<template>
  <SidebarGroup>
    <SidebarGroupLabel>Navigation</SidebarGroupLabel>
    <SidebarMenu>
      <SidebarMenuItem v-for="item in menus" :key="item.name">
        <SidebarMenuButton
          :tooltip="item.name"
          as-child
          :is-active="isActive(item.url)"
        >
          <RouterLink :to="item.url">
            <component :is="item.icon" />
            <span>{{ item.name }}</span>
          </RouterLink>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  </SidebarGroup>
</template>

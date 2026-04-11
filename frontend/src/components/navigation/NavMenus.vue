<script setup lang="ts">
import type { LucideIcon } from "lucide-vue-next"

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar'

defineProps<{
  menus: {
    name: string
    url: string
    icon: LucideIcon
  }[]
}>()

const { isMobile } = useSidebar()
</script>

<template>
  <SidebarGroup>
    <SidebarGroupLabel>Principal</SidebarGroupLabel>
    <SidebarMenu>
      <SidebarMenuItem v-for="item in menus" :key="item.name">
        <SidebarMenuButton :tooltip="item.name" as-child>
          <a :href="item.url">
            <component :is="item.icon" v-if="item.icon" />
            <span>{{ item.name }}</span>
          </a>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  </SidebarGroup>
</template>

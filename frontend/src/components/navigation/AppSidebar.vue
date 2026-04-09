<script setup lang="ts">
import type { SidebarProps } from '@/components/ui/sidebar'

import {
  Frame,
  PieChart
} from "lucide-vue-next"
import NavMenus from '@/components/navigation/NavMenus.vue'
import NavUser from '@/components/navigation/NavUser.vue'

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  useSidebar
} from '@/components/ui/sidebar'

const props = withDefaults(defineProps<SidebarProps>(), {
  collapsible: "icon",
})

const { open } = useSidebar()

// This is sample data.
const data = {
  user: {
    name: "Charly",
    email: "charly@ccharly.com",
    avatar: "src/assets/logo.png",
  },
  menus: [
    {
      name: "Restaurants",
      url: "#",
      icon: Frame,
    },
    {
      name: "Commandes",
      url: "#",
      icon: PieChart,
    },
  ],
}
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader class="">
      <div
        class="flex gap-3 items-center">
        <img src="@/assets/logo.png" alt="mon logo" class="h-8">
        <span :class="!open ? 'hidden' : ''" class="truncate font-medium text-xs px-1 py-0.5 border border-primary rounded-md">Resto App</span>
      </div>
    </SidebarHeader>
    <SidebarContent>
      <NavMenus :menus="data.menus" />
    </SidebarContent>
    <SidebarFooter>
      <NavUser :user="data.user" />
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>

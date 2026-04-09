import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/components/navigation/AppLayout.vue'),
      children: [
        // home
        { path: '', name: 'home', component: () => import('@/views/home/HomeView.vue') },
      ]
    },
    // { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

export default router

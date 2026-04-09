import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login',    name: 'login',    component: () => import('@/views/auth/LoginView.vue'),    meta: { public: true } },
    { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true } },
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

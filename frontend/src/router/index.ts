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

        // Restaurants
        { path: 'restaurants',             name: 'restaurants',       component: () => import('@/views/restaurants/RestaurantsView.vue') },
        { path: 'restaurants/:id',         name: 'restaurant-detail', component: () => import('@/views/restaurants/RestaurantDetailView.vue') },
        { path: 'restaurants/:id/menu',    name: 'restaurant-menu',   component: () => import('@/views/restaurants/RestaurantMenuView.vue') },
      ]
    },
    // { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

export default router

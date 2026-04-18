import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login',    name: 'login',    component: () => import('@/views/auth/LoginView.vue'),    meta: { public: true } },
    { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/components/navigation/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '',                       name: 'home',              component: () => import('@/views/home/HomeView.vue') },
        { path: 'restaurants',            name: 'restaurants',       component: () => import('@/views/restaurants/RestaurantsView.vue') },
        { path: 'restaurants/:id',        name: 'restaurant-detail', component: () => import('@/views/restaurants/RestaurantDetailView.vue') },
        { path: 'restaurants/:id/menu',   name: 'restaurant-menu',   component: () => import('@/views/restaurants/RestaurantMenuView.vue') },
        { path: 'cart',                   name: 'cart',              component: () => import('@/views/cart/CartView.vue') },
        { path: 'orders',                 name: 'orders',            component: () => import('@/views/orders/OrdersView.vue') },
        { path: 'orders/:id',             name: 'order-detail',      component: () => import('@/views/orders/OrderDetailView.vue') },
        { path: 'profile',                name: 'profile',           component: () => import('@/views/account/ProfileView.vue') },
        
        
        // {
        //   path: 'analytics', name: 'analytics',
        //   component: () => import('@/views/analytics/AnalyticsView.vue'),
        //   meta: { requiresAdmin: true }
        // },

        { path: 'analytics',                   name: 'analytics',              component: () => import('@/views/analytics/AnalyticsPlatformView.vue'), meta: { requiresAdmin: true } },
        { path: 'analytics/users',             name: 'analytics-users',        component: () => import('@/views/analytics/AnalyticsUsersView.vue'), meta: { requiresAdmin: true } },
        { path: 'analytics/users/:userId',     name: 'analytics-user-detail',  component: () => import('@/views/analytics/AnalyticsUserDetailView.vue'), meta: { requiresAdmin: true } },
        // { path: 'analytics/funnel',            name: 'analytics-funnel',       component: () => import('@/views/analytics/AnalyticsFunnelView.vue') },
        { path: 'analytics/pages',             name: 'analytics-pages',        component: () => import('@/views/analytics/AnalyticsPagesView.vue'), meta: { requiresAdmin: true } },
        // { path: 'analytics/searches',          name: 'analytics-searches',     component: () => import('@/views/analytics/AnalyticsSearchesView.vue') },
        { path: 'analytics/segmentation',      name: 'analytics-segmentation', component: () => import('@/views/analytics/AnalyticsSegmentationView.vue'), meta: { requiresAdmin: true } },
        // { path: 'analytics/alerts',            name: 'analytics-alerts',       component: () => import('@/views/analytics/AnalyticsAlertsView.vue') },
        // { path: 'analytics/realtime',          name: 'analytics-realtime',     component: () => import('@/views/analytics/AnalyticsRealtimeView.vue') },
        { path: 'analytics/me',                name: 'analytics-me',           component: () => import('@/views/analytics/AnalyticsMeView.vue')},
      ]
    },

    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'home' }
  }
})

export default router
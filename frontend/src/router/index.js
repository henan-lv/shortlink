import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  // / = landing = login(轮播 + 登录卡) 全屏不滚动
  { path: '/', name: 'landing', component: () => import('@/views/Login.vue'), meta: { public: true, fullBleed: true } },
  { path: '/login', redirect: '/' },
  // 登录后默认页 -> /links(管理页)
  { path: '/links', name: 'links', component: () => import('@/views/Links.vue') },
  { path: '/generate', name: 'generate', component: () => import('@/views/Generate.vue') },
  { path: '/stats', name: 'stats', component: () => import('@/views/Stats.vue') },
  { path: '/stats/:code', name: 'stats-detail', component: () => import('@/views/StatsDetail.vue') },
  { path: '/users', name: 'users', component: () => import('@/views/Users.vue'), meta: { adminOnly: true } },
  { path: '/password/:code', name: 'password', component: () => import('@/views/Password.vue'), meta: { public: true, fullBleed: true } },
  // 其他都走 /links
  { path: '/:pathMatch(.*)*', redirect: '/links' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.bootstrap()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'landing', query: { redirect: to.fullPath } }
  }
})

export default router

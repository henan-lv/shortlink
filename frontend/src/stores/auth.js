import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    bootstrapped: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.user,
    isAdmin: (s) => !!s.user?.is_admin,
  },
  actions: {
    async bootstrap() {
      if (this.bootstrapped) return
      // 刷新页面时服务端 session 还在,内存 user 已丢失
      // 调 /api/auth/me 验证 session,失败则保持未登录
      try {
        const me = await authApi.me()
        this.user = {
          id: me.id,
          username: me.username,
          is_admin: !!me.is_admin,
          is_active: me.is_active !== false,
        }
      } catch (e) {
        // 401 或网络错误,保持未登录
        this.user = null
      }
      this.bootstrapped = true
    },
    async login(username, password) {
      const data = await authApi.login({ username, password })
      this.user = {
        id: data.id,
        username: data.username,
        is_admin: !!data.is_admin,
        is_active: data.is_active !== false,
      }
      return data
    },
    async register(username, password) {
      return authApi.register({ username, password })
    },
    async logout() {
      try {
        await authApi.logout()
      } catch (e) {
        // 忽略服务端错误,客户端清空即可
      }
      this.user = null
    },
  },
})

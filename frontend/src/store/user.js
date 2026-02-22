import { defineStore } from 'pinia'
import { login as apiLogin, logout as apiLogout } from '@/api/user'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('vm_token') || '',
    username: '',
    userId: ''
  }),
  actions: {
    async login(userInfo) {
      const res = await apiLogin(userInfo)
      this.token = res.data.token
      this.username = res.data.user.username
      this.userId = res.data.user.id
      localStorage.setItem('vm_token', this.token)
      return res
    },
    async logout() {
      await apiLogout()
      this.token = ''
      this.username = ''
      this.userId = ''
      localStorage.removeItem('vm_token')
    }
  }
})

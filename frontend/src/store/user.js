import { defineStore } from 'pinia'
import { login as apiLogin, logout as apiLogout } from '@/api/user'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('vm_token') || '',
    username: localStorage.getItem('vm_username') || '',
    userId: localStorage.getItem('vm_user_id') || '',
    role: localStorage.getItem('vm_role') || ''
  }),
  actions: {
    async login(userInfo) {
      const res = await apiLogin(userInfo)
      this.token = res.data.token
      this.username = res.data.user.username
      this.userId = res.data.user.id
      this.role = res.data.user.role || ''
      localStorage.setItem('vm_token', this.token)
      localStorage.setItem('vm_username', this.username)
      localStorage.setItem('vm_user_id', String(this.userId))
      localStorage.setItem('vm_role', this.role)
      return res
    },
    async logout() {
      await apiLogout()
      this.token = ''
      this.username = ''
      this.userId = ''
      this.role = ''
      localStorage.removeItem('vm_token')
      localStorage.removeItem('vm_username')
      localStorage.removeItem('vm_user_id')
      localStorage.removeItem('vm_role')
    }
  }
})

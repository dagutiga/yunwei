import service from './index'

export const login = (userInfo) => {
  return service.post('/login', userInfo)
}

export const logout = () => {
  return service.post('/logout')
}

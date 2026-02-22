import service from './index'

export const login = (userInfo) => {
  return service.post('/login', userInfo)
}

export const logout = () => {
  return service.post('/logout')
}

export const getUsers = () => {
  return service.get('/users')
}

export const createUser = (payload) => {
  return service.post('/users', payload)
}

export const resetUserPassword = (payload) => {
  return service.post('/users/password/reset', payload)
}

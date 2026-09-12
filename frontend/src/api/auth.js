import request from './request'

export const authApi = {
  register(data) {
    return request.post('/api/auth/register', data)
  },
  login(data) {
    return request.post('/api/auth/login', data)
  },
  logout() {
    return request.post('/api/auth/logout')
  },
  me() {
    return request.get('/api/auth/me')
  },
}

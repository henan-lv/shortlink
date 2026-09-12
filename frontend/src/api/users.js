import request from './request'

export const userApi = {
  list() {
    return request.get('/api/admin/users')
  },
  create(data) {
    return request.post('/api/admin/users', data)
  },
  update(id, data) {
    return request.patch(`/api/admin/users/${id}`, data)
  },
  remove(id) {
    return request.delete(`/api/admin/users/${id}`)
  },
  regenerateKey(id) {
    return request.post(`/api/admin/users/${id}/regenerate-key`)
  },
}

import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 15000,
  withCredentials: true,
})

request.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      const err = new Error(body.message || '请求失败')
      err.code = body.code
      err.data = body.data
      throw err
    }
    return body
  },
  (err) => {
    const body = err.response?.data
    const msg = body?.message || err.message || '网络错误'
    const e = new Error(msg)
    e.code = body?.code || err.response?.status || -1
    e.status = err.response?.status

    // session 过期(401)或服务端明确未登录时,跳回登录页
    // 排除已经在 /login 页面或公开接口的请求
    if (e.status === 401 && typeof window !== 'undefined') {
      const path = window.location.pathname
      const isPublic = path === '/' || path.startsWith('/password/')
      if (!isPublic) {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/?redirect=${redirect}`
      }
    }
    throw e
  }
)

export default request

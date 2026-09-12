import request from './request'

export const shortlinkApi = {
  create(data) {
    return request.post('/api/shortlinks', data)
  },
  // 全站总览聚合(后端真实 SUM/COUNT,修复「100 条前端求和」的口径)
  getOverview(params = {}) {
    return request.get('/api/stats/overview', { params })
  },
  // 异常雷达:临期 / 高拦截 / 僵尸 / 触达上限
  getOverviewAlerts(params = {}) {
    return request.get('/api/stats/overview/alerts', { params })
  },
  // 总览 · 跨链接点击趋势(F2.1 总览维度)
  getOverviewTrend(params = {}) {
    return request.get('/api/stats/overview/trend', { params })
  },
  // 总览 · 跨链接来源 / 设备 / 系统 / 浏览器 / 地理(F2.2-F2.4 总览维度)
  getOverviewBreakdown(params = {}) {
    return request.get('/api/stats/overview/breakdown', { params })
  },
  // 总览 · 跨链接最近窗口实时(F2.6 总览维度)
  getOverviewRealtime(params = {}) {
    return request.get('/api/stats/overview/realtime', { params })
  },
  getStats(code) {
    return request.get(`/api/shortlinks/${code}/stats`)
  },
  // F2.1 点击趋势
  getTrend(code, params = {}) {
    return request.get(`/api/shortlinks/${code}/trend`, { params })
  },
  // F2.2/F2.3/F2.4 分类(来源分类 / 设备 / 系统 / 浏览器 / 地理)
  getBreakdown(code, params = {}) {
    return request.get(`/api/shortlinks/${code}/breakdown`, { params })
  },
  // F2.6 实时统计
  getRealtime(code, params = {}) {
    return request.get(`/api/shortlinks/${code}/realtime`, { params })
  },
  // F2.7 导出报表(直接返回 text/csv 流)
  exportClicks(code, params = {}) {
    return request.get(`/api/shortlinks/${code}/export`, {
      params,
      responseType: 'blob',
    })
  },
  // 访问来源聚合(IP / UA / Referer),用于统计页"看见是谁在访问"
  getVisitors(code, params = {}) {
    return request.get(`/api/shortlinks/${code}/visitors`, { params })
  },
  verifyPassword(code, password) {
    return request.post(`/api/shortlinks/${code}/verify-password`, { password })
  },
  list(params = {}) {
    return request.get('/api/links', { params })
  },
  getOne(code) {
    return request.get(`/api/links/${code}`)
  },
  remove(code) {
    return request.delete(`/api/links/${code}`)
  },
  // 从回收站恢复(撤销软删)
  restore(code) {
    return request.post(`/api/links/${code}/restore`)
  },
  patch(code, data) {
    return request.patch(`/api/links/${code}`, data)
  },
}

// 访问控制规则(风控)
export const accessRuleApi = {
  list(params = {}) {
    return request.get('/api/access-rules', { params })
  },
  create(data) {
    return request.post('/api/access-rules', data)
  },
  setEnabled(id, enabled) {
    return request.patch(`/api/access-rules/${id}`, { enabled })
  },
  remove(id) {
    return request.delete(`/api/access-rules/${id}`)
  },
}

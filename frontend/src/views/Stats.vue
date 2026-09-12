<template>
  <div class="page">
    <header class="page-head">
      <div class="head-row">
        <div>          <h2>统计总览</h2>
        </div>
        <div class="head-range">
          <span class="range-label">时间窗口</span>
          <div class="seg mini-seg">
            <button v-for="r in ranges" :key="r.value" type="button" class="seg-btn"
                    :class="{ 'is-active': days === r.value }"
                    @click="switchDays(r.value)">{{ r.label }}</button>
          </div>
        </div>
      </div>
      <p class="page-sub">近 {{ days }} 天的访问数据；总 UV 已跨链接去重；多维度对比看大盘走势与风险</p>
    </header>

    <div v-if="loading" class="glass-card">
      <div class="loading-state"><span class="dot-pulse"></span>正在加载数据…</div>
    </div>
    <div v-else-if="errorMsg" class="glass-card error-card">{{ errorMsg }}</div>
    <template v-else>
      <!-- ===== 5 张 KPI ===== -->
      <div class="stat-grid">
        <div class="glass-card stat" data-tone="cyan">
          <div class="stat-top">
            <span class="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none"><path d="M2 11l3-3 3 2 5-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="13" cy="4" r="1" fill="currentColor"/></svg>
            </span>
            <span class="stat-label">总 PV</span>
          </div>
          <div class="stat-value">{{ summary.pv }}</div>
          <div class="stat-foot">近 {{ days }} 天访问量</div>
        </div>
        <div class="glass-card stat" data-tone="green">
          <div class="stat-top">
            <span class="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none"><circle cx="6" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M2 14c0-2.2 1.8-4 4-4s4 1.8 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="12" cy="5" r="2" stroke="currentColor" stroke-width="1.2"/></svg>
            </span>
            <span class="stat-label">总 UV</span>
          </div>
          <div class="stat-value">{{ summary.uv }}</div>
          <div class="stat-foot">跨链接去重的独立访客</div>
        </div>
        <div class="glass-card stat" data-tone="blue">
          <div class="stat-top">
            <span class="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none"><rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M2 7h12" stroke="currentColor" stroke-width="1.4"/><path d="M5 10h2M9 10h2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
            </span>
            <span class="stat-label">平均 PV / 链接</span>
          </div>
          <div class="stat-value">{{ summary.avgPv }}</div>
          <div class="stat-foot">单条链接的平均访问量</div>
        </div>
        <div class="glass-card stat" data-tone="violet">
          <div class="stat-top">
            <span class="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none"><path d="M8 1.5l1.6 4.6 4.9.3-3.7 3.1 1.2 4.7L8 11.9l-4 2.3 1.2-4.7L1.5 6.4l4.9-.3z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>
            </span>
            <span class="stat-label">健康占比</span>
          </div>
          <div class="stat-value">
            {{ Math.round(summary.healthyRatio * 100) }}<span class="stat-unit">%</span>
          </div>
          <div class="stat-foot">{{ summary.enabled }} / {{ summary.total }} 链接启用中</div>
        </div>
        <div class="glass-card stat" data-tone="amber">
          <div class="stat-top">
            <span class="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none"><path d="M3 5h10l-1 8a1.5 1.5 0 01-1.5 1.4h-5A1.5 1.5 0 014 13z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 5V3.5a2 2 0 014 0V5" stroke="currentColor" stroke-width="1.4"/></svg>
            </span>
            <span class="stat-label">回收站</span>
          </div>
          <div class="stat-value">{{ summary.deleted }}</div>
          <div class="stat-foot">已删除,可恢复</div>
        </div>
      </div>

      <!-- ===== 异常雷达 ===== -->
      <div class="glass-card radar-card">
        <div class="radar-head">
          <h3>异常雷达</h3>
          <p class="radar-sub">一句话告诉你哪里出了问题 · 近 {{ days }} 天</p>
        </div>
        <div class="radar-grid">
          <div v-for="bucket in alertBuckets" :key="bucket.key" class="radar-cell" :data-tone="bucket.tone">
            <div class="radar-cell-head">
              <span class="radar-icon" v-html="bucket.icon"></span>
              <span class="radar-cell-label">{{ bucket.label }}</span>
              <span class="radar-cell-count" :class="{ 'is-zero': bucket.items.length === 0 }">
                {{ bucket.items.length }}
              </span>
            </div>
            <ul v-if="bucket.items.length" class="radar-list">
              <li v-for="it in bucket.items.slice(0, 3)" :key="it.id || it.short_code" class="radar-item">
                <button class="radar-link" @click="goStats(it.short_code)" :title="it.long_url">
                  <code>{{ it.short_code }}</code>
                  <span class="radar-meta">{{ bucket.metaOf(it) }}</span>
                </button>
              </li>
            </ul>
            <div v-else class="radar-empty">{{ bucket.emptyText }}</div>
          </div>
        </div>
      </div>

      <!-- ===== 三列 Top 对比 ===== -->
      <div class="top-row">
        <div class="glass-card top-card" v-for="col in topCols" :key="col.key">
          <div class="top-head">
            <h3>{{ col.label }}</h3>
          </div>
          <table v-if="col.rows.length">
            <thead>
              <tr>
                <th>#</th>
                <th>短码</th>
                <th>{{ col.valueLabel }}</th>
                <th>长链</th>
                <th>最后访问</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in col.rows.slice(0, 10)" :key="row.short_code"
                  class="top-row-clickable" @click="goStats(row.short_code)">
                <td class="rank-cell"><span class="rank-num">{{ String(i + 1).padStart(2, '0') }}</span></td>
                <td class="url-cell"><code>{{ row.short_code }}</code></td>
                <td class="pv-cell"><b class="pv-num">{{ row.value }}</b></td>
                <td class="url-cell" :title="row.long_url">{{ row.long_url || '—' }}</td>
                <td class="time-cell">{{ formatShortTime(row.last_visit_at) }}</td>
                <td class="op-cell"><span class="row-arrow">→</span></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty">{{ col.emptyText }}</div>
        </div>
      </div>

      <!-- ===== 趋势图 + 来源分布 + 实时窗口 ===== -->
      <div class="insight-row">
      <!-- 上面一行:趋势图(整宽) -->
      <div class="glass-card trend-card">
        <div class="trend-head">
          <h3 class="trend-title">点击趋势</h3>
          <div class="seg mini-seg trend-seg">
            <button v-for="g in trendGranularities" :key="g.value" type="button" class="seg-btn"
                    :class="{ 'is-active': granularity === g.value }"
                    :disabled="trendDisabled(g.value)"
                    @click="switchGranularity(g.value)">{{ g.label }}</button>
          </div>
        </div>
        <div v-if="trendLoading" class="loading-state"><span class="dot-pulse"></span>加载趋势…</div>
        <div v-else-if="!trendPoints.length" class="empty">窗口内还没有点击数据</div>
        <v-chart v-else class="trend-chart" :option="trendOption" autoresize></v-chart>
      </div>

      <!-- 下面一行:访问构成 + 实时窗口(等宽等高) -->
      <div class="bd-rt-row">
        <div class="glass-card bd-card">
          <div class="bd-head">
            <h3 class="bd-title">访问构成</h3>
            <div class="seg mini-seg bd-seg">
              <button v-for="d in breakdownDims" :key="d.value" type="button" class="seg-btn"
                      :class="{ 'is-active': breakdownDim === d.value }"
                      @click="switchBreakdownDim(d.value)">{{ d.label }}</button>
            </div>
          </div>
          <div v-if="breakdownLoading" class="loading-state"><span class="dot-pulse"></span>加载构成…</div>
          <div v-else-if="!breakdownItems.length" class="bd-empty-state">
            <div class="bd-empty-icon">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <circle cx="14" cy="14" r="12" stroke="currentColor" stroke-width="1.4" stroke-dasharray="3 4" opacity="0.4"/>
                <path d="M9 14h10M14 9v10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" opacity="0.7"/>
              </svg>
            </div>
            <p>近 {{ days }} 天暂无 {{ bdActiveLabel }} 数据</p>
          </div>
          <div v-else class="bd-list">
            <div v-for="(it, idx) in breakdownItems" :key="it.value" class="bd-row">
              <span class="bd-rank">{{ String(idx + 1).padStart(2, '0') }}</span>
              <span class="bd-label" :title="it.value">{{ it.value }}</span>
              <span class="bd-bar"><i :style="{ width: Math.max(4, it.ratio * 100) + '%' }"></i></span>
              <span class="bd-meta">
                <b>{{ it.pv }}</b>
                <span class="dim">{{ (it.ratio * 100).toFixed(1) }}%</span>
              </span>
            </div>
          </div>
        </div>

        <div class="glass-card rt-card">
          <div class="rt-head">
            <h3 class="rt-title">实时窗口</h3>
            <div class="rt-stat">
              <span class="rt-dot" :class="{ 'is-active': realtime.count > 0 }"></span>
              <span class="rt-num">{{ realtime.count }}</span>
              <span class="rt-unit">次 / 30min</span>
            </div>
          </div>

          <!-- 空状态:整卡一个优雅提示 -->
          <div v-if="!realtime.count && !realtime.latest?.length" class="rt-empty">
            <div class="rt-empty-visual">
              <span class="rt-empty-ring"></span>
              <span class="rt-empty-ring rt-empty-ring-2"></span>
              <span class="rt-empty-core">
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                  <path d="M11 3v3M11 16v3M3 11h3M16 11h3M5.6 5.6l2.1 2.1M14.3 14.3l2.1 2.1M5.6 16.4l2.1-2.1M14.3 7.7l2.1-2.1"
                        stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
                  <circle cx="11" cy="11" r="2.2" fill="currentColor" opacity="0.85"/>
                </svg>
              </span>
            </div>
            <p class="rt-empty-title">一切安静</p>
            <p class="rt-empty-sub">最近 30 分钟还没有人访问 · 数据每 30 秒自动刷新</p>
          </div>

          <!-- 有数据:两列紧凑布局 -->
          <div v-else class="rt-body">
            <section class="rt-col">
              <div class="rt-section-head">当前最热</div>
              <ul v-if="realtime.top_links.length" class="rt-top-list">
                <li v-for="(row, i) in realtime.top_links" :key="row.short_code">
                  <span class="rt-rank">{{ i + 1 }}</span>
                  <button class="rt-link" @click="goStats(row.short_code)" :title="row.short_code">
                    <code>{{ row.short_code }}</code>
                  </button>
                  <span class="rt-pv">{{ row.pv }}</span>
                </li>
              </ul>
              <div v-else class="rt-empty-mini">暂无热点</div>
            </section>
            <section class="rt-col">
              <div class="rt-section-head">最近活动</div>
              <ul v-if="realtime.latest.length" class="rt-stream-list">
                <li v-for="(it, i) in realtime.latest" :key="i" class="rt-stream-row">
                  <code class="rt-stream-code">{{ it.short_code }}</code>
                  <span class="rt-stream-meta">
                    <span class="rt-stream-dev">{{ it.device }} · {{ it.browser }}</span>
                    <span class="rt-stream-time">{{ formatRelative(it.clicked_at) }}</span>
                  </span>
                </li>
              </ul>
              <div v-else class="rt-empty-mini">暂无新活动</div>
            </section>
          </div>
        </div>
      </div>
      </div>

      <!-- ===== 全期累计 PV Top 10(独立,与三列 Top 对齐) ===== -->
      <div class="glass-card top-card top-card-legacy">
        <div class="top-head">
          <h3>全期累计 PV Top 10</h3>
        </div>
        <table v-if="topLegacy.length">
          <thead>
            <tr>
              <th>#</th>
              <th>短码</th>
              <th>PV / UV</th>
              <th>长链</th>
              <th>最后访问</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in topLegacy" :key="row.id" class="top-row-clickable" @click="goStats(row.short_code)">
              <td class="rank-cell"><span class="rank-num">{{ String(i + 1).padStart(2, '0') }}</span></td>
              <td class="url-cell"><code>{{ row.short_code }}</code></td>
              <td class="pv-cell">
                <span class="pv-num">{{ row.pv }}</span><span class="pv-sep">/</span><span class="pv-uv">{{ row.uv ?? 0 }}</span>
              </td>
              <td class="url-cell" :title="row.long_url">{{ row.long_url || '—' }}</td>
              <td class="time-cell">{{ formatShortTime(row.last_visit_at) }}</td>
              <td class="op-cell"><span class="row-arrow">→</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">
          还没有数据，去 <router-link to="/generate" class="empty-link">生成短链</router-link> 试试
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, watch, ref } from 'vue'
import { useRouter } from 'vue-router'
import { shortlinkApi } from '@/api/shortlink'
import VChart from 'vue-echarts'
import { use as echartsUse } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'

echartsUse([
  CanvasRenderer, LineChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
])

const router = useRouter()

const ranges = [
  { value: 1, label: '24h' },
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
]
const days = ref(7)
const granularity = ref('day')

const trendGranularities = computed(() => {
  // hour 维度对长窗口无意义,只在天数 <= 7 时启用
  const out = [{ value: 'day', label: '按天' }]
  if (days.value <= 7) out.unshift({ value: 'hour', label: '按小时' })
  return out
})
function trendDisabled(v) {
  return v === 'hour' && days.value > 7
}
function switchGranularity(v) {
  if (granularity.value === v) return
  granularity.value = v
  fetchTrend()
}

const trend = ref({ points: [], total_pv: 0, total_uv: 0, granularity: 'day' })
const trendLoading = ref(false)

const breakdownDims = [
  { value: 'device', label: '设备' },
  { value: 'browser', label: '浏览器' },
  { value: 'referer_type', label: '来源' },
]
const breakdownDim = ref('device')
const breakdownItems = ref([])
const breakdownTotal = ref(0)
const breakdownLoading = ref(false)

const realtime = ref({ count: 0, top_links: [], latest: [], window_minutes: 30 })


// 当前选中的 breakdown 维度中文名,空状态用得上
const bdActiveLabel = computed(() => {
  const map = { device: '设备', browser: '浏览器', referer_type: '来源', os: '系统', geo: '地理' }
  return map[breakdownDim.value] || ''
})

const breakdownMap = computed(() => {
  const max = breakdownItems.value.reduce((m, it) => Math.max(m, it.pv), 0) || 1
  return breakdownItems.value.map(it => ({ ...it, _pct: it.pv / max }))
})

const summary = ref({
  total: 0,
  enabled: 0,
  deleted: 0,
  pv: 0,
  uv: 0,
  healthyRatio: 0,
  avgPv: 0,
  blockedTotal: 0,
})

const topPv = ref([])
const topUv = ref([])
const topBlocked = ref([])
const topLegacy = ref([])

const alerts = ref({
  summary: { expiring: 0, high_block: 0, zombie: 0, near_cap: 0 },
  expiring: [],
  high_block: [],
  zombie: [],
  near_cap: [],
})

const loading = ref(true)
const errorMsg = ref('')

// 时间窗口切换时同时刷 overview + alerts
function switchDays(v) {
  if (days.value === v) return
  days.value = v
  fetchAll()
}

// 异常雷达 4 个分类桶
const alertBuckets = computed(() => [
  {
    key: 'expiring',
    label: '临期过期',
    tone: 'amber',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.3"/><path d="M7 4v3.2l2 1.3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>',
    items: alerts.value.expiring,
    emptyText: '未来 7 天内没有要过期的链接',
    metaOf: (it) => `${formatDate(it.expire_at)} 到期`,
  },
  {
    key: 'high_block',
    label: '集中拦截',
    tone: 'red',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5l5 2v3.5c0 2.6-2 4.7-5 5.5-3-.8-5-2.9-5-5.5V3.5l5-2z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M5 7l1.6 1.6L9.5 5.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    items: alerts.value.high_block,
    emptyText: `近 ${days.value} 天没有高频拦截`,
    metaOf: (it) => `拦截 ${it.blocked_count} 次`,
  },
  {
    key: 'zombie',
    label: '僵尸链接',
    tone: 'violet',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="2" y="2" width="10" height="10" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M5 6h4M5 8h4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>',
    items: alerts.value.zombie,
    emptyText: '30 天以上没访问的启用链接: 0',
    metaOf: (it) => it.last_visit_at ? `最后访问 ${formatDate(it.last_visit_at)}` : '从未访问',
  },
  {
    key: 'near_cap',
    label: '触达上限',
    tone: 'cyan',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5v8M3.5 5.5L7 9l3.5-3.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/><path d="M2.5 12h9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>',
    items: alerts.value.near_cap,
    emptyText: '没有接近点击上限的链接',
    metaOf: (it) => `${it.pv} / ${it.click_limit}`,
  },
])

// 三列 Top 对比
const topCols = computed(() => [
  {
    key: 'pv',
    label: 'Top 10 PV',
    valueLabel: 'PV',
    rows: topPv.value,
    emptyText: '窗口内还没有 PV 数据',
  },
  {
    key: 'uv',
    label: 'Top 10 UV',
    valueLabel: 'UV',
    rows: topUv.value,
    emptyText: '窗口内还没有 UV 数据',
  },
  {
    key: 'blocked',
    label: 'Top 10 拦截',
    valueLabel: '拦截',
    rows: topBlocked.value,
    emptyText: '窗口内没有拦截记录',
  },
])

function goStats(code) {
  router.push(`/stats/${code}`)
}

function formatTime(s) {
  if (!s) return '-'
  return new Date(s).toLocaleString()
}
function formatShortTime(s) {
  if (!s) return '—'
  const d = new Date(s)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
function formatDate(s) {
  if (!s) return '-'
  return new Date(s).toLocaleDateString()
}


async function fetchTrend() {
  trendLoading.value = true
  try {
    const r = await shortlinkApi.getOverviewTrend({ days: days.value, granularity: granularity.value })
    trend.value = r || { points: [], total_pv: 0, total_uv: 0 }
  } catch (_) {
    trend.value = { points: [], total_pv: 0, total_uv: 0 }
  } finally {
    trendLoading.value = false
  }
}

async function fetchBreakdown() {
  breakdownLoading.value = true
  try {
    const r = await shortlinkApi.getOverviewBreakdown({ by: breakdownDim.value, days: days.value })
    breakdownItems.value = r?.items || []
    breakdownTotal.value = r?.total || 0
  } catch (_) {
    breakdownItems.value = []
    breakdownTotal.value = 0
  } finally {
    breakdownLoading.value = false
  }
}

function switchBreakdownDim(v) {
  if (breakdownDim.value === v) return
  breakdownDim.value = v
  fetchBreakdown()
}

async function fetchRealtime() {
  try {
    const r = await shortlinkApi.getOverviewRealtime({ minutes: 30 })
    realtime.value = r || { count: 0, top_links: [], latest: [], window_minutes: 30 }
  } catch (_) {
    realtime.value = { count: 0, top_links: [], latest: [], window_minutes: 30 }
  }
}

const trendPoints = computed(() => trend.value.points || [])
const trendOption = computed(() => buildTrendOption(trendPoints.value, granularity.value))

function buildTrendOption(points, gran) {
  const xs = points.map(p => p.t)
  const pv = points.map(p => p.pv)
  const uv = points.map(p => p.uv)
  return {
    backgroundColor: 'transparent',
    grid: { left: 38, right: 18, top: 26, bottom: 26 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11,11,16,0.92)',
      borderColor: 'rgba(96,165,250,0.28)',
      textStyle: { color: '#E2E8F0', fontSize: 11 },
      formatter: (params) => {
        const t = params[0]?.axisValue || ''
        const lines = params.map(p =>
          `<div style="display:flex;justify-content:space-between;gap:10px"><span style="color:${p.color}">${p.seriesName}</span><b>${p.value}</b></div>`
        ).join('')
        return `<div style="font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;color:#94A3B8;margin-bottom:4px">${t}</div>${lines}`
      },
    },
    legend: {
      data: ['PV', 'UV'],
      textStyle: { color: '#94A3B8', fontSize: 10, fontFamily: 'var(--font-mono)' },
      icon: 'roundRect',
      itemWidth: 10, itemHeight: 4,
      top: 0, right: 4,
    },
    xAxis: {
      type: 'category', data: xs, boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(96,165,250,0.18)' } },
      axisLabel: {
        color: '#94A3B8', fontSize: 9, fontFamily: 'var(--font-mono)',
        formatter: (v) => {
          if (gran === 'hour') return v.slice(11, 16)
          return v.slice(5)
        },
        hideOverlap: true,
      },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(96,165,250,0.08)' } },
      axisLabel: { color: '#94A3B8', fontSize: 9, fontFamily: 'var(--font-mono)' },
    },
    series: [
      {
        name: 'PV', type: 'line', data: pv, smooth: true,
        showSymbol: false, symbolSize: 4,
        lineStyle: { color: '#60A5FA', width: 2 },
        itemStyle: { color: '#60A5FA' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(96,165,250,0.35)' },
              { offset: 1, color: 'rgba(96,165,250,0.0)' },
            ],
          },
        },
      },
      {
        name: 'UV', type: 'line', data: uv, smooth: true,
        showSymbol: false, symbolSize: 4,
        lineStyle: { color: '#67E8F9', width: 2 },
        itemStyle: { color: '#67E8F9' },
      },
    ],
  }
}

function formatRelative(s) {
  if (!s) return '-'
  const t = new Date(s).getTime()
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return Math.floor(diff / 60_000) + ' 分钟前'
  if (diff < 86400_000) return Math.floor(diff / 3600_000) + ' 小时前'
  return Math.floor(diff / 86400_000) + ' 天前'
}

async function fetchAll() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [ov, al, _tr, _bd, _rt] = await Promise.all([
      shortlinkApi.getOverview({ days: days.value }),
      shortlinkApi.getOverviewAlerts({ days: days.value }),
      fetchTrend(),
      fetchBreakdown(),
      fetchRealtime(),
    ])
    summary.value = {
      total: ov.total ?? 0,
      enabled: ov.enabled ?? 0,
      deleted: ov.deleted ?? 0,
      pv: ov.pv ?? 0,
      uv: ov.uv ?? 0,
      healthyRatio: ov.healthy_ratio ?? 0,
      avgPv: ov.avg_pv_per_link ?? 0,
      blockedTotal: ov.blocked_total ?? 0,
    }
    topPv.value = ov.top_pv || []
    topUv.value = ov.top_uv || []
    topBlocked.value = ov.top_blocked || []
    topLegacy.value = ov.top || []
    alerts.value = {
      summary: al.summary || { expiring: 0, high_block: 0, zombie: 0, near_cap: 0 },
      expiring: al.expiring || [],
      high_block: al.high_block || [],
      zombie: al.zombie || [],
      near_cap: al.near_cap || [],
    }
  } catch (e) {
    errorMsg.value = '加载失败:' + e.message
  } finally {
    loading.value = false
  }
}

onMounted(fetchAll)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 22px; }
.page-head { display: flex; flex-direction: column; gap: 4px; }
.page-head h2 { margin: 0; padding-left: 14px; }
.page-eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.24em;
  color: rgba(103, 232, 249, 0.7);
  margin-bottom: 2px;
}
.page-sub {
  margin: 0;
  padding-left: 14px;
  color: var(--text-muted);
  font-size: 13px;
}
.head-row {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
}
.head-range { display: flex; align-items: center; gap: 10px; }
.range-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--text-dim);
  text-transform: uppercase;
}

.glass-card {
  position: relative;
  background:
    linear-gradient(180deg, rgba(30, 30, 35, 0.78), rgba(20, 20, 28, 0.78)) padding-box,
    linear-gradient(135deg, rgba(96, 165, 250, 0.45), rgba(103, 232, 249, 0.18) 60%, rgba(139, 92, 246, 0.32)) border-box;
  border: 1px solid transparent;
  border-radius: 20px;
  padding: 22px;
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  box-shadow:
    0 0 0 1px rgba(59, 130, 246, 0.08),
    0 18px 48px -16px rgba(0, 0, 0, 0.65),
    0 0 64px -24px rgba(59, 130, 246, 0.35);
}
.error-card { border-color: rgba(239, 68, 68, 0.35); color: #FCA5A5; }
.loading-state {
  display: flex; align-items: center; gap: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 13px;
  padding: 12px 4px;
}
.dot-pulse {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #67E8F9;
  box-shadow: 0 0 8px #67E8F9;
  animation: pulse-glow 1s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { opacity: 0.4; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* ===== KPI 网格(5 张)— 重设计:左侧 accent bar + 顶部 icon/label ===== */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}
.stat {
  position: relative;
  padding: 18px 20px 16px;
  overflow: hidden;
  isolation: isolate;
}
/* 顶部 accent bar(色相由 tone 决定,宽度很细) */
.stat::before {
  content: '';
  position: absolute;
  top: 0; left: 14px; right: 14px;
  height: 1px;
  background: linear-gradient(90deg, var(--stat-accent, rgba(148,163,184,0.3)), transparent);
  opacity: 0.85;
}
/* 右上角柔和 glow(单色低饱和) */
.stat::after {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(circle 220px at 100% 0%, var(--stat-glow, transparent), transparent 70%);
  pointer-events: none;
  opacity: 0.55;
  z-index: -1;
}
.stat[data-tone="cyan"]   { --stat-accent: #67E8F9; --stat-glow: rgba(34, 211, 238, 0.18); }
.stat[data-tone="green"]  { --stat-accent: #6EE7B7; --stat-glow: rgba(16, 185, 129, 0.16); }
.stat[data-tone="blue"]   { --stat-accent: #93C5FD; --stat-glow: rgba(96, 165, 250, 0.18); }
.stat[data-tone="violet"] { --stat-accent: #C4B5FD; --stat-glow: rgba(139, 92, 246, 0.18); }
.stat[data-tone="amber"]  { --stat-accent: #FBBF24; --stat-glow: rgba(251, 191, 36, 0.16); }

.stat-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--stat-accent);
  opacity: 0.95;
}
.stat-label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--text-muted);
}
.stat-value {
  font-family: var(--font-sans);
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #F1F5F9;
  font-variant-numeric: tabular-nums;
  line-height: 1.05;
  text-shadow: 0 0 28px var(--stat-glow, transparent);
}
.stat-unit {
  font-size: 18px;
  color: var(--text-muted);
  margin-left: 3px;
  font-weight: 500;
}
.stat[data-tone="cyan"]   .stat-value { color: #E0FAFF; }
.stat[data-tone="green"]  .stat-value { color: #D1FAE5; }
.stat[data-tone="blue"]   .stat-value { color: #DBEAFE; }
.stat[data-tone="violet"] .stat-value { color: #EDE9FE; }
.stat[data-tone="amber"]  .stat-value { color: #FEF3C7; }
/* 数值用同色调浅色,色调统一不打架,通过 icon + accent bar 区分语义 */
.stat-foot {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  font-size: 11px;
  color: rgba(148, 163, 184, 0.7);
  line-height: 1.4;
}

/* ===== 异常雷达 ===== */
.radar-card { display: flex; flex-direction: column; gap: 16px; }
.radar-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.radar-head h3 { margin: 0; font-size: 18px; letter-spacing: -0.01em; }
.radar-sub {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
}
.radar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.radar-cell {
  padding: 14px 16px;
  background: rgba(11, 11, 16, 0.45);
  border: 1px solid rgba(96, 165, 250, 0.14);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 160px;
}
.radar-cell[data-tone="amber"]  { border-color: rgba(251, 191, 36, 0.30); }
.radar-cell[data-tone="red"]    { border-color: rgba(239, 68, 68, 0.30); }
.radar-cell[data-tone="violet"] { border-color: rgba(139, 92, 246, 0.30); }
.radar-cell[data-tone="cyan"]   { border-color: rgba(34, 211, 238, 0.30); }
.radar-cell-head {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono);
}
.radar-cell[data-tone="amber"]  .radar-cell-head { color: #FBBF24; }
.radar-cell[data-tone="red"]    .radar-cell-head { color: #FCA5A5; }
.radar-cell[data-tone="violet"] .radar-cell-head { color: #C4B5FD; }
.radar-cell[data-tone="cyan"]   .radar-cell-head { color: #67E8F9; }
.radar-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
}
.radar-cell-label {
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.radar-cell-count {
  margin-left: auto;
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.radar-cell-count.is-zero { color: var(--text-dim); opacity: 0.6; }
.radar-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex; flex-direction: column; gap: 4px;
}
.radar-item { line-height: 1; }
.radar-link {
  display: flex; align-items: center; gap: 8px;
  width: 100%;
  padding: 5px 8px;
  background: transparent;
  border: 1px solid rgba(96, 165, 250, 0.10);
  border-radius: 6px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 11px;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--t-fast), background var(--t-fast);
}
.radar-link:hover {
  border-color: rgba(96, 165, 250, 0.4);
  background: rgba(96, 165, 250, 0.06);
}
.radar-link code { color: #67E8F9; font-size: 11px; }
.radar-meta {
  margin-left: auto;
  color: var(--text-dim);
  font-size: 10.5px;
}
.radar-empty {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-dim);
  padding: 4px 0;
  line-height: 1.5;
}

/* ===== Top 三列 ===== */
.top-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}
.top-card { display: flex; flex-direction: column; gap: 14px; }
.top-head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 10px;
}
.top-head h3 {
  margin: 0;
  font-size: 15px;
  letter-spacing: 0;
}
.top-tag {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  color: rgba(103, 232, 249, 0.7);
}
.top-card table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  table-layout: fixed;
}
.top-card th {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-dim);
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.10);
}
.top-card td {
  font-size: 12px;
  padding: 9px 10px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.06);
  color: var(--text);
}
.top-card tr.top-row-clickable { cursor: pointer; transition: background 0.15s ease; }
.top-row-clickable:hover td { background: rgba(96, 165, 250, 0.06); }
.rank-cell { width: 36px; }
.rank-num {
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 0.06em;
}
.url-cell {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.url-cell code { color: #67E8F9; }
.pv-cell {
  text-align: center;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}
.pv-num { color: var(--text); font-weight: 600; }
.pv-sep { color: var(--text-dim); margin: 0 3px; }
.pv-uv { color: var(--text-muted); }
.time-cell {
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  text-align: right;
  padding-right: 18px !important;
}
.op-cell {
  width: 28px;
  text-align: center;
  color: var(--text-dim);
  padding-left: 6px !important;
  padding-right: 6px !important;
}
.row-arrow {
  display: inline-block;
  transition: transform 0.15s ease, color 0.15s ease;
}
.top-row-clickable:hover .row-arrow {
  color: #67E8F9;
  transform: translateX(2px);
}

/* 三列 Top 卡片列宽比例(排名 / 短码 / 指标 / 长链 / 时间 / 操作) */
.top-card:not(.top-card-legacy) th:nth-child(1),
.top-card:not(.top-card-legacy) td:nth-child(1) { width: 32px; }
.top-card:not(.top-card-legacy) th:nth-child(2),
.top-card:not(.top-card-legacy) td:nth-child(2) { width: 80px; }
.top-card:not(.top-card-legacy) th:nth-child(3),
.top-card:not(.top-card-legacy) td:nth-child(3) { width: 60px; }
.top-card:not(.top-card-legacy) th:nth-child(4),
.top-card:not(.top-card-legacy) td:nth-child(4) { width: auto; }
.top-card:not(.top-card-legacy) th:nth-child(5),
.top-card:not(.top-card-legacy) td:nth-child(5) { width: 90px; }
.top-card:not(.top-card-legacy) th:nth-child(6),
.top-card:not(.top-card-legacy) td:nth-child(6) { width: 32px; }

/* 全期累计表(单独卡,6 列等宽自定义) */
.top-card-legacy th:nth-child(1),
.top-card-legacy td:nth-child(1) { width: 38px; }
.top-card-legacy th:nth-child(2),
.top-card-legacy td:nth-child(2) { width: 100px; }
.top-card-legacy th:nth-child(3),
.top-card-legacy td:nth-child(3) { width: 110px; }
.top-card-legacy th:nth-child(4),
.top-card-legacy td:nth-child(4) { width: auto; }
.top-card-legacy th:nth-child(5),
.top-card-legacy td:nth-child(5) { width: 110px; }
.top-card-legacy th:nth-child(6),
.top-card-legacy td:nth-child(6) { width: 36px; }
.top-card-legacy { margin-top: 4px; }
.empty {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-dim);
  padding: 14px 4px;
}
.empty-link { color: #67E8F9; text-decoration: none; }
.empty-link:hover { text-decoration: underline; }

.seg {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px;
  background: rgba(11, 11, 16, 0.5);
  border: 1px solid rgba(96, 165, 250, 0.15);
  border-radius: 10px;
}
.seg-btn {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 5px 10px;
  border-radius: 6px;
  background: transparent;
  border: 0;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast), box-shadow var(--t-fast);
}
.seg-btn:hover { color: var(--text); background: rgba(96, 165, 250, 0.08); }
.seg-btn.is-active {
  color: #0B0B10;
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  box-shadow: 0 0 14px -2px rgba(103, 232, 249, 0.5);
}
.mini-seg { padding: 3px; }
.mini-seg .seg-btn { padding: 4px 9px; font-size: 10.5px; }

.ghost {
  background: transparent;
  border: 1px solid rgba(96, 165, 250, 0.28);
  color: #93C5FD;
  padding: 5px 10px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--t-fast);
}
.ghost:hover {
  border-color: rgba(96, 165, 250, 0.6);
  background: rgba(96, 165, 250, 0.08);
  color: #BFDBFE;
}
.mini { padding: 3px 8px; font-size: 10.5px; }


/* ===== 三列洞察行 ===== */
.insight-row {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.bd-rt-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}
.bd-rt-row > .glass-card { display: flex; flex-direction: column; gap: 14px; min-height: 0; }

/* ----- Trend chart(整行) ----- */
.trend-card { display: flex; flex-direction: column; gap: 14px; }
.trend-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: nowrap;
}
.trend-title { margin: 0; font-size: 15px; letter-spacing: -0.01em; font-weight: 600; }
.trend-seg { flex-shrink: 0; }
.trend-seg .seg-btn { padding: 3px 8px; font-size: 10.5px; }
.trend-chart { height: 200px; width: 100%; }

/* ===== 访问构成(BREAKDOWN) ===== */
.bd-card { align-self: stretch; }
.bd-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: nowrap;
}
.bd-title { margin: 0; font-size: 15px; letter-spacing: -0.01em; font-weight: 600; }
.bd-seg { flex-shrink: 0; }
.bd-seg .seg-btn { padding: 3px 8px; font-size: 10.5px; }

.bd-list { display: flex; flex-direction: column; gap: 6px; }
.bd-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 80px 64px;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 12px;
}
.bd-rank { color: var(--text-dim); font-size: 10px; letter-spacing: 0.06em; }
.bd-label {
  color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bd-bar {
  position: relative;
  display: block;
  height: 6px;
  background: rgba(96,165,250,0.06);
  border-radius: 3px;
  overflow: hidden;
}
.bd-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #60A5FA, #67E8F9);
  border-radius: 3px;
  box-shadow: 0 0 6px rgba(103,232,249,0.35);
  transition: width 0.4s ease;
}
.bd-meta { text-align: right; }
.bd-meta b { color: #67E8F9; font-variant-numeric: tabular-nums; }
.bd-meta .dim { color: var(--text-dim); margin-left: 4px; font-size: 10.5px; }

/* breakdown 空状态:小巧居中 */
.bd-empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 24px 4px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 11.5px;
  letter-spacing: 0.02em;
}
.bd-empty-icon {
  color: rgba(103,232,249,0.5);
  display: flex; align-items: center; justify-content: center;
}

/* ===== 实时窗口(REALTIME) ===== */
.rt-card { align-self: stretch; }
.rt-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: nowrap;
}
.rt-title { margin: 0; font-size: 15px; letter-spacing: -0.01em; font-weight: 600; }
.rt-stat {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(96,165,250,0.06);
  border: 1px solid rgba(96,165,250,0.18);
  flex-shrink: 0;
}
.rt-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #475569;
}
.rt-dot.is-active {
  background: #67E8F9;
  box-shadow: 0 0 0 0 rgba(103,232,249,0.6);
  animation: rt-pulse-anim 1.6s ease-out infinite;
}
@keyframes rt-pulse-anim {
  0%   { box-shadow: 0 0 0 0 rgba(103,232,249,0.55); }
  70%  { box-shadow: 0 0 0 8px rgba(103,232,249,0); }
  100% { box-shadow: 0 0 0 0 rgba(103,232,249,0); }
}
.rt-num { color: #67E8F9; font-weight: 700; font-variant-numeric: tabular-nums; }
.rt-unit { color: var(--text-dim); font-size: 10px; letter-spacing: 0.04em; }

/* rt 空状态:大视觉中心,一行副说明 */
.rt-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 14px 4px 8px;
  text-align: center;
}
.rt-empty-visual {
  position: relative;
  width: 64px; height: 64px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 8px;
}
.rt-empty-core {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(96,165,250,0.15), rgba(103,232,249,0.05));
  border: 1px solid rgba(103,232,249,0.35);
  color: #67E8F9;
  display: flex; align-items: center; justify-content: center;
  z-index: 2;
  animation: rt-empty-core-spin 12s linear infinite;
}
@keyframes rt-empty-core-spin {
  to { transform: rotate(360deg); }
}
.rt-empty-ring {
  position: absolute;
  top: 50%; left: 50%;
  width: 50px; height: 50px;
  margin: -25px 0 0 -25px;
  border-radius: 50%;
  border: 1px dashed rgba(103,232,249,0.25);
  animation: rt-empty-ring-spin 18s linear infinite;
}
.rt-empty-ring-2 {
  width: 60px; height: 60px;
  margin: -30px 0 0 -30px;
  border: 1px dotted rgba(139,92,246,0.25);
  animation-direction: reverse;
  animation-duration: 24s;
}
@keyframes rt-empty-ring-spin {
  to { transform: rotate(360deg); }
}
.rt-empty-title {
  margin: 0;
  font-size: 13px;
  color: var(--text);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
}
.rt-empty-sub {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

/* 有数据时的两列紧凑布局 */
.rt-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.rt-col { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.rt-section-head {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.18em;
  color: rgba(148,163,184,0.55);
  text-transform: uppercase;
}
.rt-empty-mini {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
  padding: 6px 0;
}
.rt-top-list, .rt-stream-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 4px;
}
.rt-top-list li {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11.5px;
}
.rt-rank { color: var(--text-dim); font-size: 10px; }
.rt-link {
  background: transparent; border: 0; padding: 0;
  color: #93C5FD; cursor: pointer;
  font-family: var(--font-mono);
  text-align: left;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rt-link:hover { color: #BFDBFE; text-decoration: underline; }
.rt-pv { text-align: right; color: #67E8F9; font-variant-numeric: tabular-nums; }
.rt-stream-list { gap: 3px; }
.rt-stream-row {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 4px 6px;
  border-radius: 6px;
  background: rgba(96,165,250,0.04);
  border: 1px solid rgba(96,165,250,0.06);
}
.rt-stream-code { color: #67E8F9; flex-shrink: 0; }
.rt-stream-meta {
  display: flex; flex-direction: column;
  margin-left: auto; align-items: flex-end; line-height: 1.25;
  min-width: 0;
}
.rt-stream-dev { color: var(--text-muted); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.rt-stream-time { color: var(--text-dim); font-size: 9.5px; }


/* ----- 洞察行响应式 ----- */
@media (max-width: 1180px) {
  .insight-row { grid-template-columns: 1fr 1fr; }
  .realtime-card { grid-column: 1 / -1; }
}
@media (max-width: 720px) {
  .insight-row { grid-template-columns: 1fr; }
  .realtime-card { grid-column: auto; }
}

/* ===== 响应式 ===== */
@media (max-width: 1180px) {
  .stat-grid { grid-template-columns: repeat(3, 1fr); }
  .top-row { grid-template-columns: 1fr; }
  .radar-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 880px) {
  .bd-rt-row { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .radar-grid { grid-template-columns: 1fr; }
}
</style>


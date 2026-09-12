<template>
  <div class="page">
    <header class="page-head page-head-row">
      <div class="page-head-left">        <h2>详情</h2>
        <p class="page-sub">
          短码 <code class="inline-code">{{ code }}</code> 的链接信息与访问监控
        </p>
      </div>
      <div class="page-head-right">
        <router-link to="/links" class="ghost mini back-btn" aria-label="返回链接列表">
          ← 返回列表
        </router-link>
        <button type="button" class="ghost mini" :disabled="refreshing" @click="refresh">
          {{ refreshing ? '刷新中…' : '↻ 刷新' }}
        </button>
        <div class="more-wrap" ref="moreWrap">
          <button type="button" class="ghost mini more-btn"
                  :class="{ 'is-open': moreOpen }"
                  aria-haspopup="menu"
                  :aria-expanded="moreOpen"
                  @click="moreOpen = !moreOpen">⋯ 更多</button>
          <div v-if="moreOpen" class="more-menu" role="menu">
            <button type="button" class="more-item" role="menuitem"
                    :disabled="toggling" @click="onToggle">
              {{ data && data.status === 'enabled' ? '停用短链' : '启用短链' }}
            </button>
            <a v-if="data && data.full_short_url" :href="data.full_short_url"
               target="_blank" rel="noopener" class="more-item" role="menuitem">
              打开短链
            </a>
            <div class="more-sep"></div>
            <button type="button" class="more-item danger" role="menuitem"
                    :disabled="deleting" @click="onDelete">
              {{ deleting ? '删除中…' : '删除到回收站' }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <div v-if="loading" class="glass-card">
      <div class="loading-state"><span class="dot-pulse"></span>正在加载数据…</div>
    </div>
    <div v-else-if="errorMsg" class="glass-card error-card">{{ errorMsg }}</div>
    <template v-else-if="data">
      <div class="glass-card summary-card">
        <div class="summary-top">
          <div class="summary-status">
            <span :class="['status-tag', data.status]">{{ statusLabel(data.status) }}</span>
            <span v-if="data.has_password" class="mini-tag locked">密码保护</span>
            <span v-else class="mini-tag plain">无密码</span>
            <span v-if="isExpired" class="mini-tag expired">已过期</span>
            <span v-else-if="isPending" class="mini-tag pending">待生效</span>
          </div>
          <div class="summary-link-row">
            <div class="summary-link-main">
              <span class="info-k-inline">短码</span>
              <code class="code-chip">{{ data.short_code }}</code>
            </div>
            <div class="summary-link-main summary-link-url">
              <span class="info-k-inline">完整短链</span>
              <a :href="data.full_short_url" target="_blank" rel="noopener" class="short-link">
                <code>{{ data.full_short_url }}</code>
              </a>
              <CopyButton :text="data.full_short_url" compact />
            </div>
          </div>
          <div class="summary-link-row summary-long-row">
            <span class="info-k-inline">原始链接</span>
            <a :href="data.long_url" target="_blank" rel="noopener" class="long-url-link">
              <code>{{ data.long_url }}</code>
            </a>
          </div>
        </div>

        <div class="summary-stats-row">
          <div class="stat-tile" data-tone="cyan">
            <div class="stat-tile-top">
              <span class="stat-tile-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none"><path d="M2 11l3-3 3 2 5-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="13" cy="4" r="1" fill="currentColor"/></svg>
              </span>
              <span class="stat-tile-label">PV</span>
            </div>
            <div class="stat-tile-value">{{ data.pv ?? 0 }}</div>
            <div class="stat-tile-foot">访问量</div>
          </div>
          <div class="stat-tile" data-tone="green">
            <div class="stat-tile-top">
              <span class="stat-tile-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none"><circle cx="6" cy="6" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M2 14c0-2.2 1.8-4 4-4s4 1.8 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="12" cy="5" r="2" stroke="currentColor" stroke-width="1.2"/></svg>
              </span>
              <span class="stat-tile-label">UV</span>
            </div>
            <div class="stat-tile-value">{{ data.uv ?? 0 }}</div>
            <div class="stat-tile-foot">独立访客</div>
          </div>
          <div class="stat-tile" data-tone="violet">
            <div class="stat-tile-top">
              <span class="stat-tile-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none"><circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.4"/><path d="M5 8h6M8 5l-3 3 3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </span>
              <span class="stat-tile-label">转化率</span>
            </div>
            <div class="stat-tile-value">{{ conversionRate }}</div>
            <div class="stat-tile-foot">PV → UV</div>
          </div>
          <div class="stat-tile" data-tone="blue">
            <div class="stat-tile-top">
              <span class="stat-tile-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/><path d="M8 4v4l2.5 1.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
              </span>
              <span class="stat-tile-label">实时</span>
            </div>
            <div class="stat-tile-value">{{ realtimeText }}</div>
            <div class="stat-tile-foot">最近访问</div>
          </div>
        </div>

        <!-- 常驻属性栏:扁平 7 列 + 细分隔线分 3 段 -->
        <div class="summary-attrs">
          <div class="attr-cell">
            <span class="attr-k">生效</span>
            <span class="attr-v">{{ data.effective_at ? formatTime(data.effective_at) : '立即' }}</span>
          </div>
          <div class="attr-cell">
            <span class="attr-k">过期</span>
            <span class="attr-v" :class="{ 'is-expired': isExpired }">{{ data.expire_at ? formatTime(data.expire_at) : '永久' }}</span>
          </div>
          <span class="attr-sep" aria-hidden="true"></span>
          <div class="attr-cell">
            <span class="attr-k">点击上限</span>
            <span class="attr-v">{{ data.click_limit ?? '不限' }}</span>
          </div>
          <div class="attr-cell">
            <span class="attr-k">渠道</span>
            <span class="attr-v">{{ data.channel || '默认' }}</span>
          </div>
          <div class="attr-cell">
            <span class="attr-k">域名</span>
            <span class="attr-v">{{ data.domain || '默认' }}</span>
          </div>
          <span class="attr-sep" aria-hidden="true"></span>
          <div class="attr-cell">
            <span class="attr-k">创建</span>
            <span class="attr-v dim">{{ formatTime(data.created_at) }}</span>
          </div>
          <div class="attr-cell">
            <span class="attr-k">最近访问</span>
            <span class="attr-v dim">{{ data.last_visit_at ? formatTime(data.last_visit_at) : '—' }}</span>
          </div>
        </div>

        <button type="button" class="advanced-toggle" :class="{ 'is-open': advancedOpen }" aria-expanded="advancedOpen" @click="advancedOpen = !advancedOpen">
          <span class="at-label">🛡 访问控制</span>
          <span class="at-hint">{{ accessRulesSummary }}</span>
          <span class="at-caret" aria-hidden="true">{{ advancedOpen ? '▴' : '▾' }}</span>
        </button>
        <div v-if="advancedOpen" class="advanced-panel">
          <div class="ac-summary-bar">
            <span class="ac-stat">生效 <b>{{ accessRuleStats.active }}</b> 条</span>
            <span class="ac-stat dim">已停用 <b>{{ accessRuleStats.disabled }}</b> 条</span>
            <span class="ac-stat dim">IP <b>{{ accessRuleStats.ip }}</b> · UA <b>{{ accessRuleStats.ua }}</b> · Referer <b>{{ accessRuleStats.referer }}</b></span>
            <span class="ac-stat dim">本链 <b>{{ accessRuleStats.shortCode }}</b> · 全局 <b>{{ accessRuleStats.global }}</b></span>
          </div>

          <div class="ac-group">
            <div class="ac-group-head"><span class="ac-group-tag block">IP 黑名单</span><span class="ac-group-meta">{{ ipBlockRules.length }} 条</span></div>
            <div v-if="!ipBlockRules.length" class="ac-empty">暂无 · 在下方"新增规则"里加上</div>
            <div v-for="r in ipBlockRules" :key="r.id" class="ac-rule-row" :class="{ 'is-off': !r.enabled }">
              <code class="ac-rule-value">{{ r.value }}</code>
              <span class="ac-rule-mode block">黑</span>
              <span class="ac-rule-action" :class="r.action">{{ r.action === 'observe' ? '观察' : '拦截' }}</span>
              <span class="ac-rule-scope">{{ r.scope === 'global' ? '全局' : '本链' }}</span>
              <span class="ac-rule-expire">{{ r.expire_at ? formatTime(r.expire_at) + ' 到期' : '永久' }}</span>
              <label class="ac-switch"><input type="checkbox" :checked="r.enabled" @change="toggleRule(r, $event.target.checked)" /><span class="ac-switch-slider"></span></label>
              <button type="button" class="ghost mini" @click="removeRule(r)">解封</button>
            </div>
          </div>

          <div class="ac-group">
            <div class="ac-group-head"><span class="ac-group-tag allow">IP 白名单</span><span class="ac-group-meta">{{ ipAllowRules.length }} 条 · 配置后未命中即拒</span></div>
            <div v-if="!ipAllowRules.length" class="ac-empty">暂无白名单</div>
            <div v-for="r in ipAllowRules" :key="r.id" class="ac-rule-row" :class="{ 'is-off': !r.enabled }">
              <code class="ac-rule-value">{{ r.value }}</code>
              <span class="ac-rule-mode allow">白</span>
              <span class="ac-rule-action" :class="r.action">{{ r.action === 'observe' ? '观察' : '放行' }}</span>
              <span class="ac-rule-scope">{{ r.scope === 'global' ? '全局' : '本链' }}</span>
              <span class="ac-rule-expire">{{ r.expire_at ? formatTime(r.expire_at) + ' 到期' : '永久' }}</span>
              <label class="ac-switch"><input type="checkbox" :checked="r.enabled" @change="toggleRule(r, $event.target.checked)" /><span class="ac-switch-slider"></span></label>
              <button type="button" class="ghost mini" @click="removeRule(r)">解封</button>
            </div>
          </div>

          <div class="ac-group">
            <div class="ac-group-head"><span class="ac-group-tag block">UA 关键词</span><span class="ac-group-meta">{{ uaRules.length }} 条 · 匹配即生效</span></div>
            <div v-if="!uaRules.length" class="ac-empty">暂无</div>
            <div v-for="r in uaRules" :key="r.id" class="ac-rule-row" :class="{ 'is-off': !r.enabled }">
              <code class="ac-rule-value">{{ r.value }}</code>
              <span class="ac-rule-mode block">黑</span>
              <span class="ac-rule-action" :class="r.action">{{ r.action === 'observe' ? '观察' : '拦截' }}</span>
              <span class="ac-rule-scope">{{ r.scope === 'global' ? '全局' : '本链' }}</span>
              <label class="ac-switch"><input type="checkbox" :checked="r.enabled" @change="toggleRule(r, $event.target.checked)" /><span class="ac-switch-slider"></span></label>
              <button type="button" class="ghost mini" @click="removeRule(r)">解封</button>
            </div>
          </div>

          <div class="ac-group">
            <div class="ac-group-head"><span class="ac-group-tag block">Referer 关键词</span><span class="ac-group-meta">{{ refererRules.length }} 条</span></div>
            <div v-if="!refererRules.length" class="ac-empty">暂无</div>
            <div v-for="r in refererRules" :key="r.id" class="ac-rule-row" :class="{ 'is-off': !r.enabled }">
              <code class="ac-rule-value">{{ r.value }}</code>
              <span class="ac-rule-mode block">黑</span>
              <span class="ac-rule-action" :class="r.action">{{ r.action === 'observe' ? '观察' : '拦截' }}</span>
              <span class="ac-rule-scope">{{ r.scope === 'global' ? '全局' : '本链' }}</span>
              <label class="ac-switch"><input type="checkbox" :checked="r.enabled" @change="toggleRule(r, $event.target.checked)" /><span class="ac-switch-slider"></span></label>
              <button type="button" class="ghost mini" @click="removeRule(r)">解封</button>
            </div>
          </div>

          <div class="ac-add-row" :class="{ 'is-open': addFormOpen }">
            <button type="button" class="ac-add-toggle" @click="addFormOpen = !addFormOpen">
              <span class="at-caret" aria-hidden="true">{{ addFormOpen ? '▾' : '▸' }}</span>
              <span>{{ addFormOpen ? '收起新增规则' : '+ 新增规则' }}</span>
            </button>
            <div v-if="addFormOpen" class="ac-add-form">
              <div class="ac-add-grid">
                <label class="ac-add-cell wide"><span class="ac-add-k">值</span><input v-model="addForm.value" type="text" class="ac-add-input" spellcheck="false" :placeholder="addValuePlaceholder" /></label>
                <label class="ac-add-cell"><span class="ac-add-k">类型</span><select v-model="addForm.rule_type" class="ac-add-input"><option value="ip">IP</option><option value="ip_cidr">IP 网段</option><option value="ua">UA 关键词</option><option value="referer">Referer 关键词</option></select></label>
                <label class="ac-add-cell"><span class="ac-add-k">模式</span><select v-model="addForm.mode" class="ac-add-input"><option value="block">黑名单</option><option value="allow">白名单</option></select></label>
                <label class="ac-add-cell"><span class="ac-add-k">命中动作</span><select v-model="addForm.action" class="ac-add-input"><option value="block">直接拦截</option><option value="observe">仅观察</option></select></label>
                <label class="ac-add-cell"><span class="ac-add-k">范围</span><select v-model="addForm.scope" class="ac-add-input"><option value="short_code">本链</option><option value="global">全局</option></select></label>
              </div>
              <div class="ac-add-foot">
                <span v-if="addFormError" class="ac-add-error">{{ addFormError }}</span>
                <span v-else class="ac-add-hint">{{ addFormHint }}</span>
                <button type="button" class="ghost mini" :disabled="addFormSaving" @click="onAddRule">{{ addFormSaving ? '提交中…' : '新增' }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== 趋势图 ===== -->
      <div class="glass-card trend-card">
        <div class="trend-head">
          <h3 class="vh-title">点击趋势</h3>
          <div class="seg mini-seg">
            <button v-for="g in trendGranularities" :key="g.value" type="button" class="seg-btn"
                    :class="{ 'is-active': granularity === g.value }"
                    :disabled="g.value === 'hour' && days > 7"
                    @click="switchGranularity(g.value)">{{ g.label }}</button>
          </div>
        </div>
        <div v-if="trendLoading" class="loading-state"><span class="dot-pulse"></span>加载趋势…</div>
        <div v-else-if="!trendPoints.length" class="empty">窗口内还没有点击数据</div>
        <v-chart v-else class="trend-chart" :option="trendOption" autoresize></v-chart>
      </div>

      <!-- ===== 访问构成 ===== -->
      <div class="glass-card breakdown-card">
        <div class="breakdown-head">
          <h3 class="vh-title">访问构成</h3>
          <div class="seg mini-seg">
            <button v-for="d in breakdownDims" :key="d.value" type="button" class="seg-btn"
                    :class="{ 'is-active': bdDim === d.value }"
                    @click="switchBdDim(d.value)">{{ d.label }}</button>
          </div>
        </div>
        <div v-if="bdLoading" class="loading-state"><span class="dot-pulse"></span>加载构成…</div>
        <div v-else-if="!bdItems.length" class="empty">窗口内没有 {{ bdLabel }} 数据</div>
        <div v-else class="bd-rows">
          <div v-for="(it, idx) in bdItems.slice(0, 8)" :key="it.value" class="bd-row">
            <span class="bd-rank">{{ String(idx + 1).padStart(2, '0') }}</span>
            <span class="bd-label" :title="it.value">{{ it.value }}</span>
            <span class="bd-bar"><i :style="{ width: Math.max(4, it.ratio * 100) + '%' }"></i></span>
            <span class="bd-meta">
              <b>{{ it.pv }}</b>
              <span class="dim">{{ (it.ratio * 100).toFixed(1) }}%</span>
            </span>
          </div>
        </div>
        <div v-if="bdGeoUnavailable" class="geo-hint">
          未接入 IP 库,只显示「内网/未知」。接入后这里会显示国家/省份/城市。
        </div>
        <div class="bd-export-row">
          <button type="button" class="ghost mini" :disabled="exporting" @click="onExport">
            {{ exporting ? '导出中…' : '⤓ 导出明细 CSV' }}
          </button>
          <span class="bd-export-hint">最多 {{ exportLimitHint }} 行</span>
        </div>
      </div>

      <!-- ===== 实时窗口 ===== -->
      <div class="glass-card rt-card">
        <div class="rt-head">
          <h3 class="vh-title">实时窗口</h3>
          <div class="rt-pulse">
            <span class="rt-dot" :class="{ 'is-active': (rt.count || 0) > 0 }"></span>
            <span class="rt-num">{{ rt.count || 0 }}</span>
            <span class="rt-unit">次 / 30min</span>
          </div>
        </div>
        <div v-if="!rt.latest?.length" class="empty">30 分钟内无访问</div>
        <ul v-if="rt.latest?.length" class="rt-stream-list">
          <li v-for="(it, i) in rt.latest.slice(0, 8)" :key="i" class="rt-stream-row">
            <span class="rt-stream-dev">{{ it.device }} · {{ it.browser }}</span>
            <span class="rt-stream-time">{{ formatRelative(it.clicked_at) }}</span>
          </li>
        </ul>
      </div>

      <div class="glass-card visitors-card">
        <div class="visitors-head">
          <div class="vh-left">
            <h3 class="vh-title">访问来源</h3>
          </div>
          <div class="vh-right">
            <div class="seg mini-seg">
              <button v-for="d in dims" :key="d.value" type="button" class="seg-btn"
                      :class="{ 'is-active': dim === d.value }" @click="switchDim(d.value)">{{ d.label }}</button>
            </div>
            <div class="seg mini-seg">
              <button v-for="r in ranges" :key="r.value" type="button" class="seg-btn"
                      :class="{ 'is-active': days === r.value }" @click="switchDays(r.value)">{{ r.label }}</button>
            </div>
          </div>
        </div>

        <div class="hits-bar">
          <span class="hits-item">近 {{ days }} 天已拦截 <b>{{ hits.blocked }}</b> 次</span>
          <span class="hits-item dim">观察 {{ hits.observed }} 次</span>
          <span v-if="rules.length" class="hits-item dim">生效规则 {{ rules.length }} 条</span>
        </div>

        <div v-if="visitorsLoading" class="loading-state">
          <span class="dot-pulse"></span>正在加载来源数据…
        </div>
        <div v-else-if="visitorsError" class="error-card small">{{ visitorsError }}</div>
        <template v-else>
          <table v-if="items.length" class="visitors-table">
            <thead>
              <tr>
                <th>{{ dimLabel }}</th>
                <th>访问量</th>
                <th>占比</th>
                <th>最近访问</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in items" :key="i" :class="{ 'is-blocked': row.blocked }">
                <td class="val-cell" :title="row.value">{{ row.value }}</td>
                <td class="pv-cell">{{ row.pv }}</td>
                <td class="ratio-cell">
                  <span class="ratio-bar"><i :style="{ width: Math.max(2, row.ratio * 100) + '%' }"></i></span>
                  <span class="ratio-num">{{ (row.ratio * 100).toFixed(1) }}%</span>
                </td>
                <td class="time-cell">{{ formatTime(row.last_at) }}</td>
                <td class="op-cell">
                  <span v-if="row.blocked" class="blocked-tag">已拦截</span>
                  <button v-else class="ghost mini block-btn" @click="blockSource(row)">拦截</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty">近 {{ days }} 天暂无访问记录</div>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CopyButton from '@/components/CopyButton.vue'
import { shortlinkApi, accessRuleApi } from '@/api/shortlink'
import { useNotifyStore } from '@/stores/notify'
import VChart from 'vue-echarts'
import { use as echartsUse } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

echartsUse([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const router = useRouter()
const notify = useNotifyStore()
const code = route.params.code

// ----- 趋势图(F2.1) -----
const granularity = ref('day')
const trendGranularities = [
  { value: 'hour', label: '按小时' },
  { value: 'day', label: '按天' },
]
const trend = ref({ points: [], total_pv: 0 })
const trendLoading = ref(false)
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
    },
    legend: {
      data: ['PV', 'UV'],
      textStyle: { color: '#94A3B8', fontSize: 10, fontFamily: 'var(--font-mono)' },
      icon: 'roundRect', itemWidth: 10, itemHeight: 4,
      top: 0, right: 4,
    },
    xAxis: {
      type: 'category', data: xs, boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(96,165,250,0.18)' } },
      axisLabel: {
        color: '#94A3B8', fontSize: 9, fontFamily: 'var(--font-mono)',
        formatter: (v) => gran === 'hour' ? v.slice(11, 16) : v.slice(5),
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
        name: 'PV', type: 'line', data: pv, smooth: true, showSymbol: false,
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
        name: 'UV', type: 'line', data: uv, smooth: true, showSymbol: false,
        lineStyle: { color: '#67E8F9', width: 2 },
        itemStyle: { color: '#67E8F9' },
      },
    ],
  }
}

function switchGranularity(v) {
  if (granularity.value === v) return
  granularity.value = v
  fetchTrend()
}

async function fetchTrend() {
  trendLoading.value = true
  try {
    const r = await shortlinkApi.getTrend(code, {
      days: days.value, granularity: granularity.value,
    })
    trend.value = r || { points: [], total_pv: 0 }
  } catch (_) {
    trend.value = { points: [], total_pv: 0 }
  } finally {
    trendLoading.value = false
  }
}

// ----- 分类构成(F2.2-F2.4) -----
const breakdownDims = [
  { value: 'device', label: '设备' },
  { value: 'os', label: '系统' },
  { value: 'browser', label: '浏览器' },
  { value: 'referer_type', label: '来源' },
  { value: 'geo', label: '地理' },
]
const bdDim = ref('device')
const bdItems = ref([])
const bdLabel = ref('设备')
const bdLoading = ref(false)
const bdGeoUnavailable = ref(false)

const bdLabelMap = { device: '设备', os: '系统', browser: '浏览器', referer_type: '来源', geo: '地理' }

async function fetchBreakdown() {
  bdLoading.value = true
  try {
    const r = await shortlinkApi.getBreakdown(code, { by: bdDim.value, days: days.value })
    bdItems.value = r?.items || []
    bdLabel.value = bdLabelMap[bdDim.value] || ''
    bdGeoUnavailable.value = bdDim.value === 'geo' && r?.available === false
  } catch (_) {
    bdItems.value = []
    bdGeoUnavailable.value = false
  } finally {
    bdLoading.value = false
  }
}

function switchBdDim(v) {
  if (bdDim.value === v) return
  bdDim.value = v
  fetchBreakdown()
}

// ----- 实时窗口(F2.6) -----
const rt = ref({ count: 0, latest: [], window_minutes: 30 })
async function fetchRealtime() {
  try {
    const r = await shortlinkApi.getRealtime(code, { minutes: 30 })
    rt.value = r || { count: 0, latest: [], window_minutes: 30 }
  } catch (_) {
    rt.value = { count: 0, latest: [], window_minutes: 30 }
  }
}

// ----- 导出(F2.7) -----
const exporting = ref(false)
const exportLimitHint = ref('2 万')
async function onExport() {
  if (exporting.value) return
  exporting.value = true
  try {
    const blob = await shortlinkApi.exportClicks(code, { days: days.value })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `clicks-${code}-${new Date().toISOString().slice(0,10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    notify.success('已导出 CSV')
  } catch (e) {
    notify.error(e.message || '导出失败')
  } finally {
    exporting.value = false
  }
}
const data = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const refreshing = ref(false)
const toggling = ref(false)
const deleting = ref(false)
const advancedOpen = ref(false)
const moreOpen = ref(false)
const moreWrap = ref(null)

const isExpired = computed(() => {
  if (!data.value || !data.value.expire_at) return false
  return new Date(data.value.expire_at).getTime() < Date.now()
})
const isPending = computed(() => {
  if (!data.value || !data.value.effective_at) return false
  return new Date(data.value.effective_at).getTime() > Date.now()
})
const conversionRate = computed(() => {
  const pv = Number(data.value?.pv || 0)
  const uv = Number(data.value?.uv || 0)
  if (!pv) return '—'
  return ((uv / pv) * 100).toFixed(1) + '%'
})
const realtimeText = computed(() => {
  if (!data.value?.last_visit_at) return '—'
  return formatRelative(data.value.last_visit_at)
})

function statusLabel(s) {
  if (s === 'enabled') return '启用中'
  if (s === 'disabled') return '已停用'
  if (s === 'malicious') return '恶意'
  return s || '—'
}

function onDocClick(e) {
  if (!moreOpen.value) return
  const wrap = moreWrap.value
  if (wrap && !wrap.contains(e.target)) moreOpen.value = false
}

// 访问来源
const dims = [
  { value: 'ip', label: 'IP' },
  { value: 'ua', label: 'UA' },
  { value: 'referer', label: 'Referer' },
]
const ranges = [
  { value: 1, label: '24h' },
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
]
const dim = ref('ip')
const days = ref(7)
const items = ref([])
const rules = ref([])
const hits = ref({ blocked: 0, observed: 0, top_ips: [] })
const visitorsLoading = ref(false)
const visitorsError = ref('')

const dimLabel = computed(() => dims.find((d) => d.value === dim.value)?.label || '来源')

function formatTime(s) {
  if (!s) return '-'
  return new Date(s).toLocaleString()
}

function formatRelative(s) {
  if (!s) return '—'
  const diff = Date.now() - new Date(s).getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return Math.floor(diff / 60_000) + ' 分钟前'
  if (diff < 86400_000) return Math.floor(diff / 3600_000) + ' 小时前'
  return Math.floor(diff / 86400_000) + ' 天前'
}

async function loadVisitors() {
  visitorsLoading.value = true
  visitorsError.value = ''
  try {
    const res = await shortlinkApi.getVisitors(code, {
      dim: dim.value,
      days: days.value,
      limit: 20,
    })
    items.value = res.items || []
    rules.value = res.rules || []
    hits.value = res.hits || { blocked: 0, observed: 0, top_ips: [] }
  } catch (e) {
    visitorsError.value = e.message || '加载失败'
  } finally {
    visitorsLoading.value = false
  }
}

function switchDim(v) {
  if (dim.value === v) return
  dim.value = v
  loadVisitors()
}
function switchDays(v) {
  if (days.value === v) return
  days.value = v
  loadVisitors()
  fetchTrend()
  fetchBreakdown()
}

async function blockSource(row) {
  if (!row.raw) return
  const payload = {
    value: row.raw,
    scope: 'short_code',
    short_code: code,
    mode: 'block',
    action: 'block',
    reason: '统计页一键拦截',
  }
  if (dim.value === 'ua') payload.rule_type = 'ua'
  if (dim.value === 'referer') payload.rule_type = 'referer'
  try {
    await accessRuleApi.create(payload)
    notify.success('已拦截 ' + row.value)
    await loadVisitors()
  } catch (e) {
    notify.error(e.message)
  }
}

async function unblock(rule) {
  try {
    await accessRuleApi.remove(rule.id)
    notify.success('已解封')
    await loadVisitors()
  } catch (e) {
    notify.error(e.message)
  }
}

async function refresh() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    const [d] = await Promise.all([
      shortlinkApi.getOne(code),
      loadVisitors(),
      fetchTrend(),
      fetchBreakdown(),
      fetchRealtime(),
      loadAccessRules(),
    ])
    data.value = d
  } catch (e) {
    notify.error(e.message || '刷新失败')
  } finally {
    refreshing.value = false
  }
}

async function onToggle() {
  if (!data.value || toggling.value) return
  moreOpen.value = false
  const next = data.value.status === 'enabled' ? 'disabled' : 'enabled'
  const label = next === 'enabled' ? '启用' : '停用'
  if (!window.confirm('确认' + label + '这条短链?')) return
  toggling.value = true
  try {
    await shortlinkApi.patch(code, { status: next })
    data.value = await shortlinkApi.getOne(code)
    notify.success('已' + label)
  } catch (e) {
    notify.error(e.message || label + '失败')
  } finally {
    toggling.value = false
  }
}

async function onDelete() {
  if (!data.value || deleting.value) return
  moreOpen.value = false
  if (!window.confirm('删除后可在回收站恢复,确认继续?')) return
  deleting.value = true
  try {
    await shortlinkApi.remove(code)
    notify.success('已移到回收站')
    router.push('/links')
  } catch (e) {
    notify.error(e.message || '删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  try {
    data.value = await shortlinkApi.getOne(code)
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
  loadVisitors()
  fetchTrend()
  fetchBreakdown()
  fetchRealtime()
  loadAccessRules()
  document.addEventListener('click', onDocClick)
})


// ===== 访问控制(本链 + 全局)=====
const accessRules = ref([])
const accessRulesLoading = ref(false)
const addFormOpen = ref(false)
const addFormSaving = ref(false)
const addFormError = ref('')
const addForm = ref({
  value: '',
  rule_type: 'ip',
  mode: 'block',
  action: 'block',
  scope: 'short_code',
})

const ipBlockRules = computed(() => accessRules.value.filter(r => (r.rule_type === 'ip' || r.rule_type === 'ip_cidr') && r.mode === 'block'))
const ipAllowRules = computed(() => accessRules.value.filter(r => (r.rule_type === 'ip' || r.rule_type === 'ip_cidr') && r.mode === 'allow'))
const uaRules = computed(() => accessRules.value.filter(r => r.rule_type === 'ua'))
const refererRules = computed(() => accessRules.value.filter(r => r.rule_type === 'referer'))
const accessRuleStats = computed(() => {
  const total = accessRules.value
  return {
    active: total.filter(r => r.enabled).length,
    disabled: total.filter(r => !r.enabled).length,
    ip: ipBlockRules.value.length + ipAllowRules.value.length,
    ua: uaRules.value.length,
    referer: refererRules.value.length,
    shortCode: total.filter(r => r.scope === 'short_code').length,
    global: total.filter(r => r.scope === 'global').length,
  }
})
const accessRulesSummary = computed(() => {
  const s = accessRuleStats.value
  if (s.active + s.disabled === 0) return '尚无规则 · 点击配置'
  return s.active + ' 条生效 · ' + s.ip + ' IP / ' + s.ua + ' UA / ' + s.referer + ' Referer'
})
const addValuePlaceholder = computed(() => {
  if (addForm.value.rule_type === 'ip') return '如 1.2.3.4'
  if (addForm.value.rule_type === 'ip_cidr') return '如 10.0.0.0/8'
  if (addForm.value.rule_type === 'ua') return '如 bot, spider(逗号分隔)'
  return '如 spam.example(逗号分隔)'
})
const addFormHint = computed(() => addValuePlaceholder.value)

async function loadAccessRules() {
  accessRulesLoading.value = true
  try {
    const res = await accessRuleApi.list({ include_expired: true })
    const all = res.items || []
    // 本链 + 全局
    accessRules.value = all.filter(r => r.scope === 'global' || r.short_code === code)
  } catch (_) {
    accessRules.value = []
  } finally {
    accessRulesLoading.value = false
  }
}

async function toggleRule(rule, enabled) {
  try {
    await accessRuleApi.setEnabled(rule.id, enabled)
    rule.enabled = enabled
    notify.success(enabled ? '已启用' : '已停用')
  } catch (e) {
    notify.error(e.message || '操作失败')
    await loadAccessRules()
  }
}

async function removeRule(rule) {
  if (!window.confirm('确认解封 ' + rule.value + '?')) return
  try {
    await accessRuleApi.remove(rule.id)
    notify.success('已解封')
    await loadAccessRules()
    await loadVisitors()
  } catch (e) {
    notify.error(e.message || '解封失败')
  }
}

function resetAddForm() {
  addForm.value = { value: '', rule_type: 'ip', mode: 'block', action: 'block', scope: 'short_code' }
  addFormError.value = ''
}

async function onAddRule() {
  addFormError.value = ''
  const v = (addForm.value.value || '').trim()
  if (!v) { addFormError.value = '请输入值'; return }
  // IP / 网段 基础校验
  if (addForm.value.rule_type === 'ip' || addForm.value.rule_type === 'ip_cidr') {
    const parts = v.split(',').map(s => s.trim()).filter(Boolean)
    const ipRe = /^[0-9a-fA-F:.]+$/
    for (const p of parts) {
      if (!ipRe.test(p)) { addFormError.value = 'IP / 网段格式不正确:' + p; return }
    }
  }
  addFormSaving.value = true
  try {
    const payload = {
      value: v,
      rule_type: addForm.value.rule_type,
      mode: addForm.value.mode,
      action: addForm.value.action,
      scope: addForm.value.scope,
      reason: '详情页新增',
    }
    if (payload.scope === 'short_code') payload.short_code = code
    await accessRuleApi.create(payload)
    notify.success('已新增')
    resetAddForm()
    addFormOpen.value = false
    await loadAccessRules()
    await loadVisitors()
  } catch (e) {
    addFormError.value = e.message || '新增失败'
  } finally {
    addFormSaving.value = false
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
/* ===== 摘要卡常驻属性栏(扁平 7 列 + 细分隔线分 3 段,无空块) ===== */
.summary-attrs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 22px;
  padding: 14px 18px;
  border: 1px solid rgba(96, 165, 250, 0.12);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(11, 11, 16, 0.32), rgba(11, 11, 16, 0.16));
}
.attr-cell {
  display: inline-flex;
  align-items: baseline;
  gap: 10px;
  padding: 6px 0;
  font-family: var(--font-mono);
  white-space: nowrap;
}
.attr-k {
  flex: 0 0 auto;
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--text-dim);
  text-transform: uppercase;
}
.attr-v {
  flex: 0 1 auto;
  font-size: 13px;
  line-height: 1.4;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}
.attr-v.dim { color: var(--text-muted); }
.attr-v.is-expired { color: #FCA5A5; }
/* 细分隔线分 3 段 */
.attr-sep {
  display: inline-block;
  align-self: stretch;
  width: 1px;
  margin: 4px 4px;
  background: linear-gradient(180deg, transparent, rgba(96, 165, 250, 0.22), transparent);
}
@media (max-width: 1180px) {
  .attr-sep { display: none; }
  .summary-attrs { gap: 4px 18px; }
}

/* ===== 访问控制面板 ===== */
.ac-summary-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  padding: 9px 14px;
  border-radius: 10px;
  background: rgba(96, 165, 250, 0.06);
  border: 1px solid rgba(96, 165, 250, 0.14);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.ac-stat b { color: #67E8F9; font-weight: 600; }
.ac-stat.dim b { color: var(--text-muted); }

.ac-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 0;
  border-top: 1px dashed rgba(96, 165, 250, 0.12);
}
.ac-group:first-of-type { border-top: 0; padding-top: 6px; }
.ac-group-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ac-group-tag {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  font-weight: 600;
}
.ac-group-tag.block { color: #FCA5A5; background: rgba(239, 68, 68, 0.10); border: 1px solid rgba(239, 68, 68, 0.28); }
.ac-group-tag.allow { color: #FBBF24; background: rgba(251, 191, 36, 0.10); border: 1px solid rgba(251, 191, 36, 0.30); }
.ac-group-meta { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); letter-spacing: 0.04em; }
.ac-empty { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); padding: 6px 4px; }

.ac-rule-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(11, 11, 16, 0.45), rgba(11, 11, 16, 0.25));
  border: 1px solid rgba(96, 165, 250, 0.08);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
  transition: opacity var(--t-fast);
}
.ac-rule-row.is-off { opacity: 0.42; }
.ac-rule-row:hover { border-color: rgba(96, 165, 250, 0.22); }

.ac-rule-value {
  flex: 1 1 auto;
  min-width: 0;
  background: transparent;
  border: 0;
  padding: 0;
  color: #67E8F9;
  font-family: var(--font-mono);
  font-size: 12px;
  text-shadow: 0 0 6px rgba(103, 232, 249, 0.35);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ac-rule-mode {
  flex: 0 0 auto;
  font-size: 9px;
  letter-spacing: 0.1em;
  padding: 2px 7px;
  border-radius: 999px;
}
.ac-rule-mode.block { color: #FCA5A5; background: rgba(239, 68, 68, 0.10); border: 1px solid rgba(239, 68, 68, 0.28); }
.ac-rule-mode.allow { color: #FBBF24; background: rgba(251, 191, 36, 0.10); border: 1px solid rgba(251, 191, 36, 0.30); }
.ac-rule-action { font-size: 10px; letter-spacing: 0.06em; color: var(--text-muted); }
.ac-rule-action.observe { color: #FBBF24; }
.ac-rule-scope, .ac-rule-expire {
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--text-dim);
  white-space: nowrap;
}

/* 启停开关 */
.ac-switch { position: relative; display: inline-flex; width: 36px; height: 20px; flex: 0 0 auto; cursor: pointer; }
.ac-switch input { opacity: 0; width: 0; height: 0; }
.ac-switch-slider {
  position: absolute; inset: 0;
  background: rgba(148, 163, 184, 0.18);
  border: 1px solid rgba(148, 163, 184, 0.30);
  border-radius: 999px;
  transition: background var(--t-fast), border-color var(--t-fast);
}
.ac-switch-slider::before {
  content: '';
  position: absolute;
  top: 1px; left: 1px;
  width: 16px; height: 16px;
  background: #94A3B8;
  border-radius: 50%;
  transition: transform var(--t-fast), background var(--t-fast);
}
.ac-switch input:checked + .ac-switch-slider {
  background: rgba(103, 232, 249, 0.18);
  border-color: rgba(103, 232, 249, 0.55);
}
.ac-switch input:checked + .ac-switch-slider::before {
  transform: translateX(16px);
  background: #67E8F9;
  box-shadow: 0 0 8px rgba(103, 232, 249, 0.55);
}

/* + 新增规则 行内表单 */
.ac-add-row {
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px dashed rgba(96, 165, 250, 0.12);
}
.ac-add-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  background: rgba(11, 11, 16, 0.45);
  border: 1px dashed rgba(96, 165, 250, 0.32);
  border-radius: 8px;
  color: #67E8F9;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background var(--t-fast), border-color var(--t-fast);
}
.ac-add-toggle:hover { background: rgba(96, 165, 250, 0.10); border-color: rgba(103, 232, 249, 0.55); }
.ac-add-row.is-open .ac-add-toggle { border-style: solid; }
.ac-add-form {
  margin-top: 10px;
  padding: 14px;
  background: rgba(11, 11, 16, 0.40);
  border: 1px solid rgba(96, 165, 250, 0.18);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ac-add-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
  gap: 10px;
}
.ac-add-cell { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ac-add-k {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.ac-add-input {
  width: 100%;
  height: 32px;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  background: rgba(11, 11, 16, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 7px;
  color: var(--text);
  outline: none;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.ac-add-input:focus { border-color: rgba(103, 232, 249, 0.55); box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.10); }
.ac-add-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 11px;
}
.ac-add-hint { color: var(--text-dim); }
.ac-add-error { color: #FCA5A5; }

@media (max-width: 880px) {
  .ac-add-grid { grid-template-columns: 1fr 1fr; }
}


/* ===== 趋势 / 构成 / 实时 卡片 ===== */
.trend-card, .breakdown-card, .rt-card {
  display: flex; flex-direction: column; gap: 12px;
}
.trend-head, .breakdown-head, .rt-head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
}
.trend-head h3, .breakdown-head h3, .rt-head h3 { margin: 0; font-size: 16px; }
.trend-chart { height: 220px; width: 100%; }
.bd-rows { display: flex; flex-direction: column; gap: 6px; }
.bd-row {
  display: grid;
  grid-template-columns: 22px 100px 1fr 80px;
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
  position: relative; display: block;
  height: 8px;
  background: rgba(96,165,250,0.06);
  border-radius: 4px; overflow: hidden;
}
.bd-bar i {
  display: block; height: 100%;
  background: linear-gradient(90deg, #60A5FA, #67E8F9);
  border-radius: 4px;
  box-shadow: 0 0 8px rgba(103,232,249,0.35);
  transition: width 0.4s ease;
}
.bd-meta { text-align: right; }
.bd-meta b { color: #67E8F9; font-variant-numeric: tabular-nums; }
.bd-meta .dim { color: var(--text-dim); margin-left: 4px; font-size: 10.5px; }
.geo-hint {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(96,165,250,0.04);
  border: 1px dashed rgba(96,165,250,0.18);
}
.bd-export-row {
  display: flex; align-items: center; gap: 10px;
  padding-top: 4px;
  border-top: 1px dashed rgba(96,165,250,0.12);
}
.bd-export-hint {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
}

/* realtime */
.rt-pulse {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--font-mono);
  font-size: 14px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(96,165,250,0.08);
  border: 1px solid rgba(96,165,250,0.2);
}
.rt-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #475569;
}
.rt-dot.is-active {
  background: #67E8F9;
  box-shadow: 0 0 0 0 rgba(103,232,249,0.6);
  animation: rt-pulse-anim 1.6s ease-out infinite;
}
@keyframes rt-pulse-anim {
  0%   { box-shadow: 0 0 0 0 rgba(103,232,249,0.55); }
  70%  { box-shadow: 0 0 0 10px rgba(103,232,249,0); }
  100% { box-shadow: 0 0 0 0 rgba(103,232,249,0); }
}
.rt-num { color: #67E8F9; font-weight: 700; font-variant-numeric: tabular-nums; }
.rt-unit { color: var(--text-dim); font-size: 10px; }
.rt-stream-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 4px;
}
.rt-stream-row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 5px 8px;
  border-radius: 6px;
  background: rgba(96,165,250,0.04);
  border: 1px solid rgba(96,165,250,0.06);
}
.rt-stream-dev { color: var(--text-muted); }
.rt-stream-time { color: var(--text-dim); font-size: 10px; }
.page { display: flex; flex-direction: column; gap: 22px; }
.page-head-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
}
.page-head-left { display: flex; flex-direction: column; gap: 4px; }
.page-head-right { display: inline-flex; align-items: center; gap: 8px; }
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
.inline-code {
  background: rgba(34, 211, 238, 0.08);
  border: 1px solid rgba(103, 232, 249, 0.28);
  border-radius: 6px;
  padding: 1px 8px;
  color: #67E8F9;
  font-size: 12px;
  text-shadow: 0 0 8px rgba(103, 232, 249, 0.4);
  font-family: var(--font-mono);
}
.back-btn { text-decoration: none; }

.more-wrap { position: relative; display: inline-flex; }
.more-btn.is-open {
  color: #67E8F9;
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 8px var(--accent-2-glow);
}
.more-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 168px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(20, 20, 28, 0.95), rgba(11, 11, 16, 0.95));
  border: 1px solid rgba(96, 165, 250, 0.28);
  box-shadow: 0 18px 38px -12px rgba(0, 0, 0, 0.7), 0 0 24px -8px rgba(59, 130, 246, 0.35);
  z-index: 20;
}
.more-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--text);
  background: transparent;
  border: 0;
  border-radius: 7px;
  cursor: pointer;
  text-align: left;
  text-decoration: none;
  transition: background var(--t-fast), color var(--t-fast);
}
.more-item:hover { background: rgba(96, 165, 250, 0.12); color: #67E8F9; }
.more-item:disabled { opacity: 0.5; cursor: not-allowed; }
.more-item.danger { color: #FCA5A5; }
.more-item.danger:hover { background: rgba(239, 68, 68, 0.14); color: #FECACA; }
.more-sep { height: 1px; background: rgba(96, 165, 250, 0.14); margin: 4px 6px; }

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
  display: flex;
  align-items: center;
  gap: 10px;
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

.summary-card {
  padding: 22px 24px 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.summary-top {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px dashed rgba(96, 165, 250, 0.14);
}
.summary-status { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.summary-link-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.summary-link-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.summary-link-url { flex: 1 1 320px; }
.summary-long-row { align-items: flex-start; }
.info-k-inline {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-dim);
  flex: 0 0 auto;
}
.code-chip {
  background: rgba(34, 211, 238, 0.08);
  border: 1px solid rgba(103, 232, 249, 0.28);
  border-radius: 6px;
  padding: 4px 10px;
  color: #67E8F9;
  font-size: 13px;
  text-shadow: 0 0 8px rgba(103, 232, 249, 0.4);
  font-family: var(--font-mono);
}
.short-link { display: inline-flex; align-items: center; gap: 6px; text-decoration: none; min-width: 0; }
.short-link code {
  background: rgba(34, 211, 238, 0.08);
  border: 1px solid rgba(103, 232, 249, 0.25);
  border-radius: 6px;
  padding: 4px 10px;
  color: #67E8F9;
  font-size: 12px;
  text-shadow: 0 0 8px rgba(103, 232, 249, 0.4);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 460px;
}
.long-url-link {
  flex: 1 1 auto;
  min-width: 0;
  text-decoration: none;
}
.long-url-link code {
  background: transparent;
  border: 0;
  padding: 0;
  color: var(--text);
  text-shadow: none;
  font-size: 13px;
  font-family: var(--font-mono);
  word-break: break-all;
}
.long-url-link:hover code { color: var(--accent-2); }

.summary-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.stat-tile {
  position: relative;
  padding: 16px 18px 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(11, 11, 16, 0.55), rgba(11, 11, 16, 0.35));
  border: 1px solid rgba(96, 165, 250, 0.14);
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
  isolation: isolate;
}
/* 顶部细 accent bar + 右上 glow */
.stat-tile::before {
  content: '';
  position: absolute;
  top: 0; left: 14px; right: 14px;
  height: 1px;
  background: linear-gradient(90deg, var(--tile-accent, rgba(148,163,184,0.3)), transparent);
  opacity: 0.85;
}
.stat-tile::after {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: radial-gradient(circle 200px at 100% 0%, var(--tile-glow, transparent), transparent 70%);
  pointer-events: none;
  opacity: 0.5;
  z-index: -1;
}
.stat-tile[data-tone="cyan"]   { --tile-accent: #67E8F9; --tile-glow: rgba(34, 211, 238, 0.18); }
.stat-tile[data-tone="green"]  { --tile-accent: #6EE7B7; --tile-glow: rgba(16, 185, 129, 0.16); }
.stat-tile[data-tone="blue"]   { --tile-accent: #93C5FD; --tile-glow: rgba(96, 165, 250, 0.18); }
.stat-tile[data-tone="violet"] { --tile-accent: #C4B5FD; --tile-glow: rgba(139, 92, 246, 0.18); }

.stat-tile-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.stat-tile-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--tile-accent);
}
.stat-tile-label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--text-muted);
}
.stat-tile-value {
  font-family: var(--font-sans);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #F1F5F9;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  text-shadow: 0 0 26px var(--tile-glow, transparent);
}
.stat-tile[data-tone="cyan"]   .stat-tile-value { color: #E0FAFF; }
.stat-tile[data-tone="green"]  .stat-tile-value { color: #D1FAE5; }
.stat-tile[data-tone="blue"]   .stat-tile-value { color: #DBEAFE; }
.stat-tile[data-tone="violet"] .stat-tile-value { color: #EDE9FE; }
.stat-tile-foot {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  font-size: 11px;
  color: rgba(148, 163, 184, 0.7);
}

.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 14px;
  border-radius: 12px;
  background: rgba(11, 11, 16, 0.4);
  border: 1px solid rgba(96, 165, 250, 0.16);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.06em;
  cursor: pointer;
  text-align: left;
  transition: background var(--t-fast), border-color var(--t-fast);
}
.advanced-toggle:hover { background: rgba(96, 165, 250, 0.08); border-color: rgba(103, 232, 249, 0.4); }
.advanced-toggle.is-open { border-color: rgba(103, 232, 249, 0.5); }
.at-label { color: #67E8F9; font-weight: 600; letter-spacing: 0.12em; }
.at-hint { flex: 1 1 auto; color: var(--text-dim); font-size: 11px; letter-spacing: 0.04em; }
.at-caret { color: var(--text-muted); font-size: 11px; }
.advanced-panel {
  padding: 14px 6px 2px;
  border-top: 1px dashed rgba(96, 165, 250, 0.12);
}
.adv-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 24px;
}
.adv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 4px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.06);
}
.adv-k {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-dim);
  flex: 0 0 88px;
}
.adv-v {
  flex: 1 1 auto;
  min-width: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
}
.adv-v.is-expired { color: #FCA5A5; }

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  padding: 3px 10px;
  border-radius: 999px;
}
.status-tag::before {
  content: '';
  width: 5px; height: 5px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}
.status-tag.enabled { color: #6EE7B7; background: rgba(16, 185, 129, 0.10); border: 1px solid rgba(16, 185, 129, 0.3); }
.status-tag.disabled { color: #FCA5A5; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.28); }
.status-tag.malicious { color: #FCD34D; background: rgba(251, 191, 36, 0.10); border: 1px solid rgba(251, 191, 36, 0.32); }

.mini-tag {
  display: inline-block;
  margin-left: 4px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
  padding: 2px 6px;
  border-radius: 4px;
  vertical-align: middle;
}
.mini-tag.pending { background: rgba(251, 191, 36, 0.12); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.35); }
.mini-tag.expired { background: rgba(239, 68, 68, 0.10); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.3); }
.mini-tag.locked { background: rgba(139, 92, 246, 0.12); color: #C4B5FD; border: 1px solid rgba(139, 92, 246, 0.3); }
.mini-tag.plain { background: rgba(148, 163, 184, 0.10); color: var(--text-muted); border: 1px solid rgba(148, 163, 184, 0.25); }

.visitors-card { padding: 22px 24px 24px; display: flex; flex-direction: column; gap: 14px; }
.visitors-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.vh-left { display: flex; flex-direction: column; gap: 2px; }
.vh-title { margin: 0; font-size: 16px; font-weight: 500; color: var(--text); }
.vh-right { display: inline-flex; align-items: center; gap: 10px; flex-wrap: wrap; }


.seg {
  display: inline-flex;
  gap: 3px;
  padding: 3px;
  background: rgba(11, 11, 16, 0.5);
  border: 1px solid rgba(96, 165, 250, 0.15);
  border-radius: 9px;
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
  box-shadow: 0 0 12px -2px rgba(103, 232, 249, 0.5);
}

.hits-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 9px 14px;
  border-radius: 10px;
  background: rgba(96, 165, 250, 0.06);
  border: 1px solid rgba(96, 165, 250, 0.14);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}
.hits-item b { color: #FCA5A5; font-weight: 600; }
.hits-item.dim { color: var(--text-dim); }

.visitors-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 6px;
}
.visitors-table thead th {
  background: transparent;
  color: rgba(148, 163, 184, 0.7);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  font-weight: 500;
  padding: 6px 12px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.12);
  text-align: left;
}
.visitors-table tbody tr {
  background: linear-gradient(180deg, rgba(11, 11, 16, 0.45), rgba(11, 11, 16, 0.25));
  transition: background var(--t-fast), box-shadow var(--t-fast);
}
.visitors-table tbody tr:hover {
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.1), rgba(34, 211, 238, 0.04));
  box-shadow: 0 0 22px -8px rgba(59, 130, 246, 0.45);
}
.visitors-table tbody tr.is-blocked { opacity: 0.62; }
.visitors-table tbody td {
  padding: 11px 12px;
  border-top: 1px solid rgba(96, 165, 250, 0.06);
  border-bottom: 1px solid rgba(96, 165, 250, 0.06);
  vertical-align: middle;
}
.visitors-table tbody td:first-child {
  border-left: 1px solid rgba(96, 165, 250, 0.06);
  border-top-left-radius: 10px;
  border-bottom-left-radius: 10px;
}
.visitors-table tbody td:last-child {
  border-right: 1px solid rgba(96, 165, 250, 0.06);
  border-top-right-radius: 10px;
  border-bottom-right-radius: 10px;
  text-align: right;
}

.val-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
}
.pv-cell {
  font-family: var(--font-mono);
  color: #67E8F9;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 8px rgba(103, 232, 249, 0.35);
}
.ratio-cell { display: flex; align-items: center; gap: 8px; }
.ratio-bar {
  flex: 0 0 70px;
  height: 5px;
  border-radius: 3px;
  background: rgba(148, 163, 184, 0.15);
  overflow: hidden;
}
.ratio-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #60A5FA, #67E8F9);
}
.ratio-num {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  min-width: 42px;
}
.time-cell {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}
.blocked-tag {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  padding: 3px 9px;
  border-radius: 999px;
  color: #FCA5A5;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
button.mini { padding: 5px 11px; font-size: 11px; letter-spacing: 0.08em; }
button.block-btn { color: #FCA5A5; border-color: rgba(239, 68, 68, 0.35); }
button.block-btn:hover { border-color: var(--danger); color: #FECACA; }

.rules-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 4px;
  border-top: 1px dashed rgba(96, 165, 250, 0.14);
}
.rules-head {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 2px;
}
.rule-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 8px;
  background: rgba(11, 11, 16, 0.4);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.rule-type {
  color: #67E8F9;
  min-width: 56px;
  letter-spacing: 0.06em;
}
.rule-value {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
}
.rule-mode {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  color: #FCA5A5;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.28);
}
.rule-mode.allow {
  color: #FBBF24;
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.3);
}
.rule-scope,
.rule-expire { color: var(--text-dim); font-size: 10px; white-space: nowrap; }
.error-card.small { padding: 14px 16px; font-size: 12px; }

@media (max-width: 880px) {
  .page-head-row { flex-direction: column; align-items: flex-start; }
  .summary-stats-row { grid-template-columns: repeat(2, 1fr); }
  .adv-grid { grid-template-columns: 1fr; }
  .visitors-head { align-items: flex-start; }
  .ratio-bar { flex-basis: 44px; }
}
</style>

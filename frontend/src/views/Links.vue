<template>
  <div class="page">
    <header class="page-head">      <h2>我的链接</h2>
      <p class="page-sub">所有由你创建的短链都在这里 — 跳转、复制、筛选、停用、删除、查看统计</p>
    </header>

    <div ref="cardRef" class="glass-card list-card">
      <!-- ===== 视图切换 + 主操作 ===== -->
      <div class="toolbar">
        <div class="view-tabs" role="tablist">
          <button type="button" role="tab" :aria-selected="view === 'active'"
                  class="view-tab" :class="{ 'is-active': view === 'active' }"
                  @click="setView('active')">活跃链接</button>
          <button type="button" role="tab" :aria-selected="view === 'trash'"
                  class="view-tab" :class="{ 'is-active': view === 'trash' }"
                  @click="setView('trash')">回收站</button>
        </div>
        <div class="toolbar-right">
          <router-link to="/generate" class="primary create-btn">
            <svg viewBox="0 0 16 16" width="12" height="12" fill="none" aria-hidden="true">
              <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
            <span>新建短链</span>
          </router-link>
          <button type="button" class="ghost refresh-btn" :disabled="loading" @click="fetchList">
            {{ loading ? '加载中…' : '↻ 刷新' }}
          </button>
        </div>
      </div>

      <!-- ===== 筛选:搜索为主,次级筛选紧凑排列 ===== -->
      <div class="filters">
        <!-- 主行:搜索(占满)+ 重置 -->
        <div class="filter-row filter-row-primary">
          <label class="f-search">
            <svg class="f-search-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.4"/>
              <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            <input v-model="keywordInput" type="text" placeholder="搜索短码 / 长链 / 渠道"
                   maxlength="128" spellcheck="false" aria-label="搜索短码或长链" />
            <kbd v-if="!keywordInput" class="f-search-kbd">/</kbd>
            <button v-if="keywordInput" type="button" class="f-clear" aria-label="清空搜索"
                    @click="keywordInput = ''">×</button>
          </label>
          <button type="button" class="f-reset" :disabled="!isDirty" @click="resetFilters"
                  :title="isDirty ? '清空所有筛选条件' : '没有可重置的筛选'">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3 8a5 5 0 1 0 1.5-3.5L3 6M3 3v3h3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>重置</span>
          </button>
        </div>

        <!-- 次行:状态 / 渠道 / 排序 / 每页,紧凑分组 -->
        <div class="filter-row filter-row-sub">
          <label class="f-chip">
            <span class="f-chip-label">状态</span>
            <select v-model="filters.status" @change="onFilterChange">
              <option value="">全部</option>
              <option value="enabled">启用</option>
              <option value="disabled">停用</option>
              <option value="malicious">恶意</option>
            </select>
          </label>
          <label class="f-chip">
            <span class="f-chip-label">渠道</span>
            <input v-model="channelInput" type="text" placeholder="精确匹配，如 wechat"
                   maxlength="32" spellcheck="false" />
          </label>
          <label class="f-chip">
            <span class="f-chip-label">排序</span>
            <select v-model="filters.sort" @change="onFilterChange">
              <option value="created_desc">最新创建</option>
              <option value="created_asc">最早创建</option>
              <option value="pv_desc">访问量最高</option>
              <option value="last_visit_desc">最近访问</option>
            </select>
          </label>
          <label class="f-chip">
            <span class="f-chip-label">每页</span>
            <select v-model.number="pageSize" @change="onFilterChange">
              <option v-for="n in PAGE_SIZES" :key="n" :value="n">{{ n }}</option>
            </select>
          </label>
        </div>
      </div>

      <!-- ===== 筛选提示(总数已由下方分页展示,此处不再重复) ===== -->
      <div v-if="hasFilters" class="meta-bar">
        <span class="meta-hint">
          已按条件筛选<template v-if="filters.keyword"> · 关键词「{{ filters.keyword }}」</template>
        </span>
      </div>

      <div v-if="errorMsg" class="error-block">! {{ errorMsg }}</div>

      <LinkTable :items="items" :view="view" :has-filters="hasFilters" @refresh="fetchList" />

      <!-- ===== 分页 ===== -->
      <div v-if="total > 0" class="pager">
        <div class="pager-info">
          共 <b>{{ total }}</b> 条 · 第 {{ page }} / {{ totalPages }} 页
        </div>

        <template v-if="totalPages > 1">
          <div class="pager-ctrl">
            <button type="button" class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
            <button v-for="it in pageItems" :key="it.key" type="button"
                    class="page-btn num" :class="{ 'is-active': it.page === page, 'is-gap': it.gap }"
                    :disabled="it.gap" @click="it.page && goPage(it.page)">
              {{ it.gap ? '…' : it.page }}
            </button>
            <button type="button" class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
          </div>

          <div class="pager-jump">
            跳至
            <input v-model.number="jumpPage" type="number" min="1" :max="totalPages"
                   aria-label="跳转到页码" @keydown.enter.prevent="goJump" />
            页
            <button type="button" class="page-btn" @click="goJump">GO</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import LinkTable from '@/components/LinkTable.vue'
import { shortlinkApi } from '@/api/shortlink'

const PAGE_SIZES = [10, 20, 50, 100]
const DEFAULT_SORT = 'created_desc'
const DEFAULT_PAGE_SIZE = 20

const items = ref([])
const total = ref(0)
const loading = ref(false)
const errorMsg = ref('')

const view = ref('active')          // active | trash
const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const jumpPage = ref(1)
const cardRef = ref(null)

const keywordInput = ref('')
const channelInput = ref('')
const filters = reactive({ keyword: '', status: '', channel: '', sort: DEFAULT_SORT })

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

// 影响结果集的筛选条件 —— 决定空态文案是"没匹配"还是"还没数据"
const hasFilters = computed(
  () => !!filters.keyword || !!filters.status || !!filters.channel
)

// 与默认值有任何差异 —— 决定"重置"按钮是否可点(排序/每页也会被重置,同样算脏)
const isDirty = computed(
  () => hasFilters.value || filters.sort !== DEFAULT_SORT || pageSize.value !== DEFAULT_PAGE_SIZE
)

// 页码窗口:首页 + 末页 + 当前页左右各两页,中间用省略号
const pageItems = computed(() => {
  const tp = totalPages.value
  const cur = page.value
  const nums = [...new Set([1, tp, cur, cur - 1, cur - 2, cur + 1, cur + 2])]
    .filter((n) => n >= 1 && n <= tp)
    .sort((a, b) => a - b)
  const out = []
  let prev = 0
  for (const n of nums) {
    if (prev && n - prev > 1) out.push({ key: `gap-${prev}`, gap: true })
    out.push({ key: `p-${n}`, page: n })
    prev = n
  }
  return out
})

function debounce(fn, ms = 350) {
  let timer = null
  const wrapped = (...args) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => { timer = null; fn(...args) }, ms)
  }
  wrapped.cancel = () => { if (timer) clearTimeout(timer); timer = null }
  return wrapped
}

const applyKeyword = debounce((v) => {
  filters.keyword = v.trim()
  page.value = 1
  fetchList()
})
const applyChannel = debounce((v) => {
  filters.channel = v.trim()
  page.value = 1
  fetchList()
})

// 输入框与已生效筛选值不同才触发,避免"重置"时多打一次请求
watch(keywordInput, (v) => {
  if (v.trim() === filters.keyword) return
  applyKeyword(v)
})
watch(channelInput, (v) => {
  if (v.trim() === filters.channel) return
  applyChannel(v)
})

async function fetchList() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { page: page.value, page_size: pageSize.value, sort: filters.sort }
    if (view.value === 'trash') params.only_deleted = true
    if (filters.status) params.status = filters.status
    if (filters.channel) params.channel = filters.channel
    if (filters.keyword) params.keyword = filters.keyword

    const data = await shortlinkApi.list(params)
    items.value = data.items
    total.value = data.total
    jumpPage.value = page.value

    // 筛选后当前页可能越界,回退到最后一页重取一次
    if (!items.value.length && total.value > 0 && page.value > 1) {
      page.value = totalPages.value
      return fetchList()
    }
  } catch (e) {
    errorMsg.value = '加载失败:' + e.message
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  fetchList()
}

function setView(v) {
  if (view.value === v) return
  view.value = v
  page.value = 1
  fetchList()
}

function goPage(p) {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  fetchList()
  cardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function goJump() {
  const n = Math.floor(Number(jumpPage.value))
  if (!Number.isFinite(n)) {
    jumpPage.value = page.value
    return
  }
  const clamped = Math.min(Math.max(1, n), totalPages.value)
  jumpPage.value = clamped
  goPage(clamped)
}

function resetFilters() {
  applyKeyword.cancel()
  applyChannel.cancel()
  filters.keyword = ''
  keywordInput.value = ''
  filters.status = ''
  filters.channel = ''
  channelInput.value = ''
  filters.sort = DEFAULT_SORT
  pageSize.value = DEFAULT_PAGE_SIZE
  page.value = 1
  fetchList()
}

onMounted(fetchList)
onUnmounted(() => {
  applyKeyword.cancel()
  applyChannel.cancel()
})
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
.list-card { padding: 18px 22px 22px; scroll-margin-top: 88px; }

/* === 工具栏 === */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.view-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: rgba(11, 11, 16, 0.5);
  border: 1px solid rgba(96, 165, 250, 0.15);
  border-radius: 10px;
}
.view-tab {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: none;
  padding: 6px 14px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast), box-shadow var(--t-fast);
}
.view-tab:hover { color: var(--text); background: rgba(96, 165, 250, 0.08); }
.view-tab:active { transform: none; }
.view-tab.is-active {
  color: #0B0B10;
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  box-shadow: 0 0 14px -2px rgba(103, 232, 249, 0.5);
}

.toolbar-right { display: inline-flex; align-items: center; gap: 10px; }
.refresh-btn { font-size: 12px; letter-spacing: 0.1em; color: var(--text-muted); }
.create-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  color: #0B0B10;
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  box-shadow: 0 0 14px -2px rgba(103, 232, 249, 0.5);
  transition: all var(--t-fast);
}
.create-btn:hover {
  color: #0B0B10;
  text-shadow: none;
  box-shadow: 0 0 22px -2px rgba(103, 232, 249, 0.75);
  transform: translateY(-1px);
}
.create-btn:active { transform: translateY(0); }

/* === 筛选行(两行布局,搜索主,次级紧凑) === */
.filters {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  margin-bottom: 14px;
  border: 1px solid rgba(96, 165, 250, 0.14);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(11, 11, 16, 0.32), rgba(11, 11, 16, 0.18));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
}

/* 主行:搜索框 + 重置按钮 */
.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.filter-row-primary { width: 100%; }

/* === 搜索框(主) === */
.f-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1 1 auto;
  min-width: 0;
  height: 40px;
  padding: 0 14px;
  border: 1px solid rgba(96, 165, 250, 0.22);
  border-radius: 10px;
  background:
    linear-gradient(180deg, rgba(20, 20, 28, 0.55), rgba(11, 11, 16, 0.65));
  color: var(--text-dim);
  transition: border-color var(--t-fast), box-shadow var(--t-fast), background var(--t-fast);
}
.f-search:hover { border-color: rgba(96, 165, 250, 0.35); }
.f-search:focus-within {
  border-color: rgba(103, 232, 249, 0.65);
  box-shadow:
    0 0 0 3px rgba(103, 232, 249, 0.12),
    inset 0 0 24px -8px rgba(103, 232, 249, 0.25);
  background:
    linear-gradient(180deg, rgba(20, 28, 38, 0.7), rgba(11, 11, 16, 0.7));
  color: #67E8F9;
}
.f-search-icon { flex: 0 0 auto; color: var(--text-dim); transition: color var(--t-fast); }
.f-search:focus-within .f-search-icon { color: #67E8F9; }
.f-search input {
  flex: 1 1 auto;
  width: auto;
  min-width: 0;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text);
  outline: none;
}
.f-search input:focus,
.f-search input:focus-visible {
  outline: none;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.f-search input::placeholder { color: var(--text-dim); font-size: 12px; }
.f-search-kbd {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 7px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 5px;
  background: rgba(11, 11, 16, 0.5);
  color: var(--text-dim);
  line-height: 1;
}
.f-clear {
  flex: 0 0 auto;
  width: 20px; height: 20px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.20);
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  text-transform: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.f-clear:hover { background: rgba(239, 68, 68, 0.28); color: #FCA5A5; box-shadow: none; }

/* 重置按钮(主行右侧) */
.f-reset {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  height: 40px;
  padding: 0 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.10em;
  color: var(--text-muted);
  background: rgba(11, 11, 16, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 10px;
  cursor: pointer;
  transition: all var(--t-fast);
}
.f-reset:hover:not(:disabled) {
  color: #FCA5A5;
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
}
.f-reset:disabled {
  opacity: 0.32;
  cursor: not-allowed;
}
.f-reset svg { transition: transform 0.4s var(--t-fast); }
.f-reset:hover:not(:disabled) svg { transform: rotate(-120deg); }

/* === 次行:状态 / 渠道 / 排序 / 每页 === */
.filter-row-sub {
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px dashed rgba(96, 165, 250, 0.10);
}
.f-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 4px 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  background: rgba(11, 11, 16, 0.32);
  transition: border-color var(--t-fast), background var(--t-fast);
}
.f-chip:hover { border-color: rgba(96, 165, 250, 0.3); background: rgba(11, 11, 16, 0.5); }
.f-chip:focus-within {
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 0 2px rgba(103, 232, 249, 0.10);
  background: rgba(11, 11, 16, 0.6);
}
.f-chip-label {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.65);
  padding-right: 8px;
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  line-height: 1;
}
.f-chip select,
.f-chip input {
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
  padding: 0 8px;
  border: 0;
  background: transparent;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
}
.f-chip select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2367E8F9' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 22px;
  min-width: 90px;
}
.f-chip input { padding-right: 10px; min-width: 140px; }
.f-chip input::placeholder { color: var(--text-dim); font-size: 11px; }
.f-chip select:focus,
.f-chip input:focus,
.f-chip select:focus-visible,
.f-chip input:focus-visible {
  outline: none;
  border: 0;
  background-color: transparent;
  box-shadow: none;
}

/* === 筛选提示 === */
.meta-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.meta-hint {
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(103, 232, 249, 0.8);
  letter-spacing: 0.04em;
}

.error-block {
  margin-bottom: 12px;
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 10px;
  color: #FCA5A5;
  font-family: var(--font-mono);
  font-size: 12px;
}

/* === 分页 === */
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed rgba(96, 165, 250, 0.14);
}
.pager-info {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 0.04em;
}
.pager-info b { color: #67E8F9; font-weight: 700; }

.pager-ctrl { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.page-btn {
  min-width: 32px;
  height: 30px;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: none;
  color: var(--text-muted);
  background: rgba(11, 11, 16, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 7px;
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast), background var(--t-fast), box-shadow var(--t-fast);
}
.page-btn:hover:not(:disabled):not(.is-active) {
  color: #67E8F9;
  border-color: rgba(103, 232, 249, 0.5);
  background: rgba(103, 232, 249, 0.08);
}
.page-btn:active:not(:disabled) { transform: translateY(1px); }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.page-btn.num { padding: 0 6px; }
.page-btn.is-gap { border-color: transparent; background: transparent; opacity: 0.6; }
.page-btn.is-active {
  color: #0B0B10;
  font-weight: 700;
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  border-color: transparent;
  box-shadow: 0 0 14px -2px rgba(103, 232, 249, 0.55);
}

.pager-jump {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.pager-jump input {
  width: 62px;
  height: 30px;
  padding: 0 8px;
  text-align: center;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 7px;
  background: rgba(11, 11, 16, 0.55);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
  -moz-appearance: textfield;
}
.pager-jump input::-webkit-outer-spin-button,
.pager-jump input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.pager-jump input:focus,
.pager-jump input:focus-visible {
  outline: none;
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.10);
}

@media (max-width: 720px) {
  .filters { align-items: stretch; }
  .f-search { flex: 1 1 100%; }
  .f-field { flex: 1 1 45%; }
  .f-field input { width: 100%; }
  .pager { justify-content: center; }
}
</style>

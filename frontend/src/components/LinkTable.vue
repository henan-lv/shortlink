<template>
  <div
    ref="scrollRef"
    class="table-scroll"
    :class="{ 'is-scrolled-left': scrolledLeft, 'is-scrolled-right': scrolledRight }"
    @scroll.passive="onScroll"
  >
    <table v-if="items.length">
      <thead>
        <tr>
          <th class="col-code">短码</th>
          <th class="col-short">短链</th>
          <th class="col-long">长链</th>
          <th class="col-status">状态</th>
          <th class="col-num">PV</th>
          <th class="col-num">UV</th>
          <th class="col-num">点击上限</th>
          <th class="col-time">生效时间</th>
          <th class="col-time">过期时间</th>
          <th class="col-time">最后访问</th>
          <th class="col-extra">渠道</th>
          <th class="col-extra">域名</th>
          <th class="col-time">创建时间</th>
          <th class="col-actions col-actions-head">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in items" :key="row.id">
          <td class="col-code">
            <a :href="row.full_short_url" target="_blank" rel="noopener" class="code-link">
              <code>{{ row.short_code }}</code>
            </a>
          </td>

          <td class="col-short">
            <span class="short-field">
              <a :href="row.full_short_url" target="_blank" rel="noopener"
                 class="short-url" :title="'点击打开 · ' + row.full_short_url">{{ row.full_short_url }}</a>
              <CopyButton :text="row.full_short_url" compact />
            </span>
          </td>

          <td class="col-long">
            <a :href="row.long_url" target="_blank" rel="noopener"
               class="long-url" :title="row.long_url">{{ row.long_url }}</a>
          </td>

          <td class="col-status">
            <span :class="['status-tag', row.status]">{{ statusLabel(row.status) }}</span>
            <span v-if="row.is_deleted" class="mini-tag deleted">已删除</span>
            <span v-else-if="isPending(row)" class="mini-tag pending"
                  :title="'将于 ' + formatTime(row.effective_at) + ' 生效'">待生效</span>
            <span v-if="isExpired(row)" class="mini-tag expired">已过期</span>
            <span v-if="row.has_password" class="mini-tag locked">密码</span>
          </td>

          <td class="col-num pv">{{ row.pv }}</td>
          <td class="col-num uv">{{ row.uv ?? 0 }}</td>
          <td class="col-num dim">{{ row.click_limit ?? '不限' }}</td>

          <td class="col-time">{{ row.effective_at ? formatTime(row.effective_at) : '立即' }}</td>
          <td class="col-time" :class="{ 'is-expired': isExpired(row) }">
            {{ row.expire_at ? formatTime(row.expire_at) : '永久' }}
          </td>
          <td class="col-time dim">{{ row.last_visit_at ? formatTime(row.last_visit_at) : '—' }}</td>

          <td class="col-extra">
            <span v-if="row.channel" class="chip">{{ row.channel }}</span>
            <span v-else class="dim">—</span>
          </td>
          <td class="col-extra">
            <span v-if="row.domain" class="chip domain" :title="row.domain">{{ row.domain }}</span>
            <span v-else class="dim">默认</span>
          </td>

          <td class="col-time dim">{{ formatTime(row.created_at) }}</td>

          <td class="col-actions">
            <template v-if="view === 'trash'">
              <button class="mini-btn restore" @click="onRestore(row)">恢复</button>
            </template>
            <template v-else>
              <button class="mini-btn" @click="goDetail(row.short_code)">详情</button>
              <button class="mini-btn" @click="onToggle(row)">
                {{ row.status === 'enabled' ? '停用' : '启用' }}
              </button>
              <button class="mini-btn danger" @click="onDelete(row)">删除</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty">
      <template v-if="view === 'trash'">回收站是空的</template>
      <template v-else-if="hasFilters">没有匹配的链接，换个条件试试</template>
      <template v-else>还没有短链，去 <router-link to="/generate" class="empty-link">生成一条</router-link> 吧</template>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import CopyButton from '@/components/CopyButton.vue'
import { shortlinkApi } from '@/api/shortlink'
import { useNotifyStore } from '@/stores/notify'

const props = defineProps({
  items: { type: Array, required: true },
  view: { type: String, default: 'active' },      // active | trash
  hasFilters: { type: Boolean, default: false },
})
const emit = defineEmits(['refresh'])
const router = useRouter()
const notify = useNotifyStore()

// 首列/末列是 sticky 吸附的,横向滚动时下方的列会从它底下穿过去,
// 被切一半的字看起来像渲染坏了。只有真的能往该方向滚时,才在吸附列上打一层
// 向外衰减的阴影,让"下面还有内容"这件事看起来是有意为之。
const scrollRef = ref(null)
const scrolledLeft = ref(false)
const scrolledRight = ref(false)

function onScroll() {
  const el = scrollRef.value
  if (!el) return
  scrolledLeft.value = el.scrollLeft > 1
  scrolledRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 1
}

function syncShadows() {
  nextTick(onScroll)
}

onMounted(() => {
  syncShadows()
  window.addEventListener('resize', syncShadows)
})
onUnmounted(() => window.removeEventListener('resize', syncShadows))

// 数据/每页条数变化后表格宽度会变,重新判断两端是否还能滚
watch(() => props.items, syncShadows)

const STATUS_LABEL = { enabled: 'LIVE', disabled: 'OFF', malicious: '恶意' }

function statusLabel(s) {
  return STATUS_LABEL[s] || s
}

function formatTime(s) {
  if (!s) return '-'
  return new Date(s).toLocaleString()
}

function isPending(row) {
  return !!row.effective_at && new Date(row.effective_at) > new Date()
}

function isExpired(row) {
  return !!row.expire_at && new Date(row.expire_at) <= new Date()
}

function goDetail(code) {
  router.push(`/stats/${code}`)
}

async function onToggle(row) {
  const newStatus = row.status === 'enabled' ? 'disabled' : 'enabled'
  try {
    await shortlinkApi.patch(row.short_code, { status: newStatus })
    notify.success(newStatus === 'enabled' ? `已启用 ${row.short_code}` : `已停用 ${row.short_code}`)
    emit('refresh')
  } catch (e) {
    notify.error(e.message)
  }
}

async function onDelete(row) {
  if (!confirm(`确认删除 ${row.short_code}?删除后可在回收站恢复`)) return
  try {
    await shortlinkApi.remove(row.short_code)
    notify.success(`已删除 ${row.short_code}`)
    emit('refresh')
  } catch (e) {
    notify.error(e.message)
  }
}

async function onRestore(row) {
  try {
    await shortlinkApi.restore(row.short_code)
    notify.success(`已恢复 ${row.short_code}`)
    emit('refresh')
  } catch (e) {
    notify.error(e.message)
  }
}
</script>

<style scoped>
/* 宽表:横向滚动容器,保证不会撑破卡片/页面 */
.table-scroll {
  overflow-x: auto;
  border: 1px solid rgba(96, 165, 250, 0.12);
  border-radius: 12px;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
}

thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: #12121A;
  color: rgba(148, 163, 184, 0.75);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-weight: 500;
  text-align: left;
  padding: 10px 14px;
  white-space: nowrap;
  border-bottom: 1px solid rgba(96, 165, 250, 0.18);
}

tbody td {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.07);
  vertical-align: middle;
  white-space: nowrap;
}
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover td { background: rgba(59, 130, 246, 0.06); }

/* === 列宽 === */
.col-code   { width: 110px; }
.col-short  { min-width: 300px; }
.col-long   { min-width: 280px; max-width: 340px; }
.col-status { min-width: 140px; }
.col-num    { width: 84px; text-align: right; font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.col-time   { width: 152px; font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }
.col-extra  { width: 110px; }
.col-actions { width: 190px; }
.col-actions-head { text-align: left; }

/* 首列(短码)与末列(操作)吸附,横向滚动时始终可见 */
.col-code {
  position: sticky;
  left: 0;
  z-index: 2;
  background: #14141C;
}
.col-actions {
  position: sticky;
  right: 0;
  z-index: 2;
  background: #14141C;
  text-align: right;
}
thead .col-code, thead .col-actions { z-index: 4; background: #12121A; }
tbody tr:hover .col-code, tbody tr:hover .col-actions { background: #182031; }
.col-code { box-shadow: 1px 0 0 rgba(96, 165, 250, 0.14); }
.col-actions { box-shadow: -1px 0 0 rgba(96, 165, 250, 0.14); }

/* 仅在该方向确实可滚时,叠加一层向外衰减的阴影(1px 描边 + 软阴影) */
.table-scroll.is-scrolled-left .col-code {
  box-shadow:
    1px 0 0 rgba(96, 165, 250, 0.16),
    16px 0 24px -16px rgba(0, 0, 0, 0.95);
}
.table-scroll.is-scrolled-right .col-actions {
  box-shadow:
    -1px 0 0 rgba(96, 165, 250, 0.16),
    -16px 0 24px -16px rgba(0, 0, 0, 0.95);
}

/* === 单元格内容 === */
.code-link code {
  font-family: var(--font-mono);
  font-size: 12px;
  color: #67E8F9;
  background: rgba(34, 211, 238, 0.08);
  border: 1px solid rgba(103, 232, 249, 0.25);
  border-radius: 6px;
  padding: 3px 9px;
  text-shadow: 0 0 8px rgba(103, 232, 249, 0.35);
}
.code-link:hover code { border-color: rgba(103, 232, 249, 0.6); }

/* 短链列:URL 与复制图标共处一个圆角框内(点文字打开 / 点图标复制),
   视觉上是一个控件,而不是"文字 + 两个漂浮的方块" */
.short-field {
  display: flex;
  align-items: stretch;
  height: 30px;
  border: 1px solid rgba(96, 165, 250, 0.22);
  border-radius: 8px;
  background: rgba(11, 11, 16, 0.45);
  overflow: hidden;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.short-field:hover { border-color: rgba(96, 165, 250, 0.42); }

.short-url {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: #67E8F9;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* 分隔线画在这里,刚好落在 URL 区与图标之间 */
  border-right: 1px solid rgba(96, 165, 250, 0.18);
}
.short-url:hover { color: #A5F3FC; text-shadow: 0 0 8px rgba(103, 232, 249, 0.5); }

.mini-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  padding: 3px 10px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--text-muted);
  text-decoration: none;
  text-transform: none;
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast), box-shadow var(--t-fast), background var(--t-fast);
}
.mini-btn:hover {
  color: #67E8F9;
  border-color: #67E8F9;
  box-shadow: 0 0 8px var(--accent-2-glow);
}
.mini-btn:active { transform: translateY(1px); }
.mini-btn + .mini-btn { margin-left: 4px; }

.mini-btn.danger { color: #FCA5A5; border-color: rgba(239, 68, 68, 0.35); }
.mini-btn.danger:hover {
  background: rgba(239, 68, 68, 0.14);
  border-color: var(--danger);
  color: #FECACA;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.45);
}
.mini-btn.restore { color: #6EE7B7; border-color: rgba(16, 185, 129, 0.35); }
.mini-btn.restore:hover {
  background: rgba(16, 185, 129, 0.12);
  border-color: var(--success);
  color: #A7F3D0;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.45);
}

.long-url {
  display: block;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: none;
}
.long-url:hover { color: var(--accent-2); }

.pv { color: #67E8F9; text-shadow: 0 0 8px rgba(103, 232, 249, 0.4); }
.uv { color: #6EE7B7; }
.col-num.dim, .col-time.dim, .dim { color: var(--text-dim); }
.col-time.is-expired { color: #FCA5A5; }

.chip {
  display: inline-block;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(96, 165, 250, 0.10);
  border: 1px solid rgba(96, 165, 250, 0.28);
  color: #93C5FD;
}
.chip.domain { background: rgba(139, 92, 246, 0.10); border-color: rgba(139, 92, 246, 0.30); color: #C4B5FD; }

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
.mini-tag.deleted { background: rgba(148, 163, 184, 0.12); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3); }
.mini-tag.locked { background: rgba(139, 92, 246, 0.12); color: #C4B5FD; border: 1px solid rgba(139, 92, 246, 0.3); }

.empty {
  padding: 56px 24px;
  text-align: center;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.06em;
}
.empty::before {
  content: '∅';
  display: block;
  font-size: 32px;
  margin-bottom: 8px;
  color: rgba(96, 165, 250, 0.4);
}
.empty-link { color: #67E8F9; border-bottom: 1px dashed currentColor; }
</style>

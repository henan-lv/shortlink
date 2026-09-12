<template>
  <div class="page">
    <header class="page-head">      <h2>用户管理</h2>
      <p class="page-sub">对系统里的账号进行启用 / 停用、提权 / 降权、重置密码、删除,以及 API Key 重置</p>
    </header>

    <div class="glass-card list-card">
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="search-wrap">
          <svg class="search-ico" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="1.4" />
            <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          </svg>
          <input v-model="keyword" type="text" placeholder="搜索用户名" maxlength="64" spellcheck="false" />
        </div>
        <button type="button" class="ghost refresh-btn" :disabled="loading" @click="fetchList">
          {{ loading ? '加载中…' : '↻ 刷新' }}
        </button>
        <button type="button" class="primary create-btn" @click="openCreate">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" aria-hidden="true">
            <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <span>新建账号</span>
        </button>
      </div>

      <!-- 表格 -->
      <div v-if="loading && !items.length" class="loading-state">
        <span class="dot-pulse"></span>正在加载…
      </div>
      <div v-else-if="!filteredItems.length" class="empty">暂无符合条件的用户</div>
      <table v-else class="users-table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>角色</th>
            <th>状态</th>
            <th>API Key</th>
            <th>创建时间</th>
            <th class="op-col-head">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredItems" :key="row.id" :class="{ 'is-self': row.id === selfId }">
            <td>
              <div class="name-cell">
                <span class="name-text">{{ row.username }}</span>
                <span v-if="row.id === selfId" class="self-tag">你</span>
              </div>
            </td>
            <td>
              <span class="role-tag" :class="{ admin: row.is_admin }">
                {{ row.is_admin ? '管理员' : '普通用户' }}
              </span>
            </td>
            <td>
              <label class="switch" :title="row.is_active ? '点击停用' : '点击启用'">
                <input
                  type="checkbox"
                  :checked="row.is_active"
                  :disabled="row.id === selfId"
                  @change="toggleActive(row, $event.target.checked)"
                />
                <span class="switch-slider"></span>
                <span class="switch-text">{{ row.is_active ? '启用' : '停用' }}</span>
              </label>
            </td>
            <td>
              <div class="key-cell">
                <code v-if="row.api_key" class="key-code" :title="row.api_key">{{ maskKey(row.api_key) }}</code>
                <span v-else class="muted">—</span>
                <button v-if="row.api_key" type="button" class="key-copy" title="复制完整 Key" @click="copyKey(row)">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="9" y="9" width="12" height="12" rx="2.5" />
                    <path d="M6.5 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1.5" />
                  </svg>
                </button>
                <button v-if="row.api_key" type="button" class="key-regen" title="重置 Key" @click="regenKey(row)">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M3 12a9 9 0 0 1 15.5-6.3M21 12a9 9 0 0 1-15.5 6.3" />
                    <path d="M18 3v4h-4M6 21v-4h4" />
                  </svg>
                </button>
              </div>
            </td>
            <td class="time-cell">{{ formatTime(row.created_at) }}</td>
            <td class="op-cell">
              <button type="button" class="ghost mini" :disabled="row.id === selfId || (!row.is_admin && !row.is_active)" @click="openPwd(row)">
                重置密码
              </button>
              <button type="button" class="ghost mini" :disabled="row.is_admin" @click="openRole(row)" :title="row.is_admin ? '已是管理员' : '设为管理员'">
                {{ row.is_admin ? '降为用户' : '设为管理员' }}
              </button>
              <button type="button" class="ghost mini danger" :disabled="row.id === selfId" @click="onDelete(row)">
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 新建账号弹窗 -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
          <div class="modal-card">
            <header class="m-head">
              <div>                <h3 class="m-title">新建账号</h3>
              </div>
              <button class="m-close" type="button" aria-label="关闭" @click="showCreate = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <line x1="6" y1="6" x2="18" y2="18" />
                  <line x1="18" y1="6" x2="6" y2="18" />
                </svg>
              </button>
            </header>
            <div class="m-body">
              <label class="field">
                <span class="field-k">用户名</span>
                <input v-model="createForm.username" type="text" maxlength="64" spellcheck="false" placeholder="3 ~ 64 个字符" />
              </label>
              <label class="field">
                <span class="field-k">初始密码</span>
                <input v-model="createForm.password" type="text" maxlength="64" placeholder="至少 6 个字符" />
              </label>
              <label class="field-check">
                <input v-model="createForm.is_admin" type="checkbox" />
                <span>同时设为管理员</span>
              </label>
              <div v-if="createError" class="form-error">{{ createError }}</div>
            </div>
            <footer class="m-foot">
              <button type="button" class="ghost" @click="showCreate = false">取消</button>
              <button type="button" class="primary" :disabled="createSaving" @click="submitCreate">
                {{ createSaving ? '创建中…' : '创建' }}
              </button>
            </footer>
          </div>
        </div>
      </transition>
    </teleport>

    <!-- 重置密码弹窗 -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="showPwd" class="modal-mask" @click.self="showPwd = false">
          <div class="modal-card narrow">
            <header class="m-head">
              <div>                <h3 class="m-title">重置 {{ pwdTarget?.username }} 的密码</h3>
              </div>
              <button class="m-close" type="button" aria-label="关闭" @click="showPwd = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <line x1="6" y1="6" x2="18" y2="18" />
                  <line x1="18" y1="6" x2="6" y2="18" />
                </svg>
              </button>
            </header>
            <div class="m-body">
              <label class="field">
                <span class="field-k">新密码</span>
                <input v-model="pwdForm.password" type="text" maxlength="64" placeholder="至少 6 个字符" />
              </label>
              <div v-if="pwdError" class="form-error">{{ pwdError }}</div>
            </div>
            <footer class="m-foot">
              <button type="button" class="ghost" @click="showPwd = false">取消</button>
              <button type="button" class="primary" :disabled="pwdSaving" @click="submitPwd">
                {{ pwdSaving ? '提交中…' : '确认重置' }}
              </button>
            </footer>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { userApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import { useNotifyStore } from '@/stores/notify'

const auth = useAuthStore()
const notify = useNotifyStore()

const items = ref([])
const keyword = ref('')
const loading = ref(false)
const selfId = computed(() => auth.user?.id)

const filteredItems = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return items.value
  return items.value.filter((u) => u.username.toLowerCase().includes(k))
})

async function fetchList() {
  loading.value = true
  try {
    const res = await userApi.list()
    items.value = res.items || []
  } catch (e) {
    notify.error(e.message || '加载用户失败')
  } finally {
    loading.value = false
  }
}

async function toggleActive(row, val) {
  try {
    await userApi.update(row.id, { is_active: val })
    row.is_active = val
    notify.success(val ? '已启用' : '已停用')
  } catch (e) {
    notify.error(e.message || '操作失败')
    await fetchList()
  }
}

async function regenKey(row) {
  if (!window.confirm(`确认重置 ${row.username} 的 API Key?`)) return
  try {
    const res = await userApi.regenerateKey(row.id)
    row.api_key = res.api_key
    notify.success('API Key 已重置')
  } catch (e) {
    notify.error(e.message || '重置失败')
  }
}

async function copyKey(row) {
  if (!row.api_key) return
  try {
    await navigator.clipboard.writeText(row.api_key)
    notify.success('已复制 API Key')
  } catch (e) {
    notify.error('复制失败')
  }
}

function openRole(row) {
  if (row.is_admin) {
    if (!window.confirm(`将 ${row.username} 降为普通用户?`)) return
    updateRole(row, false)
  } else {
    updateRole(row, true)
  }
}

async function updateRole(row, val) {
  try {
    await userApi.update(row.id, { is_admin: val })
    row.is_admin = val
    notify.success(val ? '已设为管理员' : '已降为普通用户')
  } catch (e) {
    notify.error(e.message || '操作失败')
    await fetchList()
  }
}

async function onDelete(row) {
  if (!window.confirm(`确认删除用户 ${row.username}?删除后该账号将无法登录。`)) return
  try {
    await userApi.remove(row.id)
    items.value = items.value.filter((u) => u.id !== row.id)
    notify.success('已删除')
  } catch (e) {
    notify.error(e.message || '删除失败')
  }
}

// ===== 新建 =====
const showCreate = ref(false)
const createSaving = ref(false)
const createError = ref('')
const createForm = ref({ username: '', password: '', is_admin: false })

function openCreate() {
  createForm.value = { username: '', password: '', is_admin: false }
  createError.value = ''
  showCreate.value = true
}

async function submitCreate() {
  createError.value = ''
  const u = createForm.value.username.trim()
  const p = createForm.value.password.trim()
  if (!u || u.length < 3) { createError.value = '用户名至少 3 个字符'; return }
  if (!p || p.length < 6) { createError.value = '密码至少 6 个字符'; return }
  createSaving.value = true
  try {
    await userApi.create({ username: u, password: p, is_admin: !!createForm.value.is_admin })
    notify.success('已创建')
    showCreate.value = false
    await fetchList()
  } catch (e) {
    createError.value = e.message || '创建失败'
  } finally {
    createSaving.value = false
  }
}

// ===== 重置密码 =====
const showPwd = ref(false)
const pwdTarget = ref(null)
const pwdSaving = ref(false)
const pwdError = ref('')
const pwdForm = ref({ password: '' })

function openPwd(row) {
  pwdTarget.value = row
  pwdForm.value = { password: '' }
  pwdError.value = ''
  showPwd.value = true
}

async function submitPwd() {
  pwdError.value = ''
  const p = pwdForm.value.password.trim()
  if (!p || p.length < 6) { pwdError.value = '密码至少 6 个字符'; return }
  pwdSaving.value = true
  try {
    await userApi.update(pwdTarget.value.id, { password: p })
    notify.success('密码已重置')
    showPwd.value = false
  } catch (e) {
    pwdError.value = e.message || '重置失败'
  } finally {
    pwdSaving.value = false
  }
}

function maskKey(k) {
  if (!k || k.length < 10) return k
  return k.slice(0, 6) + '…' + k.slice(-4)
}

function formatTime(s) {
  if (!s) return '—'
  try {
    const d = new Date(s)
    if (isNaN(d.getTime())) return s
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch { return s }
}

onMounted(fetchList)
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.page-head { display: flex; flex-direction: column; gap: 4px; }
.page-head h2 { margin: 0; padding-left: 14px; }
.page-eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.24em;
  color: rgba(244, 114, 182, 0.75);
  margin-bottom: 2px;
}
.page-sub {
  margin: 0;
  padding-left: 14px;
  color: var(--text-muted);
  font-size: 13px;
}

/* === 卡片(复用) === */
.glass-card {
  position: relative;
  background:
    linear-gradient(180deg, rgba(30, 30, 35, 0.78), rgba(20, 20, 28, 0.78)) padding-box,
    linear-gradient(135deg, rgba(244, 114, 182, 0.45), rgba(139, 92, 246, 0.18) 60%, rgba(96, 165, 250, 0.32)) border-box;
  border: 1px solid transparent;
  border-radius: 20px;
  padding: 22px;
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  box-shadow:
    0 0 0 1px rgba(244, 114, 182, 0.08),
    0 18px 48px -16px rgba(0, 0, 0, 0.65),
    0 0 64px -24px rgba(244, 114, 182, 0.35);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 200px;
  max-width: 360px;
}
.search-ico {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-dim);
}
.search-wrap input {
  width: 100%;
  padding: 8px 12px 8px 32px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.search-wrap input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent), 0 0 12px var(--accent-glow);
}
.toolbar .ghost,
.toolbar .primary {
  flex: 0 0 auto;
}
.create-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* === 表格 === */
.users-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 12px;
}
.users-table th, .users-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(96, 165, 250, 0.08);
}
.users-table th {
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-dim);
  font-weight: 600;
}
.users-table tbody tr:hover {
  background: rgba(244, 114, 182, 0.04);
}
.users-table tbody tr.is-self {
  background: rgba(34, 211, 238, 0.04);
}
.op-col-head { text-align: left; }

.name-cell { display: inline-flex; align-items: center; gap: 8px; }
.name-text { color: var(--text); font-weight: 500; }
.self-tag {
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--accent-2);
  padding: 2px 6px;
  border: 1px solid rgba(103, 232, 249, 0.4);
  border-radius: 999px;
  background: rgba(34, 211, 238, 0.08);
}

.role-tag {
  font-size: 10px;
  letter-spacing: 0.1em;
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-muted);
  background: rgba(11, 11, 16, 0.4);
}
.role-tag.admin {
  color: #F472B6;
  border-color: rgba(244, 114, 182, 0.45);
  background: rgba(244, 114, 182, 0.08);
}

/* 开关 */
.switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.switch input { display: none; }
.switch-slider {
  position: relative;
  width: 30px;
  height: 16px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid var(--border);
  border-radius: 999px;
  transition: background var(--t-fast), border-color var(--t-fast);
}
.switch-slider::after {
  content: '';
  position: absolute;
  left: 2px; top: 50%;
  transform: translateY(-50%);
  width: 10px; height: 10px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: left var(--t-fast), background var(--t-fast);
}
.switch input:checked + .switch-slider {
  background: rgba(16, 185, 129, 0.25);
  border-color: rgba(16, 185, 129, 0.6);
}
.switch input:checked + .switch-slider::after {
  left: 16px;
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
}
.switch input:disabled + .switch-slider { opacity: 0.5; cursor: not-allowed; }
.switch-text { font-size: 11px; color: var(--text-muted); }
.switch input:checked ~ .switch-text { color: var(--success); }

/* API Key */
.key-cell { display: inline-flex; align-items: center; gap: 6px; }
.key-code {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 11px;
  letter-spacing: 0.04em;
}
.muted { color: var(--text-dim); }
.key-copy, .key-regen {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 6px;
  color: var(--accent-2);
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast), background var(--t-fast), box-shadow var(--t-fast);
  padding: 0;
  flex: 0 0 auto;
}
.key-copy svg, .key-regen svg {
  width: 14px;
  height: 14px;
  display: block;
  stroke: currentColor;
}
.key-copy:hover, .key-regen:hover {
  color: #A5F3FC;
  border-color: var(--accent-2);
  background: rgba(34, 211, 238, 0.15);
  box-shadow: 0 0 10px -2px var(--accent-2-glow);
}

.time-cell { color: var(--text-muted); font-size: 11px; }

/* 操作列 */
.op-cell { display: flex; flex-wrap: wrap; gap: 6px; }
.op-cell .ghost.mini {
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 4px 9px;
}
.op-cell .ghost.mini:disabled { opacity: 0.4; cursor: not-allowed; }
.op-cell .ghost.mini.danger:hover {
  color: var(--danger);
  border-color: var(--danger);
}

.loading-state, .empty {
  text-align: center;
  color: var(--text-muted);
  padding: 30px 0;
  font-family: var(--font-mono);
  font-size: 12px;
}
.dot-pulse {
  display: inline-block;
  width: 8px; height: 8px;
  background: var(--accent-2);
  border-radius: 50%;
  margin-right: 8px;
  box-shadow: 0 0 8px var(--accent-2-glow);
  animation: pulse-glow 1.4s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* === 弹窗(与 Generate 弹窗风格一致) === */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.62);
  backdrop-filter: blur(10px) saturate(120%);
  -webkit-backdrop-filter: blur(10px) saturate(120%);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.modal-card {
  width: 100%;
  max-width: 460px;
  background:
    linear-gradient(180deg, rgba(30, 30, 35, 0.92), rgba(20, 20, 28, 0.92)) padding-box,
    linear-gradient(135deg, rgba(244, 114, 182, 0.55), rgba(139, 92, 246, 0.32) 55%, rgba(96, 165, 250, 0.4)) border-box;
  border: 1px solid transparent;
  border-radius: 16px;
  padding: 22px 24px;
  box-shadow:
    0 0 0 1px rgba(244, 114, 182, 0.16),
    0 32px 80px -20px rgba(0, 0, 0, 0.75),
    0 0 80px -24px rgba(244, 114, 182, 0.55);
}
.modal-card.narrow { max-width: 400px; }
.m-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.m-eyebrow {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.24em;
  color: rgba(244, 114, 182, 0.85);
  padding: 3px 9px;
  border: 1px solid rgba(244, 114, 182, 0.35);
  border-radius: 999px;
  background: rgba(244, 114, 182, 0.08);
  margin-bottom: 8px;
}
.m-title { margin: 0; font-size: 18px; color: var(--text); }
.m-close {
  width: 30px; height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast);
}
.m-close:hover { color: var(--text); border-color: var(--border-bright); }

.m-body { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field-k {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.field input {
  padding: 9px 12px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.field input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent), 0 0 12px var(--accent-glow);
}
.field-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
  cursor: pointer;
}
.field-check input { accent-color: var(--accent); }
.form-error {
  color: #FCA5A5;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
  font-family: var(--font-mono);
}

.m-foot {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 18px;
}

.modal-enter-active, .modal-leave-active { transition: opacity 240ms ease; }
.modal-enter-active .modal-card, .modal-leave-active .modal-card { transition: opacity 280ms ease, transform 280ms cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-card, .modal-leave-to .modal-card { opacity: 0; transform: translateY(16px) scale(0.96); }
</style>

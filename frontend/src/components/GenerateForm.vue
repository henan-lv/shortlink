<template>
  <div class="glass-card form-card">
    <form @submit.prevent="onSubmit">
      <!-- ===== 基础字段 ===== -->
      <div class="form-row">
        <label>长链接 <span class="req">*</span></label>
        <div class="input-wrap">
          <svg class="input-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M6.5 9.5l3-3M5 7l-1.5 1.5a2.121 2.121 0 003 3L8 10m3-3l1.5-1.5a2.121 2.121 0 00-3-3L8 6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
          <input v-model="longUrl" type="text" placeholder="https://example.com/very/long/url" required />
        </div>
      </div>

      <!-- ===== 快捷选项:有效期 / 点击上限 ===== -->
      <!-- 与下方"生效时间"共用 .seg-row 内联布局:自定义控件出现在分段按钮右侧,
           而不是另起一行,避免切换时行高变化导致整页抖动 -->
      <div class="quick-grid">
        <div class="form-row">
          <label>有效期 <span class="opt">(默认 7 天)</span></label>
          <div class="seg-row">
            <div class="seg">
              <button type="button" v-for="d in expiryPresets" :key="d.value"
                      class="seg-btn" :class="{ 'is-active': expiryChoice === d.value }"
                      @click="applyExpiry(d.value)">{{ d.label }}</button>
              <button type="button" class="seg-btn" :class="{ 'is-active': expiryChoice === 'custom' }"
                      @click="expiryChoice = 'custom'">自定义</button>
            </div>
            <DateTimePicker v-if="expiryChoice === 'custom'"
                            :model-value="expireAt" placeholder="选择到期时间"
                            @update:model-value="onExpiryPicked" />
            <span v-else class="inline-note">
              <span class="note-dot"></span>
              <span class="note-text">将于 <code>{{ formatPreview(expireAt) }}</code> 到期</span>
            </span>
          </div>
        </div>

        <div class="form-row">
          <label>点击上限 <span class="opt">(默认 1000 次)</span></label>
          <div class="seg-row">
            <div class="seg">
              <button type="button" v-for="n in clickPresets" :key="n"
                      class="seg-btn" :class="{ 'is-active': clickChoice === n }"
                      @click="applyClick(n)">{{ n >= 10000 ? (n / 1000) + 'k' : n }}</button>
              <button type="button" class="seg-btn" :class="{ 'is-active': clickChoice === 'unlimited' }"
                      @click="applyClickUnlimited">不限</button>
              <button type="button" class="seg-btn" :class="{ 'is-active': clickChoice === 'custom' }"
                      @click="clickChoice = 'custom'">自定义</button>
            </div>
            <label v-if="clickChoice === 'custom'" class="num-picker" :class="{ 'is-error': !!clickCustomError }">
              <svg class="num-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M4 2v10M10 2v10M2 5h10M2 9h10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
              </svg>
              <input v-model.number="clickLimit" type="number" min="1" step="1" placeholder="自定义次数" />
              <span class="num-suffix">次</span>
            </label>
            <span v-else-if="clickChoice === 'unlimited'" class="inline-note">
              <span class="note-dot"></span>
              <span class="note-text">不限制访问次数</span>
            </span>
            <span v-else class="inline-note">
              <span class="note-dot"></span>
              <span class="note-text">达到 <code>{{ clickChoice }}</code> 次后停止跳转</span>
            </span>
          </div>
        </div>
      </div>

      <!-- ===== 生效时间 + 访问密码(同行,与上方的快捷选项对齐) ===== -->
      <div class="quick-grid">
        <div class="form-row">
          <label>生效时间 <span class="opt">(默认立即)</span></label>
          <div class="seg-row">
            <div class="seg">
              <button type="button" class="seg-btn" :class="{ 'is-active': effectiveChoice === 'now' }"
                      @click="applyEffective('now')">立即</button>
              <button type="button" class="seg-btn" :class="{ 'is-active': effectiveChoice === '1h' }"
                      @click="applyEffective('1h')">1 小时后</button>
              <button type="button" class="seg-btn" :class="{ 'is-active': effectiveChoice === 'tomorrow' }"
                      @click="applyEffective('tomorrow')">明天</button>
              <button type="button" class="seg-btn" :class="{ 'is-active': effectiveChoice === 'custom' }"
                      @click="effectiveChoice = 'custom'">自定义</button>
            </div>
            <!-- 自定义日期+时间选择器(与"有效期"共用同一组件,保证视觉一致) -->
            <DateTimePicker v-if="effectiveChoice === 'custom'"
                            :model-value="effectiveAt" placeholder="选择生效时间"
                            @update:model-value="onEffectivePicked" />
            <span v-else-if="effectiveAt" class="inline-note">
              <span class="note-dot"></span>
              <span class="note-text">将于 <code>{{ formatPreview(effectiveAt) }}</code> 开始生效</span>
            </span>
            <!-- "立即"也保留同结构的内联说明:窄屏下内联控件会换行,
                 若此态不渲染任何元素,该列会比其它状态矮 40+px,切换时整页跳动 -->
            <span v-else class="inline-note">
              <span class="note-dot"></span>
              <span class="note-text">立即生效,创建后即可访问</span>
            </span>
          </div>
        </div>
        <div class="form-row">
          <label>访问密码 <span class="opt">(选填, 6-8 位)</span></label>
          <div class="input-wrap">
            <svg class="input-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="3" y="7" width="10" height="6.5" rx="1.4" stroke="currentColor" stroke-width="1.4"/>
              <path d="M5.5 7V5a2.5 2.5 0 015 0v2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            <input v-model="password" type="password" placeholder="留空表示无密码" minlength="6" maxlength="8" />
          </div>
        </div>
      </div>

      <!-- ===== 自定义域名 + 渠道(同行,与上方节奏一致) ===== -->
      <div class="quick-grid">
        <div class="form-row">
          <label>自定义域名 <span class="opt">(默认使用基础域名)</span></label>
          <div class="input-wrap">
            <svg class="input-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/>
              <path d="M2 8h12M8 2c2 2 2 10 0 12M8 2c-2 2-2 10 0 12" stroke="currentColor" stroke-width="1.4"/>
            </svg>
            <input v-model="domain" type="text" placeholder="如 s.example.com (不含 http://)" maxlength="128" spellcheck="false" />
          </div>
        </div>
        <div class="form-row">
          <label>渠道 <span class="opt">(不区分大小写)</span></label>
          <div class="input-wrap">
            <svg class="input-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3 5h10M3 8h10M3 11h6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            <input v-model="channel" type="text" placeholder="如 wechat / app" maxlength="32" spellcheck="false" />
          </div>
        </div>
      </div>

      <!-- ===== 高级设置:访问控制(风控) ===== -->
      <div class="advanced">
        <button type="button" class="advanced-toggle" @click="advancedOpen = !advancedOpen">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"
               :style="{ transform: advancedOpen ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 200ms' }">
            <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>高级设置 · 访问控制</span>
          <span class="advanced-meta">{{ advancedConfigured ? '已配置' : '未配置' }}</span>
        </button>

        <transition name="adv">
          <div v-if="advancedOpen" class="advanced-body">
            <div class="advanced-hint">
              <span class="hint-dot"></span>
              配置后将在<strong>跳转时</strong>对访问者做拦截;留空表示不做访问控制。规则随短链保存,之后可在统计页查看并追加。
            </div>

            <div class="ac-grid">
              <div class="ac-field">
                <label class="ac-label">
                  拦截 IP / 网段
                  <span class="ac-tag">黑名单</span>
                </label>
                <textarea v-model="acBlockIps" class="ac-area" rows="3" spellcheck="false"
                          placeholder="每行一个,如&#10;1.2.3.4&#10;10.0.0.0/8"></textarea>
                <span v-if="acBlockIpsError" class="ac-error">{{ acBlockIpsError }}</span>
              </div>

              <div class="ac-field">
                <label class="ac-label">
                  仅放行 IP / 网段
                  <span class="ac-tag warn">白名单</span>
                </label>
                <textarea v-model="acAllowIps" class="ac-area" rows="3" spellcheck="false"
                          placeholder="填写后,不在名单内的访问一律拒绝&#10;203.0.113.0/24"></textarea>
                <span v-if="acAllowIpsError" class="ac-error">{{ acAllowIpsError }}</span>
                <span v-else-if="acAllowIps.trim()" class="ac-note">已开启白名单:未命中即拒绝</span>
              </div>
            </div>

            <div class="ac-grid">
              <div class="ac-field">
                <label class="ac-label">拦截 UA 关键词</label>
                <input v-model="acBlockUa" class="ac-input" type="text" spellcheck="false"
                       placeholder="逗号分隔,如 bot, spider" />
              </div>
              <div class="ac-field">
                <label class="ac-label">拦截 Referer 关键词</label>
                <input v-model="acBlockReferer" class="ac-input" type="text" spellcheck="false"
                       placeholder="逗号分隔,如 spam.example" />
              </div>
            </div>

            <div class="ac-field">
              <label class="ac-label">命中动作</label>
              <div class="seg">
                <button type="button" class="seg-btn" :class="{ 'is-active': acAction === 'block' }"
                        @click="acAction = 'block'">直接拦截</button>
                <button type="button" class="seg-btn" :class="{ 'is-active': acAction === 'observe' }"
                        @click="acAction = 'observe'">仅观察(先看再拦)</button>
              </div>
            </div>

            <div class="advanced-preview">
              <div class="preview-head">
                <span class="preview-title">提交内容</span>
                <span class="preview-state" :class="{ on: advancedConfigured }">
                  {{ advancedConfigured ? '将随短链提交' : '留空不提交' }}
                </span>
              </div>
              <pre class="preview-json">{{ advancedPreview }}</pre>
            </div>
          </div>
        </transition>
      </div>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

      <button type="submit" class="primary submit-btn" :disabled="loading">
        <span v-if="!loading" class="btn-inner">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M7 1.5v11M2 7l5 5 5-5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          生成短链
        </span>
        <span v-else class="btn-inner">
          <span class="dot-pulse"></span>生成中…
        </span>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { shortlinkApi } from '@/api/shortlink'
import DateTimePicker from './DateTimePicker.vue'

const emit = defineEmits(['created'])

// ===== 基础字段 =====
const longUrl = ref('')
const password = ref('')
const expireAt = ref('')
const errorMsg = ref('')
const loading = ref(false)

// ===== 有效期预设 =====
const expiryPresets = [
  { label: '1 天', value: 1 },
  { label: '7 天', value: 7 },
  { label: '30 天', value: 30 },
  { label: '90 天', value: 90 },
]
const expiryChoice = ref(7)            // 默认 7 天
applyExpiry(7)                          // 写默认值到 expireAt

function applyExpiry(days) {
  expiryChoice.value = days
  const d = new Date()
  d.setDate(d.getDate() + Number(days))
  // 统一存 'YYYY-MM-DDTHH:mm',与 DateTimePicker 的 v-model 格式一致
  const pad = (n) => String(n).padStart(2, '0')
  expireAt.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 用户在日历里"确定"后才回调,因此可直接判定为自定义
function onExpiryPicked(v) {
  expireAt.value = v
  expiryChoice.value = 'custom'
}

// ===== 点击上限 =====
// clickChoice: 预设数值 | 'unlimited' | 'custom'(仅 UI 状态)
// clickLimit:  实际提交的数值,null 表示不限
const clickPresets = [100, 1000, 10000, 100000]
const clickChoice = ref(1000)
const clickLimit = ref(1000)

function applyClick(n) {
  clickChoice.value = n
  clickLimit.value = n
}
function applyClickUnlimited() {
  clickChoice.value = 'unlimited'
  clickLimit.value = null
}
const clickCustomError = computed(() => {
  if (clickChoice.value !== 'custom') return ''
  const n = Number(clickLimit.value)
  if (!clickLimit.value || !Number.isInteger(n) || n < 1) return '请填写大于 0 的整数'
  return ''
})

// ===== 生效时间(默认立即) =====
const effectiveAt = ref('')             // 'YYYY-MM-DDTHH:mm'
const effectiveChoice = ref('now')      // 'now' | '1h' | 'tomorrow' | 'custom'
applyEffective('now')                   // 立即 → 写当前时间

function applyEffective(mode) {
  effectiveChoice.value = mode
  if (mode === 'now') {
    effectiveAt.value = ''               // 留空,后端理解为立即生效
    return
  }
  const d = new Date()
  if (mode === '1h') d.setHours(d.getHours() + 1)
  else if (mode === 'tomorrow') d.setDate(d.getDate() + 1)
  const pad = (n) => String(n).padStart(2, '0')
  effectiveAt.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function onEffectivePicked(v) {
  effectiveAt.value = v
  effectiveChoice.value = 'custom'
}

const effectiveCustomError = computed(() =>
  effectiveChoice.value === 'custom' && !effectiveAt.value ? '请选择生效时间' : ''
)

function formatPreview(v) {
  if (!v) return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return v
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ===== 自定义域名 + 渠道 =====
const domain = ref('')
const channel = ref('')

// ===== 高级设置:访问控制(风控) =====
// 结构化填写,实时生成与后端 services/access_control.parse_advanced 一致的 advanced 结构
const advancedOpen = ref(false)
const acBlockIps = ref('')
const acBlockUa = ref('')
const acBlockReferer = ref('')
const acAllowIps = ref('')
const acAction = ref('block')

function splitList(s) {
  return String(s || '')
    .split(/[\n,;]/)
    .map((x) => x.trim())
    .filter(Boolean)
}

function isValidIpOrCidr(v) {
  const s = String(v || '').trim()
  if (!s) return false
  const slash = s.indexOf('/')
  const addr = slash === -1 ? s : s.slice(0, slash)
  if (slash !== -1) {
    const n = Number(s.slice(slash + 1))
    if (!Number.isInteger(n) || n < 0 || n > 128) return false
  }
  if (addr.includes(':')) {
    // IPv6 宽松校验:仅允许十六进制与冒号
    return /^[0-9a-fA-F:]+$/.test(addr) && addr.split(':').length >= 3
  }
  const parts = addr.split('.')
  if (parts.length !== 4) return false
  return parts.every((p) => /^\d{1,3}$/.test(p) && Number(p) <= 255)
}

function invalidEntries(raw) {
  return splitList(raw).filter((v) => !isValidIpOrCidr(v))
}

const acBlockIpsError = computed(() => {
  const bad = invalidEntries(acBlockIps.value)
  return bad.length ? `格式不合法:${bad.join(', ')}` : ''
})
const acAllowIpsError = computed(() => {
  const bad = invalidEntries(acAllowIps.value)
  return bad.length ? `格式不合法:${bad.join(', ')}` : ''
})

// 只有填了内容才产出 advanced;全空 = 不做访问控制
const advancedPayload = computed(() => {
  const ac = {}
  const blockIps = splitList(acBlockIps.value)
  if (blockIps.length) ac.block_ips = blockIps
  const blockUa = splitList(acBlockUa.value)
  if (blockUa.length) ac.block_ua = blockUa
  const blockRef = splitList(acBlockReferer.value)
  if (blockRef.length) ac.block_referer = blockRef
  const allowIps = splitList(acAllowIps.value)
  if (allowIps.length) ac.allow_ips = allowIps
  if (!Object.keys(ac).length) return null
  ac.action = acAction.value
  return { access_control: ac }
})

const advancedConfigured = computed(() => advancedPayload.value !== null)

const advancedPreview = computed(() =>
  advancedPayload.value ? JSON.stringify(advancedPayload.value, null, 2) : '{}'
)

function resetAdvanced() {
  acBlockIps.value = ''
  acBlockUa.value = ''
  acBlockReferer.value = ''
  acAllowIps.value = ''
  acAction.value = 'block'
}

function buildPayload() {
  const data = { long_url: longUrl.value }
  if (password.value) data.password = password.value
  if (expireAt.value) data.expire_at = new Date(expireAt.value).toISOString()
  // 点击上限:'不限'不提交 click_limit;预设/自定义提交正整数
  const clickNum = Number(clickLimit.value)
  if (clickChoice.value !== 'unlimited' && Number.isInteger(clickNum) && clickNum > 0) {
    data.click_limit = clickNum
  }
  // 生效时间:仅在非"立即"且有值时提交
  if (effectiveChoice.value !== 'now' && effectiveAt.value) {
    data.effective_at = new Date(effectiveAt.value).toISOString()
  }
  // 自定义域名 / 渠道:strip 后非空才提交(后端会归一化空白 → null)
  const dom = domain.value.trim()
  if (dom) data.domain = dom
  const ch = channel.value.trim()
  if (ch) data.channel = ch
  // 高级设置:全空不提交;有内容则提交结构化访问控制配置
  if (advancedPayload.value) data.advanced = advancedPayload.value
  return data
}
async function onSubmit() {
  errorMsg.value = ''
  // 自定义控件未填完整时提前拦截,避免静默降级(如"自定义生效时间"实际按立即生效提交)
  if (clickCustomError.value) {
    errorMsg.value = `点击上限:${clickCustomError.value}`
    return
  }
  if (effectiveCustomError.value) {
    errorMsg.value = effectiveCustomError.value
    return
  }
  // 高级设置校验:IP / 网段格式不合法 → 提前拦截
  if (acBlockIpsError.value || acAllowIpsError.value) {
    errorMsg.value = '高级设置中的 IP / 网段格式不正确,请检查'
    advancedOpen.value = true
    return
  }
  loading.value = true
  try {
    const data = buildPayload()
    const result = await shortlinkApi.create(data)
    emit('created', result)
    longUrl.value = ''
    password.value = ''
    domain.value = ''
    channel.value = ''
    resetAdvanced()
    applyExpiry(7)
    applyClick(1000)
    applyEffective('now')
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.form-card { padding: 28px; }
.form-row { margin-bottom: 16px; }

/* ===== 快捷选项:分段按钮 + 自定义输入 ===== */
.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}
.quick-grid .form-row { margin-bottom: 0; }

/* 第二组快捷行(生效时间 + 访问密码)与上一组共享 .quick-grid 网格,自动 1fr 1fr 对齐 */
.quick-grid + .quick-grid { margin-top: -2px; }  /* 与上一组紧凑一点,但保持 16px 节奏 */

@media (max-width: 720px) {
  /* 移动端:网格已塌成单列,不需要额外样式 */
}
.seg-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  /* 统一控件高度:.seg 自然高度 36px(4px 内边距 + 26px 按钮 + 2px 边框)。
     右侧内联控件全部锁定到同一高度,切换自定义/不限时行高恒定,不会抖动。
     该变量会继承进 DateTimePicker 的 .dt-trigger。 */
  --ctrl-h: 36px;
}
.seg-row .seg { flex: 0 0 auto; }

/* 分段按钮右侧的内联控件:自定义输入 / 状态说明。
   高度统一、始终与分段按钮同行 → 切换时行高不变,不会有布局抖动 */
.seg-row .inline-note,
.seg-row .num-picker {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  height: var(--ctrl-h);
  box-sizing: border-box;
  align-self: center;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 10px;
  background: rgba(96, 165, 250, 0.06);
  border: 1px solid rgba(96, 165, 250, 0.18);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-muted);
}
.seg-row .note-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.inline-note code { color: #67E8F9; background: transparent; padding: 0; }
.note-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #67E8F9; box-shadow: 0 0 8px #67E8F9;
  flex: 0 0 auto;
}

/* ===== 数字自定义输入(点击上限) =====
   .num-picker 是 <label>,会命中全局 `.form-row label`(字号/字距/大小写/margin-bottom),
   因此上面那条共享规则里必须显式覆盖,否则会多出 8px 下边距并污染输入框排版。 */
.seg-row .num-picker {
  gap: 8px;
  background: rgba(11, 11, 16, 0.55);
  font-size: 12px;
  color: var(--text);
  cursor: text;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.num-picker:focus-within {
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.1);
}
.num-picker.is-error {
  border-color: rgba(239, 68, 68, 0.5);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.08);
}
.num-icon { color: #67E8F9; flex: 0 0 auto; }
.num-picker input {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
  padding: 0;
  background: transparent;
  border: 0;
  outline: none;
  color: var(--text);
  font-family: inherit;
  font-size: inherit;
  letter-spacing: inherit;
  text-transform: inherit;
  -moz-appearance: textfield;
}
.num-picker input::-webkit-outer-spin-button,
.num-picker input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.num-picker input::placeholder { color: var(--text-dim); opacity: 0.7; }
.num-suffix { color: var(--text-muted); flex: 0 0 auto; font-size: 11px; }
@media (max-width: 720px) {
  .seg-row { flex-direction: column; align-items: stretch; }
  .seg-row .inline-note,
  .seg-row .num-picker,
  .seg-row .dt-picker { width: 100%; }
}
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
  text-transform: none;
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

/* ===== 高级设置 ===== */
.advanced {
  margin-bottom: 18px;
  border: 1px solid rgba(96, 165, 250, 0.15);
  border-radius: 12px;
  background: rgba(11, 11, 16, 0.35);
  overflow: hidden;
}
.advanced-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: transparent;
  border: 0;
  border-radius: 0;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  text-align: left;
}
.advanced-toggle:hover { color: var(--text); background: rgba(96, 165, 250, 0.05); }
.advanced-toggle:active { transform: none; }
.advanced-meta {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(103, 232, 249, 0.10);
  border: 1px solid rgba(103, 232, 249, 0.28);
  color: #67E8F9;
  font-size: 10px;
  letter-spacing: 0.06em;
}
.advanced-body {
  padding: 4px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.advanced-hint {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-muted);
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(96, 165, 250, 0.05);
}
.advanced-hint code {
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(11, 11, 16, 0.6);
  color: #67E8F9;
  border: 1px solid rgba(103, 232, 249, 0.25);
}
.advanced-hint strong {
  color: #67E8F9;
  font-weight: 600;
}
.hint-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: #67E8F9;
  box-shadow: 0 0 6px #67E8F9;
  flex-shrink: 0;
  margin-top: 6px;
}

/* ===== 高级设置:访问控制表单 ===== */
.ac-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.ac-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.ac-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  margin: 0;
  text-transform: none;
}
.ac-tag {
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 9.5px;
  letter-spacing: 0.06em;
  color: #6EE7B7;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.ac-tag.warn {
  color: #FBBF24;
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.32);
}
.ac-area,
.ac-input {
  width: 100%;
  padding: 9px 12px;
  background: rgba(11, 11, 16, 0.7);
  border: 1px solid rgba(96, 165, 250, 0.22);
  border-radius: 10px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  outline: none;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.ac-area { resize: vertical; min-height: 68px; }
.ac-area::placeholder,
.ac-input::placeholder { color: var(--text-dim); opacity: 0.7; }
.ac-area:focus,
.ac-input:focus {
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.1);
}
.ac-error {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--danger);
}
.ac-note {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: #FBBF24;
}

.advanced-preview {
  margin-top: 4px;
  border: 1px solid rgba(96, 165, 250, 0.15);
  border-radius: 10px;
  background: rgba(11, 11, 16, 0.5);
  overflow: hidden;
}
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(96, 165, 250, 0.1);
}
.preview-title {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--text-dim);
  text-transform: uppercase;
}
.preview-state {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  color: var(--text-dim);
}
.preview-state.on { color: #67E8F9; }
.preview-json {
  margin: 0;
  padding: 10px 12px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.6;
  color: #A5F3FC;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow: auto;
}

/* 折叠过渡 */
.adv-enter-active, .adv-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}
.adv-enter-from, .adv-leave-to { opacity: 0; transform: translateY(-4px); }

/* ===== 响应式 ===== */
@media (max-width: 640px) {
  .quick-grid { grid-template-columns: 1fr; }
  .ac-grid { grid-template-columns: 1fr; }
}
.form-row label {
  display: block;
  font-family: var(--font-mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  margin-bottom: 8px;
  color: var(--text-muted);
}
.form-row .req { color: #67E8F9; }
.form-row .opt { color: var(--text-dim); text-transform: none; letter-spacing: 0.04em; font-size: 10px; margin-left: 4px; }

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-dim);
  pointer-events: none;
  transition: color var(--t-fast);
}
.input-wrap input { padding-left: 38px; }
.input-wrap:focus-within .input-icon { color: #67E8F9; }

.submit-btn {
  width: 100%;
  margin-top: 6px;
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 14px;
  letter-spacing: 0.06em;
}
.btn-inner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.dot-pulse {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 8px currentColor;
  animation: pulse-glow 1s ease-in-out infinite;
}
</style>

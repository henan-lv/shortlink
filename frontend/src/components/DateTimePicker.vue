<template>
  <div class="dt-picker" :class="{ 'is-open': dtOpen, 'has-value': !!modelValue }">
    <button type="button" class="dt-trigger" @click="openDt">
      <svg class="dt-icon-prefix" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
        <rect x="2" y="3" width="10" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/>
        <path d="M2 6h10" stroke="currentColor" stroke-width="1.3"/>
        <path d="M5 2v2M9 2v2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
      </svg>
      <span class="dt-text" :class="{ 'is-empty': !modelValue }">
        {{ modelValue ? formatDateTime(modelValue) : placeholder }}
      </span>
      <svg class="dt-icon-suffix" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        <path d="M3 5l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <transition name="dt-pop">
      <div v-if="dtOpen" v-click-outside="closeDt" class="dt-popover">
        <div class="dt-cal">
          <div class="dt-cal-head">
            <button type="button" class="dt-nav" @click="prevMonth" aria-label="上一月">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M9 3L5 7l4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <div class="dt-title">
              <span class="dt-title-y">{{ calYear }}年</span>
              <span class="dt-title-m">{{ calMonth + 1 }}月</span>
            </div>
            <button type="button" class="dt-nav" @click="nextMonth" aria-label="下一月">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M5 3l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
          <div class="dt-cal-grid">
            <span v-for="d in DOW" :key="d" class="dt-dow-cell">{{ d }}</span>
            <button v-for="(c, i) in calCells" :key="i" type="button"
                    class="dt-day"
                    :class="{ 'is-other': c.other, 'is-today': c.today, 'is-selected': c.selected, 'is-disabled': c.disabled }"
                    :disabled="c.disabled"
                    @click="pickDay(c)">{{ c.day }}</button>
          </div>
        </div>
        <div class="dt-time">
          <span class="dt-time-label">时间</span>
          <div class="dt-time-inputs">
            <input v-model.number="tempHour" type="number" min="0" max="23" class="dt-num" />
            <span class="dt-time-sep">:</span>
            <input v-model.number="tempMinute" type="number" min="0" max="59" step="1" class="dt-num" />
          </div>
          <button type="button" class="dt-now" @click="setNow">现在</button>
        </div>
        <div class="dt-foot">
          <button type="button" class="dt-btn dt-btn-ghost" @click="closeDt">取消</button>
          <button type="button" class="dt-btn dt-btn-primary" @click="confirmDt" :disabled="!tempDate">确定</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  // 值为 'YYYY-MM-DDTHH:mm'(与原生 datetime-local 一致),空串表示未选择
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '选择时间' },
})
const emit = defineEmits(['update:modelValue'])

const DOW = ['日', '一', '二', '三', '四', '五', '六']

const dtOpen = ref(false)
const calYear = ref(new Date().getFullYear())
const calMonth = ref(new Date().getMonth())
const tempDate = ref(null)             // 'YYYY-MM-DD' | null
const tempHour = ref(new Date().getHours())
const tempMinute = ref(new Date().getMinutes())

const pad2 = (n) => String(n).padStart(2, '0')
const toYMD = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
const parseYMD = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d) }

function formatDateTime(v) {
  if (!v) return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return v
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

const calCells = computed(() => {
  const first = new Date(calYear.value, calMonth.value, 1)
  const startDow = first.getDay()
  const daysInMonth = new Date(calYear.value, calMonth.value + 1, 0).getDate()
  const daysInPrev = new Date(calYear.value, calMonth.value, 0).getDate()
  const cells = []
  const today = new Date()
  const todayStr = toYMD(today)
  for (let i = 0; i < 42; i++) {
    let day, other = false, y, m
    if (i < startDow) {
      day = daysInPrev - startDow + i + 1
      other = true
      y = calMonth.value === 0 ? calYear.value - 1 : calYear.value
      m = (calMonth.value + 11) % 12
    } else if (i >= startDow + daysInMonth) {
      day = i - startDow - daysInMonth + 1
      other = true
      y = calMonth.value === 11 ? calYear.value + 1 : calYear.value
      m = (calMonth.value + 1) % 12
    } else {
      day = i - startDow + 1
      y = calYear.value
      m = calMonth.value
    }
    const cellDate = new Date(y, m, day)
    const ymd = toYMD(cellDate)
    cells.push({
      day,
      other,
      today: ymd === todayStr,
      selected: tempDate.value === ymd,
      disabled: cellDate < new Date(today.getFullYear(), today.getMonth(), today.getDate()),
      ymd,
    })
  }
  return cells
})

function openDt() {
  const seed = props.modelValue
    ? new Date(props.modelValue)
    : new Date(Date.now() + 60 * 60 * 1000)
  const valid = !isNaN(seed.getTime()) ? seed : new Date(Date.now() + 60 * 60 * 1000)
  calYear.value = valid.getFullYear()
  calMonth.value = valid.getMonth()
  tempDate.value = toYMD(valid)
  tempHour.value = valid.getHours()
  tempMinute.value = valid.getMinutes()
  dtOpen.value = true
}
function closeDt() { dtOpen.value = false }
function prevMonth() {
  if (calMonth.value === 0) { calMonth.value = 11; calYear.value-- } else { calMonth.value-- }
}
function nextMonth() {
  if (calMonth.value === 11) { calMonth.value = 0; calYear.value++ } else { calMonth.value++ }
}
function pickDay(c) {
  if (c.disabled) return
  const d = parseYMD(c.ymd)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth()
  tempDate.value = c.ymd
}
function setNow() {
  const d = new Date()
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth()
  tempDate.value = toYMD(d)
  tempHour.value = d.getHours()
  tempMinute.value = d.getMinutes()
}
function confirmDt() {
  if (!tempDate.value) return
  const hh = String(Math.max(0, Math.min(23, Number(tempHour.value) || 0))).padStart(2, '0')
  const mm = String(Math.max(0, Math.min(59, Number(tempMinute.value) || 0))).padStart(2, '0')
  // 只在"确定"时向上抛出,因此父组件收到事件即代表用户真的选了一次
  emit('update:modelValue', `${tempDate.value}T${hh}:${mm}`)
  dtOpen.value = false
}

// click-outside 指令(局部)
const vClickOutside = {
  mounted(el, binding) {
    el.__coHandler__ = (e) => {
      if (!(el === e.target || el.contains(e.target))) binding.value(e)
    }
    document.addEventListener('mousedown', el.__coHandler__)
  },
  unmounted(el) {
    document.removeEventListener('mousedown', el.__coHandler__)
  },
}
</script>

<style scoped>
.dt-picker {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
}
.dt-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  /* 与同行的 .seg 保持等高(由父级 .seg-row 提供 --ctrl-h) */
  height: var(--ctrl-h, 36px);
  box-sizing: border-box;
  padding: 6px 10px;
  border-radius: 10px;
  background: rgba(11, 11, 16, 0.55);
  border: 1px solid rgba(96, 165, 250, 0.18);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
  cursor: pointer;
  transition: border-color var(--t-fast), box-shadow var(--t-fast), background var(--t-fast);
  outline: none;
}
.dt-trigger:hover { border-color: rgba(96, 165, 250, 0.35); }
.dt-picker.is-open .dt-trigger,
.dt-picker.has-value .dt-trigger {
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.1);
}
.dt-icon-prefix { color: #67E8F9; flex: 0 0 auto; }
.dt-text { flex: 1 1 auto; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dt-text.is-empty { color: var(--text-dim); }
.dt-icon-suffix { color: var(--text-muted); flex: 0 0 auto; transition: transform var(--t-fast); }
.dt-picker.is-open .dt-icon-suffix { transform: rotate(180deg); color: #67E8F9; }

.dt-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 100;
  width: 240px;
  max-width: calc(100vw - 32px);
  padding: 12px;
  background: #0F121C;            /* 纯色不透明,不再透出下面的按钮 */
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 12px;
  box-shadow: 0 16px 40px -8px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(103, 232, 249, 0.08) inset;
}
.dt-pop-enter-active, .dt-pop-leave-active { transition: opacity 160ms ease, transform 160ms ease; }
.dt-pop-enter-from, .dt-pop-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }

.dt-cal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.dt-title { font-family: var(--font-mono); font-size: 13px; color: var(--text); letter-spacing: 0.04em; }
.dt-title-y { color: var(--text-muted); margin-right: 4px; }
.dt-title-m { color: #67E8F9; }
.dt-nav {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid rgba(96, 165, 250, 0.22);
  border-radius: 7px; color: #67E8F9; cursor: pointer;
  transition: all var(--t-fast);
  flex: 0 0 auto;
  padding: 0; margin: 0;
  user-select: none;
}
.dt-nav svg { display: block; }
.dt-nav:hover { border-color: rgba(103, 232, 249, 0.55); background: rgba(103, 232, 249, 0.1); color: #B6F1FF; }

.dt-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));   /* minmax(0,1fr) 关键,防止内容撑爆 */
  gap: 2px;
}
.dt-dow-cell,
.dt-day {
  min-width: 0;                                        /* 同上,grid 子项防御 */
  box-sizing: border-box;
  text-align: center;
  line-height: 1;
  font-family: var(--font-mono);
}
.dt-dow-cell {
  height: 22px;
  font-size: 10px;
  color: var(--text-dim); letter-spacing: 0.06em;
  line-height: 22px;                                   /* 居中 */
}
.dt-day {
  height: 28px;
  font-size: 11px;
  line-height: 28px;                                   /* 居中 */
  background: transparent; border: 0; border-radius: 6px;
  color: var(--text); cursor: pointer;
  transition: all var(--t-fast);
  margin: 0; padding: 0;
}
.dt-day:hover:not(:disabled) { background: rgba(96, 165, 250, 0.12); color: #67E8F9; }
.dt-day.is-other { color: var(--text-dim); opacity: 0.45; }
.dt-day.is-today { border: 1px solid rgba(103, 232, 249, 0.4); }
.dt-day.is-selected {
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  color: #0B0B10; font-weight: 600;
  box-shadow: 0 0 12px -2px rgba(103, 232, 249, 0.5);
}
.dt-day.is-disabled { color: var(--text-dim); opacity: 0.3; cursor: not-allowed; }

.dt-time {
  display: flex; align-items: center; gap: 10px;
  margin-top: 12px; padding-top: 12px;
  border-top: 1px dashed rgba(96, 165, 250, 0.15);
}
.dt-time-label {
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); letter-spacing: 0.06em;
}
.dt-time-inputs { display: flex; align-items: center; gap: 4px; flex: 1 1 auto; }
.dt-num {
  width: 48px; padding: 5px 6px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid rgba(96, 165, 250, 0.22);
  border-radius: 6px;
  color: var(--text); font-family: var(--font-mono); font-size: 13px;
  text-align: center;
  outline: none;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
  -moz-appearance: textfield;
}
.dt-num::-webkit-outer-spin-button,
.dt-num::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.dt-num:focus { border-color: rgba(103, 232, 249, 0.55); box-shadow: 0 0 0 2px rgba(103, 232, 249, 0.1); }
.dt-time-sep { color: #67E8F9; font-family: var(--font-mono); font-size: 14px; }
.dt-now {
  font-family: var(--font-mono); font-size: 10px;
  padding: 4px 8px;
  background: transparent; border: 1px solid rgba(96, 165, 250, 0.22);
  border-radius: 5px; color: #67E8F9; cursor: pointer;
  letter-spacing: 0.06em;
  transition: all var(--t-fast);
}
.dt-now:hover { background: rgba(103, 232, 249, 0.1); border-color: rgba(103, 232, 249, 0.5); }

.dt-foot { display: flex; gap: 8px; margin-top: 12px; }
.dt-btn {
  flex: 1 1 auto;
  padding: 7px 0;
  font-family: var(--font-mono); font-size: 12px;
  border-radius: 7px; border: 1px solid transparent; cursor: pointer;
  transition: all var(--t-fast);
  letter-spacing: 0.04em;
}
.dt-btn-ghost { background: transparent; border-color: rgba(96, 165, 250, 0.18); color: var(--text-muted); }
.dt-btn-ghost:hover { border-color: rgba(96, 165, 250, 0.35); color: var(--text); }
.dt-btn-primary {
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  color: #0B0B10; font-weight: 600;
  box-shadow: 0 0 12px -2px rgba(103, 232, 249, 0.5);
}
.dt-btn-primary:hover:not(:disabled) { box-shadow: 0 0 18px -2px rgba(103, 232, 249, 0.7); }
.dt-btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
</style>

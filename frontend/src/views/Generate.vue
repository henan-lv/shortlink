<template>
  <div class="page">
    <header class="page-head">      <h2>生成短链</h2>
      <p class="page-sub">把又长又丑的链接压成一句话,再交给世界</p>
    </header>

    <GenerateForm @created="onCreated" />

    <!-- 成功结果弹窗 -->
    <teleport to="body">
      <transition name="modal">
        <div v-if="lastResult" class="modal-mask" @click.self="close" role="dialog" aria-modal="true">
          <div class="modal-card">
            <span class="corner corner-tl"></span>
            <span class="corner corner-tr"></span>
            <span class="corner corner-bl"></span>
            <span class="corner corner-br"></span>

            <header class="m-head">
              <div class="m-head-left">                <h3 class="m-title">
                  <span class="title-spark">✦</span>
                  短链已生成
                </h3>
              </div>
              <button class="m-close" type="button" aria-label="关闭" @click="close">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <line x1="6" y1="6" x2="18" y2="18" />
                  <line x1="18" y1="6" x2="6" y2="18" />
                </svg>
              </button>
            </header>

            <div class="m-rule"></div>

            <section class="m-section">
              <span class="m-label">完整短链</span>
              <div class="m-link-box">
                <a :href="lastResult.full_short_url" target="_blank" rel="noopener" class="m-link">
                  <code>{{ lastResult.full_short_url }}</code>
                </a>
                <button
                  class="m-copy"
                  :class="{ copied }"
                  type="button"
                  :aria-label="copied ? '已复制' : '复制短链'"
                  @click="copyShort"
                >
                  <svg v-if="!copied" class="m-copy-ico" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="9" y="9" width="12" height="12" rx="2.5" />
                    <path d="M6.5 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1.5" />
                  </svg>
                  <svg v-else class="m-copy-ico" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                  <span class="m-copy-text">{{ copied ? '已复制' : '复制' }}</span>
                </button>
              </div>
            </section>

            <section class="m-section">
              <span class="m-label">原始链接</span>
              <a :href="lastResult.long_url" target="_blank" rel="noopener" class="m-long" :title="lastResult.long_url">
                {{ lastResult.long_url }}
              </a>
            </section>

            <section class="m-meta">
              <div class="m-meta-item">
                <span class="m-meta-k">生效</span>
                <span class="m-meta-v">{{ lastResult.effective_at || '立即生效' }}</span>
              </div>
              <div class="m-meta-sep"></div>
              <div class="m-meta-item">
                <span class="m-meta-k">过期</span>
                <span class="m-meta-v">{{ lastResult.expire_at || '默认 7 天' }}</span>
              </div>
            </section>

            <footer class="m-foot">
              <router-link to="/links" class="m-action" @click="close">
                查看我的链接 <span class="arrow">→</span>
              </router-link>
              <router-link :to="`/stats/${lastResult.short_code}`" class="m-action primary" @click="close">
                查看统计数据 <span class="arrow">→</span>
              </router-link>
            </footer>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useNotifyStore } from '@/stores/notify'
import GenerateForm from '@/components/GenerateForm.vue'

const lastResult = ref(null)
const copied = ref(false)
const notify = useNotifyStore()

function onCreated(result) {
  lastResult.value = result
  copied.value = false
}

function close() {
  lastResult.value = null
  copied.value = false
}

async function copyShort() {
  if (!lastResult.value) return
  try {
    await navigator.clipboard.writeText(lastResult.value.full_short_url)
    copied.value = true
    notify.success('已复制到剪贴板')
    setTimeout(() => (copied.value = false), 1600)
  } catch (e) {
    notify.error('复制失败,请手动复制')
  }
}

function onKey(e) {
  if (e.key === 'Escape' && lastResult.value) close()
}

onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
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
  color: rgba(103, 232, 249, 0.7);
  margin-bottom: 2px;
}
.page-sub {
  margin: 0;
  padding-left: 14px;
  color: var(--text-muted);
  font-size: 13px;
}

/* === 弹窗遮罩 === */
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

/* === 弹窗卡片 === */
.modal-card {
  position: relative;
  width: 100%;
  max-width: 560px;
  background:
    linear-gradient(180deg, rgba(30, 30, 35, 0.92), rgba(20, 20, 28, 0.92)) padding-box,
    linear-gradient(135deg, rgba(110, 231, 183, 0.55), rgba(103, 232, 249, 0.28) 55%, rgba(139, 92, 246, 0.42)) border-box;
  border: 1px solid transparent;
  border-radius: 18px;
  padding: 26px 26px 22px;
  box-shadow:
    0 0 0 1px rgba(16, 185, 129, 0.16),
    0 32px 80px -20px rgba(0, 0, 0, 0.75),
    0 0 80px -24px rgba(16, 185, 129, 0.55);
}

/* 四角科技感装饰 */
.corner {
  position: absolute;
  width: 16px;
  height: 16px;
  border-color: rgba(110, 231, 183, 0.85);
  border-style: solid;
  border-width: 0;
  pointer-events: none;
}
.corner-tl { top: -1px; left: -1px; border-top-width: 2px; border-left-width: 2px; border-radius: 4px 0 0 0; }
.corner-tr { top: -1px; right: -1px; border-top-width: 2px; border-right-width: 2px; border-radius: 0 4px 0 0; }
.corner-bl { bottom: -1px; left: -1px; border-bottom-width: 2px; border-left-width: 2px; border-radius: 0 0 0 4px; }
.corner-br { bottom: -1px; right: -1px; border-bottom-width: 2px; border-right-width: 2px; border-radius: 0 0 4px 0; }

/* === 头部 === */
.m-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}
.m-head-left { flex: 1; min-width: 0; }
.m-eyebrow {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.24em;
  color: rgba(110, 231, 183, 0.85);
  padding: 4px 10px;
  border: 1px solid rgba(110, 231, 183, 0.35);
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.08);
  margin-bottom: 10px;
}
.m-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-spark {
  color: rgba(110, 231, 183, 0.95);
  text-shadow: 0 0 12px rgba(16, 185, 129, 0.65);
  font-size: 18px;
}
.m-close {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast), background var(--t-fast);
}
.m-close:hover {
  color: var(--text);
  border-color: var(--border-bright);
  background: rgba(15, 23, 42, 0.85);
}
.m-close svg { width: 16px; height: 16px; display: block; }

/* === 分隔 === */
.m-rule {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(110, 231, 183, 0.4), transparent);
  margin-bottom: 18px;
}

/* === 区块 === */
.m-section { margin-bottom: 16px; }
.m-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 8px;
}

/* 短链 + 复制按钮 */
.m-link-box {
  display: flex;
  align-items: stretch;
  gap: 0;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid rgba(103, 232, 249, 0.28);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 0 22px -10px rgba(34, 211, 238, 0.55);
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}
.m-link-box:hover {
  border-color: rgba(103, 232, 249, 0.55);
  box-shadow: 0 0 26px -6px rgba(34, 211, 238, 0.7);
}
.m-link {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  padding: 11px 14px;
  text-decoration: none;
}
.m-link code {
  flex: 1;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  border-radius: 0;
  font-family: var(--font-mono);
  font-size: 14px;
  color: #67E8F9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-copy {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  background: rgba(34, 211, 238, 0.08);
  border: none;
  border-left: 1px solid rgba(103, 232, 249, 0.28);
  color: var(--accent-2);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast), border-color var(--t-fast);
}
.m-copy:hover {
  background: rgba(34, 211, 238, 0.18);
  color: #A5F3FC;
}
.m-copy.copied {
  background: rgba(16, 185, 129, 0.16);
  border-left-color: rgba(16, 185, 129, 0.5);
  color: var(--success);
}
.m-copy-ico { width: 14px; height: 14px; display: block; flex: 0 0 auto; }
.m-copy-text { white-space: nowrap; }

/* 原始链接 */
.m-long {
  display: block;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
  line-height: 1.55;
  padding: 8px 12px;
  background: rgba(11, 11, 16, 0.4);
  border: 1px solid rgba(96, 165, 250, 0.08);
  border-radius: 8px;
  text-decoration: none;
  transition: color var(--t-fast), border-color var(--t-fast);
}
.m-long:hover { color: var(--text); border-color: rgba(96, 165, 250, 0.22); }

/* 元信息条 */
.m-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  margin: 6px 0 18px;
  background: rgba(11, 11, 16, 0.35);
  border: 1px solid rgba(96, 165, 250, 0.10);
  border-radius: 10px;
}
.m-meta-item { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.m-meta-k {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.m-meta-v {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-meta-sep {
  width: 1px;
  height: 14px;
  background: rgba(96, 165, 250, 0.18);
}

/* 底部行动按钮 */
.m-foot {
  display: flex;
  gap: 12px;
}
.m-action {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 11px 14px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.1em;
  color: #67E8F9;
  background: rgba(34, 211, 238, 0.06);
  border: 1px solid rgba(103, 232, 249, 0.32);
  border-radius: 10px;
  text-decoration: none;
  transition: background var(--t-fast), border-color var(--t-fast), box-shadow var(--t-fast), transform var(--t-fast);
}
.m-action:hover {
  background: rgba(34, 211, 238, 0.14);
  border-color: rgba(103, 232, 249, 0.65);
  box-shadow: 0 0 18px -4px rgba(34, 211, 238, 0.55);
}
.m-action.primary {
  color: #0F172A;
  background: linear-gradient(135deg, #67E8F9, #22D3EE);
  border-color: transparent;
  font-weight: 600;
}
.m-action.primary:hover {
  box-shadow: 0 0 26px -4px rgba(34, 211, 238, 0.85);
  transform: translateY(-1px);
}
.m-action .arrow { transition: transform var(--t-fast); }
.m-action:hover .arrow { transform: translateX(3px); }

/* 弹窗动画 */
.modal-enter-active, .modal-leave-active { transition: opacity 240ms ease; }
.modal-enter-active .modal-card, .modal-leave-active .modal-card { transition: opacity 280ms ease, transform 280ms cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-card, .modal-leave-to .modal-card { opacity: 0; transform: translateY(16px) scale(0.96); }
</style>

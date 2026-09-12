<template>
  <!-- 满屏 landing,overflow:hidden 禁止滚动 -->
  <div class="landing">
    <!-- 全屏背景轮播 -->
    <CarouselBackground />

    <!-- 顶部 brand bar -->
    <header class="topbar">
      <div class="topbar-brand">
        <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true">
          <path d="M8 8 L24 8 L20 16 L24 24 L8 24 L12 16 Z" fill="none" stroke="url(#lbg)" stroke-width="1.5"/>
          <defs>
            <linearGradient id="lbg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#60A5FA"/>
              <stop offset="100%" stop-color="#67E8F9"/>
            </linearGradient>
          </defs>
        </svg>
        <span class="brand-name">SHORT<span class="brand-accent">LINK</span></span>
      </div>
    </header>

    <!-- 右侧悬浮登录卡 -->
    <main class="landing-main">
      <div class="login-card" :class="{ 'is-register': mode === 'register' }">
        <div class="card-inner">
          <div class="card-header">
            <div class="card-cap"><span class="card-cap-tag" :class="{ reg: mode === 'register' }">{{ mode === 'login' ? 'LOG IN' : 'REGISTER' }}</span></div>
            <h1 class="card-title">
              <span class="title-prompt">&gt;</span>
              {{ mode === 'login' ? '欢迎回来' : '创建账号' }}
            </h1>
            <p class="card-sub">{{ mode === 'login' ? '继续你的短链之旅' : '只需 30 秒即可开始' }}</p>
          </div>

          <form @submit.prevent="onSubmit" class="login-form">
            <div class="field">
              <label class="field-label" for="login-username">用户名</label>
              <div class="input-wrap">
                <span class="input-prefix" aria-hidden="true">&gt;</span>
                <input id="login-username" ref="usernameInput" v-model="username" type="text" required minlength="3" maxlength="64" autocomplete="username" :placeholder="mode === 'register' ? '用户名 · 至少 3 个字符' : '请输入用户名'" />
              </div>
            </div>
            <div class="field">
              <label class="field-label" for="login-password">密码</label>
              <div class="input-wrap">
                <span class="input-prefix" aria-hidden="true">#</span>
                <input id="login-password" ref="passwordInput" v-model="password" type="password" required minlength="6" maxlength="64" autocomplete="current-password" :placeholder="mode === 'register' ? '密码 · 至少 6 位' : '请输入密码'" @keydown.meta.enter.prevent="onSubmit" @keydown.ctrl.enter.prevent="onSubmit" />
              </div>
            </div>

            <div v-if="errorMsg" class="error-block" role="alert" aria-live="polite">! {{ errorMsg }}</div>

            <button type="submit" class="primary submit-btn" :disabled="loading">
              <span v-if="!loading">{{ mode === 'login' ? '登录' : '创建账号' }}</span>
              <span v-else class="loading-text">
                <span class="loading-dots"><span></span><span></span><span></span></span>
                <span>{{ mode === 'login' ? '正在验证身份…' : '正在创建…' }}</span>
              </span>
            </button>

            <button type="button" class="ghost toggle-btn" @click="toggleMode">
              <span v-if="mode === 'login'">没有账号? <em>立即注册</em></span>
              <span v-else>已有账号? <em>立即登录</em></span>
            </button>
          </form>

          <div class="card-footer">
            <span class="footer-dot"></span>
            <span>session // secured</span>
            <span class="footer-kbd">⌘ ↵ 提交</span>
          </div>
        </div>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotifyStore } from '@/stores/notify'
import CarouselBackground from '@/components/CarouselBackground.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const notify = useNotifyStore()

const mode = ref('login')
const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

const usernameInput = ref(null)
const passwordInput = ref(null)

let errorTimer = null

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  errorMsg.value = ''
}

function clearErrorLater() {
  if (errorTimer) clearTimeout(errorTimer)
  errorTimer = setTimeout(() => { errorMsg.value = '' }, 5000)
}

async function onSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    if (mode.value === 'register') {
      const u = username.value
      const p = password.value
      // 1. 先注册
      await auth.register(u, p)
      // 2. 注册成功后自动登录,直接跳 /links,不需要用户再点一次登录
      //    (注意:auth.register 不会写 user,这里紧接着调 auth.login)
      await auth.login(u, p)
      const raw = route.query.redirect
      const target = (typeof raw === 'string' && raw.startsWith('/') && !raw.startsWith('//') && raw !== route.path)
        ? raw
        : '/links'
      notify.success('注册并登录成功')
      router.replace(target)
      return
    } else {
      await auth.login(username.value, password.value)
      // 校验 redirect query:必须是非空相对路径且不等于当前路径,否则落到默认页 /links
      // 避免类似 /?redirect=/ 这种 URL 让登录后又跳回登录页
      const raw = route.query.redirect
      const target = (typeof raw === 'string' && raw.startsWith('/') && !raw.startsWith('//') && raw !== route.path)
        ? raw
        : '/links'
      router.replace(target)
    }
  } catch (e) {
    errorMsg.value = e.message || '登录失败,请重试'
    clearErrorLater()
    // focus 第一个字段,方便用户直接修改
    if (mode.value === 'login') {
      ;(usernameInput.value || passwordInput.value)?.focus()
    } else {
      ;(usernameInput.value)?.focus()
    }
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  if (errorTimer) clearTimeout(errorTimer)
})
</script>

<style scoped>
/* === 模式徽章 === */
.card-cap-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  padding: 2px 7px;
  margin-right: 8px;
  border-radius: 4px;
  color: rgba(96, 165, 250, 0.85);
  background: rgba(96, 165, 250, 0.08);
  border: 1px solid rgba(96, 165, 250, 0.3);
  vertical-align: 2px;
}
.card-cap-tag.reg {
  color: rgba(244, 114, 182, 0.95);
  background: rgba(244, 114, 182, 0.10);
  border-color: rgba(244, 114, 182, 0.4);
  box-shadow: 0 0 8px -2px rgba(244, 114, 182, 0.45);
}
.login-card { transition: border-color var(--t-base), box-shadow var(--t-base); }
.login-card.is-register {
  border-color: rgba(244, 114, 182, 0.35);
  box-shadow:
    0 0 0 1px rgba(244, 114, 182, 0.18),
    0 24px 64px -16px rgba(0, 0, 0, 0.7),
    0 0 64px -16px rgba(244, 114, 182, 0.55);
}
.login-card.is-register .card-cap { color: rgba(244, 114, 182, 0.75); }
.login-card.is-register .title-prompt { color: #F472B6; text-shadow: 0 0 8px rgba(244, 114, 182, 0.5); }
.login-card.is-register .submit-btn {
  background: linear-gradient(135deg, #F472B6 0%, #A78BFA 100%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 8px 24px -8px rgba(244, 114, 182, 0.7),
    0 0 32px -8px rgba(167, 139, 250, 0.5);
}
.login-card.is-register .submit-btn:hover {
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.15) inset,
    0 12px 32px -8px rgba(244, 114, 182, 0.8),
    0 0 40px -6px rgba(167, 139, 250, 0.6);
}

/* === 注册确认弹窗 === */
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
.reg-modal {
  position: relative;
  width: 100%;
  max-width: 440px;
  background:
    linear-gradient(180deg, rgba(30, 30, 35, 0.92), rgba(20, 20, 28, 0.92)) padding-box,
    linear-gradient(135deg, rgba(244, 114, 182, 0.55), rgba(167, 139, 250, 0.32) 55%, rgba(96, 165, 250, 0.4)) border-box;
  border: 1px solid transparent;
  border-radius: 16px;
  padding: 24px 24px 20px;
  box-shadow:
    0 0 0 1px rgba(244, 114, 182, 0.16),
    0 32px 80px -20px rgba(0, 0, 0, 0.75),
    0 0 80px -24px rgba(244, 114, 182, 0.55);
}
.reg-modal .corner {
  position: absolute;
  width: 14px; height: 14px;
  border-color: rgba(244, 114, 182, 0.85);
  border-style: solid; border-width: 0;
  pointer-events: none;
}
.reg-modal .corner-tl { top: -1px; left: -1px; border-top-width: 2px; border-left-width: 2px; border-radius: 4px 0 0 0; }
.reg-modal .corner-tr { top: -1px; right: -1px; border-top-width: 2px; border-right-width: 2px; border-radius: 0 4px 0 0; }
.reg-modal .corner-bl { bottom: -1px; left: -1px; border-bottom-width: 2px; border-left-width: 2px; border-radius: 0 0 0 4px; }
.reg-modal .corner-br { bottom: -1px; right: -1px; border-bottom-width: 2px; border-right-width: 2px; border-radius: 0 0 4px 0; }
.rm-head { margin-bottom: 14px; }
.rm-eyebrow {
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
.rm-title { margin: 0; font-size: 18px; color: var(--text); }
.rm-body { display: flex; flex-direction: column; gap: 12px; }
.rm-desc { margin: 0; color: var(--text-muted); font-size: 13px; line-height: 1.55; }
.rm-desc strong { color: var(--text); font-weight: 600; }
.rm-tips {
  list-style: none; margin: 0; padding: 12px 14px;
  background: rgba(11, 11, 16, 0.4);
  border: 1px solid rgba(244, 114, 182, 0.18);
  border-radius: 10px;
  display: flex; flex-direction: column; gap: 8px;
}
.rm-tips li { display: flex; align-items: baseline; gap: 12px; font-family: var(--font-mono); font-size: 12px; }
.tip-k { flex: 0 0 90px; color: var(--text-dim); letter-spacing: 0.1em; text-transform: uppercase; font-size: 10px; }
.tip-v { color: var(--text); }
.rm-foot { display: flex; gap: 10px; justify-content: flex-end; margin-top: 18px; }
.rm-foot .primary {
  background: linear-gradient(135deg, #F472B6 0%, #A78BFA 100%);
  border: none; color: white; font-weight: 600;
  padding: 9px 18px; border-radius: 8px; cursor: pointer;
  box-shadow: 0 8px 24px -8px rgba(244, 114, 182, 0.6);
  transition: transform var(--t-fast), filter var(--t-fast);
}
.rm-foot .primary:hover { transform: translateY(-1px); filter: brightness(1.08); }
.rm-foot .ghost {
  background: transparent; border: 1px solid var(--border); color: var(--text-muted);
  padding: 9px 16px; border-radius: 8px; cursor: pointer; font-size: 13px;
  transition: color var(--t-fast), border-color var(--t-fast);
}
.rm-foot .ghost:hover { color: var(--text); border-color: var(--border-bright); }

.modal-enter-active, .modal-leave-active { transition: opacity 240ms ease; }
.modal-enter-active .reg-modal, .modal-leave-active .reg-modal { transition: opacity 280ms ease, transform 280ms cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .reg-modal, .modal-leave-to .reg-modal { opacity: 0; transform: translateY(16px) scale(0.96); }

/* 满屏布局/* 满屏布局:100dvh 解决 iOS Safari URL bar 跳动,@supports fallback 到 100vh */
.landing {
  position: relative;
  width: 100%;
  height: 100vh;
  min-height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  isolation: isolate;
}
@supports (height: 100dvh) {
  .landing {
    height: 100dvh;
    min-height: 100dvh;
    max-height: 100dvh;
  }
}

/* === 顶部 brand bar === */
.topbar {
  position: absolute;
  top: 0; left: 0; right: 0;
  z-index: 30;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  padding-top: max(20px, env(safe-area-inset-top));
}
.topbar-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--text);
}
.brand-name { color: var(--text); }
.brand-accent {
  background: linear-gradient(135deg, #60A5FA, #67E8F9);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-left: 2px;
}
.topbar-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(148, 163, 184, 0.7);
  letter-spacing: 0.15em;
  padding: 6px 12px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 999px;
  background: rgba(11, 11, 16, 0.4);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
  animation: pulse-glow 2s ease-in-out infinite;
}

/* === 主区 === */
.landing-main {
  position: relative;
  z-index: 20;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 80px clamp(180px, 16vw, 280px) 0 0;
}

/* === 浮动登录卡 === */
.login-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  border-radius: 20px;
  padding: 1px;
  background:
    linear-gradient(180deg, rgba(96, 165, 250, 0.45), rgba(103, 232, 249, 0.18)) padding-box,
    linear-gradient(180deg, rgba(96, 165, 250, 0.35), rgba(103, 232, 249, 0.12)) border-box;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.04) inset,
    0 30px 80px -20px rgba(0, 0, 0, 0.6),
    0 0 60px -10px rgba(96, 165, 250, 0.25);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  animation: card-rise 800ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  margin-bottom: env(safe-area-inset-bottom, 0px);
}
@keyframes card-rise {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.card-inner {
  border-radius: 19px;
  padding: 32px 32px 24px;
  background: linear-gradient(180deg, rgba(20, 20, 28, 0.78), rgba(11, 11, 16, 0.72));
  position: relative;
}

/* === 标题 === */
.card-header { text-align: left; margin-bottom: 24px; }
.card-cap {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.25em;
  color: rgba(103, 232, 249, 0.85);
  margin-bottom: 10px;
}
.card-title {
  margin: 0 0 6px;
  font-family: var(--font-sans);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text);
  line-height: 1.2;
}
.title-prompt {
  color: #67E8F9;
  margin-right: 8px;
  font-weight: 400;
  text-shadow: 0 0 12px rgba(103, 232, 249, 0.6);
}
.card-sub {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

/* === 表单 === */
.login-form { display: flex; flex-direction: column; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.2em;
  color: rgba(148, 163, 184, 0.7);
  text-transform: uppercase;
}
.input-wrap { position: relative; display: flex; align-items: center; }
.input-prefix {
  position: absolute;
  left: 16px;
  font-family: var(--font-mono);
  color: rgba(103, 232, 249, 0.7);
  font-size: 14px;
  pointer-events: none;
  z-index: 1;
}
.input-wrap input {
  width: 100%;
  padding: 13px 16px 13px 38px;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text);
  background: rgba(11, 11, 16, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  outline: none;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.2);
  transition: border-color 200ms ease, background-color 200ms ease, box-shadow 200ms ease;
}
.input-wrap input::placeholder {
  color: rgba(148, 163, 184, 0.4);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
}
.input-wrap input:hover {
  border-color: rgba(148, 163, 184, 0.25);
  background: rgba(11, 11, 16, 0.65);
}
.input-wrap input:focus {
  border-color: rgba(96, 165, 250, 0.6);
  background: rgba(11, 11, 16, 0.75);
  box-shadow:
    inset 0 1px 2px rgba(0, 0, 0, 0.2),
    0 0 0 3px rgba(96, 165, 250, 0.12),
    0 0 24px -4px rgba(96, 165, 250, 0.4);
}

/* === 按钮 === */
.submit-btn {
  margin-top: 4px;
  height: 46px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.05em;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  color: white;
  background: linear-gradient(135deg, #60A5FA 0%, #67E8F9 100%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 8px 24px -8px rgba(96, 165, 250, 0.6),
    0 0 32px -8px rgba(103, 232, 249, 0.4);
  position: relative;
  overflow: hidden;
  transition: transform 200ms cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 200ms ease, filter 200ms ease;
}
.submit-btn:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.15) inset,
    0 12px 32px -8px rgba(96, 165, 250, 0.7),
    0 0 40px -6px rgba(103, 232, 249, 0.55);
}
.submit-btn:active { transform: translateY(0); filter: brightness(0.96); }
.submit-btn:disabled {
  opacity: 0.85;
  cursor: not-allowed;
  transform: none;
  filter: saturate(0.9);
}
.submit-btn::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
  transition: left 800ms ease;
  pointer-events: none;
}
.submit-btn:hover::after { left: 100%; }

/* loading 文本 + 三点 */
.loading-text {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
}
.loading-dots { display: inline-flex; gap: 4px; align-items: center; }
.loading-dots span {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: white;
  animation: pulse-glow 1.2s ease-in-out infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }

/* === toggle === */
.toggle-btn {
  background: none;
  border: none;
  font-family: var(--font-sans);
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 0.02em;
  text-transform: none;
  cursor: pointer;
  padding: 6px 0;
  transition: color 200ms ease;
}
.toggle-btn em {
  font-style: normal;
  color: #67E8F9;
  margin-left: 4px;
  text-shadow: 0 0 8px rgba(103, 232, 249, 0.4);
}
.toggle-btn:hover { color: var(--text); }

/* === error === */
.error-block {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 10px;
  color: #FCA5A5;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.03em;
  animation: shake 400ms ease;
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%      { transform: translateX(-4px); }
  40%      { transform: translateX(4px); }
  60%      { transform: translateX(-2px); }
  80%      { transform: translateX(2px); }
}

/* === footer === */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: rgba(148, 163, 184, 0.5);
}
.footer-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
  animation: pulse-glow 2s ease-in-out infinite;
}
.footer-kbd {
  color: rgba(148, 163, 184, 0.4);
  font-size: 9px;
  letter-spacing: 0.1em;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 3px;
  padding: 2px 6px;
}

/* === 响应式 === */
@media (max-width: 900px) {
  .topbar { padding: 16px 20px; }
  .topbar-status { font-size: 10px; padding: 5px 10px; }
  .landing-main {
    padding: 80px 20px 20px;
    justify-content: center;
  }
  .login-card { max-width: 420px; }
}
</style>

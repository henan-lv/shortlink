<template>
  <div class="app">
    <Toast />
    <nav v-if="auth.isLoggedIn" class="navbar">
      <div class="nav-left">
        <div class="nav-brand">
          <router-link to="/links">
            <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true" style="vertical-align: middle; margin-right: 8px;">
              <path d="M8 8 L24 8 L20 16 L24 24 L8 24 L12 16 Z" fill="none" stroke="url(#navg)" stroke-width="1.5"/>
              <defs>
                <linearGradient id="navg" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="#60A5FA"/>
                  <stop offset="100%" stop-color="#67E8F9"/>
                </linearGradient>
              </defs>
            </svg>
            <span>SHORT<span class="accent">LINK</span></span>
          </router-link>
        </div>
        <div class="nav-links">
          <router-link to="/links" class="nav-link">
            <svg class="nav-icon" viewBox="0 0 16 16" width="13" height="13" fill="none" aria-hidden="true">
              <path d="M3 4h10M3 8h10M3 12h7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            <span>链接</span>
          </router-link>
          <router-link to="/generate" class="nav-link">
            <svg class="nav-icon" viewBox="0 0 16 16" width="13" height="13" fill="none" aria-hidden="true">
              <path d="M6.5 9.5l3-3M5 7l-1.5 1.5a2.121 2.121 0 003 3L8 10m3-3l1.5-1.5a2.121 2.121 0 00-3-3L8 6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            <span>生成</span>
          </router-link>
          <router-link to="/stats" class="nav-link">
            <svg class="nav-icon" viewBox="0 0 16 16" width="13" height="13" fill="none" aria-hidden="true">
              <rect x="3" y="9" width="2" height="5" stroke="currentColor" stroke-width="1.4"/>
              <rect x="7" y="5" width="2" height="9" stroke="currentColor" stroke-width="1.4"/>
              <rect x="11" y="7" width="2" height="7" stroke="currentColor" stroke-width="1.4"/>
            </svg>
            <span>统计</span>
          </router-link>
          <router-link v-if="auth.isAdmin" to="/users" class="nav-link nav-admin" title="用户管理">
            <svg class="nav-icon" viewBox="0 0 16 16" width="13" height="13" fill="none" aria-hidden="true">
              <circle cx="6" cy="6" r="2.5" stroke="currentColor" stroke-width="1.4"/>
              <path d="M2 13c0-2.2 1.8-4 4-4s4 1.8 4 4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <path d="M11.5 4l1 1-3 3-1-1z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
            </svg>
            <span>用户</span>
          </router-link>
        </div>
      </div>
      <div class="nav-right">
        <div class="user-chip" :title="auth.user?.username">
          <span class="user-dot"></span>
          <span class="user-name">{{ auth.user?.username }}</span>
        </div>
        <button class="nav-logout" :title="`退出登录(${auth.user?.username})`" @click="onLogout" aria-label="退出登录">
          <svg viewBox="0 0 18 18" width="16" height="16" fill="none" aria-hidden="true">
            <path d="M7 4H4a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M11 12l3-3-3-3M14 9H7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      <div class="nav-scan-clip" aria-hidden="true">
        <div class="nav-scan"></div>
      </div>
    </nav>

    <main class="main-content" :class="{ 'is-inner': !route.meta.fullBleed }">
      <router-view />
    </main>

  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotifyStore } from '@/stores/notify'
import Toast from '@/components/Toast.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const notify = useNotifyStore()

onMounted(() => {
  auth.bootstrap()
})

async function onLogout() {
  await auth.logout()
  notify.info('已退出登录')
  router.push('/')
}
</script>

<style>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* === navbar === */
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 32px;
  background: rgba(11, 11, 16, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
  gap: 12px;
}
.navbar::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.5;
}

.nav-brand a {
  display: inline-flex;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--text);
  text-decoration: none;
}
.nav-brand .accent {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 28px;                       /* logo 和导航之间留一道呼吸 */
  min-width: 0;
}
.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.nav-links {
  display: flex;
  gap: 4px;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 12px;
}

.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  color: var(--text-muted);
  text-decoration: none;
  letter-spacing: 0.04em;
  border-radius: 999px;
  font-size: 13px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition: color var(--t-fast), background-color var(--t-fast), box-shadow var(--t-fast);
}
.nav-icon { color: currentColor; opacity: 0.8; transition: opacity var(--t-fast); }
.nav-link:hover .nav-icon { opacity: 1; }
.nav-link:hover {
  color: var(--text);
  background: rgba(96, 165, 250, 0.08);
}
.nav-link.router-link-active {
  color: var(--accent-2);
  background: rgba(103, 232, 249, 0.08);
  text-shadow: 0 0 8px var(--accent-2-glow);
}
.nav-link.nav-admin { color: #F472B6; }
.nav-link.nav-admin:hover { color: #F9A8D4; background: rgba(244, 114, 182, 0.10); }
.nav-link.nav-admin.router-link-active { color: #F472B6; background: rgba(244, 114, 182, 0.12); text-shadow: 0 0 8px rgba(244, 114, 182, 0.6); }
.nav-link.router-link-active::before {
  content: '';
  position: absolute;
  left: 14px; right: 14px; bottom: -16px;
  height: 1px;
  background: var(--accent-2);
  box-shadow: 0 0 6px var(--accent-2-glow);
}

.nav-divider {
  width: 1px;
  height: 16px;
  background: var(--border);
  margin: 0 8px;
}

.nav-user {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
  padding: 0 8px;
  font-variant-numeric: tabular-nums;
}
.user-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
  animation: pulse-glow 2s ease-in-out infinite;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px 0 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.04em;
  max-width: 160px;
}
.user-chip .user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.nav-logout {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-muted);
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast), background-color var(--t-fast), box-shadow var(--t-fast), transform var(--t-fast);
}
.nav-logout:hover {
  color: #fff;
  background: rgba(239, 68, 68, 0.12);
  border-color: var(--danger);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
  transform: translateY(-1px);
}
.nav-logout:active {
  transform: translateY(0);
}

/* 扫描线裁剪层:nav-scan 会从 -30% 滑到 100%,若不裁剪,元素右缘会顶出视口
   导致页面出现横向滚动条(每 8s 一次,滚动条出现又消失) */
.nav-scan-clip {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
.nav-scan {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 1px;
  width: 30%;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  animation: nav-scan 8s linear infinite;
  pointer-events: none;
}
@keyframes nav-scan {
  0% { left: -30%; }
  100% { left: 100%; }
}

/* === main === */
/* 默认满屏(fullBleed);带 is-inner 时才是带 max-width 的内部容器 */
.main-content {
  flex: 1;
  width: 100%;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
}
.main-content.is-inner {
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 640px) {
  .navbar { padding: 10px 16px; }
  .nav-brand a { font-size: 13px; }
  .nav-links { gap: 2px; }
  .nav-link { padding: 4px 10px; font-size: 12px; }
  .nav-divider, .user-chip { display: none; }
  .nav-logout { margin-left: 0; }
  .main-content.is-inner { padding: 16px; }
}
</style>

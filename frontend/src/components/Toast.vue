<template>
  <Teleport to="body">
    <div class="toast-stack">
      <transition-group name="toast">
        <div
          v-for="n in notify.items"
          :key="n.id"
          class="toast"
          :class="`toast-${n.type}`"
          @click="notify.dismiss(n.id)"
        >
          <span class="toast-bracket">[</span>
          <span class="toast-icon">{{ icon(n.type) }}</span>
          <span class="toast-msg">{{ n.message }}</span>
          <span class="toast-bracket">]</span>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup>
import { useNotifyStore } from '@/stores/notify'

const notify = useNotifyStore()

function icon(type) {
  return { success: 'OK', error: 'ERR', info: 'INF' }[type] || 'INF'
}
</script>

<style>
.toast-stack {
  position: fixed;
  top: 80px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 4px;
  background: rgba(20, 20, 28, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-left: 2px solid var(--accent);
  min-width: 200px;
  max-width: 380px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
  cursor: pointer;
  pointer-events: auto;
  position: relative;
  color: var(--text);
}
.toast::before {
  content: '';
  position: absolute;
  top: -1px; left: -1px;
  width: 10px; height: 1px;
  background: var(--accent);
}
.toast::after {
  content: '';
  position: absolute;
  bottom: -1px; right: -1px;
  width: 10px; height: 1px;
  background: var(--accent);
}
.toast-success {
  border-left-color: var(--success);
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.25);
}
.toast-success::before, .toast-success::after { background: var(--success); }
.toast-error {
  border-left-color: var(--danger);
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.25);
}
.toast-error::before, .toast-error::after { background: var(--danger); }
.toast-info {
  border-left-color: var(--accent);
  box-shadow: 0 0 16px var(--accent-glow);
}

.toast-bracket {
  color: var(--accent);
  font-weight: 600;
}
.toast-success .toast-bracket { color: var(--success); }
.toast-error .toast-bracket { color: var(--danger); }

.toast-icon {
  font-weight: 700;
  font-size: 11px;
  padding: 1px 6px;
  background: var(--bg-elev);
  border-radius: 2px;
  letter-spacing: 0.1em;
}
.toast-success .toast-icon { color: var(--success); }
.toast-error .toast-icon { color: var(--danger); }
.toast-info .toast-icon { color: var(--accent); }

.toast-msg { flex: 1; color: var(--text); }

.toast-enter-active, .toast-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>

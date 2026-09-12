<template>
  <div class="pwd-page">
    <div class="card pwd-card">
      <div class="card-status">
        <span class="status-dot"></span>      </div>

      <div class="pwd-icon">
        <svg viewBox="0 0 24 24" width="36" height="36" aria-hidden="true">
          <rect x="4" y="10" width="16" height="11" rx="1" fill="none" stroke="url(#pg)" stroke-width="1.5"/>
          <path d="M8 10 V7 a4 4 0 0 1 8 0 V10" fill="none" stroke="url(#pg)" stroke-width="1.5"/>
          <circle cx="12" cy="15.5" r="1.2" fill="url(#pg)"/>
          <defs>
            <linearGradient id="pg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#3B82F6"/>
              <stop offset="100%" stop-color="#22D3EE"/>
            </linearGradient>
          </defs>
        </svg>
      </div>

      <h2 class="pwd-title">该短链受密码保护</h2>
      <div class="pwd-code">
        <span class="muted">SHORT_CODE</span>
        <code>{{ code }}</code>
      </div>

      <form @submit.prevent="onSubmit">
        <div class="form-row">
          <label class="field-label">PASSWORD</label>
          <input v-model="password" type="password" required minlength="6" maxlength="8" autocomplete="current-password" />
        </div>
        <div v-if="errorMsg" class="error-msg error-block">⚠ {{ errorMsg }}</div>
        <div class="form-actions">
          <button type="submit" class="primary submit-btn" :disabled="loading">
            <span v-if="!loading">UNLOCK</span>
            <span v-else>VERIFYING...</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { shortlinkApi } from '@/api/shortlink'

const route = useRoute()
const code = route.params.code
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function onSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await shortlinkApi.verifyPassword(code, password.value)
    window.location.href = `/s/${code}`
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.pwd-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: 40px 20px;
}

.pwd-card {
  width: 100%;
  max-width: 400px;
  text-align: center;
  position: relative;
}

.card-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--warn);
  letter-spacing: 0.2em;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--border);
}
.status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--warn);
  box-shadow: 0 0 8px var(--warn);
  animation: pulse-glow 2s ease-in-out infinite;
}

.pwd-icon {
  margin-bottom: 16px;
  filter: drop-shadow(0 0 12px var(--accent-glow));
}

.pwd-title {
  font-size: 18px;
  margin-bottom: 16px;
  padding-left: 0;
}
.pwd-title::before { display: none; }

.pwd-code {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
  font-family: var(--font-mono);
  font-size: 12px;
}
.pwd-code .muted {
  font-size: 10px;
  letter-spacing: 0.15em;
}

.form-row {
  text-align: left;
  margin-bottom: 16px;
}
.field-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.2em;
  margin-bottom: 6px;
}

.error-block {
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 4px;
  text-align: center;
  margin-bottom: 12px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 13px;
  letter-spacing: 0.2em;
}
</style>

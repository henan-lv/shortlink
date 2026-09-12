<template>
  <button
    class="copy-btn"
    :class="{ copied, compact }"
    :title="compact ? (copied ? '已复制' : '复制短链') : undefined"
    :aria-label="compact ? '复制短链' : undefined"
    @click="copy"
  >
    <template v-if="!compact">
      <span v-if="!copied">[ COPY ]</span>
      <span v-else>[ ✓ COPIED ]</span>
    </template>

    <svg v-else class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <template v-if="!copied">
        <rect x="9" y="9" width="12" height="12" rx="2.5" />
        <path d="M6.5 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1.5" />
      </template>
      <path v-else d="M20 6 9 17l-5-5" />
    </svg>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { useNotifyStore } from '@/stores/notify'

const props = defineProps({
  text: { type: String, required: true },
  // 紧凑图标形态:用于表格行内(宽度受限),不显示 [ COPY ] 文字
  compact: { type: Boolean, default: false },
})

const copied = ref(false)
const notify = useNotifyStore()

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch (e) {
    notify.error('复制失败,请手动复制')
  }
}
</script>

<style scoped>
.copy-btn {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.15em;
  padding: 3px 10px;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--text-muted);
  text-transform: none;
  cursor: pointer;
  transition: color var(--t-fast), border-color var(--t-fast), box-shadow var(--t-fast), background var(--t-fast);
}
.copy-btn:hover {
  color: var(--accent-2);
  border-color: var(--accent-2);
  box-shadow: 0 0 8px var(--accent-2-glow);
}
.copy-btn.copied {
  color: var(--success);
  border-color: var(--success);
  background: rgba(16, 185, 129, 0.1);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

/* 紧凑图标形态:无边框、无底色,设计为嵌在一个自带边框的容器右侧
   (由父容器负责外框与分隔线),自身只负责图标与状态色 */
.copy-btn.compact {
  flex: 0 0 auto;
  width: 34px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: stretch;
  background: transparent;
  border: none;
  border-radius: 0;
  letter-spacing: 0;
  color: var(--text-muted);
}
.copy-btn.compact .ico { width: 13px; height: 13px; display: block; }
.copy-btn.compact:hover {
  color: var(--accent-2);
  background: rgba(34, 211, 238, 0.1);
  box-shadow: none;
}
.copy-btn.compact.copied {
  color: var(--success);
  background: rgba(16, 185, 129, 0.12);
  border: none;
  box-shadow: none;
}
</style>

import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 跟踪 prefers-reduced-motion 媒体查询。
 * 用法：
 *   const { prefersReduced } = useReducedMotion()
 *   :style="{ animationDuration: prefersReduced ? '0.01ms' : '500ms' }"
 */
export function useReducedMotion() {
  const prefersReduced = ref(false)
  let mq = null
  const update = () => { if (mq) prefersReduced.value = mq.matches }
  onMounted(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      mq = window.matchMedia('(prefers-reduced-motion: reduce)')
      update()
      mq.addEventListener?.('change', update)
    }
  })
  onUnmounted(() => {
    if (mq) mq.removeEventListener?.('change', update)
  })
  return { prefersReduced }
}

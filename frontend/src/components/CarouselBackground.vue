<template>
  <div
  class="carousel-bg"
  :class="[`slide-${idx}`, { 'is-reduced': reduced }]"
  aria-hidden="true"
  :style="{
    '--mx': parallax.x.toFixed(3),
    '--my': parallax.y.toFixed(3),
  }"
>
    <!-- 底层细网格 -->
    <svg class="grid-svg" viewBox="0 0 800 600" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M 48 0 L 0 0 0 48" fill="none" stroke="rgba(96,165,250,0.05)" stroke-width="0.5"/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)"/>
    </svg>

    <!-- 大模糊球(角落) -->
    <div class="orbs">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

    <!-- 轨道环(两侧) -->
    <div class="orbit orbit-l"></div>
    <div class="orbit orbit-r"></div>

    <!-- 背景水印 SVG:每屏一个巨大图标,藏在文字背后 -->
    <div class="bg-watermark" :class="`wm-${slides[idx].cap}`">
      <!-- 统计分析:柱状图 + 折线 -->
      <svg v-if="slides[idx].cap === 'observe'" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="wmo1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#67E8F9" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#60A5FA" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <rect x="55" y="120" width="22" height="48" fill="url(#wmo1)" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
        <rect x="87" y="90" width="22" height="78" fill="url(#wmo1)" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
        <rect x="119" y="65" width="22" height="103" fill="url(#wmo1)" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
        <rect x="151" y="105" width="22" height="63" fill="url(#wmo1)" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
        <polyline points="55,115 87,85 119,55 151,95 175,45" fill="none" stroke="rgba(103,232,249,0.2)" stroke-width="1.2"/>
      </svg>
      <!-- 高并发:服务器集群堆叠 -->
      <svg v-else-if="slides[idx].cap === 'scale'" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="wmsc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#67E8F9" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <rect x="52" y="44" width="96" height="30" rx="4" fill="url(#wmsc)" stroke="rgba(103,232,249,0.2)" stroke-width="1"/>
        <rect x="52" y="85" width="96" height="30" rx="4" fill="url(#wmsc)" stroke="rgba(103,232,249,0.2)" stroke-width="1"/>
        <rect x="52" y="126" width="96" height="30" rx="4" fill="url(#wmsc)" stroke="rgba(103,232,249,0.2)" stroke-width="1"/>
        <circle cx="68" cy="59" r="2.5" fill="rgba(103,232,249,0.45)"/>
        <circle cx="68" cy="100" r="2.5" fill="rgba(103,232,249,0.45)"/>
        <circle cx="68" cy="141" r="2.5" fill="rgba(103,232,249,0.45)"/>
        <line x1="100" y1="74" x2="100" y2="85" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
        <line x1="100" y1="115" x2="100" y2="126" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
      </svg>
      <!-- 防劫持:盾牌 + 锁 -->
      <svg v-else-if="slides[idx].cap === 'safe'" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="wms1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#67E8F9" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path d="M100 25 L160 50 L160 110 Q160 155 100 175 Q40 155 40 110 L40 50 Z" fill="url(#wms1)" stroke="rgba(103,232,249,0.2)" stroke-width="1"/>
        <rect x="80" y="90" width="40" height="35" rx="3" fill="none" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
        <path d="M85 90 V78 Q85 65 100 65 Q115 65 115 78 V90" fill="none" stroke="rgba(103,232,249,0.18)" stroke-width="1"/>
      </svg>
      <!-- 智能识别:过滤漏斗 + 噪点 -->
      <svg v-else-if="slides[idx].cap === 'filter'" viewBox="0 0 200 200">
        <defs>
          <linearGradient id="wmfl" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#67E8F9" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path d="M45 50 H155 L112 108 V158 L88 145 V108 Z" fill="url(#wmfl)" stroke="rgba(103,232,249,0.2)" stroke-width="1" stroke-linejoin="round"/>
        <path d="M60 68 H140" stroke="rgba(103,232,249,0.15)" stroke-width="1"/>
        <path d="M72 84 H128" stroke="rgba(103,232,249,0.13)" stroke-width="1"/>
        <circle cx="152" cy="58" r="3" fill="rgba(103,232,249,0.4)"/>
        <circle cx="163" cy="80" r="2" fill="rgba(103,232,249,0.3)"/>
        <circle cx="146" cy="90" r="1.6" fill="rgba(103,232,249,0.25)"/>
      </svg>
      <!-- CDN 加速:闪电 -->
      <svg v-else viewBox="0 0 200 200">
        <defs>
          <linearGradient id="wmf1" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#67E8F9" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path d="M115 30 L60 115 L92 115 L78 170 L142 80 L108 80 Z" fill="url(#wmf1)" stroke="rgba(103,232,249,0.2)" stroke-width="1" stroke-linejoin="round"/>
      </svg>
    </div>

    <!-- 扫描线 + 暗角 + 右侧渐隐 -->
    <div class="vignette"></div>
    <div class="fade-right"></div>

    <!-- 顶部 live ticker(去掉边框) -->
    <div class="ticker">
      <span class="ticker-dot"></span>
      <span class="ticker-label">LIVE</span>
      <div class="ticker-window">
        <div class="ticker-track" :style="{ animationPlayState: tickerPaused ? 'paused' : 'running' }">
          <button class="ticker-pause" :aria-label="tickerPaused ? 'resume' : 'pause'" @click="tickerPaused = !tickerPaused">
            <svg v-if="!tickerPaused" width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><rect x="2" y="1.5" width="2" height="7" rx="0.5"/><rect x="6" y="1.5" width="2" height="7" rx="0.5"/></svg>
            <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><polygon points="2.5,1.5 8.5,5 2.5,8.5"/></svg>
          </button>
          <span v-for="(item, i) in tickerItems.concat(tickerItems)" :key="i" class="ticker-item">
            <span class="ticker-from">{{ item.from }}</span>
            <span class="ticker-arrow">→</span>
            <span class="ticker-to">{{ item.to }}</span>
            <span class="ticker-sep">·</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 海报区:文字居左,SVG 在背景里 -->
    <div class="poster">
      <div class="poster-frame">
        <transition name="slide-fade" mode="out-in">
          <div :key="idx" class="poster-content">
            <div class="slide-cap">
              <span class="cap-prompt">&gt;</span>
              capability.<span class="cap-key">{{ slides[idx].cap }}</span>
            </div>

            <h2 class="slide-word">{{ slides[idx].word }}</h2>

            <p class="slide-sub">{{ slides[idx].sub }}</p>

            <div class="slide-tag">
              <span class="bracket">[</span>
              <span class="tag-text">{{ slides[idx].tag }}</span>
              <span class="bracket">]</span>
            </div>

            <div class="slide-meta">
              <span v-for="(m, i) in slides[idx].meta" :key="i" class="meta-item">
                <span class="meta-k">{{ m.k }}</span>
                <span class="meta-v">{{ m.v }}</span>
              </span>
            </div>
          </div>
        </transition>

        <!-- SYS_FEED 紧贴海报下方,无边框 -->
        <div class="feed-log">
          <div class="feed-header">
            <span class="feed-dot"></span>
            <span>SYS_FEED</span>
            <span class="feed-meta">· live events</span>
          </div>
          <div class="feed-body">
            <div v-for="(line, i) in feedLines" :key="`${idx}-${i}`" class="feed-line" :style="{ animationDelay: `${i * 0.1}s` }">
              <span class="feed-time">{{ line.time }}</span>
              <span class="feed-tag" :class="line.kind">{{ line.kind }}</span>
              <span class="feed-text">{{ line.text }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- HUD 边角 -->
    <div class="corner tl"></div>
    <div class="corner tr"></div>
    <div class="corner bl"></div>
    <div class="corner br"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useReducedMotion } from '@/composables/useReducedMotion'

const idx = ref(0)

const slides = [
  {
    word: '统计分析',
    sub: '永久短链自带访问统计，记录每次访问，地区分布与设备信息一图掌握',
    tag: 'REALTIME_ANALYTICS',
    cap: 'observe',
    meta: [{ k: 'geo', v: 'ON' }, { k: 'device', v: 'TRACK' }],
  },
  {
    word: '高并发',
    sub: '企业级独立云，支持高并发高负载，全国连通性强，稳定性 SLA 99.99%',
    tag: 'HIGH_CONCURRENCY',
    cap: 'scale',
    meta: [{ k: 'sla', v: '99.99%' }, { k: 'cloud', v: 'DEDICATED' }],
  },
  {
    word: '防劫持',
    sub: '数据传输与存储严格加密，Web 防火墙与防暴力破解，杜绝流量劫持',
    tag: 'ANTI_HIJACK',
    cap: 'safe',
    meta: [{ k: 'enc', v: 'AES-256' }, { k: 'waf', v: 'ON' }],
  },
  {
    word: '智能识别',
    sub: '智能访问策略，自动过滤虚假流量，精准识假，节约成本',
    tag: 'SMART_FILTER',
    cap: 'filter',
    meta: [{ k: 'filter', v: 'AI' }, { k: 'cost', v: 'DOWN' }],
  },
  {
    word: 'CDN加速',
    sub: '全球 CDN 加速，高速云服务器，跳转更快，提升转化率',
    tag: 'CDN_ACCELERATE',
    cap: 'fast',
    meta: [{ k: 'edge', v: 'GLOBAL' }, { k: 'p99', v: '12ms' }],
  },
]

const tickerItems = [
  { from: 'github.com/user/awesome', to: 'lnk.dev/x7k9m2' },
  { from: 'docs.company.com/q4-plan', to: 'lnk.dev/m3p8r1' },
  { from: 'blog.startup.io/launch', to: 'lnk.dev/k2n4b9' },
  { from: 'shop.example.com/sale', to: 'lnk.dev/p4w7c3' },
  { from: 'news.daily.io/2026/01', to: 'lnk.dev/b8n2q5' },
  { from: 'mp.weixin.qq.com/s/abc', to: 'lnk.dev/t9r1z6' },
]

const feedBase = [
  { kind: 'CRT', text: 'link x7k9m2 → 200 OK' },
  { kind: 'HIT', text: 'pv +1 (CN, 12ms)' },
  { kind: 'HIT', text: 'pv +1 (US, 48ms)' },
  { kind: 'DLT', text: 'link m3p8r1 removed' },
  { kind: 'CRT', text: 'link k2n4b9 → 200 OK' },
  { kind: 'HIT', text: 'pv +1 (JP, 22ms)' },
]

function randTime() {
  const h = String(Math.floor(Math.random() * 24)).padStart(2, '0')
  const m = String(Math.floor(Math.random() * 60)).padStart(2, '0')
  const s = String(Math.floor(Math.random() * 60)).padStart(2, '0')
  return `${h}:${m}:${s}`
}

function buildFeed() {
  return feedBase.slice().sort(() => Math.random() - 0.5).slice(0, 4).map(l => ({ ...l, time: randTime() }))
}

const feedLines = ref(buildFeed())
const tickerPaused = ref(false)
const parallax = ref({ x: 0, y: 0 })        // -1 ~ 1
const { prefersReduced: reduced } = useReducedMotion()

let slideTimer = null
let feedTimer = null
let rafId = null
let pendingMx = 0, pendingMy = 0

function next() { idx.value = (idx.value + 1) % slides.length }

function onMouseMove(e) {
  const w = window.innerWidth || 1
  const h = window.innerHeight || 1
  pendingMx = (e.clientX / w) * 2 - 1   // -1..1
  pendingMy = (e.clientY / h) * 2 - 1
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    parallax.value = { x: pendingMx, y: pendingMy }
    rafId = null
  })
}
function onMouseLeave() {
  pendingMx = 0; pendingMy = 0
  if (rafId) { cancelAnimationFrame(rafId); rafId = null }
  parallax.value = { x: 0, y: 0 }
}

onMounted(() => {
  slideTimer = setInterval(next, 5000)
  feedTimer = setInterval(() => { feedLines.value = buildFeed() }, 4000)
  if (!reduced.value) {
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    window.addEventListener('mouseleave', onMouseLeave)
  }
})
onUnmounted(() => {
  if (slideTimer) clearInterval(slideTimer)
  if (feedTimer) clearInterval(feedTimer)
  if (rafId) cancelAnimationFrame(rafId)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseleave', onMouseLeave)
})
</script>

<style scoped>
.carousel-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background: var(--bg);
  transition: background-color 1000ms ease;
}

/* per-slide 环境光 */
.slide-0 { background:
  radial-gradient(ellipse 60% 60% at 15% 25%, rgba(16, 185, 129, 0.22), transparent 60%),
  radial-gradient(ellipse 50% 60% at 78% 80%, rgba(34, 211, 238, 0.14), transparent 60%),
  var(--bg); }
.slide-1 { background:
  radial-gradient(ellipse 60% 60% at 75% 20%, rgba(59, 130, 246, 0.24), transparent 60%),
  radial-gradient(ellipse 50% 60% at 15% 80%, rgba(34, 211, 238, 0.12), transparent 60%),
  var(--bg); }
.slide-2 { background:
  radial-gradient(ellipse 60% 60% at 22% 75%, rgba(139, 92, 246, 0.18), transparent 60%),
  radial-gradient(ellipse 50% 60% at 78% 22%, rgba(59, 130, 246, 0.16), transparent 60%),
  var(--bg); }
.slide-3 { background:
  radial-gradient(ellipse 60% 60% at 70% 25%, rgba(34, 211, 238, 0.24), transparent 60%),
  radial-gradient(ellipse 50% 60% at 22% 75%, rgba(96, 165, 250, 0.16), transparent 60%),
  var(--bg); }
.slide-4 { background:
  radial-gradient(ellipse 60% 60% at 72% 72%, rgba(34, 211, 238, 0.22), transparent 60%),
  radial-gradient(ellipse 50% 60% at 18% 22%, rgba(16, 185, 129, 0.16), transparent 60%),
  var(--bg); }

.grid-svg {
  position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0.7;
  mask-image: radial-gradient(ellipse at 30% 50%, black 30%, transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse at 30% 50%, black 30%, transparent 75%);
}

/* 角落模糊球 */
.orbs {
  position: absolute; inset: 0; pointer-events: none;
  transform-style: preserve-3d;
  transform: translate3d(calc(var(--mx, 0) * -16px), calc(var(--my, 0) * -10px), 0);
  transition: transform 700ms cubic-bezier(0.2, 0.7, 0.2, 1);
}
.orb {
  position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.55;
  will-change: transform;
}
.orb-1 { width: 520px; height: 520px; background: linear-gradient(135deg, #3B82F6, #22D3EE); top: -12%; left: -8%; animation: drift-large 22s ease-in-out infinite; }
.orb-2 { width: 460px; height: 460px; background: linear-gradient(135deg, #8B5CF6, #3B82F6); bottom: -14%; right: -6%; animation: drift-large 28s ease-in-out infinite reverse; }
.orb-3 { width: 360px; height: 360px; background: linear-gradient(135deg, #22D3EE, #10B981); top: 55%; left: 8%; opacity: 0.35; animation: drift-large 32s ease-in-out infinite;
  transform: translate(calc(var(--mx, 0) * 28px), calc(var(--my, 0) * 18px));
  transition: transform 900ms cubic-bezier(0.2, 0.7, 0.2, 1);
}
@keyframes drift-large {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33%      { transform: translate(60px, -40px) scale(1.05); }
  66%      { transform: translate(-40px, 60px) scale(0.95); }
}

/* 轨道环 */
.orbit { position: absolute; border: 1px solid; border-radius: 50%; opacity: 0.18; pointer-events: none; }
.orbit-l { width: 520px; height: 520px; top: 8%; left: -8%; border-color: #67E8F9; border-top-color: transparent; animation: orbit-spin 36s linear infinite; }
.orbit-r { width: 440px; height: 440px; bottom: -6%; right: -6%; border-color: #A78BFA; border-bottom-color: transparent; animation: orbit-spin 44s linear infinite reverse; }
@keyframes orbit-spin { to { transform: rotate(360deg); } }

/* === 背景水印(per-slide SVG,藏在文字背后) === */
.bg-watermark {
  position: absolute;
  top: 50%; left: 32%;
  width: clamp(420px, 42vw, 620px);
  height: clamp(420px, 42vw, 620px);
  transform: translate(calc(-50% + var(--mx, 0) * 22px), calc(-50% + var(--my, 0) * 14px)) rotate(-8deg);
  pointer-events: none;
  opacity: 0.55;
  z-index: 1;
  transition: opacity 600ms ease, transform 1100ms cubic-bezier(0.2, 0.7, 0.2, 1);
}
.bg-watermark svg {
  width: 100%;
  height: 100%;
}
.bg-watermark.wm-observe { filter: drop-shadow(0 0 60px rgba(139, 92, 246, 0.25)); }
.bg-watermark.wm-scale { filter: drop-shadow(0 0 60px rgba(59, 130, 246, 0.25)); }
.bg-watermark.wm-safe { filter: drop-shadow(0 0 60px rgba(16, 185, 129, 0.25)); }
.bg-watermark.wm-filter { filter: drop-shadow(0 0 60px rgba(34, 211, 238, 0.25)); }
.bg-watermark.wm-fast { filter: drop-shadow(0 0 60px rgba(34, 211, 238, 0.25)); }

/* 扫描线 */
/* vignette + 右侧渐隐 */
.vignette { position: absolute; inset: 0; background: radial-gradient(ellipse at 30% 50%, transparent 30%, rgba(11, 11, 16, 0.55) 90%); pointer-events: none; }
.fade-right { position: absolute; top: 0; right: 0; bottom: 0; width: 50%; background: linear-gradient(90deg, transparent 0%, rgba(11, 11, 16, 0.35) 50%, rgba(11, 11, 16, 0.6) 100%); pointer-events: none; }

/* === 顶部 ticker(去边框) === */
.ticker {
  position: absolute;
  top: 78px;
  left: 32px;
  right: 32px;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 28px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  z-index: 5;
  pointer-events: auto;
}

.ticker-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--success); box-shadow: 0 0 6px var(--success);
  animation: pulse-glow 1.4s ease-in-out infinite;
  flex-shrink: 0;
}
.ticker-pause {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; padding: 0;
  margin-left: 8px;
  border: 1px solid rgba(103, 232, 249, 0.35);
  border-radius: 50%;
  background: rgba(11, 11, 16, 0.55);
  color: #67E8F9;
  cursor: pointer;
  flex-shrink: 0;
  text-transform: none;
  letter-spacing: 0;
  font-size: 0;
  transition: background-color var(--t-fast), border-color var(--t-fast), box-shadow var(--t-fast), transform var(--t-fast);
  backdrop-filter: blur(6px);
}
.ticker-pause:hover {
  border-color: #67E8F9;
  color: #67E8F9;
  box-shadow: 0 0 12px rgba(103, 232, 249, 0.45);
  background: rgba(34, 211, 238, 0.08);
}
.ticker-pause:active { transform: scale(0.92); }
.ticker-pause svg { display: block; }

.ticker-label {
  color: #67E8F9; font-weight: 600; flex-shrink: 0;
  letter-spacing: 0.2em;
}
.ticker-window {
  flex: 1; overflow: hidden;
  mask-image: linear-gradient(90deg, transparent, black 6%, black 94%, transparent);
  -webkit-mask-image: linear-gradient(90deg, transparent, black 6%, black 94%, transparent);
}
.ticker-track {
  display: inline-flex; white-space: nowrap;
  animation: ticker-scroll 40s linear infinite;
  will-change: transform;
}
.ticker-item { display: inline-flex; align-items: center; gap: 8px; padding: 0 16px; }
.ticker-from { color: rgba(148, 163, 184, 0.85); }
.ticker-arrow { color: #60A5FA; }
.ticker-to { color: #67E8F9; font-weight: 600; }
.ticker-sep { color: rgba(148, 163, 184, 0.4); }
@keyframes ticker-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }

/* === 海报 === */
.poster {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 130px 0 60px clamp(80px, 12vw, 180px);  /* 文字往中间靠 */
  pointer-events: none;
}
.poster-frame {
  pointer-events: auto;
  width: 100%;
  max-width: 640px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
  z-index: 3;                            /* 文字在水印之上 */
}
.poster-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.slide-cap {
  font-family: var(--font-mono);
  font-size: 12px;
  color: rgba(103, 232, 249, 0.85);
  letter-spacing: 0.18em;
  margin-bottom: 18px;
}
.cap-prompt { color: #60A5FA; margin-right: 4px; }
.cap-key { color: rgba(248, 250, 252, 0.95); font-weight: 600; }

/* === 主词：solid color + 柔和 glow(去掉双层叠加) === */
.slide-word {
  display: inline-block;
  font-family: var(--font-sans);
  font-size: clamp(56px, 7vw, 106px);
  font-weight: 700;
  line-height: 0.95;
  margin: 0 0 18px;
  letter-spacing: 0.02em;
  text-align: left;
  color: #E2E8F0;                          /* 不用纯白,减少刺眼 */
  text-shadow:
    0 0 20px rgba(96, 165, 250, 0.25),     /* 柔和光晕 */
    0 0 48px rgba(34, 211, 238, 0.15);
}

.slide-sub {
  font-size: clamp(14px, 1.2vw, 17px);
  color: rgba(226, 232, 240, 0.78);
  margin: 0 0 16px;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.slide-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(148, 163, 184, 0.78);
  letter-spacing: 0.18em;
  margin-bottom: 16px;
}
.bracket { color: #60A5FA; margin: 0 6px; }

.slide-meta {
  display: inline-flex;
  gap: 18px;
  padding: 8px 14px;
  border: 1px solid rgba(96, 165, 250, 0.18);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  background: rgba(11, 11, 16, 0.4);
  backdrop-filter: blur(8px);
}
.meta-item { display: inline-flex; align-items: baseline; gap: 6px; }
.meta-k { color: rgba(148, 163, 184, 0.7); }
.meta-v { color: #67E8F9; font-weight: 600; }

/* === 切换动画 === */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: opacity 600ms ease, transform 600ms ease, filter 600ms ease;
}
.slide-fade-enter-from { opacity: 0; transform: translateY(20px); filter: blur(8px); }
.slide-fade-leave-to   { opacity: 0; transform: translateY(-20px); filter: blur(8px); }

/* === SYS_FEED (去边框,只在文字下方) === */
.feed-log {
  position: relative;
  width: 100%;
  max-width: 580px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  z-index: 3;
  align-self: flex-start;
}
.feed-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 6px;
  color: rgba(148, 163, 184, 0.55);
  letter-spacing: 0.18em;
  font-size: 9px;
}
.feed-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: #67E8F9;
  box-shadow: 0 0 4px #67E8F9;
  animation: pulse-glow 1.6s ease-in-out infinite;
}
.feed-meta { color: rgba(148, 163, 184, 0.4); margin-left: auto; font-size: 9px; letter-spacing: 0.1em; }
.feed-body {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.feed-line {
  display: flex;
  gap: 8px;
  align-items: baseline;
  animation: feed-fade 4s ease both;
  padding: 1px 0;
}
.feed-time { color: rgba(148, 163, 184, 0.5); flex-shrink: 0; font-variant-numeric: tabular-nums; }
.feed-tag { flex-shrink: 0; font-weight: 700; font-size: 9px; }
.feed-tag.CRT { color: #6EE7B7; }
.feed-tag.HIT { color: #67E8F9; }
.feed-tag.DLT { color: #FCD34D; }
.feed-text { color: rgba(226, 232, 240, 0.75); }
@keyframes feed-fade {
  from { opacity: 0; transform: translateX(8px); }
  to { opacity: 1; transform: translateX(0); }
}

/* === HUD 边角 === */
.corner { position: absolute; width: 32px; height: 32px; border: 1px solid rgba(96, 165, 250, 0.25); opacity: 0.7; pointer-events: none; }
.corner.tl { top: 16px; left: 16px; border-right: none; border-bottom: none; }
.corner.tr { top: 16px; right: 16px; border-left: none; border-bottom: none; }
.corner.bl { bottom: 16px; left: 16px; border-right: none; border-top: none; }
.corner.br { bottom: 16px; right: 16px; border-left: none; border-top: none; }

/* === 响应式 === */
@media (max-width: 980px) {
  .poster {
    padding: 130px 24px 24px;
    justify-content: center;
  }
  .bg-watermark { left: 50%; width: 320px; height: 320px; opacity: 0.4; }
}
@media (max-width: 720px) {
  .corner { display: none; }
  .ticker { left: 16px; right: 16px; top: 72px; }
  .bg-watermark { display: none; }
}
</style>

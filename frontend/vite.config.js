import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import http from 'node:http'
import https from 'node:https'
import { URL } from 'node:url'

// 解析代理 target:
//  1. 优先 shell 环境变量 VITE_API_BASE
//  2. 其次 .env / .env.local / .env.[mode] 里的 VITE_API_BASE 或 VITE_BASE_DOMAIN
//  3. 最后兜底为 http://127.0.0.1:8765
function resolveApiBase() {
  let raw =
    process.env.VITE_API_BASE ||
    process.env.VITE_BASE_DOMAIN
  if (!raw) {
    const env = loadEnv(process.env.NODE_ENV || 'development', process.cwd(), '')
    raw = env.VITE_API_BASE || env.VITE_BASE_DOMAIN
  }
  const fallback = 'http://127.0.0.1:8765'
  const final = (raw && raw.trim()) || fallback
  return final.replace(/\/$/, '')
}
const API_BASE = resolveApiBase()
console.log('[vite] API proxy target =>', API_BASE)

/**
 * 自定义 Vite 插件:显式前缀匹配代理
 * 规则:
 *   /api/xxx     → 代理
 *   /apidocs/xxx → 代理
 *   /s/<短码>    → 代理(短码 = [A-Za-z0-9]+,不含 '/',不会误中 /src/...)
 *   其它(包括 /src/...)→ 不代理,vite 正常服务
 */
function explicitProxy() {
  let target
  try {
    target = new URL(API_BASE)
  } catch (e) {
    throw new Error('[vite] API_BASE 不是合法 URL: ' + API_BASE)
  }
  const isHttps = target.protocol === 'https:'
  const httpLib = isHttps ? https : http

  const matchers = [
    { test: (p) => p === '/api' || p.startsWith('/api/') },
    { test: (p) => p === '/apidocs' || p.startsWith('/apidocs/') },
    { test: (p) => p === '/s' },
    { test: (p) => {
      if (!p.startsWith('/s/')) return false
      const code = p.slice(3)
      return code.length > 0 && code.indexOf('/') === -1
    }},
  ]

  return {
    name: 'explicit-proxy',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || ''
        const qIdx = url.indexOf('?')
        const pathname = qIdx === -1 ? url : url.slice(0, qIdx)

        if (!matchers.some(m => m.test(pathname))) {
          return next()
        }

        const opts = {
          hostname: target.hostname,
          port: target.port || (isHttps ? 443 : 80),
          method: req.method,
          path: url,
          headers: { ...req.headers, host: target.host },
        }

        const proxyReq = httpLib.request(opts, (proxyRes) => {
          res.writeHead(proxyRes.statusCode || 502, proxyRes.headers)
          proxyRes.pipe(res)
        })
        proxyReq.on('error', (err) => {
          console.error('[proxy] ' + pathname + ' → ' + API_BASE + ' 失败:', err.code || err.message)
          if (!res.headersSent) {
            res.statusCode = 502
            res.setHeader('Content-Type', 'application/json')
          }
          res.end(JSON.stringify({
            code: -1,
            message: '后端 ' + API_BASE + ' 连不上 (' + (err.code || err.message) + '). 请确认 python wsgi.py 已启动并监听 8765.',
          }))
        })
        req.pipe(proxyReq)
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), explicitProxy()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5174,
    allowedHosts: true,
    strictPort: true,
    proxy: undefined,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
  },
})

import { chromium } from 'playwright-core'
import fs from 'node:fs/promises'
import path from 'node:path'
import { APP_ROUTES } from '../src/app/routes/routeRegistry.js'

const BASE_URL = process.env.UI_BASE_URL || 'http://127.0.0.1:5173'
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000'
const SLO_TARGET_MS = Number(process.env.UI_AUDIT_SLO_MS || 200)
const CAPTURE_ALL_ROUTES = process.env.UI_AUDIT_ROUTES !== '0'
const PERFORMANCE_SAMPLES = Math.max(20, Number(process.env.UI_AUDIT_PERFORMANCE_SAMPLES || 20))
const EDGE_PATH = process.env.EDGE_PATH || (
  process.platform === 'win32'
    ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    : chromium.executablePath()
)
const AUDIT_ROLE = process.env.UI_AUDIT_ROLE || 'admin'
const LOCAL_AUDIT_ACCOUNTS = {
  user: { username: 'codex_ui_audit_user', password: 'CodexAuditUser!2026' },
  admin: { username: 'codex_ui_audit_admin', password: 'CodexAuditAdmin!2026' },
}
const AUDIT_USERNAME = process.env.UI_AUDIT_USERNAME || LOCAL_AUDIT_ACCOUNTS[AUDIT_ROLE]?.username
const AUDIT_PASSWORD = process.env.UI_AUDIT_PASSWORD || LOCAL_AUDIT_ACCOUNTS[AUDIT_ROLE]?.password
const AUDIT_TILE_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL5WQAAAABJRU5ErkJggg==',
  'base64',
)

if (!['public', 'user', 'admin'].includes(AUDIT_ROLE)) {
  throw new Error(`Unsupported UI_AUDIT_ROLE "${AUDIT_ROLE}". Use public, user, or admin.`)
}

const stamp = new Date().toISOString().replace(/[:.]/g, '-')
const rootDir = path.resolve(process.cwd(), '..')
const outDir = path.join(rootDir, 'reports', 'ui-audit', 'baseline', stamp)

const activeRoutes = APP_ROUTES
  .filter(route => route.shell === AUDIT_ROLE)
  .map(route => ({
    slug: route.path === '/' ? 'prediction' : route.path.replace(/^\//, '').replaceAll('/', '-'),
    path: route.path,
    label: route.title,
  }))

const predictionPath = APP_ROUTES.find(
  route => route.shell === AUDIT_ROLE && route.component === 'Prediction',
)?.path

if (!predictionPath) {
  throw new Error(`No Prediction route registered for role "${AUDIT_ROLE}".`)
}

const predictionPropertyTypes = [
  { slug: 'land', label: 'Đất nền' },
  { slug: 'apartment', label: 'Căn hộ' },
  { slug: 'townhouse', label: 'Nhà phố' },
  { slug: 'villa', label: 'Biệt thự' },
  { slug: 'house', label: 'Nhà riêng' },
]

const predictionTabs = [
  { slug: 'map', label: 'Định vị thông minh' },
  { slug: 'result', label: 'Kết quả' },
  { slug: 'comparables', label: 'So sánh' },
  { slug: 'pipeline', label: 'Pipeline' },
  { slug: 'impact', label: 'Tác động' },
]

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true })
}

async function writeManifest(manifest) {
  await fs.writeFile(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8')
}

function sanitizeError(error) {
  if (!error) return null
  const message = String(error.message || error).replace(AUDIT_PASSWORD, '[redacted]')
  return message.length > 600 ? `${message.slice(0, 600)}…` : message
}

async function login() {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: AUDIT_USERNAME, password: AUDIT_PASSWORD }),
  })
  const bodyText = await res.text()
  if (!res.ok) {
    throw new Error(`Audit admin login failed: HTTP ${res.status} ${bodyText.slice(0, 300)}`)
  }
  return JSON.parse(bodyText)
}

async function capture(page, manifest, slug, description, options = {}) {
  const file = `${slug}.png`
  const filePath = path.join(outDir, file)
  const entry = {
    slug,
    description,
    url: page.url(),
    file,
    viewport: page.viewportSize(),
    captured_at: new Date().toISOString(),
    notes: options.notes || [],
    errors: options.errors || [],
  }
  try {
    await page.screenshot({
      path: filePath,
      fullPage: true,
      animations: 'disabled',
      timeout: 90_000,
    })
    entry.status = 'captured'
  } catch (error) {
    entry.status = 'failed'
    entry.errors.push(sanitizeError(error))
  }
  manifest.screenshots.push(entry)
  await writeManifest(manifest)
  return entry
}

async function gotoAndSettle(page, routePath) {
  const response = await page.goto(`${BASE_URL}${routePath}`, { waitUntil: 'domcontentloaded', timeout: 45_000 })
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})
  await page.waitForTimeout(350)
  return response
}

async function readNavigationTiming(page) {
  return page.evaluate(() => {
    const entry = performance.getEntriesByType('navigation')[0]
    if (!entry) return null
    return {
      response_ms: Math.round((entry.responseEnd - entry.requestStart) * 10) / 10,
      dom_content_loaded_ms: Math.round(entry.domContentLoadedEventEnd * 10) / 10,
      load_event_ms: Math.round(entry.loadEventEnd * 10) / 10,
    }
  })
}

async function readCanvasPixels(page) {
  const canvas = page.locator('[data-testid="property-model-3d"] canvas').first()
  await canvas.waitFor({ state: 'visible', timeout: 15_000 })
  await page.waitForTimeout(900)
  return canvas.evaluate(async node => {
    node.__r3f?.root?.getState?.().invalidate?.()
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    const gl = node.getContext('webgl2') || node.getContext('webgl')
    if (!gl || node.width < 2 || node.height < 2) {
      return { ok: false, width: node.width, height: node.height, error: 'WebGL context unavailable' }
    }
    const pixels = new Uint8Array(node.width * node.height * 4)
    gl.readPixels(0, 0, node.width, node.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
    const reference = [pixels[0], pixels[1], pixels[2]]
    const step = Math.max(4, Math.floor(pixels.length / 80_000 / 4) * 4)
    let sampled = 0
    let nonBackground = 0
    let visible = 0
    for (let index = 0; index < pixels.length; index += step) {
      const alpha = pixels[index + 3]
      const delta = Math.abs(pixels[index] - reference[0])
        + Math.abs(pixels[index + 1] - reference[1])
        + Math.abs(pixels[index + 2] - reference[2])
      sampled++
      if (alpha > 0) visible++
      if (alpha > 0 && delta > 24) nonBackground++
    }
    const nonBackgroundRatio = sampled ? nonBackground / sampled : 0
    return {
      ok: visible > 0 && nonBackgroundRatio > 0.015,
      width: node.width,
      height: node.height,
      sampled_pixels: sampled,
      non_background_ratio: Math.round(nonBackgroundRatio * 10_000) / 10_000,
    }
  })
}

async function runBrowserApiBenchmark(page, payload) {
  return page.evaluate(async ({ body, sampleCount }) => {
    const token = localStorage.getItem('avm-token')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`
    const run = async () => {
      const startedAt = performance.now()
      const response = await fetch('/api/v2/pipeline', {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
      await response.json()
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return {
        e2e_ms: performance.now() - startedAt,
        backend_ms: Number(response.headers.get('X-Response-Time-Ms') || 0),
      }
    }
    for (let index = 0; index < 2; index++) await run()
    const samples = []
    for (let index = 0; index < sampleCount; index++) samples.push(await run())
    const percentile = (values, ratio) => {
      const sorted = [...values].sort((left, right) => left - right)
      const position = Math.max(0, Math.ceil(sorted.length * ratio) - 1)
      return Math.round(sorted[position] * 10) / 10
    }
    const e2e = samples.map(sample => sample.e2e_ms)
    const backend = samples.map(sample => sample.backend_ms)
    return {
      samples: sampleCount,
      e2e_p50_ms: percentile(e2e, 0.5),
      e2e_p95_ms: percentile(e2e, 0.95),
      backend_p95_ms: percentile(backend, 0.95),
      max_ms: Math.round(Math.max(...e2e) * 10) / 10,
    }
  }, { body: payload, sampleCount: PERFORMANCE_SAMPLES })
}

async function clickIfVisible(page, label, timeout = 2500) {
  const target = page.getByRole('button', { name: new RegExp(label, 'i') }).first()
  try {
    await target.click({ timeout, force: true })
    await page.waitForLoadState('networkidle', { timeout: 3_000 }).catch(() => {})
    await page.waitForTimeout(300)
    return true
  } catch {
    return false
  }
}

async function selectFirstDistrict(page) {
  const districtGroup = page.locator('.form-group', { hasText: /Quận|Huyện/i }).first()
  const districtSelect = districtGroup.locator('select').first()
  await districtSelect.waitFor({ state: 'visible', timeout: 8_000 })
  const options = await districtSelect.locator('option').evaluateAll(nodes =>
    nodes.map((node, index) => ({ index, value: node.value, label: node.textContent?.trim() || '' }))
  )
  const preferred = options.find(opt => /Cầu Giấy|Quận 1|Bình Thạnh|Đống Đa/i.test(opt.label))
  const fallback = options.find(opt => opt.index > 0 && opt.value)
  const selected = preferred || fallback
  if (!selected) throw new Error('No district option is available for prediction capture')
  await districtSelect.selectOption(selected.value)
}

async function fillFirstInputInGroup(page, groupText, value) {
  const label = page.locator('.form-label').filter({ hasText: groupText }).first()
  const group = label.locator('xpath=..')
  const input = group.locator('input').first()
  await input.waitFor({ state: 'visible', timeout: 4_000 })
  await input.fill(String(value))
}

async function tryRunPrediction(page, manifest, options = {}) {
  const {
    propertyLabel = 'Đất nền',
    fields = [
      [/Diện tích/i, 120],
      [/Mặt tiền/i, 6, true],
      [/Chiều sâu tối thiểu/i, 18, true],
      [/Chiều sâu tối đa/i, 20, true],
    ],
    benchmark = true,
    recordPrimary = true,
  } = options
  const result = {
    ok: false,
    notes: [],
    loading_feedback_ms: null,
    api_response_ms: null,
    response_status: null,
    backend_response_ms: null,
    network_response_ms: null,
    ui_settled_ms: null,
  }
  try {
    await clickIfVisible(page, propertyLabel, 2500)
    await selectFirstDistrict(page)
    for (const [label, value, optional] of fields) {
      const fill = fillFirstInputInGroup(page, label, value)
      if (optional) await fill.catch(() => {})
      else await fill
    }

    const submitButton = page.locator('form button[type="submit"]').first()
    await submitButton.scrollIntoViewIfNeeded()
    await submitButton.waitFor({ state: 'visible' })
    const responsePromise = page.waitForResponse(response => {
      const url = new URL(response.url())
      return url.pathname === '/api/v2/pipeline' && response.request().method() === 'POST'
    }, { timeout: 35_000 })
    const feedbackPromise = page.waitForFunction(() => (
      document.body.innerText.includes('Đang chạy Valuation Engine')
      || [...document.querySelectorAll('button')].some(button => /Đang chạy|Đang tính|Đang định giá/.test(button.textContent || ''))
    ), null, { timeout: 2_000 })
      .then(() => page.evaluate(() => Math.round((performance.now() - window.__avmAuditClickAt) * 10) / 10))
      .catch(() => null)
    await submitButton.evaluate(button => {
      window.__avmAuditClickAt = performance.now()
      button.click()
    })
    const response = await responsePromise
    await response.finished()
    const browserTiming = await page.evaluate(() => {
      const entries = performance.getEntriesByType('resource').filter(entry => {
        try { return new URL(entry.name).pathname === '/api/v2/pipeline' } catch { return false }
      })
      const entry = entries.at(-1)
      return {
        api_response_ms: entry
          ? Math.round((entry.responseEnd - window.__avmAuditClickAt) * 10) / 10
          : null,
        request_start_delay_ms: entry
          ? Math.round((entry.startTime - window.__avmAuditClickAt) * 10) / 10
          : null,
        ui_settled_ms: Math.round((performance.now() - window.__avmAuditClickAt) * 10) / 10,
      }
    })
    result.api_response_ms = browserTiming.api_response_ms
    result.request_start_delay_ms = browserTiming.request_start_delay_ms
    result.ui_settled_ms = browserTiming.ui_settled_ms
    result.loading_feedback_ms = await feedbackPromise
    result.response_status = response.status()
    result.backend_response_ms = Number(response.headers()['x-response-time-ms'] || 0) || null
    result.network_response_ms = Math.round(response.request().timing().responseEnd * 10) / 10
    if (response.ok() && benchmark) {
      result.api_benchmark = await runBrowserApiBenchmark(page, response.request().postDataJSON())
    }
    if (!response.ok()) {
      result.notes.push(`Prediction API failed: HTTP ${response.status()} ${(await response.text()).slice(0, 240)}`)
    }
    await page.waitForTimeout(500)

    const unlocked = await page.getByRole('button', { name: 'Kết quả', exact: true }).first()
      .evaluate(node => !node.disabled)
      .catch(() => false)
    result.ok = unlocked && response.ok()
    result.notes.push(unlocked ? 'Prediction result tabs unlocked.' : 'Prediction submit ran but result tabs stayed locked.')
    result.notes.push(`Loading feedback: ${result.loading_feedback_ms ?? 'not observed'}ms; click-to-response: ${result.api_response_ms}ms; network: ${result.network_response_ms}ms; backend: ${result.backend_response_ms ?? 'unknown'}ms; UI settled: ${result.ui_settled_ms}ms.`)
  } catch (error) {
    result.notes.push(`Prediction automation skipped: ${sanitizeError(error)}`)
  }
  if (recordPrimary) {
    manifest.prediction_flow = result
    await writeManifest(manifest)
  }
  return result
}

async function capture3DVariant(page, manifest, variant) {
  await gotoAndSettle(page, predictionPath)
  const prediction = await tryRunPrediction(page, manifest, {
    propertyLabel: variant.label,
    fields: variant.fields,
    benchmark: false,
    recordPrimary: false,
  })
  await clickIfVisible(page, 'Kết quả', 5_000)
  await clickIfVisible(page, 'Mô hình 3D', 8_000)
  const canvas = await readCanvasPixels(page).catch(error => ({ ok: false, error: sanitizeError(error) }))
  const result = {
    slug: variant.slug,
    label: variant.label,
    ok: prediction.ok && canvas.ok,
    response_status: prediction.response_status,
    backend_response_ms: prediction.backend_response_ms,
    canvas,
  }
  manifest.prediction_3d_variants.push(result)
  await capture(page, manifest, variant.captureSlug, `Prediction 3D variant: ${variant.label}`, {
    notes: [
      result.ok
        ? `Variant passed; canvas ratio ${canvas.non_background_ratio}.`
        : `Variant failed: ${prediction.notes.join(' ')} ${canvas.error || ''}`,
    ],
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(350)
  result.mobile_canvas = await readCanvasPixels(page).catch(error => ({ ok: false, error: sanitizeError(error) }))
  result.ok = result.ok && result.mobile_canvas.ok
  await capture(page, manifest, `${variant.captureSlug}-mobile`, `Prediction 3D mobile: ${variant.label}`, {
    notes: [
      result.mobile_canvas.ok
        ? `Mobile canvas ratio ${result.mobile_canvas.non_background_ratio}.`
        : `Mobile canvas failed: ${result.mobile_canvas.error || 'scene is blank'}`,
    ],
  })
  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.waitForTimeout(250)
  await writeManifest(manifest)
}

async function capturePredictionStates(page, manifest) {
  await gotoAndSettle(page, predictionPath)
  await capture(page, manifest, 'prediction-00-default', 'Prediction default form')

  for (const type of predictionPropertyTypes) {
    await gotoAndSettle(page, predictionPath)
    const clicked = await clickIfVisible(page, type.label)
    await capture(page, manifest, `prediction-type-${type.slug}`, `Prediction property type: ${type.label}`, {
      notes: clicked ? [] : [`Could not click property type "${type.label}".`],
    })
  }

  await gotoAndSettle(page, predictionPath)
  const clickedMap = await clickIfVisible(page, 'Định vị thông minh')
  await capture(page, manifest, 'prediction-tab-map', 'Prediction smart location tab', {
    notes: clickedMap ? [] : ['Could not open map/location tab.'],
  })

  await gotoAndSettle(page, predictionPath)
  const prediction = await tryRunPrediction(page, manifest)
  await capture(page, manifest, 'prediction-after-submit', 'Prediction after submit attempt', {
    notes: prediction.notes,
  })

  for (const tab of predictionTabs.filter(t => t.slug !== 'map' && (t.slug !== 'impact' || AUDIT_ROLE === 'admin'))) {
    const clicked = await clickIfVisible(page, tab.label)
    await capture(page, manifest, `prediction-tab-${tab.slug}`, `Prediction tab: ${tab.label}`, {
      notes: clicked ? [] : [`Tab "${tab.label}" could not be opened, likely still locked or hidden.`],
    })
    if (tab.slug === 'result' && prediction.ok) {
      await clickIfVisible(page, 'Mô hình 3D', 8_000)
      const canvas = await readCanvasPixels(page).catch(error => ({ ok: false, error: sanitizeError(error) }))
      prediction.canvas = canvas
      prediction.ok = prediction.ok && canvas.ok
      await capture(page, manifest, 'prediction-model-3d', 'Prediction 3D massing model', {
        notes: [
          canvas.ok
            ? `Canvas pixel check passed (${canvas.non_background_ratio} non-background ratio).`
            : `Canvas pixel check failed: ${canvas.error || 'scene is blank'}`,
        ],
      })
      manifest.prediction_flow = prediction
      await writeManifest(manifest)
    }
  }

  const modelVariants = [
    {
      slug: 'apartment',
      label: 'Căn hộ',
      captureSlug: 'prediction-model-3d-apartment',
      fields: [[/Diện tích căn hộ/i, 82], [/^Tầng(?:\s*\*)?$/i, 15]],
    },
    {
      slug: 'townhouse',
      label: 'Nhà phố',
      captureSlug: 'prediction-model-3d-townhouse',
      fields: [[/Diện tích đất/i, 72], [/Số tầng/i, 4]],
    },
  ]
  for (const variant of modelVariants) await capture3DVariant(page, manifest, variant)

  manifest.performance.prediction = {
    loading_feedback_ms: prediction.loading_feedback_ms,
    api_response_ms: prediction.api_response_ms,
    response_status: prediction.response_status,
    backend_response_ms: prediction.backend_response_ms,
    network_response_ms: prediction.network_response_ms,
    request_start_delay_ms: prediction.request_start_delay_ms,
    ui_settled_ms: prediction.ui_settled_ms,
    api_benchmark: prediction.api_benchmark,
    slo_target_ms: SLO_TARGET_MS,
    loading_feedback_pass: prediction.loading_feedback_ms != null && prediction.loading_feedback_ms < SLO_TARGET_MS,
    api_response_pass: prediction.api_benchmark?.e2e_p95_ms < SLO_TARGET_MS,
    backend_response_pass: prediction.api_benchmark?.backend_p95_ms < SLO_TARGET_MS,
    cold_flow_pass: prediction.api_response_ms != null && prediction.api_response_ms < 500,
  }
}

async function main() {
  await ensureDir(outDir)

  const manifest = {
    captured_at: new Date().toISOString(),
    base_url: BASE_URL,
    api_base_url: API_BASE_URL,
    out_dir: outDir,
    role: AUDIT_ROLE,
    route_count: activeRoutes.length,
    screenshots: [],
    console: [],
    page_errors: [],
    prediction_3d_variants: [],
    performance: {
      slo_target_ms: SLO_TARGET_MS,
      routes: [],
    },
  }

  const tokenData = AUDIT_ROLE === 'public' ? null : await login()
  const browser = await chromium.launch({ executablePath: EDGE_PATH, headless: true })
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    deviceScaleFactor: 1,
  })
  await context.route('**/*', route => {
    const request = route.request()
    const isExternalImage = request.resourceType() === 'image'
      && !request.url().startsWith(BASE_URL)
      && !request.url().startsWith(API_BASE_URL)
    return isExternalImage
      ? route.fulfill({ status: 200, contentType: 'image/png', body: AUDIT_TILE_PNG })
      : route.continue()
  })

  await context.addInitScript(({ accessToken, refreshToken, user }) => {
    if (accessToken && user) {
      window.localStorage.setItem('avm-token', accessToken)
      if (refreshToken) window.localStorage.setItem('avm-refresh', refreshToken)
      window.localStorage.setItem('avm-user', JSON.stringify(user))
    } else {
      window.localStorage.removeItem('avm-token')
      window.localStorage.removeItem('avm-refresh')
      window.localStorage.removeItem('avm-user')
    }
    window.localStorage.setItem('avm-theme', 'dark')
  }, {
    accessToken: tokenData?.access_token,
    refreshToken: tokenData?.refresh_token,
    user: tokenData?.user,
  })

  const page = await context.newPage()
  page.on('console', msg => {
    if (!['error', 'warning'].includes(msg.type())) return
    manifest.console.push({
      type: msg.type(),
      text: msg.text().slice(0, 700),
      location: msg.location(),
      at: new Date().toISOString(),
    })
  })
  page.on('pageerror', error => {
    manifest.page_errors.push({
      message: sanitizeError(error),
      stack: sanitizeError(error.stack),
      at: new Date().toISOString(),
    })
  })

  for (const route of CAPTURE_ALL_ROUTES ? activeRoutes : []) {
    try {
      const response = await gotoAndSettle(page, route.path)
      const timing = await readNavigationTiming(page)
      manifest.performance.routes.push({ path: route.path, ...timing })
      await capture(page, manifest, `route-${route.slug}`, `${route.label} (${route.path})`, {
        notes: [`HTTP ${response?.status?.() ?? 'unknown'}`],
      })
    } catch (error) {
      manifest.screenshots.push({
        slug: `route-${route.slug}`,
        description: `${route.label} (${route.path})`,
        status: 'failed',
        errors: [sanitizeError(error)],
      })
      await writeManifest(manifest)
    }
  }

  await capturePredictionStates(page, manifest)

  await writeManifest(manifest)
  await browser.close()

  const summary = {
    outDir,
    screenshotCount: manifest.screenshots.filter(s => s.status === 'captured').length,
    failedCount: manifest.screenshots.filter(s => s.status === 'failed').length,
    consoleCount: manifest.console.length,
    pageErrorCount: manifest.page_errors.length,
    predictionFlow: manifest.prediction_flow,
    prediction3DVariants: manifest.prediction_3d_variants,
    performance: manifest.performance.prediction,
  }
  console.log(JSON.stringify(summary, null, 2))

  if (
    AUDIT_ROLE !== 'public'
    && (
      summary.failedCount > 0
      || summary.consoleCount > 0
      || summary.pageErrorCount > 0
      || !manifest.prediction_flow?.ok
      || manifest.prediction_3d_variants.some(variant => !variant.ok)
      || !manifest.performance.prediction?.loading_feedback_pass
      || !manifest.performance.prediction?.api_response_pass
      || !manifest.performance.prediction?.backend_response_pass
      || !manifest.performance.prediction?.cold_flow_pass
    )
  ) {
    process.exitCode = 1
  }
}

main().catch(error => {
  console.error(sanitizeError(error))
  process.exit(1)
})

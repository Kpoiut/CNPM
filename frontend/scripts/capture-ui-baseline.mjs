import { chromium } from 'playwright-core'
import fs from 'node:fs/promises'
import path from 'node:path'
import { APP_ROUTES } from '../src/app/routes/routeRegistry.js'

const BASE_URL = process.env.UI_BASE_URL || 'http://127.0.0.1:5173'
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000'
const EDGE_PATH = process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const AUDIT_ROLE = process.env.UI_AUDIT_ROLE || 'admin'
const LOCAL_AUDIT_ACCOUNTS = {
  user: { username: 'codex_ui_audit_user', password: 'CodexAuditUser!2026' },
  admin: { username: 'codex_ui_audit_admin', password: 'CodexAuditAdmin!2026' },
}
const AUDIT_USERNAME = process.env.UI_AUDIT_USERNAME || LOCAL_AUDIT_ACCOUNTS[AUDIT_ROLE]?.username
const AUDIT_PASSWORD = process.env.UI_AUDIT_PASSWORD || LOCAL_AUDIT_ACCOUNTS[AUDIT_ROLE]?.password

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
  const group = page.locator('.form-group', { hasText: groupText }).first()
  const input = group.locator('input').first()
  await input.waitFor({ state: 'visible', timeout: 4_000 })
  await input.fill(String(value))
}

async function tryRunPrediction(page, manifest) {
  const result = { ok: false, notes: [] }
  try {
    await clickIfVisible(page, 'Đất nền', 2500)
    await selectFirstDistrict(page)
    await fillFirstInputInGroup(page, /Diện tích/i, 120)
    await fillFirstInputInGroup(page, /Mặt tiền/i, 6).catch(() => {})
    await fillFirstInputInGroup(page, /Chiều sâu tối thiểu/i, 18).catch(() => {})
    await fillFirstInputInGroup(page, /Chiều sâu tối đa/i, 20).catch(() => {})

    const submitButton = page.locator('form button[type="submit"]').first()
    await submitButton.evaluate(button => button.click())
    await page.waitForLoadState('networkidle', { timeout: 20_000 }).catch(() => {})
    await page.waitForTimeout(1800)

    const unlocked = await page.getByRole('button', { name: /Kết quả/i }).first()
      .evaluate(node => !node.disabled)
      .catch(() => false)
    result.ok = unlocked
    result.notes.push(unlocked ? 'Prediction result tabs unlocked.' : 'Prediction submit ran but result tabs stayed locked.')
  } catch (error) {
    result.notes.push(`Prediction automation skipped: ${sanitizeError(error)}`)
  }
  manifest.prediction_flow = result
  await writeManifest(manifest)
  return result
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
  }

  const tokenData = AUDIT_ROLE === 'public' ? null : await login()
  const browser = await chromium.launch({ executablePath: EDGE_PATH, headless: true })
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    deviceScaleFactor: 1,
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
      at: new Date().toISOString(),
    })
  })

  for (const route of activeRoutes) {
    try {
      const response = await gotoAndSettle(page, route.path)
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

  console.log(JSON.stringify({
    outDir,
    screenshotCount: manifest.screenshots.filter(s => s.status === 'captured').length,
    failedCount: manifest.screenshots.filter(s => s.status === 'failed').length,
    consoleCount: manifest.console.length,
    pageErrorCount: manifest.page_errors.length,
    predictionFlow: manifest.prediction_flow,
  }, null, 2))
}

main().catch(error => {
  console.error(sanitizeError(error))
  process.exit(1)
})

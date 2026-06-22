import { mkdir, readdir, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'

const root = process.cwd()
const assetsDir = path.join(root, 'dist', 'assets')

const budgets = [
  {
    prefix: 'index-',
    limit: 480 * 1024,
    label: 'app shell initial JavaScript',
  },
  {
    prefix: 'Prediction-',
    limit: 170 * 1024,
    label: 'trang du doan',
  },
  {
    prefix: 'Login-',
    limit: 40 * 1024,
    label: 'trang dang nhap',
  },
  {
    prefix: 'PropertyVisualizer-',
    limit: 40 * 1024,
    label: 'visualizer shell',
  },
  {
    prefix: 'PropertyModel3D-',
    limit: 40 * 1024,
    label: '3D dynamic entry',
  },
  {
    prefix: 'react-three-',
    limit: 220 * 1024,
    label: 'react-three lazy vendor',
  },
  {
    prefix: 'three-core-',
    limit: 700 * 1024,
    label: 'three core lazy vendor',
  },
]

function formatKb(bytes) {
  return `${(bytes / 1024).toFixed(1)} KB`
}

function readReportPath() {
  const arg = process.argv.find(item => item.startsWith('--report='))
  return arg ? path.resolve(root, arg.slice('--report='.length)) : null
}

const files = await readdir(assetsDir)
const jsFiles = files.filter(file => file.endsWith('.js'))
const measurements = []
const errors = []

for (const budget of budgets) {
  const matches = jsFiles.filter(file => file.startsWith(budget.prefix))
  if (matches.length === 0) {
    errors.push(`Khong tim thay bundle ${budget.prefix} cho ${budget.label}`)
    continue
  }

  for (const file of matches) {
    const fullPath = path.join(assetsDir, file)
    const { size } = await stat(fullPath)
    const item = {
      file,
      label: budget.label,
      size_bytes: size,
      limit_bytes: budget.limit,
      pass: size <= budget.limit,
    }
    measurements.push(item)
    if (!item.pass) {
      errors.push(
        `${budget.label}: ${file} = ${formatKb(size)} vuot budget ${formatKb(budget.limit)}`,
      )
    }
  }
}

const report = {
  valid: errors.length === 0,
  errors,
  budgets: measurements,
  note: 'three-core duoc phep lon hon 500 KB vi chi nam sau dynamic import cua tab 3D; gate nay khoa app shell, cac trang trong yeu va lazy vendor cua 3D.',
}

const reportPath = readReportPath()
if (reportPath) {
  await mkdir(path.dirname(reportPath), { recursive: true })
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
}

if (errors.length) {
  console.error('Bundle budget failed:')
  for (const error of errors) console.error(`- ${error}`)
  process.exit(1)
}

for (const item of measurements) {
  console.log(`${item.label}: ${item.file} ${formatKb(item.size_bytes)} / ${formatKb(item.limit_bytes)}`)
}

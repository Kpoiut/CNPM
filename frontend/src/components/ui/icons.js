/**
 * Icon system — Phosphor "duotone" (vector hai tông màu, sinh động) qua MỘT cổng
 * duy nhất `icon(key, size, className, color)`. Đổi bộ icon ở đây là toàn app đổi
 * theo, không cần sửa call-site. Vector → nét mọi độ phân giải, tự đổi màu theme.
 */
import React from 'react'
import {
  House, SquaresFour, ChartLineUp, MapPin, GlobeHemisphereEast, Broadcast, Sun, Moon,
  Buildings, Tree, Bank, Crown, Storefront,
  CheckCircle, Check, Info, Warning, XCircle, X, MagnifyingGlass, User, Users,
  CaretDown, CaretUp, CaretLeft, CaretRight, Plus, Minus, ArrowRight, ArrowLeft,
  Database, FileMagnifyingGlass, Table, ChartPie, ListBullets, Package, Tray,
  Microphone, MicrophoneSlash, ChatCircle, Robot, Sparkle,
  Scales, Shield, ShieldCheck, ShieldWarning, Lock, LockOpen, LinkSimple, FileText,
  Clock, Calendar, CalendarCheck, Bell, BellSlash, Gear, Sliders, SlidersHorizontal,
  Factory, HardHat, Hammer, Wrench, Key, Eye, EyeSlash,
  ArrowsDownUp, ArrowUp, ArrowDown, ArrowsLeftRight, ArrowsClockwise, CircleNotch,
  Copy, Clipboard, BookOpen, Flag, Tag, Star, Hash, Terminal, Code, Cloud, HardDrives,
  Ruler, Cube, BuildingOffice, StackSimple, NavigationArrow, Compass, MapPinArea, Park,
  GraduationCap, FirstAid, ShoppingCart, Bus, Waves, Camera, Image, Footprints, Church,
  Trash, Pause, Play, Mouse, Truck, Warehouse, Circle, Target, Pulse, Flask,
} from '@phosphor-icons/react'

// Map khóa domain → component Phosphor
export const ICON = {
  // Navigation & UI
  home: House, house: House, dashboard: SquaresFour,
  chart: ChartLineUp, trendingUp: ChartLineUp, barChart3: ChartLineUp, zap: Sparkle,
  map: MapPin, globe: GlobeHemisphereEast, radio: Broadcast, sun: Sun, moon: Moon,

  // Property types
  apartment: Buildings, land: Tree, tree: Tree, townhouse: Bank, villa: Crown, shophouse: Storefront,

  // Actions & status
  check: CheckCircle, checkCircle: CheckCircle, checkAlt: Check,
  info: Info, warning: Warning, alertTriangle: Warning, error: XCircle, close: X,
  search: MagnifyingGlass, user: User, users: Users,
  chevronDown: CaretDown, chevronUp: CaretUp, chevronLeft: CaretLeft, chevronRight: CaretRight,
  plus: Plus, minus: Minus, arrowRight: ArrowRight, arrowLeft: ArrowLeft,

  // ML & research
  ml: Pulse, experiment: Pulse, activity: Pulse, flask: Flask, target: Target,

  // Data
  database: Database, fileSearch: FileMagnifyingGlass, table: Table, pieChart: ChartPie,
  list: ListBullets, package: Package, packageSearch: Package, inbox: Tray,

  // Voice / Nova
  mic: Microphone, micOff: MicrophoneSlash, chat: ChatCircle, bot: Robot, sparkles: Sparkle,

  // Status / legal
  scale: Scales, shield: Shield, shieldCheck: ShieldCheck, shieldAlert: ShieldWarning,
  shieldOff: ShieldWarning, lock: Lock, unlock: LockOpen, link: LinkSimple, fileText: FileText,

  // Time
  clock: Clock, calendar: Calendar, calendarCheck: CalendarCheck, bell: Bell, bellOff: BellSlash,

  // Settings / layout
  settings: Gear, sliders: Sliders, slidersAlt: SlidersHorizontal,
  layoutGrid: SquaresFour, layoutList: ListBullets, layoutTemplate: SquaresFour,

  // Misc tools
  factory: Factory, hardHat: HardHat, hammer: Hammer, wrench: Wrench,
  key: Key, keyRound: Key, eye: Eye, eyeOff: EyeSlash, eyeHidden: EyeSlash,
  arrowUpDown: ArrowsDownUp, arrowUp: ArrowUp, arrowDown: ArrowDown, arrowLeftRight: ArrowsLeftRight,
  refreshCw: ArrowsClockwise, refreshCcw: ArrowsClockwise, loader: CircleNotch, loaderAlt: CircleNotch,
  copy: Copy, clipboard: Clipboard, clipboardCheck: Clipboard, book: BookOpen, bookMarked: BookOpen,
  flag: Flag, flagOff: Flag, tag: Tag, tags: Tag, star: Star, starHalf: Star, starOff: Star,
  hash: Hash, terminal: Terminal, terminalSquare: Terminal, code: Code,
  cloud: Cloud, cloudOff: Cloud, cloudUp: Cloud, cloudDown: Cloud, server: HardDrives,
  satellite: GlobeHemisphereEast,

  // Map / visualization / amenities
  ruler: Ruler, cube: Cube, building: BuildingOffice, layers: StackSimple,
  navigation: NavigationArrow, compass: Compass, pin: MapPin, mapPinned: MapPinArea,
  park: Park, school: GraduationCap, hospital: FirstAid, market: ShoppingCart, bus: Bus,
  water: Waves, camera: Camera, image: Image, street: Footprints, footprints: Footprints,
  church: Church, cemetery: Church, worship: Church,
  rotateCw: ArrowsClockwise, rotateCcw: ArrowsClockwise, trash: Trash, pause: Pause, play: Play,
  mouse: Mouse, truck: Truck, warehouse: Warehouse,
}

// Màu (duotone tô theo hue domain → bộ icon nhiều màu, sinh động)
const ICON_COLORS = {
  home: '#0ea5e9', house: '#0ea5e9', dashboard: '#8b5cf6',
  chart: '#22c55e', trendingUp: '#22c55e', barChart3: '#38bdf8', zap: '#f59e0b',
  map: '#f59e0b', globe: '#38bdf8', radio: '#22d3ee', satellite: '#22d3ee',
  sun: '#f59e0b', moon: '#a78bfa',
  apartment: '#8b5cf6', land: '#22c55e', tree: '#22c55e', townhouse: '#f59e0b', villa: '#ec4899', shophouse: '#06b6d4',
  check: '#10b981', checkCircle: '#10b981', info: '#38bdf8', warning: '#f59e0b', alertTriangle: '#f59e0b', error: '#ef4444',
  search: '#38bdf8', user: '#38bdf8', users: '#60a5fa',
  flask: '#a78bfa', experiment: '#a78bfa', ml: '#a78bfa', target: '#f59e0b',
  database: '#38bdf8', table: '#60a5fa', pieChart: '#f472b6', list: '#a78bfa', inbox: '#94a3b8',
  chat: '#a78bfa', bot: '#22d3ee', sparkles: '#f472b6',
  scale: '#22d3ee', shield: '#22d3ee', shieldCheck: '#10b981', shieldAlert: '#f59e0b', lock: '#f87171', unlock: '#10b981',
  link: '#22d3ee', fileText: '#60a5fa',
  clock: '#38bdf8', calendar: '#60a5fa', bell: '#fbbf24', settings: '#94a3b8', sliders: '#94a3b8',
  factory: '#94a3b8', hardHat: '#f59e0b', hammer: '#f59e0b', wrench: '#f59e0b',
  key: '#fbbf24', eye: '#60a5fa',
  ruler: '#38bdf8', cube: '#8b5cf6', building: '#60a5fa', layers: '#0ea5e9', navigation: '#0ea5e9', compass: '#f59e0b',
  pin: '#0ea5e9', mapPinned: '#0ea5e9',
  park: '#22c55e', school: '#3b82f6', hospital: '#ef4444', market: '#f59e0b', bus: '#06b6d4',
  water: '#0ea5e9', camera: '#8b5cf6', image: '#8b5cf6', street: '#22d3ee', church: '#94a3b8',
  cemetery: '#94a3b8', worship: '#a78bfa', trash: '#ef4444',
  satellite_: '#22d3ee', star: '#fbbf24', flag: '#f59e0b', tag: '#22c55e',
}

const BRAND_ICON_KEYS = new Set([
  'home', 'house', 'dashboard', 'chart', 'trendingUp', 'barChart3',
  'map', 'globe', 'radio', 'apartment', 'land', 'tree', 'townhouse',
  'villa', 'shophouse', 'database', 'table', 'ml', 'experiment',
  'flask', 'target', 'shield', 'shieldCheck', 'lock', 'users', 'user',
])

function brandPathFor(key) {
  if (['home', 'house', 'apartment', 'townhouse', 'villa', 'shophouse'].includes(key)) {
    return [
      ['path', { d: 'M5 11.3 12 5l7 6.3' }],
      ['path', { d: 'M7.5 10.2V19h9v-8.8' }],
      ['path', { d: 'M10.1 19v-5.2h3.8V19' }],
      ['path', { d: 'M15.6 7.4V5.5h2.2v3.9', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (['map', 'globe'].includes(key)) {
    return [
      ['path', { d: 'M8 5.5 4.6 7v11.5L8 17l4 1.5 4-1.5 3.4 1.5V7L16 5.5l-4 1.5z' }],
      ['path', { d: 'M8 5.5V17M12 7v11.5M16 5.5V17' }],
      ['circle', { cx: '12', cy: '11.5', r: '2.1', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (['chart', 'trendingUp', 'barChart3', 'target'].includes(key)) {
    return [
      ['path', { d: 'M5 18.5h14' }],
      ['path', { d: 'M6.5 15.5 10 12l2.7 2.2 4.8-6' }],
      ['path', { d: 'M15.2 8.1h2.3v2.3' }],
      ['path', { d: 'M7.2 18.5v-4.2M12 18.5v-6.1M16.8 18.5v-8.9', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (['database', 'table'].includes(key)) {
    return [
      ['ellipse', { cx: '12', cy: '6.7', rx: '6.4', ry: '2.7' }],
      ['path', { d: 'M5.6 6.7v10.6c0 1.5 2.9 2.7 6.4 2.7s6.4-1.2 6.4-2.7V6.7' }],
      ['path', { d: 'M5.6 12c0 1.5 2.9 2.7 6.4 2.7s6.4-1.2 6.4-2.7' }],
      ['path', { d: 'M8.7 10.1h6.6', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (['ml', 'experiment', 'flask'].includes(key)) {
    return [
      ['path', { d: 'M10 5.2h4M11 5.2v4.2l-4.5 7.8c-.8 1.4.2 3.1 1.8 3.1h7.4c1.6 0 2.6-1.7 1.8-3.1L13 9.4V5.2' }],
      ['path', { d: 'M8.7 15.7h6.6', className: 'avm-brand-icon__spark' }],
      ['circle', { cx: '15.7', cy: '8.4', r: '1', className: 'avm-brand-icon__spark' }],
      ['circle', { cx: '8.4', cy: '9.7', r: '.8', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (['shield', 'shieldCheck', 'lock'].includes(key)) {
    return [
      ['path', { d: 'M12 4.7 18.1 7v4.5c0 4-2.4 7.3-6.1 8.8-3.7-1.5-6.1-4.8-6.1-8.8V7z' }],
      ['path', { d: 'm9.2 12.4 1.8 1.8 3.9-4.3', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (['users', 'user'].includes(key)) {
    return [
      ['circle', { cx: '10', cy: '8.2', r: '2.7' }],
      ['path', { d: 'M5.5 18.8c.5-3.1 2.1-4.7 4.5-4.7s4 1.6 4.5 4.7' }],
      ['path', { d: 'M15.1 9.3c1.5.2 2.6 1.3 2.6 2.8 0 1.4-1 2.5-2.3 2.8', className: 'avm-brand-icon__spark' }],
    ]
  }
  if (key === 'radio') {
    return [
      ['circle', { cx: '12', cy: '12', r: '2.2' }],
      ['path', { d: 'M8.3 8.4a5.3 5.3 0 0 0 0 7.3M15.7 8.4a5.3 5.3 0 0 1 0 7.3' }],
      ['path', { d: 'M5.5 5.7a9 9 0 0 0 0 12.6M18.5 5.7a9 9 0 0 1 0 12.6', className: 'avm-brand-icon__spark' }],
    ]
  }
  return null
}

function CodexBrandIcon({ iconKey, size, className, color }) {
  const paths = brandPathFor(iconKey)
  if (!paths) return null
  const accent = ICON_COLORS[iconKey] || color || 'currentColor'
  const gradientId = `avmIconGradient-${iconKey}`
  return React.createElement(
    'svg',
    {
      viewBox: '0 0 24 24',
      width: size,
      height: size,
      className,
      'aria-hidden': 'true',
      focusable: 'false',
      style: { display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, color: accent },
    },
    React.createElement(
      'defs',
      null,
      React.createElement(
        'linearGradient',
        { id: gradientId, x1: '3', y1: '3', x2: '21', y2: '21' },
        React.createElement('stop', { stopColor: accent }),
        React.createElement('stop', { offset: '1', stopColor: '#34d399' }),
      ),
    ),
    React.createElement(
      'g',
      {
        fill: 'none',
        stroke: `url(#${gradientId})`,
        strokeWidth: '1.75',
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
      },
      paths.map(([tag, props], index) => React.createElement(tag, { key: index, ...props })),
    ),
  )
}

/**
 * Trả về 1 React element icon (Phosphor duotone).
 * Dùng: {icon('chart')} hoặc icon('chart', 20)
 */
export function icon(key, size = 16, className = '', color = 'currentColor') {
  const Comp = ICON[key] || Circle
  const resolvedColor = color === 'currentColor' ? (ICON_COLORS[key] || 'currentColor') : color
  const spin = key === 'loader' || key === 'loaderAlt'
  const classes = ['avm-icon', spin ? 'avm-icon-spin' : '', className].filter(Boolean).join(' ')
  // To hơn ~18% đồng loạt cho dễ nhìn, vẫn căn theo call-site
  const finalSize = Math.round(size * 1.18)
  if (BRAND_ICON_KEYS.has(key)) {
    return React.createElement(CodexBrandIcon, {
      iconKey: key,
      size: finalSize,
      className: ['avm-icon--codex', classes].filter(Boolean).join(' '),
      color: resolvedColor,
    })
  }
  return React.createElement(Comp, {
    size: finalSize,
    weight: 'duotone',
    color: resolvedColor,
    className: classes,
    style: { display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 },
  })
}

export default icon

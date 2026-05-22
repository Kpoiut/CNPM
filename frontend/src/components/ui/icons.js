/**
 * Lucide icon mapping for Real Estate AVM domain.
 * Replaces emoji shortcuts with proper SVG icons from lucide-react.
 */
import React from 'react'
import {
  Home, TrendingUp, BarChart3, Map, Globe, Radio, Link,
  CheckCircle, Info, AlertTriangle, XCircle, X,
  Zap, FlaskConical, Wrench, Layers, Search,
  Building, TreePine, Building2, Castle, Landmark,
  FileText, Lock, Unlock, User, Users, UserCheck, LogOut, Sun, Moon,
  ChevronDown, ChevronUp, ChevronLeft, ChevronRight,
  Plus, Minus, ArrowRight, ArrowLeft, Check, Filter,
  Database, FileSearch, Table2, PieChart, List, Inbox,
  Mic, MicOff, Send, MessageSquare, Bot, Sparkles,
  Scale, Shield, ShieldCheck, ShieldAlert, ShieldOff, ExternalLink,
  Activity, Target, Circle, MapPin, Navigation,
  Package, Truck, Wifi, WifiOff, Warehouse,
  Clock, Calendar, CalendarCheck, Bell, BellOff,
  Settings, Sliders, SlidersHorizontal,
  LayoutDashboard, LayoutGrid, LayoutList, LayoutTemplate,
  BuildingIcon, Factory, HardHat, Hammer, Wrench as WrenchIcon,
  Key, KeyRound, Eye, EyeOff, EyeOff as Hidden,
  ArrowUpDown, ArrowUp, ArrowDown, ArrowLeftRight,
  GripVertical, GripHorizontal,
  RefreshCw, RefreshCcw,
  Loader2, Loader, LoaderPinwheel,
  Copy, Scissors, Clipboard, ClipboardCheck,
  BookOpen, BookMarked, Book,
  Flag, FlagOff,
  Tag, Tags, TagIcon,
  Star, StarHalf, StarOff,
  Hash, HashIcon,
  Box, Package2, PackageSearch,
  Terminal, Code2, Code,
  TerminalSquare, Server,
  Cloud, CloudOff, CloudUpload, CloudDownload,
  Wifi as WifiIcon,
  Satellite,
} from 'lucide-react'

// Domain-specific icon mappings (emoji → lucide)
export const ICON = {
  // Navigation & UI
  home: Home,
  dashboard: LayoutDashboard,
  chart: TrendingUp,
  trendingUp: TrendingUp,
  barChart3: BarChart3,
  map: MapPin,
  globe: Globe,
  radio: Radio,
  sun: Sun,
  moon: Moon,

  // Property types
  house: Home,
  apartment: Building,
  land: TreePine,
  tree: TreePine,
  townhouse: Landmark,
  villa: Castle,
  shophouse: Warehouse,

  // Actions & status
  check: CheckCircle,
  checkCircle: CheckCircle,
  checkAlt: Check,
  info: Info,
  warning: AlertTriangle,
  alertTriangle: AlertTriangle,
  error: XCircle,
  close: X,
  search: Search,
  user: User,
  users: Users,
  chevronDown: ChevronDown,
  chevronUp: ChevronUp,
  chevronLeft: ChevronLeft,
  chevronRight: ChevronRight,

  // ML & research
  ml: Activity,
  flask: FlaskConical,
  experiment: Activity,
  target: Target,

  // Data
  database: Database,
  fileSearch: FileSearch,
  table: Table2,
  pieChart: PieChart,
  list: List,
  package: Package,
  packageSearch: PackageSearch,
  inbox: Inbox,

  // Voice / Nova
  mic: Mic,
  micOff: MicOff,
  chat: MessageSquare,
  bot: Bot,
  sparkles: Sparkles,

  // Status
  scale: Scale,
  shield: Shield,
  shieldCheck: ShieldCheck,
  shieldAlert: ShieldAlert,
  shieldOff: ShieldOff,
  lock: Lock,
  unlock: Unlock,
  link: Link,
  fileText: FileText,

  // Time & calendar
  clock: Clock,
  calendar: Calendar,
  calendarCheck: CalendarCheck,
  bell: Bell,
  bellOff: BellOff,

  // Settings
  settings: Settings,
  sliders: Sliders,
  slidersAlt: SlidersHorizontal,

  // Layout
  layoutGrid: LayoutGrid,
  layoutList: LayoutList,
  layoutTemplate: LayoutTemplate,

  // Misc
  factory: Factory,
  hardHat: HardHat,
  hammer: Hammer,
  wrench: WrenchIcon,
  key: Key,
  keyRound: KeyRound,
  eye: Eye,
  eyeOff: EyeOff,
  eyeHidden: Hidden,
  arrowUpDown: ArrowUpDown,
  arrowUp: ArrowUp,
  arrowDown: ArrowDown,
  arrowLeftRight: ArrowLeftRight,
  refreshCw: RefreshCw,
  refreshCcw: RefreshCcw,
  loader: Loader2,
  loaderAlt: Loader,
  copy: Copy,
  clipboard: Clipboard,
  clipboardCheck: ClipboardCheck,
  book: BookOpen,
  bookMarked: BookMarked,
  flag: Flag,
  flagOff: FlagOff,
  tag: Tag,
  tags: Tags,
  star: Star,
  starHalf: StarHalf,
  starOff: StarOff,
  hash: Hash,
  terminal: Terminal,
  terminalSquare: TerminalSquare,
  code: Code2,
  cloud: Cloud,
  cloudOff: CloudOff,
  cloudUp: CloudUpload,
  cloudDown: CloudDownload,
  server: Server,
  satellite: Satellite,
}

const ICON_COLORS = {
  // Navigation
  home: '#60a5fa',
  dashboard: '#a78bfa',
  chart: '#22c55e',
  trendingUp: '#22c55e',
  barChart3: '#38bdf8',
  map: '#f59e0b',
  globe: '#38bdf8',
  radio: '#22d3ee',
  list: '#a78bfa',

  // Property types
  house: '#60a5fa',
  apartment: '#8b5cf6',
  land: '#22c55e',
  tree: '#22c55e',
  townhouse: '#f59e0b',
  villa: '#ec4899',
  shophouse: '#06b6d4',

  // Status and data
  check: '#10b981',
  checkCircle: '#10b981',
  info: '#38bdf8',
  warning: '#f59e0b',
  alertTriangle: '#f59e0b',
  error: '#ef4444',
  database: '#38bdf8',
  table: '#60a5fa',
  shield: '#22d3ee',
  shieldCheck: '#10b981',
  shieldAlert: '#f59e0b',
  lock: '#f87171',
  unlock: '#10b981',
  user: '#38bdf8',
  users: '#60a5fa',
  chat: '#a78bfa',
  bot: '#22d3ee',
  flask: '#a78bfa',
  target: '#f59e0b',
  sparkles: '#f472b6',
  clipboard: '#60a5fa',
  clipboardCheck: '#10b981',
  fileSearch: '#38bdf8',
  search: '#38bdf8',
  link: '#22d3ee',
  satellite: '#22d3ee',
  wrench: '#f59e0b',
  settings: '#94a3b8',
  bell: '#fbbf24',
  moon: '#a78bfa',
  sun: '#f59e0b',
}

function FilledHouseIcon({ size, className }) {
  return React.createElement(
    'svg',
    {
      width: size,
      height: size,
      viewBox: '0 0 24 24',
      className,
      'aria-hidden': 'true',
      focusable: 'false',
      style: { display: 'inline-block', verticalAlign: 'middle' },
    },
    React.createElement('path', {
      d: 'M3.25 11.15 12 3.7l8.75 7.45c.62.53.25 1.55-.56 1.55h-1.14v6.1a2.2 2.2 0 0 1-2.2 2.2H7.15a2.2 2.2 0 0 1-2.2-2.2v-6.1H3.81c-.81 0-1.18-1.02-.56-1.55Z',
      fill: '#22d3ee',
    }),
    React.createElement('path', {
      d: 'M6.9 12.08 12 7.72l5.1 4.36v6.34c0 .42-.34.76-.76.76H7.66a.76.76 0 0 1-.76-.76v-6.34Z',
      fill: '#34d399',
    }),
    React.createElement('path', {
      d: 'M9.4 14.25c0-.48.39-.87.87-.87h3.46c.48 0 .87.39.87.87v4.93H9.4v-4.93Z',
      fill: '#ecfeff',
      opacity: '0.92',
    }),
    React.createElement('path', {
      d: 'M10.4 14.55h1.1v4.63h-1.1v-4.63Zm2.1 0h1.1v4.63h-1.1v-4.63Z',
      fill: '#0891b2',
      opacity: '0.65',
    })
  )
}

/**
 * Get a pre-rendered Lucide icon element.
 * Usage: <span>{icon('chart')}</span> or icon('chart', 20)
 * Returns a React element, NOT a component class.
 */
export function icon(key, size = 16, className = '', color = 'currentColor') {
  if (key === 'home' || key === 'house') {
    return React.createElement(FilledHouseIcon, {
      size,
      className: ['avm-icon', 'avm-icon-filled', className].filter(Boolean).join(' '),
    })
  }
  const Comp = ICON[key] || Activity
  const resolvedColor = color === 'currentColor' ? (ICON_COLORS[key] || color) : color
  const classes = ['avm-icon', className].filter(Boolean).join(' ')
  return React.createElement(Comp, {
    size,
    className: classes,
    strokeWidth: 2.35,
    style: { color: resolvedColor, '--avm-icon-color': resolvedColor },
  })
}

export default icon

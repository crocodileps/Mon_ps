'use client'

import { motion } from 'framer-motion'
import { BarChart3, LayoutDashboard, Settings, Target, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { Badge } from '@/components/ui/badge'
import { useUiStore } from '@/lib/stores/ui-store'
import { cn } from '@/lib/utils'

interface SidebarProps {
  opportunitiesCount?: number
  activeBetsCount?: number
}

export const navItems = [
  {
    href: '/',
    icon: LayoutDashboard,
    label: 'Dashboard',
  },
  {
    href: '/opportunities',
    icon: Target,
    label: 'Opportunités',
    badge: 'opportunities',
  },
  {
    href: '/bets',
    icon: TrendingUp,
    label: 'Paris',
    badge: 'bets',
  },
  {
    href: '/analytics',
    icon: BarChart3,
    label: 'Analytics',
  },
  {
    href: '/settings',
    icon: Settings,
    label: 'Paramètres',
  },
] as const

const containerVariants = {
  open: {
    width: 260,
    transition: { type: 'spring', stiffness: 120, damping: 14 },
  },
  collapsed: {
    width: 88,
    transition: { type: 'spring', stiffness: 120, damping: 14 },
  },
}

export function Sidebar({ opportunitiesCount = 0, activeBetsCount = 0 }: SidebarProps) {
  const pathname = usePathname()
  const { isSidebarCollapsed } = useUiStore()

  const getBadgeValue = (type?: string) => {
    switch (type) {
      case 'opportunities':
        return opportunitiesCount
      case 'bets':
        return activeBetsCount
      default:
        return undefined
    }
  }

  return (
    <motion.aside
      animate={isSidebarCollapsed ? 'collapsed' : 'open'}
      variants={containerVariants}
      className={cn(
        'hidden lg:flex h-[calc(100vh-2rem)] sticky top-4 flex-col rounded-3xl border border-border/60 bg-surface/80 p-4 shadow-inner-glow backdrop-blur-xl transition-all duration-300',
      )}
    >
      <div className="mb-8 space-y-1 px-1">
        <div className="text-xs uppercase tracking-[0.35em] text-text-muted">Mon_PS</div>
        <span className="bg-gradient-to-r from-primary to-success bg-clip-text text-2xl font-bold text-transparent">
          Quant Lab
        </span>
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          const Icon = item.icon
          const badgeValue = getBadgeValue(item.badge)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group relative flex items-center gap-3 rounded-2xl px-4 py-3 transition-colors duration-200',
                isActive
                  ? 'bg-gradient-to-r from-primary/20 via-primary/10 to-transparent text-text-primary shadow-glow'
                  : 'text-text-secondary hover:bg-surface-hover/80 hover:text-text-primary',
              )}
            >
              <span
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-xl bg-surface-hover/70 transition-colors duration-200',
                  isActive && 'bg-primary/20 text-primary-foreground',
                )}
              >
                <Icon className="h-5 w-5" />
              </span>
              <span className="text-sm font-semibold tracking-wide">{item.label}</span>
              {typeof badgeValue === 'number' && badgeValue > 0 ? (
                <Badge variant="secondary" className="ml-auto bg-primary/20 text-primary">
                  {badgeValue}
                </Badge>
              ) : null}
            </Link>
          )
        })}
      </nav>
      <div className="rounded-2xl border border-border/70 bg-surface-hover/60 p-4">
        <p className="text-xs uppercase tracking-wide text-text-muted">Stratégie hybride</p>
        <p className="mt-2 text-sm text-text-secondary">
          10 paris Tabac + 10 paris Ligne analysés en temps réel.
        </p>
      </div>
    </motion.aside>
  )
}


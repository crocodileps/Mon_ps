'use client'

import { AnimatePresence, motion } from 'framer-motion'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/lib/stores/ui-store'
import { cn } from '@/lib/utils'

import { navItems } from './sidebar'

interface MobileSidebarProps {
  opportunitiesCount?: number
  activeBetsCount?: number
}

const panelVariants = {
  initial: { x: '-100%' },
  animate: { x: 0, transition: { type: 'spring', stiffness: 220, damping: 28 } },
  exit: { x: '-100%', transition: { duration: 0.2 } },
}

export function MobileSidebar({
  opportunitiesCount = 0,
  activeBetsCount = 0,
}: MobileSidebarProps) {
  const pathname = usePathname()
  const isOpen = useUiStore((state) => state.isMobileNavOpen)
  const closeMobileNav = useUiStore((state) => state.closeMobileNav)

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
    <AnimatePresence>
      {isOpen ? (
        <>
          <motion.div
            key="overlay"
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeMobileNav}
          />
          <motion.aside
            key="panel"
            className="fixed left-0 top-0 z-50 flex h-full w-80 flex-col gap-6 border-r border-border/50 bg-background/95 p-6 backdrop-blur-xl lg:hidden"
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-text-muted">Mon_PS</p>
                <p className="text-lg font-semibold text-text-primary">Quant Lab</p>
              </div>
              <Button
                variant="ghost"
                className="rounded-2xl border border-border/60 bg-surface/70"
                size="sm"
                onClick={closeMobileNav}
              >
                Fermer
              </Button>
            </div>
            <nav className="flex flex-col gap-3">
              {navItems.map((item) => {
                const isActive = pathname === item.href
                const badgeValue = getBadgeValue(item.badge)
                const Icon = item.icon

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 rounded-2xl px-4 py-3 transition-colors duration-200',
                      isActive
                        ? 'bg-gradient-to-r from-primary/20 via-primary/10 to-transparent text-text-primary'
                        : 'text-text-secondary hover:bg-surface-hover/80 hover:text-text-primary',
                    )}
                    onClick={closeMobileNav}
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface-hover/70">
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
        </>
      ) : null}
    </AnimatePresence>
  )
}


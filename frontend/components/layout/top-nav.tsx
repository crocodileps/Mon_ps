'use client'

import { motion } from 'framer-motion'
import { Bell, Menu, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useUiStore } from '@/lib/stores/ui-store'

export function TopNav() {
  const toggleMobileNav = useUiStore((state) => state.toggleMobileNav)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border/50 bg-background/70 px-4 backdrop-blur-xl lg:hidden">
      <div className="flex items-center gap-3">
        <Button
          size="icon"
          variant="ghost"
          className="rounded-2xl border border-border/60 bg-surface/80"
          onClick={toggleMobileNav}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-text-muted">Mon_PS</p>
          <p className="text-base font-semibold text-text-primary">Quant Lab</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
          <Button
            size="icon"
            variant="ghost"
            className="rounded-2xl border border-border/60 bg-surface/70"
          >
            <Search className="h-4 w-4" />
          </Button>
        </motion.div>
        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
          <Button
            size="icon"
            variant="ghost"
            className="rounded-2xl border border-border/60 bg-surface/70"
          >
            <Bell className="h-4 w-4" />
          </Button>
        </motion.div>
      </div>
    </header>
  )
}


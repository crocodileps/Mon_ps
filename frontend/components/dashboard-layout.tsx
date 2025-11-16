'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, TrendingUp, Activity, Zap, Menu, X, Settings, LayoutDashboard, Lightbulb, FolderKanban, Layers } from 'lucide-react'
import { PortfolioModal } from './portfolio-modal'

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [portfolioModalOpen, setPortfolioModalOpen] = useState(false)
  const pathname = usePathname()

  const navItems = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/opportunities', label: 'Opportunités', icon: TrendingUp },
    { href: '/classification', label: 'Classification', icon: FolderKanban },
    { href: '/agents', label: 'Agents', icon: Zap },
    { href: '/compare-agents', label: 'Comparer les Agents', icon: Activity },
    { href: '/strategies', label: 'Stratégies', icon: Lightbulb },
    { href: '/systems', label: 'Systèmes & Combos', icon: Layers },
    { href: '/stats', label: 'Analyse', icon: BarChart3 },
  ]

  const settingsItems = [
    { href: '/settings', label: 'Paramètres', icon: Settings },
  ]

  return (
    <div className="flex h-screen bg-background">
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        w-64
        fixed inset-y-0 left-0 z-50 lg:z-30
        transition-transform duration-300 bg-card border-r border-border/50 overflow-hidden flex flex-col backdrop-blur-sm
      `}>
        <div className="p-6 border-b border-border/50 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary via-secondary to-accent flex items-center justify-center flex-shrink-0">
            <Zap size={20} className="text-white" />
          </div>
          <h1 className="text-lg font-bold bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent whitespace-nowrap">
            PS Trading
          </h1>
        </div>

        <nav className="flex-1 p-3 space-y-2 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20'
                    : 'text-foreground hover:bg-muted/50 hover:text-accent'
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon size={20} className="flex-shrink-0" />
                <span className="font-medium text-sm">{item.label}</span>
              </Link>
            )
          })}
        </nav>
<div className="p-3 border-t border-border/50 space-y-2">
          {settingsItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                }`}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon size={20} className="flex-shrink-0" />
                <span className="font-medium text-sm">{item.label}</span>
              </Link>
            )
          })}
        </div>

        <div className="p-4 border-t border-border/50">
          <button 
            onClick={() => {
              setPortfolioModalOpen(true)
              setSidebarOpen(false)
            }}
            className="w-full bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/30 rounded-lg p-4 hover:from-green-500/30 hover:to-emerald-600/30 transition-all cursor-pointer"
          >
            <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider text-left">Solde Total</p>
            <p className="text-2xl font-bold text-green-400 text-left">$1,280.50</p>
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-card/50 border-b border-border/50 px-4 py-3 flex items-center justify-between backdrop-blur-sm sticky top-0 z-30">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-3 bg-primary hover:bg-primary/90 rounded-lg transition-all text-white border-2 border-primary/80 hover:border-primary flex items-center gap-2 shadow-xl shadow-primary/30 font-bold"
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
            <span className="text-sm hidden sm:inline">
              {sidebarOpen ? "Fermer" : "Menu"}
            </span>
          </button>
          
          <div className="text-sm text-muted-foreground">
            Paris Sportif • Dashboard
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>

      <PortfolioModal 
        isOpen={portfolioModalOpen}
        onClose={() => setPortfolioModalOpen(false)}
      />
    </div>
  )
}


'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, TrendingUp, LineChart, Menu as MenuIcon, Users } from 'lucide-react'
import { Button } from './ui/button'

export function Navigation() {
  const pathname = usePathname()
  
  const links = [
    { href: '/opportunities', label: 'Opportunités', icon: TrendingUp },
    { href: '/manual-bets', label: 'P&L', icon: BarChart3 },
    { href: '/analytics', label: 'Analytics', icon: LineChart }
    ,{ href: '/agents-comparison', label: 'Comparaison Agents', icon: Users }
    ,{ href: '/full-gain', label: 'Full Gain 2.0', icon: TrendingUp }
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-lg">
                <MenuIcon className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Mon_PS</span>
            </Link>
            
            <div className="flex items-center gap-2">
              {links.map(link => {
                const Icon = link.icon
                const isActive = pathname === link.href
                return (
                  <Link key={link.href} href={link.href}>
                    <Button
                      variant={isActive ? 'default' : 'ghost'}
                      className={isActive ? 'bg-violet-600' : ''}
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {link.label}
                    </Button>
                  </Link>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

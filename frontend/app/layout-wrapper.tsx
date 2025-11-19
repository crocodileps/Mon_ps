'use client'

import { Navigation } from '@/components/Navigation'

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950">
      <Navigation />
      <div className="pt-24 px-6">
        {children}
      </div>
    </div>
  )
}

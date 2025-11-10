import { PropsWithChildren } from 'react'

import { MobileSidebar } from './mobile-sidebar'
import { Sidebar } from './sidebar'
import { TopNav } from './top-nav'

interface AppShellProps {
  opportunitiesCount?: number
  activeBetsCount?: number
}

export function AppShell({
  children,
  opportunitiesCount,
  activeBetsCount,
}: PropsWithChildren<AppShellProps>) {
  return (
    <div className="relative flex min-h-screen gap-6 bg-background text-text-primary">
      <MobileSidebar
        opportunitiesCount={opportunitiesCount}
        activeBetsCount={activeBetsCount}
      />
      <Sidebar
        opportunitiesCount={opportunitiesCount}
        activeBetsCount={activeBetsCount}
      />
      <div className="flex min-h-screen flex-1 flex-col">
        <TopNav />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
          <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">{children}</div>
        </main>
      </div>
    </div>
  )
}


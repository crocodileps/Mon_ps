import type { Metadata } from 'next'
import { Inter, JetBrains_Mono as JetBrainsMono } from 'next/font/google'
import { PropsWithChildren } from 'react'

import './globals.css'
import { Providers } from './providers'
import { AppShell } from '@/components/layout/app-shell'
import { cn } from '@/lib/utils'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sans',
})

const jetBrainsMono = JetBrainsMono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'Mon_PS – Dashboard sportif quantitatif',
  description:
    'Plateforme premium de paris sportifs pour suivre les opportunités, les performances et la bankroll.',
}

export default function RootLayout({ children }: PropsWithChildren) {
  return (
    <html lang="fr" className="dark" suppressHydrationWarning>
      <body
        className={cn(
          'min-h-screen bg-background text-text-primary selection:bg-primary/40',
          inter.variable,
          jetBrainsMono.variable,
        )}
      >
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  )
}

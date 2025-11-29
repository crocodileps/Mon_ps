import { DashboardLayout } from '@/components/dashboard-layout'

export default function FerrariLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

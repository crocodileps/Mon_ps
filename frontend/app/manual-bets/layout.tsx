import { DashboardLayout } from '@/components/dashboard-layout'

export default function ManualBetsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

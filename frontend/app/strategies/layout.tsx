import { DashboardLayout } from '@/components/dashboard-layout'

export default function StrategiesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

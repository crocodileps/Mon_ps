import { DashboardLayout } from '@/components/dashboard-layout'

export default function ImprovementLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

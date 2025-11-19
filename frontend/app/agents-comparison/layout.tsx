import { DashboardLayout } from '@/components/dashboard-layout'

export default function AgentsComparisonLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

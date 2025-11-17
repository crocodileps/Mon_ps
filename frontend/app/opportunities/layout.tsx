import { DashboardLayout } from '@/components/dashboard-layout'

export default function OpportunitiesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

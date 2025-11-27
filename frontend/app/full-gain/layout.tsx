import { DashboardLayout } from '@/components/dashboard-layout'

export default function FullGainLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}

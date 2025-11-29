"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Target,
  TrendingUp,
  Calculator,
  BarChart3,
  Settings,
  Users2,
  Shield,
  Lightbulb,
  LucideIcon,
  Diamond,
  Car,
} from "lucide-react";

interface SidebarProps {
  opportunitiesCount?: number;
  activeBetsCount?: number;
}

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  badge?: string;
}

export const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { id: "opportunities", label: "Opportunités", icon: Target, href: "/opportunities", badge: "opportunitiesCount" },
  { id: "bets", label: "Paris", icon: TrendingUp, href: "/bets", badge: "activeBetsCount" },
  { id: "manual-bets", label: "Paris & CLV", icon: Calculator, href: "/manual-bets" },
  { id: "compare-agents", label: "Comparer", icon: Users2, href: "/agents-comparison" },
  { id: "agent-strategy", label: "Stratégie", icon: Shield, href: "/agents" },
  { id: "conseil-ultim", label: "Conseil Ultim", icon: Target, href: "/conseil-ultim" },
  { id: "full-gain", label: "Full Gain 2.0", icon: Diamond, href: "/full-gain" },
  { id: "ferrari", label: "FERRARI", icon: Car, href: "/ferrari" },
  { id: "tracking-stats", label: "Tracking CLV", icon: BarChart3, href: "/full-gain/stats" },
  { id: "tips", label: "Astuces", icon: Lightbulb, href: "/tips" },
  { id: "analytics", label: "Analytics", icon: BarChart3, href: "/analytics" },
  { id: "settings", label: "Paramètres", icon: Settings, href: "/settings" },
];

export function Sidebar({ opportunitiesCount, activeBetsCount }: SidebarProps) {
  const pathname = usePathname();

  const getBadgeCount = (badgeType?: string) => {
    if (badgeType === "opportunitiesCount") return opportunitiesCount;
    if (badgeType === "activeBetsCount") return activeBetsCount;
    return undefined;
  };

  return (
    <nav className="hidden md:flex flex-col w-20 xl:w-64 bg-slate-950/80 backdrop-blur-lg border-r border-slate-800 p-4 transition-all duration-300">
      <div className="flex items-center justify-center xl:justify-start space-x-3 h-16 mb-6 px-3">
        <Target className="h-8 w-8 text-blue-400" style={{ filter: "drop-shadow(0 0 8px rgba(59,130,246,0.7))" }} />
        <span className="text-2xl font-bold text-white xl:block hidden font-tech text-glow-blue">AURA</span>
      </div>

      <ul className="flex-grow space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const badgeCount = getBadgeCount(item.badge);

          return (
            <li key={item.id}>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center justify-between space-x-4 p-3 rounded-lg text-slate-300 w-full group",
                  isActive
                    ? "bg-blue-600/20 text-blue-300 border border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                    : "hover:bg-slate-800/50"
                )}
              >
                <div className="flex items-center space-x-4">
                  <item.icon className={cn("h-6 w-6", isActive ? "text-blue-400" : "text-slate-400")} />
                  <span className="xl:block hidden text-lg font-medium">{item.label}</span>
                </div>
                {badgeCount !== undefined && badgeCount > 0 && (
                  <span className="xl:block hidden px-2 py-0.5 text-xs font-bold bg-blue-500 text-white rounded-full">
                    {badgeCount}
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto pt-4 border-t border-slate-700">
        <div className="rounded-2xl border border-slate-700/70 bg-slate-800/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">Stratégie hybride</p>
          <p className="mt-2 text-sm text-slate-300 xl:block hidden">
            10 paris Tabac + 10 paris Ligne analysés en temps réel.
          </p>
        </div>
      </div>
    </nav>
  );
}

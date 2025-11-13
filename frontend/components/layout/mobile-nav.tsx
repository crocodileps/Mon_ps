"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Target,
  TrendingUp,
  Shield,
  Lightbulb,
} from "lucide-react";

const mobileNavItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { id: "opportunities", label: "Opport.", icon: Target, href: "/opportunities" },
  { id: "bets", label: "Paris", icon: TrendingUp, href: "/bets" },
  { id: "agent-strategy", label: "Stratégie", icon: Shield, href: "/agent-strategy" },
  { id: "tips", label: "Astuces", icon: Lightbulb, href: "/tips" },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-slate-950/90 backdrop-blur-lg border-t border-slate-800 flex justify-around p-2 z-50">
      {mobileNavItems.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.id}
            href={item.href}
            className={cn(
              "flex flex-col items-center p-2 rounded-lg w-1/5",
              isActive ? "text-blue-400 bg-blue-500/10" : "text-slate-400"
            )}
            aria-label={item.label}
          >
            <item.icon className="h-5 w-5 mb-1" />
            <span className="text-xs font-medium">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

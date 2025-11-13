"use client";

import { Wallet } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getBankrollStats } from "@/lib/api";

export function Header() {
  const { data: bankrollStats } = useQuery({
    queryKey: ["bankroll-stats"],
    queryFn: getBankrollStats,
    refetchInterval: 30000, // Refresh toutes les 30s
  });

  const balance = bankrollStats?.current_balance || 0;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800/50 bg-slate-950/70 px-4 backdrop-blur-xl lg:px-8">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold text-white font-tech">Mon_PS Dashboard</h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* Wallet Button */}
        <button className="flex items-center space-x-2 bg-slate-800/50 p-2 md:px-4 md:py-2 rounded-lg border border-slate-700/50 hover:bg-slate-800 transition-all">
          <Wallet className="h-5 w-5 text-green-400" />
          <span className="hidden md:block text-green-400 font-bold font-tech">
            {balance.toFixed(2)}€
          </span>
        </button>
      </div>
    </header>
  );
}


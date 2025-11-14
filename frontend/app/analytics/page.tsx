"use client";

import { Card } from "@/components/ui/card";
import { useGlobalStats, useBankrollStats, useBookmakerStats } from "@/hooks";
import { Loader2 } from "lucide-react";
import { formatNumber } from "@/lib/format";

export default function AnalyticsPage() {
  const { data: globalStats, isLoading: loadingGlobal } = useGlobalStats();
  const { data: bankroll, isLoading: loadingBankroll } = useBankrollStats();
  const { data: bookmakers, isLoading: loadingBookmakers } = useBookmakerStats();

  const isLoading = loadingGlobal || loadingBankroll || loadingBookmakers;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">📊 Analytics</h1>
        <p className="text-gray-400">Analyses détaillées de performance</p>
      </div>

      {/* Stats Bankroll */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-6 bg-gray-900/50 border-gray-800">
          <p className="text-sm text-gray-400 mb-2">Bankroll Actuel</p>
          <p className="text-3xl font-bold text-white">
            {formatNumber(bankroll?.current_bankroll ?? 0, 2)}€
          </p>
        </Card>

        <Card className="p-6 bg-gray-900/50 border-gray-800">
          <p className="text-sm text-gray-400 mb-2">Profit Total</p>
          <p className="text-3xl font-bold text-green-500">
            +{formatNumber(bankroll?.total_profit ?? 0, 2)}€
          </p>
        </Card>

        <Card className="p-6 bg-gray-900/50 border-gray-800">
          <p className="text-sm text-gray-400 mb-2">ROI</p>
          <p className="text-3xl font-bold text-blue-400">
            {formatNumber(bankroll?.roi ?? 0, 1)}%
          </p>
        </Card>

        <Card className="p-6 bg-gray-900/50 border-gray-800">
          <p className="text-sm text-gray-400 mb-2">Win Rate</p>
          <p className="text-3xl font-bold text-purple-400">
            {formatNumber(bankroll?.win_rate ?? 0, 1)}%
          </p>
        </Card>
      </div>

      {/* Stats Globales */}
      <Card className="p-6 bg-gray-900/50 border-gray-800">
        <h2 className="text-xl font-semibold text-white mb-4">📈 Statistiques Globales</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-400">Total Paris</p>
            <p className="text-2xl font-bold text-white">{bankroll?.total_bets ?? 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Gagnés</p>
            <p className="text-2xl font-bold text-green-500">{bankroll?.won_bets ?? 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Perdus</p>
            <p className="text-2xl font-bold text-red-500">{bankroll?.lost_bets ?? 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Total Misé</p>
            <p className="text-2xl font-bold text-white">
              {formatNumber(bankroll?.total_staked ?? 0, 2)}€
            </p>
          </div>
        </div>
      </Card>

      {/* Top Bookmakers */}
      <Card className="p-6 bg-gray-900/50 border-gray-800">
        <h2 className="text-xl font-semibold text-white mb-4">🏆 Top 10 Bookmakers</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 text-gray-400">Bookmaker</th>
                <th className="text-right py-3 text-gray-400">Cotes</th>
                <th className="text-right py-3 text-gray-400">Matchs</th>
                <th className="text-right py-3 text-gray-400">Cote Moy.</th>
              </tr>
            </thead>
            <tbody>
              {bookmakers?.slice(0, 10).map((bm: any, idx: number) => (
                <tr key={idx} className="border-b border-gray-800/50">
                  <td className="py-3 text-white">{bm.bookmaker}</td>
                  <td className="text-right text-gray-300">{bm.nb_cotes.toLocaleString()}</td>
                  <td className="text-right text-gray-300">{bm.nb_matches}</td>
                  <td className="text-right text-blue-400">{formatNumber(bm.avg_odds, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

'use client'

import { useState } from 'react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { PieChart, Pie, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { X } from 'lucide-react'
import { RoiAnalysisModal } from './roi-analysis-modal'

const portfolioStats = {
  roiGlobal: 15.2,
  won: 52,
  lost: 31,
  inProgress: 5,
}

const plByAgent = [
  { name: 'Titan', value: 63, color: '#3b82f6' },
  { name: 'Oracle', value: 44, color: '#a78bfa' },
  { name: 'Momentum', value: 8, color: '#f472b6' },
  { name: 'Manual', value: 12, color: '#6b7280' },
]

const roiByType = [
  { name: 'Football', roi: 22 },
  { name: 'NBA', roi: 12 },
  { name: 'Tennis', roi: 10 },
]

interface PortfolioModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PortfolioModal({ isOpen, onClose }: PortfolioModalProps) {
  const [isRoiAnalysisOpen, setIsRoiAnalysisOpen] = useState(false)

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-[90vw] md:max-w-[1400px] max-h-[90vh] overflow-y-auto bg-[#0a0f1e] border border-white/10 p-0">
          <div className="sticky top-0 z-10 bg-[#0a0f1e]/95 backdrop-blur-lg border-b border-white/10 px-8 py-6">
            <div className="flex items-center justify-between">
              <h2 className="text-3xl font-bold text-white">Mon Portefeuille</h2>
              <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                <X size={24} className="text-gray-400" />
              </button>
            </div>
          </div>

          <div className="p-8 space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <button
                onClick={() => setIsRoiAnalysisOpen(true)}
                className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg hover:border-blue-500/50 hover:bg-[#111827]/80 transition-all cursor-pointer text-left"
              >
                <p className="text-sm text-gray-400 mb-2 uppercase tracking-wide">ROI Global</p>
                <p className="text-4xl font-bold text-green-400">{portfolioStats.roiGlobal}%</p>
              </button>
              <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
                <p className="text-sm text-gray-400 mb-2 uppercase tracking-wide">Gagnés</p>
                <p className="text-4xl font-bold text-green-400">{portfolioStats.won}</p>
              </div>
              <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
                <p className="text-sm text-gray-400 mb-2 uppercase tracking-wide">Perdus</p>
                <p className="text-4xl font-bold text-red-400">{portfolioStats.lost}</p>
              </div>
              <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
                <p className="text-sm text-gray-400 mb-2 uppercase tracking-wide">En Cours</p>
                <p className="text-4xl font-bold text-yellow-400">{portfolioStats.inProgress}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
                <h3 className="text-xl font-semibold text-white mb-6">P/L par Agent</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <PieChart>
                    <Pie data={plByAgent} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name} (${value}%)`} outerRadius={120} dataKey="value" paddingAngle={2}>
                      {plByAgent.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
                <h3 className="text-xl font-semibold text-white mb-6">ROI par Type</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={roiByType}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" tick={{ fill: '#9ca3af' }} />
                    <YAxis stroke="#9ca3af" tick={{ fill: '#9ca3af' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                    <Bar dataKey="roi" fill="#10b981" radius={[8, 8, 0, 0]} maxBarSize={80} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <RoiAnalysisModal isOpen={isRoiAnalysisOpen} onClose={() => setIsRoiAnalysisOpen(false)} roiValue={portfolioStats.roiGlobal} />
    </>
  )
}

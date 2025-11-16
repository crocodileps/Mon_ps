'use client'

import { Dialog, DialogContent } from '@/components/ui/dialog'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { X } from 'lucide-react'

const roiEvolutionData = [
  { day: 'Jour 1', roi: 0.5 },
  { day: 'Jour 5', roi: 2.8 },
  { day: 'Jour 10', roi: 5.2 },
  { day: 'Jour 15', roi: 8.5 },
  { day: 'Jour 20', roi: 11.2 },
  { day: 'Jour 25', roi: 13.8 },
  { day: 'Jour 30', roi: 15.2 },
]

interface RoiAnalysisModalProps {
  isOpen: boolean
  onClose: () => void
  roiValue: number
}

export function RoiAnalysisModal({ isOpen, onClose, roiValue }: RoiAnalysisModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[90vw] md:max-w-[1200px] max-h-[90vh] overflow-y-auto bg-[#0a0f1e] border border-white/10 p-0">
        <div className="sticky top-0 z-10 bg-[#0a0f1e]/95 backdrop-blur-lg border-b border-white/10 px-8 py-6">
          <div className="flex items-center justify-between">
            <h2 className="text-3xl font-bold text-white text-center flex-1">
              Analyse ROI Global ({roiValue}%)
            </h2>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
              <X size={24} className="text-gray-400" />
            </button>
          </div>
        </div>

        <div className="p-8 space-y-8">
          <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
            <h3 className="text-xl font-semibold text-gray-300 mb-6">Évolution du ROI (30 Jours)</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={roiEvolutionData}>
                <defs>
                  <linearGradient id="colorRoi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="day" stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 12 }} tickFormatter={(value) => `${value}%`} domain={[0, 16]} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} formatter={(value: number) => [`${value}%`, 'ROI']} />
                <Area type="monotone" dataKey="roi" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorRoi)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-[#111827]/60 backdrop-blur-sm border border-blue-500/30 rounded-xl p-6 shadow-lg">
              <p className="text-sm text-gray-400 mb-3 uppercase tracking-wide">Meilleur Agent</p>
              <p className="text-3xl font-bold text-blue-400 mb-2">Titan</p>
              <p className="text-2xl font-semibold text-green-400">ROI: 25.2%</p>
            </div>
            <div className="bg-[#111827]/60 backdrop-blur-sm border border-pink-500/30 rounded-xl p-6 shadow-lg">
              <p className="text-sm text-gray-400 mb-3 uppercase tracking-wide">Pire Agent</p>
              <p className="text-3xl font-bold text-pink-400 mb-2">Momentum</p>
              <p className="text-2xl font-semibold text-red-400">ROI: -8.1%</p>
            </div>
            <div className="bg-[#111827]/60 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6 shadow-lg">
              <p className="text-sm text-gray-400 mb-3 uppercase tracking-wide">Meilleur Sport</p>
              <p className="text-3xl font-bold text-cyan-400 mb-2">Football</p>
              <p className="text-2xl font-semibold text-green-400">ROI: 20.5%</p>
            </div>
          </div>

          <div className="bg-[#111827]/60 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Analyse de l'IA</h3>
            <div className="bg-[#0a0f1e]/60 border border-white/5 rounded-lg p-5">
              <p className="text-gray-300 leading-relaxed">
                Votre ROI de {roiValue}% est excellent. Il est principalement tiré par l'agent Titan et vos paris sur le Football.
              </p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

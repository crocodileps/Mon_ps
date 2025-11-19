'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Loader2, TrendingUp, DollarSign, Target } from 'lucide-react'
import { placeBet } from '@/lib/api'
import { toast } from 'sonner'

interface PlaceBetModalProps {
  isOpen: boolean
  onClose: () => void
  opportunity: {
    id: string
    match_id: string
    home_team: string
    away_team: string
    sport: string
    commence_time: string
    outcome: string
    best_odds: number
    bookmaker_best: string
    edge_pct: number
  }
  patronScore?: string
}

export function PlaceBetModal({ isOpen, onClose, opportunity, patronScore }: PlaceBetModalProps) {
  const [stake, setStake] = useState<string>('100')
  const [odds, setOdds] = useState<string>(opportunity.best_odds.toString())
  const [notes, setNotes] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const potentialPayout = parseFloat(stake || '0') * parseFloat(odds || '0')
  const potentialProfit = potentialPayout - parseFloat(stake || '0')

  const handleSubmit = async () => {
    if (!stake || parseFloat(stake) <= 0) {
      toast.error('Montant de mise invalide')
      return
    }

    setIsSubmitting(true)

    try {
      const betData = {
        match_id: opportunity.match_id,
        opportunity_id: opportunity.id,
        home_team: opportunity.home_team,
        away_team: opportunity.away_team,
        sport: opportunity.sport,
        commence_time: opportunity.commence_time,
        outcome: opportunity.outcome,
        odds: parseFloat(odds),
        stake: parseFloat(stake),
        bookmaker: opportunity.bookmaker_best,
        edge_pct: opportunity.edge_pct,
        agent_recommended: 'patron',
        patron_score: patronScore || 'UNKNOWN',
        notes: notes || undefined
      }

      const result = await placeBet(betData)
      
      toast.success('Pari enregistré !', {
        description: `Bet ID: ${result.bet_id} • Gain potentiel: ${potentialPayout.toFixed(2)}€`
      })

      onClose()
      setStake('100')
      setNotes('')

    } catch (error) {
      console.error('Place bet error:', error)
      toast.error('Erreur lors de l\'enregistrement du pari')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md bg-slate-900 border-slate-800">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-white flex items-center gap-2">
            <Target className="w-6 h-6 text-violet-400" />
            Placer un pari
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Infos du match */}
          <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
            <div className="text-center">
              <p className="text-lg font-bold text-white mb-1">
                {opportunity.home_team} vs {opportunity.away_team}
              </p>
              <p className="text-sm text-slate-400">
                {new Date(opportunity.commence_time).toLocaleString('fr-FR')}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3 mt-4">
              <div className="text-center">
                <p className="text-xs text-slate-500 mb-1">Pronostic</p>
                <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30 capitalize">
                  {opportunity.outcome}
                </Badge>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 mb-1">Cote ({opportunity.bookmaker_best})</p>
                <Input
                  type="number"
                  step="0.01"
                  value={odds}
                  onChange={(e) => setOdds(e.target.value)}
                  className="w-24 mx-auto text-center bg-slate-700 border-slate-600 text-white font-bold text-xl py-1"
                />
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-500 mb-1">Edge</p>
                <Badge className="bg-green-500/20 text-green-400">
                  {opportunity.edge_pct.toFixed(1)}%
                </Badge>
              </div>
            </div>

            {patronScore && (
              <div className="mt-3 pt-3 border-t border-slate-700 text-center">
                <p className="text-xs text-slate-500 mb-1">Score Patron</p>
                <Badge className={`${patronScore === 'ANALYSER' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {patronScore}
                </Badge>
              </div>
            )}
          </div>

          {/* Montant de la mise */}
          <div className="space-y-2">
            <Label htmlFor="stake" className="text-slate-300 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Montant de la mise (€)
            </Label>
            <Input
              id="stake"
              type="number"
              step="10"
              min="1"
              value={stake}
              onChange={(e) => setStake(e.target.value)}
              className="bg-slate-800 border-slate-700 text-white text-lg font-bold"
              placeholder="100"
            />
          </div>

          {/* Gains potentiels */}
          <div className="bg-gradient-to-r from-violet-500/10 to-indigo-500/10 p-4 rounded-lg border border-violet-500/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Gain potentiel
              </span>
              <span className="text-2xl font-bold text-white">
                {potentialPayout.toFixed(2)}€
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Profit net</span>
              <span className={`font-bold ${potentialProfit > 0 ? 'text-green-400' : 'text-slate-400'}`}>
                +{potentialProfit.toFixed(2)}€
              </span>
            </div>
          </div>

          {/* Notes optionnelles */}
          <div className="space-y-2">
            <Label htmlFor="notes" className="text-slate-300">
              Notes (optionnel)
            </Label>
            <Input
              id="notes"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="bg-slate-800 border-slate-700 text-white"
              placeholder="Analyse personnelle..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 border-slate-700"
            >
              Annuler
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || !stake || parseFloat(stake) <= 0}
              className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Enregistrement...
                </>
              ) : (
                'Confirmer le pari'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}


'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Loader2 } from 'lucide-react';

interface Match {
  match_id: string;
  sport: string;
  home_team: string;
  away_team: string;
  commence_time: string;
}

interface CreateBetForm {
  match_id: string;
  match_name: string;
  sport: string;
  kickoff_time: string;
  market_type: 'h2h' | 'totals';
  selection: string;
  line: number | null;
  bookmaker: string;
  odds_obtained: number;
  stake: number;
  notes: string;
}

export function CreateBetModal() {
  const [open, setOpen] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [form, setForm] = useState<CreateBetForm>({
    match_id: '',
    match_name: '',
    sport: '',
    kickoff_time: '',
    market_type: 'h2h',
    selection: '',
    line: null,
    bookmaker: '',
    odds_obtained: 0,
    stake: 0,
    notes: '',
  });

  const queryClient = useQueryClient();

  // Fetch available matches
  const { data: matches, isLoading: matchesLoading } = useQuery<Match[]>({
    queryKey: ['available-matches'],
    queryFn: () => api.get('/odds/odds/matches'),
    enabled: open,
  });

  // Create bet mutation
  const createBet = useMutation({
    mutationFn: (data: CreateBetForm) => api.post('/manual-bets/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manual-bets'] });
      queryClient.invalidateQueries({ queryKey: ['manual-bets-stats'] });
      setOpen(false);
      resetForm();
      alert('Pari créé avec succès !');
    },
    onError: (error) => {
      console.error('Error creating bet:', error);
      alert('Erreur lors de la création du pari');
    },
  });

  const resetForm = () => {
    setSelectedMatch(null);
    setForm({
      match_id: '',
      match_name: '',
      sport: '',
      kickoff_time: '',
      market_type: 'h2h',
      selection: '',
      line: null,
      bookmaker: '',
      odds_obtained: 0,
      stake: 0,
      notes: '',
    });
  };

  // Update form when match is selected
  useEffect(() => {
    if (selectedMatch) {
      setForm((prev) => ({
        ...prev,
        match_id: selectedMatch.match_id,
        match_name: `${selectedMatch.home_team} vs ${selectedMatch.away_team}`,
        sport: selectedMatch.sport,
        kickoff_time: selectedMatch.commence_time,
      }));
    }
  }, [selectedMatch]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!form.match_id) {
      alert('Veuillez sélectionner un match');
      return;
    }
    if (!form.selection) {
      alert('Veuillez entrer une sélection');
      return;
    }
    if (form.odds_obtained <= 1) {
      alert('La cote doit être supérieure à 1');
      return;
    }
    if (form.stake <= 0) {
      alert('La mise doit être positive');
      return;
    }
    if (!form.bookmaker) {
      alert('Veuillez entrer le bookmaker');
      return;
    }

    createBet.mutate(form);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-green-600 hover:bg-green-700 text-white">
          <Plus className="w-4 h-4 mr-2" />
          Nouveau Pari
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-800 border-slate-700 text-white max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">Créer un Nouveau Pari</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {/* Match Selection */}
          <div className="space-y-2">
            <Label className="text-slate-300">Match</Label>
            {matchesLoading ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                Chargement des matchs...
              </div>
            ) : (
              <Select
                value={selectedMatch?.match_id || ''}
                onValueChange={(value) => {
                  const match = matches?.find((m) => m.match_id === value);
                  setSelectedMatch(match || null);
                }}
              >
                <SelectTrigger className="bg-slate-700 border-slate-600">
                  <SelectValue placeholder="Sélectionner un match" />
                </SelectTrigger>
                <SelectContent>
                  {matches?.map((match) => (
                    <SelectItem key={match.match_id} value={match.match_id}>
                      <div className="flex flex-col">
                        <span>{match.home_team} vs {match.away_team}</span>
                        <span className="text-xs text-slate-400">
                          {match.sport.replace('soccer_', '').replace(/_/g, ' ')} • {new Date(match.commence_time).toLocaleString('fr-FR')}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Market Type */}
          <div className="space-y-2">
            <Label className="text-slate-300">Type de Marché</Label>
            <Select
              value={form.market_type}
              onValueChange={(value) => {
                setForm((prev) => ({ ...prev, market_type: value as 'h2h' | 'totals', selection: '', line: null }));
              }}
            >
              <SelectTrigger className="bg-slate-700 border-slate-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="h2h">1X2 (Home/Draw/Away)</SelectItem>
                <SelectItem value="totals">Over/Under</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Selection based on market type */}
          {form.market_type === 'h2h' ? (
            <div className="space-y-2">
              <Label className="text-slate-300">Sélection</Label>
              <Select
                value={form.selection}
                onValueChange={(value) => setForm((prev) => ({ ...prev, selection: value }))}
              >
                <SelectTrigger className="bg-slate-700 border-slate-600">
                  <SelectValue placeholder="Choisir" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Home">Home (Domicile)</SelectItem>
                  <SelectItem value="Draw">Draw (Nul)</SelectItem>
                  <SelectItem value="Away">Away (Extérieur)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-slate-300">Over/Under</Label>
                <Select
                  value={form.selection.includes('Over') ? 'Over' : form.selection.includes('Under') ? 'Under' : ''}
                  onValueChange={(value) => {
                    const line = form.line || 2.5;
                    setForm((prev) => ({ ...prev, selection: `${value} ${line}` }));
                  }}
                >
                  <SelectTrigger className="bg-slate-700 border-slate-600">
                    <SelectValue placeholder="Choisir" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Over">Over (Plus de)</SelectItem>
                    <SelectItem value="Under">Under (Moins de)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-slate-300">Ligne</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="10"
                  value={form.line || ''}
                  onChange={(e) => {
                    const line = parseFloat(e.target.value);
                    const type = form.selection.includes('Over') ? 'Over' : 'Under';
                    setForm((prev) => ({ 
                      ...prev, 
                      line: line,
                      selection: type ? `${type} ${line}` : prev.selection
                    }));
                  }}
                  className="bg-slate-700 border-slate-600"
                  placeholder="2.5"
                />
              </div>
            </div>
          )}

          {/* Bookmaker */}
          <div className="space-y-2">
            <Label className="text-slate-300">Bookmaker</Label>
            <Select
              value={form.bookmaker}
              onValueChange={(value) => setForm((prev) => ({ ...prev, bookmaker: value }))}
            >
              <SelectTrigger className="bg-slate-700 border-slate-600">
                <SelectValue placeholder="Sélectionner" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Bet365">Bet365</SelectItem>
                <SelectItem value="Winamax">Winamax</SelectItem>
                <SelectItem value="Unibet">Unibet</SelectItem>
                <SelectItem value="Betclic">Betclic</SelectItem>
                <SelectItem value="PMU">PMU</SelectItem>
                <SelectItem value="Zebet">Zebet</SelectItem>
                <SelectItem value="Netbet">Netbet</SelectItem>
                <SelectItem value="Bwin">Bwin</SelectItem>
                <SelectItem value="Parions Sport">Parions Sport</SelectItem>
                <SelectItem value="Other">Autre</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Odds and Stake */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Cote Obtenue</Label>
              <Input
                type="number"
                step="0.01"
                min="1.01"
                value={form.odds_obtained || ''}
                onChange={(e) => setForm((prev) => ({ ...prev, odds_obtained: parseFloat(e.target.value) }))}
                className="bg-slate-700 border-slate-600"
                placeholder="1.95"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Mise (€)</Label>
              <Input
                type="number"
                step="1"
                min="1"
                value={form.stake || ''}
                onChange={(e) => setForm((prev) => ({ ...prev, stake: parseFloat(e.target.value) }))}
                className="bg-slate-700 border-slate-600"
                placeholder="50"
              />
            </div>
          </div>

          {/* Potential Return */}
          {form.odds_obtained > 1 && form.stake > 0 && (
            <div className="bg-slate-700/50 p-3 rounded-lg">
              <p className="text-sm text-slate-400">Gain Potentiel</p>
              <p className="text-lg font-bold text-green-400">
                {(form.stake * form.odds_obtained).toFixed(2)}€
                <span className="text-sm text-slate-400 ml-2">
                  (Profit: {(form.stake * (form.odds_obtained - 1)).toFixed(2)}€)
                </span>
              </p>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label className="text-slate-300">Notes (optionnel)</Label>
            <Input
              value={form.notes}
              onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
              className="bg-slate-700 border-slate-600"
              placeholder="Raison du pari, analyse..."
            />
          </div>

          {/* Submit Button */}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              Annuler
            </Button>
            <Button
              type="submit"
              disabled={createBet.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {createBet.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Création...
                </>
              ) : (
                'Créer le Pari'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

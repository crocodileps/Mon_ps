"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V5.3 PHASE 2 - HEDGE FUND GRADE                       ║
║                                                                              ║
║  NOUVELLES DIMENSIONS PHASE 2:                                               ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🔗 CREATOR-FINISHER LINK:                                                   ║
║     • Combos passeur → buteur avec historique                                ║
║     • combo_score = occurrences × xG moyen                                   ║
║     • Edge: Bookmakers pricent séparément, le COMBO a plus de value          ║
║                                                                              ║
║  ⚡ MOMENTUM DNA:                                                             ║
║     • Séquences de buts par match (minutes exactes)                          ║
║     • avg_time_between_goals, burst_sequences, burst_rate                    ║
║     • Profils: BURST_SCORER (marque en série), STEADY_SCORER                 ║
║     • Edge Live: Si équipe BURST marque → probabilité élevée 2ème but rapide ║
║                                                                              ║
║  HÉRITE DE: loader_v5_2_extended.py (NP-Clinical + xGChain)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import json

# Import du loader V5.2 pour héritage
import sys
sys.path.insert(0, '/home/Mon_ps')

from agents.attack_v1.data.loader_v5_2_extended import (
    AttackDataLoaderV52Extended,
    PlayerFullProfile2025Extended,
    TeamProfile2025Extended,
    safe_int, safe_float
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# CREATOR-FINISHER COMBO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CreatorFinisherCombo:
    """
    Combo Créateur → Finisseur
    
    Edge: Les bookmakers pricent "Player A Assist" et "Player B Goal" séparément.
    Mais si le combo A→B se répète souvent, la probabilité conjointe est SUPÉRIEURE
    au produit des probabilités individuelles.
    """
    creator: str = ""
    finisher: str = ""
    team: str = ""
    occurrences: int = 0
    total_xG: float = 0.0
    avg_xG: float = 0.0
    minutes: List[int] = field(default_factory=list)
    
    # Contexte
    goals_home: int = 0
    goals_away: int = 0
    goals_1h: int = 0
    goals_2h: int = 0
    
    # Score composite
    combo_score: float = 0.0
    combo_profile: str = ""  # ELITE_COMBO, STRONG_COMBO, EMERGING_COMBO, RARE_COMBO
    
    def calculate(self) -> None:
        """Calcule les métriques du combo"""
        if self.occurrences > 0:
            self.avg_xG = self.total_xG / self.occurrences
            
        # Combo Score = occurrences × (1 + avg_xG) × bonus_consistency
        # Plus le combo est fréquent et de qualité, plus le score est élevé
        consistency_bonus = 1.0
        if self.occurrences >= 5:
            consistency_bonus = 1.5
        elif self.occurrences >= 3:
            consistency_bonus = 1.2
            
        self.combo_score = self.occurrences * (1 + self.avg_xG) * consistency_bonus
        
        # Classification
        if self.occurrences >= 5 and self.avg_xG >= 0.3:
            self.combo_profile = "ELITE_COMBO"
        elif self.occurrences >= 4 or (self.occurrences >= 3 and self.avg_xG >= 0.35):
            self.combo_profile = "STRONG_COMBO"
        elif self.occurrences >= 2:
            self.combo_profile = "EMERGING_COMBO"
        else:
            self.combo_profile = "RARE_COMBO"


# ═══════════════════════════════════════════════════════════════════════════════
# MOMENTUM DNA - Séquences de buts
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MatchGoalSequence:
    """Séquence de buts dans un match"""
    match_id: int = 0
    team: str = ""
    opponent: str = ""
    date: str = ""
    goals_minutes: List[int] = field(default_factory=list)
    total_goals: int = 0
    
    # Métriques de séquence
    time_between_goals: List[int] = field(default_factory=list)
    avg_time_between: float = 0.0
    min_time_between: int = 0
    max_time_between: int = 0
    
    # Bursts (2 buts en moins de 10 minutes)
    burst_count: int = 0
    burst_minutes: List[Tuple[int, int]] = field(default_factory=list)
    
    def calculate(self) -> None:
        """Calcule les métriques de séquence"""
        self.total_goals = len(self.goals_minutes)
        
        if self.total_goals >= 2:
            # Trier les minutes
            sorted_mins = sorted(self.goals_minutes)
            
            # Calculer les écarts
            self.time_between_goals = [
                sorted_mins[i+1] - sorted_mins[i] 
                for i in range(len(sorted_mins) - 1)
            ]
            
            if self.time_between_goals:
                self.avg_time_between = sum(self.time_between_goals) / len(self.time_between_goals)
                self.min_time_between = min(self.time_between_goals)
                self.max_time_between = max(self.time_between_goals)
                
                # Détecter les bursts (< 10 minutes entre 2 buts)
                for i, gap in enumerate(self.time_between_goals):
                    if gap <= 10:
                        self.burst_count += 1
                        self.burst_minutes.append((sorted_mins[i], sorted_mins[i+1]))


@dataclass
class TeamMomentumDNA:
    """
    ADN Momentum d'une équipe
    
    Concept: Certaines équipes marquent EN SÉRIE (burst), d'autres espacent.
    Edge Live: Si une équipe BURST_SCORER marque à 55', probabilité élevée
    d'un 2ème but avant 70'.
    """
    team: str = ""
    
    # Statistiques globales
    total_matches_with_goals: int = 0
    total_goals: int = 0
    matches_with_multiple_goals: int = 0
    
    # Séquences
    all_sequences: List[MatchGoalSequence] = field(default_factory=list)
    
    # Métriques Momentum
    avg_time_between_goals: float = 0.0
    total_bursts: int = 0
    burst_rate: float = 0.0  # bursts / matchs avec 2+ buts
    
    # Profil
    momentum_profile: str = ""  # BURST_SCORER, STEADY_SCORER, MIXED
    
    # Top séquences burst
    best_bursts: List[Dict] = field(default_factory=list)
    
    def calculate(self) -> None:
        """Calcule le profil momentum"""
        if not self.all_sequences:
            return
            
        self.total_matches_with_goals = len(self.all_sequences)
        self.total_goals = sum(s.total_goals for s in self.all_sequences)
        
        # Matchs avec 2+ buts
        multi_goal_matches = [s for s in self.all_sequences if s.total_goals >= 2]
        self.matches_with_multiple_goals = len(multi_goal_matches)
        
        if multi_goal_matches:
            # Moyenne du temps entre buts
            all_times = []
            for seq in multi_goal_matches:
                all_times.extend(seq.time_between_goals)
            if all_times:
                self.avg_time_between_goals = sum(all_times) / len(all_times)
                
            # Total bursts
            self.total_bursts = sum(s.burst_count for s in multi_goal_matches)
            self.burst_rate = (self.total_bursts / self.matches_with_multiple_goals) * 100
            
            # Classification
            if self.burst_rate >= 60:
                self.momentum_profile = "BURST_SCORER"
            elif self.burst_rate >= 30:
                self.momentum_profile = "MIXED"
            else:
                self.momentum_profile = "STEADY_SCORER"
                
            # Top 5 bursts
            all_bursts = []
            for seq in multi_goal_matches:
                for burst in seq.burst_minutes:
                    all_bursts.append({
                        'team': seq.team,
                        'opponent': seq.opponent,
                        'date': seq.date,
                        'burst': f"{burst[0]}' → {burst[1]}'",
                        'gap': burst[1] - burst[0]
                    })
            self.best_bursts = sorted(all_bursts, key=lambda x: x['gap'])[:5]


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V5.3 PHASE 2
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV53Phase2(AttackDataLoaderV52Extended):
    """
    Loader V5.3 PHASE 2 - HEDGE FUND GRADE
    
    Hérite de V5.2 et ajoute:
    • Creator-Finisher Link (combos passeur → buteur)
    • Momentum DNA (séquences de buts, burst detection)
    """
    
    def __init__(self):
        super().__init__()
        
        # Phase 2 data
        self.combos: Dict[str, CreatorFinisherCombo] = {}  # "creator|finisher|team" → Combo
        self.team_combos: Dict[str, List[CreatorFinisherCombo]] = defaultdict(list)
        self.team_momentum: Dict[str, TeamMomentumDNA] = {}
        
    def load_all(self) -> None:
        """Charge tout + Phase 2"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V5.3 PHASE 2 - HEDGE FUND GRADE")
        print("=" * 80)
        
        # Charger V5.2 (players, teams, NP-Clinical, xGChain)
        self._load_players_impact_dna()
        self._load_goals_timing_style()
        self._load_context_dna()
        self._aggregate_teams()
        self._calculate_all()
        
        # Phase 2: Creator-Finisher + Momentum
        print("\n" + "─" * 80)
        print("🚀 PHASE 2: CREATOR-FINISHER LINK + MOMENTUM DNA")
        print("─" * 80)
        
        self._build_creator_finisher_links()
        self._build_momentum_dna()
        
        self._print_phase2_insights()
        
    def _build_creator_finisher_links(self) -> None:
        """Construit les liens Creator-Finisher à partir de all_goals"""
        print("\n🔗 [PHASE 2.1] Construction Creator-Finisher Links...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        with open(path) as f:
            goals = json.load(f)
            
        combo_data = defaultdict(lambda: {
            'occurrences': 0,
            'total_xG': 0.0,
            'minutes': [],
            'goals_home': 0,
            'goals_away': 0,
            'goals_1h': 0,
            'goals_2h': 0
        })
        
        goals_with_assist = 0
        
        for g in goals:
            assister = g.get('assister', '')
            scorer = g.get('scorer', '')
            team = g.get('scoring_team', '')
            
            if not assister or not scorer or not team:
                continue
                
            goals_with_assist += 1
            key = f"{assister}|{scorer}|{team}"
            
            combo_data[key]['occurrences'] += 1
            combo_data[key]['total_xG'] += safe_float(g.get('xG', 0))
            combo_data[key]['minutes'].append(safe_int(g.get('minute', 0)))
            
            # Contexte
            if g.get('home_away') == 'h':
                combo_data[key]['goals_home'] += 1
            else:
                combo_data[key]['goals_away'] += 1
                
            if g.get('half') == '1H':
                combo_data[key]['goals_1h'] += 1
            else:
                combo_data[key]['goals_2h'] += 1
                
        # Créer les objets Combo
        for key, data in combo_data.items():
            parts = key.split('|')
            if len(parts) != 3:
                continue
                
            creator, finisher, team = parts
            
            combo = CreatorFinisherCombo(
                creator=creator,
                finisher=finisher,
                team=team,
                occurrences=data['occurrences'],
                total_xG=data['total_xG'],
                minutes=data['minutes'],
                goals_home=data['goals_home'],
                goals_away=data['goals_away'],
                goals_1h=data['goals_1h'],
                goals_2h=data['goals_2h']
            )
            combo.calculate()
            
            self.combos[key] = combo
            self.team_combos[team].append(combo)
            
        # Trier les combos par équipe
        for team in self.team_combos:
            self.team_combos[team].sort(key=lambda c: -c.combo_score)
            
        print(f"   ✅ {len(self.combos)} combos uniques créés")
        print(f"   ✅ {goals_with_assist} buts avec assist analysés")
        
        # Stats
        elite = len([c for c in self.combos.values() if c.combo_profile == "ELITE_COMBO"])
        strong = len([c for c in self.combos.values() if c.combo_profile == "STRONG_COMBO"])
        emerging = len([c for c in self.combos.values() if c.combo_profile == "EMERGING_COMBO"])
        
        print(f"\n   📊 COMBOS PAR PROFIL:")
        print(f"      • ELITE_COMBO: {elite}")
        print(f"      • STRONG_COMBO: {strong}")
        print(f"      • EMERGING_COMBO: {emerging}")
        
    def _build_momentum_dna(self) -> None:
        """Construit le Momentum DNA pour chaque équipe"""
        print("\n⚡ [PHASE 2.2] Construction Momentum DNA...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        with open(path) as f:
            goals = json.load(f)
            
        # Grouper les buts par match et équipe
        matches_data = defaultdict(lambda: defaultdict(list))
        match_info = {}
        
        for g in goals:
            match_id = g.get('match_id')
            team = g.get('scoring_team', '')
            opponent = g.get('conceding_team', '')
            minute = safe_int(g.get('minute', 0))
            date = g.get('date', '')
            
            if not match_id or not team or minute == 0:
                continue
                
            matches_data[match_id][team].append(minute)
            
            if match_id not in match_info:
                match_info[match_id] = {}
            match_info[match_id][team] = {'opponent': opponent, 'date': date}
            
        # Créer les séquences par équipe
        team_sequences = defaultdict(list)
        
        for match_id, teams in matches_data.items():
            for team, minutes in teams.items():
                info = match_info.get(match_id, {}).get(team, {})
                
                seq = MatchGoalSequence(
                    match_id=match_id,
                    team=team,
                    opponent=info.get('opponent', ''),
                    date=info.get('date', ''),
                    goals_minutes=minutes
                )
                seq.calculate()
                team_sequences[team].append(seq)
                
        # Créer le Momentum DNA par équipe
        for team, sequences in team_sequences.items():
            momentum = TeamMomentumDNA(
                team=team,
                all_sequences=sequences
            )
            momentum.calculate()
            self.team_momentum[team] = momentum
            
        print(f"   ✅ {len(self.team_momentum)} équipes avec Momentum DNA")
        
        # Stats
        burst = len([m for m in self.team_momentum.values() if m.momentum_profile == "BURST_SCORER"])
        steady = len([m for m in self.team_momentum.values() if m.momentum_profile == "STEADY_SCORER"])
        mixed = len([m for m in self.team_momentum.values() if m.momentum_profile == "MIXED"])
        
        print(f"\n   📊 MOMENTUM PAR PROFIL:")
        print(f"      • BURST_SCORER: {burst}")
        print(f"      • MIXED: {mixed}")
        print(f"      • STEADY_SCORER: {steady}")
        
    def _print_phase2_insights(self) -> None:
        """Affiche les insights Phase 2"""
        print("\n" + "─" * 80)
        print("📊 INSIGHTS PHASE 2")
        print("─" * 80)
        
        # Top 10 Combos
        print("\n🔗 TOP 10 CREATOR-FINISHER COMBOS:")
        all_combos = sorted(self.combos.values(), key=lambda c: -c.combo_score)[:10]
        
        for i, c in enumerate(all_combos, 1):
            print(f"   {i:2}. [{c.combo_profile:15}] {c.creator:20} → {c.finisher:20} | {c.team}")
            print(f"       {c.occurrences}x | xG moy: {c.avg_xG:.2f} | Score: {c.combo_score:.1f}")
            
        # Top Burst Scorers
        print("\n⚡ TOP BURST_SCORER (équipes qui marquent EN SÉRIE):")
        burst_teams = sorted(
            [m for m in self.team_momentum.values() if m.momentum_profile == "BURST_SCORER"],
            key=lambda m: -m.burst_rate
        )[:10]
        
        for m in burst_teams:
            print(f"   • {m.team:25} | Burst Rate: {m.burst_rate:.0f}% | Bursts: {m.total_bursts}")
            if m.best_bursts:
                best = m.best_bursts[0]
                print(f"     └─ Meilleur: {best['burst']} ({best['gap']} min) vs {best['opponent']}")
                
        # Top Steady Scorers
        print("\n🎯 TOP STEADY_SCORER (équipes qui espacent les buts):")
        steady_teams = sorted(
            [m for m in self.team_momentum.values() if m.momentum_profile == "STEADY_SCORER"],
            key=lambda m: m.avg_time_between_goals
        )[:5]
        
        for m in steady_teams:
            print(f"   • {m.team:25} | Écart moyen: {m.avg_time_between_goals:.0f} min | Bursts: {m.total_bursts}")
            
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS PHASE 2: CREATOR-FINISHER
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_elite_combos(self, team: str = None) -> List[CreatorFinisherCombo]:
        """Retourne les combos ELITE"""
        if team:
            return [c for c in self.team_combos.get(team, []) if c.combo_profile == "ELITE_COMBO"]
        return [c for c in self.combos.values() if c.combo_profile == "ELITE_COMBO"]
        
    def get_strong_combos(self, team: str = None) -> List[CreatorFinisherCombo]:
        """Retourne les combos STRONG"""
        if team:
            return [c for c in self.team_combos.get(team, []) if c.combo_profile in ["ELITE_COMBO", "STRONG_COMBO"]]
        return [c for c in self.combos.values() if c.combo_profile in ["ELITE_COMBO", "STRONG_COMBO"]]
        
    def get_team_combos(self, team: str, min_occurrences: int = 2) -> List[CreatorFinisherCombo]:
        """Retourne tous les combos d'une équipe"""
        return [c for c in self.team_combos.get(team, []) if c.occurrences >= min_occurrences]
        
    def get_player_as_creator(self, player_name: str) -> List[CreatorFinisherCombo]:
        """Retourne les combos où le joueur est créateur"""
        return sorted(
            [c for c in self.combos.values() if c.creator == player_name],
            key=lambda c: -c.combo_score
        )
        
    def get_player_as_finisher(self, player_name: str) -> List[CreatorFinisherCombo]:
        """Retourne les combos où le joueur est finisseur"""
        return sorted(
            [c for c in self.combos.values() if c.finisher == player_name],
            key=lambda c: -c.combo_score
        )
        
    def get_combo(self, creator: str, finisher: str, team: str) -> Optional[CreatorFinisherCombo]:
        """Retourne un combo spécifique"""
        key = f"{creator}|{finisher}|{team}"
        return self.combos.get(key)
        
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS PHASE 2: MOMENTUM DNA
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_burst_scorers(self, min_burst_rate: float = 40) -> List[TeamMomentumDNA]:
        """Retourne les équipes BURST_SCORER"""
        return sorted(
            [m for m in self.team_momentum.values() if m.burst_rate >= min_burst_rate],
            key=lambda m: -m.burst_rate
        )
        
    def get_steady_scorers(self, max_burst_rate: float = 30) -> List[TeamMomentumDNA]:
        """Retourne les équipes STEADY_SCORER"""
        return sorted(
            [m for m in self.team_momentum.values() if m.burst_rate <= max_burst_rate],
            key=lambda m: m.avg_time_between_goals
        )
        
    def get_team_momentum(self, team: str) -> Optional[TeamMomentumDNA]:
        """Retourne le Momentum DNA d'une équipe"""
        return self.team_momentum.get(team)
        
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE MATCHUP PHASE 2
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_phase2(self, team: str) -> None:
        """Analyse complète Phase 2 pour une équipe"""
        print("=" * 80)
        print(f"🎯 ANALYSE PHASE 2: {team}")
        print("=" * 80)
        
        # Combos
        combos = self.get_team_combos(team, min_occurrences=2)
        print(f"\n🔗 CREATOR-FINISHER LINKS ({len(combos)} combos):")
        
        for c in combos[:5]:
            print(f"   [{c.combo_profile:15}] {c.creator:20} → {c.finisher}")
            print(f"   {c.occurrences}x | xG: {c.avg_xG:.2f} | 1H: {c.goals_1h} | 2H: {c.goals_2h}")
            print()
            
        # Momentum
        momentum = self.get_team_momentum(team)
        if momentum:
            print(f"\n⚡ MOMENTUM DNA:")
            print(f"   • Profil: {momentum.momentum_profile}")
            print(f"   • Matchs avec buts: {momentum.total_matches_with_goals}")
            print(f"   • Matchs avec 2+ buts: {momentum.matches_with_multiple_goals}")
            print(f"   • Total bursts: {momentum.total_bursts}")
            print(f"   • Burst Rate: {momentum.burst_rate:.0f}%")
            print(f"   • Écart moyen entre buts: {momentum.avg_time_between_goals:.0f} min")
            
            if momentum.best_bursts:
                print(f"\n   🔥 MEILLEURS BURSTS:")
                for b in momentum.best_bursts[:3]:
                    print(f"      • {b['burst']} ({b['gap']} min) vs {b['opponent']}")
                    
        # Recommandations
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS BETTING PHASE 2:")
        
        if combos:
            elite = [c for c in combos if c.combo_profile == "ELITE_COMBO"]
            if elite:
                print(f"\n   🔗 COMBO BETS (Assist + Goal):")
                for c in elite[:3]:
                    print(f"      ✅ {c.creator} Assist + {c.finisher} Goal")
                    print(f"         {c.occurrences}x cette saison | xG moy: {c.avg_xG:.2f}")
                    
        if momentum and momentum.momentum_profile == "BURST_SCORER":
            print(f"\n   ⚡ LIVE BETTING:")
            print(f"      ✅ Si {team} marque → BACK Next Goal {team} (BURST_SCORER)")
            print(f"      ✅ Burst Rate: {momentum.burst_rate:.0f}% des matchs avec 2+ buts")
            
        elif momentum and momentum.momentum_profile == "STEADY_SCORER":
            print(f"\n   ⚡ LIVE BETTING:")
            print(f"      ⚠️ {team} = STEADY_SCORER (écart moyen {momentum.avg_time_between_goals:.0f} min)")
            print(f"      ⚠️ Moins de valeur sur Next Goal immédiat")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = AttackDataLoaderV53Phase2()
    loader.load_all()
    
    print("\n" + "=" * 80)
    print("🧪 TEST: ANALYSE LIVERPOOL")
    print("=" * 80)
    
    loader.analyze_phase2("Liverpool")
    
    print("\n" + "=" * 80)
    print("🧪 TEST: ANALYSE BAYERN MUNICH")
    print("=" * 80)
    
    loader.analyze_phase2("Bayern Munich")

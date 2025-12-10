"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V5.5 PHASE 4 - HEDGE FUND GRADE                       ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  NOUVELLE DIMENSION PHASE 4:                                                 ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🌤️ EXTERNAL FACTORS DNA:                                                   ║
║     • Horaires: LUNCH (12-15h), AFTERNOON (15-19h), PRIME_TIME (19-24h)     ║
║     • Performance différentielle selon le créneau                            ║
║     • Profils: PRIME_TIME_BEAST, AFTERNOON_SPECIALIST, LUNCH_WARRIOR        ║
║     • Edge: Bayern +1.55 buts/match le soir → BACK Over en Prime Time       ║
║                                                                              ║
║  HÉRITE DE: loader_v5_4_phase3.py (Phase 1 + 2 + 3)                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import json

import sys
sys.path.insert(0, '/home/Mon_ps')

from agents.attack_v1.data.loader_v5_4_phase3 import (
    AttackDataLoaderV54Phase3,
    FirstGoalImpactDNA,
    GameStateDNA
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# EXTERNAL FACTORS DNA - HORAIRES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExternalFactorsDNA:
    """
    ADN des facteurs externes - UNIQUE par équipe
    
    Concept: Certaines équipes performent différemment selon les conditions.
    
    Catégories horaires:
    • LUNCH (12h-15h): Matchs du midi (Liga, Serie A)
    • AFTERNOON (15h-19h): Classique EPL (15h, 17h30)
    • PRIME_TIME (19h-24h): Soirée, Champions League, gros matchs
    
    Profils:
    • PRIME_TIME_BEAST: Bien meilleur le soir (+1.0 delta)
    • AFTERNOON_SPECIALIST: Meilleur l'après-midi
    • LUNCH_WARRIOR: Meilleur le midi
    • CONSISTENT: Stable peu importe l'heure
    
    Edge:
    • Bayern PRIME_TIME_BEAST: +1.55 buts/match le soir → BACK Over 3.5 en soirée
    • Eintracht AFTERNOON_SPECIALIST: -1.89 delta → BACK Over l'après-midi, LAY le soir
    """
    team: str = ""
    
    # Statistiques brutes par créneau
    lunch_goals: int = 0          # 12h-15h
    lunch_matches: int = 0
    afternoon_goals: int = 0      # 15h-19h
    afternoon_matches: int = 0
    prime_time_goals: int = 0     # 19h-24h
    prime_time_matches: int = 0
    
    # Early (10h-12h) - bonus si data
    early_goals: int = 0
    early_matches: int = 0
    
    # Moyennes
    lunch_avg: float = 0.0
    afternoon_avg: float = 0.0
    prime_time_avg: float = 0.0
    early_avg: float = 0.0
    overall_avg: float = 0.0
    
    # Deltas (différence vs moyenne globale)
    lunch_delta: float = 0.0
    afternoon_delta: float = 0.0
    prime_time_delta: float = 0.0
    
    # Best/Worst slots
    best_slot: str = ""
    worst_slot: str = ""
    best_slot_avg: float = 0.0
    worst_slot_avg: float = 0.0
    max_delta: float = 0.0  # Différence entre best et worst
    
    # Profil
    schedule_profile: str = ""
    
    # Détails par créneau (pour analyse)
    slot_details: Dict = field(default_factory=dict)
    
    def calculate(self) -> None:
        """Calcule les métriques External Factors"""
        
        # Moyennes par créneau
        if self.lunch_matches > 0:
            self.lunch_avg = self.lunch_goals / self.lunch_matches
        if self.afternoon_matches > 0:
            self.afternoon_avg = self.afternoon_goals / self.afternoon_matches
        if self.prime_time_matches > 0:
            self.prime_time_avg = self.prime_time_goals / self.prime_time_matches
        if self.early_matches > 0:
            self.early_avg = self.early_goals / self.early_matches
            
        # Moyenne globale
        total_goals = self.lunch_goals + self.afternoon_goals + self.prime_time_goals + self.early_goals
        total_matches = self.lunch_matches + self.afternoon_matches + self.prime_time_matches + self.early_matches
        
        if total_matches > 0:
            self.overall_avg = total_goals / total_matches
            
        # Deltas vs moyenne globale
        if self.overall_avg > 0:
            self.lunch_delta = self.lunch_avg - self.overall_avg
            self.afternoon_delta = self.afternoon_avg - self.overall_avg
            self.prime_time_delta = self.prime_time_avg - self.overall_avg
            
        # Identifier best/worst slots (min 2 matchs pour être significatif)
        slots = []
        if self.lunch_matches >= 2:
            slots.append(('LUNCH', self.lunch_avg, self.lunch_matches))
        if self.afternoon_matches >= 2:
            slots.append(('AFTERNOON', self.afternoon_avg, self.afternoon_matches))
        if self.prime_time_matches >= 2:
            slots.append(('PRIME_TIME', self.prime_time_avg, self.prime_time_matches))
            
        if len(slots) >= 2:
            slots.sort(key=lambda x: -x[1])  # Tri décroissant par moyenne
            
            self.best_slot = slots[0][0]
            self.best_slot_avg = slots[0][1]
            self.worst_slot = slots[-1][0]
            self.worst_slot_avg = slots[-1][1]
            self.max_delta = self.best_slot_avg - self.worst_slot_avg
            
        # Classification
        self._classify()
        
        # Détails pour export
        self.slot_details = {
            'LUNCH': {'goals': self.lunch_goals, 'matches': self.lunch_matches, 'avg': self.lunch_avg, 'delta': self.lunch_delta},
            'AFTERNOON': {'goals': self.afternoon_goals, 'matches': self.afternoon_matches, 'avg': self.afternoon_avg, 'delta': self.afternoon_delta},
            'PRIME_TIME': {'goals': self.prime_time_goals, 'matches': self.prime_time_matches, 'avg': self.prime_time_avg, 'delta': self.prime_time_delta}
        }
        
    def _classify(self) -> None:
        """Classifie le profil horaire"""
        
        # Besoin d'au moins 2 créneaux avec data
        slots_with_data = sum([
            1 if self.lunch_matches >= 2 else 0,
            1 if self.afternoon_matches >= 2 else 0,
            1 if self.prime_time_matches >= 2 else 0
        ])
        
        if slots_with_data < 2:
            self.schedule_profile = "INSUFFICIENT_DATA"
            return
            
        # Classification basée sur le delta max
        if self.max_delta < 0.5:
            self.schedule_profile = "CONSISTENT"
        elif self.best_slot == "PRIME_TIME" and self.prime_time_delta >= 0.5:
            self.schedule_profile = "PRIME_TIME_BEAST"
        elif self.best_slot == "AFTERNOON" and self.afternoon_delta >= 0.5:
            self.schedule_profile = "AFTERNOON_SPECIALIST"
        elif self.best_slot == "LUNCH" and self.lunch_delta >= 0.5:
            self.schedule_profile = "LUNCH_WARRIOR"
        elif self.worst_slot == "PRIME_TIME" and self.prime_time_delta <= -0.5:
            self.schedule_profile = "PRIME_TIME_WEAK"
        elif self.worst_slot == "AFTERNOON" and self.afternoon_delta <= -0.5:
            self.schedule_profile = "AFTERNOON_WEAK"
        else:
            self.schedule_profile = "SLIGHT_PREFERENCE"


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V5.5 PHASE 4
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV55Phase4(AttackDataLoaderV54Phase3):
    """
    Loader V5.5 PHASE 4 - HEDGE FUND GRADE
    
    Hérite de V5.4 (Phase 1 + 2 + 3) et ajoute:
    • External Factors DNA (horaires)
    
    PHILOSOPHIE: Chaque équipe = ADN UNIQUE = Empreinte digitale
    """
    
    def __init__(self):
        super().__init__()
        
        # Phase 4 data
        self.external_factors_dna: Dict[str, ExternalFactorsDNA] = {}
        
    def load_all(self) -> None:
        """Charge tout + Phase 4"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V5.5 PHASE 4 - HEDGE FUND GRADE")
        print("=" * 80)
        
        # Phase 1: V5.2 (NP-Clinical + xGChain)
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
        
        # Phase 3: First Goal Impact + Game State
        print("\n" + "─" * 80)
        print("🚀 PHASE 3: FIRST GOAL IMPACT + GAME STATE DNA")
        print("─" * 80)
        self._reconstruct_matches()
        self._build_first_goal_impact_dna()
        self._build_game_state_dna()
        
        # Phase 4: External Factors
        print("\n" + "─" * 80)
        print("🚀 PHASE 4: EXTERNAL FACTORS DNA (HORAIRES)")
        print("─" * 80)
        self._build_external_factors_dna()
        
        self._print_phase4_insights()
        
    def _get_time_slot(self, hour: int) -> str:
        """Retourne le créneau horaire"""
        if 10 <= hour < 12:
            return 'EARLY'
        elif 12 <= hour < 15:
            return 'LUNCH'
        elif 15 <= hour < 19:
            return 'AFTERNOON'
        elif 19 <= hour < 24:
            return 'PRIME_TIME'
        else:
            return 'OTHER'
            
    def _build_external_factors_dna(self) -> None:
        """Construit l'External Factors DNA pour chaque équipe"""
        print("\n🌤️ [PHASE 4.1] Construction External Factors DNA...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        with open(path) as f:
            goals = json.load(f)
            
        # Collecter les données par équipe et créneau
        team_data = defaultdict(lambda: {
            'EARLY': {'goals': 0, 'matches': set()},
            'LUNCH': {'goals': 0, 'matches': set()},
            'AFTERNOON': {'goals': 0, 'matches': set()},
            'PRIME_TIME': {'goals': 0, 'matches': set()}
        })
        
        for g in goals:
            date_str = g.get('date', '')
            match_id = g.get('match_id')
            team = g.get('scoring_team', '')
            
            if not date_str or not match_id or not team:
                continue
                
            try:
                dt = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                hour = dt.hour
                slot = self._get_time_slot(hour)
                
                if slot in team_data[team]:
                    team_data[team][slot]['goals'] += 1
                    team_data[team][slot]['matches'].add(match_id)
            except:
                pass
                
        # Créer le DNA pour chaque équipe
        for team, data in team_data.items():
            dna = ExternalFactorsDNA(team=team)
            
            dna.early_goals = data['EARLY']['goals']
            dna.early_matches = len(data['EARLY']['matches'])
            
            dna.lunch_goals = data['LUNCH']['goals']
            dna.lunch_matches = len(data['LUNCH']['matches'])
            
            dna.afternoon_goals = data['AFTERNOON']['goals']
            dna.afternoon_matches = len(data['AFTERNOON']['matches'])
            
            dna.prime_time_goals = data['PRIME_TIME']['goals']
            dna.prime_time_matches = len(data['PRIME_TIME']['matches'])
            
            dna.calculate()
            self.external_factors_dna[team] = dna
            
        print(f"   ✅ {len(self.external_factors_dna)} équipes avec External Factors DNA")
        
        # Stats
        profiles = defaultdict(int)
        for dna in self.external_factors_dna.values():
            profiles[dna.schedule_profile] += 1
            
        print(f"\n   📊 PROFILS HORAIRES:")
        for profile, count in sorted(profiles.items(), key=lambda x: -x[1]):
            print(f"      • {profile}: {count}")
            
    def _print_phase4_insights(self) -> None:
        """Affiche les insights Phase 4"""
        print("\n" + "─" * 80)
        print("📊 INSIGHTS PHASE 4 - EXTERNAL FACTORS")
        print("─" * 80)
        
        # Top PRIME_TIME_BEAST
        print("\n🌙 TOP PRIME_TIME_BEAST (meilleurs le soir):")
        prime_beasts = sorted(
            [d for d in self.external_factors_dna.values() 
             if d.schedule_profile == "PRIME_TIME_BEAST" or 
             (d.prime_time_delta >= 0.5 and d.prime_time_matches >= 2)],
            key=lambda x: -x.prime_time_delta
        )[:10]
        
        for d in prime_beasts:
            print(f"   • {d.team:25} | Soir: {d.prime_time_avg:.2f} | Global: {d.overall_avg:.2f} | Delta: +{d.prime_time_delta:.2f}")
            
        # Top AFTERNOON_SPECIALIST
        print("\n☀️ TOP AFTERNOON_SPECIALIST (meilleurs l'après-midi):")
        afternoon_specs = sorted(
            [d for d in self.external_factors_dna.values() 
             if d.schedule_profile == "AFTERNOON_SPECIALIST" or 
             (d.afternoon_delta >= 0.5 and d.afternoon_matches >= 2)],
            key=lambda x: -x.afternoon_delta
        )[:10]
        
        for d in afternoon_specs:
            print(f"   • {d.team:25} | Après-midi: {d.afternoon_avg:.2f} | Global: {d.overall_avg:.2f} | Delta: +{d.afternoon_delta:.2f}")
            
        # Top PRIME_TIME_WEAK (à éviter le soir)
        print("\n⚠️ TOP PRIME_TIME_WEAK (éviter le soir):")
        prime_weak = sorted(
            [d for d in self.external_factors_dna.values() 
             if d.prime_time_delta <= -0.5 and d.prime_time_matches >= 2],
            key=lambda x: x.prime_time_delta
        )[:10]
        
        for d in prime_weak:
            print(f"   • {d.team:25} | Soir: {d.prime_time_avg:.2f} | Global: {d.overall_avg:.2f} | Delta: {d.prime_time_delta:.2f}")
            
        # Équipes les plus CONSISTENT
        print("\n🎯 TOP CONSISTENT (stables peu importe l'heure):")
        consistent = sorted(
            [d for d in self.external_factors_dna.values() 
             if d.schedule_profile == "CONSISTENT" and d.max_delta < 0.3],
            key=lambda x: x.max_delta
        )[:10]
        
        for d in consistent:
            print(f"   • {d.team:25} | Delta max: {d.max_delta:.2f} | Best: {d.best_slot} ({d.best_slot_avg:.2f})")
            
        # Plus grandes différences (edge max)
        print("\n🔥 PLUS GRANDES DIFFÉRENCES (EDGE MAXIMUM):")
        max_diff = sorted(
            [d for d in self.external_factors_dna.values() if d.max_delta >= 1.0],
            key=lambda x: -x.max_delta
        )[:10]
        
        for d in max_diff:
            print(f"   • {d.team:25} | Best: {d.best_slot} ({d.best_slot_avg:.2f}) | Worst: {d.worst_slot} ({d.worst_slot_avg:.2f}) | Δ {d.max_delta:.2f}")
            
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS PHASE 4
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_external_factors_dna(self, team: str) -> Optional[ExternalFactorsDNA]:
        """Retourne l'External Factors DNA d'une équipe"""
        return self.external_factors_dna.get(team)
        
    def get_prime_time_beasts(self, min_delta: float = 0.5) -> List[ExternalFactorsDNA]:
        """Retourne les équipes PRIME_TIME_BEAST"""
        return sorted(
            [d for d in self.external_factors_dna.values() 
             if d.prime_time_delta >= min_delta and d.prime_time_matches >= 2],
            key=lambda x: -x.prime_time_delta
        )
        
    def get_afternoon_specialists(self, min_delta: float = 0.5) -> List[ExternalFactorsDNA]:
        """Retourne les équipes AFTERNOON_SPECIALIST"""
        return sorted(
            [d for d in self.external_factors_dna.values() 
             if d.afternoon_delta >= min_delta and d.afternoon_matches >= 2],
            key=lambda x: -x.afternoon_delta
        )
        
    def get_prime_time_weak(self, max_delta: float = -0.5) -> List[ExternalFactorsDNA]:
        """Retourne les équipes faibles le soir"""
        return sorted(
            [d for d in self.external_factors_dna.values() 
             if d.prime_time_delta <= max_delta and d.prime_time_matches >= 2],
            key=lambda x: x.prime_time_delta
        )
        
    def get_consistent_teams(self, max_diff: float = 0.3) -> List[ExternalFactorsDNA]:
        """Retourne les équipes CONSISTENT"""
        return sorted(
            [d for d in self.external_factors_dna.values() 
             if d.max_delta <= max_diff and d.schedule_profile != "INSUFFICIENT_DATA"],
            key=lambda x: x.max_delta
        )
        
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE COMPLÈTE PHASE 4
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_phase4(self, team: str) -> None:
        """Analyse complète Phase 4 pour une équipe"""
        print("=" * 80)
        print(f"🌤️ ANALYSE PHASE 4 - EXTERNAL FACTORS: {team}")
        print("=" * 80)
        
        ef_dna = self.get_external_factors_dna(team)
        if not ef_dna:
            print(f"❌ Pas de données External Factors pour {team}")
            return
            
        print(f"\n🌤️ EXTERNAL FACTORS DNA:")
        print(f"   • Profil: {ef_dna.schedule_profile}")
        print(f"   • Moyenne globale: {ef_dna.overall_avg:.2f} buts/match")
        
        print(f"\n   📊 PAR CRÉNEAU:")
        print(f"      🍽️ LUNCH (12h-15h):     {ef_dna.lunch_goals:2}G en {ef_dna.lunch_matches:2} matchs | {ef_dna.lunch_avg:.2f}/match | Delta: {ef_dna.lunch_delta:+.2f}")
        print(f"      ☀️ AFTERNOON (15h-19h): {ef_dna.afternoon_goals:2}G en {ef_dna.afternoon_matches:2} matchs | {ef_dna.afternoon_avg:.2f}/match | Delta: {ef_dna.afternoon_delta:+.2f}")
        print(f"      🌙 PRIME_TIME (19h-24h): {ef_dna.prime_time_goals:2}G en {ef_dna.prime_time_matches:2} matchs | {ef_dna.prime_time_avg:.2f}/match | Delta: {ef_dna.prime_time_delta:+.2f}")
        
        print(f"\n   🎯 BEST/WORST:")
        print(f"      ✅ Meilleur créneau: {ef_dna.best_slot} ({ef_dna.best_slot_avg:.2f} buts/match)")
        print(f"      ❌ Pire créneau: {ef_dna.worst_slot} ({ef_dna.worst_slot_avg:.2f} buts/match)")
        print(f"      📊 Différence: {ef_dna.max_delta:.2f} buts/match")
        
        # Recommandations
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS PHASE 4:")
        
        if ef_dna.schedule_profile == "PRIME_TIME_BEAST":
            print(f"   ✅ Match {team} en SOIRÉE (19h+) → BACK Over Team Goals")
            print(f"      Raison: +{ef_dna.prime_time_delta:.2f} buts/match le soir")
        elif ef_dna.schedule_profile == "PRIME_TIME_WEAK":
            print(f"   ⚠️ Match {team} en SOIRÉE (19h+) → LAY Over / BACK Under")
            print(f"      Raison: {ef_dna.prime_time_delta:.2f} buts/match le soir")
            
        if ef_dna.schedule_profile == "AFTERNOON_SPECIALIST":
            print(f"   ✅ Match {team} l'APRÈS-MIDI (15h-19h) → BACK Over Team Goals")
            print(f"      Raison: +{ef_dna.afternoon_delta:.2f} buts/match l'après-midi")
        elif ef_dna.afternoon_delta <= -0.5:
            print(f"   ⚠️ Match {team} l'APRÈS-MIDI → LAY Over")
            print(f"      Raison: {ef_dna.afternoon_delta:.2f} buts/match l'après-midi")
            
        if ef_dna.max_delta >= 1.0:
            print(f"\n   🔥 EDGE MAXIMUM ({ef_dna.max_delta:.2f} buts/match de différence):")
            print(f"      ✅ Parier {ef_dna.best_slot}: {ef_dna.best_slot_avg:.2f} buts/match")
            print(f"      ❌ Éviter {ef_dna.worst_slot}: {ef_dna.worst_slot_avg:.2f} buts/match")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = AttackDataLoaderV55Phase4()
    loader.load_all()
    
    print("\n" + "=" * 80)
    print("🧪 TEST: ANALYSE EXTERNAL FACTORS")
    print("=" * 80)
    
    for team in ["Bayern Munich", "Liverpool", "Eintracht Frankfurt"]:
        loader.analyze_phase4(team)
        print()

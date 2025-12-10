"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V5.4 PHASE 3 - HEDGE FUND GRADE                       ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  NOUVELLES DIMENSIONS PHASE 3:                                               ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🎯 FIRST GOAL IMPACT DNA:                                                   ║
║     • Comment l'équipe réagit selon QUI marque en premier                    ║
║     • win_rate_scoring_first, comeback_rate, collapse_rate                   ║
║     • Profils: FRONT_RUNNER, COMEBACK_KING, FRAGILE, RESILIENT               ║
║     • Edge: Liverpool COMEBACK_KING mené 1-0 → BACK Liverpool Win            ║
║                                                                              ║
║  🔥 GAME STATE DNA:                                                          ║
║     • Comportement selon le SCORE ACTUEL (mène/mené/égalité)                 ║
║     • leading_goals, trailing_goals, level_goals                             ║
║     • Profils: KILLER, SETTLER, COMEBACK_SPECIALIST, BALANCED                ║
║     • Edge Live: Bayern mène 2-0 → BACK Over (KILLER continue à marquer)     ║
║                                                                              ║
║  HÉRITE DE: loader_v5_3_phase2.py (Phase 1 + Phase 2)                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import json

import sys
sys.path.insert(0, '/home/Mon_ps')

from agents.attack_v1.data.loader_v5_3_phase2 import (
    AttackDataLoaderV53Phase2,
    CreatorFinisherCombo,
    TeamMomentumDNA
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# FIRST GOAL IMPACT DNA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FirstGoalImpactDNA:
    """
    ADN de réaction au premier but - UNIQUE par équipe
    
    Concept: Comment l'équipe réagit psychologiquement selon qui marque en premier.
    
    Profils:
    • FRONT_RUNNER: Domine quand marque en premier (win_rate >= 80%)
    • COMEBACK_KING: Revient souvent quand mené (comeback_rate >= 40%)
    • FRAGILE: S'effondre quand mené (collapse_rate >= 60%)
    • RESILIENT: Stable peu importe le scénario
    
    Edge:
    • Liverpool COMEBACK_KING mené 1-0 à 60' → BACK Liverpool Win (value)
    • Everton FRAGILE mené 1-0 → BACK Opponent Win
    """
    team: str = ""
    
    # Statistiques brutes
    matches_scored_first: int = 0
    matches_conceded_first: int = 0
    total_matches: int = 0
    
    # Quand l'équipe marque en premier
    wins_after_scoring_first: int = 0
    draws_after_scoring_first: int = 0
    losses_after_scoring_first: int = 0
    goals_after_scoring_first: int = 0  # Buts marqués APRÈS avoir ouvert le score
    
    # Quand l'équipe encaisse en premier
    wins_after_conceding_first: int = 0
    draws_after_conceding_first: int = 0
    losses_after_conceding_first: int = 0
    goals_after_conceding_first: int = 0  # Buts marqués APRÈS avoir encaissé
    
    # Métriques clés
    win_rate_scoring_first: float = 0.0
    win_rate_conceding_first: float = 0.0
    comeback_rate: float = 0.0  # % de matchs gagnés/nuls après avoir encaissé premier
    collapse_rate: float = 0.0  # % de matchs perdus après avoir marqué premier
    killer_instinct: float = 0.0  # Buts marqués après avoir ouvert le score (moyenne)
    
    # Profil
    first_goal_profile: str = ""
    
    # Détails des matchs
    comeback_matches: List[Dict] = field(default_factory=list)
    collapse_matches: List[Dict] = field(default_factory=list)
    
    def calculate(self) -> None:
        """Calcule les métriques First Goal Impact"""
        self.total_matches = self.matches_scored_first + self.matches_conceded_first
        
        # Win rate quand marque en premier
        if self.matches_scored_first > 0:
            self.win_rate_scoring_first = (self.wins_after_scoring_first / self.matches_scored_first) * 100
            self.collapse_rate = (self.losses_after_scoring_first / self.matches_scored_first) * 100
            self.killer_instinct = self.goals_after_scoring_first / self.matches_scored_first
            
        # Win rate quand encaisse en premier
        if self.matches_conceded_first > 0:
            self.win_rate_conceding_first = (self.wins_after_conceding_first / self.matches_conceded_first) * 100
            # Comeback = win OU draw après avoir encaissé premier
            self.comeback_rate = ((self.wins_after_conceding_first + self.draws_after_conceding_first) / self.matches_conceded_first) * 100
            
        # Classification
        if self.win_rate_scoring_first >= 80 and self.matches_scored_first >= 3:
            self.first_goal_profile = "FRONT_RUNNER"
        elif self.comeback_rate >= 50 and self.matches_conceded_first >= 3:
            self.first_goal_profile = "COMEBACK_KING"
        elif self.collapse_rate >= 30 and self.matches_scored_first >= 3:
            self.first_goal_profile = "FRAGILE"
        elif self.win_rate_conceding_first <= 10 and self.matches_conceded_first >= 3:
            self.first_goal_profile = "MENTALLY_WEAK"
        else:
            self.first_goal_profile = "RESILIENT"


# ═══════════════════════════════════════════════════════════════════════════════
# GAME STATE DNA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GameStateDNA:
    """
    ADN de comportement selon le score - UNIQUE par équipe
    
    Concept: Comment l'équipe joue selon qu'elle MÈNE, est MENÉE, ou à ÉGALITÉ.
    
    Profils:
    • KILLER: Continue à marquer quand mène (leading_goals_per_match >= 1.0)
    • SETTLER: Se contente du score quand mène (leading_goals faibles)
    • COMEBACK_SPECIALIST: Marque beaucoup quand mené
    • LEVEL_SCORER: Marque principalement à égalité
    
    Edge Live:
    • Bayern (KILLER) mène 2-0 à 60' → BACK Over 3.5 (va continuer)
    • Atlético (SETTLER) mène 1-0 à 60' → LAY Over 2.5 (va défendre)
    """
    team: str = ""
    
    # Statistiques brutes
    total_goals: int = 0
    total_matches: int = 0
    
    # Buts par game state
    goals_when_leading: int = 0      # Buts marqués quand l'équipe MÈNE
    goals_when_trailing: int = 0     # Buts marqués quand l'équipe est MENÉE
    goals_when_level: int = 0        # Buts marqués à ÉGALITÉ (0-0, 1-1, etc.)
    
    # Buts encaissés par game state
    conceded_when_leading: int = 0   # Buts encaissés quand MÈNE
    conceded_when_trailing: int = 0  # Buts encaissés quand MENÉ
    conceded_when_level: int = 0     # Buts encaissés à ÉGALITÉ
    
    # Temps passé dans chaque state (approximatif via goals)
    matches_with_lead: int = 0
    matches_when_trailing: int = 0
    
    # Métriques clés
    pct_goals_leading: float = 0.0
    pct_goals_trailing: float = 0.0
    pct_goals_level: float = 0.0
    
    leading_goal_rate: float = 0.0      # Buts/match quand mène
    trailing_goal_rate: float = 0.0     # Buts/match quand mené
    level_goal_rate: float = 0.0        # Buts/match à égalité
    
    killer_index: float = 0.0           # goals_leading / conceded_leading
    resilience_index: float = 0.0       # goals_trailing / total_trailing_situations
    
    # Profil
    game_state_profile: str = ""
    
    def calculate(self) -> None:
        """Calcule les métriques Game State"""
        if self.total_goals > 0:
            self.pct_goals_leading = (self.goals_when_leading / self.total_goals) * 100
            self.pct_goals_trailing = (self.goals_when_trailing / self.total_goals) * 100
            self.pct_goals_level = (self.goals_when_level / self.total_goals) * 100
            
        if self.matches_with_lead > 0:
            self.leading_goal_rate = self.goals_when_leading / self.matches_with_lead
            
        if self.matches_when_trailing > 0:
            self.trailing_goal_rate = self.goals_when_trailing / self.matches_when_trailing
            
        if self.total_matches > 0:
            self.level_goal_rate = self.goals_when_level / self.total_matches
            
        # Killer Index: ratio buts marqués / encaissés quand on mène
        if self.conceded_when_leading > 0:
            self.killer_index = self.goals_when_leading / self.conceded_when_leading
        elif self.goals_when_leading > 0:
            self.killer_index = self.goals_when_leading * 2  # Bonus si 0 encaissé
            
        # Resilience Index
        if self.matches_when_trailing > 0:
            self.resilience_index = self.goals_when_trailing / self.matches_when_trailing
            
        # Classification
        if self.pct_goals_leading >= 35 and self.killer_index >= 2.0:
            self.game_state_profile = "KILLER"
        elif self.pct_goals_leading >= 25 and self.killer_index <= 0.5:
            self.game_state_profile = "SETTLER"
        elif self.pct_goals_trailing >= 30 and self.resilience_index >= 1.0:
            self.game_state_profile = "COMEBACK_SPECIALIST"
        elif self.pct_goals_level >= 50:
            self.game_state_profile = "LEVEL_SCORER"
        else:
            self.game_state_profile = "BALANCED"


# ═══════════════════════════════════════════════════════════════════════════════
# MATCH RECONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReconstructedMatch:
    """Match reconstruit à partir des buts"""
    match_id: int = 0
    date: str = ""
    home_team: str = ""
    away_team: str = ""
    
    # Score final
    final_home: int = 0
    final_away: int = 0
    
    # Score mi-temps
    halftime_home: int = 0
    halftime_away: int = 0
    
    # Premier but
    first_goal_team: str = ""
    first_goal_minute: int = 0
    first_goal_scorer: str = ""
    
    # Timeline des buts
    goals_timeline: List[Dict] = field(default_factory=list)
    
    # Résultat par équipe
    home_result: str = ""  # W, D, L
    away_result: str = ""  # W, D, L


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V5.4 PHASE 3
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV54Phase3(AttackDataLoaderV53Phase2):
    """
    Loader V5.4 PHASE 3 - HEDGE FUND GRADE
    
    Hérite de V5.3 (Phase 1 + 2) et ajoute:
    • First Goal Impact DNA (réaction psychologique)
    • Game State DNA (comportement selon le score)
    
    PHILOSOPHIE: Chaque équipe = ADN UNIQUE = Empreinte digitale
    """
    
    def __init__(self):
        super().__init__()
        
        # Phase 3 data
        self.reconstructed_matches: Dict[int, ReconstructedMatch] = {}
        self.first_goal_dna: Dict[str, FirstGoalImpactDNA] = {}
        self.game_state_dna: Dict[str, GameStateDNA] = {}
        
    def load_all(self) -> None:
        """Charge tout + Phase 3"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V5.4 PHASE 3 - HEDGE FUND GRADE")
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
        
        self._print_phase3_insights()
        
    def _reconstruct_matches(self) -> None:
        """Reconstruit les matchs à partir des buts"""
        print("\n📊 [PHASE 3.0] Reconstruction des matchs...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        with open(path) as f:
            goals = json.load(f)
            
        # Grouper les buts par match
        matches_goals = defaultdict(list)
        for g in goals:
            match_id = g.get('match_id')
            if match_id:
                matches_goals[match_id].append(g)
                
        # Reconstruire chaque match
        for match_id, match_goals in matches_goals.items():
            # Trier par minute
            match_goals.sort(key=lambda x: x.get('minute', 0))
            
            # Identifier home/away teams
            home_team = None
            away_team = None
            for g in match_goals:
                if g.get('home_away') == 'h':
                    home_team = g.get('scoring_team')
                    away_team = g.get('conceding_team')
                    break
                elif g.get('home_away') == 'a':
                    away_team = g.get('scoring_team')
                    home_team = g.get('conceding_team')
                    break
                    
            if not home_team or not away_team:
                continue
                
            # Reconstruire le match
            match = ReconstructedMatch(
                match_id=match_id,
                date=match_goals[0].get('date', ''),
                home_team=home_team,
                away_team=away_team
            )
            
            # Calculer le score progressif
            home_score = 0
            away_score = 0
            
            for g in match_goals:
                minute = g.get('minute', 0)
                scoring_team = g.get('scoring_team')
                scorer = g.get('scorer')
                home_away = g.get('home_away')
                
                # Score AVANT ce but
                score_before_home = home_score
                score_before_away = away_score
                
                # Mettre à jour le score
                if home_away == 'h':
                    home_score += 1
                else:
                    away_score += 1
                    
                # Timeline
                match.goals_timeline.append({
                    'minute': minute,
                    'scorer': scorer,
                    'team': scoring_team,
                    'home_away': home_away,
                    'score_before': f"{score_before_home}-{score_before_away}",
                    'score_after': f"{home_score}-{away_score}",
                    'game_state_before': self._get_game_state(score_before_home, score_before_away, home_away)
                })
                
                # Premier but
                if not match.first_goal_team:
                    match.first_goal_team = scoring_team
                    match.first_goal_minute = minute
                    match.first_goal_scorer = scorer
                    
                # Score mi-temps
                if minute <= 45:
                    match.halftime_home = home_score
                    match.halftime_away = away_score
                    
            # Score final
            match.final_home = home_score
            match.final_away = away_score
            
            # Résultats
            if home_score > away_score:
                match.home_result = 'W'
                match.away_result = 'L'
            elif home_score < away_score:
                match.home_result = 'L'
                match.away_result = 'W'
            else:
                match.home_result = 'D'
                match.away_result = 'D'
                
            self.reconstructed_matches[match_id] = match
            
        print(f"   ✅ {len(self.reconstructed_matches)} matchs reconstruits")
        
    def _get_game_state(self, home_score: int, away_score: int, perspective: str) -> str:
        """Retourne le game state du point de vue de l'équipe qui marque"""
        if perspective == 'h':
            if home_score > away_score:
                return 'LEADING'
            elif home_score < away_score:
                return 'TRAILING'
            else:
                return 'LEVEL'
        else:
            if away_score > home_score:
                return 'LEADING'
            elif away_score < home_score:
                return 'TRAILING'
            else:
                return 'LEVEL'
                
    def _build_first_goal_impact_dna(self) -> None:
        """Construit le First Goal Impact DNA pour chaque équipe"""
        print("\n🎯 [PHASE 3.1] Construction First Goal Impact DNA...")
        
        team_data = defaultdict(lambda: {
            'scored_first': [],
            'conceded_first': []
        })
        
        for match in self.reconstructed_matches.values():
            if not match.first_goal_team:
                continue
                
            home_team = match.home_team
            away_team = match.away_team
            
            # Qui a marqué en premier?
            if match.first_goal_team == home_team:
                # Home a marqué en premier
                team_data[home_team]['scored_first'].append({
                    'match_id': match.match_id,
                    'opponent': away_team,
                    'result': match.home_result,
                    'final_score': f"{match.final_home}-{match.final_away}",
                    'goals_after': match.final_home - 1,  # Buts après le premier
                    'minute': match.first_goal_minute
                })
                team_data[away_team]['conceded_first'].append({
                    'match_id': match.match_id,
                    'opponent': home_team,
                    'result': match.away_result,
                    'final_score': f"{match.final_away}-{match.final_home}",
                    'goals_after': match.final_away,  # Tous les buts sont après
                    'minute': match.first_goal_minute
                })
            else:
                # Away a marqué en premier
                team_data[away_team]['scored_first'].append({
                    'match_id': match.match_id,
                    'opponent': home_team,
                    'result': match.away_result,
                    'final_score': f"{match.final_away}-{match.final_home}",
                    'goals_after': match.final_away - 1,
                    'minute': match.first_goal_minute
                })
                team_data[home_team]['conceded_first'].append({
                    'match_id': match.match_id,
                    'opponent': away_team,
                    'result': match.home_result,
                    'final_score': f"{match.final_home}-{match.final_away}",
                    'goals_after': match.final_home,
                    'minute': match.first_goal_minute
                })
                
        # Créer le DNA pour chaque équipe
        for team, data in team_data.items():
            dna = FirstGoalImpactDNA(team=team)
            
            # Quand l'équipe marque en premier
            dna.matches_scored_first = len(data['scored_first'])
            for m in data['scored_first']:
                if m['result'] == 'W':
                    dna.wins_after_scoring_first += 1
                elif m['result'] == 'D':
                    dna.draws_after_scoring_first += 1
                else:
                    dna.losses_after_scoring_first += 1
                    dna.collapse_matches.append(m)
                dna.goals_after_scoring_first += m['goals_after']
                
            # Quand l'équipe encaisse en premier
            dna.matches_conceded_first = len(data['conceded_first'])
            for m in data['conceded_first']:
                if m['result'] == 'W':
                    dna.wins_after_conceding_first += 1
                    dna.comeback_matches.append(m)
                elif m['result'] == 'D':
                    dna.draws_after_conceding_first += 1
                else:
                    dna.losses_after_conceding_first += 1
                dna.goals_after_conceding_first += m['goals_after']
                
            dna.calculate()
            self.first_goal_dna[team] = dna
            
        print(f"   ✅ {len(self.first_goal_dna)} équipes avec First Goal Impact DNA")
        
        # Stats
        profiles = defaultdict(int)
        for dna in self.first_goal_dna.values():
            profiles[dna.first_goal_profile] += 1
            
        print(f"\n   📊 PROFILS FIRST GOAL IMPACT:")
        for profile, count in sorted(profiles.items(), key=lambda x: -x[1]):
            print(f"      • {profile}: {count}")
            
    def _build_game_state_dna(self) -> None:
        """Construit le Game State DNA pour chaque équipe"""
        print("\n🔥 [PHASE 3.2] Construction Game State DNA...")
        
        team_data = defaultdict(lambda: {
            'total_goals': 0,
            'total_matches': 0,
            'goals_leading': 0,
            'goals_trailing': 0,
            'goals_level': 0,
            'conceded_leading': 0,
            'conceded_trailing': 0,
            'conceded_level': 0,
            'matches_with_lead': set(),
            'matches_when_trailing': set()
        })
        
        for match in self.reconstructed_matches.values():
            home_team = match.home_team
            away_team = match.away_team
            
            # Compter les matchs
            team_data[home_team]['total_matches'] += 1
            team_data[away_team]['total_matches'] += 1
            
            # Analyser chaque but
            home_score = 0
            away_score = 0
            
            for goal in match.goals_timeline:
                minute = goal.get('minute', 0)
                home_away = goal.get('home_away')
                game_state = goal.get('game_state_before')
                
                if home_away == 'h':
                    # But pour home
                    scoring_team = home_team
                    conceding_team = away_team
                    home_score += 1
                else:
                    # But pour away
                    scoring_team = away_team
                    conceding_team = home_team
                    away_score += 1
                    
                team_data[scoring_team]['total_goals'] += 1
                
                # Game state du point de vue de l'équipe qui marque
                if game_state == 'LEADING':
                    team_data[scoring_team]['goals_leading'] += 1
                    team_data[conceding_team]['conceded_leading'] += 1
                    team_data[scoring_team]['matches_with_lead'].add(match.match_id)
                elif game_state == 'TRAILING':
                    team_data[scoring_team]['goals_trailing'] += 1
                    team_data[conceding_team]['conceded_trailing'] += 1
                    team_data[scoring_team]['matches_when_trailing'].add(match.match_id)
                else:  # LEVEL
                    team_data[scoring_team]['goals_level'] += 1
                    team_data[conceding_team]['conceded_level'] += 1
                    
            # Tracker les situations de lead/trailing
            if match.final_home > match.final_away:
                team_data[home_team]['matches_with_lead'].add(match.match_id)
            elif match.final_away > match.final_home:
                team_data[away_team]['matches_with_lead'].add(match.match_id)
                
        # Créer le DNA pour chaque équipe
        for team, data in team_data.items():
            dna = GameStateDNA(
                team=team,
                total_goals=data['total_goals'],
                total_matches=data['total_matches'],
                goals_when_leading=data['goals_leading'],
                goals_when_trailing=data['goals_trailing'],
                goals_when_level=data['goals_level'],
                conceded_when_leading=data['conceded_leading'],
                conceded_when_trailing=data['conceded_trailing'],
                conceded_when_level=data['conceded_level'],
                matches_with_lead=len(data['matches_with_lead']),
                matches_when_trailing=len(data['matches_when_trailing'])
            )
            dna.calculate()
            self.game_state_dna[team] = dna
            
        print(f"   ✅ {len(self.game_state_dna)} équipes avec Game State DNA")
        
        # Stats
        profiles = defaultdict(int)
        for dna in self.game_state_dna.values():
            profiles[dna.game_state_profile] += 1
            
        print(f"\n   📊 PROFILS GAME STATE:")
        for profile, count in sorted(profiles.items(), key=lambda x: -x[1]):
            print(f"      • {profile}: {count}")
            
    def _print_phase3_insights(self) -> None:
        """Affiche les insights Phase 3"""
        print("\n" + "─" * 80)
        print("📊 INSIGHTS PHASE 3 - ADN PSYCHOLOGIQUE")
        print("─" * 80)
        
        # Top FRONT_RUNNER
        print("\n🏃 TOP FRONT_RUNNER (dominent quand marquent en premier):")
        front_runners = sorted(
            [d for d in self.first_goal_dna.values() 
             if d.first_goal_profile == "FRONT_RUNNER" and d.matches_scored_first >= 3],
            key=lambda x: -x.win_rate_scoring_first
        )[:10]
        
        for d in front_runners:
            print(f"   • {d.team:25} | Win Rate: {d.win_rate_scoring_first:.0f}% | {d.matches_scored_first} matchs")
            
        # Top COMEBACK_KING
        print("\n👑 TOP COMEBACK_KING (reviennent quand menés):")
        comeback_kings = sorted(
            [d for d in self.first_goal_dna.values() 
             if d.comeback_rate >= 40 and d.matches_conceded_first >= 3],
            key=lambda x: -x.comeback_rate
        )[:10]
        
        for d in comeback_kings:
            wins = d.wins_after_conceding_first
            draws = d.draws_after_conceding_first
            print(f"   • {d.team:25} | Comeback: {d.comeback_rate:.0f}% ({wins}W {draws}D) | {d.matches_conceded_first} matchs")
            
        # Top FRAGILE
        print("\n💔 TOP FRAGILE (s'effondrent quand menés):")
        fragile = sorted(
            [d for d in self.first_goal_dna.values() 
             if d.win_rate_conceding_first <= 20 and d.matches_conceded_first >= 3],
            key=lambda x: x.win_rate_conceding_first
        )[:10]
        
        for d in fragile:
            print(f"   • {d.team:25} | Win Rate mené: {d.win_rate_conceding_first:.0f}% | Losses: {d.losses_after_conceding_first}")
            
        # Top KILLER
        print("\n🔥 TOP KILLER (continuent à marquer en menant):")
        killers = sorted(
            [d for d in self.game_state_dna.values() 
             if d.game_state_profile == "KILLER" or d.pct_goals_leading >= 30],
            key=lambda x: -x.pct_goals_leading
        )[:10]
        
        for d in killers:
            print(f"   • {d.team:25} | {d.pct_goals_leading:.0f}% buts en menant | Killer Index: {d.killer_index:.1f}")
            
        # Top SETTLER
        print("\n🛡️ TOP SETTLER (se contentent du score):")
        settlers = sorted(
            [d for d in self.game_state_dna.values() 
             if d.pct_goals_leading <= 15 and d.matches_with_lead >= 3],
            key=lambda x: x.pct_goals_leading
        )[:10]
        
        for d in settlers:
            print(f"   • {d.team:25} | {d.pct_goals_leading:.0f}% buts en menant | {d.goals_when_leading}G en menant")
            
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS PHASE 3
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_first_goal_dna(self, team: str) -> Optional[FirstGoalImpactDNA]:
        """Retourne le First Goal Impact DNA d'une équipe"""
        return self.first_goal_dna.get(team)
        
    def get_game_state_dna(self, team: str) -> Optional[GameStateDNA]:
        """Retourne le Game State DNA d'une équipe"""
        return self.game_state_dna.get(team)
        
    def get_front_runners(self, min_win_rate: float = 75) -> List[FirstGoalImpactDNA]:
        """Retourne les équipes FRONT_RUNNER"""
        return sorted(
            [d for d in self.first_goal_dna.values() 
             if d.win_rate_scoring_first >= min_win_rate and d.matches_scored_first >= 3],
            key=lambda x: -x.win_rate_scoring_first
        )
        
    def get_comeback_kings(self, min_comeback_rate: float = 40) -> List[FirstGoalImpactDNA]:
        """Retourne les équipes COMEBACK_KING"""
        return sorted(
            [d for d in self.first_goal_dna.values() 
             if d.comeback_rate >= min_comeback_rate and d.matches_conceded_first >= 3],
            key=lambda x: -x.comeback_rate
        )
        
    def get_fragile_teams(self, max_win_rate: float = 20) -> List[FirstGoalImpactDNA]:
        """Retourne les équipes FRAGILE quand menées"""
        return sorted(
            [d for d in self.first_goal_dna.values() 
             if d.win_rate_conceding_first <= max_win_rate and d.matches_conceded_first >= 3],
            key=lambda x: x.win_rate_conceding_first
        )
        
    def get_killers(self, min_pct: float = 25) -> List[GameStateDNA]:
        """Retourne les équipes KILLER"""
        return sorted(
            [d for d in self.game_state_dna.values() 
             if d.pct_goals_leading >= min_pct],
            key=lambda x: -x.pct_goals_leading
        )
        
    def get_settlers(self, max_pct: float = 15) -> List[GameStateDNA]:
        """Retourne les équipes SETTLER"""
        return sorted(
            [d for d in self.game_state_dna.values() 
             if d.pct_goals_leading <= max_pct and d.matches_with_lead >= 3],
            key=lambda x: x.pct_goals_leading
        )
        
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE COMPLÈTE PHASE 3
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_phase3(self, team: str) -> None:
        """Analyse complète Phase 3 pour une équipe"""
        print("=" * 80)
        print(f"🧠 ANALYSE PHASE 3 - ADN PSYCHOLOGIQUE: {team}")
        print("=" * 80)
        
        # First Goal Impact
        fg_dna = self.get_first_goal_dna(team)
        if fg_dna:
            print(f"\n🎯 FIRST GOAL IMPACT DNA:")
            print(f"   • Profil: {fg_dna.first_goal_profile}")
            print(f"\n   📈 Quand {team} MARQUE en premier ({fg_dna.matches_scored_first} matchs):")
            print(f"      Win Rate: {fg_dna.win_rate_scoring_first:.0f}%")
            print(f"      W/D/L: {fg_dna.wins_after_scoring_first}/{fg_dna.draws_after_scoring_first}/{fg_dna.losses_after_scoring_first}")
            print(f"      Killer Instinct: {fg_dna.killer_instinct:.1f} buts après")
            print(f"      Collapse Rate: {fg_dna.collapse_rate:.0f}%")
            
            print(f"\n   📉 Quand {team} ENCAISSE en premier ({fg_dna.matches_conceded_first} matchs):")
            print(f"      Win Rate: {fg_dna.win_rate_conceding_first:.0f}%")
            print(f"      Comeback Rate: {fg_dna.comeback_rate:.0f}%")
            print(f"      W/D/L: {fg_dna.wins_after_conceding_first}/{fg_dna.draws_after_conceding_first}/{fg_dna.losses_after_conceding_first}")
            
            if fg_dna.comeback_matches:
                print(f"\n   👑 COMEBACKS:")
                for m in fg_dna.comeback_matches[:3]:
                    print(f"      • vs {m['opponent']} ({m['final_score']}) - encaissé {m['minute']}'")
                    
        # Game State DNA
        gs_dna = self.get_game_state_dna(team)
        if gs_dna:
            print(f"\n🔥 GAME STATE DNA:")
            print(f"   • Profil: {gs_dna.game_state_profile}")
            print(f"\n   📊 Distribution des {gs_dna.total_goals} buts:")
            print(f"      En menant:  {gs_dna.goals_when_leading:2}G ({gs_dna.pct_goals_leading:.0f}%)")
            print(f"      En étant mené: {gs_dna.goals_when_trailing:2}G ({gs_dna.pct_goals_trailing:.0f}%)")
            print(f"      À égalité:  {gs_dna.goals_when_level:2}G ({gs_dna.pct_goals_level:.0f}%)")
            print(f"\n   🎯 Indices:")
            print(f"      Killer Index: {gs_dna.killer_index:.2f}")
            print(f"      Resilience Index: {gs_dna.resilience_index:.2f}")
            
        # Recommandations
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS PHASE 3:")
        
        if fg_dna:
            if fg_dna.first_goal_profile == "FRONT_RUNNER":
                print(f"   ✅ Si {team} marque en premier → BACK {team} Win (Win Rate {fg_dna.win_rate_scoring_first:.0f}%)")
            elif fg_dna.first_goal_profile == "COMEBACK_KING":
                print(f"   ✅ Si {team} mené → BACK {team} Draw/Win (Comeback {fg_dna.comeback_rate:.0f}%)")
            elif fg_dna.first_goal_profile == "FRAGILE":
                print(f"   ⚠️ Si {team} mené → LAY {team} (Win Rate mené: {fg_dna.win_rate_conceding_first:.0f}%)")
                
        if gs_dna:
            if gs_dna.game_state_profile == "KILLER":
                print(f"   ✅ LIVE: Si {team} mène → BACK Over (KILLER, {gs_dna.pct_goals_leading:.0f}% buts en menant)")
            elif gs_dna.game_state_profile == "SETTLER":
                print(f"   ⚠️ LIVE: Si {team} mène → LAY Over (SETTLER, seulement {gs_dna.pct_goals_leading:.0f}% buts en menant)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = AttackDataLoaderV54Phase3()
    loader.load_all()
    
    print("\n" + "=" * 80)
    print("🧪 TEST: ANALYSE LIVERPOOL")
    print("=" * 80)
    loader.analyze_phase3("Liverpool")
    
    print("\n" + "=" * 80)
    print("🧪 TEST: ANALYSE BAYERN MUNICH")
    print("=" * 80)
    loader.analyze_phase3("Bayern Munich")

"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM BACKTESTER QUANT 2.0                                       ║
║                                                                                       ║
║  OBJECTIF: Passer de "statisticien amateur" à "Quant Hedge Fund Grade"                ║
║                                                                                       ║
║  MÉTHODOLOGIE SCIENTIFIQUE:                                                           ║
║  ─────────────────────────────────────────────────────────────────────────────────── ║
║  1. Pour CHAQUE équipe (99 équipes):                                                 ║
║     a. Charger TOUS ses matchs (home + away)                                          ║
║     b. Appliquer TOUTES les stratégies à chaque match                                 ║
║     c. Calculer P&L, WR, ROI par stratégie                                           ║
║                                                                                       ║
║  2. STRATÉGIES TESTÉES:                                                              ║
║     • Groupe A: 20 Scénarios Quantum (ADCM + Friction + DNA)                         ║
║     • Groupe B: Stratégies empiriques (EDGE_HIGH, CONVERGENCE_OVER_MC, etc.)         ║
║     • Groupe C: Marchés spécifiques (Over 2.5, BTTS, etc.)                           ║
║                                                                                       ║
║  3. OUTPUT:                                                                           ║
║     • Matrice 99 équipes × N stratégies                                              ║
║     • Meilleure stratégie PAR ÉQUIPE                                                 ║
║     • Analyse des pertes (xG-based = malchance vs bad analysis)                      ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import json
import math


# ═══════════════════════════════════════════════════════════════════════════════════════
# STRATÉGIES À TESTER
# ═══════════════════════════════════════════════════════════════════════════════════════

class StrategyFamily(Enum):
    """Familles de stratégies"""
    QUANTUM_SCENARIOS = "quantum_scenarios"  # Les 20 scénarios
    EMPIRICAL = "empirical"  # Stratégies validées par audit
    MARKET_SPECIFIC = "market_specific"  # Marchés purs
    HYBRID = "hybrid"  # Combinaisons


@dataclass
class Strategy:
    """Définition d'une stratégie"""
    id: str
    name: str
    family: StrategyFamily
    market_type: str  # over_25, btts_yes, home_win, etc.
    conditions: Dict[str, Any] = field(default_factory=dict)
    min_edge: float = 0.0
    description: str = ""
    
    def matches_conditions(self, match_context: Dict) -> Tuple[bool, float]:
        """Vérifie si la stratégie s'applique au contexte du match"""
        raise NotImplementedError("Doit être implémenté par les sous-classes")


# ═══════════════════════════════════════════════════════════════════════════════════════
# CATALOGUE DES STRATÉGIES
# ═══════════════════════════════════════════════════════════════════════════════════════

def get_all_strategies() -> Dict[str, Strategy]:
    """
    Retourne TOUTES les stratégies à backtester.
    Basé sur l'audit QUANT 2.0 et les 20 scénarios.
    """
    strategies = {}
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE A: STRATÉGIES EMPIRIQUES (validées par l'audit 99 équipes)
    # ─────────────────────────────────────────────────────────────────────────────
    
    # Ces stratégies ont été découvertes comme les meilleures pour certaines équipes
    strategies["EDGE_HIGH_5"] = Strategy(
        id="EDGE_HIGH_5",
        name="Edge Élevé (>5%)",
        family=StrategyFamily.EMPIRICAL,
        market_type="best_edge",  # Marché avec le meilleur edge
        conditions={"min_edge": 5.0},
        min_edge=5.0,
        description="Parier uniquement quand l'edge calculé > 5%"
    )
    
    strategies["DIAMOND_SNIPER_30"] = Strategy(
        id="DIAMOND_SNIPER_30",
        name="Diamond Sniper (Score 30+)",
        family=StrategyFamily.EMPIRICAL,
        market_type="multi",  # Multi-markets
        conditions={"min_diamond_score": 30},
        description="Stratégie V13 Multi-Strike pour scores élevés"
    )
    
    strategies["CONVERGENCE_OVER_MC"] = Strategy(
        id="CONVERGENCE_OVER_MC",
        name="Convergence Over + Monte Carlo",
        family=StrategyFamily.EMPIRICAL,
        market_type="over_25",
        conditions={"mc_over_prob": 0.55, "friction_high": True},
        description="Over 2.5 validé par Monte Carlo + Friction élevée"
    )
    
    strategies["QUANT_BEST_MARKET"] = Strategy(
        id="QUANT_BEST_MARKET",
        name="Meilleur Marché de l'Équipe",
        family=StrategyFamily.EMPIRICAL,
        market_type="team_best",  # Dépend de l'équipe
        conditions={},
        description="Utilise le marché historiquement le plus rentable pour cette équipe"
    )
    
    strategies["ADAPTIVE_ENGINE"] = Strategy(
        id="ADAPTIVE_ENGINE",
        name="Moteur Adaptatif",
        family=StrategyFamily.EMPIRICAL,
        market_type="adaptive",
        conditions={"use_context": True, "use_friction": True},
        description="Combine contexte + friction pour choisir le marché"
    )
    
    strategies["MONTE_CARLO_PURE"] = Strategy(
        id="MONTE_CARLO_PURE",
        name="Monte Carlo Pur",
        family=StrategyFamily.EMPIRICAL,
        market_type="mc_best",
        conditions={"min_mc_prob": 0.55, "min_simulations": 1000},
        description="Marché avec la meilleure probabilité Monte Carlo"
    )
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE B: MARCHÉS SPÉCIFIQUES (purs, sans conditions)
    # ─────────────────────────────────────────────────────────────────────────────
    
    strategies["MARKET_OVER25"] = Strategy(
        id="MARKET_OVER25",
        name="Over 2.5 Goals",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="over_25",
        description="Parier systématiquement Over 2.5"
    )
    
    strategies["MARKET_UNDER25"] = Strategy(
        id="MARKET_UNDER25",
        name="Under 2.5 Goals",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="under_25",
        description="Parier systématiquement Under 2.5"
    )
    
    strategies["MARKET_BTTS_YES"] = Strategy(
        id="MARKET_BTTS_YES",
        name="BTTS Yes",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="btts_yes",
        description="Parier systématiquement BTTS Yes"
    )
    
    strategies["MARKET_BTTS_NO"] = Strategy(
        id="MARKET_BTTS_NO",
        name="BTTS No",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="btts_no",
        description="Parier systématiquement BTTS No"
    )
    
    strategies["MARKET_HOME_WIN"] = Strategy(
        id="MARKET_HOME_WIN",
        name="Home Win",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="home_win",
        description="Parier systématiquement Home Win"
    )
    
    strategies["MARKET_AWAY_WIN"] = Strategy(
        id="MARKET_AWAY_WIN",
        name="Away Win",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="away_win",
        description="Parier systématiquement Away Win"
    )
    
    strategies["MARKET_OVER35"] = Strategy(
        id="MARKET_OVER35",
        name="Over 3.5 Goals",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="over_35",
        description="Parier systématiquement Over 3.5"
    )
    
    strategies["MARKET_UNDER35"] = Strategy(
        id="MARKET_UNDER35",
        name="Under 3.5 Goals",
        family=StrategyFamily.MARKET_SPECIFIC,
        market_type="under_35",
        description="Parier systématiquement Under 3.5"
    )
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE C: STRATÉGIES CONDITIONNELLES (avec contexte)
    # ─────────────────────────────────────────────────────────────────────────────
    
    strategies["HOME_OVER25_WHEN_ATTACKING"] = Strategy(
        id="HOME_OVER25_WHEN_ATTACKING",
        name="Over 2.5 quand équipe attaquante à domicile",
        family=StrategyFamily.HYBRID,
        market_type="over_25",
        conditions={"is_home": True, "style": "attacking"},
        description="Over 2.5 quand l'équipe est offensive et joue à domicile"
    )
    
    strategies["AWAY_BTTS_WHEN_LEAKY"] = Strategy(
        id="AWAY_BTTS_WHEN_LEAKY",
        name="BTTS quand équipe fragile à l'extérieur",
        family=StrategyFamily.HYBRID,
        market_type="btts_yes",
        conditions={"is_away": True, "defensive_weakness": True},
        description="BTTS Yes quand l'équipe a une défense fragile à l'extérieur"
    )
    
    strategies["HOME_WIN_VS_BOTTOM6"] = Strategy(
        id="HOME_WIN_VS_BOTTOM6",
        name="Home Win contre équipes faibles",
        family=StrategyFamily.HYBRID,
        market_type="home_win",
        conditions={"opponent_tier": "bottom"},
        description="Home Win quand l'adversaire est dans le bas du classement"
    )
    
    strategies["UNDER25_WHEN_DEFENSIVE"] = Strategy(
        id="UNDER25_WHEN_DEFENSIVE",
        name="Under 2.5 quand équipe défensive",
        family=StrategyFamily.HYBRID,
        market_type="under_25",
        conditions={"style": "defensive"},
        description="Under 2.5 quand l'équipe a un profil défensif"
    )
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE D: STRATÉGIES TEMPORELLES (basées sur les patterns de timing)
    # ─────────────────────────────────────────────────────────────────────────────
    
    strategies["TEAM_GOALS_2H"] = Strategy(
        id="TEAM_GOALS_2H",
        name="Goals 2ème mi-temps",
        family=StrategyFamily.HYBRID,
        market_type="team_goals_2h",
        conditions={"diesel_factor": 0.6},
        description="Parier sur les buts en 2ème mi-temps pour les équipes 'diesel'"
    )
    
    strategies["GOAL_75_90"] = Strategy(
        id="GOAL_75_90",
        name="But 75-90 minutes",
        family=StrategyFamily.HYBRID,
        market_type="goal_75_90",
        conditions={"late_game_killer": True},
        description="But dans les 15 dernières minutes"
    )
    
    strategies["FIRST_HALF_OVER15"] = Strategy(
        id="FIRST_HALF_OVER15",
        name="1ère MT Over 1.5",
        family=StrategyFamily.HYBRID,
        market_type="first_half_over_15",
        conditions={"sprinter_factor": 0.6},
        description="Over 1.5 en première mi-temps pour les équipes 'sprinter'"
    )
    
    return strategies


# ═══════════════════════════════════════════════════════════════════════════════════════
# STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyResult:
    """Résultat d'une stratégie pour une équipe"""
    strategy_id: str
    strategy_name: str
    bets: int = 0
    wins: int = 0
    losses: int = 0
    staked: float = 0.0
    profit: float = 0.0
    
    # Métriques avancées
    xg_supported_wins: int = 0  # Victoires supportées par xG
    xg_supported_losses: int = 0  # Pertes "malchanceuses" (xG supportait le pari)
    bad_analysis_losses: int = 0  # Pertes où l'analyse était fausse
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.bets * 100) if self.bets > 0 else 0.0
    
    @property
    def roi(self) -> float:
        return (self.profit / self.staked * 100) if self.staked > 0 else 0.0
    
    @property
    def is_profitable(self) -> bool:
        return self.profit > 0
    
    @property
    def luck_factor(self) -> float:
        """Facteur de chance: % de pertes dues à la malchance vs mauvaise analyse"""
        total_losses = self.xg_supported_losses + self.bad_analysis_losses
        if total_losses == 0:
            return 0.0
        return self.xg_supported_losses / total_losses * 100


@dataclass
class TeamBacktestResult:
    """Résultat complet du backtest pour une équipe"""
    team_name: str
    team_tier: str = "UNKNOWN"
    team_style: str = "unknown"
    total_matches: int = 0
    
    # Résultats par stratégie
    strategy_results: Dict[str, StrategyResult] = field(default_factory=dict)
    
    # Meilleure stratégie identifiée
    best_strategy: str = ""
    best_strategy_pnl: float = 0.0
    best_strategy_wr: float = 0.0
    best_strategy_n: int = 0
    
    # 2ème meilleure (pour robustesse)
    second_best: str = ""
    second_best_pnl: float = 0.0
    
    # Stratégies à éviter
    blacklisted_strategies: List[str] = field(default_factory=list)
    
    def calculate_best_strategies(self):
        """Calcule les meilleures stratégies basées sur les résultats"""
        # Filtrer les stratégies avec assez de paris (min 5)
        valid_strategies = [
            (sid, res) for sid, res in self.strategy_results.items()
            if res.bets >= 5
        ]
        
        if not valid_strategies:
            return
        
        # Trier par P&L décroissant
        sorted_by_pnl = sorted(valid_strategies, key=lambda x: x[1].profit, reverse=True)
        
        # Meilleure stratégie
        best = sorted_by_pnl[0]
        self.best_strategy = best[0]
        self.best_strategy_pnl = best[1].profit
        self.best_strategy_wr = best[1].win_rate
        self.best_strategy_n = best[1].bets
        
        # 2ème meilleure
        if len(sorted_by_pnl) > 1:
            second = sorted_by_pnl[1]
            self.second_best = second[0]
            self.second_best_pnl = second[1].profit
        
        # Stratégies à éviter (ROI < -20% et n >= 5)
        self.blacklisted_strategies = [
            sid for sid, res in self.strategy_results.items()
            if res.roi < -20 and res.bets >= 5
        ]


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTESTER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBacktesterQuant2:
    """
    Backtester scientifique QUANT 2.0
    
    Analyse granulaire par équipe avec test de TOUTES les stratégies.
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.strategies = get_all_strategies()
        self.team_results: Dict[str, TeamBacktestResult] = {}
        self.name_mappings: Dict[str, str] = {}
        
    async def initialize(self):
        """Charge les données nécessaires"""
        if self.db:
            await self._load_name_mappings()
            await self._load_team_profiles()
    
    async def _load_name_mappings(self):
        """Charge les mappings de noms d'équipes"""
        query = """
            SELECT quantum_name, db_name 
            FROM quantum.team_name_mapping
        """
        # À implémenter avec la vraie connexion DB
        pass
    
    async def _load_team_profiles(self):
        """Charge les profils des 99 équipes"""
        query = """
            SELECT team_name, tier, quantum_dna 
            FROM quantum.team_profiles
        """
        # À implémenter avec la vraie connexion DB
        pass
    
    async def load_team_matches(self, team_name: str, limit: int = 100) -> List[Dict]:
        """
        Charge TOUS les matchs d'une équipe (home ET away).
        
        Returns:
            Liste de matchs avec toutes les données nécessaires
        """
        query = """
            SELECT 
                m.id,
                m.match_date,
                m.home_team,
                m.away_team,
                m.home_goals,
                m.away_goals,
                m.league,
                -- xG si disponible
                m.home_xg,
                m.away_xg,
                -- Stats additionnelles
                m.home_shots,
                m.away_shots,
                m.home_shots_on_target,
                m.away_shots_on_target
            FROM matches_results m
            WHERE (LOWER(m.home_team) = LOWER(%s) OR LOWER(m.away_team) = LOWER(%s))
              AND m.home_goals IS NOT NULL
            ORDER BY m.match_date DESC
            LIMIT %s
        """
        # À implémenter avec la vraie connexion DB
        return []
    
    def evaluate_bet_outcome(
        self, 
        match: Dict, 
        market_type: str, 
        is_home_team: bool
    ) -> Tuple[bool, float, float]:
        """
        Évalue le résultat d'un pari sur un match.
        
        Args:
            match: Données du match
            market_type: Type de marché (over_25, btts_yes, home_win, etc.)
            is_home_team: True si on parie pour l'équipe à domicile
            
        Returns:
            (is_winner, profit, stake)
        """
        home_goals = match.get('home_goals', 0) or 0
        away_goals = match.get('away_goals', 0) or 0
        total_goals = home_goals + away_goals
        
        # Stake fixe de 1 unité pour le backtest
        stake = 1.0
        
        # Cote moyenne par marché (estimations basées sur les données historiques)
        avg_odds = {
            'over_25': 1.85,
            'under_25': 2.00,
            'over_35': 2.50,
            'under_35': 1.55,
            'btts_yes': 1.75,
            'btts_no': 2.10,
            'home_win': 1.80,
            'away_win': 3.20,
            'draw': 3.50,
            'first_half_over_15': 2.20,
            'second_half_over_15': 1.70,
            'goal_75_90': 2.30,
            'team_goals_2h': 1.50,
            'home_over_05': 1.30,
            'away_over_05': 1.55,
            'home_over_15': 2.10,
            'away_over_15': 3.00,
        }
        
        odds = avg_odds.get(market_type, 2.00)
        
        # Évaluation du résultat
        is_winner = False
        
        if market_type == 'over_25':
            is_winner = total_goals > 2.5
        elif market_type == 'under_25':
            is_winner = total_goals < 2.5
        elif market_type == 'over_35':
            is_winner = total_goals > 3.5
        elif market_type == 'under_35':
            is_winner = total_goals < 3.5
        elif market_type == 'btts_yes':
            is_winner = home_goals > 0 and away_goals > 0
        elif market_type == 'btts_no':
            is_winner = home_goals == 0 or away_goals == 0
        elif market_type == 'home_win':
            is_winner = home_goals > away_goals
        elif market_type == 'away_win':
            is_winner = away_goals > home_goals
        elif market_type == 'draw':
            is_winner = home_goals == away_goals
        elif market_type == 'home_over_05':
            is_winner = home_goals >= 1
        elif market_type == 'away_over_05':
            is_winner = away_goals >= 1
        elif market_type == 'home_over_15':
            is_winner = home_goals >= 2
        elif market_type == 'away_over_15':
            is_winner = away_goals >= 2
        
        # Calcul du profit
        if is_winner:
            profit = stake * (odds - 1)
        else:
            profit = -stake
        
        return is_winner, profit, stake
    
    def should_apply_strategy(
        self,
        strategy: Strategy,
        match: Dict,
        team_dna: Dict,
        is_home_team: bool
    ) -> Tuple[bool, str]:
        """
        Vérifie si une stratégie doit s'appliquer à un match donné.
        
        Returns:
            (should_bet, market_type)
        """
        # Stratégies de marché pur: toujours appliquer
        if strategy.family == StrategyFamily.MARKET_SPECIFIC:
            return True, strategy.market_type
        
        # Stratégies conditionnelles
        conditions = strategy.conditions
        
        # Vérifier les conditions spécifiques
        if 'is_home' in conditions and conditions['is_home'] != is_home_team:
            return False, ""
        
        if 'is_away' in conditions and conditions['is_away'] == is_home_team:
            return False, ""
        
        # Conditions sur le style
        if 'style' in conditions:
            team_style = team_dna.get('style', 'balanced')
            if conditions['style'] == 'attacking' and team_style not in ['attacking', 'offensive']:
                return False, ""
            if conditions['style'] == 'defensive' and team_style not in ['defensive', 'conservative']:
                return False, ""
        
        # Conditions sur le diesel_factor
        if 'diesel_factor' in conditions:
            diesel = team_dna.get('diesel_factor', 0.5)
            if diesel < conditions['diesel_factor']:
                return False, ""
        
        # Conditions sur le late_game_killer
        if 'late_game_killer' in conditions:
            killer = team_dna.get('late_game_killer', False)
            if not killer:
                return False, ""
        
        # Stratégies empiriques: logique spécifique
        if strategy.id == "QUANT_BEST_MARKET":
            best_market = team_dna.get('best_market', 'over_25')
            return True, best_market
        
        return True, strategy.market_type
    
    def analyze_loss_with_xg(
        self,
        match: Dict,
        market_type: str,
        is_home_team: bool
    ) -> str:
        """
        Analyse si une perte est due à la malchance (xG supportait le pari) 
        ou à une mauvaise analyse.
        
        Returns:
            'XG_SUPPORTED' si malchance, 'BAD_ANALYSIS' sinon
        """
        home_xg = match.get('home_xg', 0) or 0
        away_xg = match.get('away_xg', 0) or 0
        total_xg = home_xg + away_xg
        
        home_goals = match.get('home_goals', 0) or 0
        away_goals = match.get('away_goals', 0) or 0
        
        if market_type == 'over_25':
            # xG > 2.5 mais < 3 buts marqués = malchance
            if total_xg > 2.5:
                return 'XG_SUPPORTED'
        elif market_type == 'under_25':
            # xG < 2.5 mais >= 3 buts marqués = malchance
            if total_xg < 2.5:
                return 'XG_SUPPORTED'
        elif market_type == 'btts_yes':
            # Les deux avaient du xG mais un n'a pas marqué
            if home_xg > 0.5 and away_xg > 0.5:
                return 'XG_SUPPORTED'
        elif market_type == 'home_win':
            # Home xG > Away xG mais défaite
            if home_xg > away_xg and home_goals <= away_goals:
                return 'XG_SUPPORTED'
        elif market_type == 'away_win':
            # Away xG > Home xG mais défaite
            if away_xg > home_xg and away_goals <= home_goals:
                return 'XG_SUPPORTED'
        
        return 'BAD_ANALYSIS'
    
    async def analyze_team(
        self,
        team_name: str,
        matches: List[Dict],
        team_dna: Dict
    ) -> TeamBacktestResult:
        """
        Analyse complète d'une équipe avec TOUTES les stratégies.
        
        C'est le cœur du backtest QUANT 2.0.
        """
        result = TeamBacktestResult(
            team_name=team_name,
            team_tier=team_dna.get('tier', 'UNKNOWN'),
            team_style=team_dna.get('style', 'unknown'),
            total_matches=len(matches)
        )
        
        # Initialiser les résultats pour chaque stratégie
        for strategy_id, strategy in self.strategies.items():
            result.strategy_results[strategy_id] = StrategyResult(
                strategy_id=strategy_id,
                strategy_name=strategy.name
            )
        
        # Analyser chaque match
        for match in matches:
            is_home = match['home_team'].lower() == team_name.lower()
            
            # Appliquer chaque stratégie
            for strategy_id, strategy in self.strategies.items():
                should_bet, market_type = self.should_apply_strategy(
                    strategy, match, team_dna, is_home
                )
                
                if not should_bet or not market_type:
                    continue
                
                # Évaluer le résultat du pari
                is_winner, profit, stake = self.evaluate_bet_outcome(
                    match, market_type, is_home
                )
                
                # Mettre à jour les stats
                sr = result.strategy_results[strategy_id]
                sr.bets += 1
                sr.staked += stake
                sr.profit += profit
                
                if is_winner:
                    sr.wins += 1
                else:
                    sr.losses += 1
                    # Analyser la cause de la perte
                    loss_type = self.analyze_loss_with_xg(match, market_type, is_home)
                    if loss_type == 'XG_SUPPORTED':
                        sr.xg_supported_losses += 1
                    else:
                        sr.bad_analysis_losses += 1
        
        # Calculer les meilleures stratégies
        result.calculate_best_strategies()
        
        return result
    
    async def run_full_backtest(
        self,
        teams: List[str] = None,
        limit_per_team: int = 50,
        verbose: bool = True
    ):
        """
        Lance le backtest complet sur toutes les équipes.
        
        Args:
            teams: Liste des équipes à analyser (None = toutes)
            limit_per_team: Nombre max de matchs par équipe
            verbose: Afficher la progression
        """
        if verbose:
            print("=" * 100)
            print("🧬 QUANTUM BACKTESTER QUANT 2.0 - ANALYSE SCIENTIFIQUE GRANULAIRE")
            print("=" * 100)
            print(f"📊 Stratégies testées: {len(self.strategies)}")
            print(f"📅 Matchs par équipe: max {limit_per_team}")
            print()
        
        # Charger les équipes si non spécifiées
        if teams is None:
            teams = await self._get_all_teams()
        
        total_teams = len(teams)
        
        for i, team_name in enumerate(teams):
            if verbose:
                print(f"\r[{i+1}/{total_teams}] Analyse: {team_name:30}", end="", flush=True)
            
            # Charger les matchs
            matches = await self.load_team_matches(team_name, limit_per_team)
            
            if len(matches) < 5:
                if verbose:
                    print(f" ⚠️ Pas assez de matchs ({len(matches)})")
                continue
            
            # Charger le DNA de l'équipe
            team_dna = await self._get_team_dna(team_name)
            
            # Analyser
            result = await self.analyze_team(team_name, matches, team_dna)
            self.team_results[team_name] = result
        
        if verbose:
            print("\n")
            print("✅ Backtest terminé!")
    
    async def _get_all_teams(self) -> List[str]:
        """Récupère la liste de toutes les équipes"""
        # À implémenter avec la vraie connexion DB
        return []
    
    async def _get_team_dna(self, team_name: str) -> Dict:
        """Récupère le DNA d'une équipe"""
        # À implémenter avec la vraie connexion DB
        return {}
    
    def print_report(self, top_n: int = 30):
        """
        Affiche le rapport complet du backtest.
        Format identique à l'audit QUANT 2.0.
        """
        print()
        print("=" * 120)
        print("🏆 RAPPORT BACKTEST QUANT 2.0 - ANALYSE GRANULAIRE PAR ÉQUIPE")
        print("=" * 120)
        print()
        
        # Trier par P&L de la meilleure stratégie
        sorted_teams = sorted(
            self.team_results.items(),
            key=lambda x: x[1].best_strategy_pnl,
            reverse=True
        )
        
        # En-tête
        print(f"{'#':>3}  {'Équipe':26} {'Best Strategy':25} {'Tier':8} "
              f"{'P':>4} {'W':>4} {'L':>4} {'WR':>6} {'P&L':>10} {'2nd Best'}")
        print("-" * 120)
        
        # Stats globales
        total_positive = 0
        total_elite = 0
        total_negative = 0
        strategy_usage = {}
        
        for rank, (team_name, result) in enumerate(sorted_teams[:top_n], 1):
            if not result.best_strategy:
                continue
            
            # Icône basée sur P&L
            if result.best_strategy_pnl >= 20:
                icon = "💎"
                total_elite += 1
            elif result.best_strategy_pnl >= 10:
                icon = "🏆"
                total_positive += 1
            elif result.best_strategy_pnl >= 5:
                icon = "✅"
                total_positive += 1
            elif result.best_strategy_pnl >= 0:
                icon = "🔸"
                total_positive += 1
            else:
                icon = "❌"
                total_negative += 1
            
            # Stats de la meilleure stratégie
            sr = result.strategy_results.get(result.best_strategy)
            if sr:
                wins = sr.wins
                losses = sr.losses
            else:
                wins = losses = 0
            
            # 2nd best
            second_info = f"{result.second_best}({result.second_best_pnl:+.1f})" if result.second_best else "-"
            
            print(f"{icon}{rank:>2}  {team_name:26} {result.best_strategy:25} {result.team_tier:8} "
                  f"{result.best_strategy_n:>4} {wins:>4} {losses:>4} "
                  f"{result.best_strategy_wr:>5.1f}% {result.best_strategy_pnl:>+9.1f}u "
                  f"{second_info}")
            
            # Compter l'usage des stratégies
            if result.best_strategy:
                strategy_usage[result.best_strategy] = strategy_usage.get(result.best_strategy, 0) + 1
        
        # Résumé
        print()
        print("=" * 120)
        print("📊 RÉSUMÉ")
        print("=" * 120)
        print(f"  💎 ELITE (P&L ≥ 20u)    : {total_elite} équipes")
        print(f"  ✅ POSITIF (P&L > 0u)   : {total_positive} équipes")
        print(f"  ❌ NÉGATIF (P&L < 0u)   : {total_negative} équipes")
        print()
        
        # Stratégies les plus utilisées
        print("📈 STRATÉGIES LES PLUS PERFORMANTES (comme Best Strategy)")
        print("-" * 80)
        sorted_strategies = sorted(strategy_usage.items(), key=lambda x: x[1], reverse=True)
        
        for strategy_id, count in sorted_strategies[:10]:
            # Calculer le P&L total de cette stratégie
            total_pnl = sum(
                r.strategy_results[strategy_id].profit
                for r in self.team_results.values()
                if strategy_id in r.strategy_results and r.strategy_results[strategy_id].bets >= 5
            )
            avg_pnl = total_pnl / count if count > 0 else 0
            print(f"   {strategy_id:30} | {count:3} équipes | Total: {total_pnl:+8.1f}u | Avg: {avg_pnl:+6.1f}u")
        
        print()
    
    def export_results_json(self, filepath: str):
        """Exporte les résultats en JSON"""
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "total_teams": len(self.team_results),
            "strategies_tested": len(self.strategies),
            "teams": {}
        }
        
        for team_name, result in self.team_results.items():
            export_data["teams"][team_name] = {
                "tier": result.team_tier,
                "style": result.team_style,
                "total_matches": result.total_matches,
                "best_strategy": result.best_strategy,
                "best_strategy_pnl": result.best_strategy_pnl,
                "best_strategy_wr": result.best_strategy_wr,
                "second_best": result.second_best,
                "second_best_pnl": result.second_best_pnl,
                "blacklisted": result.blacklisted_strategies,
                "all_strategies": {
                    sid: {
                        "bets": sr.bets,
                        "wins": sr.wins,
                        "losses": sr.losses,
                        "profit": sr.profit,
                        "win_rate": sr.win_rate,
                        "roi": sr.roi,
                        "luck_factor": sr.luck_factor
                    }
                    for sid, sr in result.strategy_results.items()
                    if sr.bets > 0
                }
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Résultats exportés vers: {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    """Point d'entrée pour le backtest"""
    print("🧬 QUANTUM BACKTESTER QUANT 2.0")
    print("=" * 60)
    
    backtester = QuantumBacktesterQuant2()
    
    # Exemple d'utilisation (sans connexion DB réelle)
    print("\n⚠️ Ce script nécessite une connexion à la base de données.")
    print("Exécutez-le sur le serveur de production avec:")
    print()
    print("  from quantum.services.backtester_quant2 import QuantumBacktesterQuant2")
    print("  backtester = QuantumBacktesterQuant2(db_connection)")
    print("  await backtester.initialize()")
    print("  await backtester.run_full_backtest(limit_per_team=50)")
    print("  backtester.print_report()")
    print()


if __name__ == "__main__":
    asyncio.run(main())

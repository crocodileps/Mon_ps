#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║          QUANTUM BACKTESTER QUANT 2.0 - SCRIPT D'EXÉCUTION PRODUCTION                ║
║                                                                                       ║
║  Usage sur le serveur:                                                                ║
║  python3 /home/Mon_ps/scripts/run_quant2_backtest.py                                 ║
║                                                                                       ║
║  Ce script:                                                                           ║
║  1. Se connecte à PostgreSQL                                                          ║
║  2. Charge les 99 équipes avec leur DNA                                               ║
║  3. Pour chaque équipe, teste TOUTES les stratégies                                   ║
║  4. Génère le rapport QUANT 2.0 (identique à l'audit)                                ║
║  5. Exporte les résultats en JSON                                                     ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import json
import sys
import os


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "monps_db", 
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Cotes moyennes par marché (basées sur les données historiques)
AVG_ODDS = {
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
    'home_over_05': 1.30,
    'away_over_05': 1.55,
    'home_over_15': 2.10,
    'away_over_15': 3.00,
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyResult:
    """Résultat d'une stratégie pour une équipe"""
    strategy_id: str
    bets: int = 0
    wins: int = 0
    losses: int = 0
    staked: float = 0.0
    profit: float = 0.0
    xg_bad_luck_losses: int = 0
    bad_analysis_losses: int = 0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.bets * 100) if self.bets > 0 else 0.0
    
    @property
    def roi(self) -> float:
        return (self.profit / self.staked * 100) if self.staked > 0 else 0.0


@dataclass
class TeamResult:
    """Résultat complet du backtest pour une équipe"""
    team_name: str
    tier: str = "UNKNOWN"
    style: str = "unknown"
    total_matches: int = 0
    strategies: Dict[str, StrategyResult] = field(default_factory=dict)
    best_strategy: str = ""
    best_pnl: float = 0.0
    best_wr: float = 0.0
    best_n: int = 0
    second_best: str = ""
    second_pnl: float = 0.0
    blacklisted: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════
# DÉFINITION DES STRATÉGIES
# ═══════════════════════════════════════════════════════════════════════════════════════

def get_strategies() -> Dict[str, Dict]:
    """
    Retourne toutes les stratégies à tester.
    
    Chaque stratégie définit:
    - market: Le type de marché à parier
    - conditions: Les conditions pour appliquer la stratégie (optionnel)
    - description: Description de la stratégie
    """
    return {
        # GROUPE A: Marchés purs (toujours applicable)
        "MARKET_OVER25": {
            "market": "over_25",
            "conditions": {},
            "description": "Over 2.5 Goals systématique"
        },
        "MARKET_UNDER25": {
            "market": "under_25", 
            "conditions": {},
            "description": "Under 2.5 Goals systématique"
        },
        "MARKET_OVER35": {
            "market": "over_35",
            "conditions": {},
            "description": "Over 3.5 Goals systématique"
        },
        "MARKET_UNDER35": {
            "market": "under_35",
            "conditions": {},
            "description": "Under 3.5 Goals systématique"
        },
        "MARKET_BTTS_YES": {
            "market": "btts_yes",
            "conditions": {},
            "description": "BTTS Yes systématique"
        },
        "MARKET_BTTS_NO": {
            "market": "btts_no",
            "conditions": {},
            "description": "BTTS No systématique"
        },
        "MARKET_HOME_WIN": {
            "market": "home_win",
            "conditions": {"is_home": True},
            "description": "Home Win quand l'équipe joue à domicile"
        },
        "MARKET_AWAY_WIN": {
            "market": "away_win",
            "conditions": {"is_away": True},
            "description": "Away Win quand l'équipe joue à l'extérieur"
        },
        
        # GROUPE B: Stratégies conditionnelles (basées sur DNA)
        "HOME_OVER25_ATTACKING": {
            "market": "over_25",
            "conditions": {"is_home": True, "style_contains": "attack"},
            "description": "Over 2.5 à domicile pour équipes offensives"
        },
        "HOME_UNDER25_DEFENSIVE": {
            "market": "under_25",
            "conditions": {"is_home": True, "style_contains": "defens"},
            "description": "Under 2.5 à domicile pour équipes défensives"
        },
        "AWAY_BTTS_LEAKY": {
            "market": "btts_yes",
            "conditions": {"is_away": True, "xg_against_high": True},
            "description": "BTTS Yes à l'extérieur pour équipes qui encaissent"
        },
        "HOME_WIN_VS_WEAK": {
            "market": "home_win",
            "conditions": {"is_home": True, "tier_gap": 2},
            "description": "Home Win contre équipes plus faibles (2 tiers)"
        },
        
        # GROUPE C: Stratégies empiriques (audit QUANT 2.0)
        "CONVERGENCE_OVER": {
            "market": "over_25",
            "conditions": {"friction_high": True, "xg_combined_high": True},
            "description": "Over 2.5 quand friction + xG élevés"
        },
        "CONVERGENCE_UNDER": {
            "market": "under_25",
            "conditions": {"friction_low": True, "xg_combined_low": True},
            "description": "Under 2.5 quand friction + xG faibles"
        },
        
        # GROUPE D: Stratégies temporelles
        "TEAM_2H_DIESEL": {
            "market": "team_goals_2h",
            "conditions": {"diesel_factor_high": True},
            "description": "Buts 2ème MT pour équipes 'diesel'"
        },
        "FIRST_HALF_SPRINTER": {
            "market": "first_half_over_15",
            "conditions": {"sprinter_factor_high": True},
            "description": "Over 1.5 1ère MT pour équipes 'sprinter'"
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTESTER
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBacktester:
    """Backtester QUANT 2.0"""
    
    def __init__(self):
        self.conn = None
        self.strategies = get_strategies()
        self.name_mappings = {}
        self.team_dna = {}
        self.results: Dict[str, TeamResult] = {}
        
    def connect(self):
        """Connexion à PostgreSQL"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connecté à PostgreSQL")
        
    def close(self):
        """Ferme la connexion"""
        if self.conn:
            self.conn.close()
            
    def load_name_mappings(self):
        """Charge les mappings de noms"""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT quantum_name, historical_name 
                FROM quantum.team_name_mapping
            """)
            for row in cur.fetchall():
                self.name_mappings[row[0].lower()] = row[1].lower()
                self.name_mappings[row[1].lower()] = row[0].lower()
            print(f"✅ {len(self.name_mappings)//2} mappings chargés")
        except Exception as e:
            print(f"⚠️ Pas de table de mapping: {e}")
        finally:
            cur.close()
            
    def load_team_profiles(self):
        """Charge les profils DNA des équipes"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT team_name, tier, quantum_dna
                FROM quantum.team_profiles
            """)
            for row in cur.fetchall():
                team = row['team_name'].lower()
                dna = row['quantum_dna'] or {}
                if isinstance(dna, str):
                    dna = json.loads(dna)
                    
                self.team_dna[team] = {
                    'tier': row['tier'] or 'UNKNOWN',
                    'style': dna.get('tactical_dna', {}).get('style', 'balanced'),
                    'diesel_factor': dna.get('temporal_dna', {}).get('diesel_factor', 0.5),
                    'xg_for': dna.get('current_season', {}).get('xg', 1.5),
                    'xg_against': dna.get('current_season', {}).get('xga', 1.5),
                    'best_market': dna.get('market_dna', {}).get('best_market', 'over_25'),
                }
            print(f"✅ {len(self.team_dna)} équipes avec DNA chargées")
        except Exception as e:
            print(f"⚠️ Erreur chargement DNA: {e}")
        finally:
            cur.close()
            
    def get_all_teams(self) -> List[str]:
        """Récupère la liste des équipes"""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT DISTINCT team_name 
                FROM quantum.team_profiles
                ORDER BY team_name
            """)
            teams = [row[0] for row in cur.fetchall()]
            return teams
        except:
            # Fallback: utiliser matches_results
            cur.execute("""
                SELECT DISTINCT home_team as team FROM matches_results
                UNION
                SELECT DISTINCT away_team as team FROM matches_results
                ORDER BY team
            """)
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
            
    def load_team_matches(self, team_name: str, limit: int = 50) -> List[Dict]:
        """Charge les matchs d'une équipe"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Normaliser le nom
        team_lower = team_name.lower()
        historical_name = self.name_mappings.get(team_lower, team_lower)
        
        try:
            cur.execute("""
                SELECT DISTINCT ON (DATE(match_date), home_team, away_team)
                    match_date,
                    home_team,
                    away_team,
                    home_goals,
                    away_goals,
                    league,
                    0 as home_xg,
                    0 as away_xg
                FROM matches_results
                WHERE (LOWER(home_team) = %s OR LOWER(away_team) = %s
                    OR LOWER(home_team) = %s OR LOWER(away_team) = %s)
                  AND home_goals IS NOT NULL
                ORDER BY DATE(match_date), home_team, away_team, match_date DESC
                LIMIT %s
            """, (team_lower, team_lower, historical_name, historical_name, limit))
            
            matches = []
            for row in cur.fetchall():
                matches.append({
                    'date': row['match_date'],
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'home_goals': row['home_goals'] or 0,
                    'away_goals': row['away_goals'] or 0,
                    'league': row['league'],
                    'home_xg': row['home_xg'] or 0,
                    'away_xg': row['away_xg'] or 0,
                })
            return matches
        finally:
            cur.close()
            
    def evaluate_bet(self, match: Dict, market: str, is_home: bool) -> Tuple[bool, float]:
        """
        Évalue le résultat d'un pari.
        
        Returns:
            (is_winner, profit)
        """
        hg = match['home_goals']
        ag = match['away_goals']
        total = hg + ag
        
        stake = 1.0
        odds = AVG_ODDS.get(market, 2.0)
        
        # Marchés relatifs à l'équipe
        team_goals = hg if is_home else ag
        opp_goals = ag if is_home else hg
        
        is_winner = False
        
        if market == 'over_25':
            is_winner = total > 2.5
        elif market == 'under_25':
            is_winner = total < 2.5
        elif market == 'over_35':
            is_winner = total > 3.5
        elif market == 'under_35':
            is_winner = total < 3.5
        elif market == 'btts_yes':
            is_winner = hg > 0 and ag > 0
        elif market == 'btts_no':
            is_winner = hg == 0 or ag == 0
        elif market == 'home_win':
            is_winner = hg > ag
        elif market == 'away_win':
            is_winner = ag > hg
        elif market == 'draw':
            is_winner = hg == ag
        elif market == 'home_over_05':
            is_winner = hg >= 1
        elif market == 'away_over_05':
            is_winner = ag >= 1
        elif market == 'home_over_15':
            is_winner = hg >= 2
        elif market == 'away_over_15':
            is_winner = ag >= 2
        elif market == 'team_goals_2h':
            # Approximation: si l'équipe a marqué et le match a été serré
            is_winner = team_goals >= 1
        elif market == 'first_half_over_15':
            # Approximation: si le total > 2 et match ouvert
            is_winner = total >= 3
        
        profit = stake * (odds - 1) if is_winner else -stake
        return is_winner, profit
    
    def check_conditions(self, strategy: Dict, match: Dict, team_dna: Dict, is_home: bool) -> bool:
        """Vérifie si les conditions d'une stratégie sont remplies"""
        conditions = strategy.get('conditions', {})
        
        if not conditions:
            return True
            
        # Condition is_home
        if 'is_home' in conditions and conditions['is_home'] != is_home:
            return False
        if 'is_away' in conditions and conditions['is_away'] == is_home:
            return False
            
        # Condition style
        if 'style_contains' in conditions:
            style = team_dna.get('style', 'balanced')
            if conditions['style_contains'] not in style.lower():
                return False
                
        # Condition xG élevé
        if 'xg_against_high' in conditions:
            xga = team_dna.get('xg_against', 1.5)
            if xga < 1.5:
                return False
                
        # Condition friction haute
        if 'friction_high' in conditions:
            xg_for = team_dna.get('xg_for', 1.5)
            if xg_for < 1.7:
                return False
                
        # Condition friction basse
        if 'friction_low' in conditions:
            xg_for = team_dna.get('xg_for', 1.5)
            if xg_for > 1.3:
                return False
                
        # Condition xG combiné élevé
        if 'xg_combined_high' in conditions:
            total_xg = team_dna.get('xg_for', 1.5) + team_dna.get('xg_against', 1.5)
            if total_xg < 3.0:
                return False
                
        # Condition xG combiné faible
        if 'xg_combined_low' in conditions:
            total_xg = team_dna.get('xg_for', 1.5) + team_dna.get('xg_against', 1.5)
            if total_xg > 2.5:
                return False
                
        # Condition diesel
        if 'diesel_factor_high' in conditions:
            diesel = team_dna.get('diesel_factor', 0.5)
            if diesel < 0.6:
                return False
                
        # Condition sprinter
        if 'sprinter_factor_high' in conditions:
            diesel = team_dna.get('diesel_factor', 0.5)
            if diesel > 0.4:  # Sprinter = faible diesel
                return False
                
        return True
    
    def analyze_loss(self, match: Dict, market: str, is_home: bool) -> str:
        """Analyse si une perte est malchanceuse ou mauvaise analyse"""
        hxg = match.get('home_xg', 0) or 0
        axg = match.get('away_xg', 0) or 0
        total_xg = hxg + axg
        
        hg = match['home_goals']
        ag = match['away_goals']
        total = hg + ag
        
        # Over 2.5 perdu alors que xG > 2.5 = malchance
        if market == 'over_25' and total_xg > 2.5:
            return 'BAD_LUCK'
        # Under 2.5 perdu alors que xG < 2.5 = malchance
        if market == 'under_25' and total_xg < 2.5:
            return 'BAD_LUCK'
        # BTTS Yes perdu alors que les deux avaient du xG
        if market == 'btts_yes' and hxg > 0.5 and axg > 0.5:
            return 'BAD_LUCK'
        # Home win perdu alors que home xG > away xG
        if market == 'home_win' and hxg > axg and hg <= ag:
            return 'BAD_LUCK'
            
        return 'BAD_ANALYSIS'
    
    def analyze_team(self, team_name: str, limit: int = 50) -> TeamResult:
        """Analyse complète d'une équipe"""
        result = TeamResult(team_name=team_name)
        
        # Récupérer le DNA
        team_lower = team_name.lower()
        dna = self.team_dna.get(team_lower, {})
        result.tier = dna.get('tier', 'UNKNOWN')
        result.style = dna.get('style', 'unknown')
        
        # Charger les matchs
        matches = self.load_team_matches(team_name, limit)
        result.total_matches = len(matches)
        
        if len(matches) < 5:
            return result
            
        # Initialiser les résultats pour chaque stratégie
        for sid in self.strategies:
            result.strategies[sid] = StrategyResult(strategy_id=sid)
            
        # Analyser chaque match
        for match in matches:
            is_home = match['home_team'].lower() == team_lower or \
                      match['home_team'].lower() == self.name_mappings.get(team_lower, '')
            
            for sid, strategy in self.strategies.items():
                # Vérifier les conditions
                if not self.check_conditions(strategy, match, dna, is_home):
                    continue
                    
                market = strategy['market']
                is_win, profit = self.evaluate_bet(match, market, is_home)
                
                sr = result.strategies[sid]
                sr.bets += 1
                sr.staked += 1.0
                sr.profit += profit
                
                if is_win:
                    sr.wins += 1
                else:
                    sr.losses += 1
                    loss_type = self.analyze_loss(match, market, is_home)
                    if loss_type == 'BAD_LUCK':
                        sr.xg_bad_luck_losses += 1
                    else:
                        sr.bad_analysis_losses += 1
        
        # Calculer les meilleures stratégies
        valid = [(sid, sr) for sid, sr in result.strategies.items() if sr.bets >= 5]
        if valid:
            sorted_by_pnl = sorted(valid, key=lambda x: x[1].profit, reverse=True)
            best = sorted_by_pnl[0]
            result.best_strategy = best[0]
            result.best_pnl = best[1].profit
            result.best_wr = best[1].win_rate
            result.best_n = best[1].bets
            
            if len(sorted_by_pnl) > 1:
                second = sorted_by_pnl[1]
                result.second_best = second[0]
                result.second_pnl = second[1].profit
                
            # Blacklist
            result.blacklisted = [
                sid for sid, sr in result.strategies.items()
                if sr.roi < -20 and sr.bets >= 5
            ]
        
        return result
    
    def run_backtest(self, limit_per_team: int = 50, verbose: bool = True):
        """Lance le backtest complet"""
        if verbose:
            print()
            print("=" * 100)
            print("🧬 QUANTUM BACKTESTER QUANT 2.0 - ANALYSE SCIENTIFIQUE GRANULAIRE")
            print("=" * 100)
            print(f"📊 Stratégies testées: {len(self.strategies)}")
            print(f"📅 Matchs par équipe: max {limit_per_team}")
            print()
        
        # Charger les données
        self.load_name_mappings()
        self.load_team_profiles()
        
        teams = self.get_all_teams()
        total = len(teams)
        
        if verbose:
            print(f"🏟️ Équipes à analyser: {total}")
            print()
        
        for i, team in enumerate(teams):
            if verbose:
                print(f"\r[{i+1}/{total}] {team:30}", end="", flush=True)
            
            result = self.analyze_team(team, limit_per_team)
            
            if result.total_matches >= 5:
                self.results[team] = result
        
        if verbose:
            print("\n")
            print("✅ Backtest terminé!")
            print(f"   {len(self.results)} équipes analysées")
            
    def print_report(self, top_n: int = 50):
        """Affiche le rapport"""
        print()
        print("=" * 130)
        print("🏆 RAPPORT BACKTEST QUANT 2.0 - ANALYSE GRANULAIRE PAR ÉQUIPE")
        print("=" * 130)
        print()
        
        # Trier par P&L
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: x[1].best_pnl,
            reverse=True
        )
        
        # En-tête
        print(f"{'#':>3}  {'Équipe':28} {'Best Strategy':25} {'Tier':8} "
              f"{'P':>4} {'W':>4} {'L':>4} {'WR':>6} {'P&L':>10} {'2nd Best (P&L)'}")
        print("-" * 130)
        
        # Stats globales
        elite = positive = negative = 0
        strategy_usage = {}
        total_pnl = 0
        
        for rank, (team, res) in enumerate(sorted_results[:top_n], 1):
            if not res.best_strategy:
                continue
                
            # Icône
            if res.best_pnl >= 20:
                icon = "💎"
                elite += 1
            elif res.best_pnl >= 10:
                icon = "🏆"
                positive += 1
            elif res.best_pnl >= 5:
                icon = "✅"
                positive += 1
            elif res.best_pnl >= 0:
                icon = "🔸"
                positive += 1
            else:
                icon = "❌"
                negative += 1
            
            total_pnl += res.best_pnl
            
            sr = res.strategies.get(res.best_strategy)
            wins = sr.wins if sr else 0
            losses = sr.losses if sr else 0
            
            second = f"{res.second_best}({res.second_pnl:+.1f})" if res.second_best else "-"
            
            print(f"{icon}{rank:>2}  {team:28} {res.best_strategy:25} {res.tier:8} "
                  f"{res.best_n:>4} {wins:>4} {losses:>4} "
                  f"{res.best_wr:>5.1f}% {res.best_pnl:>+9.1f}u "
                  f"{second}")
            
            # Usage des stratégies
            if res.best_strategy:
                strategy_usage[res.best_strategy] = strategy_usage.get(res.best_strategy, 0) + 1
        
        # Résumé
        print()
        print("=" * 130)
        print("📊 RÉSUMÉ GLOBAL")
        print("=" * 130)
        print(f"  💎 ELITE (P&L ≥ 20u)    : {elite} équipes")
        print(f"  ✅ POSITIF (P&L > 0u)   : {positive + elite} équipes")
        print(f"  ❌ NÉGATIF (P&L < 0u)   : {negative} équipes")
        print(f"  📈 P&L TOTAL            : {total_pnl:+.1f}u")
        print()
        
        # Stratégies les plus utilisées
        print("📈 STRATÉGIES LES PLUS PERFORMANTES (comme Best Strategy)")
        print("-" * 90)
        sorted_strats = sorted(strategy_usage.items(), key=lambda x: x[1], reverse=True)
        
        for sid, count in sorted_strats[:10]:
            # Calculer P&L total pour cette stratégie
            total = sum(
                r.strategies[sid].profit
                for r in self.results.values()
                if sid in r.strategies and r.strategies[sid].bets >= 5
            )
            avg = total / count if count > 0 else 0
            print(f"   {sid:30} | {count:3} équipes | Total: {total:+8.1f}u | Avg: {avg:+6.1f}u")
        
        print()
        
    def export_json(self, filepath: str):
        """Exporte les résultats en JSON"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_teams": len(self.results),
            "strategies_tested": len(self.strategies),
            "teams": {}
        }
        
        for team, res in self.results.items():
            data["teams"][team] = {
                "tier": res.tier,
                "style": res.style,
                "total_matches": res.total_matches,
                "best_strategy": res.best_strategy,
                "best_pnl": res.best_pnl,
                "best_wr": res.best_wr,
                "best_n": res.best_n,
                "second_best": res.second_best,
                "second_pnl": res.second_pnl,
                "blacklisted": res.blacklisted,
                "strategies": {
                    sid: {
                        "bets": sr.bets,
                        "wins": sr.wins,
                        "losses": sr.losses,
                        "profit": round(sr.profit, 2),
                        "win_rate": round(sr.win_rate, 1),
                        "roi": round(sr.roi, 1),
                        "bad_luck_losses": sr.xg_bad_luck_losses,
                        "bad_analysis_losses": sr.bad_analysis_losses
                    }
                    for sid, sr in res.strategies.items()
                    if sr.bets > 0
                }
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Résultats exportés: {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée"""
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════════════════╗")
    print("║          QUANTUM BACKTESTER QUANT 2.0 - DE AMATEUR À HEDGE FUND GRADE                ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    backtester = QuantumBacktester()
    
    try:
        backtester.connect()
        backtester.run_backtest(limit_per_team=50, verbose=True)
        backtester.print_report(top_n=50)
        
        # Exporter les résultats
        output_dir = "/home/Mon_ps/exports"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/quant2_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backtester.export_json(output_file)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        backtester.close()


if __name__ == "__main__":
    main()

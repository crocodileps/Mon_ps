#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║     🏦 QUANTUM BACKTEST V4.0 INSTITUTIONNEL - HEDGE FUND GRADE                                                                        ║
║                                                                                                                                       ║
║  ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════   ║
║                                                                                                                                       ║
║  📊 DONNÉES SOURCES:                                                                                                                  ║
║     • quantum.team_strategies    → 92 équipes, 812 paris, stratégies optimales                                                        ║
║     • quantum.market_performance → Best market validé par équipe                                                                      ║
║     • quantum.team_profiles      → Style tactique (offensive/defensive/balanced)                                                      ║
║     • match_xg_stats             → Matchs joués par équipe                                                                            ║
║     • team_market_profiles       → ROI par marché                                                                                     ║
║     • tracking_clv_picks         → Picks détaillés avec résultats                                                                     ║
║                                                                                                                                       ║
║  📈 MÉTRIQUES AFFICHÉES:                                                                                                              ║
║     • Matchs Joués / Paris / Wins / Losses                                                                                            ║
║     • Win Rate% / ROI% / P&L                                                                                                          ║
║     • Malchance% (pertes non dues à l'analyse)                                                                                        ║
║     • Erreur% (pertes dues à mauvaise analyse)                                                                                        ║
║     • Best Market validé                                                                                                              ║
║     • Style tactique                                                                                                                  ║
║     • Tier (ELITE/GOLD/SILVER/BRONZE/WATCH)                                                                                           ║
║                                                                                                                                       ║
║  🎯 PRINCIPE MYA: "L'ÉQUIPE génère le ROI, pas la stratégie générique"                                                                ║
║                                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json
import argparse

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Couleurs ANSI pour terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GOLD = '\033[38;5;220m'
    SILVER = '\033[38;5;250m'
    BRONZE = '\033[38;5;208m'
    PURPLE = '\033[38;5;135m'
    ORANGE = '\033[38;5;214m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

# Tiers basés sur performance
TIER_THRESHOLDS = {
    'ELITE': {'min_rank': 1, 'max_rank': 10, 'min_pnl': 15, 'min_wr': 80, 'emoji': '💎', 'color': Colors.GOLD},
    'GOLD': {'min_rank': 1, 'max_rank': 25, 'min_pnl': 8, 'min_wr': 70, 'emoji': '🏆', 'color': Colors.YELLOW},
    'SILVER': {'min_rank': 1, 'max_rank': 50, 'min_pnl': 3, 'min_wr': 65, 'emoji': '✅', 'color': Colors.CYAN},
    'BRONZE': {'min_rank': 1, 'max_rank': 75, 'min_pnl': 0, 'min_wr': 55, 'emoji': '⚪', 'color': Colors.WHITE},
    'WATCH': {'min_rank': 1, 'max_rank': 999, 'min_pnl': -999, 'min_wr': 0, 'emoji': '⚠️', 'color': Colors.RED},
}

# Mapping des stratégies vers familles
STRATEGY_FAMILIES = {
    'CONVERGENCE': ['CONVERGENCE_OVER_PURE', 'CONVERGENCE_OVER_MC', 'CONVERGENCE_UNDER_PURE', 'CONVERGENCE_UNDER_MC'],
    'MONTE_CARLO': ['MONTE_CARLO_PURE', 'MC_V2_PURE', 'MC_NO_CLASH'],
    'QUANT': ['QUANT_BEST_MARKET', 'QUANT_ROI_30', 'QUANT_ROI_40'],
    'CHAOS': ['TOTAL_CHAOS'],
    'GENERIC': ['GENERIC', 'DEFAULT'],
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamAnalysis:
    """Analyse complète d'une équipe"""
    rank: int = 0
    team_name: str = ""
    
    # Stratégie
    best_strategy: str = ""
    strategy_family: str = ""
    
    # Performance
    matches_played: int = 0
    bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    roi: float = 0.0
    pnl: float = 0.0
    
    # Diagnostic des pertes
    unlucky_count: int = 0
    bad_analysis_count: int = 0
    unlucky_pct: float = 0.0
    error_pct: float = 0.0
    
    # Enrichissement
    style: str = "N/A"
    best_market: str = "N/A"
    market_roi: float = 0.0
    tier: str = "WATCH"
    tier_emoji: str = "⚠️"
    
    # Stats avancées
    avg_odds: float = 0.0
    bet_frequency: float = 0.0  # bets / matches_played
    
    # Ligue
    league: str = "N/A"


@dataclass
class StrategyAnalysis:
    """Analyse d'une stratégie"""
    name: str = ""
    family: str = ""
    teams_count: int = 0
    total_bets: int = 0
    total_wins: int = 0
    total_losses: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_roi: float = 0.0
    best_team: str = ""
    best_team_pnl: float = 0.0


@dataclass 
class MarketAnalysis:
    """Analyse d'un marché"""
    name: str = ""
    teams_count: int = 0
    total_bets: int = 0
    total_wins: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_roi: float = 0.0


@dataclass
class TierAnalysis:
    """Analyse d'un tier"""
    name: str = ""
    emoji: str = ""
    teams_count: int = 0
    total_bets: int = 0
    total_wins: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM V4 INSTITUTIONNEL
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumV4Institutionnel:
    """Backtest V4 Institutionnel - Hedge Fund Grade"""
    
    def __init__(self):
        self.pool = None
        self.teams: List[TeamAnalysis] = []
        self.strategies: Dict[str, StrategyAnalysis] = {}
        self.markets: Dict[str, MarketAnalysis] = {}
        self.tiers: Dict[str, TierAnalysis] = {}
        self.leagues: Dict[str, dict] = {}
        
        # Stats globales
        self.total_teams = 0
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.total_pnl = 0.0
        self.global_wr = 0.0
        self.global_roi = 0.0
        self.profitable_count = 0
        self.losing_count = 0
        
    async def connect(self):
        """Connexion à la base de données"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print(f"{Colors.GREEN}✅ Connexion PostgreSQL établie{Colors.END}")
        
    async def close(self):
        """Fermeture de la connexion"""
        if self.pool:
            await self.pool.close()
            print(f"{Colors.CYAN}🔌 Connexion fermée{Colors.END}")
    
    def get_strategy_family(self, strategy_name: str) -> str:
        """Retourne la famille d'une stratégie"""
        for family, strategies in STRATEGY_FAMILIES.items():
            if strategy_name in strategies:
                return family
        if 'CONVERGENCE' in strategy_name:
            return 'CONVERGENCE'
        if 'MC' in strategy_name or 'MONTE' in strategy_name:
            return 'MONTE_CARLO'
        if 'QUANT' in strategy_name:
            return 'QUANT'
        return 'OTHER'
    
    def get_tier(self, rank: int, pnl: float, wr: float) -> Tuple[str, str]:
        """Retourne le tier et emoji basé sur la performance"""
        if rank <= 10 and pnl >= 15 and wr >= 80:
            return 'ELITE', '💎'
        elif rank <= 25 and pnl >= 8 and wr >= 70:
            return 'GOLD', '🏆'
        elif rank <= 50 and pnl >= 3 and wr >= 65:
            return 'SILVER', '✅'
        elif pnl >= 0 and wr >= 55:
            return 'BRONZE', '⚪'
        else:
            return 'WATCH', '⚠️'
    
    async def load_all_data(self):
        """Charge toutes les données nécessaires"""
        async with self.pool.acquire() as conn:
            
            # ═══════════════════════════════════════════════════════════════════
            # 1. CHARGER LES STRATÉGIES PAR ÉQUIPE (source principale)
            # ═══════════════════════════════════════════════════════════════════
            print(f"\n{Colors.CYAN}📊 Chargement données quantum.team_strategies...{Colors.END}")
            
            strategy_rows = await conn.fetch("""
                SELECT 
                    team_name,
                    strategy_name,
                    bets,
                    wins,
                    losses,
                    win_rate,
                    roi,
                    profit,
                    unlucky_count,
                    bad_analysis_count
                FROM quantum.team_strategies 
                WHERE is_best_strategy = true 
                ORDER BY profit DESC
            """)
            print(f"   → {len(strategy_rows)} équipes avec best_strategy")
            
            # ═══════════════════════════════════════════════════════════════════
            # 2. CHARGER LES MATCHS JOUÉS PAR ÉQUIPE
            # ═══════════════════════════════════════════════════════════════════
            print(f"{Colors.CYAN}📊 Chargement matchs joués par équipe...{Colors.END}")
            
            matches_rows = await conn.fetch("""
                SELECT team, COUNT(*) as matches_played
                FROM (
                    SELECT home_team as team FROM match_xg_stats WHERE match_date >= '2024-08-01'
                    UNION ALL
                    SELECT away_team as team FROM match_xg_stats WHERE match_date >= '2024-08-01'
                ) t
                GROUP BY team
            """)
            matches_map = {r['team']: r['matches_played'] for r in matches_rows}
            print(f"   → {len(matches_map)} équipes avec matchs")
            
            # ═══════════════════════════════════════════════════════════════════
            # 3. CHARGER LES STYLES TACTIQUES
            # ═══════════════════════════════════════════════════════════════════
            print(f"{Colors.CYAN}📊 Chargement styles tactiques...{Colors.END}")
            
            style_rows = await conn.fetch("""
                SELECT team_name, current_style, tier
                FROM quantum.team_profiles
            """)
            style_map = {r['team_name']: r['current_style'] for r in style_rows}
            print(f"   → {len(style_map)} profils tactiques")
            
            # ═══════════════════════════════════════════════════════════════════
            # 4. CHARGER LES BEST MARKETS
            # ═══════════════════════════════════════════════════════════════════
            print(f"{Colors.CYAN}📊 Chargement best markets validés...{Colors.END}")
            
            market_rows = await conn.fetch("""
                SELECT DISTINCT ON (team_name) 
                    team_name, market_type, total_pnl, win_rate
                FROM quantum.market_performance
                WHERE total_picks >= 3
                ORDER BY team_name, total_pnl DESC
            """)
            market_map = {r['team_name']: {
                'market': r['market_type'],
                'roi': float(r['total_pnl']) if r['total_pnl'] else 0.0
            } for r in market_rows}
            print(f"   → {len(market_map)} équipes avec best_market validé")
            
            # ═══════════════════════════════════════════════════════════════════
            # 5. CHARGER LES LIGUES
            # ═══════════════════════════════════════════════════════════════════
            print(f"{Colors.CYAN}📊 Chargement ligues par équipe...{Colors.END}")
            
            league_rows = await conn.fetch("""
                SELECT DISTINCT team_name, league 
                FROM team_intelligence
            """)
            league_map = {r['team_name']: r['league'] for r in league_rows}
            print(f"   → {len(league_map)} équipes avec ligue")
            
            # ═══════════════════════════════════════════════════════════════════
            # 6. CHARGER LES COTES MOYENNES PAR ÉQUIPE
            # ═══════════════════════════════════════════════════════════════════
            print(f"{Colors.CYAN}📊 Chargement cotes moyennes...{Colors.END}")
            
            odds_rows = await conn.fetch("""
                SELECT team_name, market_type, avg_odds
                FROM team_market_profiles
                WHERE is_best_market = true
            """)
            odds_map = {r['team_name']: float(r['avg_odds'] or 1.85) for r in odds_rows}
            print(f"   → {len(odds_map)} équipes avec cotes moyennes")
            
            # ═══════════════════════════════════════════════════════════════════
            # 7. CONSTRUIRE LES ANALYSES PAR ÉQUIPE
            # ═══════════════════════════════════════════════════════════════════
            print(f"\n{Colors.CYAN}🔬 Construction des analyses par équipe...{Colors.END}")
            
            for i, row in enumerate(strategy_rows, 1):
                team_name = row['team_name']
                losses = int(row['losses'] or 0)
                unlucky = int(row['unlucky_count'] or 0)
                bad_analysis = int(row['bad_analysis_count'] or 0)
                
                # Calcul Mal% et Err%
                unlucky_pct = (unlucky / losses * 100) if losses > 0 else 0
                error_pct = (bad_analysis / losses * 100) if losses > 0 else 0
                
                # Matchs joués
                matches_played = matches_map.get(team_name, 0)
                
                # Style - gérer None
                raw_style = style_map.get(team_name)
                style_value = raw_style[:10] if raw_style else 'N/A'
                
                # Tier
                tier, tier_emoji = self.get_tier(i, float(row['profit'] or 0), float(row['win_rate'] or 0))
                
                # Bet frequency
                bet_freq = (row['bets'] / matches_played * 100) if matches_played > 0 else 0
                
                team = TeamAnalysis(
                    rank=i,
                    team_name=team_name,
                    best_strategy=row['strategy_name'],
                    strategy_family=self.get_strategy_family(row['strategy_name']),
                    matches_played=matches_played,
                    bets=int(row['bets'] or 0),
                    wins=int(row['wins'] or 0),
                    losses=losses,
                    win_rate=float(row['win_rate'] or 0),
                    roi=float(row['roi'] or 0),
                    pnl=float(row['profit'] or 0),
                    unlucky_count=unlucky,
                    bad_analysis_count=bad_analysis,
                    unlucky_pct=unlucky_pct,
                    error_pct=error_pct,
                    style=style_map.get(team_name, 'N/A')[:10] if style_map.get(team_name) else 'N/A',
                    best_market=market_map.get(team_name, {}).get('market', 'N/A'),
                    market_roi=float(market_map.get(team_name, {}).get('roi', 0) or 0),
                    tier=tier,
                    tier_emoji=tier_emoji,
                    avg_odds=float(odds_map.get(team_name, 1.85) or 1.85),
                    bet_frequency=bet_freq,
                    league=league_map.get(team_name, 'N/A')
                )
                self.teams.append(team)
            
            print(f"   → {len(self.teams)} équipes analysées")
            
            # ═══════════════════════════════════════════════════════════════════
            # 8. CALCULER LES STATS GLOBALES
            # ═══════════════════════════════════════════════════════════════════
            self.total_teams = len(self.teams)
            self.total_bets = sum(t.bets for t in self.teams)
            self.total_wins = sum(t.wins for t in self.teams)
            self.total_losses = sum(t.losses for t in self.teams)
            self.total_pnl = sum(t.pnl for t in self.teams)
            self.global_wr = (self.total_wins / self.total_bets * 100) if self.total_bets > 0 else 0
            self.global_roi = (self.total_pnl / self.total_bets * 100) if self.total_bets > 0 else 0
            self.profitable_count = sum(1 for t in self.teams if t.pnl > 0)
            self.losing_count = sum(1 for t in self.teams if t.pnl <= 0)
            
            # ═══════════════════════════════════════════════════════════════════
            # 9. ANALYSER PAR STRATÉGIE
            # ═══════════════════════════════════════════════════════════════════
            for team in self.teams:
                strat = team.best_strategy
                if strat not in self.strategies:
                    self.strategies[strat] = StrategyAnalysis(
                        name=strat,
                        family=team.strategy_family
                    )
                s = self.strategies[strat]
                s.teams_count += 1
                s.total_bets += team.bets
                s.total_wins += team.wins
                s.total_losses += team.losses
                s.total_pnl += team.pnl
                if team.pnl > s.best_team_pnl:
                    s.best_team = team.team_name
                    s.best_team_pnl = team.pnl
            
            for s in self.strategies.values():
                s.win_rate = (s.total_wins / s.total_bets * 100) if s.total_bets > 0 else 0
                s.avg_roi = (s.total_pnl / s.total_bets * 100) if s.total_bets > 0 else 0
            
            # ═══════════════════════════════════════════════════════════════════
            # 10. ANALYSER PAR TIER
            # ═══════════════════════════════════════════════════════════════════
            for team in self.teams:
                tier = team.tier
                if tier not in self.tiers:
                    self.tiers[tier] = TierAnalysis(name=tier, emoji=team.tier_emoji)
                t = self.tiers[tier]
                t.teams_count += 1
                t.total_bets += team.bets
                t.total_wins += team.wins
                t.total_pnl += team.pnl
            
            for t in self.tiers.values():
                t.win_rate = (t.total_wins / t.total_bets * 100) if t.total_bets > 0 else 0
            
            # ═══════════════════════════════════════════════════════════════════
            # 11. ANALYSER PAR LIGUE
            # ═══════════════════════════════════════════════════════════════════
            for team in self.teams:
                league = team.league
                if league not in self.leagues:
                    self.leagues[league] = {'teams': 0, 'bets': 0, 'wins': 0, 'pnl': 0}
                self.leagues[league]['teams'] += 1
                self.leagues[league]['bets'] += team.bets
                self.leagues[league]['wins'] += team.wins
                self.leagues[league]['pnl'] += team.pnl
    
    def print_header(self):
        """Affiche l'en-tête du rapport"""
        print(f"\n{'═'*160}")
        print(f"║{Colors.BOLD}{Colors.GOLD}                                    🏦 QUANTUM BACKTEST V4.0 INSTITUTIONNEL - HEDGE FUND GRADE                                         {Colors.END}║")
        print(f"{'═'*160}")
        print(f"║{Colors.CYAN}  📅 Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}{' '*120}║")
        print(f"║{Colors.CYAN}  🎯 Principe: L'ÉQUIPE génère le ROI, pas la stratégie générique (ADN Unique par équipe){Colors.END}{' '*51}║")
        print(f"{'═'*160}\n")
    
    def print_global_summary(self):
        """Affiche le résumé global"""
        print(f"{'┌'+'─'*158+'┐'}")
        print(f"│{Colors.BOLD}{Colors.GOLD} 📊 RÉSUMÉ GLOBAL - PERFORMANCE HEDGE FUND{Colors.END}{' '*114}│")
        print(f"{'├'+'─'*158+'┤'}")
        
        # Ligne 1: Équipes
        profitable_pct = (self.profitable_count / self.total_teams * 100) if self.total_teams > 0 else 0
        print(f"│ {'📈 Équipes Analysées:':<30} {Colors.BOLD}{self.total_teams}{Colors.END} "
              f"({Colors.GREEN}{self.profitable_count} profitables ({profitable_pct:.0f}%){Colors.END} | "
              f"{Colors.RED}{self.losing_count} en surveillance{Colors.END}){' '*50}│")
        
        # Ligne 2: Paris
        print(f"│ {'📊 Total Paris:':<30} {Colors.BOLD}{self.total_bets}{Colors.END} "
              f"({Colors.GREEN}{self.total_wins}W{Colors.END} / {Colors.RED}{self.total_losses}L{Colors.END}){' '*80}│")
        
        # Ligne 3: Win Rate
        wr_color = Colors.GREEN if self.global_wr >= 70 else Colors.YELLOW if self.global_wr >= 60 else Colors.RED
        print(f"│ {'🎯 Win Rate Global:':<30} {wr_color}{Colors.BOLD}{self.global_wr:.1f}%{Colors.END}{' '*112}│")
        
        # Ligne 4: ROI
        roi_color = Colors.GREEN if self.global_roi >= 50 else Colors.YELLOW if self.global_roi >= 20 else Colors.RED
        print(f"│ {'💹 ROI Global:':<30} {roi_color}{Colors.BOLD}{self.global_roi:+.1f}%{Colors.END}{' '*111}│")
        
        # Ligne 5: P&L
        pnl_color = Colors.GREEN if self.total_pnl > 0 else Colors.RED
        print(f"│ {'💰 P&L Total:':<30} {pnl_color}{Colors.BOLD}{self.total_pnl:+.1f}u{Colors.END}{' '*110}│")
        
        # Ligne 6: Pertes
        total_unlucky = sum(t.unlucky_count for t in self.teams)
        total_bad = sum(t.bad_analysis_count for t in self.teams)
        unlucky_pct = (total_unlucky / self.total_losses * 100) if self.total_losses > 0 else 0
        bad_pct = (total_bad / self.total_losses * 100) if self.total_losses > 0 else 0
        print(f"│ {'🍀 Analyse Pertes:':<30} Malchance: {Colors.YELLOW}{total_unlucky} ({unlucky_pct:.0f}%){Colors.END} | "
              f"Erreur Analyse: {Colors.RED}{total_bad} ({bad_pct:.0f}%){Colors.END}{' '*58}│")
        
        print(f"{'└'+'─'*158+'┘'}\n")
    
    def print_tier_analysis(self):
        """Affiche l'analyse par tier"""
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.PURPLE} 🏅 ANALYSE PAR TIER{Colors.END}{' '*99}│")
        print(f"{'├'+'─'*120+'┤'}")
        print(f"│ {'Tier':<12} │ {'Équipes':>8} │ {'Paris':>7} │ {'Wins':>6} │ {'WR%':>7} │ {'P&L':>10} │ {'ROI%':>8} │ {'Description':<40} │")
        print(f"{'├'+'─'*120+'┤'}")
        
        tier_order = ['ELITE', 'GOLD', 'SILVER', 'BRONZE', 'WATCH']
        tier_desc = {
            'ELITE': 'Top performers, ROI > 100%',
            'GOLD': 'Excellents, ROI 50-100%',
            'SILVER': 'Bons, ROI 20-50%',
            'BRONZE': 'Corrects, ROI > 0%',
            'WATCH': 'En surveillance, ROI négatif'
        }
        
        for tier_name in tier_order:
            if tier_name in self.tiers:
                t = self.tiers[tier_name]
                roi = (t.total_pnl / t.total_bets * 100) if t.total_bets > 0 else 0
                color = TIER_THRESHOLDS[tier_name]['color']
                print(f"│ {t.emoji} {tier_name:<9} │ {t.teams_count:>8} │ {t.total_bets:>7} │ {t.total_wins:>6} │ "
                      f"{color}{t.win_rate:>6.1f}%{Colors.END} │ {color}{t.total_pnl:>+9.1f}u{Colors.END} │ "
                      f"{roi:>+7.1f}% │ {tier_desc.get(tier_name, ''):<40} │")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def print_strategy_analysis(self):
        """Affiche l'analyse par stratégie"""
        print(f"{'┌'+'─'*140+'┐'}")
        print(f"│{Colors.BOLD}{Colors.BLUE} 📈 ANALYSE PAR STRATÉGIE{Colors.END}{' '*113}│")
        print(f"{'├'+'─'*140+'┤'}")
        print(f"│ {'#':<3} │ {'Stratégie':<25} │ {'Famille':<12} │ {'Équipes':>8} │ {'Paris':>7} │ {'WR%':>7} │ {'P&L':>10} │ {'ROI%':>8} │ {'Best Team':<25} │")
        print(f"{'├'+'─'*140+'┤'}")
        
        sorted_strats = sorted(self.strategies.values(), key=lambda x: x.total_pnl, reverse=True)
        
        for i, s in enumerate(sorted_strats, 1):
            emoji = "✅" if s.total_pnl > 0 else "❌"
            color = Colors.GREEN if s.total_pnl > 0 else Colors.RED
            print(f"│ {emoji}{i:<2} │ {s.name:<25} │ {s.family:<12} │ {s.teams_count:>8} │ {s.total_bets:>7} │ "
                  f"{color}{s.win_rate:>6.1f}%{Colors.END} │ {color}{s.total_pnl:>+9.1f}u{Colors.END} │ "
                  f"{s.avg_roi:>+7.1f}% │ {s.best_team[:24]:<25} │")
        
        print(f"{'└'+'─'*140+'┘'}\n")
    
    def print_league_analysis(self):
        """Affiche l'analyse par ligue"""
        print(f"{'┌'+'─'*100+'┐'}")
        print(f"│{Colors.BOLD}{Colors.ORANGE} 🌍 ANALYSE PAR LIGUE{Colors.END}{' '*78}│")
        print(f"{'├'+'─'*100+'┤'}")
        print(f"│ {'Ligue':<30} │ {'Équipes':>8} │ {'Paris':>7} │ {'Wins':>6} │ {'WR%':>7} │ {'P&L':>10} │ {'ROI%':>8} │")
        print(f"{'├'+'─'*100+'┤'}")
        
        sorted_leagues = sorted(
            [(k, v) for k, v in self.leagues.items() if k and k != 'N/A'],
            key=lambda x: x[1]['pnl'], 
            reverse=True
        )
        
        for league, data in sorted_leagues[:10]:
            wr = (data['wins'] / data['bets'] * 100) if data['bets'] > 0 else 0
            roi = (data['pnl'] / data['bets'] * 100) if data['bets'] > 0 else 0
            emoji = "✅" if data['pnl'] > 0 else "❌"
            color = Colors.GREEN if data['pnl'] > 0 else Colors.RED
            print(f"│ {emoji} {league[:28]:<28} │ {data['teams']:>8} │ {data['bets']:>7} │ {data['wins']:>6} │ "
                  f"{wr:>6.1f}% │ {color}{data['pnl']:>+9.1f}u{Colors.END} │ {roi:>+7.1f}% │")
        
        print(f"{'└'+'─'*100+'┘'}\n")
    
    def print_full_table(self):
        """Affiche le tableau complet des 92 équipes"""
        print(f"{'╔'+'═'*200+'╗'}")
        print(f"║{Colors.BOLD}{Colors.GOLD}                                                    🏆 TABLEAU COMPLET - {self.total_teams} ÉQUIPES ADN UNIQUE                                                           {Colors.END}║")
        print(f"{'╠'+'═'*200+'╣'}")
        
        # En-tête
        header = (f"║ {'#':<3} │ {'Équipe':<22} │ {'Best Strategy':<20} │ {'Style':<10} │ "
                  f"{'Match':>5} │ {'Bets':>4} │ {'W':>3} │ {'L':>3} │ {'WR%':>6} │ {'ROI%':>7} │ "
                  f"{'P&L':>8} │ {'Mal%':>5} │ {'Err%':>5} │ {'Freq%':>5} │ {'Best Market':<12} │ {'Ligue':<20} ║")
        print(header)
        print(f"{'╠'+'═'*200+'╣'}")
        
        # Données
        for t in self.teams:
            # Gérer les None
            best_market = t.best_market if t.best_market else 'N/A'
            league = t.league if t.league else 'N/A'
            style = t.style if t.style else 'N/A'
            
            # Couleurs conditionnelles
            wr_color = Colors.GREEN if t.win_rate >= 75 else Colors.YELLOW if t.win_rate >= 65 else Colors.RED
            pnl_color = Colors.GREEN if t.pnl > 0 else Colors.RED
            mal_color = Colors.YELLOW if t.unlucky_pct > 70 else Colors.END
            err_color = Colors.RED if t.error_pct > 30 else Colors.END
            
            # Formatage
            wr_str = f"{t.win_rate:>5.1f}%"
            roi_str = f"{t.roi:>+6.1f}%"
            pnl_str = f"{t.pnl:>+7.1f}u"
            mal_str = f"{t.unlucky_pct:>4.0f}%" if t.losses > 0 else "  -  "
            err_str = f"{t.error_pct:>4.0f}%" if t.losses > 0 else "  -  "
            freq_str = f"{t.bet_frequency:>4.0f}%"
            
            row = (f"║ {t.tier_emoji}{t.rank:<2} │ {t.team_name[:21]:<22} │ {t.best_strategy[:19]:<20} │ {style[:9]:<10} │ "
                   f"{t.matches_played:>5} │ {t.bets:>4} │ {t.wins:>3} │ {t.losses:>3} │ "
                   f"{wr_color}{wr_str}{Colors.END} │ {roi_str} │ "
                   f"{pnl_color}{pnl_str}{Colors.END} │ {mal_color}{mal_str}{Colors.END} │ {err_color}{err_str}{Colors.END} │ "
                   f"{freq_str} │ {best_market[:11]:<12} │ {league[:19]:<20} ║")
            print(row)
        
        print(f"{'╚'+'═'*200+'╝'}\n")
    
    def print_elite_section(self):
        """Affiche la section ÉLITE"""
        elite = [t for t in self.teams if t.tier == 'ELITE']
        
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.GOLD} 💎 SECTION ÉLITE - TOP PERFORMERS (WR ≥ 80%, P&L ≥ 15u){Colors.END}{' '*62}│")
        print(f"{'├'+'─'*120+'┤'}")
        
        if elite:
            for t in elite:
                diagnostic = f"100% Malchance" if t.unlucky_pct == 100 else f"Mal {t.unlucky_pct:.0f}% / Err {t.error_pct:.0f}%"
                best_market = t.best_market if t.best_market else 'N/A'
                print(f"│ 💎 {t.team_name:<22} │ {t.best_strategy:<20} │ {t.bets:>2}p │ "
                      f"{Colors.GREEN}{t.win_rate:.0f}% WR{Colors.END} │ {Colors.GREEN}+{t.pnl:.1f}u{Colors.END} │ "
                      f"{diagnostic:<20} │ {best_market:<10} │")
        else:
            print(f"│ Aucune équipe ÉLITE (critères: WR ≥ 80% ET P&L ≥ 15u){' '*64}│")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def print_gold_section(self):
        """Affiche la section GOLD"""
        gold = [t for t in self.teams if t.tier == 'GOLD']
        
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.YELLOW} 🏆 SECTION GOLD - EXCELLENTS (WR ≥ 70%, P&L ≥ 8u){Colors.END}{' '*68}│")
        print(f"{'├'+'─'*120+'┤'}")
        
        if gold:
            for t in gold[:15]:
                diagnostic = f"100% Malchance" if t.unlucky_pct == 100 else f"Mal {t.unlucky_pct:.0f}% / Err {t.error_pct:.0f}%"
                best_market = t.best_market if t.best_market else 'N/A'
                print(f"│ 🏆 {t.team_name:<22} │ {t.best_strategy:<20} │ {t.bets:>2}p │ "
                      f"{Colors.GREEN}{t.win_rate:.0f}% WR{Colors.END} │ {Colors.GREEN}+{t.pnl:.1f}u{Colors.END} │ "
                      f"{diagnostic:<20} │ {best_market:<10} │")
        else:
            print(f"│ Aucune équipe GOLD{' '*100}│")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def print_watch_section(self):
        """Affiche la section EN SURVEILLANCE"""
        watch = [t for t in self.teams if t.tier == 'WATCH']
        
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.RED} ⚠️ EN SURVEILLANCE - DANGER (P&L < 0 ou WR < 55%){Colors.END}{' '*67}│")
        print(f"{'├'+'─'*120+'┤'}")
        
        if watch:
            for t in watch:
                if t.unlucky_pct > 70:
                    diagnostic = f"MALCHANCE ({t.unlucky_pct:.0f}%)"
                    diag_color = Colors.YELLOW
                elif t.error_pct > 30:
                    diagnostic = f"ERREUR ANALYSE ({t.error_pct:.0f}%)"
                    diag_color = Colors.RED
                else:
                    diagnostic = f"MIXTE (M:{t.unlucky_pct:.0f}%/E:{t.error_pct:.0f}%)"
                    diag_color = Colors.ORANGE
                
                print(f"│ ⚠️ {t.team_name:<22} │ {t.bets:>2}p │ {t.wins}W/{t.losses}L │ "
                      f"{Colors.RED}{t.win_rate:.0f}% WR{Colors.END} │ {Colors.RED}{t.pnl:+.1f}u{Colors.END} │ "
                      f"{diag_color}{diagnostic:<25}{Colors.END} │ Action: SURVEILLER │")
        else:
            print(f"│ ✅ Aucune équipe en danger !{' '*90}│")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def print_insights(self):
        """Affiche les insights quant"""
        print(f"{'┌'+'─'*140+'┐'}")
        print(f"│{Colors.BOLD}{Colors.CYAN} 🧠 INSIGHTS QUANTITATIFS - HEDGE FUND ANALYSIS{Colors.END}{' '*91}│")
        print(f"{'├'+'─'*140+'┤'}")
        
        # 1. Meilleure stratégie
        best_strat = max(self.strategies.values(), key=lambda x: x.total_pnl)
        print(f"│ 📈 Meilleure Stratégie: {Colors.GREEN}{best_strat.name}{Colors.END} "
              f"({best_strat.teams_count} équipes, {best_strat.total_bets} paris, +{best_strat.total_pnl:.1f}u){' '*45}│")
        
        # 2. Équipes 100% WR
        perfect = [t for t in self.teams if t.win_rate == 100 and t.bets >= 3]
        perfect_names = ', '.join([t.team_name for t in perfect[:5]]) if perfect else 'Aucune'
        print(f"│ 🎯 Équipes 100% WR (≥3 paris): {Colors.GREEN}{len(perfect)}{Colors.END} "
              f"→ {perfect_names}{' '*50}│")
        
        # 3. Ratio global Malchance vs Erreur
        total_unlucky = sum(t.unlucky_count for t in self.teams)
        total_bad = sum(t.bad_analysis_count for t in self.teams)
        print(f"│ 🍀 Ratio Pertes: Malchance {Colors.YELLOW}{total_unlucky}{Colors.END} ({total_unlucky/self.total_losses*100:.0f}%) "
              f"vs Erreur Analyse {Colors.RED}{total_bad}{Colors.END} ({total_bad/self.total_losses*100:.0f}%) "
              f"→ {Colors.GREEN}L'analyse est correcte dans {100-total_bad/self.total_losses*100:.0f}% des cas{Colors.END}{' '*5}│")
        
        # 4. ROI moyen profitables
        profitable = [t for t in self.teams if t.pnl > 0]
        avg_roi = sum(t.roi for t in profitable) / len(profitable) if profitable else 0
        avg_wr = sum(t.win_rate for t in profitable) / len(profitable) if profitable else 0
        print(f"│ 💰 Profitables ({len(profitable)} équipes): ROI moyen {Colors.GREEN}{avg_roi:.1f}%{Colors.END}, "
              f"WR moyen {Colors.GREEN}{avg_wr:.1f}%{Colors.END}{' '*60}│")
        
        # 5. Top 5 P&L
        top5 = self.teams[:5]
        print(f"│ 🏆 Top 5 P&L: {', '.join([f'{t.team_name} (+{t.pnl:.0f}u)' for t in top5])}{' '*35}│")
        
        # 6. Fréquence de paris
        avg_freq = sum(t.bet_frequency for t in self.teams if t.matches_played > 0) / len([t for t in self.teams if t.matches_played > 0])
        print(f"│ 📊 Fréquence de paris moyenne: {avg_freq:.0f}% des matchs → "
              f"Sélectif et discipliné{' '*62}│")
        
        # 7. Meilleure ligue
        valid_leagues = {k: v for k, v in self.leagues.items() if k and k != 'N/A'}
        if valid_leagues:
            best_league = max(valid_leagues.items(), key=lambda x: x[1]['pnl'])
            print(f"│ 🌍 Meilleure Ligue: {Colors.GREEN}{best_league[0]}{Colors.END} "
                  f"({best_league[1]['teams']} équipes, +{best_league[1]['pnl']:.1f}u){' '*65}│")
        else:
            print(f"│ 🌍 Meilleure Ligue: Données non disponibles{' '*90}│")
        
        print(f"{'└'+'─'*140+'┘'}\n")
    
    def print_recommendations(self):
        """Affiche les recommandations"""
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.GREEN} 💡 RECOMMANDATIONS STRATÉGIQUES{Colors.END}{' '*85}│")
        print(f"{'├'+'─'*120+'┤'}")
        
        # 1. Équipes à prioriser
        elite_gold = [t for t in self.teams if t.tier in ['ELITE', 'GOLD']]
        print(f"│ ✅ PRIORISER: {len(elite_gold)} équipes ELITE/GOLD → Focus sur ces équipes pour maximiser le ROI{' '*35}│")
        
        # 2. Équipes en malchance pure
        pure_unlucky = [t for t in self.teams if t.unlucky_pct == 100 and t.pnl < 0]
        if pure_unlucky:
            unlucky_names = ', '.join([t.team_name for t in pure_unlucky[:3]])
            print(f"│ 🍀 PATIENCE: {len(pure_unlucky)} équipes en malchance pure ({unlucky_names}) → Variance, continuer{' '*20}│")
        
        # 3. Équipes avec erreurs
        with_errors = [t for t in self.teams if t.error_pct > 30]
        if with_errors:
            print(f"│ 🔍 RÉVISER: {len(with_errors)} équipes avec erreurs analyse > 30% → Revoir le modèle pour ces équipes{' '*27}│")
        
        # 4. Stratégies gagnantes
        winning_strats = [s for s in self.strategies.values() if s.total_pnl > 0]
        best_strat_name = winning_strats[0].name if winning_strats else 'N/A'
        print(f"│ 📈 STRATÉGIES: {len(winning_strats)}/{len(self.strategies)} stratégies positives → "
              f"Favoriser {best_strat_name}{' '*40}│")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def save_report(self):
        """Sauvegarde le rapport en JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'version': 'V4.0 Institutionnel',
            'summary': {
                'total_teams': self.total_teams,
                'profitable': self.profitable_count,
                'losing': self.losing_count,
                'total_bets': self.total_bets,
                'total_wins': self.total_wins,
                'total_losses': self.total_losses,
                'global_wr': round(self.global_wr, 2),
                'global_roi': round(self.global_roi, 2),
                'total_pnl': round(self.total_pnl, 2),
                'total_unlucky': sum(t.unlucky_count for t in self.teams),
                'total_bad_analysis': sum(t.bad_analysis_count for t in self.teams)
            },
            'teams': [
                {
                    'rank': t.rank,
                    'name': t.team_name,
                    'tier': t.tier,
                    'strategy': t.best_strategy,
                    'strategy_family': t.strategy_family,
                    'style': t.style,
                    'league': t.league,
                    'matches_played': t.matches_played,
                    'bets': t.bets,
                    'wins': t.wins,
                    'losses': t.losses,
                    'win_rate': round(t.win_rate, 1),
                    'roi': round(t.roi, 1),
                    'pnl': round(t.pnl, 1),
                    'unlucky_count': t.unlucky_count,
                    'bad_analysis_count': t.bad_analysis_count,
                    'unlucky_pct': round(t.unlucky_pct, 0),
                    'error_pct': round(t.error_pct, 0),
                    'best_market': t.best_market,
                    'market_roi': round(t.market_roi, 1),
                    'avg_odds': round(t.avg_odds, 2),
                    'bet_frequency': round(t.bet_frequency, 1)
                }
                for t in self.teams
            ],
            'strategies': [
                {
                    'name': s.name,
                    'family': s.family,
                    'teams': s.teams_count,
                    'bets': s.total_bets,
                    'wins': s.total_wins,
                    'win_rate': round(s.win_rate, 1),
                    'pnl': round(s.total_pnl, 1),
                    'roi': round(s.avg_roi, 1),
                    'best_team': s.best_team,
                    'best_team_pnl': round(s.best_team_pnl, 1)
                }
                for s in sorted(self.strategies.values(), key=lambda x: x.total_pnl, reverse=True)
            ],
            'tiers': {
                name: {
                    'teams': t.teams_count,
                    'bets': t.total_bets,
                    'wins': t.total_wins,
                    'win_rate': round(t.win_rate, 1),
                    'pnl': round(t.total_pnl, 1)
                }
                for name, t in self.tiers.items()
            },
            'leagues': {
                name: {
                    'teams': data['teams'],
                    'bets': data['bets'],
                    'wins': data['wins'],
                    'pnl': round(data['pnl'], 1)
                }
                for name, data in sorted(self.leagues.items(), key=lambda x: x[1]['pnl'], reverse=True)
                if name != 'N/A'
            }
        }
        
        filename = f"quantum_v4_institutional_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: {filename}{Colors.END}")
        
        # Sauvegarder aussi une version fixe
        with open('quantum_v4_institutional_latest.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: quantum_v4_institutional_latest.json{Colors.END}")
    
    async def run(self):
        """Exécute le rapport complet"""
        await self.connect()
        await self.load_all_data()
        
        # Affichage complet
        self.print_header()
        self.print_global_summary()
        self.print_tier_analysis()
        self.print_strategy_analysis()
        self.print_league_analysis()
        self.print_full_table()
        self.print_elite_section()
        self.print_gold_section()
        self.print_watch_section()
        self.print_insights()
        self.print_recommendations()
        
        # Sauvegarde
        self.save_report()
        
        await self.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description='Quantum V4 Institutionnel - Hedge Fund Report')
    parser.add_argument('--json-only', action='store_true', help='Générer uniquement le JSON sans affichage')
    args = parser.parse_args()
    
    engine = QuantumV4Institutionnel()
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║     🧬 QUANTUM V5.0 ADN EXPLORER - HEDGE FUND GRADE                                                                                   ║
║                                                                                                                                       ║
║  ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════   ║
║                                                                                                                                       ║
║  📊 15 VECTEURS ADN ANALYSÉS:                                                                                                         ║
║     1. MARKET DNA      - Best strategy, specialists                                                                                   ║
║     2. CONTEXT DNA     - Home/Away strength, tendencies                                                                               ║
║     3. PSYCHE DNA      - Killer instinct, panic, comeback                                                                             ║
║     4. TEMPORAL DNA    - Diesel factor, fast starter, periods                                                                         ║
║     5. NEMESIS DNA     - Verticality, territory, keeper                                                                               ║
║     6. PHYSICAL DNA    - Stamina, pressing, late game                                                                                 ║
║     7. TACTICAL DNA    - Formation, set pieces, open play                                                                             ║
║     8. ROSTER DNA      - MVP dependency, key players                                                                                  ║
║     9. CHAMELEON DNA   - Adaptability, flexibility                                                                                    ║
║    10. LUCK DNA        - Finishing/defensive luck                                                                                     ║
║    11. SENTIMENT DNA   - Market sentiment (future)                                                                                    ║
║    12. CURRENT SEASON  - 2025/2026 stats                                                                                              ║
║    13. META DNA        - Audit rank, source                                                                                           ║
║    14. FRICTION SIGS   - Matchup signatures (future)                                                                                  ║
║    15. LEAGUE          - Competition                                                                                                  ║
║                                                                                                                                       ║
║  🎯 PRINCIPE MYA: "L'ADN UNIQUE génère le ROI, pas la stratégie générique"                                                            ║
║                                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import asyncpg
from datetime import datetime
from typing import Dict, List, Optional, Any
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

# Couleurs ANSI
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
    PINK = '\033[38;5;213m'

# Mapping des ligues
LEAGUE_DISPLAY = {
    'EPL': 'Premier League',
    'LaLiga': 'La Liga',
    'SerieA': 'Serie A',
    'Bundesliga': 'Bundesliga',
    'Ligue1': 'Ligue 1',
    'Championship': 'Championship',
    'Liga2': 'La Liga 2',
    'SerieB': 'Serie B',
    'Bundesliga2': 'Bundesliga 2',
    'Ligue2': 'Ligue 2'
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamADN:
    """ADN complet d'une équipe"""
    # Identification
    rank: int = 0
    team_name: str = ""
    league: str = "N/A"
    tier: str = "N/A"
    
    # Performance (from team_strategies)
    best_strategy: str = ""
    bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    roi: float = 0.0
    pnl: float = 0.0
    unlucky_count: int = 0
    bad_analysis_count: int = 0
    
    # Market DNA
    over_specialist: bool = False
    under_specialist: bool = False
    btts_yes_specialist: bool = False
    btts_no_specialist: bool = False
    profitable_strategies: int = 0
    
    # Context DNA
    style: str = "N/A"
    home_strength: int = 0
    away_strength: int = 0
    btts_tendency: int = 0
    goals_tendency: int = 0
    draw_tendency: int = 0
    
    # Psyche DNA
    killer_instinct: float = 0.0
    panic_factor: float = 0.0
    comeback_mentality: float = 0.0
    lead_protection: float = 0.0
    psyche_profile: str = "N/A"
    
    # Temporal DNA
    diesel_factor: float = 0.0
    fast_starter: float = 0.0
    temporal_profile: str = "N/A"
    first_half_xg_pct: float = 0.0
    second_half_xg_pct: float = 0.0
    
    # Nemesis DNA
    verticality: float = 0.0
    territorial_dominance: float = 0.0
    keeper_status: str = "N/A"
    nemesis_style: str = "N/A"
    
    # Physical DNA
    stamina_profile: str = "N/A"
    pressing_intensity: float = 0.0
    late_game_dominance: float = 0.0
    late_game_threat: str = "N/A"
    
    # Tactical DNA
    main_formation: str = "N/A"
    set_piece_threat: float = 0.0
    open_play_reliance: float = 0.0
    tactical_profile: str = "N/A"
    
    # Roster DNA
    mvp_name: str = "N/A"
    mvp_dependency: float = 0.0
    top3_dependency: float = 0.0
    mvp_missing_impact: str = "N/A"
    
    # Chameleon DNA
    adaptability_index: float = 0.0
    tempo_flexibility: float = 0.0
    chameleon_profile: str = "N/A"
    
    # Luck DNA
    total_luck: float = 0.0
    luck_profile: str = "N/A"
    finishing_luck: float = 0.0
    defensive_luck: float = 0.0
    
    # Current Season
    season_ppg: float = 0.0
    season_goals: int = 0
    season_xg_avg: float = 0.0
    season_clinical: bool = False
    season_matches: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM V5 ADN EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumV5ADNExplorer:
    """V5 ADN Explorer - Analyse complète des 15 vecteurs"""
    
    def __init__(self):
        self.pool = None
        self.teams: List[TeamADN] = []
        
        # Stats globales
        self.total_teams = 0
        self.total_bets = 0
        self.total_pnl = 0.0
        self.global_wr = 0.0
        
        # Stats par ligue
        self.leagues: Dict[str, dict] = {}
        
        # Stats par vecteur
        self.psyche_stats = {}
        self.tactical_stats = {}
        self.temporal_stats = {}
        
    async def connect(self):
        """Connexion à la base de données"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print(f"{Colors.GREEN}✅ Connexion PostgreSQL établie{Colors.END}")
        
    async def close(self):
        """Fermeture de la connexion"""
        if self.pool:
            await self.pool.close()
            print(f"{Colors.CYAN}🔌 Connexion fermée{Colors.END}")
    
    def safe_get(self, data: dict, *keys, default=None):
        """Récupération sécurisée dans un dict imbriqué"""
        try:
            result = data
            for key in keys:
                if result is None:
                    return default
                result = result.get(key, default) if isinstance(result, dict) else default
            return result if result is not None else default
        except:
            return default
    
    async def load_all_data(self):
        """Charge toutes les données ADN"""
        async with self.pool.acquire() as conn:
            
            # ═══════════════════════════════════════════════════════════════════
            # 1. CHARGER LES STRATÉGIES (source performance)
            # ═══════════════════════════════════════════════════════════════════
            print(f"\n{Colors.CYAN}📊 Chargement quantum.team_strategies...{Colors.END}")
            
            strategy_rows = await conn.fetch("""
                SELECT 
                    team_name, strategy_name, bets, wins, losses,
                    win_rate, roi, profit, unlucky_count, bad_analysis_count
                FROM quantum.team_strategies 
                WHERE is_best_strategy = true 
                ORDER BY profit DESC
            """)
            strategy_map = {r['team_name']: r for r in strategy_rows}
            print(f"   → {len(strategy_rows)} équipes avec best_strategy")
            
            # ═══════════════════════════════════════════════════════════════════
            # 2. CHARGER LES PROFILS ADN COMPLETS
            # ═══════════════════════════════════════════════════════════════════
            print(f"{Colors.CYAN}📊 Chargement quantum.team_profiles avec ADN...{Colors.END}")
            
            profile_rows = await conn.fetch("""
                SELECT 
                    team_name, tier, current_style, quantum_dna
                FROM quantum.team_profiles 
                WHERE quantum_dna IS NOT NULL
            """)
            profile_map = {r['team_name']: r for r in profile_rows}
            print(f"   → {len(profile_rows)} équipes avec ADN complet")
            
            # ═══════════════════════════════════════════════════════════════════
            # 3. CONSTRUIRE LES ANALYSES PAR ÉQUIPE
            # ═══════════════════════════════════════════════════════════════════
            print(f"\n{Colors.CYAN}🧬 Extraction des 15 vecteurs ADN...{Colors.END}")
            
            for i, (team_name, strat) in enumerate(strategy_map.items(), 1):
                profile = profile_map.get(team_name, {})
                dna = profile.get('quantum_dna', {}) if profile else {}
                
                # Parser le JSONB si nécessaire
                if isinstance(dna, str):
                    try:
                        dna = json.loads(dna)
                    except:
                        dna = {}
                
                # Extraire chaque vecteur
                market_dna = dna.get('market_dna', {}) or {}
                context_dna = dna.get('context_dna', {}) or {}
                psyche_dna = dna.get('psyche_dna', {}) or {}
                temporal_dna = dna.get('temporal_dna', {}) or {}
                nemesis_dna = dna.get('nemesis_dna', {}) or {}
                physical_dna = dna.get('physical_dna', {}) or {}
                tactical_dna = dna.get('tactical_dna', {}) or {}
                roster_dna = dna.get('roster_dna', {}) or {}
                chameleon_dna = dna.get('chameleon_dna', {}) or {}
                luck_dna = dna.get('luck_dna', {}) or {}
                current_season = dna.get('current_season', {}) or {}
                empirical = market_dna.get('empirical_profile', {}) or {}
                mvp_data = roster_dna.get('mvp', {}) or {}
                
                # League depuis le JSONB
                league_raw = dna.get('league', 'N/A') or 'N/A'
                league_display = LEAGUE_DISPLAY.get(league_raw, league_raw)
                
                team = TeamADN(
                    rank=i,
                    team_name=team_name,
                    league=league_display,
                    tier=profile.get('tier', 'N/A') if profile else 'N/A',
                    
                    # Performance
                    best_strategy=strat['strategy_name'],
                    bets=int(strat['bets'] or 0),
                    wins=int(strat['wins'] or 0),
                    losses=int(strat['losses'] or 0),
                    win_rate=float(strat['win_rate'] or 0),
                    roi=float(strat['roi'] or 0),
                    pnl=float(strat['profit'] or 0),
                    unlucky_count=int(strat['unlucky_count'] or 0),
                    bad_analysis_count=int(strat['bad_analysis_count'] or 0),
                    
                    # Market DNA
                    over_specialist=empirical.get('over_specialist', False) or False,
                    under_specialist=empirical.get('under_specialist', False) or False,
                    btts_yes_specialist=empirical.get('btts_yes_specialist', False) or False,
                    btts_no_specialist=empirical.get('btts_no_specialist', False) or False,
                    profitable_strategies=market_dna.get('profitable_strategies', 0) or 0,
                    
                    # Context DNA
                    style=context_dna.get('style', 'N/A') or 'N/A',
                    home_strength=int(context_dna.get('home_strength', 0) or 0),
                    away_strength=int(context_dna.get('away_strength', 0) or 0),
                    btts_tendency=int(context_dna.get('btts_tendency', 0) or 0),
                    goals_tendency=int(context_dna.get('goals_tendency', 0) or 0),
                    draw_tendency=int(context_dna.get('draw_tendency', 0) or 0),
                    
                    # Psyche DNA
                    killer_instinct=float(psyche_dna.get('killer_instinct', 0) or 0),
                    panic_factor=float(psyche_dna.get('panic_factor', 0) or 0),
                    comeback_mentality=float(psyche_dna.get('comeback_mentality', 0) or 0),
                    lead_protection=float(psyche_dna.get('lead_protection', 0) or 0),
                    psyche_profile=psyche_dna.get('profile', 'N/A') or 'N/A',
                    
                    # Temporal DNA
                    diesel_factor=float(temporal_dna.get('diesel_factor', 0) or 0),
                    fast_starter=float(temporal_dna.get('fast_starter', 0) or 0),
                    temporal_profile=temporal_dna.get('profile', 'N/A') or 'N/A',
                    first_half_xg_pct=float(temporal_dna.get('first_half_xg_pct', 0) or 0),
                    second_half_xg_pct=float(temporal_dna.get('second_half_xg_pct', 0) or 0),
                    
                    # Nemesis DNA
                    verticality=float(nemesis_dna.get('verticality', 0) or 0),
                    territorial_dominance=float(nemesis_dna.get('territorial_dominance', 0) or 0),
                    keeper_status=nemesis_dna.get('keeper_status', 'N/A') or 'N/A',
                    nemesis_style=nemesis_dna.get('style', 'N/A') or 'N/A',
                    
                    # Physical DNA
                    stamina_profile=physical_dna.get('stamina_profile', 'N/A') or 'N/A',
                    pressing_intensity=float(physical_dna.get('pressing_intensity', 0) or 0),
                    late_game_dominance=float(physical_dna.get('late_game_dominance', 0) or 0),
                    late_game_threat=physical_dna.get('late_game_threat_level', 'N/A') or 'N/A',
                    
                    # Tactical DNA
                    main_formation=tactical_dna.get('main_formation', 'N/A') or 'N/A',
                    set_piece_threat=float(tactical_dna.get('set_piece_threat', 0) or 0),
                    open_play_reliance=float(tactical_dna.get('open_play_reliance', 0) or 0),
                    tactical_profile=tactical_dna.get('tactical_profile', 'N/A') or 'N/A',
                    
                    # Roster DNA
                    mvp_name=mvp_data.get('name', 'N/A') or 'N/A',
                    mvp_dependency=float(mvp_data.get('dependency_score', 0) or 0),
                    top3_dependency=float(roster_dna.get('top3_dependency', 0) or 0),
                    mvp_missing_impact=roster_dna.get('mvp_missing_impact', 'N/A') or 'N/A',
                    
                    # Chameleon DNA
                    adaptability_index=float(chameleon_dna.get('adaptability_index', 0) or 0),
                    tempo_flexibility=float(chameleon_dna.get('tempo_flexibility', 0) or 0),
                    chameleon_profile=chameleon_dna.get('chameleon_profile', 'N/A') or 'N/A',
                    
                    # Luck DNA
                    total_luck=float(luck_dna.get('total_luck', 0) or 0),
                    luck_profile=luck_dna.get('luck_profile', 'N/A') or 'N/A',
                    finishing_luck=float(luck_dna.get('finishing_luck', 0) or 0),
                    defensive_luck=float(luck_dna.get('defensive_luck', 0) or 0),
                    
                    # Current Season
                    season_ppg=float(current_season.get('ppg', 0) or 0),
                    season_goals=int(current_season.get('goals_for', 0) or 0),
                    season_xg_avg=float(current_season.get('xg_for_avg', 0) or 0),
                    season_clinical=current_season.get('clinical', False) or False,
                    season_matches=int(current_season.get('matches_played', 0) or 0)
                )
                self.teams.append(team)
            
            print(f"   → {len(self.teams)} équipes analysées avec ADN complet")
            
            # ═══════════════════════════════════════════════════════════════════
            # 4. CALCULER LES STATS GLOBALES
            # ═══════════════════════════════════════════════════════════════════
            self.total_teams = len(self.teams)
            self.total_bets = sum(t.bets for t in self.teams)
            self.total_pnl = sum(t.pnl for t in self.teams)
            total_wins = sum(t.wins for t in self.teams)
            self.global_wr = (total_wins / self.total_bets * 100) if self.total_bets > 0 else 0
            
            # Stats par ligue
            for team in self.teams:
                league = team.league
                if league not in self.leagues:
                    self.leagues[league] = {'teams': 0, 'bets': 0, 'wins': 0, 'pnl': 0.0}
                self.leagues[league]['teams'] += 1
                self.leagues[league]['bets'] += team.bets
                self.leagues[league]['wins'] += team.wins
                self.leagues[league]['pnl'] += team.pnl
    
    def print_header(self):
        """Affiche l'en-tête"""
        print(f"\n{'═'*180}")
        print(f"║{Colors.BOLD}{Colors.GOLD}                                           🧬 QUANTUM V5.0 ADN EXPLORER - HEDGE FUND GRADE                                                    {Colors.END}║")
        print(f"{'═'*180}")
        print(f"║{Colors.CYAN}  📅 Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}{' '*140}║")
        print(f"║{Colors.CYAN}  🎯 15 Vecteurs ADN analysés pour {self.total_teams} équipes | {self.total_bets} paris | {self.global_wr:.1f}% WR | {self.total_pnl:+.1f}u P&L{Colors.END}{' '*60}║")
        print(f"{'═'*180}\n")
    
    def print_league_analysis(self):
        """Analyse par ligue"""
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.PURPLE} 🌍 ANALYSE PAR LIGUE{Colors.END}{' '*98}│")
        print(f"{'├'+'─'*120+'┤'}")
        print(f"│ {'Ligue':<20} │ {'Équipes':>8} │ {'Paris':>7} │ {'Wins':>6} │ {'WR%':>7} │ {'P&L':>10} │ {'ROI%':>8} │ {'Top Team':<30} │")
        print(f"{'├'+'─'*120+'┤'}")
        
        sorted_leagues = sorted(
            [(k, v) for k, v in self.leagues.items() if k and k != 'N/A'],
            key=lambda x: x[1]['pnl'],
            reverse=True
        )
        
        for league, data in sorted_leagues:
            wr = (data['wins'] / data['bets'] * 100) if data['bets'] > 0 else 0
            roi = (data['pnl'] / data['bets'] * 100) if data['bets'] > 0 else 0
            emoji = "✅" if data['pnl'] > 0 else "❌"
            color = Colors.GREEN if data['pnl'] > 0 else Colors.RED
            
            # Trouver la meilleure équipe de cette ligue
            best_team = max([t for t in self.teams if t.league == league], key=lambda x: x.pnl, default=None)
            best_team_name = best_team.team_name[:29] if best_team else "N/A"
            
            print(f"│ {emoji} {league[:18]:<18} │ {data['teams']:>8} │ {data['bets']:>7} │ {data['wins']:>6} │ "
                  f"{wr:>6.1f}% │ {color}{data['pnl']:>+9.1f}u{Colors.END} │ {roi:>+7.1f}% │ {best_team_name:<30} │")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def print_main_table(self):
        """Tableau principal avec métriques clés"""
        print(f"{'╔'+'═'*220+'╗'}")
        print(f"║{Colors.BOLD}{Colors.GOLD}                                                         🏆 TABLEAU COMPLET - {self.total_teams} ÉQUIPES ADN UNIQUE                                                                       {Colors.END}║")
        print(f"{'╠'+'═'*220+'╣'}")
        
        # En-tête
        header = (f"║ {'#':<3} │ {'Équipe':<20} │ {'Ligue':<15} │ {'Strategy':<18} │ "
                  f"{'B':>3} │ {'W':>3} │ {'WR%':>6} │ {'P&L':>7} │ "
                  f"{'Kill':>5} │ {'Dies':>5} │ {'Vert':>5} │ {'Press':>5} │ "
                  f"{'Home':>4} │ {'Away':>4} │ {'BTTS':>4} │ {'MVP Dep':>7} │ {'Formation':<10} │ {'Luck':>6} │ {'Style':<10} ║")
        print(header)
        print(f"{'╠'+'═'*220+'╣'}")
        
        # Données
        for t in self.teams:
            # Tier emoji
            if t.pnl >= 15 and t.win_rate >= 80:
                tier_emoji = "💎"
            elif t.pnl >= 8 and t.win_rate >= 70:
                tier_emoji = "🏆"
            elif t.pnl >= 3 and t.win_rate >= 65:
                tier_emoji = "✅"
            elif t.pnl >= 0:
                tier_emoji = "⚪"
            else:
                tier_emoji = "⚠️"
            
            # Couleurs
            wr_color = Colors.GREEN if t.win_rate >= 75 else Colors.YELLOW if t.win_rate >= 65 else Colors.RED
            pnl_color = Colors.GREEN if t.pnl > 0 else Colors.RED
            
            # Formatage sécurisé
            league = t.league[:14] if t.league else 'N/A'
            strategy = t.best_strategy[:17] if t.best_strategy else 'N/A'
            formation = t.main_formation[:9] if t.main_formation else 'N/A'
            style = t.style[:9] if t.style else 'N/A'
            
            row = (f"║ {tier_emoji}{t.rank:<2} │ {t.team_name[:19]:<20} │ {league:<15} │ {strategy:<18} │ "
                   f"{t.bets:>3} │ {t.wins:>3} │ {wr_color}{t.win_rate:>5.1f}%{Colors.END} │ {pnl_color}{t.pnl:>+6.1f}u{Colors.END} │ "
                   f"{t.killer_instinct:>5.2f} │ {t.diesel_factor:>5.2f} │ {t.verticality:>5.1f} │ {t.pressing_intensity:>5.1f} │ "
                   f"{t.home_strength:>4} │ {t.away_strength:>4} │ {t.btts_tendency:>4} │ {t.mvp_dependency:>6.1f}% │ {formation:<10} │ {t.total_luck:>+5.1f} │ {style:<10} ║")
            print(row)
        
        print(f"{'╚'+'═'*220+'╝'}\n")
    
    def print_psyche_analysis(self):
        """Analyse du vecteur Psyche DNA"""
        print(f"{'┌'+'─'*140+'┐'}")
        print(f"│{Colors.BOLD}{Colors.PINK} 🧠 PSYCHE DNA - PROFILS MENTAUX{Colors.END}{' '*106}│")
        print(f"{'├'+'─'*140+'┤'}")
        print(f"│ {'Équipe':<22} │ {'Profile':<12} │ {'Killer':>7} │ {'Panic':>6} │ {'Comeback':>8} │ {'Lead Prot':>9} │ {'Diagnostic':<50} │")
        print(f"{'├'+'─'*140+'┤'}")
        
        # Top 15 killer instinct
        sorted_by_killer = sorted(self.teams, key=lambda x: x.killer_instinct, reverse=True)[:15]
        
        for t in sorted_by_killer:
            # Diagnostic
            if t.killer_instinct > 1.0 and t.panic_factor < 1.0:
                diag = "🦈 PREDATOR - Finisseur de matchs"
                diag_color = Colors.GREEN
            elif t.comeback_mentality > 2.0:
                diag = "🔥 PHOENIX - Revient toujours"
                diag_color = Colors.ORANGE
            elif t.panic_factor > 1.5:
                diag = "😰 FRAGILE - Craque sous pression"
                diag_color = Colors.RED
            elif t.lead_protection > 2.0:
                diag = "🛡️ FORTRESS - Protège son avance"
                diag_color = Colors.CYAN
            else:
                diag = "⚖️ BALANCED - Profil équilibré"
                diag_color = Colors.WHITE
            
            print(f"│ {t.team_name[:21]:<22} │ {t.psyche_profile[:11]:<12} │ {t.killer_instinct:>7.2f} │ "
                  f"{t.panic_factor:>6.2f} │ {t.comeback_mentality:>8.2f} │ {t.lead_protection:>9.2f} │ "
                  f"{diag_color}{diag:<50}{Colors.END} │")
        
        print(f"{'└'+'─'*140+'┘'}\n")
    
    def print_temporal_analysis(self):
        """Analyse du vecteur Temporal DNA"""
        print(f"{'┌'+'─'*130+'┐'}")
        print(f"│{Colors.BOLD}{Colors.ORANGE} ⏱️ TEMPORAL DNA - PATTERNS DE SCORING{Colors.END}{' '*89}│")
        print(f"{'├'+'─'*130+'┤'}")
        print(f"│ {'Équipe':<22} │ {'Profile':<12} │ {'Diesel':>7} │ {'Fast':>6} │ {'1H xG%':>7} │ {'2H xG%':>7} │ {'Diagnostic':<45} │")
        print(f"{'├'+'─'*130+'┤'}")
        
        # Top 15 diesel factor
        sorted_by_diesel = sorted(self.teams, key=lambda x: x.diesel_factor, reverse=True)[:15]
        
        for t in sorted_by_diesel:
            # Diagnostic
            if t.diesel_factor > 0.4:
                diag = "🚂 DIESEL - Monte en puissance"
                diag_color = Colors.ORANGE
            elif t.fast_starter > 0.2:
                diag = "⚡ SPRINTER - Démarre fort"
                diag_color = Colors.YELLOW
            elif t.first_half_xg_pct > 55:
                diag = "🌅 1H DOMINANT - Fait le travail tôt"
                diag_color = Colors.CYAN
            elif t.second_half_xg_pct > 40:
                diag = "🌙 2H FINISHER - Termine en force"
                diag_color = Colors.PURPLE
            else:
                diag = "📊 CONSISTENT - Régulier"
                diag_color = Colors.WHITE
            
            print(f"│ {t.team_name[:21]:<22} │ {t.temporal_profile[:11]:<12} │ {t.diesel_factor:>7.2f} │ "
                  f"{t.fast_starter:>6.2f} │ {t.first_half_xg_pct:>6.1f}% │ {t.second_half_xg_pct:>6.1f}% │ "
                  f"{diag_color}{diag:<45}{Colors.END} │")
        
        print(f"{'└'+'─'*130+'┘'}\n")
    
    def print_tactical_analysis(self):
        """Analyse du vecteur Tactical DNA"""
        print(f"{'┌'+'─'*140+'┐'}")
        print(f"│{Colors.BOLD}{Colors.BLUE} ⚽ TACTICAL DNA - PROFILS DE JEU{Colors.END}{' '*105}│")
        print(f"{'├'+'─'*140+'┤'}")
        print(f"│ {'Équipe':<22} │ {'Formation':<12} │ {'Profile':<18} │ {'Set Piece':>10} │ {'Open Play':>10} │ {'Vert':>5} │ {'Press':>6} │ {'Style':<20} │")
        print(f"{'├'+'─'*140+'┤'}")
        
        # Top 15 set piece threat
        sorted_by_setpiece = sorted(self.teams, key=lambda x: x.set_piece_threat, reverse=True)[:15]
        
        for t in sorted_by_setpiece:
            # Style tactique
            if t.set_piece_threat > 25:
                style_diag = "🎯 SET PIECE MASTER"
            elif t.open_play_reliance > 80:
                style_diag = "🎨 OPEN PLAY ARTIST"
            elif t.verticality > 8:
                style_diag = "⬆️ VERTICAL DIRECT"
            elif t.pressing_intensity > 15:
                style_diag = "🏃 HIGH PRESS"
            else:
                style_diag = "⚖️ BALANCED"
            
            formation = t.main_formation[:11] if t.main_formation else 'N/A'
            profile = t.tactical_profile[:17] if t.tactical_profile else 'N/A'
            
            print(f"│ {t.team_name[:21]:<22} │ {formation:<12} │ {profile:<18} │ "
                  f"{t.set_piece_threat:>9.1f}% │ {t.open_play_reliance:>9.1f}% │ {t.verticality:>5.1f} │ {t.pressing_intensity:>6.1f} │ "
                  f"{style_diag:<20} │")
        
        print(f"{'└'+'─'*140+'┘'}\n")
    
    def print_roster_analysis(self):
        """Analyse du vecteur Roster DNA"""
        print(f"{'┌'+'─'*130+'┐'}")
        print(f"│{Colors.BOLD}{Colors.GOLD} 👤 ROSTER DNA - DÉPENDANCE MVP{Colors.END}{' '*96}│")
        print(f"{'├'+'─'*130+'┤'}")
        print(f"│ {'Équipe':<22} │ {'MVP':<25} │ {'MVP Dep':>8} │ {'Top3 Dep':>9} │ {'Impact':>12} │ {'Risque':<30} │")
        print(f"{'├'+'─'*130+'┤'}")
        
        # Top 15 MVP dependency
        sorted_by_mvp = sorted(self.teams, key=lambda x: x.mvp_dependency, reverse=True)[:15]
        
        for t in sorted_by_mvp:
            mvp_name = t.mvp_name[:24] if t.mvp_name else 'N/A'
            impact = t.mvp_missing_impact[:11] if t.mvp_missing_impact else 'N/A'
            
            # Risque
            if t.mvp_dependency > 15:
                risk = "🚨 CRITIQUE - Très dépendant"
                risk_color = Colors.RED
            elif t.mvp_dependency > 10:
                risk = "⚠️ ÉLEVÉ - Dépendant"
                risk_color = Colors.YELLOW
            elif t.top3_dependency > 40:
                risk = "📊 CONCENTRÉ - Top 3 fort"
                risk_color = Colors.ORANGE
            else:
                risk = "✅ ÉQUILIBRÉ - Bien réparti"
                risk_color = Colors.GREEN
            
            print(f"│ {t.team_name[:21]:<22} │ {mvp_name:<25} │ {t.mvp_dependency:>7.1f}% │ "
                  f"{t.top3_dependency:>8.1f}% │ {impact:<12} │ {risk_color}{risk:<30}{Colors.END} │")
        
        print(f"{'└'+'─'*130+'┘'}\n")
    
    def print_luck_analysis(self):
        """Analyse du vecteur Luck DNA"""
        print(f"{'┌'+'─'*120+'┐'}")
        print(f"│{Colors.BOLD}{Colors.GREEN} 🍀 LUCK DNA - ANALYSE DE LA CHANCE{Colors.END}{' '*82}│")
        print(f"{'├'+'─'*120+'┤'}")
        print(f"│ {'Équipe':<22} │ {'Profile':<12} │ {'Total':>7} │ {'Finish':>8} │ {'Defense':>8} │ {'Diagnostic':<40} │")
        print(f"{'├'+'─'*120+'┤'}")
        
        # Top 15 par luck (les plus chanceux)
        sorted_by_luck = sorted(self.teams, key=lambda x: x.total_luck, reverse=True)[:10]
        # Bottom 5 (les plus malchanceux)
        sorted_by_unluck = sorted(self.teams, key=lambda x: x.total_luck)[:5]
        
        for t in sorted_by_luck:
            if t.total_luck > 5:
                diag = "🍀🍀 TRÈS CHANCEUX - Surperforme"
                diag_color = Colors.GREEN
            elif t.total_luck > 2:
                diag = "🍀 CHANCEUX - Légère surperf"
                diag_color = Colors.CYAN
            else:
                diag = "⚖️ NEUTRE"
                diag_color = Colors.WHITE
            
            print(f"│ {t.team_name[:21]:<22} │ {t.luck_profile[:11]:<12} │ {t.total_luck:>+6.1f} │ "
                  f"{t.finishing_luck:>+7.1f} │ {t.defensive_luck:>+7.1f} │ {diag_color}{diag:<40}{Colors.END} │")
        
        print(f"│ {'─'*118} │")
        
        for t in sorted_by_unluck:
            if t.total_luck < -5:
                diag = "😢😢 TRÈS MALCHANCEUX - Sous-perf"
                diag_color = Colors.RED
            elif t.total_luck < -2:
                diag = "😢 MALCHANCEUX - Légère sous-perf"
                diag_color = Colors.YELLOW
            else:
                diag = "⚖️ NEUTRE"
                diag_color = Colors.WHITE
            
            print(f"│ {t.team_name[:21]:<22} │ {t.luck_profile[:11]:<12} │ {t.total_luck:>+6.1f} │ "
                  f"{t.finishing_luck:>+7.1f} │ {t.defensive_luck:>+7.1f} │ {diag_color}{diag:<40}{Colors.END} │")
        
        print(f"{'└'+'─'*120+'┘'}\n")
    
    def print_specialists_analysis(self):
        """Analyse des spécialistes par marché"""
        print(f"{'┌'+'─'*100+'┐'}")
        print(f"│{Colors.BOLD}{Colors.CYAN} 🎯 MARKET SPECIALISTS - ÉQUIPES PAR MARCHÉ{Colors.END}{' '*55}│")
        print(f"{'├'+'─'*100+'┤'}")
        
        # Over specialists
        over_specs = [t for t in self.teams if t.over_specialist]
        under_specs = [t for t in self.teams if t.under_specialist]
        btts_yes_specs = [t for t in self.teams if t.btts_yes_specialist]
        btts_no_specs = [t for t in self.teams if t.btts_no_specialist]
        
        print(f"│ {Colors.GREEN}📈 OVER SPECIALISTS ({len(over_specs)}){Colors.END}: ", end="")
        print(", ".join([t.team_name for t in over_specs[:10]]) + f"{' '*20}│")
        
        print(f"│ {Colors.BLUE}📉 UNDER SPECIALISTS ({len(under_specs)}){Colors.END}: ", end="")
        print(", ".join([t.team_name for t in under_specs[:10]]) + f"{' '*20}│")
        
        print(f"│ {Colors.YELLOW}✅ BTTS YES SPECIALISTS ({len(btts_yes_specs)}){Colors.END}: ", end="")
        print(", ".join([t.team_name for t in btts_yes_specs[:10]]) + f"{' '*10}│")
        
        print(f"│ {Colors.RED}❌ BTTS NO SPECIALISTS ({len(btts_no_specs)}){Colors.END}: ", end="")
        print(", ".join([t.team_name for t in btts_no_specs[:10]]) + f"{' '*15}│")
        
        print(f"{'└'+'─'*100+'┘'}\n")
    
    def print_insights(self):
        """Insights globaux"""
        print(f"{'┌'+'─'*150+'┐'}")
        print(f"│{Colors.BOLD}{Colors.GOLD} 💡 INSIGHTS QUANTITATIFS - HEDGE FUND ANALYSIS{Colors.END}{' '*101}│")
        print(f"{'├'+'─'*150+'┤'}")
        
        # 1. Meilleur killer instinct
        best_killer = max(self.teams, key=lambda x: x.killer_instinct)
        print(f"│ 🦈 Meilleur Killer Instinct: {Colors.GREEN}{best_killer.team_name}{Colors.END} ({best_killer.killer_instinct:.2f}) → Finisseur de matchs{' '*50}│")
        
        # 2. Meilleur diesel factor
        best_diesel = max(self.teams, key=lambda x: x.diesel_factor)
        print(f"│ 🚂 Meilleur Diesel Factor: {Colors.ORANGE}{best_diesel.team_name}{Colors.END} ({best_diesel.diesel_factor:.2f}) → Monte en puissance en 2H{' '*48}│")
        
        # 3. Plus haute verticality
        best_vert = max(self.teams, key=lambda x: x.verticality)
        print(f"│ ⬆️ Plus haute Verticality: {Colors.CYAN}{best_vert.team_name}{Colors.END} ({best_vert.verticality:.1f}) → Jeu direct{' '*60}│")
        
        # 4. Meilleur pressing
        best_press = max(self.teams, key=lambda x: x.pressing_intensity)
        print(f"│ 🏃 Plus haute Pressing Intensity: {Colors.YELLOW}{best_press.team_name}{Colors.END} ({best_press.pressing_intensity:.1f}) → High press agressif{' '*42}│")
        
        # 5. Plus chanceux
        luckiest = max(self.teams, key=lambda x: x.total_luck)
        print(f"│ 🍀 Plus chanceux: {Colors.GREEN}{luckiest.team_name}{Colors.END} (luck: {luckiest.total_luck:+.1f}) → Surperforme ses xG{' '*55}│")
        
        # 6. Plus malchanceux
        unluckiest = min(self.teams, key=lambda x: x.total_luck)
        print(f"│ 😢 Plus malchanceux: {Colors.RED}{unluckiest.team_name}{Colors.END} (luck: {unluckiest.total_luck:+.1f}) → Sous-performe ses xG{' '*50}│")
        
        # 7. Plus forte dépendance MVP
        most_dependent = max(self.teams, key=lambda x: x.mvp_dependency)
        print(f"│ 👤 Plus forte dépendance MVP: {Colors.ORANGE}{most_dependent.team_name}{Colors.END} ({most_dependent.mvp_dependency:.1f}% - {most_dependent.mvp_name[:20]}) → Risque si absent{' '*20}│")
        
        # 8. Meilleure home strength
        best_home = max(self.teams, key=lambda x: x.home_strength)
        print(f"│ 🏠 Meilleure Home Strength: {Colors.GREEN}{best_home.team_name}{Colors.END} ({best_home.home_strength}) → Forteresse à domicile{' '*48}│")
        
        # 9. Meilleure away strength
        best_away = max(self.teams, key=lambda x: x.away_strength)
        print(f"│ 🚗 Meilleure Away Strength: {Colors.CYAN}{best_away.team_name}{Colors.END} ({best_away.away_strength}) → Road warriors{' '*52}│")
        
        # 10. Set piece specialists
        best_setpiece = max(self.teams, key=lambda x: x.set_piece_threat)
        print(f"│ 🎯 Meilleur Set Piece Threat: {Colors.PURPLE}{best_setpiece.team_name}{Colors.END} ({best_setpiece.set_piece_threat:.1f}%) → Dangereux sur coups de pied arrêtés{' '*30}│")
        
        print(f"{'└'+'─'*150+'┘'}\n")
    
    def save_report(self):
        """Sauvegarde le rapport en JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'version': 'V5.0 ADN Explorer',
            'summary': {
                'total_teams': self.total_teams,
                'total_bets': self.total_bets,
                'global_wr': round(self.global_wr, 2),
                'total_pnl': round(self.total_pnl, 2)
            },
            'leagues': {
                name: {
                    'teams': data['teams'],
                    'bets': data['bets'],
                    'wins': data['wins'],
                    'pnl': round(data['pnl'], 1),
                    'wr': round((data['wins'] / data['bets'] * 100) if data['bets'] > 0 else 0, 1)
                }
                for name, data in sorted(self.leagues.items(), key=lambda x: x[1]['pnl'], reverse=True)
                if name and name != 'N/A'
            },
            'teams': [
                {
                    'rank': t.rank,
                    'name': t.team_name,
                    'league': t.league,
                    'tier': t.tier,
                    'performance': {
                        'strategy': t.best_strategy,
                        'bets': t.bets,
                        'wins': t.wins,
                        'losses': t.losses,
                        'win_rate': round(t.win_rate, 1),
                        'roi': round(t.roi, 1),
                        'pnl': round(t.pnl, 1)
                    },
                    'market_dna': {
                        'over_specialist': t.over_specialist,
                        'under_specialist': t.under_specialist,
                        'btts_yes_specialist': t.btts_yes_specialist,
                        'btts_no_specialist': t.btts_no_specialist,
                        'profitable_strategies': t.profitable_strategies
                    },
                    'context_dna': {
                        'style': t.style,
                        'home_strength': t.home_strength,
                        'away_strength': t.away_strength,
                        'btts_tendency': t.btts_tendency,
                        'goals_tendency': t.goals_tendency
                    },
                    'psyche_dna': {
                        'profile': t.psyche_profile,
                        'killer_instinct': round(t.killer_instinct, 2),
                        'panic_factor': round(t.panic_factor, 2),
                        'comeback_mentality': round(t.comeback_mentality, 2),
                        'lead_protection': round(t.lead_protection, 2)
                    },
                    'temporal_dna': {
                        'profile': t.temporal_profile,
                        'diesel_factor': round(t.diesel_factor, 2),
                        'fast_starter': round(t.fast_starter, 2),
                        'first_half_xg_pct': round(t.first_half_xg_pct, 1),
                        'second_half_xg_pct': round(t.second_half_xg_pct, 1)
                    },
                    'nemesis_dna': {
                        'style': t.nemesis_style,
                        'verticality': round(t.verticality, 1),
                        'territorial_dominance': round(t.territorial_dominance, 2),
                        'keeper_status': t.keeper_status
                    },
                    'physical_dna': {
                        'stamina_profile': t.stamina_profile,
                        'pressing_intensity': round(t.pressing_intensity, 1),
                        'late_game_dominance': round(t.late_game_dominance, 1),
                        'late_game_threat': t.late_game_threat
                    },
                    'tactical_dna': {
                        'main_formation': t.main_formation,
                        'tactical_profile': t.tactical_profile,
                        'set_piece_threat': round(t.set_piece_threat, 1),
                        'open_play_reliance': round(t.open_play_reliance, 1)
                    },
                    'roster_dna': {
                        'mvp_name': t.mvp_name,
                        'mvp_dependency': round(t.mvp_dependency, 1),
                        'top3_dependency': round(t.top3_dependency, 1),
                        'mvp_missing_impact': t.mvp_missing_impact
                    },
                    'chameleon_dna': {
                        'profile': t.chameleon_profile,
                        'adaptability_index': round(t.adaptability_index, 1),
                        'tempo_flexibility': round(t.tempo_flexibility, 1)
                    },
                    'luck_dna': {
                        'profile': t.luck_profile,
                        'total_luck': round(t.total_luck, 1),
                        'finishing_luck': round(t.finishing_luck, 1),
                        'defensive_luck': round(t.defensive_luck, 1)
                    },
                    'current_season': {
                        'ppg': round(t.season_ppg, 2),
                        'goals': t.season_goals,
                        'xg_avg': round(t.season_xg_avg, 2),
                        'clinical': t.season_clinical,
                        'matches': t.season_matches
                    }
                }
                for t in self.teams
            ]
        }
        
        filename = f"quantum_v5_adn_explorer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: {filename}{Colors.END}")
        
        # Version fixe
        with open('quantum_v5_adn_latest.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: quantum_v5_adn_latest.json{Colors.END}")
    
    async def run(self):
        """Exécute le rapport complet"""
        await self.connect()
        await self.load_all_data()
        
        # Affichage complet
        self.print_header()
        self.print_league_analysis()
        self.print_main_table()
        self.print_psyche_analysis()
        self.print_temporal_analysis()
        self.print_tactical_analysis()
        self.print_roster_analysis()
        self.print_luck_analysis()
        self.print_specialists_analysis()
        self.print_insights()
        
        # Sauvegarde
        self.save_report()
        
        await self.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description='Quantum V5 ADN Explorer')
    parser.add_argument('--json-only', action='store_true', help='Générer uniquement le JSON')
    args = parser.parse_args()
    
    explorer = QuantumV5ADNExplorer()
    await explorer.run()


if __name__ == "__main__":
    asyncio.run(main())

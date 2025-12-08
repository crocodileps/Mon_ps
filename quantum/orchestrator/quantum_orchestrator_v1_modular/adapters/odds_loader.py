"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    ODDS LOADER - Chargement des cotes                                 ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Responsabilités:                                                                     ║
║  • Charger les matchs à venir depuis odds_history                                    ║
║  • Charger les cotes BTTS depuis odds_btts                                           ║
║  • Charger les cotes Over/Under depuis odds_totals                                   ║
║  • Agréger les meilleures cotes par bookmaker                                        ║
║  • Calculer les cotes de consensus                                                   ║
║                                                                                       ║
║  NE CONNAÎT PAS: Les modèles, le consensus, les décisions de paris                  ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncpg
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

import sys
sys.path.insert(0, '/home/Mon_ps/quantum/orchestrator')
from config.settings import DB_CONFIG, TABLES, BOOKMAKER_CONFIG

logger = logging.getLogger("OddsLoader")


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class OddsMovement:
    """Analyse du mouvement d'une cote (Steam)"""
    market: str
    opening_odds: float
    current_odds: float
    movement_pct: float          # Changement en %
    direction: str               # UP, DOWN, STABLE
    steam_signal: str            # SHARP_MONEY, PUBLIC_MONEY, NEUTRAL
    samples: int
    first_seen: datetime = None
    last_seen: datetime = None
    
    @property
    def is_significant(self) -> bool:
        """Mouvement > 3% est significatif"""
        return abs(self.movement_pct) > 3.0
    
    @property
    def is_sharp_steam(self) -> bool:
        """Sharp money = cote baisse rapidement"""
        return self.movement_pct < -5.0


@dataclass
class MatchOdds:
    """Cotes complètes d'un match"""
    match_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    sport: str = "soccer"
    league: str = ""
    
    # Cotes 1X2 (moyennes ou best)
    home_odds: float = 0.0
    draw_odds: float = 0.0
    away_odds: float = 0.0
    
    # Cotes Over/Under
    over_15_odds: float = 0.0
    over_25_odds: float = 0.0
    over_35_odds: float = 0.0
    under_15_odds: float = 0.0
    under_25_odds: float = 0.0
    under_35_odds: float = 0.0
    
    # Cotes BTTS
    btts_yes_odds: float = 0.0
    btts_no_odds: float = 0.0
    
    # Métadonnées
    bookmaker_count: int = 0
    last_update: datetime = None
    
    # Cotes par bookmaker (pour analyse CLV)
    odds_by_bookmaker: Dict[str, Dict] = field(default_factory=dict)
    
    # Steam/Mouvements de cotes
    odds_movements: Dict[str, OddsMovement] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Convertit en dict pour les modèles"""
        return {
            "home_win": self.home_odds,
            "draw": self.draw_odds,
            "away_win": self.away_odds,
            "over_15": self.over_15_odds,
            "over_25": self.over_25_odds,
            "over_35": self.over_35_odds,
            "under_15": self.under_15_odds,
            "under_25": self.under_25_odds,
            "under_35": self.under_35_odds,
            "btts_yes": self.btts_yes_odds,
            "btts_no": self.btts_no_odds
        }
    
    def get_best_odds(self, market: str) -> Tuple[float, str]:
        """Retourne les meilleures cotes et le bookmaker pour un marché"""
        best_odds = 0.0
        best_bookie = ""
        
        for bookie, odds in self.odds_by_bookmaker.items():
            if market in odds and odds[market] > best_odds:
                best_odds = odds[market]
                best_bookie = bookie
        
        return best_odds, best_bookie
    
    def get_steam_summary(self) -> Dict[str, Any]:
        """Résumé des mouvements de cotes"""
        significant = [m for m in self.odds_movements.values() if m.is_significant]
        sharp = [m for m in self.odds_movements.values() if m.is_sharp_steam]
        
        return {
            "total_markets_tracked": len(self.odds_movements),
            "significant_movements": len(significant),
            "sharp_steam_detected": len(sharp) > 0,
            "sharp_markets": [m.market for m in sharp],
            "movements": {
                m.market: {
                    "direction": m.direction,
                    "change_pct": f"{m.movement_pct:+.1f}%",
                    "signal": m.steam_signal
                }
                for m in self.odds_movements.values()
            }
        }


@dataclass
class UpcomingMatch:
    """Match à venir avec toutes ses cotes"""
    match_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    sport: str = "soccer"
    league: str = ""
    odds: MatchOdds = None
    
    def __post_init__(self):
        if self.odds is None:
            self.odds = MatchOdds(
                match_id=self.match_id,
                home_team=self.home_team,
                away_team=self.away_team,
                commence_time=self.commence_time
            )


# ═══════════════════════════════════════════════════════════════════════════════════════
# ODDS LOADER
# ═══════════════════════════════════════════════════════════════════════════════════════

class OddsLoader:
    """
    Chargeur de cotes depuis PostgreSQL.
    
    Agrège les données de:
    - odds_history (1X2)
    - odds_btts (BTTS)
    - odds_totals (Over/Under)
    """
    
    def __init__(self, pool: asyncpg.Pool = None):
        self.pool = pool
        self.priority_bookmakers = BOOKMAKER_CONFIG.PRIORITY_ORDER
    
    def set_pool(self, pool: asyncpg.Pool):
        """Configure le pool de connexions"""
        self.pool = pool
    
    def _decimal_to_float(self, value: Any) -> float:
        """Convertit Decimal en float"""
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value) if value else 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # UPCOMING MATCHES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_upcoming_matches(
        self, 
        hours_ahead: int = 48,
        min_bookmakers: int = 1,
        sports: List[str] = None
    ) -> List[UpcomingMatch]:
        """
        Charge tous les matchs à venir dans les prochaines heures.
        
        Args:
            hours_ahead: Nombre d'heures à regarder
            min_bookmakers: Nombre minimum de bookmakers requis
            sports: Liste des sports (défaut: soccer)
        
        Returns:
            Liste de UpcomingMatch avec cotes complètes
        """
        if not self.pool:
            raise RuntimeError("OddsLoader: pool non configuré")
        
        sports = sports or ["soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a", 
                           "soccer_germany_bundesliga", "soccer_france_ligue_one"]
        
        # 1. Charger les matchs uniques depuis odds_history
        matches = await self._load_unique_matches(hours_ahead)
        
        if not matches:
            logger.warning("⚠️ Aucun match trouvé dans odds_history")
            return []
        
        logger.info(f"📊 {len(matches)} matchs trouvés")
        
        # 2. Enrichir avec toutes les cotes
        enriched_matches = []
        for match in matches:
            odds = await self._load_all_odds_for_match(
                match['match_id'],
                match['home_team'],
                match['away_team'],
                match['commence_time']
            )
            
            if odds.bookmaker_count >= min_bookmakers:
                enriched_matches.append(UpcomingMatch(
                    match_id=match['match_id'],
                    home_team=match['home_team'],
                    away_team=match['away_team'],
                    commence_time=match['commence_time'],
                    sport=match.get('sport', 'soccer'),
                    odds=odds
                ))
        
        logger.info(f"✅ {len(enriched_matches)} matchs avec cotes complètes")
        return enriched_matches
    
    async def _load_unique_matches(self, hours_ahead: int) -> List[Dict]:
        """Charge les matchs uniques à venir"""
        query = f"""
            SELECT DISTINCT ON (home_team, away_team, DATE(commence_time))
                match_id, sport, home_team, away_team, commence_time
            FROM {TABLES.ODDS_HISTORY}
            WHERE commence_time > NOW()
              AND commence_time < NOW() + INTERVAL '{hours_ahead} hours'
            ORDER BY home_team, away_team, DATE(commence_time), collected_at DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Erreur chargement matchs: {e}")
            return []
    
    async def _load_all_odds_for_match(
        self, 
        match_id: str, 
        home_team: str, 
        away_team: str,
        commence_time: datetime
    ) -> MatchOdds:
        """Charge toutes les cotes pour un match spécifique"""
        
        odds = MatchOdds(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_time
        )
        
        # 1. Charger cotes 1X2
        await self._load_1x2_odds(odds, match_id, home_team, away_team)
        
        # 2. Charger cotes BTTS
        await self._load_btts_odds(odds, match_id, home_team, away_team)
        
        # 3. Charger cotes Over/Under
        await self._load_totals_odds(odds, match_id, home_team, away_team)
        
        return odds
    
    async def _load_1x2_odds(
        self, 
        odds: MatchOdds, 
        match_id: str,
        home_team: str,
        away_team: str
    ) -> None:
        """Charge les cotes 1X2 depuis odds_history"""
        
        query = f"""
            SELECT bookmaker, home_odds, draw_odds, away_odds, collected_at
            FROM {TABLES.ODDS_HISTORY}
            WHERE match_id = $1
               OR (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3)
                   AND commence_time = $4)
            ORDER BY collected_at DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id, home_team, away_team, odds.commence_time)
                
                if not rows:
                    return
                
                # Grouper par bookmaker (garder le plus récent)
                by_bookmaker = {}
                for row in rows:
                    bookie = row['bookmaker']
                    if bookie not in by_bookmaker:
                        by_bookmaker[bookie] = {
                            'home_win': self._decimal_to_float(row['home_odds']),
                            'draw': self._decimal_to_float(row['draw_odds']),
                            'away_win': self._decimal_to_float(row['away_odds'])
                        }
                
                # Stocker par bookmaker
                for bookie, bookie_odds in by_bookmaker.items():
                    if bookie not in odds.odds_by_bookmaker:
                        odds.odds_by_bookmaker[bookie] = {}
                    odds.odds_by_bookmaker[bookie].update(bookie_odds)
                
                # Calculer moyenne/consensus
                home_values = [o['home_win'] for o in by_bookmaker.values() if o['home_win'] > 0]
                draw_values = [o['draw'] for o in by_bookmaker.values() if o['draw'] > 0]
                away_values = [o['away_win'] for o in by_bookmaker.values() if o['away_win'] > 0]
                
                odds.home_odds = sum(home_values) / len(home_values) if home_values else 0
                odds.draw_odds = sum(draw_values) / len(draw_values) if draw_values else 0
                odds.away_odds = sum(away_values) / len(away_values) if away_values else 0
                odds.bookmaker_count = len(by_bookmaker)
                
        except Exception as e:
            logger.error(f"❌ Erreur cotes 1X2 {home_team} vs {away_team}: {e}")
    
    async def _load_btts_odds(
        self, 
        odds: MatchOdds, 
        match_id: str,
        home_team: str,
        away_team: str
    ) -> None:
        """Charge les cotes BTTS depuis odds_btts"""
        
        query = f"""
            SELECT bookmaker, btts_yes_odds, btts_no_odds, collected_at
            FROM {TABLES.ODDS_BTTS}
            WHERE match_id = $1
               OR (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3)
                   AND commence_time = $4)
            ORDER BY collected_at DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id, home_team, away_team, odds.commence_time)
                
                if not rows:
                    return
                
                # Grouper par bookmaker
                by_bookmaker = {}
                for row in rows:
                    bookie = row['bookmaker']
                    if bookie not in by_bookmaker:
                        by_bookmaker[bookie] = {
                            'btts_yes': self._decimal_to_float(row['btts_yes_odds']),
                            'btts_no': self._decimal_to_float(row['btts_no_odds'])
                        }
                
                # Stocker par bookmaker
                for bookie, bookie_odds in by_bookmaker.items():
                    if bookie not in odds.odds_by_bookmaker:
                        odds.odds_by_bookmaker[bookie] = {}
                    odds.odds_by_bookmaker[bookie].update(bookie_odds)
                
                # Calculer moyenne
                yes_values = [o['btts_yes'] for o in by_bookmaker.values() if o['btts_yes'] > 0]
                no_values = [o['btts_no'] for o in by_bookmaker.values() if o['btts_no'] > 0]
                
                odds.btts_yes_odds = sum(yes_values) / len(yes_values) if yes_values else 0
                odds.btts_no_odds = sum(no_values) / len(no_values) if no_values else 0
                
        except Exception as e:
            logger.error(f"❌ Erreur cotes BTTS {home_team} vs {away_team}: {e}")
    
    async def _load_totals_odds(
        self, 
        odds: MatchOdds, 
        match_id: str,
        home_team: str,
        away_team: str
    ) -> None:
        """Charge les cotes Over/Under depuis odds_totals"""
        
        query = f"""
            SELECT bookmaker, line, over_odds, under_odds, collected_at
            FROM {TABLES.ODDS_TOTALS}
            WHERE match_id = $1
               OR (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3)
                   AND commence_time = $4)
            ORDER BY collected_at DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id, home_team, away_team, odds.commence_time)
                
                if not rows:
                    return
                
                # Organiser par line et bookmaker
                by_line = {1.5: {}, 2.5: {}, 3.5: {}}
                
                for row in rows:
                    line = self._decimal_to_float(row['line'])
                    bookie = row['bookmaker']
                    
                    if line in by_line and bookie not in by_line[line]:
                        by_line[line][bookie] = {
                            'over': self._decimal_to_float(row['over_odds']),
                            'under': self._decimal_to_float(row['under_odds'])
                        }
                
                # Stocker par bookmaker
                for line, bookies in by_line.items():
                    for bookie, line_odds in bookies.items():
                        if bookie not in odds.odds_by_bookmaker:
                            odds.odds_by_bookmaker[bookie] = {}
                        
                        line_str = str(line).replace('.', '')
                        odds.odds_by_bookmaker[bookie][f'over_{line_str}'] = line_odds['over']
                        odds.odds_by_bookmaker[bookie][f'under_{line_str}'] = line_odds['under']
                
                # Calculer moyennes par ligne
                for line, bookies in by_line.items():
                    over_values = [o['over'] for o in bookies.values() if o['over'] > 0]
                    under_values = [o['under'] for o in bookies.values() if o['under'] > 0]
                    
                    avg_over = sum(over_values) / len(over_values) if over_values else 0
                    avg_under = sum(under_values) / len(under_values) if under_values else 0
                    
                    if line == 1.5:
                        odds.over_15_odds = avg_over
                        odds.under_15_odds = avg_under
                    elif line == 2.5:
                        odds.over_25_odds = avg_over
                        odds.under_25_odds = avg_under
                    elif line == 3.5:
                        odds.over_35_odds = avg_over
                        odds.under_35_odds = avg_under
                
        except Exception as e:
            logger.error(f"❌ Erreur cotes totals {home_team} vs {away_team}: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MATCH FILTERING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_matches_with_quantum_teams(
        self,
        hours_ahead: int = 48,
        quantum_teams: List[str] = None
    ) -> List[UpcomingMatch]:
        """
        Filtre les matchs pour ne garder que ceux avec des équipes 
        présentes dans quantum.team_profiles.
        """
        all_matches = await self.get_upcoming_matches(hours_ahead)
        
        if not quantum_teams:
            # Charger la liste des équipes quantum
            query = "SELECT team_name FROM quantum.team_profiles"
            try:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query)
                    quantum_teams = [row['team_name'].lower() for row in rows]
            except:
                return all_matches
        
        quantum_teams_lower = [t.lower() for t in quantum_teams]
        
        filtered = []
        for match in all_matches:
            home_ok = match.home_team.lower() in quantum_teams_lower
            away_ok = match.away_team.lower() in quantum_teams_lower
            
            if home_ok and away_ok:
                filtered.append(match)
                logger.debug(f"✅ Match retenu: {match.home_team} vs {match.away_team}")
            elif home_ok or away_ok:
                logger.debug(f"⚠️ Match partiel: {match.home_team} vs {match.away_team}")
        
        logger.info(f"🎯 {len(filtered)}/{len(all_matches)} matchs avec équipes quantum")
        return filtered
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CLV UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_odds_history_for_clv(
        self,
        match_id: str,
        market: str,
        hours_back: int = 24
    ) -> List[Tuple[datetime, float]]:
        """
        Charge l'historique des cotes pour calcul CLV.
        
        Returns:
            Liste de (timestamp, odds) triée chronologiquement
        """
        # Mapper le market vers la colonne
        market_column_map = {
            'home_win': 'home_odds',
            'draw': 'draw_odds',
            'away_win': 'away_odds',
            'btts_yes': 'btts_yes_odds',
            'btts_no': 'btts_no_odds'
        }
        
        # Pour les totals, c'est plus complexe
        if market.startswith('over_') or market.startswith('under_'):
            return await self._get_totals_history_for_clv(match_id, market, hours_back)
        
        column = market_column_map.get(market)
        if not column:
            return []
        
        table = TABLES.ODDS_BTTS if 'btts' in market else TABLES.ODDS_HISTORY
        
        query = f"""
            SELECT collected_at, {column} as odds_value
            FROM {table}
            WHERE match_id = $1
              AND collected_at > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY collected_at ASC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id)
                return [(row['collected_at'], self._decimal_to_float(row['odds_value'])) 
                        for row in rows if row['odds_value']]
        except Exception as e:
            logger.error(f"❌ Erreur historique CLV: {e}")
            return []
    
    async def _get_totals_history_for_clv(
        self,
        match_id: str,
        market: str,
        hours_back: int
    ) -> List[Tuple[datetime, float]]:
        """Charge l'historique des cotes Over/Under pour CLV"""
        
        # Parser le market (over_25 -> line=2.5, type=over)
        parts = market.split('_')
        if len(parts) != 2:
            return []
        
        market_type = parts[0]  # over ou under
        line = float(parts[1]) / 10  # 25 -> 2.5
        
        column = 'over_odds' if market_type == 'over' else 'under_odds'
        
        query = f"""
            SELECT collected_at, {column} as odds_value
            FROM {TABLES.ODDS_TOTALS}
            WHERE match_id = $1
              AND line = $2
              AND collected_at > NOW() - INTERVAL '{hours_back} hours'
            ORDER BY collected_at ASC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id, line)
                return [(row['collected_at'], self._decimal_to_float(row['odds_value'])) 
                        for row in rows if row['odds_value']]
        except Exception as e:
            logger.error(f"❌ Erreur historique CLV totals: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # STEAM ANALYSIS - Mouvements de cotes
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def analyze_steam(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        hours_back: int = 24
    ) -> Dict[str, OddsMovement]:
        """
        Analyse les mouvements de cotes pour détecter le steam.
        
        Steam = Mouvement significatif des cotes indiquant:
        - Sharp money (pros qui parient)
        - Public money (récréationnels)
        - Information asymétrique (blessure, météo, etc.)
        
        Returns:
            Dict[market, OddsMovement] pour chaque marché analysé
        """
        movements = {}
        
        # Analyser les cotes 1X2
        for market, column in [('home_win', 'home_odds'), ('draw', 'draw_odds'), ('away_win', 'away_odds')]:
            movement = await self._analyze_market_steam(
                match_id, home_team, away_team,
                TABLES.ODDS_HISTORY, column, market, hours_back
            )
            if movement:
                movements[market] = movement
        
        # Analyser Over 2.5
        movement = await self._analyze_totals_steam(
            match_id, home_team, away_team,
            2.5, 'over', hours_back
        )
        if movement:
            movements['over_25'] = movement
        
        return movements
    
    async def _analyze_market_steam(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        table: str,
        column: str,
        market: str,
        hours_back: int
    ) -> Optional[OddsMovement]:
        """Analyse le steam pour un marché 1X2"""
        
        query = f"""
            SELECT {column} as odds_value, collected_at
            FROM {table}
            WHERE match_id = $1
              AND collected_at > NOW() - INTERVAL '{hours_back} hours'
              AND {column} IS NOT NULL
            ORDER BY collected_at ASC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id)
                
                if len(rows) < 2:
                    return None
                
                opening = self._decimal_to_float(rows[0]['odds_value'])
                current = self._decimal_to_float(rows[-1]['odds_value'])
                
                if opening <= 0:
                    return None
                
                movement_pct = ((current - opening) / opening) * 100
                
                # Déterminer la direction
                if movement_pct > 1:
                    direction = "UP"
                elif movement_pct < -1:
                    direction = "DOWN"
                else:
                    direction = "STABLE"
                
                # Déterminer le signal
                if movement_pct < -5:
                    steam_signal = "SHARP_MONEY"  # Cote baisse = argent sharp
                elif movement_pct > 5:
                    steam_signal = "PUBLIC_MONEY"  # Cote monte = moins d'argent
                else:
                    steam_signal = "NEUTRAL"
                
                return OddsMovement(
                    market=market,
                    opening_odds=opening,
                    current_odds=current,
                    movement_pct=movement_pct,
                    direction=direction,
                    steam_signal=steam_signal,
                    samples=len(rows),
                    first_seen=rows[0]['collected_at'],
                    last_seen=rows[-1]['collected_at']
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur analyse steam {market}: {e}")
            return None
    
    async def _analyze_totals_steam(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        line: float,
        market_type: str,
        hours_back: int
    ) -> Optional[OddsMovement]:
        """Analyse le steam pour Over/Under"""
        
        column = 'over_odds' if market_type == 'over' else 'under_odds'
        market = f"{market_type}_{int(line*10)}"
        
        query = f"""
            SELECT {column} as odds_value, collected_at
            FROM {TABLES.ODDS_TOTALS}
            WHERE match_id = $1
              AND line = $2
              AND collected_at > NOW() - INTERVAL '{hours_back} hours'
              AND {column} IS NOT NULL
            ORDER BY collected_at ASC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id, line)
                
                if len(rows) < 2:
                    return None
                
                opening = self._decimal_to_float(rows[0]['odds_value'])
                current = self._decimal_to_float(rows[-1]['odds_value'])
                
                if opening <= 0:
                    return None
                
                movement_pct = ((current - opening) / opening) * 100
                
                if movement_pct > 1:
                    direction = "UP"
                elif movement_pct < -1:
                    direction = "DOWN"
                else:
                    direction = "STABLE"
                
                if movement_pct < -5:
                    steam_signal = "SHARP_MONEY"
                elif movement_pct > 5:
                    steam_signal = "PUBLIC_MONEY"
                else:
                    steam_signal = "NEUTRAL"
                
                return OddsMovement(
                    market=market,
                    opening_odds=opening,
                    current_odds=current,
                    movement_pct=movement_pct,
                    direction=direction,
                    steam_signal=steam_signal,
                    samples=len(rows),
                    first_seen=rows[0]['collected_at'],
                    last_seen=rows[-1]['collected_at']
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur analyse steam {market}: {e}")
            return None
    
    async def enrich_match_with_steam(self, match: 'UpcomingMatch') -> None:
        """Enrichit un match avec l'analyse steam"""
        movements = await self.analyze_steam(
            match.match_id,
            match.home_team,
            match.away_team
        )
        match.odds.odds_movements = movements


# ═══════════════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════════════

__all__ = ['OddsLoader', 'MatchOdds', 'UpcomingMatch', 'OddsMovement']


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 APPROXIMATION BTTS (ajouté par patch)
# ═══════════════════════════════════════════════════════════════════════════════

def approximate_btts_odds(over_25_odds: float) -> tuple:
    """
    Approxime les cotes BTTS depuis Over 2.5
    The Odds API ne supporte pas "btts" (erreur 422)
    Corrélation BTTS/Over2.5 ≈ 92%
    """
    if over_25_odds <= 1.0:
        return 0.0, 0.0
    
    BTTS_OVER25_RATIO = 0.92
    btts_yes = over_25_odds * BTTS_OVER25_RATIO
    btts_yes = max(btts_yes, 1.40)
    
    implied_yes = 1 / btts_yes
    implied_no = 1 - implied_yes + 0.05
    btts_no = 1 / max(implied_no, 0.30)
    btts_no = min(btts_no, 3.50)
    
    return round(btts_yes, 2), round(btts_no, 2)

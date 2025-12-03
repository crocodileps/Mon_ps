#!/usr/bin/env python3
"""
🎯 CLV ORCHESTRATOR V9.3 - SCIENTIFIC EDITION

BASÉ SUR L'ANALYSE RÉELLE DES TABLES DB (Diagnostic 03/12/2025)
═══════════════════════════════════════════════════════════════════════════════

TABLES ANALYSÉES ET COLONNES RÉELLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. team_intelligence (675 lignes)
   - team_name: "Liverpool" (SANS FC!)
   - current_style: balanced/pressing/possession...
   - home_btts_rate, away_btts_rate
   - home_over25_rate, away_over25_rate
   - home_goals_scored_avg, away_goals_scored_avg
   - btts_tendency, goals_tendency (0-100)
   - confidence_overall, is_reliable

2. team_momentum (110 lignes)
   - team_name: "Liverpool FC" (AVEC FC!)
   - momentum_score

3. team_name_mapping (179 lignes) - RÉSOLVEUR DE NOMS
   - source_name: "Manchester United FC"
   - canonical_name: "Manchester United"
   - normalized_name: "manchester united"

4. team_class (231 lignes)
   - team_name: "Liverpool"
   - tier: A/B/C/D
   - playing_style: high_press
   - star_players: JSON
   - big_game_factor, psychological_edge

5. tactical_matrix (144 lignes)
   - style_a, style_b
   - btts_probability, over_25_probability
   - sample_size, confidence_level

6. referee_intelligence (21 lignes)
   - referee_name, league
   - avg_goals_per_game, under_over_tendency

7. team_head_to_head (772 lignes)
   - team_a, team_b
   - btts_pct, over_25_pct

8. team_market_profiles (71 lignes)
   - team_name, location
   - best_market, win_rate

9. market_traps (196 lignes)
   - team_name, market_type
   - alert_level, is_active

10. reality_check_results (839 lignes)
    - match_id, reality_score
    - convergence_status

11. fg_sharp_money (6 lignes)
    - match_id, market_type
    - is_sharp_move, movement_direction
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import psycopg2
import psycopg2.extras

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER WEIGHTS (V9.3 - Calibré)
# ═══════════════════════════════════════════════════════════════════════════════

LAYER_WEIGHTS = {
    'momentum': 15,      # team_momentum
    'tactical': 12,      # tactical_matrix + team_intelligence.current_style
    'referee': 10,       # referee_intelligence
    'h2h': 12,           # team_head_to_head
    'reality': 10,       # reality_check_results
    'profile': 10,       # team_market_profiles
    'steam': 15,         # fg_sharp_money
    'class': 8,          # team_class (tier, big_game_factor)
    'intelligence': 8,   # team_intelligence (tendencies)
}

# ML comme multiplicateur (évite double counting)
ML_CONFIG = {
    'enabled': True,
    'multiplier_high': 1.20,      # ML WIN ≥70%
    'multiplier_medium': 1.10,    # ML WIN 60-70%
    'multiplier_low': 0.90,       # ML LOSE ≥60%
    'bonus_high': 10,
    'bonus_medium': 5,
    'penalty_low': -8,
}

# Sweet Spots (V5 calibrated)
SWEET_SPOTS = {
    'btts_yes': {'min': 1.65, 'max': 1.85, 'bonus': 10},
    'btts_no': {'min': 1.90, 'max': 2.20, 'bonus': 8},
    'over_25': {'min': 1.70, 'max': 1.95, 'bonus': 10},
    'under_25': {'min': 1.85, 'max': 2.15, 'bonus': 8},
    'over_35': {'min': 2.20, 'max': 2.60, 'bonus': 6},
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASS - PICK V9.3
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QuantProPick:
    """Pick avec toutes les données V9.3 Scientific"""
    
    # Identifiants
    match_id: str = ""
    home_team: str = ""
    away_team: str = ""
    league: str = ""
    
    # Marché
    market_type: str = ""
    odds: float = 0.0
    implied_prob: float = 0.0
    edge: float = 0.0
    
    # Scores par layer
    base_score: int = 0
    momentum_score: int = 0
    tactical_score: int = 0
    referee_score: int = 0
    h2h_score: int = 0
    reality_score: int = 0
    profile_score: int = 0
    steam_score: int = 0
    class_score: int = 0           # NOUVEAU V9.3
    intelligence_score: int = 0     # NOUVEAU V9.3
    sweet_spot_score: int = 0
    
    # Scores agrégés
    layer_score: int = 0
    ml_score: int = 0
    ml_multiplier: float = 1.0
    final_score: int = 0
    
    # ML
    ml_confidence: float = 0.5
    ml_prediction: str = "NO_MODEL"
    
    # Data coverage (confiance)
    data_coverage: float = 0.0
    layers_active: int = 0
    
    # Données enrichies
    home_momentum: Optional[Dict] = None
    away_momentum: Optional[Dict] = None
    home_intelligence: Optional[Dict] = None
    away_intelligence: Optional[Dict] = None
    home_class: Optional[Dict] = None
    away_class: Optional[Dict] = None
    tactical_match: Optional[Dict] = None
    referee_data: Optional[Dict] = None
    h2h_data: Optional[Dict] = None
    reality_data: Optional[Dict] = None
    steam_data: Optional[Dict] = None
    
    # Flags
    is_trap: bool = False
    trap_reason: str = ""
    is_sweet_spot: bool = False
    profile_consensus: bool = False
    
    # Output
    kelly: float = 0.0
    recommendation: str = ""
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V9.3 SCIENTIFIC
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestratorV93Scientific:
    """
    Orchestrator V9.3 - Scientific Edition
    Basé sur l'analyse réelle des structures DB
    """
    
    def __init__(self):
        self.conn = None
        self.ml_model = None
        self.ml_scaler = None
        self._name_cache = {}      # Cache pour résolution de noms
        self._context_cache = {}   # Cache pour données match
        
        self.stats = {
            'analyzed': 0,
            'momentum_applied': 0,
            'tactical_applied': 0,
            'referee_applied': 0,
            'h2h_applied': 0,
            'reality_applied': 0,
            'class_applied': 0,
            'intelligence_applied': 0,
            'traps_blocked': 0,
            'steam_detected': 0,
            'sweet_spots': 0,
            'high_coverage': 0,
            'low_coverage': 0,
            'final_picks': 0,
        }
        
        self._connect_db()
        self._load_ml_model()
        self._load_name_mappings()
        
        logger.info("🎯 Orchestrator V9.3 Scientific initialisé")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE CONNECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _connect_db(self):
        """Connexion à la base de données"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connexion DB établie")
        except Exception as e:
            logger.error(f"❌ Erreur DB: {e}")
            self.conn = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ML MODEL LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_ml_model(self):
        """Charge le modèle ML avec fallback multi-paths"""
        try:
            import joblib
            
            model_paths = [
                "/home/Mon_ps/backend/ml/models/best_model.joblib",
                "/home/Mon_ps/ml_smart_quant/models/best_model.joblib",
                "/home/Mon_ps/models/best_model.joblib",
            ]
            
            scaler_paths = [
                "/home/Mon_ps/backend/ml/models/scaler.joblib",
                "/home/Mon_ps/ml_smart_quant/models/scaler.joblib",
                "/home/Mon_ps/models/scaler.joblib",
            ]
            
            for path in model_paths:
                if os.path.exists(path):
                    self.ml_model = joblib.load(path)
                    logger.info(f"✅ ML chargé: {path}")
                    break
            
            for path in scaler_paths:
                if os.path.exists(path):
                    self.ml_scaler = joblib.load(path)
                    logger.info(f"✅ Scaler chargé: {path}")
                    break
            
            if not self.ml_model:
                logger.warning("⚠️ ML non trouvé - Le système fonctionne sans ML")
                
        except Exception as e:
            logger.warning(f"⚠️ ML error: {e}")
            self.ml_model = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NAME RESOLUTION (V9.3 - Basé sur team_name_mapping)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_name_mappings(self):
        """
        Charge les mappings de noms depuis team_name_mapping
        source_name → canonical_name
        """
        if not self.conn:
            return
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT source_name, canonical_name, normalized_name
                    FROM team_name_mapping
                    WHERE is_verified = TRUE
                """)
                
                for row in cur.fetchall():
                    source = row['source_name'].lower().strip()
                    canonical = row['canonical_name']
                    normalized = row['normalized_name']
                    
                    self._name_cache[source] = canonical
                    self._name_cache[normalized] = canonical
                    
                logger.info(f"✅ {len(self._name_cache)} mappings de noms chargés")
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur chargement mappings: {e}")
    
    def _resolve_team_name(self, team_name: str, target_table: str = None) -> List[str]:
        """
        V9.3 - Résout un nom d'équipe vers toutes les variantes possibles
        
        LOGIQUE:
        - team_momentum utilise "Liverpool FC"
        - team_intelligence utilise "Liverpool"
        - team_name_mapping fait le lien
        
        Returns: Liste de variantes à chercher
        """
        name_lower = team_name.lower().strip()
        variants = set([team_name, name_lower])
        
        # 1. Chercher dans le cache de mappings
        if name_lower in self._name_cache:
            canonical = self._name_cache[name_lower]
            variants.add(canonical)
            variants.add(canonical.lower())
        
        # 2. Ajouter/retirer " FC" automatiquement
        if name_lower.endswith(' fc'):
            without_fc = name_lower[:-3].strip()
            variants.add(without_fc)
            variants.add(without_fc.title())
        else:
            with_fc = name_lower + ' fc'
            variants.add(with_fc)
            variants.add(team_name + ' FC')
        
        # 3. Variantes communes
        common_mappings = {
            'man city': ['manchester city', 'manchester city fc'],
            'man utd': ['manchester united', 'manchester united fc'],
            'spurs': ['tottenham', 'tottenham hotspur', 'tottenham hotspur fc'],
            'wolves': ['wolverhampton', 'wolverhampton wanderers fc'],
            'psg': ['paris saint germain', 'paris saint-germain'],
            'barca': ['barcelona', 'fc barcelona'],
            'bayern': ['bayern munich', 'fc bayern münchen'],
            'inter': ['inter milan', 'fc internazionale milano'],
            'juve': ['juventus', 'juventus fc'],
            'atletico': ['atletico madrid', 'club atlético de madrid'],
        }
        
        for short, full_names in common_mappings.items():
            if name_lower == short or name_lower in full_names:
                variants.update(full_names)
                variants.add(short)
        
        return list(variants)
    
    def _build_name_where(self, column: str, team_name: str) -> Tuple[str, List[str]]:
        """Construit une clause WHERE pour recherche de nom"""
        variants = self._resolve_team_name(team_name)
        
        # Utiliser LOWER et LIKE pour flexibilité
        conditions = []
        params = []
        
        for v in variants[:8]:  # Limiter à 8 variantes max
            conditions.append(f"LOWER({column}) = %s")
            params.append(v.lower())
        
        # Ajouter recherche LIKE en fallback
        conditions.append(f"LOWER({column}) LIKE %s")
        params.append(f"%{team_name.lower()}%")
        
        where_clause = f"({' OR '.join(conditions)})"
        return where_clause, params
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRE-FETCH CONTEXT (Optimisation SQL)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _prefetch_match_context(self, home_team: str, away_team: str, 
                                 match_id: str, league: str, 
                                 referee_name: str = None) -> Dict:
        """
        V9.3 - Pré-charge TOUTES les données du match
        Réduit le nombre de requêtes SQL
        """
        cache_key = f"{home_team}_{away_team}_{match_id}"
        
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        context = {
            # Momentum (team_momentum - utilise "Liverpool FC")
            'home_momentum': self._get_team_momentum(home_team),
            'away_momentum': self._get_team_momentum(away_team),
            
            # Intelligence (team_intelligence - utilise "Liverpool")
            'home_intelligence': self._get_team_intelligence(home_team),
            'away_intelligence': self._get_team_intelligence(away_team),
            
            # Class (team_class - utilise "Liverpool")
            'home_class': self._get_team_class(home_team),
            'away_class': self._get_team_class(away_team),
            
            # Tactical
            'tactical': None,  # Calculé après avoir les styles
            
            # Referee
            'referee': self._get_referee_data(referee_name, league),
            
            # H2H
            'h2h': self._get_h2h_data(home_team, away_team),
            
            # Reality Check
            'reality': self._get_reality_check(match_id),
            
            # Steam
            'steam': self._get_steam_data(match_id),
            
            # Profiles
            'home_profile': self._get_team_profile(home_team, 'home'),
            'away_profile': self._get_team_profile(away_team, 'away'),
            
            # Traps
            'home_traps': self._get_team_traps(home_team),
            'away_traps': self._get_team_traps(away_team),
        }
        
        # Calculer tactical après avoir les styles
        home_style = self._determine_team_style(context['home_intelligence'], context['home_class'])
        away_style = self._determine_team_style(context['away_intelligence'], context['away_class'])
        context['home_style'] = home_style
        context['away_style'] = away_style
        context['tactical'] = self._get_tactical_match(home_style, away_style)
        
        self._context_cache[cache_key] = context
        return context
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA FETCHERS (Basés sur vraies structures DB)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_team_momentum(self, team_name: str) -> Optional[Dict]:
        """
        Récupère momentum depuis team_momentum
        Note: Cette table utilise "Liverpool FC" (avec FC)
        """
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name,
                        momentum_score,
                        goals_scored_last_5,
                        goals_conceded_last_5,
                        form_last_5,
                        win_streak,
                        unbeaten_streak,
                        key_player_absent,
                        key_absence_impact
                    FROM team_momentum
                    WHERE {where}
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Momentum error: {e}")
            return None
    
    def _get_team_intelligence(self, team_name: str) -> Optional[Dict]:
        """
        Récupère intelligence depuis team_intelligence
        Note: Cette table utilise "Liverpool" (SANS FC)
        
        Colonnes clés (réelles):
        - current_style, current_pressing
        - home_btts_rate, away_btts_rate
        - home_over25_rate, away_over25_rate
        - home_goals_scored_avg, away_goals_scored_avg
        - btts_tendency, goals_tendency (0-100)
        """
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name,
                        current_style,
                        current_pressing,
                        current_form,
                        home_strength,
                        away_strength,
                        home_btts_rate,
                        away_btts_rate,
                        home_over25_rate,
                        away_over25_rate,
                        home_goals_scored_avg,
                        away_goals_scored_avg,
                        home_goals_conceded_avg,
                        away_goals_conceded_avg,
                        home_clean_sheet_rate,
                        away_clean_sheet_rate,
                        btts_tendency,
                        goals_tendency,
                        clean_sheet_tendency,
                        confidence_overall,
                        is_reliable
                    FROM team_intelligence
                    WHERE {where}
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Intelligence error: {e}")
            return None
    
    def _get_team_class(self, team_name: str) -> Optional[Dict]:
        """
        Récupère classe depuis team_class
        Note: Cette table utilise "Liverpool" (SANS FC)
        
        Colonnes clés:
        - tier: A/B/C/D
        - playing_style: high_press, etc.
        - star_players: JSON
        - big_game_factor, psychological_edge
        """
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name,
                        tier,
                        league,
                        historical_strength,
                        squad_value_millions,
                        star_players,
                        big_game_factor,
                        home_fortress_factor,
                        away_weakness_factor,
                        psychological_edge,
                        correction_factor,
                        playing_style,
                        calculated_power_index
                    FROM team_class
                    WHERE {where}
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Class error: {e}")
            return None
    
    def _determine_team_style(self, intelligence: Optional[Dict], 
                               team_class: Optional[Dict]) -> str:
        """
        Détermine le style d'une équipe en combinant les sources
        Priorité: team_intelligence.current_style > team_class.playing_style
        """
        style = 'balanced'  # Default
        
        if intelligence and intelligence.get('current_style'):
            style = intelligence['current_style']
        elif team_class and team_class.get('playing_style'):
            style = team_class['playing_style']
        
        return style.lower().strip()
    
    def _get_tactical_match(self, style_a: str, style_b: str) -> Optional[Dict]:
        """
        Récupère données tactiques depuis tactical_matrix
        """
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Recherche exacte d'abord
                cur.execute("""
                    SELECT 
                        style_a, style_b,
                        btts_probability,
                        over_25_probability,
                        under_25_probability,
                        avg_goals_total,
                        sample_size,
                        confidence_level,
                        data_quality_score
                    FROM tactical_matrix
                    WHERE LOWER(style_a) = %s AND LOWER(style_b) = %s
                    LIMIT 1
                """, (style_a.lower(), style_b.lower()))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
                
                # Fallback: chercher avec "balanced"
                cur.execute("""
                    SELECT 
                        style_a, style_b,
                        btts_probability,
                        over_25_probability,
                        under_25_probability,
                        avg_goals_total,
                        sample_size,
                        confidence_level
                    FROM tactical_matrix
                    WHERE (LOWER(style_a) = %s AND LOWER(style_b) = 'balanced')
                       OR (LOWER(style_a) = 'balanced' AND LOWER(style_b) = %s)
                       OR (LOWER(style_a) = 'balanced' AND LOWER(style_b) = 'balanced')
                    ORDER BY sample_size DESC
                    LIMIT 1
                """, (style_a.lower(), style_b.lower()))
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Tactical error: {e}")
            return None
    
    def _get_referee_data(self, referee_name: str, league: str) -> Optional[Dict]:
        """
        Récupère données arbitre depuis referee_intelligence
        Avec fallback sur moyenne de la ligue
        """
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Recherche par nom si fourni
                if referee_name:
                    cur.execute("""
                        SELECT 
                            referee_name,
                            league,
                            strictness_level,
                            avg_goals_per_game,
                            under_over_tendency,
                            home_bias_factor,
                            penalty_frequency,
                            matches_officiated
                        FROM referee_intelligence
                        WHERE LOWER(referee_name) LIKE %s
                        LIMIT 1
                    """, (f"%{referee_name.lower()}%",))
                    
                    row = cur.fetchone()
                    if row:
                        return dict(row)
                
                # Fallback: moyenne de la ligue
                if league:
                    cur.execute("""
                        SELECT 
                            'League Average' as referee_name,
                            %s as league,
                            AVG(strictness_level)::int as strictness_level,
                            AVG(avg_goals_per_game) as avg_goals_per_game,
                            'neutral' as under_over_tendency,
                            1.0 as home_bias_factor,
                            AVG(penalty_frequency) as penalty_frequency,
                            AVG(matches_officiated)::int as matches_officiated
                        FROM referee_intelligence
                        WHERE LOWER(league) LIKE %s
                    """, (league, f"%{league.lower()}%"))
                    
                    row = cur.fetchone()
                    if row and row['avg_goals_per_game']:
                        return dict(row)
                
                return None
                
        except Exception as e:
            logger.debug(f"Referee error: {e}")
            return None
    
    def _get_h2h_data(self, home_team: str, away_team: str) -> Optional[Dict]:
        """
        Récupère H2H depuis team_head_to_head
        """
        if not self.conn:
            return None
        
        try:
            home_variants = self._resolve_team_name(home_team)
            away_variants = self._resolve_team_name(away_team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Essayer toutes les combinaisons
                for hv in home_variants[:5]:
                    for av in away_variants[:5]:
                        cur.execute("""
                            SELECT 
                                team_a, team_b,
                                total_matches,
                                team_a_wins, team_b_wins, draws,
                                btts_pct,
                                over_25_pct,
                                over_15_pct,
                                avg_total_goals,
                                last_match_date,
                                last3_btts
                            FROM team_head_to_head
                            WHERE (LOWER(team_a) = %s AND LOWER(team_b) = %s)
                               OR (LOWER(team_a) = %s AND LOWER(team_b) = %s)
                            LIMIT 1
                        """, (hv.lower(), av.lower(), av.lower(), hv.lower()))
                        
                        row = cur.fetchone()
                        if row:
                            return dict(row)
                
                return None
                
        except Exception as e:
            logger.debug(f"H2H error: {e}")
            return None
    
    def _get_reality_check(self, match_id: str) -> Optional[Dict]:
        """Récupère reality check depuis reality_check_results"""
        if not self.conn or not match_id:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        match_id,
                        home_tier, away_tier,
                        tier_difference,
                        class_score,
                        star_player_score,
                        context_score,
                        psychological_score,
                        reality_score,
                        convergence_status,
                        adjusted_confidence
                    FROM reality_check_results
                    WHERE match_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (match_id,))
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Reality error: {e}")
            return None
    
    def _get_steam_data(self, match_id: str) -> Optional[Dict]:
        """Récupère steam moves depuis fg_sharp_money"""
        if not self.conn or not match_id:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        market_type,
                        opening_odds,
                        current_odds,
                        closing_odds,
                        movement_pct,
                        movement_direction,
                        is_sharp_move
                    FROM fg_sharp_money
                    WHERE match_id = %s
                """, (match_id,))
                
                rows = cur.fetchall()
                if rows:
                    return {
                        'moves': [dict(r) for r in rows],
                        'has_sharp': any(r['is_sharp_move'] for r in rows)
                    }
                return None
                
        except Exception as e:
            logger.debug(f"Steam error: {e}")
            return None
    
    def _get_team_profile(self, team_name: str, location: str) -> Optional[Dict]:
        """Récupère profil marché depuis team_market_profiles"""
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            params.append(location)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name,
                        location,
                        best_market,
                        best_market_group,
                        win_rate,
                        profit,
                        picks_count,
                        composite_score,
                        avoid_markets
                    FROM team_market_profiles
                    WHERE {where} AND location = %s
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Profile error: {e}")
            return None
    
    def _get_team_traps(self, team_name: str) -> List[Dict]:
        """Récupère les traps actifs pour une équipe depuis market_traps"""
        if not self.conn:
            return []
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name,
                        market_type,
                        alert_level,
                        alert_reason,
                        alternative_market,
                        confidence_score
                    FROM market_traps
                    WHERE {where}
                      AND is_active = TRUE
                      AND alert_level IN ('TRAP', 'DANGER')
                """, params)
                
                return [dict(r) for r in cur.fetchall()]
                
        except Exception as e:
            logger.debug(f"Traps error: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE CALCULATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_base_score(self, pick: QuantProPick) -> int:
        """Score de base selon les odds et edge"""
        score = 0
        
        # Edge basique
        if pick.edge > 0.10:
            score += 15
        elif pick.edge > 0.05:
            score += 10
        elif pick.edge > 0.02:
            score += 5
        
        # Odds dans range optimal
        if 1.60 <= pick.odds <= 2.20:
            score += 5
        
        return score
    
    def calculate_momentum_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur momentum des équipes"""
        score = 0
        
        home_mom = context.get('home_momentum')
        away_mom = context.get('away_momentum')
        
        pick.home_momentum = home_mom
        pick.away_momentum = away_mom
        
        if not home_mom and not away_mom:
            return 0
        
        self.stats['momentum_applied'] += 1
        
        # Momentum scores
        home_score = home_mom.get('momentum_score', 50) if home_mom else 50
        away_score = away_mom.get('momentum_score', 50) if away_mom else 50
        
        # Goals last 5
        home_goals = home_mom.get('goals_scored_last_5', 0) if home_mom else 0
        away_goals = away_mom.get('goals_scored_last_5', 0) if away_mom else 0
        total_goals = (home_goals or 0) + (away_goals or 0)
        
        market = pick.market_type.lower()
        
        if market in ['btts_yes', 'over_25', 'over_35']:
            # Les deux équipes en forme offensive = bon pour buts
            if home_score >= 70 and away_score >= 70:
                score += 12
                pick.reasons.append(f"🔥 Momentum élevé: {home_score}/{away_score}")
            elif home_score >= 60 and away_score >= 60:
                score += 8
            
            # Buts récents
            if total_goals >= 15:  # >3 buts/match en moyenne
                score += 5
                
        elif market in ['btts_no', 'under_25']:
            # Momentum faible = moins de buts
            if home_score <= 40 or away_score <= 40:
                score += 8
            
        # Absences clés
        if home_mom and home_mom.get('key_player_absent'):
            impact = home_mom.get('key_absence_impact', 0) or 0
            if market in ['btts_no', 'under_25']:
                score += min(impact, 5)
            elif market in ['btts_yes', 'over_25']:
                score -= min(impact, 5)
        
        return max(-LAYER_WEIGHTS['momentum'], min(LAYER_WEIGHTS['momentum'], score))
    
    def calculate_tactical_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur la matrice tactique"""
        score = 0
        
        tactical = context.get('tactical')
        pick.tactical_match = tactical
        
        if not tactical:
            return 0
        
        self.stats['tactical_applied'] += 1
        
        market = pick.market_type.lower()
        
        btts_prob = float(tactical.get('btts_probability', 50) or 50)
        over25_prob = float(tactical.get('over_25_probability', 50) or 50)
        sample = tactical.get('sample_size', 0) or 0
        
        # Pondération selon sample size
        confidence_mult = 1.0
        if sample < 5:
            confidence_mult = 0.5
        elif sample < 10:
            confidence_mult = 0.7
        elif sample < 20:
            confidence_mult = 0.85
        
        if market == 'btts_yes':
            if btts_prob >= 55:
                score += int(10 * confidence_mult)
                pick.reasons.append(f"📊 Tactique BTTS: {btts_prob:.0f}%")
            elif btts_prob >= 50:
                score += int(5 * confidence_mult)
        elif market == 'btts_no':
            if btts_prob <= 45:
                score += int(10 * confidence_mult)
            elif btts_prob <= 50:
                score += int(5 * confidence_mult)
        elif market == 'over_25':
            if over25_prob >= 55:
                score += int(10 * confidence_mult)
                pick.reasons.append(f"📊 Tactique O2.5: {over25_prob:.0f}%")
            elif over25_prob >= 50:
                score += int(5 * confidence_mult)
        elif market == 'under_25':
            if over25_prob <= 45:
                score += int(10 * confidence_mult)
        
        return max(-LAYER_WEIGHTS['tactical'], min(LAYER_WEIGHTS['tactical'], score))
    
    def calculate_intelligence_score(self, pick: QuantProPick, context: Dict) -> int:
        """
        V9.3 - Score basé sur team_intelligence (tendencies)
        Colonnes: btts_tendency, goals_tendency (0-100)
        """
        score = 0
        
        home_intel = context.get('home_intelligence')
        away_intel = context.get('away_intelligence')
        
        pick.home_intelligence = home_intel
        pick.away_intelligence = away_intel
        
        if not home_intel and not away_intel:
            return 0
        
        self.stats['intelligence_applied'] += 1
        
        market = pick.market_type.lower()
        
        # Récupérer tendencies (0-100)
        home_btts = float(home_intel.get('btts_tendency', 50) or 50) if home_intel else 50
        away_btts = float(away_intel.get('btts_tendency', 50) or 50) if away_intel else 50
        home_goals = float(home_intel.get('goals_tendency', 50) or 50) if home_intel else 50
        away_goals = float(away_intel.get('goals_tendency', 50) or 50) if away_intel else 50
        
        avg_btts = (home_btts + away_btts) / 2
        avg_goals = (home_goals + away_goals) / 2
        
        if market == 'btts_yes':
            if avg_btts >= 65:
                score += 8
                pick.reasons.append(f"📈 Tendance BTTS: {avg_btts:.0f}")
            elif avg_btts >= 55:
                score += 4
        elif market == 'btts_no':
            if avg_btts <= 40:
                score += 8
            elif avg_btts <= 50:
                score += 4
        elif market in ['over_25', 'over_35']:
            if avg_goals >= 65:
                score += 8
            elif avg_goals >= 55:
                score += 4
        elif market == 'under_25':
            if avg_goals <= 40:
                score += 8
            elif avg_goals <= 50:
                score += 4
        
        return max(-LAYER_WEIGHTS['intelligence'], min(LAYER_WEIGHTS['intelligence'], score))
    
    def calculate_class_score(self, pick: QuantProPick, context: Dict) -> int:
        """
        V9.3 - Score basé sur team_class (tier, big_game_factor)
        """
        score = 0
        
        home_class = context.get('home_class')
        away_class = context.get('away_class')
        
        pick.home_class = home_class
        pick.away_class = away_class
        
        if not home_class and not away_class:
            return 0
        
        self.stats['class_applied'] += 1
        
        # Tier mapping
        tier_values = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
        
        home_tier = home_class.get('tier', 'C') if home_class else 'C'
        away_tier = away_class.get('tier', 'C') if away_class else 'C'
        
        home_val = tier_values.get(home_tier, 2)
        away_val = tier_values.get(away_tier, 2)
        
        # Équipes de classe similaire = plus de matchs équilibrés
        tier_diff = abs(home_val - away_val)
        
        market = pick.market_type.lower()
        
        if market in ['btts_yes', 'over_25']:
            # Matchs équilibrés = plus de buts
            if tier_diff == 0:
                score += 6
            elif tier_diff == 1:
                score += 3
            
            # Big game factor
            home_bgf = float(home_class.get('big_game_factor', 1.0) or 1.0) if home_class else 1.0
            away_bgf = float(away_class.get('big_game_factor', 1.0) or 1.0) if away_class else 1.0
            
            if home_bgf >= 1.1 and away_bgf >= 1.1:
                score += 4
                pick.reasons.append("⭐ Big game matchup")
                
        elif market in ['btts_no', 'under_25']:
            # Grand écart de classe = domination = moins BTTS
            if tier_diff >= 2:
                score += 5
        
        return max(-LAYER_WEIGHTS['class'], min(LAYER_WEIGHTS['class'], score))
    
    def calculate_referee_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur l'arbitre"""
        score = 0
        
        ref = context.get('referee')
        pick.referee_data = ref
        
        if not ref:
            return 0
        
        self.stats['referee_applied'] += 1
        
        market = pick.market_type.lower()
        
        avg_goals = float(ref.get('avg_goals_per_game', 2.5) or 2.5)
        tendency = ref.get('under_over_tendency', 'neutral')
        
        if market in ['btts_yes', 'over_25', 'over_35']:
            if tendency == 'over':
                score += 7
                pick.reasons.append(f"⚖️ Arbitre pro-over ({avg_goals:.2f} buts/match)")
            elif avg_goals >= 2.8:
                score += 5
        elif market in ['btts_no', 'under_25']:
            if tendency == 'under':
                score += 7
            elif avg_goals <= 2.4:
                score += 5
        
        return max(-LAYER_WEIGHTS['referee'], min(LAYER_WEIGHTS['referee'], score))
    
    def calculate_h2h_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur H2H"""
        score = 0
        
        h2h = context.get('h2h')
        pick.h2h_data = h2h
        
        if not h2h:
            return 0
        
        total = h2h.get('total_matches', 0) or 0
        if total < 2:
            return 0
        
        self.stats['h2h_applied'] += 1
        
        market = pick.market_type.lower()
        
        btts_pct = float(h2h.get('btts_pct', 50) or 50)
        over25_pct = float(h2h.get('over_25_pct', 50) or 50)
        
        # Pondération sample
        confidence = 1.0 if total >= 5 else 0.7
        
        if market == 'btts_yes':
            if btts_pct >= 70:
                score += int(10 * confidence)
                pick.reasons.append(f"📜 H2H BTTS: {btts_pct:.0f}% ({total} matchs)")
            elif btts_pct >= 55:
                score += int(6 * confidence)
        elif market == 'btts_no':
            if btts_pct <= 35:
                score += int(10 * confidence)
            elif btts_pct <= 45:
                score += int(6 * confidence)
        elif market == 'over_25':
            if over25_pct >= 70:
                score += int(10 * confidence)
            elif over25_pct >= 55:
                score += int(6 * confidence)
        elif market == 'under_25':
            if over25_pct <= 35:
                score += int(10 * confidence)
        
        return max(-LAYER_WEIGHTS['h2h'], min(LAYER_WEIGHTS['h2h'], score))
    
    def calculate_reality_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur Reality Check"""
        score = 0
        
        reality = context.get('reality')
        pick.reality_data = reality
        
        if not reality:
            return 0
        
        self.stats['reality_applied'] += 1
        
        convergence = reality.get('convergence_status', '')
        reality_score = reality.get('reality_score', 50) or 50
        
        if convergence == 'strong_convergence':
            score += 8
            pick.reasons.append("✅ Reality Check: Convergence forte")
        elif convergence == 'moderate_convergence':
            score += 4
        elif convergence == 'divergence':
            score -= 5
            pick.warnings.append("⚠️ Reality Check: Divergence détectée")
        
        return max(-LAYER_WEIGHTS['reality'], min(LAYER_WEIGHTS['reality'], score))
    
    def calculate_steam_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur steam moves"""
        score = 0
        
        steam = context.get('steam')
        pick.steam_data = steam
        
        if not steam:
            return 0
        
        moves = steam.get('moves', [])
        market = pick.market_type.lower()
        
        for move in moves:
            move_market = move.get('market_type', '').lower()
            is_sharp = move.get('is_sharp_move', False)
            direction = move.get('movement_direction', '')
            
            if move_market == market or self._markets_related(move_market, market):
                self.stats['steam_detected'] += 1
                
                if is_sharp:
                    if direction == 'shortening':
                        score += 12
                        pick.reasons.append(f"🔥 Steam move détecté sur {move_market}")
                    elif direction == 'drifting':
                        score -= 8
                        pick.warnings.append(f"⚠️ Steam contre sur {move_market}")
        
        return max(-LAYER_WEIGHTS['steam'], min(LAYER_WEIGHTS['steam'], score))
    
    def _markets_related(self, m1: str, m2: str) -> bool:
        """Vérifie si deux marchés sont liés"""
        btts_markets = ['btts_yes', 'btts_no', 'btts']
        goals_markets = ['over_25', 'under_25', 'over_35', 'under_35', 'over_15']
        
        m1, m2 = m1.lower(), m2.lower()
        
        if m1 in btts_markets and m2 in btts_markets:
            return True
        if m1 in goals_markets and m2 in goals_markets:
            return True
        
        return False
    
    def calculate_profile_score(self, pick: QuantProPick, context: Dict) -> int:
        """Score basé sur les profils marché"""
        score = 0
        
        home_prof = context.get('home_profile')
        away_prof = context.get('away_profile')
        
        if not home_prof and not away_prof:
            return 0
        
        market = pick.market_type.lower()
        
        # Vérifier consensus
        home_best = home_prof.get('best_market', '').lower() if home_prof else ''
        away_best = away_prof.get('best_market', '').lower() if away_prof else ''
        
        if home_best == market and away_best == market:
            score += 10
            pick.profile_consensus = True
            pick.reasons.append(f"�� Consensus profil: {market}")
        elif home_best == market or away_best == market:
            score += 5
        
        # Vérifier avoid_markets
        if home_prof:
            avoid = home_prof.get('avoid_markets', []) or []
            if any(m.get('market', '').lower() == market for m in avoid if isinstance(m, dict)):
                score -= 5
                pick.warnings.append(f"⚠️ {pick.home_team} évite {market}")
        
        return max(-LAYER_WEIGHTS['profile'], min(LAYER_WEIGHTS['profile'], score))
    
    def check_trap(self, pick: QuantProPick, context: Dict) -> bool:
        """Vérifie si le pick est bloqué par un trap"""
        home_traps = context.get('home_traps', [])
        away_traps = context.get('away_traps', [])
        
        market = pick.market_type.lower()
        
        for trap in home_traps + away_traps:
            trap_market = trap.get('market_type', '').lower()
            if trap_market == market:
                pick.is_trap = True
                pick.trap_reason = trap.get('alert_reason', 'Trap détecté')
                self.stats['traps_blocked'] += 1
                return True
        
        return False
    
    def calculate_sweet_spot(self, pick: QuantProPick) -> int:
        """Bonus pour odds dans le sweet spot"""
        market = pick.market_type.lower()
        
        if market in SWEET_SPOTS:
            spot = SWEET_SPOTS[market]
            if spot['min'] <= pick.odds <= spot['max']:
                pick.is_sweet_spot = True
                self.stats['sweet_spots'] += 1
                return spot['bonus']
        
        return 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ML PREDICTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_ml_score(self, pick: QuantProPick, context: Dict) -> Tuple[int, float]:
        """
        Calcule score ML et multiplicateur
        V9.3: ML comme multiplicateur (évite double counting)
        """
        if not self.ml_model:
            pick.ml_confidence = 0.5
            pick.ml_prediction = "NO_MODEL"
            return 0, 1.0
        
        try:
            import numpy as np
            import warnings
            warnings.filterwarnings('ignore')
            
            # Construire features depuis context réel
            home_intel = context.get('home_intelligence') or {}
            away_intel = context.get('away_intelligence') or {}
            
            # Features basées sur vraies colonnes de team_intelligence
            features = [
                pick.implied_prob,
                pick.odds,
                pick.edge,
                float(home_intel.get('home_btts_rate', 50) or 50) / 100,
                float(away_intel.get('away_btts_rate', 50) or 50) / 100,
                float(home_intel.get('home_over25_rate', 50) or 50) / 100,
                float(away_intel.get('away_over25_rate', 50) or 50) / 100,
                float(home_intel.get('home_goals_scored_avg', 1.3) or 1.3),
                float(away_intel.get('away_goals_scored_avg', 1.1) or 1.1),
                float(home_intel.get('btts_tendency', 50) or 50) / 100,
                float(away_intel.get('btts_tendency', 50) or 50) / 100,
                float(home_intel.get('goals_tendency', 50) or 50) / 100,
                float(away_intel.get('goals_tendency', 50) or 50) / 100,
                pick.momentum_score / LAYER_WEIGHTS['momentum'] if LAYER_WEIGHTS['momentum'] else 0,
                pick.tactical_score / LAYER_WEIGHTS['tactical'] if LAYER_WEIGHTS['tactical'] else 0,
                1.0 if pick.profile_consensus else 0.0,
            ]
            
            X = np.array(features).reshape(1, -1)
            
            # Adapter au nombre de features attendu
            if self.ml_scaler:
                n_expected = getattr(self.ml_scaler, 'n_features_in_', len(features))
                if len(features) < n_expected:
                    features.extend([0.5] * (n_expected - len(features)))
                    X = np.array(features[:n_expected]).reshape(1, -1)
                elif len(features) > n_expected:
                    X = np.array(features[:n_expected]).reshape(1, -1)
                X = self.ml_scaler.transform(X)
            
            proba = self.ml_model.predict_proba(X)[0]
            confidence = max(proba)
            prediction = "WIN" if proba[1] >= 0.5 else "LOSE"
            
            pick.ml_confidence = confidence
            pick.ml_prediction = prediction
            
            # Score et multiplicateur
            ml_score = 0
            ml_mult = 1.0
            
            if prediction == "WIN" and confidence >= 0.70:
                ml_score = ML_CONFIG['bonus_high']
                ml_mult = ML_CONFIG['multiplier_high']
            elif prediction == "WIN" and confidence >= 0.60:
                ml_score = ML_CONFIG['bonus_medium']
                ml_mult = ML_CONFIG['multiplier_medium']
            elif prediction == "LOSE" and confidence >= 0.60:
                ml_score = ML_CONFIG['penalty_low']
                ml_mult = ML_CONFIG['multiplier_low']
            
            return ml_score, ml_mult
            
        except Exception as e:
            logger.debug(f"ML error: {e}")
            pick.ml_confidence = 0.5
            pick.ml_prediction = "ERROR"
            return 0, 1.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA COVERAGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_data_coverage(self, pick: QuantProPick) -> Tuple[float, int]:
        """
        Calcule le pourcentage de layers actifs
        V9.3: 8 layers possibles
        """
        layers = 0
        total = 8
        
        if pick.momentum_score != 0 or pick.home_momentum:
            layers += 1
        if pick.tactical_score != 0 or pick.tactical_match:
            layers += 1
        if pick.referee_score != 0 or pick.referee_data:
            layers += 1
        if pick.h2h_score != 0 or pick.h2h_data:
            layers += 1
        if pick.reality_score != 0 or pick.reality_data:
            layers += 1
        if pick.class_score != 0 or pick.home_class:
            layers += 1
        if pick.intelligence_score != 0 or pick.home_intelligence:
            layers += 1
        if pick.steam_score != 0 or pick.steam_data:
            layers += 1
        
        coverage = layers / total
        return coverage, layers
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECOMMENDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_recommendation(self, pick: QuantProPick) -> str:
        """Génère la recommandation finale"""
        score = pick.final_score
        coverage = pick.data_coverage
        
        low_data = coverage < 0.4
        suffix = " (Low Data)" if low_data else ""
        
        if pick.is_trap:
            return f"🚫 BLOCKED: {pick.trap_reason}"
        
        if score >= 80:
            return f"🟢 STRONG BET{suffix}"
        elif score >= 65:
            return f"🟢 GOOD BET{suffix}"
        elif score >= 50:
            return f"🟡 MODERATE{suffix}"
        elif score >= 35:
            return f"⚪ WATCH{suffix}"
        else:
            return f"🔴 SKIP{suffix}"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # KELLY CRITERION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_kelly(self, pick: QuantProPick) -> float:
        """Calcule le Kelly Criterion"""
        if pick.odds <= 1 or pick.edge <= 0:
            return 0.0
        
        # Estimation win prob basée sur edge
        win_prob = pick.implied_prob + pick.edge
        win_prob = max(0.01, min(0.99, win_prob))
        
        # Kelly = (bp - q) / b
        b = pick.odds - 1
        q = 1 - win_prob
        
        kelly = (b * win_prob - q) / b
        
        # Limiter à 5% max (Kelly fractionné)
        return max(0, min(kelly * 100, 5.0))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_match(self, match_data: Dict, referee_name: str = None) -> List[QuantProPick]:
        """
        Analyse complète d'un match
        V9.3 - Scientific Edition
        """
        picks = []
        
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        match_id = match_data.get('match_id', '')
        league = match_data.get('league', '')
        odds = match_data.get('odds', {})
        
        # Pre-fetch context (1 seul fetch pour tout le match)
        context = self._prefetch_match_context(
            home_team, away_team, match_id, league, referee_name
        )
        
        # Marchés à analyser
        markets = [
            ('btts_yes', odds.get('btts_yes')),
            ('btts_no', odds.get('btts_no')),
            ('over_25', odds.get('over_25')),
            ('under_25', odds.get('under_25')),
            ('over_35', odds.get('over_35')),
            ('under_35', odds.get('under_35')),
            ('over_15', odds.get('over_15')),
            ('home', odds.get('home')),
            ('away', odds.get('away')),
        ]
        
        for market_type, market_odds in markets:
            if not market_odds or market_odds <= 1:
                continue
            
            pick = QuantProPick(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                market_type=market_type,
                odds=market_odds,
                implied_prob=1 / market_odds,
                edge=max(0, (1 / market_odds) - 0.52),  # Baseline 52%
            )
            
            # Base score
            pick.base_score = self.calculate_base_score(pick)
            
            # Check trap first
            if self.check_trap(pick, context):
                pick.final_score = 0
                pick.recommendation = self.get_recommendation(pick)
                picks.append(pick)
                self.stats['analyzed'] += 1
                continue
            
            # Calculate all layer scores
            pick.momentum_score = self.calculate_momentum_score(pick, context)
            pick.tactical_score = self.calculate_tactical_score(pick, context)
            pick.intelligence_score = self.calculate_intelligence_score(pick, context)
            pick.class_score = self.calculate_class_score(pick, context)
            pick.referee_score = self.calculate_referee_score(pick, context)
            pick.h2h_score = self.calculate_h2h_score(pick, context)
            pick.reality_score = self.calculate_reality_score(pick, context)
            pick.steam_score = self.calculate_steam_score(pick, context)
            pick.profile_score = self.calculate_profile_score(pick, context)
            
            # Layer score (avant ML)
            pick.layer_score = (
                pick.base_score +
                pick.momentum_score +
                pick.tactical_score +
                pick.intelligence_score +
                pick.class_score +
                pick.referee_score +
                pick.h2h_score +
                pick.reality_score +
                pick.steam_score +
                pick.profile_score
            )
            
            # Sweet spot
            pick.sweet_spot_score = self.calculate_sweet_spot(pick)
            pick.layer_score += pick.sweet_spot_score
            
            # ML (multiplicateur)
            pick.ml_score, pick.ml_multiplier = self.calculate_ml_score(pick, context)
            
            # Final score
            pick.final_score = int(pick.layer_score * pick.ml_multiplier) + pick.ml_score
            
            # Data coverage
            pick.data_coverage, pick.layers_active = self.calculate_data_coverage(pick)
            
            if pick.data_coverage >= 0.5:
                self.stats['high_coverage'] += 1
            else:
                self.stats['low_coverage'] += 1
            
            # Kelly
            pick.kelly = self.calculate_kelly(pick)
            
            # Recommendation
            pick.recommendation = self.get_recommendation(pick)
            
            picks.append(pick)
            self.stats['analyzed'] += 1
        
        return picks
    
    def filter_best_picks(self, picks: List[QuantProPick], max_picks: int = 5) -> List[QuantProPick]:
        """Filtre et trie les meilleurs picks"""
        # Filtrer les traps
        valid = [p for p in picks if not p.is_trap]
        
        # Trier par score final
        valid.sort(key=lambda p: (p.final_score, p.data_coverage), reverse=True)
        
        self.stats['final_picks'] = min(len(valid), max_picks)
        
        return valid[:max_picks]
    
    def print_summary(self):
        """Affiche le résumé des stats"""
        print("\n" + "="*70)
        print("📊 ORCHESTRATOR V9.3 SCIENTIFIC - RÉSUMÉ")
        print("="*70)
        for key, value in self.stats.items():
            label = key.replace('_', ' ').title()
            print(f"   {label:<30} {value}")
        print("="*70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("🎯 ORCHESTRATOR V9.3 - SCIENTIFIC EDITION")
    print("="*70)
    print("Basé sur analyse réelle des structures DB (03/12/2025)")
    print("="*70)
    print("Tables utilisées:")
    print("  • team_intelligence (675 lignes) - tendencies, styles")
    print("  • team_momentum (110 lignes) - form, streaks")
    print("  • team_class (231 lignes) - tier, big_game_factor")
    print("  • team_name_mapping (179 lignes) - résolution noms")
    print("  • tactical_matrix (144 lignes) - style matchups")
    print("  • referee_intelligence (21 lignes)")
    print("  • team_head_to_head (772 lignes)")
    print("  • market_traps (196 lignes)")
    print("  • team_market_profiles (71 lignes)")
    print("  • fg_sharp_money (6 lignes)")
    print("="*70)
    
    orchestrator = OrchestratorV93Scientific()
    
    # Test match
    test_match = {
        'match_id': 'test_liverpool_city',
        'home_team': 'Liverpool',
        'away_team': 'Manchester City',
        'league': 'Premier League',
        'odds': {
            'home': 2.80,
            'draw': 3.40,
            'away': 2.50,
            'btts_yes': 1.65,
            'btts_no': 2.10,
            'over_25': 1.70,
            'under_25': 2.05,
            'over_35': 2.40,
            'under_35': 1.55,
        }
    }
    
    print(f"\n📌 Test: {test_match['home_team']} vs {test_match['away_team']}")
    print("-"*70)
    
    picks = orchestrator.analyze_match(test_match, referee_name="Michael Oliver")
    best_picks = orchestrator.filter_best_picks(picks, max_picks=5)
    
    print(f"\n🎯 TOP {len(best_picks)} PICKS:")
    print("-"*70)
    
    for i, pick in enumerate(best_picks, 1):
        sweet = "⭐" if pick.is_sweet_spot else ""
        data_ind = "🟢" if pick.data_coverage >= 0.5 else "🟡" if pick.data_coverage >= 0.4 else "🔴"
        
        print(f"\n#{i} {pick.market_type.upper()} @ {pick.odds} {sweet}")
        print(f"   Score Final: {pick.final_score} | Layer: {pick.layer_score} | Edge: {pick.edge*100:.1f}%")
        print(f"   📊 Data Coverage: {data_ind} {pick.data_coverage*100:.0f}% ({pick.layers_active}/8 layers)")
        print(f"   Layers: Mom={pick.momentum_score} | Tac={pick.tactical_score} | Intel={pick.intelligence_score} | Class={pick.class_score}")
        print(f"           Ref={pick.referee_score} | H2H={pick.h2h_score} | RC={pick.reality_score} | Steam={pick.steam_score}")
        print(f"   Profile={pick.profile_score} | SS={pick.sweet_spot_score}")
        print(f"   🤖 ML: {pick.ml_confidence*100:.1f}% {pick.ml_prediction} (×{pick.ml_multiplier:.2f})")
        print(f"   Kelly: {pick.kelly:.2f}%")
        print(f"   ➜ {pick.recommendation}")
        
        if pick.reasons:
            for reason in pick.reasons[:3]:
                print(f"      {reason}")
        if pick.warnings:
            for warning in pick.warnings[:2]:
                print(f"      {warning}")
    
    orchestrator.print_summary()
    print("\n✅ Orchestrator V9.3 Scientific prêt!")


if __name__ == "__main__":
    main()


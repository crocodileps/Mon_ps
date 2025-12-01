"""
🏎️ FERRARI Intelligence Service
================================
Module d'enrichissement pour PATRON Diamond V3

Fournit:
- Profils d'équipes (tags, style, alertes)
- Alertes pièges pour les marchés
- Recommandations basées sur l'intelligence tactique

Intégration:
- Se connecte à team_intelligence
- Enrichit les analyses PATRON Diamond
- Ajoute des warnings sur les pièges
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Coach Intelligence Integration
import sys
sys.path.insert(0, "/app/agents")
try:
    from coach_impact import CoachImpactCalculator
    COACH_INTELLIGENCE_ENABLED = True
except ImportError:
    COACH_INTELLIGENCE_ENABLED = False

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    TRAP = "TRAP"           # 🚨 Piège - NE PAS PARIER
    CAUTION = "CAUTION"     # ⚠️ Attention - Réduire stake
    NEUTRAL = "NEUTRAL"     # ➖ Neutre
    VALUE = "VALUE"         # ✅ Value potentielle
    SAFE = "SAFE"           # 💚 Safe bet


@dataclass
class TeamProfile:
    """Profil complet d'une équipe"""
    name: str
    style: str
    style_score: int
    
    # Profils dom/ext
    home_profile: str
    away_profile: str
    home_strength: int
    away_strength: int
    
    # Stats clés
    home_win_rate: float
    home_draw_rate: float
    away_win_rate: float
    btts_rate: float
    over25_rate: float
    clean_sheet_rate: float
    
    # Tags et alertes
    tags: List[str]
    market_alerts: Dict
    
    # Meta
    matches_analyzed: int
    is_reliable: bool
    confidence: int


@dataclass
class MarketAlert:
    """Alerte pour un marché spécifique"""
    market: str
    level: AlertLevel
    reason: str
    alternative: Optional[str]
    value: float
    threshold: float


class FerrariIntelligenceService:
    """
    Service d'intelligence tactique FERRARI
    
    Enrichit les analyses avec:
    - Profils d'équipes
    - Alertes pièges
    - Recommandations contextuelles
    """
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'monps_postgres'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
        logger.info("🏎️ Ferrari Intelligence Service initialisé")

    def get_coach_enrichment(self, team_name: str) -> Dict:
        """
        🧠 Enrichit avec les données Coach Intelligence
        
        Returns:
            {
                'coach_name': str,
                'tactical_style': str,
                'att_multiplier': float,
                'def_multiplier': float,
                'is_reliable': bool,
                'insights': List[str]
            }
        """
        if not COACH_INTELLIGENCE_ENABLED:
            return {'enabled': False}
        
        try:
            calc = CoachImpactCalculator()
            factors = calc.get_coach_factors(team_name)
            
            insights = []
            
            # Générer insights basés sur le style
            style = factors.get('style', 'unknown')
            att = factors.get('att', 1.0)
            def_mult = factors.get('def', 1.0)
            
            if 'offensive' in style:
                insights.append(f"🔥 Coach offensif (ATT x{att:.2f})")
                if att > 1.5:
                    insights.append("⚽ Favorise les Over/BTTS")
            elif 'defensive' in style:
                insights.append(f"🛡️ Coach défensif (DEF x{def_mult:.2f})")
                if def_mult < 0.7:
                    insights.append("🧱 Favorise les Under/Clean Sheet")
            
            if def_mult > 1.3:
                insights.append("⚠️ Défense poreuse - BTTS probable")
            elif def_mult < 0.6:
                insights.append("💪 Défense solide - Under probable")
            
            return {
                'enabled': True,
                'coach_name': factors.get('coach'),
                'tactical_style': style,
                'att_multiplier': round(att, 2),
                'def_multiplier': round(def_mult, 2),
                'is_reliable': factors.get('reliable', False),
                'insights': insights
            }
        except Exception as e:
            logger.debug(f"Coach enrichment error: {e}")
            return {'enabled': False, 'error': str(e)}

    def enrich_match_with_coaches(self, home_team: str, away_team: str) -> Dict:
        """
        🧠 Enrichissement complet avec les 2 coaches
        
        Returns:
            {
                'home_coach': {...},
                'away_coach': {...},
                'tactical_matchup': str,
                'xg_adjustment': {...},
                'market_insights': {...}
            }
        """
        home_coach = self.get_coach_enrichment(home_team)
        away_coach = self.get_coach_enrichment(away_team)
        
        result = {
            'home_coach': home_coach,
            'away_coach': away_coach,
            'tactical_matchup': 'unknown',
            'market_insights': {}
        }
        
        if not home_coach.get('enabled') or not away_coach.get('enabled'):
            return result
        
        h_style = home_coach.get('tactical_style', 'unknown')
        a_style = away_coach.get('tactical_style', 'unknown')
        h_att = home_coach.get('att_multiplier', 1.0)
        a_att = away_coach.get('att_multiplier', 1.0)
        h_def = home_coach.get('def_multiplier', 1.0)
        a_def = away_coach.get('def_multiplier', 1.0)
        
        # Déterminer le type de confrontation
        if 'offensive' in h_style and 'offensive' in a_style:
            result['tactical_matchup'] = 'OPEN_GAME'
            result['market_insights'] = {
                'over_25': {'boost': 15, 'reason': '2 coaches offensifs = match ouvert'},
                'btts_yes': {'boost': 10, 'reason': 'Les deux équipes marquent'},
            }
        elif 'defensive' in h_style and 'defensive' in a_style:
            result['tactical_matchup'] = 'CLOSED_GAME'
            result['market_insights'] = {
                'under_25': {'boost': 15, 'reason': '2 coaches défensifs = match fermé'},
                'draw': {'boost': 10, 'reason': 'Équilibre défensif'},
            }
        elif 'offensive' in h_style and 'defensive' in a_style:
            result['tactical_matchup'] = 'HOME_ATTACK_VS_AWAY_BLOCK'
            result['market_insights'] = {
                'home_win': {'boost': 5, 'reason': f'{home_coach.get("coach_name")} offensif à domicile'},
                'under_25': {'boost': 8, 'reason': 'Visiteur défensif'},
            }
        elif 'defensive' in h_style and 'offensive' in a_style:
            result['tactical_matchup'] = 'COUNTER_ATTACK_RISK'
            result['market_insights'] = {
                'away_win': {'boost': 5, 'reason': f'{away_coach.get("coach_name")} offensif en déplacement'},
                'btts_yes': {'boost': 5, 'reason': 'Contre-attaque probable'},
            }
        
        # xG Adjustment preview
        total_att = h_att * a_def + a_att * h_def
        if total_att > 3.0:
            result['market_insights']['over_35'] = {'boost': 10, 'reason': f'xG élevés attendus ({total_att:.1f})'}
        elif total_att < 2.0:
            result['market_insights']['under_15'] = {'boost': 10, 'reason': f'xG faibles attendus ({total_att:.1f})'}
        
        return result

    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    # ════════════════════════════════════════════════════════════
    # RÉCUPÉRATION PROFILS
    # ════════════════════════════════════════════════════════════
    
    def get_team_profile(self, team_name: str) -> Optional[TeamProfile]:
        """
        Récupère le profil complet d'une équipe depuis team_intelligence
        """
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Recherche exacte puis fuzzy
            cur.execute("""
                SELECT * FROM team_intelligence
                WHERE team_name = %s 
                   OR team_name ILIKE %s
                   OR team_name_normalized ILIKE %s
                LIMIT 1
            """, (team_name, f"%{team_name}%", f"%{team_name.lower().replace(' ', '_')}%"))
            
            row = cur.fetchone()
            if not row:
                logger.debug(f"Profil non trouvé pour: {team_name}")
                return None
            
            # Parser les JSONB
            tags = row["tags"] if row["tags"] else []
            alerts = row["market_alerts"] if row["market_alerts"] else {}
            
            return TeamProfile(
                name=row['team_name'],
                style=row['current_style'] or 'unknown',
                style_score=row['current_style_score'] or 50,
                home_profile=row['home_profile'] or 'balanced',
                away_profile=row['away_profile'] or 'balanced',
                home_strength=row['home_strength'] or 50,
                away_strength=row['away_strength'] or 30,
                home_win_rate=float(row['home_win_rate'] or 50),
                home_draw_rate=float(row['home_draw_rate'] or 25),
                away_win_rate=float(row['away_win_rate'] or 25),
                btts_rate=float(row['btts_tendency'] or 50),
                over25_rate=float(row['goals_tendency'] or 50),
                clean_sheet_rate=float(row['clean_sheet_tendency'] or 25),
                tags=tags,
                market_alerts=alerts,
                matches_analyzed=row['matches_analyzed'] or 0,
                is_reliable=row['is_reliable'] or False,
                confidence=row['confidence_overall'] or 0
            )
            
        except Exception as e:
            logger.error(f"Erreur get_team_profile: {e}")
            return None
        finally:
            cur.close()
            conn.close()
    
    # ════════════════════════════════════════════════════════════
    # ALERTES MARCHÉS
    # ════════════════════════════════════════════════════════════
    
    def get_market_alerts(self, team_name: str, market: str) -> Optional[MarketAlert]:
        """
        Récupère l'alerte pour un marché spécifique
        """
        profile = self.get_team_profile(team_name)
        if not profile or not profile.market_alerts:
            return None
        
        # Normaliser le nom du marché
        market_key = market.lower().replace(' ', '_').replace('.', '_')
        market_mappings = {
            'btts': 'btts_yes',
            'btts yes': 'btts_yes',
            'btts no': 'btts_no',
            'over 2.5': 'over_25',
            'over25': 'over_25',
            'under 2.5': 'under_25',
            'under25': 'under_25',
            'double chance 12': 'dc_12',
            'dc12': 'dc_12',
            '1x2 home': 'home',
            '1x2 away': 'away',
            '1x2 draw': 'draw',
        }
        market_key = market_mappings.get(market_key, market_key)
        
        alert_data = profile.market_alerts.get(market_key)
        if not alert_data:
            return None
        
        return MarketAlert(
            market=market_key,
            level=AlertLevel[alert_data.get('level', 'NEUTRAL')],
            reason=alert_data.get('reason', ''),
            alternative=alert_data.get('alternative'),
            value=alert_data.get('value', 0),
            threshold=alert_data.get('threshold', 0)
        )
    
    def check_match_traps(self, home_team: str, away_team: str, market: str) -> Dict:
        """
        Vérifie les pièges pour un match sur un marché donné
        
        Returns:
            {
                'has_trap': bool,
                'alerts': [MarketAlert],
                'recommendation': str,
                'adjusted_confidence': float
            }
        """
        home_alert = self.get_market_alerts(home_team, market)
        away_alert = self.get_market_alerts(away_team, market)
        
        alerts = []
        has_trap = False
        confidence_penalty = 0
        
        if home_alert:
            alerts.append({
                'team': home_team,
                'location': 'home',
                'level': home_alert.level.value,
                'reason': home_alert.reason,
                'alternative': home_alert.alternative
            })
            if home_alert.level == AlertLevel.TRAP:
                has_trap = True
                confidence_penalty += 30
            elif home_alert.level == AlertLevel.CAUTION:
                confidence_penalty += 15
        
        if away_alert:
            alerts.append({
                'team': away_team,
                'location': 'away',
                'level': away_alert.level.value,
                'reason': away_alert.reason,
                'alternative': away_alert.alternative
            })
            if away_alert.level == AlertLevel.TRAP:
                has_trap = True
                confidence_penalty += 30
            elif away_alert.level == AlertLevel.CAUTION:
                confidence_penalty += 15
        
        # Générer recommandation
        if has_trap:
            recommendation = f"🚨 PIÈGE DÉTECTÉ - Éviter {market.upper()}"
            if alerts and alerts[0].get('alternative'):
                recommendation += f" → Préférer {alerts[0]['alternative'].upper()}"
        elif confidence_penalty > 0:
            recommendation = f"⚠️ PRUDENCE sur {market.upper()} - Réduire stake"
        else:
            recommendation = f"✅ {market.upper()} - Pas d'alerte"
        
        return {
            'has_trap': has_trap,
            'alerts': alerts,
            'recommendation': recommendation,
            'confidence_penalty': confidence_penalty
        }
    
    # ════════════════════════════════════════════════════════════
    # ENRICHISSEMENT ANALYSE
    # ════════════════════════════════════════════════════════════
    
    def enrich_match_analysis(self, home_team: str, away_team: str) -> Dict:
        """
        Enrichit une analyse de match avec l'intelligence FERRARI
        
        Returns:
            {
                'home_profile': TeamProfile,
                'away_profile': TeamProfile,
                'style_matchup': str,
                'traps': {market: trap_info},
                'recommendations': [str],
                'confidence_adjustment': int
            }
        """
        home_profile = self.get_team_profile(home_team)
        away_profile = self.get_team_profile(away_team)
        
        # Analyse du matchup de styles
        style_matchup = self._analyze_style_matchup(home_profile, away_profile)
        
        # Vérifier les pièges sur tous les marchés
        markets_to_check = ['home', 'away', 'draw', 'btts_yes', 'btts_no', 
                           'over_25', 'under_25', 'dc_12', 'dc_1x', 'dc_x2']
        
        traps = {}
        total_penalty = 0
        recommendations = []
        
        for market in markets_to_check:
            trap_info = self.check_match_traps(home_team, away_team, market)
            if trap_info['has_trap'] or trap_info['confidence_penalty'] > 0:
                traps[market] = trap_info
                total_penalty = max(total_penalty, trap_info['confidence_penalty'])
                if trap_info['has_trap']:
                    recommendations.append(trap_info['recommendation'])
        
        # Générer les recommandations basées sur les profils
        if home_profile and away_profile:
            recommendations.extend(self._generate_profile_recommendations(
                home_profile, away_profile
            ))
        
        return {
            'home_profile': self._profile_to_dict(home_profile) if home_profile else None,
            'away_profile': self._profile_to_dict(away_profile) if away_profile else None,
            'style_matchup': style_matchup,
            'traps': traps,
            'recommendations': recommendations[:5],  # Top 5
            'confidence_adjustment': -total_penalty,
            'ferrari_analyzed': True
        }
    
    def _analyze_style_matchup(self, home: Optional[TeamProfile], 
                                away: Optional[TeamProfile]) -> str:
        """Analyse le matchup des styles"""
        if not home or not away:
            return "unknown"
        
        # Combinaisons intéressantes
        if home.style == 'offensive' and away.style == 'offensive':
            return "🔥 HIGH SCORING EXPECTED - Deux équipes offensives"
        elif home.style == 'defensive' and away.style == 'defensive':
            return "🛡️ LOW SCORING EXPECTED - Deux équipes défensives"
        elif home.style == 'offensive' and away.style == 'defensive':
            return "⚔️ ATTACK vs DEFENSE - Match tactique"
        elif 'fortress_home' in home.tags:
            return "🏰 FORTRESS HOME - Domicile très fort"
        elif 'weak_away' in away.tags:
            return "📉 WEAK VISITORS - Extérieur fragile"
        elif 'roi_nuls' in home.tags or 'roi_nuls' in away.tags:
            return "🤝 DRAW LIKELY - Équipe(s) qui fait beaucoup de nuls"
        else:
            return "📊 STANDARD MATCHUP"
    
    def _generate_profile_recommendations(self, home: TeamProfile, 
                                          away: TeamProfile) -> List[str]:
        """Génère des recommandations basées sur les profils"""
        recs = []
        
        # Home fortress
        if 'fortress_home' in home.tags:
            recs.append(f"🏰 {home.name} très fort à domicile ({home.home_win_rate:.0f}% WR)")
        
        # Weak away
        if 'weak_away' in away.tags:
            recs.append(f"📉 {away.name} faible en déplacement ({away.away_win_rate:.0f}% WR)")
        
        # BTTS friendly
        if 'btts_friendly' in home.tags and 'btts_friendly' in away.tags:
            recs.append("⚽ BTTS YES recommandé - Deux équipes qui marquent et encaissent")
        
        # High scoring
        if 'high_scoring' in home.tags or 'high_scoring' in away.tags:
            recs.append("🎯 OVER 2.5 favorable - Match à buts attendu")
        
        # Defensive matchup
        if 'defensif' in home.tags and 'defensif' in away.tags:
            recs.append("🛡️ UNDER 2.5 favorable - Deux équipes défensives")
        
        # Draw tendency
        if 'roi_nuls' in home.tags:
            recs.append(f"🤝 {home.name} fait beaucoup de nuls - DC_1X ou DRAW")
        
        return recs
    
    def _profile_to_dict(self, profile: TeamProfile) -> Dict:
        """Convertit un profil en dictionnaire"""
        return {
            'name': profile.name,
            'style': profile.style,
            'style_score': profile.style_score,
            'home_profile': profile.home_profile,
            'away_profile': profile.away_profile,
            'home_strength': profile.home_strength,
            'away_strength': profile.away_strength,
            'home_win_rate': profile.home_win_rate,
            'away_win_rate': profile.away_win_rate,
            'tags': profile.tags,
            'is_reliable': profile.is_reliable,
            'matches_analyzed': profile.matches_analyzed
        }


# Singleton
_ferrari_service = None

def get_ferrari_intelligence():
    """Factory pour obtenir le service Ferrari"""
    global _ferrari_service
    if _ferrari_service is None:
        _ferrari_service = FerrariIntelligenceService()
    return _ferrari_service

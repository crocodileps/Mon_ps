"""
🧠 TACTICAL INTELLIGENCE SERVICE - V4.1
══════════════════════════════════════════════════════════════════════════════

Modules d'intelligence tactique pour corriger les biais de l'algo:

1. TACTICAL MISMATCH (Vitesse vs Lenteur)
2. SQUAD VALUE GAP (Écart Technique)  
3. RECENCY BIAS CORRECTION (Dépréciation Historique)
4. GAME SCRIPT SIMULATOR (Fragilité Mentale)

Basé sur l'analyse post-mortem Everton 0-3 Newcastle

VERSION: 4.1.0
DATE: 29/11/2025
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DB
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "dbname": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


class RiskLevel(Enum):
    """Niveaux de risque"""
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGER = "DANGER"
    REJECT = "REJECT"


@dataclass
class TacticalAlert:
    """Alerte tactique"""
    alert_type: str
    risk_level: RiskLevel
    message: str
    penalty_score: int
    details: Dict


@dataclass
class TeamProfile:
    """Profil tactique d'une équipe"""
    team_name: str
    # Vitesse
    attack_speed: str  # "FAST_COUNTER", "POSSESSION", "DIRECT"
    defense_speed: str  # "HIGH_LINE", "SLOW_BLOCK", "BALANCED"
    # Qualité
    squad_value_tier: str  # "TOP4", "MID_TABLE", "RELEGATION"
    quality_score: float  # 0-100
    # Forme
    last_5_points: int
    last_5_goals_for: int
    last_5_goals_against: int
    # Résilience
    resilience_score: float  # % de matchs récupérés après 0-1
    collapse_rate: float  # % de matchs perdus 2+ buts après 0-1


class TacticalIntelligenceService:
    """Service d'Intelligence Tactique"""
    
    def __init__(self):
        self.conn = None
        
        # Classification des équipes par tier (à enrichir)
        self.SQUAD_TIERS = {
            # Premier League TOP 4
            "Manchester City": "TOP4",
            "Arsenal": "TOP4", 
            "Liverpool": "TOP4",
            "Newcastle United": "TOP4",
            "Chelsea": "TOP4",
            "Manchester United": "TOP6",
            "Tottenham Hotspur": "TOP6",
            "Aston Villa": "TOP6",
            # Mid-table
            "Brighton and Hove Albion": "MID_TABLE",
            "West Ham United": "MID_TABLE",
            "Fulham": "MID_TABLE",
            "Brentford": "MID_TABLE",
            "Crystal Palace": "MID_TABLE",
            "Bournemouth": "MID_TABLE",
            "Wolverhampton Wanderers": "MID_TABLE",
            "Nottingham Forest": "MID_TABLE",
            # Relegation
            "Everton": "RELEGATION",
            "Luton Town": "RELEGATION",
            "Burnley": "RELEGATION",
            "Sheffield United": "RELEGATION",
            "Ipswich Town": "RELEGATION",
            "Leicester City": "RELEGATION",
            "Southampton": "RELEGATION",
        }
        
        # Profils de vitesse d'attaque
        self.ATTACK_PROFILES = {
            # Fast Counter Teams
            "Newcastle United": "FAST_COUNTER",
            "Liverpool": "FAST_COUNTER",
            "Arsenal": "FAST_COUNTER",
            "Brentford": "FAST_COUNTER",
            "Borussia Dortmund": "FAST_COUNTER",
            "Real Madrid": "FAST_COUNTER",
            "Athletic Bilbao": "FAST_COUNTER",
            # Possession
            "Manchester City": "POSSESSION",
            "Barcelona": "POSSESSION",
            "Bayern Munich": "POSSESSION",
            # Direct
            "Everton": "DIRECT",
            "Burnley": "DIRECT",
            "West Ham United": "DIRECT",
        }
        
        # Profils de défense
        self.DEFENSE_PROFILES = {
            # Slow Block (vulnérables aux contres)
            "Everton": "SLOW_BLOCK",
            "Burnley": "SLOW_BLOCK",
            "West Ham United": "SLOW_BLOCK",
            "Sheffield United": "SLOW_BLOCK",
            "Levante": "SLOW_BLOCK",
            # High Line (vulnérables aux ballons en profondeur)
            "Manchester City": "HIGH_LINE",
            "Arsenal": "HIGH_LINE",
            "Liverpool": "HIGH_LINE",
            # Balanced
            "Newcastle United": "BALANCED",
            "Chelsea": "BALANCED",
            "Tottenham Hotspur": "BALANCED",
        }
    
    def get_connection(self):
        """Obtenir connexion DB"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MODULE 1: TACTICAL MISMATCH (Vitesse vs Lenteur)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_tactical_mismatch(self, home_team: str, away_team: str) -> Optional[TacticalAlert]:
        """
        Vérifie le mismatch tactique Vitesse vs Lenteur
        
        RÈGLE: Si l'attaque adverse est FAST_COUNTER et la défense locale est SLOW_BLOCK
        → Pénalité -30 points, Risque de carnage en contre-attaque
        """
        away_attack = self.ATTACK_PROFILES.get(away_team, "UNKNOWN")
        home_defense = self.DEFENSE_PROFILES.get(home_team, "UNKNOWN")
        
        if away_attack == "FAST_COUNTER" and home_defense == "SLOW_BLOCK":
            return TacticalAlert(
                alert_type="TACTICAL_MISMATCH",
                risk_level=RiskLevel.DANGER,
                message=f"⚡ MISMATCH VITESSE: {away_team} (contre-attaque rapide) vs {home_team} (défense lente)",
                penalty_score=-30,
                details={
                    "away_attack_style": away_attack,
                    "home_defense_style": home_defense,
                    "risk": "Si le home encaisse en premier, risque de carnage (0-3, 0-4)",
                    "recommendation": "ÉVITER 1X ou HOME WIN"
                }
            )
        
        if away_attack == "FAST_COUNTER" and home_defense != "HIGH_LINE":
            return TacticalAlert(
                alert_type="TACTICAL_CAUTION",
                risk_level=RiskLevel.CAUTION,
                message=f"⚠️ {away_team} dangereux en contre-attaque",
                penalty_score=-10,
                details={
                    "away_attack_style": away_attack,
                    "home_defense_style": home_defense,
                    "risk": "Potentiel de buts rapides si scénario défavorable"
                }
            )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MODULE 2: SQUAD VALUE GAP (Écart Technique)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_tier_value(self, tier: str) -> int:
        """Retourne une valeur numérique pour le tier"""
        tiers = {
            "TOP4": 100,
            "TOP6": 85,
            "MID_TABLE": 60,
            "RELEGATION": 35,
            "UNKNOWN": 50
        }
        return tiers.get(tier, 50)
    
    def check_squad_value_gap(self, home_team: str, away_team: str) -> Optional[TacticalAlert]:
        """
        Vérifie l'écart technique entre les équipes
        
        RÈGLE: Si Away vaut 2.5x plus que Home → DÉSACTIVER le signal 1X/Home Win
        """
        home_tier = self.SQUAD_TIERS.get(home_team, "UNKNOWN")
        away_tier = self.SQUAD_TIERS.get(away_team, "UNKNOWN")
        
        home_value = self.get_tier_value(home_tier)
        away_value = self.get_tier_value(away_tier)
        
        ratio = away_value / max(home_value, 1)
        
        if ratio >= 2.5:
            return TacticalAlert(
                alert_type="SQUAD_VALUE_GAP",
                risk_level=RiskLevel.REJECT,
                message=f"🚫 ÉCART TECHNIQUE CRITIQUE: {away_team} ({away_tier}) >> {home_team} ({home_tier})",
                penalty_score=-50,
                details={
                    "home_tier": home_tier,
                    "away_tier": away_tier,
                    "value_ratio": round(ratio, 2),
                    "recommendation": "INTERDIRE 1X et HOME WIN - David vs Goliath"
                }
            )
        elif ratio >= 1.5:
            return TacticalAlert(
                alert_type="SQUAD_VALUE_CAUTION",
                risk_level=RiskLevel.CAUTION,
                message=f"⚠️ Écart technique notable: {away_team} > {home_team}",
                penalty_score=-15,
                details={
                    "home_tier": home_tier,
                    "away_tier": away_tier,
                    "value_ratio": round(ratio, 2),
                    "recommendation": "Réduire confiance sur 1X"
                }
            )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MODULE 3: RECENCY BIAS CORRECTION (Dépréciation Historique)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_form(self, team_name: str) -> Dict:
        """Récupère la forme récente d'une équipe"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COALESCE(last_5_form, '') as form,
                        COALESCE(home_win_rate, 0) as home_win_rate,
                        COALESCE(away_win_rate, 0) as away_win_rate,
                        COALESCE(home_goals_scored_avg, 0) as home_goals_avg,
                        COALESCE(home_goals_conceded_avg, 0) as home_conceded_avg
                    FROM team_intelligence
                    WHERE team_name ILIKE %s
                    LIMIT 1
                """, (f"%{team_name}%",))
                
                row = cur.fetchone()
                if row:
                    # Calculer les points des 5 derniers matchs depuis la forme
                    form = row.get('form', '')
                    points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in form[:5])
                    
                    return {
                        "form": form[:5],
                        "last_5_points": points,
                        "home_win_rate": float(row['home_win_rate']),
                        "home_goals_avg": float(row['home_goals_avg']),
                        "home_conceded_avg": float(row['home_conceded_avg'])
                    }
                return {"form": "", "last_5_points": 0, "home_win_rate": 0}
        except Exception as e:
            logger.error(f"Error getting team form: {e}")
            return {"form": "", "last_5_points": 0, "home_win_rate": 0}
    
    def check_recency_bias(self, home_team: str, market_type: str) -> Optional[TacticalAlert]:
        """
        Corrige le biais de récence - la forme actuelle prime sur l'historique
        
        RÈGLE: Si forme récente < 4 points sur 15 possibles → WARNING même si ROI historique positif
        """
        form_data = self.get_team_form(home_team)
        last_5_points = form_data.get("last_5_points", 0)
        form_str = form_data.get("form", "")
        
        # Forme critique (moins de 4 points sur 15)
        if last_5_points < 4:
            return TacticalAlert(
                alert_type="RECENCY_BIAS_WARNING",
                risk_level=RiskLevel.DANGER,
                message=f"📉 FORME CRITIQUE: {home_team} ({form_str}) = {last_5_points}/15 pts",
                penalty_score=-25,
                details={
                    "form": form_str,
                    "points": last_5_points,
                    "max_points": 15,
                    "recommendation": "L'historique ne compense PAS une forme actuelle catastrophique"
                }
            )
        
        # Forme moyenne (5-7 points)
        elif last_5_points < 7:
            return TacticalAlert(
                alert_type="FORM_CAUTION",
                risk_level=RiskLevel.CAUTION,
                message=f"⚠️ Forme moyenne: {home_team} ({form_str}) = {last_5_points}/15 pts",
                penalty_score=-10,
                details={
                    "form": form_str,
                    "points": last_5_points,
                    "recommendation": "Réduire la confiance"
                }
            )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MODULE 4: GAME SCRIPT SIMULATOR (Résilience/Collapse)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_resilience(self, home_team: str, away_team: str) -> Optional[TacticalAlert]:
        """
        Vérifie la capacité de l'équipe à réagir après avoir encaissé
        
        RÈGLE: Si le home a un taux de "collapse" élevé face à une équipe qui marque souvent en premier
        → Interdire le pari 1X
        """
        # Équipes qui marquent souvent en premier
        EARLY_SCORERS = [
            "Newcastle United", "Liverpool", "Arsenal", "Manchester City",
            "Bayer Leverkusen", "Real Madrid", "Barcelona", "Bayern Munich",
            "Borussia Dortmund", "Inter Milan", "Napoli"
        ]
        
        # Équipes avec faible résilience (collapse quand menés)
        LOW_RESILIENCE = {
            "Everton": 0.65,  # 65% de collapse
            "Burnley": 0.70,
            "Sheffield United": 0.75,
            "Luton Town": 0.68,
            "Southampton": 0.60,
            "Ipswich Town": 0.62,
            "Levante": 0.55,
        }
        
        home_collapse = LOW_RESILIENCE.get(home_team, 0.3)  # 30% par défaut
        away_is_early_scorer = away_team in EARLY_SCORERS
        
        if home_collapse > 0.5 and away_is_early_scorer:
            return TacticalAlert(
                alert_type="COLLAPSE_RISK",
                risk_level=RiskLevel.DANGER,
                message=f"💔 RISQUE EFFONDREMENT: {home_team} ({int(home_collapse*100)}% collapse) vs {away_team} (marque tôt)",
                penalty_score=-35,
                details={
                    "home_collapse_rate": home_collapse,
                    "away_early_scorer": True,
                    "scenario": f"Si {away_team} marque en premier, {home_team} risque de s'effondrer",
                    "recommendation": "INTERDIRE 1X - Scénario 0-2 ou 0-3 probable"
                }
            )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SANITY CHECK PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def sanity_check(self, home_team: str, away_team: str, market_type: str) -> Dict:
        """
        Vérification de cohérence complète avant de valider un pari
        
        Exécute tous les modules et retourne un verdict final
        """
        alerts = []
        total_penalty = 0
        
        # Module 1: Tactical Mismatch
        mismatch = self.check_tactical_mismatch(home_team, away_team)
        if mismatch:
            alerts.append(mismatch)
            total_penalty += mismatch.penalty_score
        
        # Module 2: Squad Value Gap
        gap = self.check_squad_value_gap(home_team, away_team)
        if gap:
            alerts.append(gap)
            total_penalty += gap.penalty_score
        
        # Module 3: Recency Bias
        recency = self.check_recency_bias(home_team, market_type)
        if recency:
            alerts.append(recency)
            total_penalty += recency.penalty_score
        
        # Module 4: Resilience/Collapse
        resilience = self.check_resilience(home_team, away_team)
        if resilience:
            alerts.append(resilience)
            total_penalty += resilience.penalty_score
        
        # Déterminer le verdict final
        has_reject = any(a.risk_level == RiskLevel.REJECT for a in alerts)
        has_danger = any(a.risk_level == RiskLevel.DANGER for a in alerts)
        danger_count = sum(1 for a in alerts if a.risk_level == RiskLevel.DANGER)
        
        if has_reject:
            verdict = "🚫 REJECT"
            recommendation = "NE PAS PARIER - Écart technique trop grand"
        elif danger_count >= 2:
            verdict = "🚫 REJECT"
            recommendation = "NE PAS PARIER - Trop de signaux de danger"
        elif has_danger:
            verdict = "⚠️ DANGER"
            recommendation = "Pari très risqué - Réduire la mise de 75%"
        elif alerts:
            verdict = "⚠️ CAUTION"
            recommendation = "Réduire la mise de 50%"
        else:
            verdict = "✅ VALID"
            recommendation = "Pari validé par l'Intelligence Tactique"
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "market_type": market_type,
            "verdict": verdict,
            "recommendation": recommendation,
            "total_penalty": total_penalty,
            "alerts_count": len(alerts),
            "alerts": [
                {
                    "type": a.alert_type,
                    "level": a.risk_level.value,
                    "message": a.message,
                    "penalty": a.penalty_score,
                    "details": a.details
                }
                for a in alerts
            ]
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE BATCH
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_upcoming_matches(self) -> List[Dict]:
        """Analyser tous les matchs à venir avec l'Intelligence Tactique"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT
                        home_team,
                        away_team,
                        market_type,
                        diamond_score,
                        odds_taken,
                        commence_time
                    FROM tracking_clv_picks
                    WHERE commence_time > NOW()
                    AND commence_time < NOW() + INTERVAL '48 hours'
                    AND diamond_score >= 80
                    AND market_type IN ('dc_1x', 'dc_12', 'home', '1x', 'draw')
                    ORDER BY diamond_score DESC
                    LIMIT 30
                """)
                
                picks = cur.fetchall()
                results = []
                
                for pick in picks:
                    check = self.sanity_check(
                        pick['home_team'],
                        pick['away_team'],
                        pick['market_type']
                    )
                    
                    results.append({
                        "match": f"{pick['home_team']} vs {pick['away_team']}",
                        "market": pick['market_type'],
                        "original_score": pick['diamond_score'],
                        "adjusted_score": max(0, pick['diamond_score'] + check['total_penalty']),
                        "odds": float(pick['odds_taken']) if pick['odds_taken'] else 0,
                        "commence_time": pick['commence_time'].isoformat() if pick['commence_time'] else None,
                        **check
                    })
                
                # Trier par score ajusté
                results.sort(key=lambda x: x['adjusted_score'], reverse=True)
                
                return results
                
        except Exception as e:
            logger.error(f"Error analyzing matches: {e}")
            return []


# Instance globale
tactical_intel = TacticalIntelligenceService()

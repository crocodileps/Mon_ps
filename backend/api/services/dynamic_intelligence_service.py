"""
🧠 DYNAMIC INTELLIGENCE SERVICE - V5.1 SMART
══════════════════════════════════════════════════════════════════════════════

Service d'intelligence DYNAMIQUE et SMART - ZÉRO hardcoding.
Utilise les MEILLEURS profils (pas juste home/away) pour une analyse réaliste.

AMÉLIORATIONS V5.1:
- Profil GLOBAL (moyenne) + PEAK (meilleur) pour chaque équipe
- Détection du "Danger Potentiel Maximum" de l'adversaire
- Calcul de la "Vulnérabilité" du home face au profil adverse
- Score de confiance dynamique basé sur les données réelles

VERSION: 5.1.0
DATE: 29/11/2025
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

# Coach Intelligence Integration
import sys
sys.path.insert(0, "/app/agents")
try:
    from coach_impact import CoachImpactCalculator
    COACH_INTELLIGENCE_ENABLED = True
except ImportError:
    COACH_INTELLIGENCE_ENABLED = False

logger = structlog.get_logger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "dbname": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


class RiskLevel(Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGER = "DANGER"
    REJECT = "REJECT"


@dataclass
class SmartTeamProfile:
    """Profil SMART d'équipe - utilise les meilleures métriques"""
    team_name: str
    
    # Stats brutes
    attack_home: float
    attack_away: float
    defense_home: float  # Buts encaissés (plus c'est bas = mieux)
    defense_away: float
    home_win_rate: float
    away_win_rate: float
    home_draw_rate: float
    current_style: str
    
    # Stats CALCULÉES (SMART)
    avg_attack: float      # Moyenne attaque globale
    avg_defense: float     # Moyenne défense globale
    avg_win_rate: float    # Win rate moyen
    peak_attack: float     # MEILLEURE attaque (home ou away)
    peak_defense: float    # MEILLEURE défense (min des buts encaissés)
    
    # Scores SMART
    offensive_threat: float   # Menace offensive (0-100)
    defensive_solidity: float # Solidité défensive (0-100)
    quality_score: float      # Score qualité global (0-100)
    danger_index: float       # Indice de danger pour l'adversaire (0-100)


@dataclass
class TacticalAlert:
    """Alerte tactique"""
    alert_type: str
    risk_level: RiskLevel
    message: str
    penalty_score: int
    details: Dict


class DynamicIntelligenceService:
    """Service d'Intelligence Dynamique V5.1 SMART"""
    
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SMART PROFILING - Calcul intelligent des profils
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_smart_profile(self, team_name: str) -> Optional[SmartTeamProfile]:
        """
        Récupère le profil SMART d'une équipe avec calculs avancés
        """
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        team_name,
                        COALESCE(home_goals_scored_avg, 1.0) as attack_home,
                        COALESCE(away_goals_scored_avg, 0.8) as attack_away,
                        COALESCE(home_goals_conceded_avg, 1.2) as defense_home,
                        COALESCE(away_goals_conceded_avg, 1.5) as defense_away,
                        COALESCE(home_win_rate, 40) as home_win_rate,
                        COALESCE(away_win_rate, 25) as away_win_rate,
                        COALESCE(home_draw_rate, 25) as home_draw_rate,
                        COALESCE(current_style, 'balanced') as current_style,
                        -- Calculs SQL directs pour performance
                        (COALESCE(home_goals_scored_avg, 1.0) + COALESCE(away_goals_scored_avg, 0.8)) / 2 as avg_attack,
                        (COALESCE(home_goals_conceded_avg, 1.2) + COALESCE(away_goals_conceded_avg, 1.5)) / 2 as avg_defense,
                        (COALESCE(home_win_rate, 40) + COALESCE(away_win_rate, 25)) / 2 as avg_win_rate,
                        GREATEST(COALESCE(home_goals_scored_avg, 1.0), COALESCE(away_goals_scored_avg, 0.8)) as peak_attack,
                        LEAST(COALESCE(home_goals_conceded_avg, 1.2), COALESCE(away_goals_conceded_avg, 1.5)) as peak_defense
                    FROM team_intelligence
                    WHERE team_name ILIKE %s
                    LIMIT 1
                """, (f"%{team_name}%",))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                # Extraction des valeurs
                attack_home = float(row['attack_home'])
                attack_away = float(row['attack_away'])
                defense_home = float(row['defense_home'])
                defense_away = float(row['defense_away'])
                home_win_rate = float(row['home_win_rate'])
                away_win_rate = float(row['away_win_rate'])
                avg_attack = float(row['avg_attack'])
                avg_defense = float(row['avg_defense'])
                avg_win_rate = float(row['avg_win_rate'])
                peak_attack = float(row['peak_attack'])
                peak_defense = float(row['peak_defense'])
                
                # ═══════════════════════════════════════════════════════════════
                # CALCULS SMART
                # ═══════════════════════════════════════════════════════════════
                
                # Offensive Threat (0-100)
                # Basé sur: peak_attack + avg_attack + win_rate
                # Une équipe qui marque 2+ buts/match est très dangereuse
                offensive_threat = min(100, (
                    (peak_attack * 25) +           # Max 50 points si 2 buts/match
                    (avg_attack * 20) +            # Max 40 points si 2 buts/match
                    (avg_win_rate * 0.3)           # Max 30 points si 100% win rate
                ))
                
                # Defensive Solidity (0-100)
                # Moins on encaisse = plus c'est solide
                # peak_defense = minimum de buts encaissés (meilleur scénario)
                defensive_solidity = max(0, min(100, (
                    100 - (peak_defense * 30) -    # Pénalité pour buts encaissés
                    (avg_defense * 20)
                )))
                
                # Quality Score (0-100)
                # Combinaison pondérée de toutes les métriques
                quality_score = (
                    offensive_threat * 0.35 +
                    defensive_solidity * 0.35 +
                    avg_win_rate * 0.30
                )
                
                # Danger Index (0-100)
                # Mesure le danger que représente cette équipe pour ses adversaires
                # Basé sur la capacité à marquer ET à ne pas encaisser
                danger_index = (
                    (peak_attack * 20) +           # Capacité à exploser le score
                    (avg_attack * 15) +            # Régularité offensive
                    (avg_win_rate * 0.4) +         # Capacité à gagner
                    ((100 - avg_defense * 25) * 0.25)  # Ne pas se faire contrer
                )
                danger_index = min(100, max(0, danger_index))
                
                return SmartTeamProfile(
                    team_name=row['team_name'],
                    attack_home=attack_home,
                    attack_away=attack_away,
                    defense_home=defense_home,
                    defense_away=defense_away,
                    home_win_rate=home_win_rate,
                    away_win_rate=away_win_rate,
                    home_draw_rate=float(row['home_draw_rate']),
                    current_style=row['current_style'],
                    avg_attack=round(avg_attack, 2),
                    avg_defense=round(avg_defense, 2),
                    avg_win_rate=round(avg_win_rate, 1),
                    peak_attack=round(peak_attack, 2),
                    peak_defense=round(peak_defense, 2),
                    offensive_threat=round(offensive_threat, 1),
                    defensive_solidity=round(defensive_solidity, 1),
                    quality_score=round(quality_score, 1),
                    danger_index=round(danger_index, 1)
                )
                
        except Exception as e:
            logger.error(f"Error getting smart profile: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SMART MISMATCH DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_smart_mismatch(
        self, 
        home: SmartTeamProfile, 
        away: SmartTeamProfile
    ) -> List[TacticalAlert]:
        """
        Détection SMART des mismatches utilisant les profils complets
        """
        alerts = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 1: Danger Index Gap
        # Si l'adversaire a un danger_index bien supérieur
        # ═══════════════════════════════════════════════════════════════════════
        danger_gap = away.danger_index - home.danger_index
        
        if danger_gap > 25:
            alerts.append(TacticalAlert(
                alert_type="DANGER_INDEX_GAP",
                risk_level=RiskLevel.REJECT,
                message=f"🚫 ÉCART DE DANGER CRITIQUE: {away.team_name} ({away.danger_index}) >> {home.team_name} ({home.danger_index})",
                penalty_score=-50,
                details={
                    "home_danger": home.danger_index,
                    "away_danger": away.danger_index,
                    "gap": round(danger_gap, 1),
                    "analysis": "L'adversaire est significativement plus dangereux"
                }
            ))
        elif danger_gap > 15:
            alerts.append(TacticalAlert(
                alert_type="DANGER_INDEX_HIGH",
                risk_level=RiskLevel.DANGER,
                message=f"⚠️ Écart de danger important: {away.team_name} ({away.danger_index}) > {home.team_name} ({home.danger_index})",
                penalty_score=-30,
                details={"gap": round(danger_gap, 1)}
            ))
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 2: Peak Attack vs Defense Vulnerability
        # L'attaque PEAK de l'adversaire vs la défense du home
        # ═══════════════════════════════════════════════════════════════════════
        # Si l'adversaire peut marquer 1.5+ buts ET le home encaisse 1.5+ buts
        if away.peak_attack >= 1.5 and home.defense_home >= 1.2:
            vulnerability_score = away.peak_attack * home.defense_home
            
            if vulnerability_score > 2.5:
                alerts.append(TacticalAlert(
                    alert_type="ATTACK_VULNERABILITY",
                    risk_level=RiskLevel.DANGER,
                    message=f"💥 VULNÉRABILITÉ: {away.team_name} (peak {away.peak_attack} buts) vs {home.team_name} (encaisse {home.defense_home}/match)",
                    penalty_score=-35,
                    details={
                        "away_peak_attack": away.peak_attack,
                        "home_defense": home.defense_home,
                        "vulnerability_score": round(vulnerability_score, 2),
                        "risk": "Risque élevé de score fleuve"
                    }
                ))
            elif vulnerability_score > 1.8:
                alerts.append(TacticalAlert(
                    alert_type="ATTACK_CONCERN",
                    risk_level=RiskLevel.CAUTION,
                    message=f"⚠️ {away.team_name} peut faire mal (peak {away.peak_attack})",
                    penalty_score=-15,
                    details={"vulnerability_score": round(vulnerability_score, 2)}
                ))
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 3: Quality Score Gap
        # ═══════════════════════════════════════════════════════════════════════
        quality_gap = away.quality_score - home.quality_score
        
        if quality_gap > 20:
            alerts.append(TacticalAlert(
                alert_type="QUALITY_GAP_HIGH",
                risk_level=RiskLevel.DANGER,
                message=f"📊 Écart qualité: {away.team_name} ({away.quality_score}) > {home.team_name} ({home.quality_score})",
                penalty_score=-25,
                details={
                    "home_quality": home.quality_score,
                    "away_quality": away.quality_score,
                    "gap": round(quality_gap, 1)
                }
            ))
        elif quality_gap > 10:
            alerts.append(TacticalAlert(
                alert_type="QUALITY_GAP_MODERATE",
                risk_level=RiskLevel.CAUTION,
                message=f"📈 Avantage qualité pour {away.team_name}",
                penalty_score=-10,
                details={"gap": round(quality_gap, 1)}
            ))
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 4: Win Rate Inversion
        # Si l'adversaire gagne plus souvent que le home ne gagne chez lui
        # ═══════════════════════════════════════════════════════════════════════
        if away.avg_win_rate > home.home_win_rate:
            alerts.append(TacticalAlert(
                alert_type="WIN_RATE_INVERSION",
                risk_level=RiskLevel.CAUTION,
                message=f"🔄 {away.team_name} gagne plus souvent ({away.avg_win_rate}%) que {home.team_name} à domicile ({home.home_win_rate}%)",
                penalty_score=-20,
                details={
                    "away_avg_win": away.avg_win_rate,
                    "home_win_rate": home.home_win_rate
                }
            ))
        
        # ═══════════════════════════════════════════════════════════════════════
        # CHECK 5: Offensive Threat Mismatch
        # ═══════════════════════════════════════════════════════════════════════
        threat_gap = away.offensive_threat - home.offensive_threat
        
        if threat_gap > 20:
            alerts.append(TacticalAlert(
                alert_type="OFFENSIVE_THREAT_GAP",
                risk_level=RiskLevel.DANGER,
                message=f"🔥 Menace offensive: {away.team_name} ({away.offensive_threat}) >> {home.team_name} ({home.offensive_threat})",
                penalty_score=-25,
                details={
                    "away_threat": away.offensive_threat,
                    "home_threat": home.offensive_threat,
                    "gap": round(threat_gap, 1)
                }
            ))
        
        return alerts
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HOME UNDERDOG TRAP DETECTOR
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_home_trap(
        self, 
        home: SmartTeamProfile, 
        away: SmartTeamProfile,
        market_type: str
    ) -> Optional[TacticalAlert]:
        """
        Détecte le piège du home underdog (cas Everton)
        """
        if market_type not in ['dc_1x', '1x', 'home', 'draw', 'dc_12']:
            return None
        
        trap_signals = []
        
        # Signal 1: Home win rate faible
        if home.home_win_rate < 55:
            trap_signals.append(f"Win rate domicile faible: {home.home_win_rate}%")
        
        # Signal 2: Away a un meilleur avg_win_rate que home à domicile
        if away.avg_win_rate > home.home_win_rate:
            trap_signals.append(f"{away.team_name} gagne plus ({away.avg_win_rate}%) que {home.team_name} chez lui ({home.home_win_rate}%)")
        
        # Signal 3: Away a une meilleure attaque peak
        if away.peak_attack > home.peak_attack:
            trap_signals.append(f"{away.team_name} plus explosif (peak {away.peak_attack} vs {home.peak_attack})")
        
        # Signal 4: Home encaisse beaucoup
        if home.defense_home > 1.0:
            trap_signals.append(f"{home.team_name} encaisse {home.defense_home} buts/match à domicile")
        
        # Signal 5: Écart de danger index
        if away.danger_index > home.danger_index + 10:
            trap_signals.append(f"Danger index défavorable: {away.danger_index} vs {home.danger_index}")
        
        # Signal 6: Écart de qualité
        if away.quality_score > home.quality_score + 5:
            trap_signals.append(f"Qualité supérieure: {away.quality_score} vs {home.quality_score}")
        
        # Évaluation
        if len(trap_signals) >= 4:
            return TacticalAlert(
                alert_type="HOME_UNDERDOG_TRAP",
                risk_level=RiskLevel.REJECT,
                message=f"🪤 PIÈGE CRITIQUE: {home.team_name} cumule {len(trap_signals)} signaux négatifs",
                penalty_score=-60,
                details={
                    "signals": trap_signals,
                    "signal_count": len(trap_signals),
                    "recommendation": "NE PAS PARIER sur 1X/Home - Trop de signaux négatifs"
                }
            )
        elif len(trap_signals) >= 3:
            return TacticalAlert(
                alert_type="HOME_UNDERDOG_DANGER",
                risk_level=RiskLevel.DANGER,
                message=f"⚠️ {home.team_name}: {len(trap_signals)} signaux d'alerte",
                penalty_score=-35,
                details={"signals": trap_signals}
            )
        elif len(trap_signals) >= 2:
            return TacticalAlert(
                alert_type="HOME_UNDERDOG_CAUTION",
                risk_level=RiskLevel.CAUTION,
                message=f"📊 {home.team_name}: signaux mixtes",
                penalty_score=-15,
                details={"signals": trap_signals}
            )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FULL SMART ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def full_smart_analysis(
        self, 
        home_team: str, 
        away_team: str, 
        market_type: str
    ) -> Dict:
        """
        Analyse SMART complète d'un match
        """
        # Récupérer les profils SMART
        home = self.get_smart_profile(home_team)
        away = self.get_smart_profile(away_team)
        
        if not home:
            return {"error": f"Équipe non trouvée: {home_team}", "verdict": "❓ UNKNOWN"}
        if not away:
            return {"error": f"Équipe non trouvée: {away_team}", "verdict": "❓ UNKNOWN"}
        

        # ═══════════════════════════════════════════════════════════════
        # 🧠 COACH INTELLIGENCE ENRICHMENT
        # ═══════════════════════════════════════════════════════════════
        coach_data = {"enabled": False}
        if COACH_INTELLIGENCE_ENABLED:
            try:
                coach_calc = CoachImpactCalculator()
                home_coach = coach_calc.get_coach_factors(home_team)
                away_coach = coach_calc.get_coach_factors(away_team)
                h_style = home_coach.get("style", "unknown")
                a_style = away_coach.get("style", "unknown")
                matchup = "BALANCED"
                boost = {}
                if "offensive" in h_style and "offensive" in a_style:
                    matchup = "OPEN_GAME"
                    boost = {"over_25": 15, "btts_yes": 10}
                elif "defensive" in h_style and "defensive" in a_style:
                    matchup = "CLOSED_GAME"
                    boost = {"under_25": 15, "draw": 10}
                elif "offensive" in h_style and "defensive" in a_style:
                    matchup = "HOME_PUSH"
                    boost = {"home_win": 5}
                elif "defensive" in h_style and "offensive" in a_style:
                    matchup = "COUNTER_RISK"
                    boost = {"away_win": 5}
                coach_data = {
                    "enabled": True,
                    "home": {"coach": home_coach.get("coach"), "style": h_style, "att": round(home_coach.get("att", 1.0), 2)},
                    "away": {"coach": away_coach.get("coach"), "style": a_style, "att": round(away_coach.get("att", 1.0), 2)},
                    "matchup": matchup,
                    "boost": boost
                }
                logger.info("coach_intel", home=home_team, away=away_team, matchup=matchup)
            except Exception as e:
                logger.debug("coach_error", error=str(e))

        all_alerts = []
        total_penalty = 0
        
        # Détection des mismatches
        mismatch_alerts = self.detect_smart_mismatch(home, away)
        all_alerts.extend(mismatch_alerts)
        
        # Détection du piège home underdog
        trap = self.detect_home_trap(home, away, market_type)
        if trap:
            all_alerts.append(trap)
        
        # Calcul du penalty total
        for alert in all_alerts:
            total_penalty += alert.penalty_score
        
        # Verdict final
        reject_count = sum(1 for a in all_alerts if a.risk_level == RiskLevel.REJECT)
        danger_count = sum(1 for a in all_alerts if a.risk_level == RiskLevel.DANGER)
        
        if reject_count > 0:
            verdict = "🚫 REJECT"
            recommendation = "NE PAS PARIER - Signaux critiques détectés"
            confidence = 0
        elif danger_count >= 2:
            verdict = "🚫 REJECT"
            recommendation = "NE PAS PARIER - Cumul de signaux dangereux"
            confidence = 10
        elif danger_count == 1:
            verdict = "⚠️ DANGER"
            recommendation = "Réduire la mise de 75%"
            confidence = 25
        elif all_alerts:
            verdict = "⚠️ CAUTION"
            recommendation = "Réduire la mise de 50%"
            confidence = 50
        else:
            verdict = "✅ VALID"
            recommendation = "Pari validé par l'analyse SMART"
            confidence = 80
        
        return {
            "match": f"{home_team} vs {away_team}",
            "market": market_type,
            "verdict": verdict,
            "recommendation": recommendation,
            "confidence": confidence,
            "total_penalty": total_penalty,
            "alerts_count": len(all_alerts),
            "coach_intelligence": coach_data,
            "home_profile": {
                "team": home.team_name,
                "quality_score": home.quality_score,
                "danger_index": home.danger_index,
                "offensive_threat": home.offensive_threat,
                "defensive_solidity": home.defensive_solidity,
                "peak_attack": home.peak_attack,
                "defense_home": home.defense_home,
                "home_win_rate": home.home_win_rate,
                "avg_win_rate": home.avg_win_rate,
                "style": home.current_style
            },
            "away_profile": {
                "team": away.team_name,
                "quality_score": away.quality_score,
                "danger_index": away.danger_index,
                "offensive_threat": away.offensive_threat,
                "defensive_solidity": away.defensive_solidity,
                "peak_attack": away.peak_attack,
                "avg_attack": away.avg_attack,
                "avg_win_rate": away.avg_win_rate,
                "style": away.current_style
            },
            "alerts": [
                {
                    "type": a.alert_type,
                    "level": a.risk_level.value,
                    "message": a.message,
                    "penalty": a.penalty_score,
                    "details": a.details
                }
                for a in all_alerts
            ]
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION EVERTON vs NEWCASTLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def simulate_everton_newcastle(self) -> Dict:
        """Test: DOIT retourner REJECT ou DANGER"""
        return self.full_smart_analysis("Everton", "Newcastle United", "dc_1x")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BATCH ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_upcoming_matches(self, market_filter: str = None) -> List[Dict]:
        """Analyse tous les matchs à venir"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT DISTINCT home_team, away_team, market_type, diamond_score, commence_time
                    FROM tracking_clv_picks
                    WHERE commence_time > NOW()
                    AND commence_time < NOW() + INTERVAL '48 hours'
                    AND diamond_score >= 80
                """
                if market_filter:
                    query += f" AND market_type = '{market_filter}'"
                query += " ORDER BY diamond_score DESC LIMIT 50"
                
                cur.execute(query)
                picks = cur.fetchall()
                
                results = []
                for pick in picks:
                    analysis = self.full_smart_analysis(
                        pick['home_team'],
                        pick['away_team'],
                        pick['market_type']
                    )
                    
                    if 'error' not in analysis:
                        analysis['original_score'] = pick['diamond_score']
                        analysis['adjusted_score'] = max(0, pick['diamond_score'] + analysis['total_penalty'])
                        analysis['commence_time'] = pick['commence_time'].isoformat() if pick['commence_time'] else None
                        results.append(analysis)
                
                # Trier par score ajusté
                results.sort(key=lambda x: x.get('adjusted_score', 0), reverse=True)
                return results
                
        except Exception as e:
            logger.error(f"Error analyzing matches: {e}")
            return []


# Instance globale
dynamic_intel = DynamicIntelligenceService()

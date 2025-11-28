#!/usr/bin/env python3
"""
🏎️ FERRARI COMBO INTEGRATION
=============================
Enrichit les combinés avec l'intelligence FERRARI

Fonctionnalités:
- Analyse chaque leg pour détecter les pièges
- Calcule un score de risque global
- Génère des alertes visuelles
- Recommande des alternatives
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}


class RiskLevel(Enum):
    """Niveaux de risque FERRARI"""
    SAFE = "🟢 SAFE"
    CAUTION = "🟡 CAUTION"
    RISKY = "🟠 RISKY"
    TRAP = "🔴 TRAP"
    DANGER = "💀 DANGER"


@dataclass
class LegAnalysis:
    """Analyse d'un leg du combo"""
    home_team: str
    away_team: str
    market: str
    original_score: int
    
    # FERRARI enrichment
    ferrari_score: int
    traps_detected: List[str]
    alerts: List[Dict]
    risk_level: str
    confidence_penalty: int
    
    # Recommandations
    should_avoid: bool
    alternative_market: Optional[str]
    alternative_reason: Optional[str]


@dataclass
class ComboAnalysis:
    """Analyse complète d'un combo"""
    combo_id: int
    num_legs: int
    
    # Scores
    original_total_score: int
    ferrari_total_score: int
    risk_penalty: int
    
    # Risques
    total_traps: int
    risk_level: str
    legs_at_risk: int
    
    # Détails
    legs_analysis: List[Dict]
    global_alerts: List[str]
    
    # Verdict
    recommendation: str
    should_bet: bool
    suggested_stake_modifier: float


class FerrariComboIntegration:
    """Service d'intégration FERRARI pour les combos"""
    
    def __init__(self):
        self.conn = None
        
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe pour matching"""
        if not name:
            return ""
        # Enlever suffixes courants
        suffixes = [' FC', ' CF', ' SC', ' AC', ' AS', ' SL', ' SK']
        result = name.strip()
        for suffix in suffixes:
            if result.endswith(suffix):
                result = result[:-len(suffix)]
        return result.strip()
    
    def _get_team_intelligence(self, team_name: str) -> Optional[Dict]:
        """Récupère l'intelligence FERRARI pour une équipe"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        normalized = self._normalize_team_name(team_name)
        
        try:
            # Recherche exacte d'abord
            cur.execute("""
                SELECT * FROM team_intelligence 
                WHERE team_name ILIKE %s 
                   OR team_name ILIKE %s
                LIMIT 1
            """, (team_name, f"%{normalized}%"))
            
            result = cur.fetchone()
            
            if not result:
                # Recherche via mapping
                cur.execute("""
                    SELECT ti.* FROM team_intelligence ti
                    JOIN team_name_mapping tnm ON ti.team_name = tnm.canonical_name
                    WHERE tnm.source_name ILIKE %s
                    LIMIT 1
                """, (f"%{normalized}%",))
                result = cur.fetchone()
            
            return dict(result) if result else None
            
        finally:
            cur.close()
    
    def _get_market_alert(self, team_data: Dict, market: str, is_home: bool) -> Dict:
        """Récupère l'alerte pour un marché spécifique"""
        
        if not team_data:
            return {"level": "UNKNOWN", "message": "Équipe non trouvée"}
        
        alerts = team_data.get('market_alerts', {})
        if isinstance(alerts, str):
            try:
                alerts = json.loads(alerts)
            except:
                alerts = {}
        
        # Mapper le marché
        market_mapping = {
            'home': 'home_win' if is_home else 'away_win',
            'away': 'away_win' if is_home else 'home_win',
            'draw': 'draw',
            '1x2_home': 'home_win',
            '1x2_away': 'away_win',
            '1x2_draw': 'draw',
            'btts_yes': 'btts_yes',
            'btts_no': 'btts_no',
            'btts': 'btts_yes',
            'over_25': 'over_25',
            'under_25': 'under_25',
            'over': 'over_25',
            'under': 'under_25',
            'dc_1x': 'double_chance_1x',
            'dc_x2': 'double_chance_x2',
            'dc_12': 'double_chance_12',
        }
        
        mapped_market = market_mapping.get(market.lower(), market.lower())
        alert = alerts.get(mapped_market, {})
        
        return {
            "level": alert.get("level", "NEUTRAL"),
            "message": alert.get("message", ""),
            "stat": alert.get("stat"),
            "is_trap": alert.get("level") == "TRAP"
        }
    
    def analyze_leg(self, home_team: str, away_team: str, market: str, 
                    original_score: int = 50) -> LegAnalysis:
        """Analyse un leg individuel du combo"""
        
        # Récupérer intelligence des deux équipes
        home_intel = self._get_team_intelligence(home_team)
        away_intel = self._get_team_intelligence(away_team)
        
        traps = []
        alerts = []
        confidence_penalty = 0
        
        # Analyser le marché pour l'équipe concernée
        if market.lower() in ['home', '1x2_home', 'dc_1x', 'dc_12']:
            # Paris sur domicile - analyser home team
            if home_intel:
                alert = self._get_market_alert(home_intel, market, is_home=True)
                if alert.get('is_trap'):
                    traps.append(f"{home_team}: {alert.get('message', 'TRAP')}")
                    confidence_penalty -= 25
                alerts.append({
                    "team": home_team,
                    "type": "home",
                    **alert
                })
                
        elif market.lower() in ['away', '1x2_away', 'dc_x2']:
            # Paris sur extérieur - analyser away team
            if away_intel:
                alert = self._get_market_alert(away_intel, market, is_home=False)
                if alert.get('is_trap'):
                    traps.append(f"{away_team}: {alert.get('message', 'TRAP')}")
                    confidence_penalty -= 25
                alerts.append({
                    "team": away_team,
                    "type": "away",
                    **alert
                })
                
        elif market.lower() in ['btts', 'btts_yes', 'btts_no']:
            # BTTS - analyser les deux équipes
            for team, intel, is_home in [(home_team, home_intel, True), 
                                          (away_team, away_intel, False)]:
                if intel:
                    alert = self._get_market_alert(intel, market, is_home)
                    if alert.get('is_trap'):
                        traps.append(f"{team}: {alert.get('message', 'TRAP')}")
                        confidence_penalty -= 15
                    alerts.append({
                        "team": team,
                        "type": "home" if is_home else "away",
                        **alert
                    })
                    
        elif market.lower() in ['over', 'over_25', 'under', 'under_25']:
            # Over/Under - analyser les deux équipes
            for team, intel, is_home in [(home_team, home_intel, True), 
                                          (away_team, away_intel, False)]:
                if intel:
                    alert = self._get_market_alert(intel, market, is_home)
                    if alert.get('is_trap'):
                        traps.append(f"{team}: {alert.get('message', 'TRAP')}")
                        confidence_penalty -= 15
                    alerts.append({
                        "team": team,
                        "type": "home" if is_home else "away",
                        **alert
                    })
        
        # Calculer score ajusté
        ferrari_score = max(0, min(100, original_score + confidence_penalty))
        
        # Déterminer le niveau de risque
        if len(traps) >= 2:
            risk_level = RiskLevel.DANGER.value
        elif len(traps) == 1:
            risk_level = RiskLevel.TRAP.value
        elif confidence_penalty < -10:
            risk_level = RiskLevel.RISKY.value
        elif confidence_penalty < 0:
            risk_level = RiskLevel.CAUTION.value
        else:
            risk_level = RiskLevel.SAFE.value
        
        # Recommandation alternative
        should_avoid = len(traps) > 0
        alternative_market = None
        alternative_reason = None
        
        if should_avoid:
            # Suggérer une alternative
            if market.lower() in ['btts_no'] and home_intel:
                btts_rate = home_intel.get('btts_rate', 50)
                if btts_rate > 55:
                    alternative_market = "btts_yes"
                    alternative_reason = f"BTTS rate élevé ({btts_rate}%)"
            elif market.lower() in ['under_25', 'under']:
                alternative_market = "over_25"
                alternative_reason = "Équipes offensives détectées"
        
        return LegAnalysis(
            home_team=home_team,
            away_team=away_team,
            market=market,
            original_score=original_score,
            ferrari_score=ferrari_score,
            traps_detected=traps,
            alerts=alerts,
            risk_level=risk_level,
            confidence_penalty=confidence_penalty,
            should_avoid=should_avoid,
            alternative_market=alternative_market,
            alternative_reason=alternative_reason
        )
    
    def analyze_combo(self, combo_id: int) -> Optional[ComboAnalysis]:
        """Analyse complète d'un combo avec FERRARI"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Récupérer le combo
            cur.execute("""
                SELECT * FROM fg_combo_tracking WHERE id = %s
            """, (combo_id,))
            
            combo = cur.fetchone()
            if not combo:
                return None
            
            selections = combo.get('selections', {})
            if isinstance(selections, str):
                selections = json.loads(selections)
            
            # Supporter les deux formats de selections
            if isinstance(selections, list):
                # Format array: [{match, market, odds, score}, ...]
                picks = selections
                if picks and picks[0].get('match'):
                    # Extraire home/away du match "Team A vs Team B"
                    match_str = picks[0].get('match', 'Unknown vs Unknown')
                    parts = match_str.split(' vs ')
                    home_team = parts[0].strip() if len(parts) >= 1 else 'Unknown'
                    away_team = parts[1].strip() if len(parts) >= 2 else 'Unknown'
                else:
                    home_team = 'Unknown'
                    away_team = 'Unknown'
            else:
                # Format object: {match, picks, home_team, away_team}
                home_team = selections.get('home_team', '')
                away_team = selections.get('away_team', '')
                picks = selections.get('picks', [])
            
            if not picks:
                return None
            
            # Analyser chaque leg
            legs_analysis = []
            total_original_score = 0
            total_ferrari_score = 0
            total_traps = 0
            legs_at_risk = 0
            global_alerts = []
            
            for pick in picks:
                market = pick.get('market', '')
                original_score = pick.get('score', 50)
                
                leg = self.analyze_leg(home_team, away_team, market, original_score)
                legs_analysis.append(asdict(leg))
                
                total_original_score += original_score
                total_ferrari_score += leg.ferrari_score
                total_traps += len(leg.traps_detected)
                
                if leg.should_avoid:
                    legs_at_risk += 1
                    global_alerts.extend(leg.traps_detected)
            
            num_legs = len(picks)
            avg_original = total_original_score // num_legs if num_legs > 0 else 0
            avg_ferrari = total_ferrari_score // num_legs if num_legs > 0 else 0
            risk_penalty = avg_original - avg_ferrari
            
            # Niveau de risque global
            if total_traps >= 3 or legs_at_risk >= 2:
                risk_level = RiskLevel.DANGER.value
                should_bet = False
                recommendation = "❌ ÉVITER - Trop de pièges détectés"
                stake_modifier = 0.0
            elif total_traps >= 2:
                risk_level = RiskLevel.TRAP.value
                should_bet = False
                recommendation = "🚨 TRAP - Plusieurs alertes détectées"
                stake_modifier = 0.25
            elif total_traps >= 1:
                risk_level = RiskLevel.RISKY.value
                should_bet = True
                recommendation = "⚠️ PRUDENCE - 1 piège détecté, réduire stake"
                stake_modifier = 0.5
            elif legs_at_risk > 0:
                risk_level = RiskLevel.CAUTION.value
                should_bet = True
                recommendation = "🟡 ATTENTION - Legs à risque identifiés"
                stake_modifier = 0.75
            else:
                risk_level = RiskLevel.SAFE.value
                should_bet = True
                recommendation = "✅ SAFE - Aucun piège FERRARI détecté"
                stake_modifier = 1.0
            
            return ComboAnalysis(
                combo_id=combo_id,
                num_legs=num_legs,
                original_total_score=avg_original,
                ferrari_total_score=avg_ferrari,
                risk_penalty=risk_penalty,
                total_traps=total_traps,
                risk_level=risk_level,
                legs_at_risk=legs_at_risk,
                legs_analysis=legs_analysis,
                global_alerts=global_alerts,
                recommendation=recommendation,
                should_bet=should_bet,
                suggested_stake_modifier=stake_modifier
            )
            
        finally:
            cur.close()
    
    def analyze_all_pending(self) -> List[Dict]:
        """Analyse tous les combos pending"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT id FROM fg_combo_tracking 
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)
            
            results = []
            for row in cur.fetchall():
                analysis = self.analyze_combo(row['id'])
                if analysis:
                    results.append(asdict(analysis))
            
            return results
            
        finally:
            cur.close()
    
    def get_safe_combos(self) -> List[Dict]:
        """Retourne uniquement les combos SAFE"""
        all_analyses = self.analyze_all_pending()
        return [a for a in all_analyses if a.get('should_bet', False) 
                and a.get('total_traps', 0) == 0]
    
    def get_risky_combos(self) -> List[Dict]:
        """Retourne les combos avec des pièges"""
        all_analyses = self.analyze_all_pending()
        return [a for a in all_analyses if a.get('total_traps', 0) > 0]


# Singleton
_ferrari_combo = None

def get_ferrari_combo_service() -> FerrariComboIntegration:
    global _ferrari_combo
    if _ferrari_combo is None:
        _ferrari_combo = FerrariComboIntegration()
    return _ferrari_combo


if __name__ == "__main__":
    # Test
    service = get_ferrari_combo_service()
    
    print("🏎️ FERRARI COMBO INTEGRATION - TEST")
    print("=" * 60)
    
    # Tester sur un combo existant
    import sys
    combo_id = int(sys.argv[1]) if len(sys.argv) > 1 else 34
    
    analysis = service.analyze_combo(combo_id)
    if analysis:
        print(f"\n📊 Combo #{analysis.combo_id}")
        print(f"   Legs: {analysis.num_legs}")
        print(f"   Score Original: {analysis.original_total_score}")
        print(f"   Score FERRARI: {analysis.ferrari_total_score}")
        print(f"   Pénalité: -{analysis.risk_penalty}")
        print(f"   Pièges: {analysis.total_traps}")
        print(f"   Risque: {analysis.risk_level}")
        print(f"   Recommandation: {analysis.recommendation}")
        print(f"   Parier: {'✅ OUI' if analysis.should_bet else '❌ NON'}")
        print(f"   Stake modifier: {analysis.suggested_stake_modifier}x")
        
        if analysis.global_alerts:
            print(f"\n   🚨 ALERTES:")
            for alert in analysis.global_alerts:
                print(f"      → {alert}")
    else:
        print(f"❌ Combo #{combo_id} non trouvé")

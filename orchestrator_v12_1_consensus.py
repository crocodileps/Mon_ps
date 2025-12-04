#!/usr/bin/env python3
"""
Orchestrator V12.1 - Consensus Matrix + CLV Tracking
=====================================================
Améliorations par rapport à V12.0:
- ConsensusMatrix: Résolution intelligente des conflits V11 vs Smart Market
- CLV Tracking: Logging automatique pour mesure de performance
- Actions granulaires: MAX_BET, CONFIDENT_BET, VALUE_BET, CAUTIOUS_BET, BAD_PRICE, SKIP
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib

# Import des composants
from orchestrator_v11_4_god_tier import OrchestratorV11_4
from smart_market_selector_v3_final import SmartMarketSelector, Recommendation


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS MATRIX
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusMatrix:
    """
    Matrice de résolution des conflits V11 vs Smart Market
    Inspiré des pratiques Hedge Fund
    """
    
    # Seuils calibrés
    HUGE_EDGE = 0.15        # Edge considéré comme "énorme"
    GOOD_SHARPE = 0.8       # Sharpe considéré comme "bon"
    HIGH_V11_SCORE = 35     # Score V11 considéré comme "élevé"
    
    @staticmethod
    def resolve(v11_action: str, v11_score: float, best_bet: Optional[Recommendation]) -> Tuple[str, float, str]:
        """
        Returns: (action, stake_multiplier, reason)
        
        Actions possibles:
        - MAX_BET: Accord parfait, 100% Kelly
        - CONFIDENT_BET: Bon accord, 75% Kelly
        - VALUE_BET: Désaccord mais edge énorme, 50% Kelly
        - CAUTIOUS_BET: Signal faible, 25% Kelly
        - BAD_PRICE: Bon contexte mais pas de value, 0%
        - SKIP: Pas de signal clair, 0%
        """
        if not best_bet:
            return ("SKIP", 0.0, "Pas de recommandation Smart Market")
        
        edge = best_bet.edge
        sharpe = best_bet.sharpe
        rec = best_bet.recommendation
        divergence = best_bet.market_divergence
        
        # ═══════════════════════════════════════════════════════════════════
        # CAS 1: ACCORD PARFAIT (V11 SNIPER + Smart SNIPER/NORMAL)
        # ═══════════════════════════════════════════════════════════════════
        if v11_action == "SNIPER_BET" and rec in ["SNIPER", "NORMAL"]:
            if not divergence:
                return ("MAX_BET", 1.0, "Accord parfait V11+Smart sans divergence")
            else:
                return ("CONFIDENT_BET", 0.75, "Accord V11+Smart mais divergence Pinnacle")
        
        # ═══════════════════════════════════════════════════════════════════
        # CAS 2: V11 CHAUD + SMART TIÈDE (Possible piège de prix)
        # ═══════════════════════════════════════════════════════════════════
        if v11_action == "SNIPER_BET" and rec == "HIGH_RISK":
            if edge > ConsensusMatrix.HUGE_EDGE:
                return ("CONFIDENT_BET", 0.75, "V11 SNIPER + edge énorme malgré HIGH_RISK")
            elif edge > 0.08:
                return ("CAUTIOUS_BET", 0.25, "V11 SNIPER mais Smart prudent")
            else:
                return ("BAD_PRICE", 0.0, "V11 voit opportunité mais prix inefficient")
        
        # ═══════════════════════════════════════════════════════════════════
        # CAS 3: SMART CHAUD + V11 FROID (Faille de marché potentielle)
        # ═══════════════════════════════════════════════════════════════════
        if v11_action == "SKIP" and rec in ["SNIPER", "NORMAL", "SPECULATIVE"]:
            if divergence:
                return ("SKIP", 0.0, "Smart voit value mais divergence Pinnacle = danger")
            
            if edge > ConsensusMatrix.HUGE_EDGE and sharpe > ConsensusMatrix.GOOD_SHARPE:
                return ("VALUE_BET", 0.5, f"Edge {edge*100:.1f}% trop gros pour ignorer")
            elif edge > ConsensusMatrix.HUGE_EDGE:
                return ("VALUE_BET", 0.5, f"Edge {edge*100:.1f}% énorme malgré V11 SKIP")
            elif edge > 0.10:
                return ("CAUTIOUS_BET", 0.25, "Edge intéressant mais V11 prudent")
            else:
                return ("SKIP", 0.0, "Edge insuffisant face au SKIP de V11")
        
        # ═══════════════════════════════════════════════════════════════════
        # CAS 4: V11 NORMAL + SMART SPECULATIVE
        # ═══════════════════════════════════════════════════════════════════
        if v11_action == "NORMAL_BET" and rec == "SPECULATIVE":
            if v11_score > ConsensusMatrix.HIGH_V11_SCORE and edge > 0.08:
                return ("CAUTIOUS_BET", 0.25, "Signaux tièdes concordants")
            else:
                return ("SKIP", 0.0, "Signaux trop faibles")
        
        # ═══════════════════════════════════════════════════════════════════
        # CAS 5: V11 NORMAL + SMART NORMAL/SNIPER
        # ═══════════════════════════════════════════════════════════════════
        if v11_action == "NORMAL_BET" and rec in ["SNIPER", "NORMAL"]:
            if not divergence:
                return ("CONFIDENT_BET", 0.75, "Bon accord V11 NORMAL + Smart fort")
            else:
                return ("CAUTIOUS_BET", 0.25, "Accord mais divergence Pinnacle")
        
        # ═══════════════════════════════════════════════════════════════════
        # CAS PAR DÉFAUT
        # ═══════════════════════════════════════════════════════════════════
        if rec == "HIGH_RISK" and edge > ConsensusMatrix.HUGE_EDGE and not divergence:
            return ("CAUTIOUS_BET", 0.25, "HIGH_RISK mais edge énorme sans divergence")
        
        return ("SKIP", 0.0, "Pas de consensus clair")


# ═══════════════════════════════════════════════════════════════════════════════
# CLV TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class CLVTracker:
    """Gère le logging des paris pour tracking CLV"""
    
    def __init__(self, conn):
        self.conn = conn
    
    def generate_match_id(self, home: str, away: str, kick_off: datetime = None) -> str:
        """Génère un ID unique pour le match"""
        date_str = kick_off.strftime("%Y%m%d") if kick_off else datetime.now().strftime("%Y%m%d")
        raw = f"{home}_{away}_{date_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
    
    def log_recommendation(self, 
                          home: str, away: str, league: str,
                          market: str, bookmaker: str,
                          odds_detected: float,
                          v11_score: float, v11_action: str,
                          smart_edge: float, smart_sharpe: float,
                          smart_recommendation: str,
                          consensus_action: str, consensus_reason: str,
                          kelly_suggested: float, stake_multiplier: float,
                          market_divergence: bool = False,
                          pinnacle_gap: float = None,
                          kick_off: datetime = None) -> int:
        """Log une recommandation dans bet_tracker_clv"""
        
        match_id = self.generate_match_id(home, away, kick_off)
        
        # Convertir numpy types en Python natifs
        def to_float(v):
            if v is None:
                return None
            return float(v)
        
        odds_detected = to_float(odds_detected)
        v11_score = to_float(v11_score)
        smart_edge = to_float(smart_edge)
        smart_sharpe = to_float(smart_sharpe)
        kelly_suggested = to_float(kelly_suggested)
        stake_multiplier = to_float(stake_multiplier)
        pinnacle_gap = to_float(pinnacle_gap)
        
        cur = self.conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO bet_tracker_clv (
                    match_id, home_team, away_team, league, kick_off,
                    market, bookmaker, odds_detected,
                    v11_score, v11_action,
                    smart_edge, smart_sharpe, smart_recommendation,
                    consensus_action, consensus_reason,
                    kelly_suggested, stake_multiplier,
                    market_divergence, pinnacle_gap
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
                ON CONFLICT (match_id, market, bookmaker) 
                DO UPDATE SET
                    odds_detected = EXCLUDED.odds_detected,
                    v11_score = EXCLUDED.v11_score,
                    consensus_action = EXCLUDED.consensus_action,
                    consensus_reason = EXCLUDED.consensus_reason,
                    created_at = NOW()
                RETURNING id
            """, (
                match_id, home, away, league, kick_off,
                market, bookmaker, odds_detected,
                v11_score, v11_action,
                smart_edge, smart_sharpe, smart_recommendation,
                consensus_action, consensus_reason,
                kelly_suggested, stake_multiplier,
                market_divergence, pinnacle_gap
            ))
            
            self.conn.commit()
            result = cur.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Erreur CLV logging: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V12.1
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestratorV12_1(OrchestratorV11_4):
    """
    Orchestrator V12.1 - Consensus Matrix + CLV Tracking
    
    Hérite de V11.4 (God Tier) et intègre:
    - Smart Market Selector V3 Final
    - ConsensusMatrix pour résolution des conflits
    - CLV Tracker pour mesure de performance
    """
    
    VERSION = "12.1"
    
    def __init__(self):
        super().__init__()
        self.smart_market = SmartMarketSelector()
        self.clv_tracker = CLVTracker(self.smart_market.conn)
        print(f"   🚀 Orchestrator V{self.VERSION} initialisé avec Consensus Matrix + CLV Tracking")
    
    def analyze_match_v12(self, home: str, away: str, league: str, 
                          log_clv: bool = True) -> Dict:
        """
        Analyse complète avec ConsensusMatrix et CLV logging
        """
        timestamp = datetime.now()
        
        # 1. Analyse V11.4
        v11_result = self.analyze_match(home, away)
        
        # 2. Analyse Smart Market
        smart_result = self.smart_market.analyze(home, away, league)
        
        # 3. Consensus Matrix
        recommendations = smart_result.get('recommendations', [])
        
        # Trouver le best bet
        best_bet = self._find_best_bet(recommendations)
        
        # Résoudre le consensus
        v11_action = v11_result.get('action', 'SKIP')
        v11_score = v11_result.get('score', 0)
        
        consensus_action, stake_multiplier, consensus_reason = ConsensusMatrix.resolve(
            v11_action, v11_score, best_bet
        )
        
        # 4. Calculer Kelly ajusté
        kelly_adjusted = 0.0
        if best_bet and stake_multiplier > 0:
            kelly_adjusted = best_bet.kelly * stake_multiplier
        
        # 5. Log CLV si demandé
        clv_id = None
        if log_clv and best_bet and consensus_action not in ["SKIP", "BAD_PRICE"]:
            clv_id = self.clv_tracker.log_recommendation(
                home=home, away=away, league=league,
                market=best_bet.market,
                bookmaker=best_bet.bookmaker,
                odds_detected=best_bet.odds,
                v11_score=v11_score,
                v11_action=v11_action,
                smart_edge=best_bet.edge,
                smart_sharpe=best_bet.sharpe,
                smart_recommendation=best_bet.recommendation,
                consensus_action=consensus_action,
                consensus_reason=consensus_reason,
                kelly_suggested=best_bet.kelly,
                stake_multiplier=stake_multiplier,
                market_divergence=best_bet.market_divergence,
                pinnacle_gap=best_bet.pinnacle_gap
            )
        
        # 6. Construire le résultat
        return {
            'home': home,
            'away': away,
            'league': league,
            'timestamp': timestamp.isoformat(),
            'version': self.VERSION,
            
            'v11_analysis': {
                'score': v11_score,
                'action': v11_action,
                'recommended_market': v11_result.get('recommended_market', 'over_25'),
                'layers': v11_result.get('layers', {})
            },
            
            'smart_market': {
                'home_lambda': smart_result.get('home_lambda', 0),
                'away_lambda': smart_result.get('away_lambda', 0),
                'total_xg': smart_result.get('total_xg', 0),
                'rho': smart_result.get('rho', 0),
                'probabilities': smart_result.get('probabilities', {}),
                'recommendations': recommendations
            },
            
            'consensus': {
                'action': consensus_action,
                'stake_multiplier': stake_multiplier,
                'reason': consensus_reason,
                'kelly_adjusted': kelly_adjusted,
                'best_bet': self._rec_to_dict(best_bet) if best_bet else None
            },
            
            'clv_tracking': {
                'logged': clv_id is not None,
                'clv_id': clv_id
            }
        }
    
    def _find_best_bet(self, recommendations: List) -> Optional[Recommendation]:
        """Trouve le meilleur pari selon la hiérarchie"""
        if not recommendations:
            return None
        
        # Hiérarchie: SNIPER > NORMAL > SPECULATIVE > HIGH_RISK (si edge > 10%)
        for level in ["SNIPER", "NORMAL", "SPECULATIVE"]:
            for rec in recommendations:
                if rec.recommendation == level and not rec.market_divergence:
                    return rec
        
        # HIGH_RISK seulement si edge > 10%
        for rec in recommendations:
            if rec.recommendation == "HIGH_RISK" and rec.edge > 0.10 and not rec.market_divergence:
                return rec
        
        # Sinon premier non-divergent
        for rec in recommendations:
            if not rec.market_divergence:
                return rec
        
        return recommendations[0] if recommendations else None
    
    def _rec_to_dict(self, rec: Recommendation) -> Dict:
        """Convertit une Recommendation en dictionnaire"""
        return {
            'market': rec.market,
            'bookmaker': rec.bookmaker,
            'odds': rec.odds,
            'edge': rec.edge,
            'sharpe': rec.sharpe,
            'kelly': rec.kelly,
            'recommendation': rec.recommendation,
            'market_divergence': rec.market_divergence,
            'pinnacle_gap': rec.pinnacle_gap
        }
    
    def print_analysis(self, home: str, away: str, league: str, log_clv: bool = True):
        """Affiche l'analyse formatée avec ConsensusMatrix"""
        result = self.analyze_match_v12(home, away, league, log_clv)
        
        print("\n" + "═" * 100)
        print(f"   🏆 ORCHESTRATOR V{self.VERSION} - CONSENSUS MATRIX")
        print(f"   ⚽ {home} vs {away} ({league})")
        print("═" * 100)
        
        # V11
        v11 = result['v11_analysis']
        print(f"\n   📊 V11.4 ANALYSIS:")
        print(f"      Score: {v11['score']:.1f}/100 | Action: {v11['action']}")
        
        # Smart Market
        sm = result['smart_market']
        print(f"\n   📈 SMART MARKET:")
        print(f"      λ Home: {sm['home_lambda']:.2f} | λ Away: {sm['away_lambda']:.2f}")
        probs = sm['probabilities']
        if probs:
            print(f"      Over 2.5: {probs.get('over_2.5', 0)*100:.0f}% | Over 3.5: {probs.get('over_3.5', 0)*100:.0f}%")
        
        # Recommendations
        recs = sm['recommendations']
        if recs:
            print(f"\n   🎯 RECOMMENDATIONS ({len(recs)} total):")
            for i, rec in enumerate(recs[:5], 1):
                icon = "🎯" if rec.recommendation == "SNIPER" else "✅" if rec.recommendation == "NORMAL" else "⚡" if rec.recommendation == "SPECULATIVE" else "⚠️"
                print(f"      {i}. {icon} {rec.market} @ {rec.odds:.2f} ({rec.bookmaker})")
                print(f"         Edge: {rec.edge*100:.1f}% | Sharpe: {rec.sharpe:.2f} | {rec.recommendation}")
                if rec.market_divergence:
                    print(f"         ⚠️ DIVERGENCE PINNACLE: {rec.pinnacle_gap*100:+.1f}%")
        
        # CONSENSUS (le plus important!)
        cons = result['consensus']
        print(f"\n   {'═' * 60}")
        print(f"   🎲 CONSENSUS MATRIX:")
        print(f"   {'═' * 60}")
        
        action_icons = {
            "MAX_BET": "🚀",
            "CONFIDENT_BET": "✅",
            "VALUE_BET": "💰",
            "CAUTIOUS_BET": "⚡",
            "BAD_PRICE": "🚫",
            "SKIP": "❌"
        }
        
        icon = action_icons.get(cons['action'], "❓")
        print(f"      {icon} ACTION: {cons['action']}")
        print(f"      📊 Stake Multiplier: {cons['stake_multiplier']*100:.0f}% du Kelly")
        print(f"      💡 Raison: {cons['reason']}")
        
        if cons['best_bet']:
            bb = cons['best_bet']
            print(f"\n      💰 BEST BET: {bb['market']} @ {bb['odds']:.2f}")
            print(f"         Kelly suggéré: {bb['kelly']*100:.2f}%")
            print(f"         Kelly ajusté: {cons['kelly_adjusted']*100:.2f}%")
        
        # CLV
        clv = result['clv_tracking']
        if clv['logged']:
            print(f"\n      📝 CLV Tracking: Logged (ID: {clv['clv_id']})")
        
        print("\n" + "═" * 100)
        
        return result
    
    def close(self):
        """Ferme les connexions"""
        if hasattr(self, 'smart_market'):
            self.smart_market.close()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 100)
    print("   🧪 TEST ORCHESTRATOR V12.1 - CONSENSUS MATRIX + CLV TRACKING")
    print("=" * 100)
    
    orch = OrchestratorV12_1()
    
    # Test 1: Barcelona vs Atlético Madrid
    orch.print_analysis("Barcelona", "Atlético Madrid", "La Liga")
    
    # Test 2: Marseille vs Monaco (le cas d'école)
    orch.print_analysis("Marseille", "Monaco", "Ligue 1")
    
    # Stats CLV
    print("\n" + "=" * 100)
    print("   📊 STATS CLV TRACKER")
    print("=" * 100)
    
    cur = orch.smart_market.conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT consensus_action, COUNT(*) as count 
        FROM bet_tracker_clv 
        GROUP BY consensus_action 
        ORDER BY count DESC
    """)
    
    print("\n   Actions loggées:")
    for row in cur.fetchall():
        print(f"      {row['consensus_action']}: {row['count']}")
    
    orch.close()
    print("\n✅ Test V12.1 terminé!")

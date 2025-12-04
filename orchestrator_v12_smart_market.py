#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
ORCHESTRATOR V12 - SMART MARKET INTEGRATION
═══════════════════════════════════════════════════════════════════════════════════════

HÉRITE DE: V11.4 (God Tier)

NOUVELLE INTÉGRATION:
- Smart Market Selector V3 Final (Dixon-Coles, Sharpe, Monte Carlo, Pinnacle Gap)
- Recommandations multi-marchés avec classification SNIPER/NORMAL/SPECULATIVE/HIGH_RISK
- Détection des divergences marché (Pinnacle Gap > 15%)

PRINCIPE: "Extend, Don't Break"

Auteur: Mon_PS Quant System
Version: 12.0 Smart Market
═══════════════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import de la base V11.4
from orchestrator_v11_4_god_tier import (
    OrchestratorV11_4,
    ScoringConfigV11_4,
    PortfolioManager
)

# Import du Smart Market Selector V3
from smart_market_selector_v3_final import (
    SmartMarketSelector,
    DixonColes,
    MonteCarlo,
    Recommendation
)

from datetime import datetime
from typing import Dict, List, Optional
import json


class OrchestratorV12(OrchestratorV11_4):
    """
    Orchestrator V12 avec intégration Smart Market Selector
    """
    
    def __init__(self):
        super().__init__()
        self.smart_selector = SmartMarketSelector()
        self.version = "12.0"
        print(f"   🚀 Orchestrator V{self.version} initialisé avec Smart Market Selector")
    
    def analyze_match_v12(self, home: str, away: str, league: str = None) -> Dict:
        """
        Analyse complète V12 combinant:
        1. Analyse V11.4 (layers multi-dimensionnels)
        2. Smart Market Selector V3 (recommandations multi-marchés)
        """
        
        # 1. Analyse V11.4 standard
        v11_result = self.analyze_match(home, away, league=league)
        
        # 2. Analyse Smart Market Selector
        smart_result = self.smart_selector.analyze(home, away, league)
        
        # 3. Combiner les résultats
        combined = {
            'home': home,
            'away': away,
            'league': league or smart_result.get('league', 'Unknown'),
            'timestamp': datetime.now().isoformat(),
            'version': self.version,
            
            # Résultats V11.4
            'v11_analysis': {
                'final_score': v11_result.get('score', 0),
                'confidence': v11_result.get('action', 'SKIP'),
                'layers': v11_result.get('layers', {}),
                'recommended_market': v11_result.get('recommended_market', 'over_25'),
            },
            
            # Résultats Smart Market Selector
            'smart_market': {
                'home_lambda': smart_result.get('home_lambda', 0),
                'away_lambda': smart_result.get('away_lambda', 0),
                'total_xg': smart_result.get('total_xg', 0),
                'rho': smart_result.get('rho', -0.13),
                'probabilities': smart_result.get('probabilities', {}),
                'recommendations': [self._rec_to_dict(r) for r in smart_result.get('recommendations', [])],
            },
            
            # Synthèse finale
            'synthesis': self._synthesize(v11_result, smart_result)
        }
        
        return combined
    
    def _rec_to_dict(self, rec: Recommendation) -> Dict:
        """Convertit une Recommendation en dictionnaire"""
        return {
            'market': rec.market,
            'line': rec.line,
            'team': rec.team,
            'odds': rec.odds,
            'bookmaker': rec.bookmaker,
            'model_prob': rec.model_prob,
            'edge': rec.edge,
            'sharpe': rec.sharpe,
            'prob_profit': rec.prob_profit,
            'recommendation': rec.recommendation,
            'kelly': rec.kelly,
            'pinnacle_odds': rec.pinnacle_odds,
            'pinnacle_gap': rec.pinnacle_gap,
            'market_divergence': rec.market_divergence,
        }
    
    def _synthesize(self, v11_result: Dict, smart_result: Dict) -> Dict:
        """
        Synthèse intelligente des deux analyses
        Combine V11 (layers multi-dimensionnels) + Smart Market (edges quantitatifs)
        """
        recommendations = smart_result.get('recommendations', [])
        
        # Compter par type
        sniper = [r for r in recommendations if r.recommendation == 'SNIPER']
        normal = [r for r in recommendations if r.recommendation == 'NORMAL']
        speculative = [r for r in recommendations if r.recommendation == 'SPECULATIVE']
        high_risk = [r for r in recommendations if r.recommendation == 'HIGH_RISK']
        
        # Divergences marché
        divergences = [r for r in recommendations if r.market_divergence]
        
        # Best bet (premier SNIPER ou NORMAL, sinon SPECULATIVE, sinon HIGH_RISK avec bon edge)
        best_bet = None
        if sniper:
            best_bet = sniper[0]
        elif normal:
            best_bet = normal[0]
        elif speculative and not speculative[0].market_divergence:
            best_bet = speculative[0]
        elif high_risk and high_risk[0].edge > 0.10 and not high_risk[0].market_divergence:
            # HIGH_RISK avec edge > 10% et pas de divergence
            best_bet = high_risk[0]
        
        # Récupérer les infos V11
        v11_score = v11_result.get('score', 0)
        v11_action = v11_result.get('action', 'SKIP')
        
        # Confidence finale - COMBINE V11 + Smart Market
        if best_bet:
            if best_bet.recommendation in ['SNIPER', 'NORMAL']:
                # Smart Market fort
                if v11_action == 'SNIPER_BET':
                    final_confidence = 'VERY_HIGH'
                elif v11_action == 'NORMAL_BET' or v11_score >= 30:
                    final_confidence = 'HIGH'
                else:
                    final_confidence = 'MEDIUM'
            elif best_bet.recommendation == 'SPECULATIVE':
                # Smart Market moyen
                if v11_action == 'SNIPER_BET':
                    final_confidence = 'HIGH'
                elif v11_action == 'NORMAL_BET' or v11_score >= 30:
                    final_confidence = 'MEDIUM'
                else:
                    final_confidence = 'LOW'
            else:
                # HIGH_RISK seulement
                if v11_action == 'SNIPER_BET' and best_bet.edge > 0.10:
                    final_confidence = 'MEDIUM'
                elif v11_score >= 30 and best_bet.edge > 0.10:
                    final_confidence = 'LOW'
                else:
                    final_confidence = 'SKIP'
        else:
            # Pas de best_bet Smart Market
            if v11_action == 'SNIPER_BET':
                final_confidence = 'V11_ONLY'  # V11 recommande mais pas de cote value
            else:
                final_confidence = 'SKIP'
        
        return {
            'best_bet': self._rec_to_dict(best_bet) if best_bet else None,
            'counts': {
                'sniper': len(sniper),
                'normal': len(normal),
                'speculative': len(speculative),
                'high_risk': len(high_risk),
                'total': len(recommendations),
            },
            'warnings': {
                'market_divergences': len(divergences),
                'divergent_markets': [r.market for r in divergences],
            },
            'final_confidence': final_confidence,
            'v11_score': v11_score,
        }
    
    def get_top_recommendations(self, home: str, away: str, league: str = None, top_n: int = 5) -> List[Dict]:
        """
        Retourne les top N recommandations pour un match
        """
        smart_result = self.smart_selector.analyze(home, away, league)
        recommendations = smart_result.get('recommendations', [])[:top_n]
        return [self._rec_to_dict(r) for r in recommendations]
    
    def print_analysis(self, home: str, away: str, league: str = None):
        """
        Affiche une analyse complète formatée
        """
        result = self.analyze_match_v12(home, away, league)
        
        print("\n" + "═" * 100)
        print(f"   🏆 ORCHESTRATOR V12 - ANALYSE COMPLÈTE")
        print(f"   ⚽ {home} vs {away} ({result['league']})")
        print("═" * 100)
        
        # Section V11.4
        v11 = result['v11_analysis']
        print(f"\n   📊 ANALYSE V11.4:")
        print(f"      Score: {v11['final_score']:.1f}/100 | Confidence: {v11['confidence']}")
        print(f"      Marché recommandé: {v11['recommended_market']}")
        
        # Section Smart Market
        sm = result['smart_market']
        print(f"\n   📈 SMART MARKET SELECTOR:")
        print(f"      λ Home: {sm['home_lambda']:.2f} | λ Away: {sm['away_lambda']:.2f} | Total xG: {sm['total_xg']:.2f}")
        
        probs = sm['probabilities']
        if probs:
            print(f"      1X2: {probs.get('home', 0)*100:.0f}% | {probs.get('draw', 0)*100:.0f}% | {probs.get('away', 0)*100:.0f}%")
            print(f"      Over 2.5: {probs.get('over_2.5', 0)*100:.0f}% | Over 3.5: {probs.get('over_3.5', 0)*100:.0f}%")
        
        # Recommandations
        recs = sm['recommendations']
        if recs:
            print(f"\n   🎯 TOP RECOMMANDATIONS ({len(recs)} total):")
            for i, rec in enumerate(recs[:5], 1):
                emoji = "🎯" if rec['recommendation'] == 'SNIPER' else "✅" if rec['recommendation'] == 'NORMAL' else "⚡" if rec['recommendation'] == 'SPECULATIVE' else "⚠️"
                print(f"\n      {i}. {emoji} {rec['market']} @ {rec['odds']:.2f} ({rec['bookmaker']})")
                print(f"         Edge: {rec['edge']*100:.1f}% | Sharpe: {rec['sharpe']:.2f} | Kelly: {rec['kelly']*100:.1f}%")
                if rec['market_divergence']:
                    print(f"         ⚠️ MARKET DIVERGENCE: Écart Pinnacle {rec['pinnacle_gap']*100:+.1f}%")
        
        # Synthèse
        synth = result['synthesis']
        print(f"\n   🎯 SYNTHÈSE FINALE:")
        print(f"      V11 Score: {synth['v11_score']:.1f} | Final Confidence: {synth['final_confidence']}")
        print(f"      Opportunités: {synth['counts']['sniper']} SNIPER | {synth['counts']['normal']} NORMAL | {synth['counts']['speculative']} SPEC")
        
        if synth['warnings']['market_divergences'] > 0:
            print(f"      ⚠️ {synth['warnings']['market_divergences']} divergence(s) marché détectée(s)")
        
        if synth['best_bet']:
            bb = synth['best_bet']
            print(f"\n   💰 BEST BET: {bb['market']} @ {bb['odds']:.2f}")
            print(f"      Edge: {bb['edge']*100:.1f}% | Sharpe: {bb['sharpe']:.2f} | {bb['recommendation']}")
        else:
            print(f"\n   ❌ Pas de pari recommandé (SKIP)")
        
        print("\n" + "═" * 100)
        
        return result
    
    def close(self):
        """Ferme les connexions"""
        # Fermer la connexion Smart Market Selector
        if hasattr(self, 'smart_selector'):
            self.smart_selector.close()
        # Fermer la connexion DB héritée si elle existe
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════════════

def test_v12():
    print("=" * 100)
    print("   🧪 TEST ORCHESTRATOR V12 - SMART MARKET INTEGRATION")
    print("=" * 100)
    
    orchestrator = OrchestratorV12()
    
    matches = [
        ("Barcelona", "Atlético Madrid", "La Liga"),
        ("Marseille", "Monaco", "Ligue 1"),
    ]
    
    for home, away, league in matches:
        orchestrator.print_analysis(home, away, league)
    
    orchestrator.close()
    
    print("\n✅ Test V12 terminé!")


if __name__ == "__main__":
    test_v12()

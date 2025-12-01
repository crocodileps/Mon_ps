"""
🏎️💎 PATRON DIAMOND + FERRARI INTEGRATION
==========================================
Intégration de l'intelligence FERRARI dans PATRON Diamond

Fonctionnalités:
- Enrichissement automatique des analyses
- Détection des pièges avant recommandation
- Ajustement des scores basé sur les alertes
- Recommandations contextuelles intelligentes

Flow:
1. PATRON Diamond analyse le match (Poisson, xG, etc.)
2. FERRARI enrichit avec profils et alertes
3. Scores ajustés selon les pièges détectés
4. Recommandations finales enrichies
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Imports des services
sys.path.insert(0, '/app')
from api.services.patron_diamond_v3 import PatronDiamondV3, get_patron_diamond
from api.services.ferrari_intelligence_service import (
    FerrariIntelligenceService, 
    get_ferrari_intelligence,
    AlertLevel
)

logger = logging.getLogger(__name__)


class EnrichedRecommendation(Enum):
    """Recommandations enrichies avec contexte FERRARI"""
    DIAMOND_SAFE = "💎🏎️ DIAMOND SAFE"      # Diamond + pas de piège
    DIAMOND_CAUTION = "💎⚠️ DIAMOND CAUTION"  # Diamond + attention
    STRONG_SAFE = "✅🏎️ STRONG SAFE"         # Strong + pas de piège
    STRONG_CAUTION = "✅⚠️ STRONG CAUTION"    # Strong + attention
    TRAP_DETECTED = "🚨 TRAP DETECTED"        # Piège détecté
    VALUE_HIDDEN = "🔍 HIDDEN VALUE"          # Value cachée
    SKIP = "⏭️ SKIP"
    AVOID = "❌ AVOID"


@dataclass
class EnrichedMarketAnalysis:
    """Analyse de marché enrichie avec FERRARI"""
    market: str
    original_score: float
    adjusted_score: float
    original_recommendation: str
    enriched_recommendation: str
    has_trap: bool
    trap_details: Optional[Dict]
    ferrari_insights: List[str]
    confidence_adjustment: int


class PatronFerrariIntegration:
    """
    Intégration PATRON Diamond + FERRARI Intelligence
    
    Combine la puissance analytique de PATRON Diamond
    avec l'intelligence tactique de FERRARI.
    """
    
    def __init__(self):
        self.patron = get_patron_diamond()
        self.ferrari = get_ferrari_intelligence()
        logger.info("🏎️💎 PATRON + FERRARI Integration initialisée")
    
    def analyze_match_enriched(self, match_id: str, home_team: str, away_team: str,
                               agents_analysis: List[Dict] = None,
                               odds_btts: float = None, 
                               odds_over25: float = None) -> Dict:
        """
        Analyse complète enrichie d'un match
        
        1. Analyse PATRON Diamond (Poisson, xG, marchés)
        2. Enrichissement FERRARI (profils, pièges)
        3. Ajustement des scores et recommandations
        
        Returns:
            Analyse complète avec intelligence FERRARI intégrée
        """
        # ════════════════════════════════════════════════════════════
        # ÉTAPE 1: ANALYSE PATRON DIAMOND
        # ════════════════════════════════════════════════════════════
        patron_analysis = self.patron.analyze_match_full(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            agents_analysis=agents_analysis,
            odds_btts=odds_btts,
            odds_over25=odds_over25
        )
        
        # ════════════════════════════════════════════════════════════
        # ÉTAPE 2: ENRICHISSEMENT FERRARI
        # ════════════════════════════════════════════════════════════
        ferrari_enrichment = self.ferrari.enrich_match_analysis(home_team, away_team)

        # ════════════════════════════════════════════════════════════
        # ÉTAPE 2.5: ENRICHISSEMENT COACH INTELLIGENCE 🧠
        # ════════════════════════════════════════════════════════════
        coach_enrichment = self.ferrari.enrich_match_with_coaches(home_team, away_team)
        if coach_enrichment.get("home_coach", {}).get("enabled"):
            logger.info(f"🧠 Coach: {home_team} ({coach_enrichment['home_coach'].get('coach_name')}) vs {away_team} ({coach_enrichment['away_coach'].get('coach_name')})")
        
        # ════════════════════════════════════════════════════════════
        # ÉTAPE 3: ENRICHIR CHAQUE MARCHÉ
        # ════════════════════════════════════════════════════════════
        enriched_markets = {}
        
        # BTTS
        if 'btts' in patron_analysis:
            btts_trap = ferrari_enrichment['traps'].get('btts_yes', {})
            btts_no_trap = ferrari_enrichment['traps'].get('btts_no', {})
            
            enriched_markets['btts'] = self._enrich_market(
                market_name='btts_yes',
                original_data=patron_analysis['btts'],
                trap_info=btts_trap,
                counter_trap_info=btts_no_trap
            )
        
        # Over 2.5
        if 'over25' in patron_analysis:
            over_trap = ferrari_enrichment['traps'].get('over_25', {})
            under_trap = ferrari_enrichment['traps'].get('under_25', {})
            
            enriched_markets['over25'] = self._enrich_market(
                market_name='over_25',
                original_data=patron_analysis['over25'],
                trap_info=over_trap,
                counter_trap_info=under_trap
            )
        
        # 1X2 Markets
        for market in ['home', 'away', 'draw']:
            trap_info = ferrari_enrichment['traps'].get(market, {})
            if trap_info:
                enriched_markets[f'1x2_{market}'] = {
                    'has_trap': trap_info.get('has_trap', False),
                    'alerts': trap_info.get('alerts', []),
                    'recommendation': trap_info.get('recommendation', '')
                }
        
        # ════════════════════════════════════════════════════════════
        # ÉTAPE 4: AJUSTER LE SCORE GLOBAL
        # ════════════════════════════════════════════════════════════
        confidence_penalty = ferrari_enrichment.get('confidence_adjustment', 0)
        
        original_patron_score = patron_analysis.get('patron_score', 50)
        adjusted_patron_score = max(0, original_patron_score + confidence_penalty)
        
        # ════════════════════════════════════════════════════════════
        # ÉTAPE 5: GÉNÉRER RECOMMANDATION ENRICHIE
        # ════════════════════════════════════════════════════════════
        has_any_trap = any(
            m.get('has_trap', False) 
            for m in enriched_markets.values() 
            if isinstance(m, dict)
        )
        
        enriched_recommendation = self._generate_enriched_recommendation(
            patron_score=adjusted_patron_score,
            has_trap=has_any_trap,
            ferrari_recs=ferrari_enrichment.get('recommendations', [])
        )
        
        # ════════════════════════════════════════════════════════════
        # ÉTAPE 6: CONSTRUIRE LA RÉPONSE FINALE
        # ════════════════════════════════════════════════════════════
        return {
            # Données PATRON originales
            **patron_analysis,
            
            # Enrichissement FERRARI
            'ferrari': {
                'home_profile': ferrari_enrichment.get('home_profile'),
                'away_profile': ferrari_enrichment.get('away_profile'),
                'style_matchup': ferrari_enrichment.get('style_matchup'),
                'traps_detected': list(ferrari_enrichment.get('traps', {}).keys()),
                'recommendations': ferrari_enrichment.get('recommendations', []),
                'analyzed': ferrari_enrichment.get('ferrari_analyzed', False),
                'coach_intelligence': coach_enrichment
            },
            
            # Marchés enrichis
            'enriched_markets': enriched_markets,
            
            # Scores ajustés
            'adjusted_scores': {
                'original_patron_score': original_patron_score,
                'confidence_penalty': confidence_penalty,
                'adjusted_patron_score': adjusted_patron_score
            },
            
            # Recommandation finale
            'enriched_recommendation': enriched_recommendation,
            'has_trap': has_any_trap,
            
            # Meta
            'integration_version': '1.0.0',
            'powered_by': 'PATRON Diamond + FERRARI Intelligence'
        }
    
    def _enrich_market(self, market_name: str, original_data: Dict,
                       trap_info: Dict, counter_trap_info: Dict = None) -> Dict:
        """Enrichit un marché avec les données FERRARI"""
        
        original_score = original_data.get('score', 50)
        original_rec = original_data.get('recommendation', 'SKIP')
        
        has_trap = trap_info.get('has_trap', False)
        confidence_penalty = trap_info.get('confidence_penalty', 0)
        
        # Ajuster le score
        adjusted_score = max(0, original_score - confidence_penalty)
        
        # Générer insights
        insights = []
        
        if has_trap:
            insights.append(f"🚨 PIÈGE sur {market_name.upper()}")
            for alert in trap_info.get('alerts', []):
                insights.append(f"  → {alert.get('reason', '')}")
        
        # Vérifier si le marché opposé est safe
        if counter_trap_info and counter_trap_info.get('has_trap'):
            alternative = trap_info.get('alerts', [{}])[0].get('alternative', '')
            if alternative:
                insights.append(f"💡 Alternative suggérée: {alternative.upper()}")
        
        # Déterminer la recommandation enrichie
        if has_trap:
            enriched_rec = EnrichedRecommendation.TRAP_DETECTED.value
        elif adjusted_score >= 70:
            enriched_rec = EnrichedRecommendation.DIAMOND_SAFE.value
        elif adjusted_score >= 55:
            enriched_rec = EnrichedRecommendation.STRONG_SAFE.value
        else:
            enriched_rec = original_rec
        
        return {
            'market': market_name,
            'original_score': original_score,
            'adjusted_score': adjusted_score,
            'original_recommendation': original_rec,
            'enriched_recommendation': enriched_rec,
            'has_trap': has_trap,
            'trap_details': trap_info if has_trap else None,
            'insights': insights,
            'confidence_penalty': confidence_penalty
        }
    
    def _generate_enriched_recommendation(self, patron_score: float,
                                          has_trap: bool,
                                          ferrari_recs: List[str]) -> Dict:
        """Génère la recommandation finale enrichie"""
        
        # Déterminer le niveau
        if has_trap:
            level = "CAUTION"
            emoji = "⚠️"
            action = "Vérifier les pièges avant de parier"
        elif patron_score >= 70:
            level = "DIAMOND"
            emoji = "💎"
            action = "Opportunité excellente"
        elif patron_score >= 55:
            level = "STRONG"
            emoji = "✅"
            action = "Bonne opportunité"
        elif patron_score >= 45:
            level = "MONITOR"
            emoji = "👁️"
            action = "À surveiller"
        else:
            level = "SKIP"
            emoji = "⏭️"
            action = "Passer ce match"
        
        return {
            'level': level,
            'emoji': emoji,
            'action': action,
            'patron_score': patron_score,
            'ferrari_insights': ferrari_recs[:3],  # Top 3
            'summary': f"{emoji} {level} - {action}"
        }
    
    def get_market_recommendation(self, home_team: str, away_team: str, 
                                  market: str) -> Dict:
        """
        Obtient une recommandation rapide pour un marché spécifique
        
        Utile pour les checks rapides avant un pari
        """
        # Check des pièges
        trap_info = self.ferrari.check_match_traps(home_team, away_team, market)
        
        # Profils
        home_profile = self.ferrari.get_team_profile(home_team)
        away_profile = self.ferrari.get_team_profile(away_team)
        
        recommendation = {
            'match': f"{home_team} vs {away_team}",
            'market': market,
            'safe_to_bet': not trap_info['has_trap'],
            'trap_detected': trap_info['has_trap'],
            'alerts': trap_info['alerts'],
            'recommendation': trap_info['recommendation'],
            'confidence_penalty': trap_info['confidence_penalty']
        }
        
        # Ajouter contexte des profils
        if home_profile:
            recommendation['home_context'] = {
                'style': home_profile.style,
                'tags': home_profile.tags[:3],
                'reliable': home_profile.is_reliable
            }
        
        if away_profile:
            recommendation['away_context'] = {
                'style': away_profile.style,
                'tags': away_profile.tags[:3],
                'reliable': away_profile.is_reliable
            }
        
        return recommendation


# Singleton
_integration = None

def get_patron_ferrari():
    """Factory pour obtenir l'intégration PATRON + FERRARI"""
    global _integration
    if _integration is None:
        _integration = PatronFerrariIntegration()
    return _integration

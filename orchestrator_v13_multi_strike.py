#!/usr/bin/env python3
"""
ORCHESTRATOR V13 - MULTI-STRIKE (CORRIGÉ)
==========================================
Utilise les probabilités TACTICAL (vraies stats) au lieu de XG par défaut

Règles:
- SNIPER (≥32): Over 2.5 + BTTS (si TACTICAL >55%) + Over 3.5 (si >40%)
- NORMAL (≥30): Over 2.5 uniquement
- SKIP (<30): SKIP ABSOLU
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from math import factorial, exp
from orchestrator_v11_4_god_tier import OrchestratorV11_4


@dataclass
class MultiStrikeBet:
    """Un pari dans la stratégie Multi-Strike"""
    market: str
    probability: float
    stake_units: float
    odds_estimate: float
    confidence: str
    reason: str


@dataclass  
class MultiStrikeResult:
    """Résultat complet de l'analyse V13"""
    home: str
    away: str
    league: str
    v11_score: float
    v11_action: str
    bets: List[MultiStrikeBet]
    total_stake: float
    expected_value: float
    probabilities: Dict[str, float]


class OrchestratorV13:
    """
    V13 Multi-Strike: Maximiser les gains sur matchs SNIPER
    en utilisant les probabilités TACTICAL réelles
    """
    
    # Seuils V11.4
    SNIPER_THRESHOLD = 32.0
    NORMAL_THRESHOLD = 30.0
    
    # Seuils de probabilité pour marchés bonus
    BTTS_THRESHOLD = 55.0       # 55% pour BTTS (en %)
    OVER35_THRESHOLD = 40.0     # 40% pour Over 3.5 (en %)
    
    # Stakes par niveau (en unités)
    STAKES = {
        'SNIPER': {
            'over_25': 3.0,
            'btts': 1.5,
            'over_35': 1.0,
        },
        'NORMAL': {
            'over_25': 2.0,
        }
    }
    
    # Cotes estimées moyennes
    ODDS_ESTIMATE = {
        'over_25': 1.85,
        'btts': 1.80,
        'over_35': 2.40,
    }
    
    def __init__(self):
        """Initialise V13 avec V11.4 comme moteur de décision"""
        self.v11 = OrchestratorV11_4()
        print("   🚀 V13 Multi-Strike initialisé (TACTICAL probs)")
        print(f"   �� SNIPER ≥{self.SNIPER_THRESHOLD} | NORMAL ≥{self.NORMAL_THRESHOLD}")
        print(f"   📊 BTTS si ≥{self.BTTS_THRESHOLD}% | O35 si ≥{self.OVER35_THRESHOLD}%")
    
    def calculate_over35_prob(self, over25_prob: float) -> float:
        """
        Estime Over 3.5 à partir de Over 2.5
        Règle empirique: O35 ≈ O25 × 0.55 à 0.65
        """
        # Si Over 2.5 = 70%, Over 3.5 ≈ 42%
        # Si Over 2.5 = 50%, Over 3.5 ≈ 30%
        return over25_prob * 0.60
    
    def analyze_match(self, home: str, away: str, league: str) -> Optional[MultiStrikeResult]:
        """Analyse complète V13 Multi-Strike avec probabilités TACTICAL"""
        
        # 1. Obtenir l'analyse V11.4
        v11_result = self.v11.analyze_match(home, away, league)
        
        if not v11_result:
            return None
        
        v11_score = float(v11_result.get('score', 0))
        
        # 2. Extraire les probabilités TACTICAL (vraies stats)
        layers = v11_result.get('layers', {})
        tactical = layers.get('tactical', {})
        
        # Priorité: TACTICAL > XG > défaut
        over25_prob = float(tactical.get('over25', 50.0))  # En %
        btts_prob = float(tactical.get('btts', 50.0))       # En %
        over35_prob = self.calculate_over35_prob(over25_prob)  # Estimé
        
        probabilities = {
            'over_25': over25_prob,
            'btts': btts_prob,
            'over_35': over35_prob,
        }
        
        # 3. Construire les paris selon le SCORE V11.4
        bets = []
        
        # ══════════════════════════════════════════════════════════════
        # SKIP ABSOLU si Score < 30
        # ══════════════════════════════════════════════════════════════
        if v11_score < self.NORMAL_THRESHOLD:
            return MultiStrikeResult(
                home=home, away=away, league=league,
                v11_score=v11_score, v11_action='SKIP',
                bets=[], total_stake=0.0, expected_value=0.0,
                probabilities=probabilities
            )
        
        # ══════════════════════════════════════════════════════════════
        # SNIPER (Score ≥ 32): Multi-Strike
        # ══════════════════════════════════════════════════════════════
        if v11_score >= self.SNIPER_THRESHOLD:
            action = 'SNIPER_BET'
            
            # Pari 1: Over 2.5 (TOUJOURS)
            bets.append(MultiStrikeBet(
                market='over_25',
                probability=over25_prob / 100,  # Convertir en décimal pour EV
                stake_units=self.STAKES['SNIPER']['over_25'],
                odds_estimate=self.ODDS_ESTIMATE['over_25'],
                confidence='HIGH',
                reason=f"SNIPER: O25 prob={over25_prob:.0f}%"
            ))
            
            # Pari 2: BTTS (si prob ≥ 55%)
            if btts_prob >= self.BTTS_THRESHOLD:
                conf = 'HIGH' if btts_prob >= 60 else 'MEDIUM'
                bets.append(MultiStrikeBet(
                    market='btts',
                    probability=btts_prob / 100,
                    stake_units=self.STAKES['SNIPER']['btts'],
                    odds_estimate=self.ODDS_ESTIMATE['btts'],
                    confidence=conf,
                    reason=f"SNIPER+: BTTS prob={btts_prob:.0f}% ≥ 55%"
                ))
            
            # Pari 3: Over 3.5 (si prob ≥ 40%)
            if over35_prob >= self.OVER35_THRESHOLD:
                conf = 'MEDIUM' if over35_prob >= 50 else 'LOW'
                bets.append(MultiStrikeBet(
                    market='over_35',
                    probability=over35_prob / 100,
                    stake_units=self.STAKES['SNIPER']['over_35'],
                    odds_estimate=self.ODDS_ESTIMATE['over_35'],
                    confidence=conf,
                    reason=f"SNIPER+: O35 prob={over35_prob:.0f}% ≥ 40%"
                ))
        
        # ══════════════════════════════════════════════════════════════
        # NORMAL (Score 30-32): Over 2.5 uniquement
        # ══════════════════════════════════════════════════════════════
        else:
            action = 'NORMAL_BET'
            
            bets.append(MultiStrikeBet(
                market='over_25',
                probability=over25_prob / 100,
                stake_units=self.STAKES['NORMAL']['over_25'],
                odds_estimate=self.ODDS_ESTIMATE['over_25'],
                confidence='MEDIUM',
                reason=f"NORMAL: O25 prob={over25_prob:.0f}%"
            ))
        
        # 4. Calculer totaux
        total_stake = sum(b.stake_units for b in bets)
        expected_value = sum(
            b.stake_units * (b.probability * b.odds_estimate - 1)
            for b in bets
        )
        
        return MultiStrikeResult(
            home=home, away=away, league=league,
            v11_score=v11_score, v11_action=action,
            bets=bets, total_stake=total_stake, expected_value=expected_value,
            probabilities=probabilities
        )
    
    def print_analysis(self, result: MultiStrikeResult):
        """Affiche l'analyse formatée"""
        print("\n" + "=" * 80)
        print(f"🎯 V13: {result.home} vs {result.away}")
        print("=" * 80)
        
        icon = "🎯" if result.v11_action == 'SNIPER_BET' else "📈" if result.v11_action == 'NORMAL_BET' else "⏭️"
        print(f"\n📊 V11.4 Score: {result.v11_score:.1f} → {icon} {result.v11_action}")
        
        print(f"\n📈 Probabilités TACTICAL:")
        print(f"   Over 2.5: {result.probabilities['over_25']:.1f}%")
        print(f"   BTTS:     {result.probabilities['btts']:.1f}%")
        print(f"   Over 3.5: {result.probabilities['over_35']:.1f}% (estimé)")
        
        if not result.bets:
            print(f"\n⏭️ SKIP ABSOLU - Pas de pari")
            return
        
        print(f"\n🎰 PARIS ({len(result.bets)}):")
        for i, bet in enumerate(result.bets, 1):
            icon = "🎯" if bet.confidence == 'HIGH' else "✅" if bet.confidence == 'MEDIUM' else "⚡"
            print(f"   {i}. {icon} {bet.market.upper():10} | {bet.probability*100:.0f}% | {bet.stake_units}u @ ~{bet.odds_estimate}")
            print(f"      └─ {bet.reason}")
        
        print(f"\n💰 Total: {result.total_stake}u | EV: {result.expected_value:+.2f}u")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    v13 = OrchestratorV13()
    
    test_matches = [
        ("Arsenal", "Tottenham", "Premier League"),
        ("Barcelona", "Atlético Madrid", "La Liga"),
        ("Bayern Munich", "Freiburg", "Bundesliga"),
        ("Bournemouth", "West Ham", "Premier League"),
        ("Leverkusen", "Dortmund", "Bundesliga"),
        ("Roma", "Napoli", "Serie A"),
    ]
    
    print("=" * 80)
    print("�� TEST V13 MULTI-STRIKE (TACTICAL PROBS)")
    print("=" * 80)
    
    summary = {'SNIPER': 0, 'NORMAL': 0, 'SKIP': 0, 'bets': 0, 'stake': 0}
    
    for home, away, league in test_matches:
        result = v13.analyze_match(home, away, league)
        if result:
            v13.print_analysis(result)
            if 'SNIPER' in result.v11_action:
                summary['SNIPER'] += 1
            elif 'NORMAL' in result.v11_action:
                summary['NORMAL'] += 1
            else:
                summary['SKIP'] += 1
            summary['bets'] += len(result.bets)
            summary['stake'] += result.total_stake
    
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ V13")
    print("=" * 80)
    print(f"   🎯 SNIPER: {summary['SNIPER']} | 📈 NORMAL: {summary['NORMAL']} | ⏭️ SKIP: {summary['SKIP']}")
    print(f"   Total: {summary['bets']} paris | {summary['stake']}u stake")
    print("=" * 80)

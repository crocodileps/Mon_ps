"""
🩳 DEFENSE SHORTING ENGINE
Niveau Quant 3.0 - "On ne parie pas sur le sport, on parie sur l'effondrement"

Philosophie:
- Ne pas chercher QUI VA GAGNER
- Chercher QUI VA CRAQUER
- Short les défenses instables comme on short une action surévaluée
"""

import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path


class CollapseRisk(Enum):
    """Niveau de risque d'effondrement défensif"""
    CRITICAL = "CRITICAL"      # 80%+ → SHORT AGRESSIF
    HIGH = "HIGH"              # 60-80% → SHORT STANDARD
    ELEVATED = "ELEVATED"      # 40-60% → MONITOR
    MODERATE = "MODERATE"      # 20-40% → NEUTRAL
    LOW = "LOW"                # <20% → AVOID SHORT


class ShortSignal(Enum):
    """Type de signal de vente"""
    AGGRESSIVE_SHORT = "AGGRESSIVE_SHORT"  # Kelly max
    STANDARD_SHORT = "STANDARD_SHORT"      # Kelly normal
    OPPORTUNISTIC = "OPPORTUNISTIC"        # Si cote value
    MONITOR = "MONITOR"                    # Surveiller
    NO_TRADE = "NO_TRADE"                  # Pas de signal


@dataclass
class DefenseShortAnalysis:
    """Résultat de l'analyse Short"""
    team: str
    collapse_probability: float
    collapse_risk: CollapseRisk
    signal: ShortSignal
    
    # Détails
    defenders_in_crisis: int
    total_defenders: int
    crisis_names: List[str]
    
    # Métriques financières
    avg_alpha: float
    avg_sharpe: float
    max_cvar: float
    
    # Leadership
    has_leader: bool
    leader_name: Optional[str]
    leader_absent_edge: float
    
    # Raisons
    reasons: List[str]
    
    # Recommandations de paris
    recommended_markets: List[Dict]
    kelly_multiplier: float
    
    def __str__(self):
        risk_emoji = {
            CollapseRisk.CRITICAL: "🔴🔴",
            CollapseRisk.HIGH: "��",
            CollapseRisk.ELEVATED: "🟠",
            CollapseRisk.MODERATE: "🟡",
            CollapseRisk.LOW: "🟢"
        }
        return f"{risk_emoji[self.collapse_risk]} {self.team}: {self.collapse_probability:.0f}% collapse risk ({self.signal.value})"


class DefenseShortingEngine:
    """
    Moteur de détection des effondrements défensifs
    
    Principe: Identifier les défenses "en faillite technique"
    - Markov Crisis (psychologie)
    - Alpha Négatif (sous-performance structurelle)
    - CVaR élevé (risque extrême)
    - Leadership Vacuum (pas de leader)
    """
    
    CRISIS_STATES = [
        'PRESSURE_CRACKER',
        'SLUMP', 
        'CONFIDENCE_CRISIS',
        'LIABILITY_CONFIRMED',
        'TOTAL_COLLAPSE',
        'DECLINING'
    ]
    
    POSITIVE_STATES = [
        'ELITE_FORM',
        'CLUTCH_MODE',
        'CONSISTENT_ROCK',
        'IMPROVING'
    ]
    
    def __init__(self):
        self.defenders_data: List[Dict] = []
        self.teams_defenders: Dict[str, List[Dict]] = {}
        self.loaded = False
        
    def load_data(self):
        """Charge les données defender_dna_quant_v9"""
        if self.loaded:
            return
            
        path = Path("/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json")
        if path.exists():
            with open(path) as f:
                self.defenders_data = json.load(f)
                
            # Grouper par équipe
            for d in self.defenders_data:
                team = d.get('team', 'Unknown')
                if team not in self.teams_defenders:
                    self.teams_defenders[team] = []
                self.teams_defenders[team].append(d)
                
        self.loaded = True
        print(f"✅ Defense Shorting Engine: {len(self.defenders_data)} défenseurs, {len(self.teams_defenders)} équipes")
    
    def _get_markov_state(self, defender: Dict) -> str:
        """Extrait l'état Hidden Markov"""
        return defender.get('quant_v9', {}).get('hidden_markov', {}).get('current_state', 'UNKNOWN')
    
    def _get_alpha(self, defender: Dict) -> float:
        """Extrait l'alpha"""
        return defender.get('quant_v9', {}).get('alpha_beta', {}).get('alpha', 0)
    
    def _get_beta(self, defender: Dict) -> float:
        """Extrait le beta"""
        return defender.get('quant_v9', {}).get('alpha_beta', {}).get('beta', 1.0)
    
    def _get_sharpe(self, defender: Dict) -> float:
        """Extrait le Sharpe ratio"""
        return defender.get('quant_v9', {}).get('sharpe', {}).get('sharpe_ratio', 0)
    
    def _get_cvar95(self, defender: Dict) -> float:
        """Extrait le CVaR 95%"""
        return defender.get('quant_v9', {}).get('cvar', {}).get('CVaR_95', 0)
    
    def _get_leadership(self, defender: Dict) -> Dict:
        """Extrait les données de leadership"""
        return defender.get('quant_v9', {}).get('leadership', {})
    
    def _get_tilt(self, defender: Dict) -> Dict:
        """Extrait les données de tilt"""
        return defender.get('quant_v9', {}).get('tilt', {})
    
    def _get_transition_vuln(self, defender: Dict) -> Dict:
        """Extrait la vulnérabilité aux transitions"""
        return defender.get('quant_v9', {}).get('transition', {})
    
    def analyze_team_defense(self, team: str, opponent_style: str = None) -> DefenseShortAnalysis:
        """
        Analyse complète de la défense d'une équipe pour Short
        
        Args:
            team: Nom de l'équipe
            opponent_style: Style de l'adversaire (FAST, DIRECT, POSSESSION, etc.)
        """
        self.load_data()
        
        defenders = self.teams_defenders.get(team, [])
        if not defenders:
            return None
            
        # Filtrer les titulaires (temps de jeu > 500 min)
        starters = [d for d in defenders if d.get('time', 0) > 500]
        if not starters:
            starters = defenders[:5]  # Fallback
            
        risk_score = 0
        reasons = []
        recommended_markets = []
        
        # ═══════════════════════════════════════════════════════════════
        # 1. ANALYSE HIDDEN MARKOV (Psychologie collective)
        # ═══════════════════════════════════════════════════════════════
        crisis_defenders = []
        positive_defenders = []
        
        for d in starters:
            state = self._get_markov_state(d)
            name = d.get('name', 'Unknown')
            
            if state in self.CRISIS_STATES:
                crisis_defenders.append((name, state))
            elif state in self.POSITIVE_STATES:
                positive_defenders.append((name, state))
        
        crisis_ratio = len(crisis_defenders) / len(starters) if starters else 0
        
        # Score basé sur le ratio de défenseurs en crise
        if crisis_ratio >= 0.75:  # 75%+ en crise
            risk_score += 45
            reasons.append(f"🚨 EFFONDREMENT SYSTÉMIQUE: {len(crisis_defenders)}/{len(starters)} défenseurs en CRISE")
        elif crisis_ratio >= 0.50:  # 50%+ en crise
            risk_score += 30
            reasons.append(f"⚠️ Crise collective: {len(crisis_defenders)}/{len(starters)} défenseurs instables")
        elif crisis_ratio >= 0.25:  # 25%+ en crise
            risk_score += 15
            reasons.append(f"🟠 Fragilité détectée: {len(crisis_defenders)} défenseurs en difficulté")
        
        # Bonus négatif si défenseurs en forme
        if len(positive_defenders) >= 2:
            risk_score -= 10
            reasons.append(f"🟢 Stabilisateurs présents: {len(positive_defenders)} en bonne forme")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. ANALYSE ALPHA/BETA (Performance structurelle)
        # ═══════════════════════════════════════════════════════════════
        alphas = [self._get_alpha(d) for d in starters]
        betas = [self._get_beta(d) for d in starters]
        
        avg_alpha = np.mean(alphas) if alphas else 0
        avg_beta = np.mean(betas) if betas else 1
        
        # Alpha négatif = sous-performance structurelle
        if avg_alpha < -0.5:
            risk_score += 25
            reasons.append(f"📉 Alpha TRÈS NÉGATIF ({avg_alpha:.2f}): Destruction de valeur systémique")
        elif avg_alpha < -0.3:
            risk_score += 15
            reasons.append(f"📉 Alpha négatif ({avg_alpha:.2f}): Sous-performance structurelle")
        elif avg_alpha < 0:
            risk_score += 5
            reasons.append(f"📊 Alpha légèrement négatif ({avg_alpha:.2f})")
        
        # Beta élevé = volatilité
        if avg_beta > 1.3:
            risk_score += 10
            reasons.append(f"📈 Beta élevé ({avg_beta:.2f}): Défense IMPRÉVISIBLE")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. ANALYSE CVaR (Risque extrême)
        # ═══════════════════════════════════════════════════════════════
        cvars = [self._get_cvar95(d) for d in starters]
        max_cvar = max(cvars) if cvars else 0
        avg_cvar = np.mean(cvars) if cvars else 0
        
        if max_cvar > 4.0:
            risk_score += 20
            reasons.append(f"💣 CVaR EXTRÊME ({max_cvar:.1f}): Risque d'explosion dans les pires cas")
            recommended_markets.append({
                'market': 'Over 3.5 Goals',
                'edge': 5.0,
                'reasoning': f'CVaR {max_cvar:.1f} = risque de 4+ buts dans matchs difficiles'
            })
        elif max_cvar > 3.0:
            risk_score += 10
            reasons.append(f"⚠️ CVaR élevé ({max_cvar:.1f}): Vulnérable dans matchs tendus")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. ANALYSE SHARPE (Qualité de la défense)
        # ═══════════════════════════════════════════════════════════════
        sharpes = [self._get_sharpe(d) for d in starters]
        avg_sharpe = np.mean(sharpes) if sharpes else 0
        
        if avg_sharpe < 0.3:
            risk_score += 15
            reasons.append(f"📊 Sharpe faible ({avg_sharpe:.2f}): Mauvais ratio risque/rendement")
        
        # ═══════════════════════════════════════════════════════════════
        # 5. ANALYSE LEADERSHIP (Vacuum?)
        # ═══════════════════════════════════════════════════════════════
        leaders = [d for d in starters if self._get_leadership(d).get('is_leader', False)]
        has_leader = len(leaders) > 0
        leader_name = leaders[0].get('name') if leaders else None
        
        # Dépendance au leader
        dependent_defenders = [d for d in starters if 
                             self._get_leadership(d).get('role') == 'LEADER_DEPENDENT']
        
        if not has_leader and len(dependent_defenders) >= 2:
            risk_score += 20
            reasons.append(f"🕳️ LEADERSHIP VACUUM: {len(dependent_defenders)} défenseurs dépendants sans leader")
        
        # Edge si leader absent
        leader_absent_edge = 0
        if leaders:
            for dep in dependent_defenders:
                edge = self._get_leadership(dep).get('edge_if_leader_absent', 0)
                leader_absent_edge = max(leader_absent_edge, edge)
        
        # ═══════════════════════════════════════════════════════════════
        # 6. ANALYSE TILT (Erreurs en cascade)
        # ═══════════════════════════════════════════════════════════════
        tilters = [d for d in starters if 
                  self._get_tilt(d).get('profile') in ['TILTER', 'REACTIVE']]
        
        if len(tilters) >= 2:
            compound_risk = sum(self._get_tilt(d).get('compound_error_risk', 0) for d in tilters)
            if compound_risk > 20:
                risk_score += 10
                reasons.append(f"🎰 TILT RISK: {len(tilters)} défenseurs peuvent tilter (cascade d'erreurs)")
        
        # ═══════════════════════════════════════════════════════════════
        # 7. ANALYSE TRANSITION (vs style adversaire)
        # ═══════════════════════════════════════════════════════════════
        if opponent_style in ['FAST', 'COUNTER', 'TRANSITION']:
            transition_vulns = [d for d in starters if 
                              self._get_transition_vuln(d).get('vs_fast_teams') == 'VULNERABLE']
            
            if len(transition_vulns) >= 2:
                risk_score += 15
                reasons.append(f"⚡ MATCHUP DANGER: {len(transition_vulns)} vulnérables aux contres vs équipe rapide")
        
        # ═══════════════════════════════════════════════════════════════
        # CALCUL FINAL
        # ═══════════════════════════════════════════════════════════════
        collapse_probability = min(100, max(0, risk_score))
        
        # Déterminer le niveau de risque
        if collapse_probability >= 80:
            collapse_risk = CollapseRisk.CRITICAL
            signal = ShortSignal.AGGRESSIVE_SHORT
            kelly_mult = 1.5
        elif collapse_probability >= 60:
            collapse_risk = CollapseRisk.HIGH
            signal = ShortSignal.STANDARD_SHORT
            kelly_mult = 1.0
        elif collapse_probability >= 40:
            collapse_risk = CollapseRisk.ELEVATED
            signal = ShortSignal.OPPORTUNISTIC
            kelly_mult = 0.7
        elif collapse_probability >= 20:
            collapse_risk = CollapseRisk.MODERATE
            signal = ShortSignal.MONITOR
            kelly_mult = 0.5
        else:
            collapse_risk = CollapseRisk.LOW
            signal = ShortSignal.NO_TRADE
            kelly_mult = 0
        
        # Recommandations de marchés
        if collapse_probability >= 60:
            recommended_markets.append({
                'market': 'Opponent Team Over 1.5 Goals',
                'edge': collapse_probability / 10,
                'reasoning': 'Short la défense instable'
            })
        
        if collapse_probability >= 75:
            recommended_markets.append({
                'market': 'Opponent Team Over 2.5 Goals',
                'edge': (collapse_probability - 50) / 10,
                'reasoning': 'Effondrement probable'
            })
        
        if max_cvar > 3.5:
            recommended_markets.append({
                'market': 'Match Over 3.5 Goals',
                'edge': max_cvar - 2,
                'reasoning': f'CVaR tail risk {max_cvar:.1f}'
            })
        
        return DefenseShortAnalysis(
            team=team,
            collapse_probability=collapse_probability,
            collapse_risk=collapse_risk,
            signal=signal,
            defenders_in_crisis=len(crisis_defenders),
            total_defenders=len(starters),
            crisis_names=[f"{n} ({s})" for n, s in crisis_defenders],
            avg_alpha=avg_alpha,
            avg_sharpe=avg_sharpe,
            max_cvar=max_cvar,
            has_leader=has_leader,
            leader_name=leader_name,
            leader_absent_edge=leader_absent_edge,
            reasons=reasons,
            recommended_markets=recommended_markets,
            kelly_multiplier=kelly_mult
        )
    
    def scan_all_teams(self) -> List[DefenseShortAnalysis]:
        """Scan toutes les équipes et retourne les SHORT signals"""
        self.load_data()
        
        results = []
        for team in self.teams_defenders.keys():
            analysis = self.analyze_team_defense(team)
            if analysis and analysis.signal != ShortSignal.NO_TRADE:
                results.append(analysis)
        
        # Trier par probabilité d'effondrement
        results.sort(key=lambda x: -x.collapse_probability)
        return results
    
    def get_short_opportunities(self, min_probability: float = 60) -> List[DefenseShortAnalysis]:
        """Retourne les meilleures opportunités de Short"""
        all_analyses = self.scan_all_teams()
        return [a for a in all_analyses if a.collapse_probability >= min_probability]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = DefenseShortingEngine()
    
    print("="*80)
    print("🩳 DEFENSE SHORTING ENGINE - SCAN")
    print("="*80)
    
    # Analyser West Ham spécifiquement
    print("\n" + "="*80)
    print("📊 ANALYSE WEST HAM")
    print("="*80)
    
    wh = engine.analyze_team_defense("West Ham", opponent_style="FAST")
    if wh:
        print(f"\n{wh}")
        print(f"\n   Défenseurs en crise: {wh.defenders_in_crisis}/{wh.total_defenders}")
        for name in wh.crisis_names:
            print(f"      • {name}")
        print(f"\n   Métriques:")
        print(f"      • Alpha moyen: {wh.avg_alpha:.2f}")
        print(f"      • Sharpe moyen: {wh.avg_sharpe:.2f}")
        print(f"      • CVaR max: {wh.max_cvar:.2f}")
        print(f"      • Leader: {wh.leader_name or 'AUCUN'}")
        print(f"\n   Raisons:")
        for r in wh.reasons:
            print(f"      {r}")
        print(f"\n   Marchés recommandés:")
        for m in wh.recommended_markets:
            print(f"      • {m['market']}: +{m['edge']:.1f}% edge")
            print(f"        {m['reasoning']}")
    
    # Top 10 opportunités de Short
    print("\n" + "="*80)
    print("🎯 TOP 10 SHORT OPPORTUNITIES")
    print("="*80)
    
    shorts = engine.get_short_opportunities(min_probability=50)
    for i, s in enumerate(shorts[:10], 1):
        print(f"\n{i}. {s}")
        print(f"   Kelly multiplier: {s.kelly_multiplier}x")
        if s.recommended_markets:
            print(f"   Best market: {s.recommended_markets[0]['market']}")

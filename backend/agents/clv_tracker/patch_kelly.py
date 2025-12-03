#!/usr/bin/env python3
"""Corriger le calcul Kelly"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Ancien calcul (bugué)
old = '''    def _calculate_kelly(self, pick: QuantPick) -> float:
        """Kelly Criterion"""
        if pick.odds <= 1 or pick.mc_edge <= 0:
            return 0.0
        win_prob = pick.mc_prob
        b = pick.odds - 1
        q = 1 - win_prob
        kelly = (b * win_prob - q) / b
        # Kelly fractionné (25%)
        return max(0, min(kelly * 25, 5.0))'''

# Nouveau calcul (corrigé)
new = '''    def _calculate_kelly(self, pick: QuantPick) -> float:
        """Kelly Criterion - retourne un pourcentage (ex: 0.05 = 5%)"""
        if pick.odds <= 1 or pick.mc_edge <= 0:
            return 0.0
        win_prob = pick.mc_prob
        b = pick.odds - 1
        q = 1 - win_prob
        kelly = (b * win_prob - q) / b
        # Kelly fractionné (25% du Kelly optimal), max 5% du bankroll
        return max(0, min(kelly * 0.25, 0.05))'''

if old in content:
    content = content.replace(old, new)
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.write(content)
    print("OK - Kelly corrigé")
else:
    print("Code Kelly non trouvé")

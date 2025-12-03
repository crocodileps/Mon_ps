#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
QUANT 2.0 SNIPER - SMART HYBRID SCORING
═══════════════════════════════════════════════════════════════════════════════

Remplace les seuils fixes par une formule continue :
Score_MC = Edge × 200 × Confidence × SweetSpotBonus

Nouveaux seuils de recommandation plus granulaires.
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. REMPLACER LE CALCUL DE SCORE MC (lignes ~2036-2048)
# ═══════════════════════════════════════════════════════════════════════════════

old_score_calc = '''        # Score basé sur edge et confiance
        score = 0
        if pick.mc_edge > 0.10:
            score = 20
        elif pick.mc_edge > 0.05:
            score = 15
        elif pick.mc_edge > 0.02:
            score = 10
        elif pick.mc_edge > 0:
            score = 5
        elif pick.mc_edge < -0.05:
            score = -10
        
        # Pondérer par confiance MC
        score = int(score * mc_result.confidence_score)'''

new_score_calc = '''        # ═══════════════════════════════════════════════════════
        # SMART HYBRID SCORING 2.0
        # Score continu pondéré par confiance + bonus sweet spot
        # ═══════════════════════════════════════════════════════
        
        # 1. Score de base proportionnel à l'Edge (linéaire)
        # Edge 5% = 10 pts, Edge 10% = 20 pts
        base_score = pick.mc_edge * 200
        
        # 2. Facteur de Confiance du Modèle
        confidence_factor = mc_result.confidence_score  # 0.0 à 1.0
        
        # 3. Bonus "Sweet Spot" - Edge entre 3% et 8% est le plus fiable
        sweet_spot_multiplier = 1.0
        if 0.03 <= pick.mc_edge <= 0.08:
            sweet_spot_multiplier = 1.25  # +25% bonus
        elif pick.mc_edge > 0.15:
            sweet_spot_multiplier = 0.8  # -20% penalty (suspect)
        
        # 4. Calcul Final pondéré
        score = int(base_score * confidence_factor * sweet_spot_multiplier)'''

if old_score_calc in content:
    content = content.replace(old_score_calc, new_score_calc)
    print("✅ 1. Smart Hybrid Scoring remplacé")
else:
    print("❌ 1. Pattern score calc non trouvé")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. REMPLACER LES SEUILS DE RECOMMANDATION (lignes ~2418-2434)
# ═══════════════════════════════════════════════════════════════════════════════

old_thresholds = '''        suffix = " ⚠️Low Data" if coverage < 0.4 else ""
        
        if pick.is_trap:
            return f"🚫 BLOCKED: {pick.trap_reason}"
        
        if score >= 80 and coverage >= 0.5:
            pick.confidence_level = "TRÈS HAUTE"
            return f"🟢🟢 STRONG BET{suffix}"
        elif score >= 65:
            pick.confidence_level = "HAUTE"
            return f"🟢 GOOD BET{suffix}"
        elif score >= 50:
            pick.confidence_level = "MOYENNE"
            return f"🟡 MODERATE{suffix}"
        elif score >= 35:
            pick.confidence_level = "BASSE"
            return f"⚪ WATCH{suffix}"
        else:
            pick.confidence_level = "TRÈS BASSE"
            return f"🔴 SKIP{suffix}"'''

new_thresholds = '''        suffix = " ⚠️Low Data" if coverage < 0.4 else ""
        
        if pick.is_trap:
            return f"🚫 BLOCKED: {pick.trap_reason}"
        
        # ═══════════════════════════════════════════════════════
        # NOUVEAUX SEUILS HYBRIDES V2.0
        # Plus granulaires, favorise Volume + EV positive
        # ═══════════════════════════════════════════════════════
        
        if score >= 75 and coverage >= 0.6:
            pick.confidence_level = "ELITE"
            return f"💎 ELITE VALUE{suffix}"
        elif score >= 60:
            pick.confidence_level = "TRÈS HAUTE"
            return f"🟢🟢 STRONG BET{suffix}"
        elif score >= 45:
            pick.confidence_level = "HAUTE"
            return f"🟢 GOOD BET{suffix}"
        elif score >= 30:
            pick.confidence_level = "MOYENNE"
            return f"🟡 VALUE LEAN{suffix}"
        elif score >= 18:
            pick.confidence_level = "BASSE"
            return f"⚪ WATCH{suffix}"
        else:
            pick.confidence_level = "TRÈS BASSE"
            return f"🔴 SKIP{suffix}"'''

if old_thresholds in content:
    content = content.replace(old_thresholds, new_thresholds)
    print("✅ 2. Nouveaux seuils hybrides appliqués")
else:
    print("❌ 2. Pattern thresholds non trouvé")

# Sauvegarder
with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n" + "="*70)
print("✅ SMART HYBRID SCORING V2.0 APPLIQUÉ!")
print("="*70)
print("""
Changements:
  1. Score MC = Edge × 200 × Confidence × SweetSpotBonus
     - Sweet Spot (3-8%): +25% bonus
     - Edge > 15%: -20% penalty (suspect)
  
  2. Nouveaux seuils:
     ≥75 + 60% coverage → 💎 ELITE VALUE
     ≥60 → 🟢🟢 STRONG BET  
     ≥45 → 🟢 GOOD BET
     ≥30 → 🟡 VALUE LEAN (nouveau!)
     ≥18 → ⚪ WATCH
     <18 → 🔴 SKIP
""")

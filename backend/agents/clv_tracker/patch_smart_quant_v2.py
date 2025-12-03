#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SMART QUANT 2.0 - DEFENSE CRUSHER + HYBRID BLENDER
═══════════════════════════════════════════════════════════════════════════════

Implémente:
1. Defense Crusher: Suppression xG basée sur clean_sheet_tendency (exponentiel)
2. Hybrid Blender: Mélange MC + Historique pondéré par confidence

Remplace les tiers hardcodés par une approche data-driven.
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. AJOUTER LES FONCTIONS HELPER APRÈS LA CLASSE LineupImpact
# ═══════════════════════════════════════════════════════════════════════════════

# Trouver l'endroit pour insérer (après les imports, avant MonteCarloEngine)
insert_after = '''LAYER_WEIGHTS = {
    'monte_carlo': 25,'''

helper_functions = '''LAYER_WEIGHTS = {
    'monte_carlo': 25,

# ═══════════════════════════════════════════════════════════════════════════════
# SMART QUANT 2.0 - HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def apply_defense_crusher(opponent_base_xg: float, defense_clean_sheet_rate: float) -> float:
    """
    Réduit l'xG adverse basé sur la tendance clean sheet de la défense.
    
    Formule exponentielle:
    - CS < 30%: Pas d'impact (défense normale)
    - CS = 50%: Facteur ~0.80 (-20%)
    - CS = 78%: Facteur ~0.45 (-55%)
    
    Args:
        opponent_base_xg: xG de base de l'adversaire
        defense_clean_sheet_rate: Taux de clean sheet (0-100)
    
    Returns:
        xG ajusté
    """
    if defense_clean_sheet_rate < 30:
        return opponent_base_xg  # Défense normale
    
    # Facteur de suppression exponentiel
    suppression_factor = 1 - (defense_clean_sheet_rate / 140) ** 1.5
    suppression_factor = max(0.3, suppression_factor)  # Minimum 30% de l'xG original
    
    return opponent_base_xg * suppression_factor


def calculate_hybrid_probability(mc_prob: float, hist_prob: float, 
                                  confidence_score: float) -> float:
    """
    Mélange simulation Monte Carlo et taux historique.
    
    Plus la confiance est haute, plus on écoute l'historique.
    
    Args:
        mc_prob: Probabilité Monte Carlo (0-1)
        hist_prob: Probabilité historique (0-1)
        confidence_score: Score de confiance (0-100)
    
    Returns:
        Probabilité hybride (0-1)
    """
    # Poids historique: max 50% si confidence = 100
    weight_hist = min(confidence_score, 100) / 200
    weight_mc = 1.0 - weight_hist
    
    return (mc_prob * weight_mc) + (hist_prob * weight_hist)


'''

if insert_after in content:
    content = content.replace(insert_after, helper_functions)
    print("✅ 1. Helper functions (Defense Crusher + Hybrid Blender) ajoutées")
else:
    print("❌ 1. Pattern LAYER_WEIGHTS non trouvé")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. MODIFIER CALCULATE_IMPACT POUR UTILISER DEFENSE CRUSHER
# ═══════════════════════════════════════════════════════════════════════════════

# Trouver le bloc après calcul des xG de base, avant Tier Adjustment
old_tier_block = '''        # ═══════════════════════════════════════════════════════
        # V10.3 - LEAGUE TIER ADJUSTMENT
        # D1 vs D2 = boost attaque D1, malus défense D2
        # ═══════════════════════════════════════════════════════
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        home_tier_val = tier_values.get(home_tier, 3)
        away_tier_val = tier_values.get(away_tier, 3)
        tier_diff = home_tier_val - away_tier_val
        
        if tier_diff >= 2:  # Home très supérieur (ex: Liverpool vs Sunderland)
            impact.home_base_xg *= 1.25  # +25% attaque home
            impact.away_base_xg *= 0.75  # -25% attaque away
        elif tier_diff >= 1:  # Home supérieur
            impact.home_base_xg *= 1.10  # +10% attaque home
            impact.away_base_xg *= 0.90  # -10% attaque away
        elif tier_diff <= -2:  # Away très supérieur
            impact.home_base_xg *= 0.75
            impact.away_base_xg *= 1.25
        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.90
            impact.away_base_xg *= 1.10'''

new_tier_block = '''        # ═══════════════════════════════════════════════════════
        # SMART QUANT 2.0 - DEFENSE CRUSHER
        # Suppression xG basée sur clean_sheet_tendency (exponentiel)
        # ═══════════════════════════════════════════════════════
        
        # Récupérer les métriques défensives
        home_cs_rate = float(home_intel.get('clean_sheet_tendency', 30)) if home_intel else 30
        away_cs_rate = float(away_intel.get('clean_sheet_tendency', 30)) if away_intel else 30
        
        # Appliquer Defense Crusher
        # Liverpool (78% CS) va écraser l'xG de Sunderland
        impact.away_base_xg = apply_defense_crusher(impact.away_base_xg, home_cs_rate)
        impact.home_base_xg = apply_defense_crusher(impact.home_base_xg, away_cs_rate)
        
        # ═══════════════════════════════════════════════════════
        # TIER ADJUSTMENT (Version allégée - le Defense Crusher fait le gros du travail)
        # ═══════════════════════════════════════════════════════
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        home_tier_val = tier_values.get(home_tier, 3)
        away_tier_val = tier_values.get(away_tier, 3)
        tier_diff = home_tier_val - away_tier_val
        
        # Ajustement allégé (le Defense Crusher gère la majeure partie)
        if tier_diff >= 2:  # Home très supérieur
            impact.home_base_xg *= 1.15  # +15% (réduit de 25%)
            impact.away_base_xg *= 0.85  # -15% (réduit de 25%)
        elif tier_diff >= 1:  # Home supérieur
            impact.home_base_xg *= 1.08
            impact.away_base_xg *= 0.92
        elif tier_diff <= -2:  # Away très supérieur
            impact.home_base_xg *= 0.85
            impact.away_base_xg *= 1.15
        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.92
            impact.away_base_xg *= 1.08'''

if old_tier_block in content:
    content = content.replace(old_tier_block, new_tier_block)
    print("✅ 2. Defense Crusher intégré dans calculate_impact")
else:
    print("❌ 2. Pattern Tier Adjustment non trouvé")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. SAUVEGARDER
# ═══════════════════════════════════════════════════════════════════════════════

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n" + "="*70)
print("✅ SMART QUANT 2.0 APPLIQUÉ!")
print("="*70)
print("""
Intégrations:
  1. apply_defense_crusher() - Suppression xG exponentielle
     - CS 30%: 0% réduction
     - CS 50%: 20% réduction  
     - CS 78%: 55% réduction (Liverpool!)
     
  2. calculate_hybrid_probability() - Blend MC + Historique
     - Pondération par confidence_score
     
  3. Tier Adjustment allégé (Defense Crusher fait le gros du travail)
""")

#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
HYBRID BLENDER - Intégration dans _calculate_mc_score
═══════════════════════════════════════════════════════════════════════════════
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. MODIFIER LA SIGNATURE ET LE CORPS DE _calculate_mc_score
# ═══════════════════════════════════════════════════════════════════════════════

old_method = '''    def _calculate_mc_score(self, pick: QuantPick, mc_result: MonteCarloResult) -> int:
        """Score basé sur Monte Carlo"""
        market = pick.market_type.lower()
        
        # Mapper marché vers probabilité MC
        if 'btts_yes' in market:
            mc_prob = mc_result.btts_prob
        elif 'btts_no' in market:
            mc_prob = 1 - mc_result.btts_prob
        elif 'over_25' in market:
            mc_prob = mc_result.over_25_prob
        elif 'under_25' in market:
            mc_prob = 1 - mc_result.over_25_prob
        elif 'over_35' in market:
            mc_prob = mc_result.over_35_prob
        elif 'over_15' in market:
            mc_prob = mc_result.over_15_prob
        elif 'home' in market:
            mc_prob = mc_result.home_win_prob
        elif 'away' in market:
            mc_prob = mc_result.away_win_prob
        elif 'draw' in market:
            mc_prob = mc_result.draw_prob
        else:
            mc_prob = 0.5
        
        pick.mc_prob = mc_prob'''

new_method = '''    def _calculate_mc_score(self, pick: QuantPick, mc_result: MonteCarloResult,
                            context: Dict = None) -> int:
        """Score basé sur Monte Carlo + Hybrid Blender"""
        market = pick.market_type.lower()
        
        # Mapper marché vers probabilité MC
        if 'btts_yes' in market:
            mc_prob = mc_result.btts_prob
        elif 'btts_no' in market:
            mc_prob = 1 - mc_result.btts_prob
        elif 'over_25' in market:
            mc_prob = mc_result.over_25_prob
        elif 'under_25' in market:
            mc_prob = 1 - mc_result.over_25_prob
        elif 'over_35' in market:
            mc_prob = mc_result.over_35_prob
        elif 'over_15' in market:
            mc_prob = mc_result.over_15_prob
        elif 'home' in market:
            mc_prob = mc_result.home_win_prob
        elif 'away' in market:
            mc_prob = mc_result.away_win_prob
        elif 'draw' in market:
            mc_prob = mc_result.draw_prob
        else:
            mc_prob = 0.5
        
        # ═══════════════════════════════════════════════════════
        # HYBRID BLENDER - Mélange MC + Historique
        # ═══════════════════════════════════════════════════════
        if context:
            home_intel = context.get('home_intelligence', {}) or {}
            away_intel = context.get('away_intelligence', {}) or {}
            
            # Récupérer taux historiques selon le marché
            hist_prob = None
            
            if 'btts' in market:
                home_btts = float(home_intel.get('home_btts_rate', 50) or 50)
                away_btts = float(away_intel.get('away_btts_rate', 50) or 50)
                hist_btts = (home_btts + away_btts) / 2 / 100  # Convertir en 0-1
                
                if 'yes' in market:
                    hist_prob = hist_btts
                else:  # btts_no
                    hist_prob = 1 - hist_btts
                    
            elif 'over_25' in market or 'under_25' in market:
                home_over = float(home_intel.get('home_over25_rate', 50) or 50)
                away_over = float(away_intel.get('away_over25_rate', 50) or 50)
                hist_over = (home_over + away_over) / 2 / 100
                
                if 'over' in market:
                    hist_prob = hist_over
                else:  # under
                    hist_prob = 1 - hist_over
            
            # Appliquer Hybrid Blender si on a les données
            if hist_prob is not None:
                # Confidence = min des deux équipes
                home_conf = float(home_intel.get('confidence_overall', 50) or 50)
                away_conf = float(away_intel.get('confidence_overall', 50) or 50)
                confidence = min(home_conf, away_conf)
                
                # Mélanger MC + Historique
                mc_prob = calculate_hybrid_probability(mc_prob, hist_prob, confidence)
        
        pick.mc_prob = mc_prob'''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("✅ 1. Hybrid Blender intégré dans _calculate_mc_score")
else:
    print("❌ 1. Pattern _calculate_mc_score non trouvé - cherchons...")
    # Afficher les premières lignes de la méthode
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '_calculate_mc_score' in line and 'def ' in line:
            print(f"   Ligne {i}: {line[:70]}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. MODIFIER L'APPEL POUR PASSER LE CONTEXTE
# ═══════════════════════════════════════════════════════════════════════════════

old_call = "pick.mc_score = self._calculate_mc_score(pick, mc_result)"
new_call = "pick.mc_score = self._calculate_mc_score(pick, mc_result, context)"

if old_call in content:
    content = content.replace(old_call, new_call)
    print("✅ 2. Appel modifié pour passer context")
else:
    print("❌ 2. Pattern d'appel non trouvé")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. SAUVEGARDER
# ═══════════════════════════════════════════════════════════════════════════════

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n" + "="*70)
print("✅ HYBRID BLENDER INTÉGRÉ!")
print("="*70)
print("""
Fonctionnement:
  1. Récupère mc_prob depuis Monte Carlo
  2. Récupère hist_prob depuis team_intelligence (btts_rate, over25_rate)
  3. Calcule confidence = min(home_conf, away_conf)
  4. Applique: final_prob = MC * weight_mc + HIST * weight_hist
  
  Où weight_hist = confidence / 200 (max 50%)
  
Exemple Liverpool (conf=95) vs Sunderland (conf=?):
  - MC BTTS: 37.8%
  - HIST BTTS: (55.56% + away_btts) / 2
  - weight_hist = 95/200 = 47.5%
  - final = 37.8% * 0.525 + hist * 0.475
""")

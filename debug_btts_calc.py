#!/usr/bin/env python3
"""Debug: Pourquoi BTTS YES est à 48.5%?"""
import math

print("="*70)
print("DEBUG BTTS - CALCUL xG")
print("="*70)

# Données actuelles
liv_home_scored = 1.67
liv_home_conceded = 1.33
sun_away_scored = 0.50
sun_away_conceded = 1.00

# xG Formula: attack * 0.6 + defense * 0.4
liv_xg = (liv_home_scored * 0.6) + (sun_away_conceded * 0.4)
sun_xg = (sun_away_scored * 0.6) + (liv_home_conceded * 0.4)

print(f"\n1. xG BRUT:")
print(f"   Liverpool xG = ({liv_home_scored} × 0.6) + ({sun_away_conceded} × 0.4) = {liv_xg:.2f}")
print(f"   Sunderland xG = ({sun_away_scored} × 0.6) + ({liv_home_conceded} × 0.4) = {sun_xg:.2f}")

# Tier adjustment (Liverpool A vs Sunderland C = diff 2)
liv_xg_adj = liv_xg * 1.25
sun_xg_adj = sun_xg * 0.75

print(f"\n2. APRÈS TIER ADJUSTMENT (Liverpool ×1.25, Sunderland ×0.75):")
print(f"   Liverpool xG = {liv_xg_adj:.2f}")
print(f"   Sunderland xG = {sun_xg_adj:.2f}")

# Poisson
def p_score(xg):
    return 1 - math.exp(-xg)

p_liv = p_score(liv_xg_adj)
p_sun = p_score(sun_xg_adj)

print(f"\n3. PROBABILITÉS DE MARQUER (Poisson):")
print(f"   P(Liverpool marque) = 1 - e^(-{liv_xg_adj:.2f}) = {p_liv*100:.1f}%")
print(f"   P(Sunderland marque) = 1 - e^(-{sun_xg_adj:.2f}) = {p_sun*100:.1f}%")

btts_yes = p_liv * p_sun
btts_no = 1 - btts_yes

print(f"\n4. BTTS:")
print(f"   BTTS YES = {p_liv:.3f} × {p_sun:.3f} = {btts_yes*100:.1f}%")
print(f"   BTTS NO = {btts_no*100:.1f}%")

# Problème identifié
print(f"\n" + "="*70)
print("PROBLÈME IDENTIFIÉ:")
print("="*70)
print(f"   Liverpool conceded = {liv_home_conceded} est TROP ÉLEVÉ!")
print(f"   → Gonfle artificiellement le xG de Sunderland")
print(f"\n   Si Liverpool conceded = 0.50 (réaliste pour top équipe):")
sun_xg_real = (sun_away_scored * 0.6) + (0.50 * 0.4)
sun_xg_real_adj = sun_xg_real * 0.75
p_sun_real = p_score(sun_xg_real_adj)
btts_yes_real = p_liv * p_sun_real
print(f"   Sunderland xG = {sun_xg_real_adj:.2f}")
print(f"   P(Sunderland marque) = {p_sun_real*100:.1f}%")
print(f"   BTTS YES = {btts_yes_real*100:.1f}%")
print(f"   BTTS NO = {(1-btts_yes_real)*100:.1f}%")

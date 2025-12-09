#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE RESPONSE MODEL (DRM) V3.0                                           ║
║  Transformation des données brutes en ADN défensif personnalisé              ║
║  Quant Institutionnel - Chaque équipe = Fingerprint unique                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

DIMENSIONS DE RÉSISTANCE (7 axes):
1. resist_global      : Force défensive globale
2. resist_aerial      : Résistance aux attaques aériennes (corners, 6 yards)
3. resist_longshot    : Résistance aux tirs de loin
4. resist_open_play   : Résistance en jeu ouvert
5. resist_early       : Résistance en début de match (0-30 min)
6. resist_late        : Résistance en fin de match (60-90 min)
7. resist_chaos       : Résistance au chaos (penalties, erreurs)

BONUS DIMENSIONS (3 axes contextuels):
8. resist_home        : Force défensive à domicile
9. resist_away        : Force défensive à l'extérieur
10. resist_set_piece  : Résistance globale sur coups de pied arrêtés
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Paths
DATA_DIR = Path('/home/Mon_ps/data/defense_dna')
INPUT_FILE = DATA_DIR / 'team_defense_dna_2025.json'
OUTPUT_FILE = DATA_DIR / 'team_defense_dna_v3.json'
REPORT_FILE = DATA_DIR / 'DRM_V3_REPORT.txt'

def load_data() -> List[Dict]:
    """Charge les données brutes"""
    with open(INPUT_FILE, 'r') as f:
        return json.load(f)

def normalize_min_max(values: List[float], inverse: bool = True) -> List[float]:
    """
    Normalise les valeurs entre 0 et 100
    inverse=True : plus la valeur brute est BASSE, plus le score est HAUT
    (car xGA bas = bonne défense = resist élevé)
    """
    if not values:
        return []
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return [50.0] * len(values)
    
    normalized = []
    for v in values:
        if inverse:
            # Inverse: xGA bas → score haut
            score = (1 - (v - min_val) / (max_val - min_val)) * 100
        else:
            # Direct: valeur haute → score haut
            score = ((v - min_val) / (max_val - min_val)) * 100
        normalized.append(round(score, 1))
    
    return normalized

def calculate_percentile(value: float, all_values: List[float], inverse: bool = True) -> int:
    """
    Calcule le percentile d'une valeur dans une distribution
    inverse=True : plus la valeur brute est BASSE, plus le percentile est HAUT
    """
    if inverse:
        # Compter combien de valeurs sont >= à la valeur actuelle
        count = sum(1 for v in all_values if v >= value)
    else:
        # Compter combien de valeurs sont <= à la valeur actuelle
        count = sum(1 for v in all_values if v <= value)
    
    return int((count / len(all_values)) * 100)

def calculate_resist_scores(teams: List[Dict]) -> List[Dict]:
    """
    Calcule les 10 scores de résistance pour chaque équipe
    """
    # Extraire les valeurs brutes pour normalisation
    raw_metrics = {
        'xga_per_90': [t.get('xga_per_90', 0) for t in teams],
        'xga_aerial': [t.get('xga_corner', 0) + t.get('xga_six_yard', 0) + t.get('xga_set_piece', 0) for t in teams],
        'xga_outside_box': [t.get('xga_outside_box', 0) for t in teams],
        'xga_open_play': [t.get('xga_open_play', 0) for t in teams],
        'xga_early': [t.get('xga_0_15', 0) + t.get('xga_16_30', 0) for t in teams],
        'xga_late': [t.get('xga_61_75', 0) + t.get('xga_76_90', 0) for t in teams],
        'xga_chaos': [t.get('xga_penalty', 0) for t in teams],
        'xga_home': [t.get('xga_per_90_home', 0) for t in teams],
        'xga_away': [t.get('xga_per_90_away', 0) for t in teams],
        'xga_set_piece_total': [t.get('xga_set_piece_total', 0) for t in teams],
        # Métriques additionnelles pour l'analyse
        'xga_mid': [t.get('xga_31_45', 0) + t.get('xga_46_60', 0) for t in teams],
        'xga_penalty_area': [t.get('xga_penalty_area', 0) for t in teams],
        'cs_pct': [t.get('cs_pct', 0) for t in teams],
    }
    
    # Normaliser chaque métrique (inverse car xGA bas = bon)
    normalized = {}
    for key, values in raw_metrics.items():
        if key == 'cs_pct':
            # Clean sheet % : plus c'est haut, mieux c'est (pas inverse)
            normalized[key] = normalize_min_max(values, inverse=False)
        else:
            normalized[key] = normalize_min_max(values, inverse=True)
    
    # Calculer les scores composites pour chaque équipe
    enriched_teams = []
    
    for i, team in enumerate(teams):
        enriched = team.copy()
        
        # ═══════════════════════════════════════════════════════════════
        # SCORES DE RÉSISTANCE (0-100, 100 = impénétrable)
        # ═══════════════════════════════════════════════════════════════
        
        # 1. RESIST_GLOBAL: Combinaison xGA/90 + CS%
        resist_global = (normalized['xga_per_90'][i] * 0.7 + normalized['cs_pct'][i] * 0.3)
        enriched['resist_global'] = round(resist_global, 1)
        
        # 2. RESIST_AERIAL: Corners + Six Yard + Set Pieces
        enriched['resist_aerial'] = round(normalized['xga_aerial'][i], 1)
        
        # 3. RESIST_LONGSHOT: Outside box
        enriched['resist_longshot'] = round(normalized['xga_outside_box'][i], 1)
        
        # 4. RESIST_OPEN_PLAY: Jeu ouvert
        enriched['resist_open_play'] = round(normalized['xga_open_play'][i], 1)
        
        # 5. RESIST_EARLY: 0-30 min
        enriched['resist_early'] = round(normalized['xga_early'][i], 1)
        
        # 6. RESIST_LATE: 60-90 min
        enriched['resist_late'] = round(normalized['xga_late'][i], 1)
        
        # 7. RESIST_CHAOS: Penalties concédés
        enriched['resist_chaos'] = round(normalized['xga_chaos'][i], 1)
        
        # 8. RESIST_HOME: Défense à domicile
        enriched['resist_home'] = round(normalized['xga_home'][i], 1)
        
        # 9. RESIST_AWAY: Défense à l'extérieur
        enriched['resist_away'] = round(normalized['xga_away'][i], 1)
        
        # 10. RESIST_SET_PIECE: Coups de pied arrêtés globaux
        enriched['resist_set_piece'] = round(normalized['xga_set_piece_total'][i], 1)
        
        # ═══════════════════════════════════════════════════════════════
        # DNA VECTOR (pour ML)
        # ═══════════════════════════════════════════════════════════════
        
        enriched['dna_vector'] = [
            enriched['resist_global'],
            enriched['resist_aerial'],
            enriched['resist_longshot'],
            enriched['resist_open_play'],
            enriched['resist_early'],
            enriched['resist_late'],
            enriched['resist_chaos'],
            enriched['resist_home'],
            enriched['resist_away'],
            enriched['resist_set_piece']
        ]
        
        enriched_teams.append(enriched)
    
    return enriched_teams

def calculate_percentiles(teams: List[Dict]) -> List[Dict]:
    """
    Calcule les percentiles pour chaque dimension
    """
    resist_keys = [
        'resist_global', 'resist_aerial', 'resist_longshot', 'resist_open_play',
        'resist_early', 'resist_late', 'resist_chaos', 'resist_home', 
        'resist_away', 'resist_set_piece'
    ]
    
    # Collecter toutes les valeurs par dimension
    all_values = {key: [t[key] for t in teams] for key in resist_keys}
    
    for team in teams:
        team['percentiles'] = {}
        for key in resist_keys:
            # Plus le score est haut, plus le percentile est haut (pas inverse)
            pct = calculate_percentile(team[key], all_values[key], inverse=False)
            team['percentiles'][key.replace('resist_', '')] = pct
        
        # Score composite percentile
        avg_pct = sum(team['percentiles'].values()) / len(team['percentiles'])
        team['percentiles']['composite'] = int(avg_pct)
    
    return teams

def generate_tags(teams: List[Dict]) -> List[Dict]:
    """
    Génère les tags automatiques basés sur les percentiles et scores
    """
    for team in teams:
        tags = []
        weaknesses = []
        strengths = []
        
        pct = team['percentiles']
        
        # ═══════════════════════════════════════════════════════════════
        # TAGS PRIMAIRES (Profil global)
        # ═══════════════════════════════════════════════════════════════
        
        if pct['global'] >= 90:
            tags.append('FORTRESS')
        elif pct['global'] >= 75:
            tags.append('SOLID')
        elif pct['global'] >= 40:
            tags.append('AVERAGE')
        elif pct['global'] >= 20:
            tags.append('LEAKY')
        else:
            tags.append('SIEVE')
        
        # ═══════════════════════════════════════════════════════════════
        # TAGS TEMPORELS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['early'] <= 25:
            tags.append('SLOW_STARTER')
            weaknesses.append('early_game')
        elif pct['early'] >= 80:
            strengths.append('early_game')
        
        if pct['late'] <= 25:
            tags.append('LATE_COLLAPSER')
            weaknesses.append('late_game')
        elif pct['late'] >= 80:
            tags.append('LATE_SOLID')
            strengths.append('late_game')
        
        # ═══════════════════════════════════════════════════════════════
        # TAGS SITUATIONNELS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['aerial'] <= 25:
            tags.append('AERIAL_WEAK')
            weaknesses.append('aerial')
        elif pct['aerial'] >= 80:
            tags.append('AERIAL_DOMINANT')
            strengths.append('aerial')
        
        if pct['set_piece'] <= 25:
            tags.append('SP_VULNERABLE')
            weaknesses.append('set_pieces')
        elif pct['set_piece'] >= 80:
            strengths.append('set_pieces')
        
        if pct['longshot'] <= 25:
            tags.append('LONGSHOT_VULNERABLE')
            weaknesses.append('longshots')
        elif pct['longshot'] >= 80:
            strengths.append('longshots')
        
        if pct['chaos'] <= 25:
            tags.append('CHAOS_PRONE')
            weaknesses.append('discipline')
        elif pct['chaos'] >= 80:
            tags.append('COMPOSED')
            strengths.append('discipline')
        
        # ═══════════════════════════════════════════════════════════════
        # TAGS HOME/AWAY
        # ═══════════════════════════════════════════════════════════════
        
        home_away_diff = pct['home'] - pct['away']
        
        if home_away_diff >= 30:
            tags.append('HOME_FORTRESS')
            strengths.append('home')
            weaknesses.append('away')
        elif home_away_diff <= -30:
            tags.append('ROAD_WARRIORS')
            strengths.append('away')
            weaknesses.append('home')
        
        if pct['away'] <= 20:
            tags.append('AWAY_DISASTER')
        
        if pct['home'] <= 20:
            tags.append('HOME_WEAK')
        
        # ═══════════════════════════════════════════════════════════════
        # TAGS COMBINÉS (Patterns)
        # ═══════════════════════════════════════════════════════════════
        
        # Pattern: Bon globalement mais avec une faille critique
        if pct['global'] >= 70 and min(pct.values()) <= 30:
            tags.append('HIDDEN_WEAKNESS')
        
        # Pattern: Mauvais globalement mais résiste bien quelque part
        if pct['global'] <= 30 and max([pct['early'], pct['late'], pct['aerial']]) >= 60:
            tags.append('PARTIAL_RESIST')
        
        # Pattern: Très équilibré
        values = [pct['early'], pct['late'], pct['aerial'], pct['open_play']]
        if max(values) - min(values) <= 20:
            tags.append('BALANCED')
        
        team['tags'] = tags
        team['weaknesses'] = list(set(weaknesses))
        team['strengths'] = list(set(strengths))
    
    return teams

def generate_betting_insights(teams: List[Dict]) -> List[Dict]:
    """
    Génère des insights betting automatiques basés sur le profil
    """
    for team in teams:
        insights = {
            'back': [],   # Paris à prendre
            'fade': [],   # Paris à éviter
            'value': [],  # Paris à valeur potentielle
        }
        
        pct = team['percentiles']
        
        # ═══════════════════════════════════════════════════════════════
        # FIRST GOALSCORER INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['early'] <= 30:
            insights['back'].append({
                'market': 'First Goalscorer',
                'reason': f"SLOW_STARTER - Early resist {pct['early']}th pct",
                'confidence': 'HIGH' if pct['early'] <= 20 else 'MEDIUM'
            })
        elif pct['early'] >= 80:
            insights['fade'].append({
                'market': 'First Goalscorer',
                'reason': f"Strong early defense - {pct['early']}th pct",
                'confidence': 'HIGH'
            })
        
        # ═══════════════════════════════════════════════════════════════
        # LAST GOALSCORER INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['late'] <= 30:
            insights['back'].append({
                'market': 'Last Goalscorer',
                'reason': f"LATE_COLLAPSER - Late resist {pct['late']}th pct",
                'confidence': 'HIGH' if pct['late'] <= 20 else 'MEDIUM'
            })
        elif pct['late'] >= 80:
            insights['fade'].append({
                'market': 'Last Goalscorer',
                'reason': f"Strong late defense - {pct['late']}th pct",
                'confidence': 'HIGH'
            })
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER/AERIAL INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['aerial'] <= 30:
            insights['back'].append({
                'market': 'Header Scorer / Corner Goals',
                'reason': f"AERIAL_WEAK - Aerial resist {pct['aerial']}th pct",
                'confidence': 'HIGH' if pct['aerial'] <= 20 else 'MEDIUM'
            })
        
        if pct['set_piece'] <= 30:
            insights['back'].append({
                'market': 'Set Piece Goal',
                'reason': f"SP_VULNERABLE - Set piece resist {pct['set_piece']}th pct",
                'confidence': 'HIGH' if pct['set_piece'] <= 20 else 'MEDIUM'
            })
        
        # ═══════════════════════════════════════════════════════════════
        # ANYTIME SCORER INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['global'] <= 20:
            insights['back'].append({
                'market': 'Anytime Scorer (Any attacker)',
                'reason': f"SIEVE defense - Global resist {pct['global']}th pct",
                'confidence': 'HIGH'
            })
        elif pct['global'] >= 85:
            insights['fade'].append({
                'market': 'Anytime Scorer (vs weak attackers)',
                'reason': f"FORTRESS defense - Global resist {pct['global']}th pct",
                'confidence': 'HIGH'
            })
        
        # ═══════════════════════════════════════════════════════════════
        # HOME/AWAY SPECIFIC INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['away'] <= 25:
            insights['back'].append({
                'market': 'Home Team Goals / Home Attacker Scorer',
                'reason': f"AWAY_DISASTER - Away resist {pct['away']}th pct",
                'confidence': 'HIGH' if pct['away'] <= 15 else 'MEDIUM'
            })
        
        if pct['home'] <= 25:
            insights['value'].append({
                'market': 'Away Team Goals',
                'reason': f"HOME_WEAK - Home resist {pct['home']}th pct",
                'confidence': 'MEDIUM'
            })
        
        # ═══════════════════════════════════════════════════════════════
        # CHAOS/PENALTY INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['chaos'] <= 25:
            insights['back'].append({
                'market': 'Penalty Scored / Penalty Awarded',
                'reason': f"CHAOS_PRONE - Chaos resist {pct['chaos']}th pct",
                'confidence': 'MEDIUM'
            })
        
        # ═══════════════════════════════════════════════════════════════
        # OVER/UNDER INSIGHTS
        # ═══════════════════════════════════════════════════════════════
        
        if pct['global'] <= 25 and pct['open_play'] <= 30:
            insights['back'].append({
                'market': 'Over 2.5 Goals',
                'reason': f"Weak in open play ({pct['open_play']}th pct) + overall ({pct['global']}th pct)",
                'confidence': 'MEDIUM'
            })
        
        team['betting_insights'] = insights
    
    return teams

def generate_matchup_multipliers(teams: List[Dict]) -> List[Dict]:
    """
    Génère les multiplicateurs de friction pour différents types d'attaquants
    """
    for team in teams:
        pct = team['percentiles']
        
        # Multiplicateurs: < 1.0 = avantage attaquant, > 1.0 = avantage défense
        multipliers = {}
        
        # vs EARLY_BIRD attacker
        multipliers['vs_early_bird'] = round(pct['early'] / 50, 2)  # 50 = neutral
        
        # vs DIESEL/CLUTCH attacker
        multipliers['vs_diesel'] = round(pct['late'] / 50, 2)
        
        # vs HEADER_SPECIALIST
        multipliers['vs_header'] = round(pct['aerial'] / 50, 2)
        
        # vs SET_PIECE_THREAT
        multipliers['vs_set_piece'] = round(pct['set_piece'] / 50, 2)
        
        # vs LONGSHOT_SPECIALIST
        multipliers['vs_longshot'] = round(pct['longshot'] / 50, 2)
        
        # vs CLINICAL/PENALTY_TAKER
        multipliers['vs_clinical'] = round(pct['chaos'] / 50, 2)
        
        # vs HOME_SPECIALIST (quand cette défense joue à l'extérieur)
        multipliers['vs_home_specialist'] = round(pct['away'] / 50, 2)
        
        # vs AWAY_SPECIALIST (quand cette défense joue à domicile)
        multipliers['vs_away_specialist'] = round(pct['home'] / 50, 2)
        
        team['friction_multipliers'] = multipliers
    
    return teams

def calculate_vulnerability_score(team: Dict) -> float:
    """
    Calcule un score de vulnérabilité globale (0-100, 100 = très vulnérable)
    """
    pct = team['percentiles']
    
    # Pondération des faiblesses
    weights = {
        'global': 0.25,
        'early': 0.15,
        'late': 0.15,
        'aerial': 0.15,
        'open_play': 0.10,
        'set_piece': 0.10,
        'chaos': 0.10,
    }
    
    vulnerability = 0
    for key, weight in weights.items():
        # Inverser: percentile bas = vulnérabilité haute
        vulnerability += (100 - pct[key]) * weight
    
    return round(vulnerability, 1)

def main():
    print("=" * 80)
    print("🧬 DEFENSE RESPONSE MODEL (DRM) V3.0")
    print("=" * 80)
    
    # 1. Charger les données
    print("\n📂 Chargement des données...")
    teams = load_data()
    print(f"   ✅ {len(teams)} équipes chargées")
    
    # 2. Calculer les scores de résistance
    print("\n🔬 Calcul des scores de résistance...")
    teams = calculate_resist_scores(teams)
    print("   ✅ 10 dimensions calculées")
    
    # 3. Calculer les percentiles
    print("\n📊 Calcul des percentiles...")
    teams = calculate_percentiles(teams)
    print("   ✅ Percentiles calculés")
    
    # 4. Générer les tags
    print("\n🏷️ Génération des tags automatiques...")
    teams = generate_tags(teams)
    print("   ✅ Tags générés")
    
    # 5. Générer les insights betting
    print("\n🎯 Génération des insights betting...")
    teams = generate_betting_insights(teams)
    print("   ✅ Insights générés")
    
    # 6. Générer les multiplicateurs de friction
    print("\n⚡ Génération des multiplicateurs de friction...")
    teams = generate_matchup_multipliers(teams)
    print("   ✅ Multiplicateurs générés")
    
    # 7. Calculer le score de vulnérabilité
    print("\n🎯 Calcul des scores de vulnérabilité...")
    for team in teams:
        team['vulnerability_score'] = calculate_vulnerability_score(team)
    print("   ✅ Scores calculés")
    
    # 8. Sauvegarder
    print("\n💾 Sauvegarde...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(teams, f, indent=2)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # ═══════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("📊 RAPPORT DRM V3.0")
    print("=" * 80)
    
    # Top FORTRESS
    print("\n🏰 TOP 10 FORTRESS (Global Resist):")
    sorted_by_global = sorted(teams, key=lambda x: x['resist_global'], reverse=True)
    for i, t in enumerate(sorted_by_global[:10], 1):
        print(f"   {i:2}. {t['team_name']:25} | Resist: {t['resist_global']:5.1f} | "
              f"Pct: {t['percentiles']['global']:3}th | Tags: {', '.join(t['tags'][:3])}")
    
    # Top SIEVE
    print("\n🕳️ TOP 10 SIEVE (Plus vulnérables):")
    sorted_by_vuln = sorted(teams, key=lambda x: x['vulnerability_score'], reverse=True)
    for i, t in enumerate(sorted_by_vuln[:10], 1):
        print(f"   {i:2}. {t['team_name']:25} | Vuln: {t['vulnerability_score']:5.1f} | "
              f"Tags: {', '.join(t['tags'][:3])}")
    
    # SLOW_STARTER
    print("\n⏰ SLOW_STARTERS (Back First Goalscorer):")
    slow_starters = [t for t in teams if 'SLOW_STARTER' in t['tags']]
    slow_starters.sort(key=lambda x: x['percentiles']['early'])
    for t in slow_starters[:10]:
        print(f"   • {t['team_name']:25} | Early Pct: {t['percentiles']['early']:3}th | "
              f"Resist Early: {t['resist_early']:.1f}")
    
    # LATE_COLLAPSER
    print("\n🌙 LATE_COLLAPSERS (Back Last Goalscorer):")
    late_collapsers = [t for t in teams if 'LATE_COLLAPSER' in t['tags']]
    late_collapsers.sort(key=lambda x: x['percentiles']['late'])
    for t in late_collapsers[:10]:
        print(f"   • {t['team_name']:25} | Late Pct: {t['percentiles']['late']:3}th | "
              f"Resist Late: {t['resist_late']:.1f}")
    
    # AERIAL_WEAK
    print("\n🎯 AERIAL_WEAK (Back Header Specialists):")
    aerial_weak = [t for t in teams if 'AERIAL_WEAK' in t['tags']]
    aerial_weak.sort(key=lambda x: x['percentiles']['aerial'])
    for t in aerial_weak[:10]:
        print(f"   • {t['team_name']:25} | Aerial Pct: {t['percentiles']['aerial']:3}th | "
              f"Resist Aerial: {t['resist_aerial']:.1f}")
    
    # HIDDEN_WEAKNESS (Paradoxes)
    print("\n🔍 HIDDEN_WEAKNESS (Fort globalement mais faille cachée):")
    hidden = [t for t in teams if 'HIDDEN_WEAKNESS' in t['tags']]
    for t in hidden:
        weakest = min(t['percentiles'].items(), key=lambda x: x[1] if x[0] != 'composite' else 100)
        print(f"   • {t['team_name']:25} | Global: {t['percentiles']['global']:3}th | "
              f"Weakness: {weakest[0]} ({weakest[1]}th pct)")
    
    # Exemple détaillé
    print("\n" + "=" * 80)
    print("📋 EXEMPLE DÉTAILLÉ: ARSENAL")
    print("=" * 80)
    arsenal = next((t for t in teams if 'Arsenal' in t['team_name']), None)
    if arsenal:
        print(f"""
   TEAM: {arsenal['team_name']}
   
   DNA VECTOR: {arsenal['dna_vector']}
   
   SCORES DE RÉSISTANCE:
   ├── Global:     {arsenal['resist_global']:5.1f} ({arsenal['percentiles']['global']}th pct)
   ├── Aerial:     {arsenal['resist_aerial']:5.1f} ({arsenal['percentiles']['aerial']}th pct)
   ├── Longshot:   {arsenal['resist_longshot']:5.1f} ({arsenal['percentiles']['longshot']}th pct)
   ├── Open Play:  {arsenal['resist_open_play']:5.1f} ({arsenal['percentiles']['open_play']}th pct)
   ├── Early:      {arsenal['resist_early']:5.1f} ({arsenal['percentiles']['early']}th pct)
   ├── Late:       {arsenal['resist_late']:5.1f} ({arsenal['percentiles']['late']}th pct)
   ├── Chaos:      {arsenal['resist_chaos']:5.1f} ({arsenal['percentiles']['chaos']}th pct)
   ├── Home:       {arsenal['resist_home']:5.1f} ({arsenal['percentiles']['home']}th pct)
   ├── Away:       {arsenal['resist_away']:5.1f} ({arsenal['percentiles']['away']}th pct)
   └── Set Piece:  {arsenal['resist_set_piece']:5.1f} ({arsenal['percentiles']['set_piece']}th pct)
   
   VULNERABILITY SCORE: {arsenal['vulnerability_score']}/100
   
   TAGS: {arsenal['tags']}
   WEAKNESSES: {arsenal['weaknesses']}
   STRENGTHS: {arsenal['strengths']}
   
   FRICTION MULTIPLIERS:
   ├── vs Early Bird:    {arsenal['friction_multipliers']['vs_early_bird']}x
   ├── vs Diesel:        {arsenal['friction_multipliers']['vs_diesel']}x
   ├── vs Header:        {arsenal['friction_multipliers']['vs_header']}x
   └── vs Set Piece:     {arsenal['friction_multipliers']['vs_set_piece']}x
   
   BETTING INSIGHTS:
   BACK: {[i['market'] for i in arsenal['betting_insights']['back']]}
   FADE: {[i['market'] for i in arsenal['betting_insights']['fade']]}
""")
    
    # Stats globales
    print("\n" + "=" * 80)
    print("📊 DISTRIBUTION DES TAGS")
    print("=" * 80)
    
    all_tags = {}
    for t in teams:
        for tag in t['tags']:
            all_tags[tag] = all_tags.get(tag, 0) + 1
    
    for tag, count in sorted(all_tags.items(), key=lambda x: -x[1]):
        print(f"   {tag:25}: {count:3} équipes")
    
    print("\n" + "=" * 80)
    print(f"✅ DRM V3.0 COMPLET - {len(teams)} équipes enrichies")
    print(f"📁 Fichier: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()

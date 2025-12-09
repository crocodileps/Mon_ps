#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE RESPONSE MODEL (DRM) V5.1 - CORRECTIONS COMPLÈTES                   ║
║                                                                              ║
║  CORRECTIONS:                                                                ║
║  1. TIMING DUAL: resist_early_absolute + resist_early_proportion             ║
║  2. EDGE CATEGORIES: WEAK (<2%), MEDIUM (2-4%), STRONG (>4%)                 ║
║  3. MARKET-SPECIFIC METRICS: First/Last GS = PROPORTION, Anytime = ABSOLUTE  ║
║  4. MATCHUP GUIDE CORRIGÉ selon le type de marché                            ║
║  5. VALIDATION Barcelona et autres anomalies                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter
from scipy import stats

def convert_numpy(obj):
    """Convertit récursivement les types numpy en types Python natifs"""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(item) for item in obj]
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

# Paths
DATA_DIR = Path('/home/Mon_ps/data/defense_dna')
INPUT_RAW = DATA_DIR / 'team_defense_dna_2025.json'  # Données brutes avec %
INPUT_V3 = DATA_DIR / 'team_defense_dna_v3.json'     # Données avec percentiles V3
OUTPUT_FILE = DATA_DIR / 'team_defense_dna_v5_1_corrected.json'

# Dimensions avec leurs codes
DIMENSIONS = {
    'global': {'name': 'Défense Globale', 'code': 'GLO'},
    'aerial': {'name': 'Duels Aériens', 'code': 'AER'},
    'longshot': {'name': 'Tirs de Loin', 'code': 'LNG'},
    'open_play': {'name': 'Jeu Ouvert', 'code': 'OPN'},
    'early_abs': {'name': 'Début Match (Absolu)', 'code': 'ERL_ABS'},
    'early_prop': {'name': 'Début Match (Proportion)', 'code': 'ERL_PRO'},
    'late_abs': {'name': 'Fin Match (Absolu)', 'code': 'LAT_ABS'},
    'late_prop': {'name': 'Fin Match (Proportion)', 'code': 'LAT_PRO'},
    'chaos': {'name': 'Discipline', 'code': 'CHA'},
    'home': {'name': 'À Domicile', 'code': 'HOM'},
    'away': {'name': 'À l\'Extérieur', 'code': 'AWY'},
    'set_piece': {'name': 'Coups de Pied Arrêtés', 'code': 'STP'}
}

# Niveaux de défense
DEFENSE_LEVELS = {
    (90, 101): {'name': 'Forteresse', 'code': 'FRT', 'emoji': '🏰'},
    (75, 90): {'name': 'Muraille', 'code': 'MUR', 'emoji': '🧱'},
    (60, 75): {'name': 'Bouclier', 'code': 'BOU', 'emoji': '🛡️'},
    (45, 60): {'name': 'Ligne', 'code': 'LGN', 'emoji': '📏'},
    (30, 45): {'name': 'Passoire', 'code': 'PAS', 'emoji': '🕳️'},
    (0, 30): {'name': 'Chaos', 'code': 'CHA', 'emoji': '💥'}
}

# Descripteurs
STRENGTH_DESCRIPTORS = {
    'global': {'strong': 'Impénétrable', 'weak': 'Perméable'},
    'aerial': {'strong': 'Dominante en l\'Air', 'weak': 'Vulnérable aux Têtes'},
    'longshot': {'strong': 'Anti-Frappe', 'weak': 'Perméable de Loin'},
    'open_play': {'strong': 'Hermétique', 'weak': 'Ouverte'},
    'early_abs': {'strong': 'Solide au Départ', 'weak': 'Fragile au Départ'},
    'early_prop': {'strong': 'Équilibrée Timing', 'weak': 'Slow Starter'},
    'late_abs': {'strong': 'Solide en Fin', 'weak': 'Fragile en Fin'},
    'late_prop': {'strong': 'Stable Timing', 'weak': 'Late Collapser'},
    'chaos': {'strong': 'Disciplinée', 'weak': 'Indisciplinée'},
    'home': {'strong': 'Imprenable à Dom.', 'weak': 'Fragile à Dom.'},
    'away': {'strong': 'Solide en Dépl.', 'weak': 'Fragile en Dépl.'},
    'set_piece': {'strong': 'Solide sur CPA', 'weak': 'Vulnérable sur CPA'}
}

def load_data():
    """Charge les données brutes et V3"""
    with open(INPUT_RAW, 'r') as f:
        raw_teams = json.load(f)
    with open(INPUT_V3, 'r') as f:
        v3_teams = json.load(f)
    
    # Créer un dictionnaire pour accès rapide
    raw_dict = {t['team_name']: t for t in raw_teams}
    
    return v3_teams, raw_dict

def calculate_proportion_percentiles(teams: List[Dict], raw_dict: Dict) -> Dict[str, Dict]:
    """
    Calcule les percentiles PROPORTION pour timing
    
    ABSOLU: xGA total en 0-30 min (peu = bon)
    PROPORTION: % du xGA total en 0-30 min (élevé = SLOW_STARTER = mauvais)
    """
    
    # Collecter les données de proportion
    early_proportions = []  # xga_first_15_pct + approximation 16-30
    late_proportions = []   # xga_last_15_pct
    
    for team in teams:
        team_name = team['team_name']
        raw = raw_dict.get(team_name, {})
        
        # Proportion early (0-30 min)
        # On utilise xga_1h_pct / 2 comme approximation ou xga_first_15_pct * 2
        first_15_pct = raw.get('xga_first_15_pct', 0)
        first_half_pct = raw.get('xga_1h_pct', 50)
        # Approximation: 0-30 min ≈ first_half_pct (on prend la 1H comme proxy)
        early_prop = first_half_pct
        
        # Proportion late (60-90 min)
        last_15_pct = raw.get('xga_last_15_pct', 0)
        second_half_pct = raw.get('xga_2h_pct', 50)
        late_prop = second_half_pct
        
        early_proportions.append((team_name, early_prop, first_15_pct))
        late_proportions.append((team_name, late_prop, last_15_pct))
    
    # Calculer les percentiles (inversés: haut % = mauvais = bas percentile)
    early_values = [x[1] for x in early_proportions]
    late_values = [x[1] for x in late_proportions]
    
    proportion_pcts = {}
    
    for team_name, early_prop, first_15 in early_proportions:
        # Percentile inversé: plus la proportion est haute, plus c'est mauvais
        # Donc on fait 100 - percentile
        early_pct = 100 - stats.percentileofscore(early_values, early_prop, kind='rank')
        proportion_pcts[team_name] = {
            'early_prop_raw': round(early_prop, 1),
            'early_prop_pct': round(early_pct, 0),
            'first_15_raw': round(first_15, 1)
        }
    
    for team_name, late_prop, last_15 in late_proportions:
        late_pct = 100 - stats.percentileofscore(late_values, late_prop, kind='rank')
        proportion_pcts[team_name]['late_prop_raw'] = round(late_prop, 1)
        proportion_pcts[team_name]['late_prop_pct'] = round(late_pct, 0)
        proportion_pcts[team_name]['last_15_raw'] = round(last_15, 1)
    
    return proportion_pcts

def get_defense_level(global_pct):
    for (low, high), level in DEFENSE_LEVELS.items():
        if low <= global_pct < high:
            return level
    return DEFENSE_LEVELS[(0, 30)]

def generate_fingerprint_code(pct: Dict) -> str:
    """Génère le code fingerprint avec les nouvelles dimensions"""
    parts = ['DEF']
    dims = ['global', 'aerial', 'longshot', 'open_play', 'early_abs', 'early_prop', 
            'late_abs', 'late_prop', 'chaos', 'home', 'away', 'set_piece']
    for dim in dims:
        parts.append(str(int(pct.get(dim, 50))))
    return '-'.join(parts)

def generate_compact_fingerprint(pct: Dict) -> str:
    parts = []
    dim_codes = {
        'global': 'GLO', 'aerial': 'AER', 'longshot': 'LNG', 'open_play': 'OPN',
        'early_abs': 'ERL', 'early_prop': 'ERP', 'late_abs': 'LAT', 'late_prop': 'LTP',
        'chaos': 'CHA', 'home': 'HOM', 'away': 'AWY', 'set_piece': 'STP'
    }
    for dim, code in dim_codes.items():
        val = int(pct.get(dim, 50))
        parts.append(f"{code}{val}")
    return '|'.join(parts)

def calculate_team_average(pct: Dict) -> float:
    """Moyenne des dimensions principales (excluant les doublons timing)"""
    main_dims = ['global', 'aerial', 'longshot', 'open_play', 'early_prop', 
                 'late_prop', 'chaos', 'home', 'away', 'set_piece']
    values = [pct.get(dim, 50) for dim in main_dims]
    return float(np.mean(values))

def find_relative_weaknesses(pct: Dict, team_avg: float) -> List[Dict]:
    """Trouve les faiblesses relatives et absolues"""
    weaknesses = []
    
    # Dimensions à analyser (on utilise PROPORTION pour timing)
    dims_to_check = {
        'global': 'Défense Globale',
        'aerial': 'Duels Aériens',
        'longshot': 'Tirs de Loin',
        'open_play': 'Jeu Ouvert',
        'early_prop': 'Début Match (Timing)',
        'late_prop': 'Fin Match (Timing)',
        'chaos': 'Discipline',
        'home': 'À Domicile',
        'away': 'À l\'Extérieur',
        'set_piece': 'Coups de Pied Arrêtés'
    }
    
    for dim, name in dims_to_check.items():
        val = pct.get(dim, 50)
        gap = team_avg - val
        
        # Severity basée sur absolu ET relatif
        if val <= 15:
            severity = 'CRITICAL'
        elif val <= 25:
            severity = 'HIGH'
        elif val <= 35 or gap > 20:
            severity = 'MEDIUM'
        elif gap > 10:
            severity = 'LOW'
        else:
            severity = 'MINIMAL'
        
        weaknesses.append({
            'dimension': dim,
            'dimension_name': name,
            'percentile': int(val),
            'team_average': round(team_avg, 1),
            'gap_to_average': round(gap, 1),
            'is_relative_weakness': gap > 10,
            'is_absolute_weakness': val <= 35,
            'severity': severity
        })
    
    weaknesses.sort(key=lambda x: (-1 if x['is_absolute_weakness'] else 0, x['gap_to_average']), reverse=True)
    return weaknesses

def find_relative_strengths(pct: Dict, team_avg: float) -> List[Dict]:
    """Trouve les forces relatives et absolues"""
    strengths = []
    
    dims_to_check = {
        'global': 'Défense Globale',
        'aerial': 'Duels Aériens',
        'longshot': 'Tirs de Loin',
        'open_play': 'Jeu Ouvert',
        'early_prop': 'Début Match (Timing)',
        'late_prop': 'Fin Match (Timing)',
        'chaos': 'Discipline',
        'home': 'À Domicile',
        'away': 'À l\'Extérieur',
        'set_piece': 'Coups de Pied Arrêtés'
    }
    
    for dim, name in dims_to_check.items():
        val = pct.get(dim, 50)
        gap = val - team_avg
        
        if val >= 90:
            level = 'ELITE'
        elif val >= 75:
            level = 'STRONG'
        elif gap > 10:
            level = 'SOLID'
        else:
            level = 'AVERAGE'
        
        strengths.append({
            'dimension': dim,
            'dimension_name': name,
            'percentile': int(val),
            'team_average': round(team_avg, 1),
            'gap_to_average': round(gap, 1),
            'is_relative_strength': gap > 10,
            'is_absolute_strength': val >= 75,
            'level': level
        })
    
    strengths.sort(key=lambda x: x['gap_to_average'], reverse=True)
    return strengths

def calculate_edge(weakness: Dict, is_fortress: bool) -> Tuple[float, str]:
    """
    Calcule l'edge estimé et sa catégorie
    
    WEAK: < 2% (noise, pas actionnable seul)
    MEDIUM: 2-4% (actionnable avec autres facteurs)
    STRONG: > 4% (actionnable seul)
    """
    pct = weakness['percentile']
    gap = weakness['gap_to_average']
    
    if weakness['is_absolute_weakness']:
        # Formule pour faiblesse absolue
        edge = (40 - pct) / 6  # Plus agressif pour les vraies faiblesses
    elif weakness['is_relative_weakness']:
        # Formule pour faiblesse relative
        if is_fortress:
            edge = gap / 20  # Réduit pour FORTRESS (edge limité)
        else:
            edge = gap / 12
    else:
        edge = max(0.5, gap / 25)  # Minimum edge
    
    edge = round(edge, 1)
    
    # Catégoriser
    if edge >= 4:
        category = 'STRONG'
    elif edge >= 2:
        category = 'MEDIUM'
    else:
        category = 'WEAK'
    
    return edge, category

def generate_exploit_paths(pct: Dict, weaknesses: List[Dict], is_fortress: bool) -> List[Dict]:
    """
    Génère les exploit paths avec les bonnes métriques par marché
    """
    
    # Mapping dimension -> marché avec métrique appropriée
    exploit_mapping = {
        'early_prop': {
            'market': 'First Goalscorer',
            'attacker_profile': 'EARLY_BIRD',
            'tactic': 'Attaquer 0-30 min',
            'metric_type': 'PROPORTION'
        },
        'late_prop': {
            'market': 'Last Goalscorer',
            'attacker_profile': 'DIESEL / CLUTCH',
            'tactic': 'Pousser 60-90 min',
            'metric_type': 'PROPORTION'
        },
        'aerial': {
            'market': 'Header Scorer / Headed Goal',
            'attacker_profile': 'HEADER_SPECIALIST',
            'tactic': 'Centres et corners',
            'metric_type': 'ABSOLUTE'
        },
        'set_piece': {
            'market': 'Goal from Set Piece',
            'attacker_profile': 'SET_PIECE_THREAT',
            'tactic': 'Corners et FK',
            'metric_type': 'ABSOLUTE'
        },
        'longshot': {
            'market': 'Goal from Outside Box',
            'attacker_profile': 'LONGSHOT_SPECIALIST',
            'tactic': 'Tirs 20-25m',
            'metric_type': 'ABSOLUTE'
        },
        'chaos': {
            'market': 'Penalty Scored',
            'attacker_profile': 'CLINICAL',
            'tactic': 'Provoquer fautes',
            'metric_type': 'ABSOLUTE'
        },
        'away': {
            'market': 'Home Team Goals (vs Away)',
            'attacker_profile': 'HOME_SPECIALIST',
            'tactic': 'Exploiter déplacement',
            'metric_type': 'ABSOLUTE',
            'condition': 'Quand équipe joue AWAY'
        },
        'home': {
            'market': 'Away Team Goals (vs Home)',
            'attacker_profile': 'AWAY_SPECIALIST',
            'tactic': 'Exploiter domicile',
            'metric_type': 'ABSOLUTE',
            'condition': 'Quand équipe joue HOME'
        },
        'open_play': {
            'market': 'Anytime Scorer',
            'attacker_profile': 'VOLUME_SHOOTER',
            'tactic': 'Jeu ouvert',
            'metric_type': 'ABSOLUTE'
        },
        'global': {
            'market': 'Over Goals',
            'attacker_profile': 'ANY_ATTACKER',
            'tactic': 'Attaquer partout',
            'metric_type': 'ABSOLUTE'
        }
    }
    
    exploits = []
    
    for weakness in weaknesses:
        dim = weakness['dimension']
        if dim not in exploit_mapping:
            continue
        
        mapping = exploit_mapping[dim]
        edge, edge_category = calculate_edge(weakness, is_fortress)
        
        # Déterminer le type d'exploit et la confiance
        if weakness['is_absolute_weakness']:
            exploit_type = 'ABSOLUTE'
            if weakness['severity'] == 'CRITICAL':
                confidence = 'VERY_HIGH'
            else:
                confidence = 'HIGH'
            reason = f"Faiblesse absolue: {weakness['percentile']}th percentile"
        elif weakness['is_relative_weakness']:
            exploit_type = 'RELATIVE'
            confidence = 'MEDIUM' if is_fortress else 'HIGH'
            reason = f"Faiblesse relative: {weakness['gap_to_average']:+.1f} pts vs moyenne ({weakness['team_average']:.0f})"
        else:
            exploit_type = 'MINOR'
            confidence = 'LOW'
            reason = f"Point le moins fort: {weakness['percentile']}th pct"
        
        exploit = {
            'dimension': dim,
            'market': mapping['market'],
            'attacker_profile': mapping['attacker_profile'],
            'tactic': mapping['tactic'],
            'metric_type': mapping['metric_type'],
            'vulnerability_pct': int(weakness['percentile']),
            'gap_to_team_avg': float(weakness['gap_to_average']),
            'exploit_type': exploit_type,
            'confidence': confidence,
            'edge_estimate': edge,
            'edge_category': edge_category,
            'reason': reason,
            'actionable': edge_category in ['MEDIUM', 'STRONG']
        }
        
        if 'condition' in mapping:
            exploit['condition'] = mapping['condition']
        
        exploits.append(exploit)
    
    # Trier par edge décroissant
    exploits.sort(key=lambda x: x['edge_estimate'], reverse=True)
    return exploits[:6]

def generate_dna_string(pct: Dict, weaknesses: List[Dict], strengths: List[Dict]) -> List[str]:
    """Génère le DNA string avec les nouvelles dimensions"""
    tags = []
    
    # Niveau global
    level = get_defense_level(pct.get('global', 50))
    tags.append(level['code'])
    
    # Forces absolues
    for s in strengths:
        if s['is_absolute_strength'] and s['level'] == 'ELITE':
            code = s['dimension'].upper().replace('_PROP', '_P').replace('_ABS', '_A')[:3]
            tags.append(f"{code}_ELITE")
    
    # Faiblesses absolues
    for w in weaknesses:
        if w['is_absolute_weakness']:
            code = w['dimension'].upper().replace('_PROP', '_P').replace('_ABS', '_A')[:3]
            tags.append(f"{code}_WEAK")
    
    # Faiblesses relatives significatives
    for w in weaknesses:
        if w['is_relative_weakness'] and not w['is_absolute_weakness'] and w['gap_to_average'] > 15:
            code = w['dimension'].upper().replace('_PROP', '_P').replace('_ABS', '_A')[:3]
            tags.append(f"{code}_REL_WEAK")
    
    # Tags contextuels timing
    early_prop = pct.get('early_prop', 50)
    late_prop = pct.get('late_prop', 50)
    
    if early_prop <= 25:
        tags.append('SLOW_STARTER')
    elif early_prop >= 75:
        tags.append('FAST_STARTER')
    
    if late_prop <= 25:
        tags.append('LATE_COLLAPSER')
    elif late_prop >= 75:
        tags.append('STRONG_FINISHER')
    
    # Balance
    values = [pct.get(d, 50) for d in ['global', 'aerial', 'longshot', 'open_play', 'chaos', 'home', 'away', 'set_piece']]
    if max(values) - min(values) <= 25:
        tags.append('BALANCED')
    elif max(values) - min(values) >= 50:
        tags.append('UNBALANCED')
    
    return tags

def generate_enriched_name(pct: Dict, strengths: List[Dict], weaknesses: List[Dict]) -> str:
    """Génère le nom enrichi 3 composants"""
    level = get_defense_level(pct.get('global', 50))
    level_name = level['name']
    
    # Force principale
    top_strength = strengths[0] if strengths else None
    strength_desc = ""
    if top_strength and (top_strength['is_absolute_strength'] or top_strength['gap_to_average'] > 5):
        dim = top_strength['dimension']
        if dim in STRENGTH_DESCRIPTORS:
            strength_desc = STRENGTH_DESCRIPTORS[dim]['strong']
    
    # Faiblesse principale
    top_weakness = weaknesses[0] if weaknesses else None
    weakness_desc = ""
    if top_weakness and (top_weakness['is_absolute_weakness'] or top_weakness['gap_to_average'] > 10):
        dim = top_weakness['dimension']
        if dim in STRENGTH_DESCRIPTORS:
            weakness_desc = STRENGTH_DESCRIPTORS[dim]['weak']
    
    if strength_desc and weakness_desc:
        return f"{level_name} {strength_desc}, {weakness_desc}"
    elif strength_desc:
        return f"{level_name} {strength_desc}"
    elif weakness_desc:
        return f"{level_name} {weakness_desc}"
    return f"{level_name} Équilibrée"

def calculate_matchup_friction(pct: Dict, attacker_profile: str) -> Dict:
    """
    Calcule la friction matchup avec la BONNE métrique
    
    First/Last Goalscorer = utilise PROPORTION (timing relatif)
    Anytime = utilise ABSOLUTE (volume)
    """
    
    # Mapping profile -> dimension et type de métrique
    profile_mapping = {
        'EARLY_BIRD': {'dim': 'early_prop', 'market': 'First Goalscorer'},
        'DIESEL': {'dim': 'late_prop', 'market': 'Last Goalscorer'},
        'CLUTCH_PLAYER': {'dim': 'late_prop', 'market': 'Last Goalscorer'},
        'HEADER_SPECIALIST': {'dim': 'aerial', 'market': 'Header Scorer'},
        'SET_PIECE_THREAT': {'dim': 'set_piece', 'market': 'Set Piece Goal'},
        'LONGSHOT_SPECIALIST': {'dim': 'longshot', 'market': 'Outside Box Goal'},
        'CLINICAL': {'dim': 'chaos', 'market': 'Penalty'},
        'PENALTY_TAKER': {'dim': 'chaos', 'market': 'Penalty'},
        'HOME_SPECIALIST': {'dim': 'away', 'market': 'Home Goals'},
        'AWAY_SPECIALIST': {'dim': 'home', 'market': 'Away Goals'},
        'VOLUME_SHOOTER': {'dim': 'open_play', 'market': 'Anytime Scorer'},
        'POACHER': {'dim': 'aerial', 'market': 'Anytime Scorer'},
        'SUPER_SUB': {'dim': 'late_prop', 'market': 'Last Goalscorer'}
    }
    
    mapping = profile_mapping.get(attacker_profile, {'dim': 'global', 'market': 'Any'})
    dim = mapping['dim']
    resist = pct.get(dim, 50)
    
    # Friction basée sur résistance
    if resist <= 15:
        multiplier, verdict, emoji = 0.5, 'GOLDEN_MATCHUP', '🟢🟢'
    elif resist <= 30:
        multiplier, verdict, emoji = 0.65, 'FAVORABLE', '🟢'
    elif resist <= 45:
        multiplier, verdict, emoji = 0.8, 'SLIGHT_EDGE', '🟡'
    elif resist <= 55:
        multiplier, verdict, emoji = 1.0, 'NEUTRAL', '⚪'
    elif resist <= 70:
        multiplier, verdict, emoji = 1.15, 'DIFFICULT', '🟠'
    elif resist <= 85:
        multiplier, verdict, emoji = 1.3, 'HARD', '🔴'
    else:
        multiplier, verdict, emoji = 1.5, 'AVOID', '🔴🔴'
    
    return {
        'profile': attacker_profile,
        'dimension': dim,
        'market': mapping['market'],
        'resist_pct': int(resist),
        'friction_multiplier': float(multiplier),
        'verdict': verdict,
        'emoji': emoji
    }

def generate_best_markets(exploits: List[Dict]) -> List[Dict]:
    """Génère les meilleurs marchés avec edge category"""
    markets = []
    for exploit in exploits:
        if exploit['actionable']:
            markets.append({
                'market': exploit['market'],
                'confidence': exploit['confidence'],
                'edge_estimate': exploit['edge_estimate'],
                'edge_category': exploit['edge_category'],
                'exploit_type': exploit['exploit_type'],
                'reason': exploit['reason'],
                'target_attacker': exploit['attacker_profile'],
                'condition': exploit.get('condition', 'Toujours applicable')
            })
    return markets[:5]

def main():
    print("=" * 80)
    print("🧬 DEFENSE RESPONSE MODEL (DRM) V5.1 - CORRECTIONS COMPLÈTES")
    print("   Timing Dual (Absolu + Proportion) | Edge Categories | Market-Specific")
    print("=" * 80)
    
    # Charger les données
    print("\n📂 Chargement des données...")
    v3_teams, raw_dict = load_data()
    print(f"   ✅ {len(v3_teams)} équipes V3 chargées")
    print(f"   ✅ {len(raw_dict)} équipes brutes chargées")
    
    # Calculer les percentiles PROPORTION
    print("\n🔬 Calcul des percentiles PROPORTION timing...")
    proportion_pcts = calculate_proportion_percentiles(v3_teams, raw_dict)
    
    # Générer les profils V5.1
    print("\n🔬 Génération des profils V5.1...")
    enriched_teams = []
    
    for team in v3_teams:
        team_name = team['team_name']
        raw = raw_dict.get(team_name, {})
        prop_pct = proportion_pcts.get(team_name, {})
        
        # Construire le nouveau dictionnaire de percentiles
        pct = team.get('percentiles', {}).copy()
        
        # Ajouter les métriques timing duales
        pct['early_abs'] = pct.get('early', 50)  # Ancien = absolu
        pct['late_abs'] = pct.get('late', 50)
        pct['early_prop'] = prop_pct.get('early_prop_pct', 50)  # Nouveau = proportion
        pct['late_prop'] = prop_pct.get('late_prop_pct', 50)
        
        # Calculer moyenne équipe
        team_avg = calculate_team_average(pct)
        is_fortress = pct.get('global', 50) >= 75
        
        # Trouver forces et faiblesses
        weaknesses = find_relative_weaknesses(pct, team_avg)
        strengths = find_relative_strengths(pct, team_avg)
        
        # Construire le profil enrichi
        enriched = team.copy()
        enriched['percentiles'] = pct
        enriched['percentiles_v5_1'] = {
            'global': pct.get('global', 50),
            'aerial': pct.get('aerial', 50),
            'longshot': pct.get('longshot', 50),
            'open_play': pct.get('open_play', 50),
            'early_absolute': pct.get('early_abs', 50),
            'early_proportion': pct.get('early_prop', 50),
            'late_absolute': pct.get('late_abs', 50),
            'late_proportion': pct.get('late_prop', 50),
            'chaos': pct.get('chaos', 50),
            'home': pct.get('home', 50),
            'away': pct.get('away', 50),
            'set_piece': pct.get('set_piece', 50)
        }
        
        # Données brutes timing pour référence
        enriched['timing_raw'] = {
            'xga_1h_pct': raw.get('xga_1h_pct', 0),
            'xga_2h_pct': raw.get('xga_2h_pct', 0),
            'xga_first_15_pct': raw.get('xga_first_15_pct', 0),
            'xga_last_15_pct': raw.get('xga_last_15_pct', 0)
        }
        
        enriched['fingerprint_code'] = generate_fingerprint_code(pct)
        enriched['fingerprint_compact'] = generate_compact_fingerprint(pct)
        enriched['team_average_pct'] = round(team_avg, 1)
        enriched['is_fortress'] = is_fortress
        
        enriched['relative_strengths'] = strengths[:5]
        enriched['relative_weaknesses'] = weaknesses[:5]
        
        exploit_paths = generate_exploit_paths(pct, weaknesses, is_fortress)
        enriched['exploit_paths'] = exploit_paths
        
        dna_string = generate_dna_string(pct, weaknesses, strengths)
        enriched['dna_string'] = dna_string
        enriched['dna_string_full'] = '-'.join(dna_string)
        
        enriched['enriched_name'] = generate_enriched_name(pct, strengths, weaknesses)
        
        level = get_defense_level(pct.get('global', 50))
        enriched['defense_level'] = level
        
        enriched['best_markets'] = generate_best_markets(exploit_paths)
        
        # Matchup guide
        attacker_profiles = ['EARLY_BIRD', 'DIESEL', 'CLUTCH_PLAYER', 'HEADER_SPECIALIST',
            'SET_PIECE_THREAT', 'LONGSHOT_SPECIALIST', 'CLINICAL', 'PENALTY_TAKER',
            'HOME_SPECIALIST', 'AWAY_SPECIALIST', 'VOLUME_SHOOTER', 'POACHER', 'SUPER_SUB']
        enriched['matchup_guide'] = {p: calculate_matchup_friction(pct, p) for p in attacker_profiles}
        
        # Anti-exploits
        anti_exploits = []
        for strength in strengths[:3]:
            if strength['is_absolute_strength']:
                dim = strength['dimension']
                if dim in STRENGTH_DESCRIPTORS:
                    anti_exploits.append({
                        'dimension': dim,
                        'dimension_name': strength['dimension_name'],
                        'percentile': int(strength['percentile']),
                        'avoid': f"Attaques via {strength['dimension_name']}",
                        'reason': f"Force absolue: {strength['percentile']}th percentile"
                    })
        enriched['anti_exploits'] = anti_exploits
        
        enriched_teams.append(enriched)
    
    print(f"   ✅ {len(enriched_teams)} profils V5.1 générés")
    
    # Sauvegarder
    print("\n💾 Sauvegarde...")
    with open(OUTPUT_FILE, 'w') as f:
        enriched_teams = convert_numpy(enriched_teams)
        json.dump(enriched_teams, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # Vérification unicité
    print("\n🔍 Vérification de l'unicité...")
    fingerprints = [t['fingerprint_code'] for t in enriched_teams]
    dna_strings = [t['dna_string_full'] for t in enriched_teams]
    names = [t['enriched_name'] for t in enriched_teams]
    
    print(f"   • Fingerprints uniques: {len(set(fingerprints))}/{len(fingerprints)}")
    print(f"   • DNA Strings uniques: {len(set(dna_strings))}/{len(dna_strings)}")
    print(f"   • Noms enrichis uniques: {len(set(names))}/{len(names)}")
    
    # Rapport détaillé
    print("\n" + "=" * 80)
    print("📊 RAPPORT DRM V5.1 - CORRECTIONS APPLIQUÉES")
    print("=" * 80)
    
    # Arsenal avant/après
    arsenal = next((t for t in enriched_teams if 'Arsenal' in t['team_name']), None)
    if arsenal:
        print(f"\n🔬 ARSENAL - VALIDATION CORRECTION TIMING")
        print(f"   {'─' * 60}")
        print(f"   AVANT (V5.0 BUG):")
        print(f"      Early resist: 91th pct (basé sur xGA ABSOLU)")
        print(f"      → Matchup EARLY_BIRD: AVOID ❌")
        print(f"   ")
        print(f"   APRÈS (V5.1 CORRIGÉ):")
        print(f"      Early ABSOLU:     {arsenal['percentiles_v5_1']['early_absolute']}th pct (volume faible = bon)")
        print(f"      Early PROPORTION: {arsenal['percentiles_v5_1']['early_proportion']}th pct (% élevé = SLOW_STARTER)")
        print(f"      xga_1h_pct brut:  {arsenal['timing_raw']['xga_1h_pct']:.1f}%")
        
        early_bird = arsenal['matchup_guide']['EARLY_BIRD']
        print(f"      → Matchup EARLY_BIRD: {early_bird['verdict']} {early_bird['emoji']} (resist: {early_bird['resist_pct']}th)")
        
        if arsenal['exploit_paths']:
            first_gs = next((e for e in arsenal['exploit_paths'] if 'First' in e['market']), None)
            if first_gs:
                print(f"      → First Goalscorer exploit: {first_gs['confidence']} | Edge: {first_gs['edge_estimate']}% [{first_gs['edge_category']}]")
    
    # Barcelona vérification
    barcelona = next((t for t in enriched_teams if 'Barcelona' in t['team_name']), None)
    if barcelona:
        print(f"\n🔬 BARCELONA - VALIDATION SLOW_STARTER")
        print(f"   {'─' * 60}")
        print(f"   Early PROPORTION: {barcelona['percentiles_v5_1']['early_proportion']}th pct")
        print(f"   xga_1h_pct brut:  {barcelona['timing_raw']['xga_1h_pct']:.1f}%")
        print(f"   xga_first_15_pct: {barcelona['timing_raw']['xga_first_15_pct']:.1f}%")
        
        early_bird = barcelona['matchup_guide']['EARLY_BIRD']
        print(f"   → Matchup EARLY_BIRD: {early_bird['verdict']} {early_bird['emoji']}")
    
    # Top cibles First Goalscorer CORRIGÉ
    print(f"\n🎯 TOP CIBLES FIRST GOALSCORER (PROPORTION METRIC)")
    print(f"   {'─' * 60}")
    
    # Trier par early_proportion (bas = vulnérable)
    sorted_teams = sorted(enriched_teams, key=lambda t: t['percentiles_v5_1']['early_proportion'])
    
    for i, team in enumerate(sorted_teams[:10], 1):
        pct = team['percentiles_v5_1']['early_proportion']
        raw = team['timing_raw']['xga_1h_pct']
        level = team['defense_level']['emoji']
        
        # Trouver l'exploit First GS
        exploit = next((e for e in team['exploit_paths'] if 'First' in e['market']), None)
        edge_info = f"Edge: {exploit['edge_estimate']}% [{exploit['edge_category']}]" if exploit else "N/A"
        
        print(f"   {i:2}. {team['team_name']:<25} {level} | EarlyProp: {pct:3.0f}th | 1H%: {raw:5.1f}% | {edge_info}")
    
    # Top cibles Last Goalscorer
    print(f"\n🎯 TOP CIBLES LAST GOALSCORER (PROPORTION METRIC)")
    print(f"   {'─' * 60}")
    
    sorted_teams = sorted(enriched_teams, key=lambda t: t['percentiles_v5_1']['late_proportion'])
    
    for i, team in enumerate(sorted_teams[:10], 1):
        pct = team['percentiles_v5_1']['late_proportion']
        raw = team['timing_raw']['xga_2h_pct']
        level = team['defense_level']['emoji']
        
        exploit = next((e for e in team['exploit_paths'] if 'Last' in e['market']), None)
        edge_info = f"Edge: {exploit['edge_estimate']}% [{exploit['edge_category']}]" if exploit else "N/A"
        
        print(f"   {i:2}. {team['team_name']:<25} {level} | LateProp: {pct:3.0f}th | 2H%: {raw:5.1f}% | {edge_info}")
    
    # Distribution des edges
    print(f"\n📊 DISTRIBUTION DES EDGE CATEGORIES")
    print(f"   {'─' * 60}")
    
    all_exploits = [e for t in enriched_teams for e in t['exploit_paths']]
    edge_counts = Counter(e['edge_category'] for e in all_exploits)
    total = len(all_exploits)
    
    for cat in ['STRONG', 'MEDIUM', 'WEAK']:
        count = edge_counts.get(cat, 0)
        pct = count / total * 100 if total > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"   {cat:8}: {count:3} ({pct:5.1f}%) {bar}")
    
    # Actionable exploits
    actionable = sum(1 for e in all_exploits if e['actionable'])
    print(f"\n   ✅ Exploits actionnables (MEDIUM+STRONG): {actionable}/{total} ({actionable/total*100:.1f}%)")
    
    print(f"\n{'=' * 80}")
    print(f"✅ DRM V5.1 COMPLET - CORRECTIONS APPLIQUÉES")
    print(f"   📁 Fichier: {OUTPUT_FILE}")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE RESPONSE MODEL (DRM) V5.0 - ULTIMATE FINGERPRINT                    ║
║  96 équipes = 96 ADN 100% UNIQUES                                            ║
║                                                                              ║
║  SOLUTIONS INTÉGRÉES:                                                        ║
║  1. FINGERPRINT NUMÉRIQUE UNIQUE (Code DNA)                                  ║
║  2. EXPLOIT PATH RELATIF (Même pour les FORTRESS)                            ║
║  3. DNA STRING COMPLET (Combinaison de tags unique)                          ║
║  4. NOMMAGE ENRICHI 3 COMPOSANTS (Niveau + Force + Faille)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter

# Paths
DATA_DIR = Path('/home/Mon_ps/data/defense_dna')
INPUT_FILE = DATA_DIR / 'team_defense_dna_v3.json'
OUTPUT_FILE = DATA_DIR / 'team_defense_dna_v5_ultimate.json'

# Dimensions avec leurs codes courts
DIMENSIONS = {
    'global': {'name': 'Défense Globale', 'code': 'GLO', 'short': 'Glo'},
    'aerial': {'name': 'Duels Aériens', 'code': 'AER', 'short': 'Aer'},
    'longshot': {'name': 'Tirs de Loin', 'code': 'LNG', 'short': 'Lng'},
    'open_play': {'name': 'Jeu Ouvert', 'code': 'OPN', 'short': 'Opn'},
    'early': {'name': 'Début Match (0-30\')', 'code': 'ERL', 'short': 'Erl'},
    'late': {'name': 'Fin Match (60-90\')', 'code': 'LAT', 'short': 'Lat'},
    'chaos': {'name': 'Discipline', 'code': 'CHA', 'short': 'Cha'},
    'home': {'name': 'À Domicile', 'code': 'HOM', 'short': 'Hom'},
    'away': {'name': 'À l\'Extérieur', 'code': 'AWY', 'short': 'Awy'},
    'set_piece': {'name': 'Coups de Pied Arrêtés', 'code': 'STP', 'short': 'Stp'}
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

# Descripteurs de force/faiblesse
STRENGTH_DESCRIPTORS = {
    'global': {'strong': 'Impénétrable', 'weak': 'Perméable'},
    'aerial': {'strong': 'Dominante en l\'Air', 'weak': 'Vulnérable aux Têtes'},
    'longshot': {'strong': 'Anti-Frappe', 'weak': 'Perméable de Loin'},
    'open_play': {'strong': 'Hermétique', 'weak': 'Ouverte'},
    'early': {'strong': 'Matinale', 'weak': 'Endormie'},
    'late': {'strong': 'Nocturne', 'weak': 'Épuisée'},
    'chaos': {'strong': 'Disciplinée', 'weak': 'Indisciplinée'},
    'home': {'strong': 'Imprenable à Dom.', 'weak': 'Fragile à Dom.'},
    'away': {'strong': 'Solide en Dépl.', 'weak': 'Fragile en Dépl.'},
    'set_piece': {'strong': 'Solide sur CPA', 'weak': 'Vulnérable sur CPA'}
}

def load_data() -> List[Dict]:
    """Charge les données V3"""
    with open(INPUT_FILE, 'r') as f:
        return json.load(f)

def get_defense_level(global_pct: int) -> Dict:
    """Retourne le niveau de défense basé sur le percentile global"""
    for (low, high), level in DEFENSE_LEVELS.items():
        if low <= global_pct < high:
            return level
    return DEFENSE_LEVELS[(0, 30)]

def generate_fingerprint_code(team: Dict) -> str:
    """
    SOLUTION 1: Génère un code fingerprint numérique unique
    Format: DEF-[Global]-[Aerial]-[Long]-[Open]-[Early]-[Late]-[Chaos]-[Home]-[Away]-[SP]
    """
    pct = team['percentiles']
    
    code_parts = ['DEF']
    for dim in ['global', 'aerial', 'longshot', 'open_play', 'early', 'late', 'chaos', 'home', 'away', 'set_piece']:
        code_parts.append(str(pct.get(dim, 50)))
    
    return '-'.join(code_parts)

def generate_compact_fingerprint(team: Dict) -> str:
    """
    Génère un fingerprint compact lisible
    Format: FRT-98|AER-79|LNG-96|...
    """
    pct = team['percentiles']
    
    parts = []
    for dim, info in DIMENSIONS.items():
        val = pct.get(dim, 50)
        parts.append(f"{info['code']}{val}")
    
    return '|'.join(parts)

def calculate_team_average(team: Dict) -> float:
    """Calcule la moyenne des percentiles de l'équipe"""
    pct = team['percentiles']
    values = [pct.get(dim, 50) for dim in DIMENSIONS.keys()]
    return np.mean(values)

def find_relative_weaknesses(team: Dict) -> List[Dict]:
    """
    SOLUTION 2: Trouve les faiblesses RELATIVES (même pour les FORTRESS)
    Compare chaque dimension à la MOYENNE de l'équipe
    """
    pct = team['percentiles']
    team_avg = calculate_team_average(team)
    
    weaknesses = []
    for dim, info in DIMENSIONS.items():
        val = pct.get(dim, 50)
        gap = team_avg - val  # Positif si en dessous de la moyenne
        
        weaknesses.append({
            'dimension': dim,
            'dimension_name': info['name'],
            'percentile': val,
            'team_average': round(team_avg, 1),
            'gap_to_average': round(gap, 1),
            'is_relative_weakness': gap > 10,  # Plus de 10 pts sous la moyenne
            'is_absolute_weakness': val <= 35,
            'severity': 'CRITICAL' if val <= 20 else 'HIGH' if val <= 35 else 'MEDIUM' if gap > 15 else 'LOW'
        })
    
    # Trier par gap (plus grand gap = plus grande faiblesse relative)
    weaknesses.sort(key=lambda x: x['gap_to_average'], reverse=True)
    
    return weaknesses

def find_relative_strengths(team: Dict) -> List[Dict]:
    """Trouve les forces RELATIVES (au-dessus de la moyenne de l'équipe)"""
    pct = team['percentiles']
    team_avg = calculate_team_average(team)
    
    strengths = []
    for dim, info in DIMENSIONS.items():
        val = pct.get(dim, 50)
        gap = val - team_avg  # Positif si au-dessus de la moyenne
        
        strengths.append({
            'dimension': dim,
            'dimension_name': info['name'],
            'percentile': val,
            'team_average': round(team_avg, 1),
            'gap_to_average': round(gap, 1),
            'is_relative_strength': gap > 10,
            'is_absolute_strength': val >= 75,
            'level': 'ELITE' if val >= 90 else 'STRONG' if val >= 75 else 'SOLID' if gap > 10 else 'AVERAGE'
        })
    
    strengths.sort(key=lambda x: x['gap_to_average'], reverse=True)
    
    return strengths

def generate_relative_exploit_paths(team: Dict, weaknesses: List[Dict]) -> List[Dict]:
    """
    SOLUTION 2: Génère des exploit paths même pour les équipes fortes
    Utilise les faiblesses RELATIVES
    """
    exploit_mapping = {
        'early': {
            'attacker_profile': 'EARLY_BIRD',
            'market': 'First Goalscorer',
            'tactic': 'Attaquer dans les 30 premières minutes'
        },
        'late': {
            'attacker_profile': 'DIESEL / CLUTCH',
            'market': 'Last Goalscorer',
            'tactic': 'Pousser en fin de match'
        },
        'aerial': {
            'attacker_profile': 'HEADER_SPECIALIST',
            'market': 'Header Scorer / Headed Goal',
            'tactic': 'Centres et corners'
        },
        'set_piece': {
            'attacker_profile': 'SET_PIECE_THREAT',
            'market': 'Goal from Set Piece',
            'tactic': 'Maximiser corners et coups francs'
        },
        'longshot': {
            'attacker_profile': 'LONGSHOT_SPECIALIST',
            'market': 'Goal from Outside Box',
            'tactic': 'Tirs de 20-25m'
        },
        'chaos': {
            'attacker_profile': 'CLINICAL / PENALTY_TAKER',
            'market': 'Penalty Scored',
            'tactic': 'Provoquer des fautes'
        },
        'away': {
            'attacker_profile': 'HOME_SPECIALIST',
            'market': 'Home Team Goals',
            'tactic': 'Exploiter quand ils jouent à l\'extérieur',
            'condition': 'Quand l\'équipe joue AWAY'
        },
        'home': {
            'attacker_profile': 'AWAY_SPECIALIST',
            'market': 'Away Team Goals',
            'tactic': 'Exploiter leur faiblesse à domicile',
            'condition': 'Quand l\'équipe joue HOME'
        },
        'open_play': {
            'attacker_profile': 'VOLUME_SHOOTER',
            'market': 'Anytime Scorer',
            'tactic': 'Attaques rapides en jeu ouvert'
        },
        'global': {
            'attacker_profile': 'ANY_ATTACKER',
            'market': 'Over Goals / Anytime Scorer',
            'tactic': 'Attaquer sur tous les fronts'
        }
    }
    
    team_avg = calculate_team_average(team)
    is_fortress = team['percentiles'].get('global', 50) >= 75
    
    exploits = []
    
    for weakness in weaknesses:
        dim = weakness['dimension']
        if dim not in exploit_mapping:
            continue
        
        exploit = exploit_mapping[dim].copy()
        exploit['dimension'] = dim
        exploit['vulnerability_pct'] = weakness['percentile']
        exploit['gap_to_team_avg'] = weakness['gap_to_average']
        
        # Déterminer la confiance
        if weakness['is_absolute_weakness']:
            exploit['confidence'] = 'HIGH'
            exploit['exploit_type'] = 'ABSOLUTE'
            exploit['reason'] = f"Faiblesse absolue: {weakness['percentile']}th percentile"
        elif weakness['is_relative_weakness']:
            exploit['confidence'] = 'MEDIUM' if is_fortress else 'HIGH'
            exploit['exploit_type'] = 'RELATIVE'
            exploit['reason'] = f"Faiblesse relative: {weakness['gap_to_average']:+.1f} pts vs moyenne équipe ({team_avg:.0f})"
        else:
            exploit['confidence'] = 'LOW'
            exploit['exploit_type'] = 'MINOR'
            exploit['reason'] = f"Point le moins fort: {weakness['percentile']}th pct"
        
        # Edge estimé
        if weakness['is_absolute_weakness']:
            exploit['edge_estimate'] = round((50 - weakness['percentile']) / 8, 1)
        else:
            exploit['edge_estimate'] = round(weakness['gap_to_average'] / 15, 1)
        
        exploits.append(exploit)
    
    # Toujours retourner au moins 3 exploits
    return exploits[:5] if len(exploits) >= 3 else exploits

def generate_dna_string(team: Dict, weaknesses: List[Dict], strengths: List[Dict]) -> List[str]:
    """
    SOLUTION 3: Génère un DNA STRING complet avec tous les tags pertinents
    """
    pct = team['percentiles']
    tags = []
    
    # 1. TAG DE NIVEAU
    level = get_defense_level(pct.get('global', 50))
    tags.append(level['code'])
    
    # 2. TAGS DE FORCE ABSOLUE (>= 80th percentile)
    for strength in strengths:
        if strength['is_absolute_strength']:
            dim = strength['dimension']
            tags.append(f"{DIMENSIONS[dim]['code']}_ELITE")
    
    # 3. TAGS DE FORCE RELATIVE (> 15 pts au-dessus moyenne)
    for strength in strengths:
        if strength['gap_to_average'] > 15 and not strength['is_absolute_strength']:
            dim = strength['dimension']
            tags.append(f"{DIMENSIONS[dim]['code']}_STRONG")
    
    # 4. TAGS DE FAIBLESSE ABSOLUE (<= 25th percentile)
    for weakness in weaknesses:
        if weakness['percentile'] <= 25:
            dim = weakness['dimension']
            tags.append(f"{DIMENSIONS[dim]['code']}_WEAK")
    
    # 5. TAGS DE FAIBLESSE RELATIVE (> 15 pts sous moyenne)
    for weakness in weaknesses:
        if weakness['gap_to_average'] > 15 and weakness['percentile'] > 25:
            dim = weakness['dimension']
            tags.append(f"{DIMENSIONS[dim]['code']}_REL_WEAK")
    
    # 6. TAGS CONTEXTUELS
    home_away_diff = pct.get('home', 50) - pct.get('away', 50)
    if home_away_diff > 25:
        tags.append('HOME_DOMINANT')
    elif home_away_diff < -25:
        tags.append('AWAY_DOMINANT')
    
    early_late_diff = pct.get('early', 50) - pct.get('late', 50)
    if early_late_diff > 20:
        tags.append('STARTS_STRONG')
    elif early_late_diff < -20:
        tags.append('FINISHES_STRONG')
    
    # 7. TAG DE BALANCE
    values = [pct.get(dim, 50) for dim in DIMENSIONS.keys()]
    if max(values) - min(values) <= 25:
        tags.append('BALANCED')
    elif max(values) - min(values) >= 50:
        tags.append('UNBALANCED')
    
    return tags

def generate_enriched_name(team: Dict, strengths: List[Dict], weaknesses: List[Dict]) -> str:
    """
    SOLUTION 4: Génère un nom enrichi en 3 composants
    Format: [Niveau] [Force Principale], [Faille Principale]
    """
    pct = team['percentiles']
    
    # 1. NIVEAU
    level = get_defense_level(pct.get('global', 50))
    level_name = level['name']
    
    # 2. FORCE PRINCIPALE (la plus forte ou la plus au-dessus de la moyenne)
    top_strength = strengths[0] if strengths else None
    if top_strength and (top_strength['is_absolute_strength'] or top_strength['gap_to_average'] > 5):
        dim = top_strength['dimension']
        strength_desc = STRENGTH_DESCRIPTORS[dim]['strong']
    else:
        strength_desc = ""
    
    # 3. FAILLE PRINCIPALE (la plus faible ou la plus sous la moyenne)
    top_weakness = weaknesses[0] if weaknesses else None
    if top_weakness and (top_weakness['is_absolute_weakness'] or top_weakness['gap_to_average'] > 10):
        dim = top_weakness['dimension']
        weakness_desc = STRENGTH_DESCRIPTORS[dim]['weak']
        weakness_pct = top_weakness['percentile']
    else:
        weakness_desc = ""
        weakness_pct = None
    
    # Construire le nom
    if strength_desc and weakness_desc:
        name = f"{level_name} {strength_desc}, {weakness_desc}"
    elif strength_desc:
        name = f"{level_name} {strength_desc}"
    elif weakness_desc:
        name = f"{level_name} {weakness_desc}"
    else:
        name = f"{level_name} Équilibrée"
    
    return name

def generate_short_description(team: Dict, strengths: List[Dict], weaknesses: List[Dict]) -> str:
    """Génère une description courte et unique"""
    pct = team['percentiles']
    team_avg = calculate_team_average(team)
    
    # Force principale
    top_strength = strengths[0] if strengths else None
    # Faiblesse principale
    top_weakness = weaknesses[0] if weaknesses else None
    
    parts = []
    
    # Niveau global
    if pct['global'] >= 90:
        parts.append("Elite défensive")
    elif pct['global'] >= 75:
        parts.append("Très solide")
    elif pct['global'] >= 60:
        parts.append("Solide")
    elif pct['global'] >= 45:
        parts.append("Moyenne")
    elif pct['global'] >= 30:
        parts.append("Fragile")
    else:
        parts.append("Très fragile")
    
    # Force
    if top_strength and top_strength['gap_to_average'] > 5:
        parts.append(f"forte en {DIMENSIONS[top_strength['dimension']]['name']}")
    
    # Faiblesse
    if top_weakness and (top_weakness['is_absolute_weakness'] or top_weakness['gap_to_average'] > 10):
        if top_weakness['is_absolute_weakness']:
            parts.append(f"très vulnérable en {DIMENSIONS[top_weakness['dimension']]['name']} ({top_weakness['percentile']}th)")
        else:
            parts.append(f"relativement faible en {DIMENSIONS[top_weakness['dimension']]['name']} (-{top_weakness['gap_to_average']:.0f} pts)")
    
    return ", ".join(parts) + "."

def calculate_matchup_friction(team: Dict, attacker_profile: str) -> Dict:
    """Calcule la friction pour un type d'attaquant spécifique"""
    pct = team['percentiles']
    
    profile_to_dim = {
        'EARLY_BIRD': 'early',
        'DIESEL': 'late',
        'CLUTCH_PLAYER': 'late',
        'HEADER_SPECIALIST': 'aerial',
        'SET_PIECE_THREAT': 'set_piece',
        'LONGSHOT_SPECIALIST': 'longshot',
        'CLINICAL': 'chaos',
        'PENALTY_TAKER': 'chaos',
        'HOME_SPECIALIST': 'away',
        'AWAY_SPECIALIST': 'home',
        'VOLUME_SHOOTER': 'open_play',
        'POACHER': 'aerial',
        'TARGET_MAN': 'aerial',
        'PLAYMAKER': 'open_play',
        'SUPER_SUB': 'late'
    }
    
    dim = profile_to_dim.get(attacker_profile, 'global')
    resist = pct.get(dim, 50)
    
    # Calculer le multiplicateur
    if resist <= 15:
        multiplier = 0.5
        verdict = 'GOLDEN_MATCHUP'
        emoji = '🟢🟢'
    elif resist <= 30:
        multiplier = 0.65
        verdict = 'FAVORABLE'
        emoji = '🟢'
    elif resist <= 45:
        multiplier = 0.8
        verdict = 'SLIGHT_EDGE'
        emoji = '🟡'
    elif resist <= 55:
        multiplier = 1.0
        verdict = 'NEUTRAL'
        emoji = '⚪'
    elif resist <= 70:
        multiplier = 1.15
        verdict = 'DIFFICULT'
        emoji = '🟠'
    elif resist <= 85:
        multiplier = 1.3
        verdict = 'HARD'
        emoji = '🔴'
    else:
        multiplier = 1.5
        verdict = 'AVOID'
        emoji = '🔴🔴'
    
    return {
        'profile': attacker_profile,
        'dimension': dim,
        'resist_pct': resist,
        'friction_multiplier': multiplier,
        'verdict': verdict,
        'emoji': emoji
    }

def generate_best_markets(team: Dict, exploits: List[Dict]) -> List[Dict]:
    """Génère les meilleurs marchés basés sur les exploits"""
    markets = []
    
    for exploit in exploits:
        if exploit['confidence'] in ['HIGH', 'MEDIUM']:
            markets.append({
                'market': exploit['market'],
                'confidence': exploit['confidence'],
                'edge_estimate': exploit['edge_estimate'],
                'exploit_type': exploit['exploit_type'],
                'reason': exploit['reason'],
                'target_attacker': exploit['attacker_profile'],
                'condition': exploit.get('condition', 'Toujours applicable')
            })
    
    return markets[:5]

def verify_uniqueness(teams: List[Dict]) -> Dict:
    """Vérifie l'unicité des profils"""
    fingerprints = [t['fingerprint_code'] for t in teams]
    enriched_names = [t['enriched_name'] for t in teams]
    dna_strings = ['-'.join(t['dna_string']) for t in teams]
    
    return {
        'fingerprint_unique': len(set(fingerprints)) == len(fingerprints),
        'fingerprint_count': len(set(fingerprints)),
        'enriched_name_unique': len(set(enriched_names)) == len(enriched_names),
        'enriched_name_count': len(set(enriched_names)),
        'dna_string_unique': len(set(dna_strings)) == len(dna_strings),
        'dna_string_count': len(set(dna_strings)),
        'total_teams': len(teams)
    }

def main():
    print("=" * 80)
    print("🧬 DEFENSE RESPONSE MODEL (DRM) V5.0 - ULTIMATE FINGERPRINT")
    print("   96 équipes = 96 ADN 100% UNIQUES")
    print("=" * 80)
    
    # 1. Charger les données
    print("\n📂 Chargement des données V3...")
    teams = load_data()
    print(f"   ✅ {len(teams)} équipes chargées")
    
    # 2. Enrichir chaque équipe
    print("\n🔬 Génération des profils V5.0...")
    
    enriched_teams = []
    
    for team in teams:
        enriched = team.copy()
        pct = team['percentiles']
        
        # SOLUTION 1: Fingerprint numérique unique
        enriched['fingerprint_code'] = generate_fingerprint_code(team)
        enriched['fingerprint_compact'] = generate_compact_fingerprint(team)
        
        # Moyenne de l'équipe
        enriched['team_average_pct'] = round(calculate_team_average(team), 1)
        
        # SOLUTION 2: Forces et faiblesses RELATIVES
        strengths = find_relative_strengths(team)
        weaknesses = find_relative_weaknesses(team)
        enriched['relative_strengths'] = strengths[:5]
        enriched['relative_weaknesses'] = weaknesses[:5]
        
        # Exploit paths (RELATIFS)
        exploit_paths = generate_relative_exploit_paths(team, weaknesses)
        enriched['exploit_paths'] = exploit_paths
        
        # SOLUTION 3: DNA STRING complet
        dna_string = generate_dna_string(team, weaknesses, strengths)
        enriched['dna_string'] = dna_string
        enriched['dna_string_full'] = '-'.join(dna_string)
        
        # SOLUTION 4: Nommage enrichi 3 composants
        enriched['enriched_name'] = generate_enriched_name(team, strengths, weaknesses)
        enriched['short_description'] = generate_short_description(team, strengths, weaknesses)
        
        # Niveau de défense
        level = get_defense_level(pct.get('global', 50))
        enriched['defense_level'] = level
        
        # Meilleurs marchés
        enriched['best_markets'] = generate_best_markets(team, exploit_paths)
        
        # Matchup guide complet
        attacker_profiles = [
            'EARLY_BIRD', 'DIESEL', 'CLUTCH_PLAYER', 'HEADER_SPECIALIST',
            'SET_PIECE_THREAT', 'LONGSHOT_SPECIALIST', 'CLINICAL', 
            'PENALTY_TAKER', 'HOME_SPECIALIST', 'AWAY_SPECIALIST',
            'VOLUME_SHOOTER', 'POACHER', 'SUPER_SUB'
        ]
        enriched['matchup_guide'] = {
            profile: calculate_matchup_friction(team, profile)
            for profile in attacker_profiles
        }
        
        # Anti-exploits (forces)
        anti_exploits = []
        for strength in strengths[:3]:
            if strength['is_absolute_strength']:
                dim = strength['dimension']
                anti_exploits.append({
                    'dimension': dim,
                    'dimension_name': DIMENSIONS[dim]['name'],
                    'percentile': strength['percentile'],
                    'avoid': f"Attaques via {DIMENSIONS[dim]['name']}",
                    'reason': f"Force absolue: {strength['percentile']}th percentile"
                })
        enriched['anti_exploits'] = anti_exploits
        
        enriched_teams.append(enriched)
    
    print(f"   ✅ {len(enriched_teams)} profils V5.0 générés")
    
    # 3. Vérifier l'unicité
    print("\n🔍 Vérification de l'unicité...")
    uniqueness = verify_uniqueness(enriched_teams)
    print(f"   • Fingerprints uniques: {uniqueness['fingerprint_count']}/{uniqueness['total_teams']} ({'✅ 100%' if uniqueness['fingerprint_unique'] else '❌'})")
    print(f"   • Noms enrichis uniques: {uniqueness['enriched_name_count']}/{uniqueness['total_teams']} ({uniqueness['enriched_name_count']/uniqueness['total_teams']*100:.1f}%)")
    print(f"   • DNA Strings uniques: {uniqueness['dna_string_count']}/{uniqueness['total_teams']} ({uniqueness['dna_string_count']/uniqueness['total_teams']*100:.1f}%)")
    
    # 4. Sauvegarder
    print("\n�� Sauvegarde...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(enriched_teams, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # ═══════════════════════════════════════════════════════════════════
    # RAPPORT DÉTAILLÉ
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("📊 RAPPORT DRM V5.0 - ULTIMATE")
    print("=" * 80)
    
    # Exemples par niveau
    print("\n🏰 EXEMPLES PAR NIVEAU DE DÉFENSE:")
    for (low, high), level in DEFENSE_LEVELS.items():
        level_teams = [t for t in enriched_teams if low <= t['percentiles']['global'] < high]
        if level_teams:
            example = level_teams[0]
            print(f"\n   {level['emoji']} {level['name'].upper()} ({len(level_teams)} équipes):")
            print(f"      Exemple: {example['team_name']}")
            print(f"      Code: {example['fingerprint_code']}")
            print(f"      Nom: {example['enriched_name']}")
            print(f"      DNA: {example['dna_string_full']}")
            if example['exploit_paths']:
                print(f"      Exploit #1: {example['exploit_paths'][0]['market']} ({example['exploit_paths'][0]['confidence']})")
    
    # TOP exploits par marché
    print("\n" + "=" * 80)
    print("🎯 TOP CIBLES PAR MARCHÉ")
    print("=" * 80)
    
    markets_teams = {
        'First Goalscorer': [],
        'Last Goalscorer': [],
        'Header Scorer / Headed Goal': [],
        'Goal from Set Piece': [],
        'Goal from Outside Box': [],
        'Penalty Scored': [],
        'Home Team Goals': [],
        'Away Team Goals': []
    }
    
    for team in enriched_teams:
        for exploit in team['exploit_paths']:
            market = exploit['market']
            if market in markets_teams and exploit['confidence'] in ['HIGH', 'MEDIUM']:
                markets_teams[market].append({
                    'team': team['team_name'],
                    'pct': exploit['vulnerability_pct'],
                    'confidence': exploit['confidence'],
                    'type': exploit['exploit_type']
                })
    
    for market, teams_list in markets_teams.items():
        if teams_list:
            teams_list.sort(key=lambda x: x['pct'])
            print(f"\n   📌 {market}:")
            for t in teams_list[:5]:
                print(f"      • {t['team']:25} ({t['pct']}th pct) [{t['confidence']}] [{t['type']}]")
    
    # Exemple complet ARSENAL
    print("\n" + "=" * 80)
    print("📋 EXEMPLE COMPLET: ARSENAL")
    print("=" * 80)
    
    arsenal = next((t for t in enriched_teams if 'Arsenal' in t['team_name']), None)
    if arsenal:
        print(f"""
   ╔══════════════════════════════════════════════════════════════════════════════╗
   ║  {arsenal['team_name']:^74}  ║
   ╚══════════════════════════════════════════════════════════════════════════════╝
   
   🆔 FINGERPRINT CODE:
      {arsenal['fingerprint_code']}
   
   📊 FINGERPRINT COMPACT:
      {arsenal['fingerprint_compact']}
   
   🏷️ NOM ENRICHI:
      {arsenal['enriched_name']}
   
   📝 DESCRIPTION:
      {arsenal['short_description']}
   
   🧬 DNA STRING:
      {arsenal['dna_string_full']}
      Tags: {arsenal['dna_string']}
   
   📈 MOYENNE ÉQUIPE: {arsenal['team_average_pct']}th percentile
   
   💪 FORCES RELATIVES (vs moyenne équipe):
""")
        for s in arsenal['relative_strengths'][:3]:
            gap = f"+{s['gap_to_average']:.0f}" if s['gap_to_average'] > 0 else f"{s['gap_to_average']:.0f}"
            print(f"      • {s['dimension_name']:25}: {s['percentile']}th pct ({gap} pts) [{s['level']}]")
        
        print(f"""
   ⚠️ FAIBLESSES RELATIVES (vs moyenne équipe):
""")
        for w in arsenal['relative_weaknesses'][:3]:
            gap = f"-{w['gap_to_average']:.0f}" if w['gap_to_average'] > 0 else f"+{abs(w['gap_to_average']):.0f}"
            print(f"      • {w['dimension_name']:25}: {w['percentile']}th pct ({gap} pts) [{w['severity']}]")
        
        print(f"""
   🔓 EXPLOIT PATHS (Comment attaquer Arsenal):
""")
        for exp in arsenal['exploit_paths'][:4]:
            print(f"      • {exp['market']:30} [{exp['confidence']}] [{exp['exploit_type']}]")
            print(f"        └─ {exp['reason']}")
            print(f"        └─ Cibler: {exp['attacker_profile']} | Edge ~{exp['edge_estimate']}%")
        
        print(f"""
   🛡️ ANTI-EXPLOITS (Ce qui NE MARCHE PAS):
""")
        for anti in arsenal['anti_exploits'][:3]:
            print(f"      ✗ {anti['avoid']}")
            print(f"        └─ {anti['reason']}")
        
        print(f"""
   🎰 MEILLEURS MARCHÉS:
""")
        for mkt in arsenal['best_markets'][:3]:
            print(f"      • {mkt['market']} ({mkt['confidence']}) - Edge ~{mkt['edge_estimate']}%")
        
        print(f"""
   📈 MATCHUP GUIDE (Top 5):
""")
        sorted_matchups = sorted(arsenal['matchup_guide'].items(), key=lambda x: x[1]['friction_multiplier'])
        for profile, data in sorted_matchups[:5]:
            print(f"      {data['emoji']} vs {profile:20}: {data['verdict']:15} (×{data['friction_multiplier']}) [resist: {data['resist_pct']}th]")
    
    # Stats finales
    print("\n" + "=" * 80)
    print("�� STATISTIQUES FINALES")
    print("=" * 80)
    
    # Compter les niveaux
    print("\n   Distribution par niveau:")
    for (low, high), level in DEFENSE_LEVELS.items():
        count = len([t for t in enriched_teams if low <= t['percentiles']['global'] < high])
        pct = count / len(enriched_teams) * 100
        print(f"      {level['emoji']} {level['name']:12}: {count:3} ({pct:.1f}%)")
    
    # Équipes avec exploits HIGH
    high_exploits = [t for t in enriched_teams if any(e['confidence'] == 'HIGH' for e in t['exploit_paths'])]
    print(f"\n   Équipes avec exploit HIGH: {len(high_exploits)}/{len(enriched_teams)}")
    
    # Vérification finale
    print("\n" + "=" * 80)
    print("✅ VALIDATION FINALE")
    print("=" * 80)
    print(f"   • Fingerprints 100% uniques: {'✅ OUI' if uniqueness['fingerprint_unique'] else '❌ NON'}")
    print(f"   • Toutes équipes ont exploit path: {'✅ OUI' if all(t['exploit_paths'] for t in enriched_teams) else '❌ NON'}")
    print(f"   • DNA String générés: {uniqueness['dna_string_count']}/{uniqueness['total_teams']}")
    
    print("\n" + "=" * 80)
    print(f"✅ DRM V5.0 ULTIMATE COMPLET - {len(enriched_teams)} ADN UNIQUES")
    print(f"�� Fichier: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()

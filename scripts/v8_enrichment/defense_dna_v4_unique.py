#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE RESPONSE MODEL (DRM) V4.0 - UNIQUE FINGERPRINT                      ║
║  96 équipes = 96 ADN UNIQUES                                                 ║
║  Zéro catégorie générique - Personnalisation maximale                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

NOUVELLE APPROCHE:
- Chaque équipe a un PROFIL NARRATIF unique
- Rankings RELATIFS (pas juste percentiles)
- EXPLOIT PATH spécifique par équipe
- SIGNATURE METRICS (où l'équipe est extrême)
- BEST MARKETS personnalisés
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Paths
DATA_DIR = Path('/home/Mon_ps/data/defense_dna')
INPUT_FILE = DATA_DIR / 'team_defense_dna_v3.json'
OUTPUT_FILE = DATA_DIR / 'team_defense_dna_v4_unique.json'

# Dimensions avec noms lisibles
DIMENSIONS = {
    'global': 'Défense Globale',
    'aerial': 'Duels Aériens',
    'longshot': 'Tirs de Loin',
    'open_play': 'Jeu Ouvert',
    'early': 'Début de Match (0-30\')',
    'late': 'Fin de Match (60-90\')',
    'chaos': 'Discipline/Chaos',
    'home': 'À Domicile',
    'away': 'À l\'Extérieur',
    'set_piece': 'Coups de Pied Arrêtés'
}

def load_data() -> List[Dict]:
    """Charge les données V3"""
    with open(INPUT_FILE, 'r') as f:
        return json.load(f)

def get_league_context(team: Dict, all_teams: List[Dict]) -> Dict:
    """Calcule le contexte de ligue pour une équipe"""
    league = team['league']
    league_teams = [t for t in all_teams if t['league'] == league]
    
    context = {
        'league_size': len(league_teams),
        'league_ranks': {}
    }
    
    # Ranking dans la ligue pour chaque dimension
    for dim in DIMENSIONS.keys():
        key = f'resist_{dim}'
        if key in team:
            sorted_teams = sorted(league_teams, key=lambda x: x.get(key, 0), reverse=True)
            rank = next((i+1 for i, t in enumerate(sorted_teams) if t['team_name'] == team['team_name']), None)
            context['league_ranks'][dim] = rank
    
    return context

def find_signature_metrics(team: Dict, all_teams: List[Dict]) -> List[Dict]:
    """
    Trouve les 3 métriques où l'équipe est la plus EXTRÊME (positive ou négative)
    """
    signatures = []
    
    for dim, dim_name in DIMENSIONS.items():
        key = f'resist_{dim}'
        if key not in team:
            continue
        
        value = team[key]
        pct = team['percentiles'].get(dim, 50)
        
        # Calculer l'écart à la moyenne
        all_values = [t.get(key, 50) for t in all_teams]
        mean_val = np.mean(all_values)
        std_val = np.std(all_values)
        
        if std_val > 0:
            z_score = (value - mean_val) / std_val
        else:
            z_score = 0
        
        # Ranking global
        sorted_teams = sorted(all_teams, key=lambda x: x.get(key, 0), reverse=True)
        global_rank = next((i+1 for i, t in enumerate(sorted_teams) if t['team_name'] == team['team_name']), 50)
        
        signatures.append({
            'dimension': dim,
            'dimension_name': dim_name,
            'value': value,
            'percentile': pct,
            'z_score': round(z_score, 2),
            'global_rank': global_rank,
            'is_strength': pct >= 75,
            'is_weakness': pct <= 25,
            'extremity': abs(z_score)
        })
    
    # Trier par extrémité (plus extrême en premier)
    signatures.sort(key=lambda x: x['extremity'], reverse=True)
    
    return signatures

def generate_unique_profile_name(team: Dict, signatures: List[Dict]) -> str:
    """
    Génère un nom de profil UNIQUE basé sur les caractéristiques distinctives
    """
    team_name = team['team_name']
    pct = team['percentiles']
    
    # Trouver la caractéristique la plus distinctive
    top_sig = signatures[0] if signatures else None
    
    # Composants du nom
    prefix = ""
    suffix = ""
    
    # PREFIX basé sur la force globale
    if pct['global'] >= 90:
        prefix = "La Forteresse"
    elif pct['global'] >= 75:
        prefix = "Le Mur"
    elif pct['global'] >= 60:
        prefix = "Le Bouclier"
    elif pct['global'] >= 40:
        prefix = "La Ligne"
    elif pct['global'] >= 25:
        prefix = "La Passoire"
    else:
        prefix = "Le Chaos"
    
    # SUFFIX basé sur la caractéristique la plus extrême
    if top_sig:
        dim = top_sig['dimension']
        is_strong = top_sig['is_strength']
        
        suffixes_strong = {
            'early': 'Matinale',
            'late': 'Nocturne',
            'aerial': 'Aérienne',
            'set_piece': 'sur CPA',
            'chaos': 'Disciplinée',
            'home': 'Imprenable',
            'away': 'Nomade',
            'longshot': 'Anti-Frappe',
            'open_play': 'Hermétique'
        }
        
        suffixes_weak = {
            'early': 'Endormie',
            'late': 'Épuisée',
            'aerial': 'Vulnérable aux Têtes',
            'set_piece': 'Fragile sur CPA',
            'chaos': 'Indisciplinée',
            'home': 'Timide à Domicile',
            'away': 'Voyageuse Fragile',
            'longshot': 'Perméable de Loin',
            'open_play': 'Ouverte'
        }
        
        if is_strong:
            suffix = suffixes_strong.get(dim, '')
        elif top_sig['is_weakness']:
            suffix = suffixes_weak.get(dim, '')
        else:
            # Caractéristique moyenne mais distinctive par z-score
            if top_sig['z_score'] > 0:
                suffix = suffixes_strong.get(dim, '')
            else:
                suffix = suffixes_weak.get(dim, '')
    
    if suffix:
        return f"{prefix} {suffix}"
    return prefix

def generate_narrative_description(team: Dict, signatures: List[Dict], league_context: Dict) -> str:
    """
    Génère une description narrative UNIQUE pour l'équipe
    """
    team_name = team['team_name']
    pct = team['percentiles']
    league = team['league']
    league_ranks = league_context['league_ranks']
    league_size = league_context['league_size']
    
    # Trouver les 2 meilleures et 2 pires dimensions
    sorted_sigs = sorted(signatures, key=lambda x: x['percentile'], reverse=True)
    best_2 = sorted_sigs[:2]
    worst_2 = sorted_sigs[-2:]
    
    # Construire la description
    parts = []
    
    # Intro basée sur le niveau global
    global_rank = league_ranks.get('global', 10)
    if pct['global'] >= 85:
        parts.append(f"{team_name} est la {global_rank}{'ère' if global_rank == 1 else 'ème'} meilleure défense de {league}")
    elif pct['global'] >= 60:
        parts.append(f"{team_name} affiche une défense solide en {league} ({global_rank}/{league_size})")
    elif pct['global'] >= 40:
        parts.append(f"{team_name} présente une défense moyenne en {league} ({global_rank}/{league_size})")
    else:
        parts.append(f"{team_name} souffre défensivement en {league} ({global_rank}/{league_size})")
    
    # Points forts
    if best_2[0]['percentile'] >= 70:
        parts.append(f"Point fort: {best_2[0]['dimension_name']} ({best_2[0]['percentile']}ème percentile)")
    
    # Points faibles
    if worst_2[-1]['percentile'] <= 30:
        parts.append(f"Faille: {worst_2[-1]['dimension_name']} ({worst_2[-1]['percentile']}ème percentile)")
    
    # Particularité unique
    if signatures[0]['extremity'] > 1.5:
        sig = signatures[0]
        if sig['z_score'] > 0:
            parts.append(f"Signature: Exceptionnellement forte en {sig['dimension_name']} (Top {sig['global_rank']}/96)")
        else:
            parts.append(f"Signature: Particulièrement vulnérable en {sig['dimension_name']} ({97-sig['global_rank']}/96 pires)")
    
    return ". ".join(parts) + "."

def generate_exploit_paths(team: Dict, signatures: List[Dict]) -> List[Dict]:
    """
    Génère les chemins d'exploitation SPÉCIFIQUES pour cette équipe
    """
    exploit_paths = []
    pct = team['percentiles']
    
    # Analyser chaque faiblesse potentielle
    weakness_exploits = {
        'early': {
            'attacker_profile': 'EARLY_BIRD',
            'market': 'First Goalscorer',
            'tactic': 'Attaquer dans les 30 premières minutes',
            'ideal_attacker': 'Joueur qui marque souvent tôt (0-30\')'
        },
        'late': {
            'attacker_profile': 'DIESEL / CLUTCH',
            'market': 'Last Goalscorer',
            'tactic': 'Pousser en fin de match',
            'ideal_attacker': 'Joueur qui marque souvent tard (60-90\')'
        },
        'aerial': {
            'attacker_profile': 'HEADER_SPECIALIST',
            'market': 'Header Scorer / Headed Goal',
            'tactic': 'Centres et corners',
            'ideal_attacker': 'Grand joueur avec bon jeu de tête'
        },
        'set_piece': {
            'attacker_profile': 'SET_PIECE_THREAT',
            'market': 'Goal from Set Piece / Corner Goal',
            'tactic': 'Maximiser les corners et coups francs',
            'ideal_attacker': 'Spécialiste des CPA'
        },
        'longshot': {
            'attacker_profile': 'LONGSHOT_SPECIALIST',
            'market': 'Goal from Outside Box',
            'tactic': 'Tirs de 20-25m',
            'ideal_attacker': 'Tireur de loin précis'
        },
        'chaos': {
            'attacker_profile': 'CLINICAL / PENALTY_TAKER',
            'market': 'Penalty Scored',
            'tactic': 'Provoquer des fautes dans la surface',
            'ideal_attacker': 'Joueur technique qui provoque les fautes'
        },
        'away': {
            'attacker_profile': 'HOME_SPECIALIST',
            'market': 'Home Team Goals',
            'tactic': 'Exploiter quand ils jouent à l\'extérieur',
            'ideal_attacker': 'Attaquant performant à domicile',
            'condition': 'Quand cette équipe joue à l\'EXTÉRIEUR'
        },
        'home': {
            'attacker_profile': 'AWAY_SPECIALIST',
            'market': 'Away Team Goals',
            'tactic': 'Exploiter leur faiblesse à domicile',
            'ideal_attacker': 'Attaquant performant à l\'extérieur',
            'condition': 'Quand cette équipe joue à DOMICILE'
        }
    }
    
    # Trier les dimensions par faiblesse (percentile le plus bas)
    sorted_dims = sorted(
        [(dim, pct.get(dim, 50)) for dim in weakness_exploits.keys()],
        key=lambda x: x[1]
    )
    
    for dim, percentile in sorted_dims:
        if percentile <= 40:  # Vulnérabilité exploitable
            exploit = weakness_exploits[dim].copy()
            exploit['dimension'] = dim
            exploit['vulnerability_pct'] = percentile
            exploit['confidence'] = 'HIGH' if percentile <= 20 else 'MEDIUM' if percentile <= 30 else 'LOW'
            exploit['edge_estimate'] = round((50 - percentile) / 10, 1)  # Estimation de l'edge
            exploit_paths.append(exploit)
    
    return exploit_paths[:5]  # Top 5 exploits

def generate_anti_exploit(team: Dict, signatures: List[Dict]) -> List[Dict]:
    """
    Génère les approches qui NE MARCHENT PAS contre cette défense
    """
    anti_exploits = []
    pct = team['percentiles']
    
    strength_antiexploits = {
        'early': {
            'avoid': 'First Goalscorer bets',
            'reason': 'Défense très solide en début de match'
        },
        'late': {
            'avoid': 'Last Goalscorer bets',
            'reason': 'Ne s\'effondre pas en fin de match'
        },
        'aerial': {
            'avoid': 'Header Scorer / Aerial threats',
            'reason': 'Domine les duels aériens'
        },
        'set_piece': {
            'avoid': 'Set Piece goals',
            'reason': 'Très organisée sur CPA'
        },
        'longshot': {
            'avoid': 'Outside box shots',
            'reason': 'Bloque bien les tirs de loin'
        },
        'chaos': {
            'avoid': 'Penalty bets',
            'reason': 'Défense disciplinée, peu de fautes'
        },
        'home': {
            'avoid': 'Away goals (quand ils jouent à domicile)',
            'reason': 'Forteresse imprenable à domicile'
        },
        'away': {
            'avoid': 'Home goals (quand ils jouent à l\'extérieur)',
            'reason': 'Solide même en déplacement'
        }
    }
    
    for dim, antiexploit in strength_antiexploits.items():
        if pct.get(dim, 50) >= 75:
            anti_exploits.append({
                'dimension': dim,
                'strength_pct': pct[dim],
                **antiexploit
            })
    
    return anti_exploits

def generate_best_markets(team: Dict, exploit_paths: List[Dict]) -> List[Dict]:
    """
    Génère les meilleurs marchés à cibler contre cette équipe
    """
    markets = []
    
    for exploit in exploit_paths[:3]:  # Top 3
        if exploit['confidence'] in ['HIGH', 'MEDIUM']:
            markets.append({
                'market': exploit['market'],
                'confidence': exploit['confidence'],
                'edge_estimate': exploit['edge_estimate'],
                'reason': f"Vulnérabilité {exploit['dimension']} ({exploit['vulnerability_pct']}th pct)",
                'attacker_to_target': exploit['attacker_profile'],
                'condition': exploit.get('condition', 'Toujours')
            })
    
    return markets

def generate_matchup_guide(team: Dict, signatures: List[Dict]) -> Dict:
    """
    Génère un guide de matchup complet
    """
    pct = team['percentiles']
    
    # Calculer les multiplicateurs de friction raffinés
    friction_guide = {}
    
    attacker_profiles = {
        'EARLY_BIRD': 'early',
        'DIESEL': 'late',
        'CLUTCH_PLAYER': 'late',
        'HEADER_SPECIALIST': 'aerial',
        'SET_PIECE_THREAT': 'set_piece',
        'LONGSHOT_SPECIALIST': 'longshot',
        'CLINICAL': 'chaos',
        'PENALTY_TAKER': 'chaos',
        'HOME_SPECIALIST': 'away',  # Exploite la faiblesse away de la défense
        'AWAY_SPECIALIST': 'home',  # Exploite la faiblesse home de la défense
        'VOLUME_SHOOTER': 'open_play',
        'POACHER': 'aerial'
    }
    
    for profile, dim in attacker_profiles.items():
        resist = pct.get(dim, 50)
        
        # Calculer le multiplicateur
        # < 50 = avantage attaquant, > 50 = avantage défense
        if resist <= 20:
            multiplier = 0.6
            verdict = 'GOLDEN_MATCHUP'
        elif resist <= 35:
            multiplier = 0.75
            verdict = 'FAVORABLE'
        elif resist <= 50:
            multiplier = 0.9
            verdict = 'SLIGHT_EDGE'
        elif resist <= 65:
            multiplier = 1.0
            verdict = 'NEUTRAL'
        elif resist <= 80:
            multiplier = 1.15
            verdict = 'DIFFICULT'
        else:
            multiplier = 1.3
            verdict = 'AVOID'
        
        friction_guide[profile] = {
            'friction_multiplier': multiplier,
            'verdict': verdict,
            'defense_resist_pct': resist,
            'dimension': dim
        }
    
    return friction_guide

def calculate_uniqueness_score(team: Dict, all_teams: List[Dict]) -> float:
    """
    Calcule un score d'unicité (combien cette équipe est différente des autres)
    """
    team_vector = team['dna_vector']
    
    # Calculer la distance moyenne avec toutes les autres équipes
    distances = []
    for other in all_teams:
        if other['team_name'] != team['team_name']:
            other_vector = other['dna_vector']
            # Distance euclidienne
            dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(team_vector, other_vector)))
            distances.append(dist)
    
    # Score = distance moyenne (plus c'est haut, plus l'équipe est unique)
    return round(np.mean(distances), 2)

def find_similar_teams(team: Dict, all_teams: List[Dict], n: int = 3) -> List[Dict]:
    """
    Trouve les équipes avec un profil similaire
    """
    team_vector = team['dna_vector']
    
    similarities = []
    for other in all_teams:
        if other['team_name'] != team['team_name']:
            other_vector = other['dna_vector']
            dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(team_vector, other_vector)))
            similarities.append({
                'team': other['team_name'],
                'league': other['league'],
                'distance': round(dist, 2)
            })
    
    similarities.sort(key=lambda x: x['distance'])
    return similarities[:n]

def generate_radar_data(team: Dict) -> Dict:
    """
    Génère les données pour un graphique radar
    """
    return {
        'labels': list(DIMENSIONS.values()),
        'values': [
            team.get(f'resist_{dim}', 50) 
            for dim in DIMENSIONS.keys()
        ],
        'percentiles': [
            team['percentiles'].get(dim, 50)
            for dim in DIMENSIONS.keys()
        ]
    }

def main():
    print("=" * 80)
    print("🧬 DEFENSE RESPONSE MODEL (DRM) V4.0 - UNIQUE FINGERPRINT")
    print("   96 équipes = 96 ADN UNIQUES")
    print("=" * 80)
    
    # 1. Charger les données V3
    print("\n📂 Chargement des données V3...")
    teams = load_data()
    print(f"   ✅ {len(teams)} équipes chargées")
    
    # 2. Enrichir chaque équipe avec un profil unique
    print("\n🔬 Génération des profils uniques...")
    
    enriched_teams = []
    
    for team in teams:
        enriched = team.copy()
        
        # Contexte de ligue
        league_context = get_league_context(team, teams)
        enriched['league_context'] = league_context
        
        # Métriques signature
        signatures = find_signature_metrics(team, teams)
        enriched['signature_metrics'] = signatures[:5]  # Top 5
        
        # Nom de profil unique
        enriched['unique_profile_name'] = generate_unique_profile_name(team, signatures)
        
        # Description narrative
        enriched['narrative'] = generate_narrative_description(team, signatures, league_context)
        
        # Chemins d'exploitation
        exploit_paths = generate_exploit_paths(team, signatures)
        enriched['exploit_paths'] = exploit_paths
        
        # Anti-exploits (ce qui ne marche pas)
        enriched['anti_exploits'] = generate_anti_exploit(team, signatures)
        
        # Meilleurs marchés
        enriched['best_markets'] = generate_best_markets(team, exploit_paths)
        
        # Guide de matchup
        enriched['matchup_guide'] = generate_matchup_guide(team, signatures)
        
        # Score d'unicité
        enriched['uniqueness_score'] = calculate_uniqueness_score(team, teams)
        
        # Équipes similaires
        enriched['similar_teams'] = find_similar_teams(team, teams)
        
        # Données radar
        enriched['radar_data'] = generate_radar_data(team)
        
        enriched_teams.append(enriched)
    
    print(f"   ✅ {len(enriched_teams)} profils uniques générés")
    
    # 3. Sauvegarder
    print("\n💾 Sauvegarde...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(enriched_teams, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # ═══════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("📊 RAPPORT DRM V4.0 - PROFILS UNIQUES")
    print("=" * 80)
    
    # Vérifier l'unicité des noms de profils
    profile_names = [t['unique_profile_name'] for t in enriched_teams]
    unique_names = set(profile_names)
    print(f"\n📊 UNICITÉ DES PROFILS:")
    print(f"   • Noms de profils: {len(profile_names)}")
    print(f"   • Noms uniques: {len(unique_names)}")
    print(f"   • Taux d'unicité: {len(unique_names)/len(profile_names)*100:.1f}%")
    
    # Top équipes les plus uniques
    print(f"\n🎯 TOP 10 ÉQUIPES LES PLUS UNIQUES (profil distinctif):")
    sorted_by_uniqueness = sorted(enriched_teams, key=lambda x: x['uniqueness_score'], reverse=True)
    for i, t in enumerate(sorted_by_uniqueness[:10], 1):
        print(f"   {i:2}. {t['team_name']:25} | Unicité: {t['uniqueness_score']:5.1f} | {t['unique_profile_name']}")
    
    # Exemples de profils par ligue
    print(f"\n📋 EXEMPLES DE PROFILS PAR LIGUE:")
    for league in ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']:
        league_teams = [t for t in enriched_teams if t['league'] == league]
        if league_teams:
            # Prendre le plus unique de chaque ligue
            best = max(league_teams, key=lambda x: x['uniqueness_score'])
            print(f"\n   📊 {league}: {best['team_name']}")
            print(f"      Profil: {best['unique_profile_name']}")
            print(f"      {best['narrative']}")
            if best['exploit_paths']:
                print(f"      Exploit: {best['exploit_paths'][0]['market']} ({best['exploit_paths'][0]['confidence']})")
    
    # Exemple détaillé
    print("\n" + "=" * 80)
    print("📋 EXEMPLE COMPLET: ARSENAL")
    print("=" * 80)
    
    arsenal = next((t for t in enriched_teams if 'Arsenal' in t['team_name']), None)
    if arsenal:
        print(f"""
   ╔══════════════════════════════════════════════════════════════════════════╗
   ║  {arsenal['team_name']:^70}  ║
   ╚══════════════════════════════════════════════════════════════════════════╝
   
   🎯 PROFIL UNIQUE: {arsenal['unique_profile_name']}
   
   📝 NARRATIVE:
   {arsenal['narrative']}
   
   📊 SIGNATURE METRICS (Ce qui rend Arsenal unique):
""")
        for sig in arsenal['signature_metrics'][:3]:
            direction = "↑" if sig['z_score'] > 0 else "↓"
            print(f"      • {sig['dimension_name']}: {sig['value']:.1f} ({sig['percentile']}th pct) {direction} Z={sig['z_score']}")
        
        print(f"""
   🔓 EXPLOIT PATHS (Comment attaquer Arsenal):
""")
        for exp in arsenal['exploit_paths'][:3]:
            print(f"      • {exp['market']}: {exp['confidence']} (Edge ~{exp['edge_estimate']}%)")
            print(f"        → Cibler: {exp['attacker_profile']}")
        
        print(f"""
   🛡️ ANTI-EXPLOITS (Ce qui NE MARCHE PAS):
""")
        for anti in arsenal['anti_exploits'][:3]:
            print(f"      ✗ {anti['avoid']}: {anti['reason']}")
        
        print(f"""
   🎰 MEILLEURS MARCHÉS:
""")
        for mkt in arsenal['best_markets']:
            print(f"      • {mkt['market']} ({mkt['confidence']})")
        
        print(f"""
   👥 ÉQUIPES SIMILAIRES:
""")
        for sim in arsenal['similar_teams']:
            print(f"      • {sim['team']} ({sim['league']}) - Distance: {sim['distance']}")
        
        print(f"""
   📈 MATCHUP GUIDE (Friction par type d'attaquant):
""")
        for profile, data in list(arsenal['matchup_guide'].items())[:5]:
            emoji = "🟢" if data['verdict'] in ['GOLDEN_MATCHUP', 'FAVORABLE'] else "🟡" if data['verdict'] in ['SLIGHT_EDGE', 'NEUTRAL'] else "🔴"
            print(f"      {emoji} vs {profile:20}: {data['verdict']:15} (×{data['friction_multiplier']})")
    
    # Stats globales
    print("\n" + "=" * 80)
    print("📊 DISTRIBUTION DES PROFILS UNIQUES")
    print("=" * 80)
    
    # Compter les préfixes
    prefixes = {}
    for t in enriched_teams:
        prefix = t['unique_profile_name'].split()[0] + " " + t['unique_profile_name'].split()[1] if len(t['unique_profile_name'].split()) > 1 else t['unique_profile_name']
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    
    for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1]):
        print(f"   {prefix:30}: {count:3} équipes")
    
    print("\n" + "=" * 80)
    print(f"✅ DRM V4.0 COMPLET - {len(enriched_teams)} ADN UNIQUES")
    print(f"📁 Fichier: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()

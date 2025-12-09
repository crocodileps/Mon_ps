#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧤 GOALKEEPER TIMING DNA V1.0                                               ║
║  Profil de vulnérabilité temporelle COMPLET par gardien                      ║
║                                                                              ║
║  Dimensions:                                                                 ║
║  - Mi-temps (1H vs 2H)                                                       ║
║  - Périodes 15 min (0-15, 16-30, 31-45, 46-60, 61-75, 76-90, 90+)           ║
║  - Situations (OpenPlay, Corner, SetPiece, Penalty, FK)                      ║
║  - Types de tir (RightFoot, LeftFoot, Head)                                  ║
║  - Difficulté (Easy, Medium, Hard, VeryHard par xG)                         ║
║  - First Goal vulnerability                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore

# Paths
DATA_DIR = Path('/home/Mon_ps/data')
SHOTS_CACHE = DATA_DIR / 'goalkeeper_dna/all_shots_against_2025.json'
GK_V31 = DATA_DIR / 'goalkeeper_dna/goalkeeper_dna_v3_1_final.json'
GOALS_FILE = DATA_DIR / 'goal_analysis/all_goals_2025.json'
OUTPUT_FILE = DATA_DIR / 'goalkeeper_dna/goalkeeper_timing_dna_v1.json'

# Gardiens par équipe
GOALKEEPERS = {
    'Arsenal': 'David Raya', 'Aston Villa': 'Emiliano Martínez', 'Bournemouth': 'Kepa Arrizabalaga',
    'Brentford': 'Mark Flekken', 'Brighton': 'Bart Verbruggen', 'Burnley': 'James Trafford',
    'Chelsea': 'Robert Sánchez', 'Crystal Palace': 'Dean Henderson', 'Everton': 'Jordan Pickford',
    'Fulham': 'Bernd Leno', 'Leeds': 'Illan Meslier', 'Leicester': 'Mads Hermansen',
    'Liverpool': 'Alisson Becker', 'Manchester City': 'Ederson', 'Manchester United': 'André Onana',
    'Newcastle United': 'Nick Pope', 'Nottingham Forest': 'Matz Sels', 'Sunderland': 'Anthony Patterson',
    'Tottenham': 'Guglielmo Vicario', 'West Ham': 'Lukasz Fabianski', 'Wolverhampton Wanderers': 'José Sá',
    'Alaves': 'Antonio Sivera', 'Athletic Club': 'Unai Simón', 'Atletico Madrid': 'Jan Oblak',
    'Barcelona': 'Iñaki Peña', 'Celta Vigo': 'Vicente Guaita', 'Espanyol': 'Joan García',
    'Getafe': 'David Soria', 'Girona': 'Paulo Gazzaniga', 'Las Palmas': 'Jasper Cillessen',
    'Leganes': 'Marko Dmitrović', 'Levante': 'Andrés Fernández', 'Mallorca': 'Dominik Greif',
    'Osasuna': 'Sergio Herrera', 'Rayo Vallecano': 'Augusto Batalla', 'Real Betis': 'Rui Silva',
    'Real Madrid': 'Thibaut Courtois', 'Real Sociedad': 'Álex Remiro', 'Real Valladolid': 'Karl Hein',
    'Sevilla': 'Ørjan Nyland', 'Valencia': 'Giorgi Mamardashvili', 'Villarreal': 'Diego Conde',
    'Augsburg': 'Nediljko Labrović', 'Bayern Munich': 'Manuel Neuer', 'Bochum': 'Patrick Drewes',
    'Borussia Dortmund': 'Gregor Kobel', 'Borussia M.Gladbach': 'Moritz Nicolas',
    'Eintracht Frankfurt': 'Kevin Trapp', 'FC Heidenheim': 'Kevin Müller', 'Freiburg': 'Noah Atubolu',
    'Hoffenheim': 'Oliver Baumann', 'Holstein Kiel': 'Timon Weiner', 'Mainz 05': 'Robin Zentner',
    'RB Leipzig': 'Péter Gulácsi', 'St. Pauli': 'Nikola Vasilj', 'Union Berlin': 'Frederik Rønnow',
    'VfB Stuttgart': 'Alexander Nübel', 'Werder Bremen': 'Michael Zetterer', 'Wolfsburg': 'Kamil Grabara',
    'Bayer Leverkusen': 'Lukáš Hrádecký',
    'AC Milan': 'Mike Maignan', 'Atalanta': 'Marco Carnesecchi', 'Bologna': 'Łukasz Skorupski',
    'Cagliari': 'Simone Scuffet', 'Como': 'Pepe Reina', 'Empoli': 'Devis Vasquez',
    'Fiorentina': 'David de Gea', 'Genoa': 'Pierluigi Gollini', 'Hellas Verona': 'Lorenzo Montipò',
    'Inter': 'Yann Sommer', 'Juventus': 'Michele Di Gregorio', 'Lazio': 'Ivan Provedel',
    'Lecce': 'Wladimiro Falcone', 'Monza': 'Stefano Turati', 'Napoli': 'Alex Meret',
    'Parma Calcio 1913': 'Zion Suzuki', 'Roma': 'Mile Svilar', 'Torino': 'Vanja Milinković-Savić',
    'Udinese': 'Maduka Okoye', 'Venezia': 'Jesse Joronen',
    'Angers': 'Yahia Fofana', 'Auxerre': 'Donovan Léon', 'Brest': 'Marco Bizot',
    'Le Havre': 'Arthur Desmas', 'Lens': 'Brice Samba', 'Lille': 'Lucas Chevalier',
    'Lorient': 'Yvon Mvogo', 'Lyon': 'Lucas Perri', 'Marseille': 'Geronimo Rulli',
    'Metz': 'Alexandre Oukidja', 'Monaco': 'Radosław Majecki', 'Montpellier': 'Benjamin Lecomte',
    'Nantes': 'Alban Lafont', 'Nice': 'Marcin Bułka', 'Paris FC': 'Christophe Kerbrat',
    'Paris Saint Germain': 'Gianluigi Donnarumma', 'Reims': 'Yehvann Diouf', 'Rennes': 'Steve Mandanda',
    'Saint-Etienne': 'Gautier Larsonneur', 'Strasbourg': 'Djordje Petrović', 'Toulouse': 'Guillaume Restes',
}

PERIODS = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']
SITUATIONS = ['OpenPlay', 'FromCorner', 'Penalty', 'SetPiece', 'DirectFreekick']
SHOT_TYPES = ['RightFoot', 'LeftFoot', 'Head']

def get_period(minute: int) -> str:
    if minute <= 15: return '0-15'
    elif minute <= 30: return '16-30'
    elif minute <= 45: return '31-45'
    elif minute <= 60: return '46-60'
    elif minute <= 75: return '61-75'
    elif minute <= 90: return '76-90'
    else: return '90+'

def get_difficulty(xG: float) -> str:
    if xG < 0.1: return 'easy'
    elif xG < 0.3: return 'medium'
    elif xG < 0.5: return 'hard'
    else: return 'very_hard'

def main():
    print("=" * 80)
    print("🧤 GOALKEEPER TIMING DNA V1.0")
    print("   Profil de vulnérabilité temporelle COMPLET")
    print("=" * 80)
    
    # 1. Charger les données
    print("\n📂 Chargement des données...")
    
    with open(SHOTS_CACHE, 'r') as f:
        all_shots = json.load(f)
    print(f"   ✅ Cache tirs: {sum(len(s) for s in all_shots.values())} tirs")
    
    with open(GK_V31, 'r') as f:
        gk_v31 = json.load(f)
    gk_v31_dict = {gk['team']: gk for gk in gk_v31}
    print(f"   ✅ GK V3.1: {len(gk_v31)} gardiens")
    
    with open(GOALS_FILE, 'r') as f:
        all_goals = json.load(f)
    print(f"   ✅ Buts: {len(all_goals)}")
    
    # 2. Identifier les premiers buts par match
    match_first_goals = {}
    for goal in all_goals:
        match_id = goal['match_id']
        if match_id not in match_first_goals or goal['minute'] < match_first_goals[match_id]['minute']:
            match_first_goals[match_id] = goal
    
    first_goal_teams = defaultdict(int)
    for fg in match_first_goals.values():
        first_goal_teams[fg['conceding_team']] += 1
    
    print(f"   ✅ Premiers buts: {len(match_first_goals)} matchs")
    
    # 3. Analyser chaque équipe/gardien
    print("\n🔬 Analyse détaillée par gardien...")
    
    gk_profiles = []
    
    # Collecter les baselines globales
    global_stats = {
        'by_period': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0}),
        'by_situation': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0}),
        'by_shot_type': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0}),
        'by_half': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0}),
    }
    
    for team, shots in all_shots.items():
        for shot in shots:
            if shot.get('result') in ['SavedShot', 'Goal']:
                minute = int(shot.get('minute', 45))
                period = get_period(minute)
                half = '1H' if minute <= 45 else '2H'
                situation = shot.get('situation', 'OpenPlay')
                shot_type = shot.get('shotType', 'RightFoot')
                
                global_stats['by_period'][period]['shots'] += 1
                global_stats['by_half'][half]['shots'] += 1
                global_stats['by_situation'][situation]['shots'] += 1
                global_stats['by_shot_type'][shot_type]['shots'] += 1
                
                if shot.get('result') == 'SavedShot':
                    global_stats['by_period'][period]['saves'] += 1
                    global_stats['by_half'][half]['saves'] += 1
                    global_stats['by_situation'][situation]['saves'] += 1
                    global_stats['by_shot_type'][shot_type]['saves'] += 1
                else:
                    global_stats['by_period'][period]['goals'] += 1
                    global_stats['by_half'][half]['goals'] += 1
                    global_stats['by_situation'][situation]['goals'] += 1
                    global_stats['by_shot_type'][shot_type]['goals'] += 1
    
    # Calculer les save rates de baseline
    baseline = {}
    for category in ['by_period', 'by_half', 'by_situation', 'by_shot_type']:
        baseline[category] = {}
        for key, data in global_stats[category].items():
            if data['shots'] > 0:
                baseline[category][key] = data['saves'] / data['shots'] * 100
    
    print(f"\n📊 BASELINES GLOBALES:")
    print(f"   Par mi-temps: 1H={baseline['by_half'].get('1H', 0):.1f}%, 2H={baseline['by_half'].get('2H', 0):.1f}%")
    
    # Analyser chaque gardien
    for team, shots in all_shots.items():
        goalkeeper = GOALKEEPERS.get(team, f"GK {team}")
        v31_data = gk_v31_dict.get(team, {})
        
        # Stats par dimension
        stats = {
            'by_period': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0}),
            'by_half': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0}),
            'by_situation': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0}),
            'by_shot_type': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0}),
            'by_difficulty': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0}),
        }
        
        total_shots = 0
        total_saves = 0
        total_goals = 0
        total_xG = 0
        
        for shot in shots:
            if shot.get('result') not in ['SavedShot', 'Goal']:
                continue
            
            minute = int(shot.get('minute', 45))
            xG = float(shot.get('xG', 0))
            period = get_period(minute)
            half = '1H' if minute <= 45 else '2H'
            situation = shot.get('situation', 'OpenPlay')
            shot_type = shot.get('shotType', 'RightFoot')
            difficulty = get_difficulty(xG)
            is_save = shot.get('result') == 'SavedShot'
            
            total_shots += 1
            total_xG += xG
            
            for cat, key in [('by_period', period), ('by_half', half), 
                            ('by_situation', situation), ('by_shot_type', shot_type),
                            ('by_difficulty', difficulty)]:
                stats[cat][key]['shots'] += 1
                stats[cat][key]['xG'] += xG
                if is_save:
                    stats[cat][key]['saves'] += 1
                else:
                    stats[cat][key]['goals'] += 1
            
            if is_save:
                total_saves += 1
            else:
                total_goals += 1
        
        if total_shots < 20:  # Minimum pour analyse significative
            continue
        
        # Calculer les métriques
        profile = {
            'goalkeeper': goalkeeper,
            'team': team,
            
            # Stats V3.1
            'gk_performance': v31_data.get('gk_performance', 0),
            'gk_percentile': v31_data.get('gk_percentile', 50),
            'profile_v31': v31_data.get('profile', 'AVERAGE'),
            
            # Totaux
            'total_shots': total_shots,
            'total_saves': total_saves,
            'total_goals': total_goals,
            'total_xG': round(total_xG, 2),
            'save_rate': round(total_saves / total_shots * 100, 1),
            
            # First Goal
            'first_goals_conceded': first_goal_teams.get(team, 0),
            
            # Détails par dimension
            'timing': {},
            'situations': {},
            'shot_types': {},
            'difficulty': {},
            
            # Vulnérabilités
            'vulnerabilities': [],
            'strengths': [],
            
            # Tags
            'timing_tags': [],
        }
        
        # Analyser chaque dimension et comparer à baseline
        
        # === TIMING (Périodes) ===
        for period in PERIODS:
            data = stats['by_period'][period]
            if data['shots'] >= 3:
                save_rate = data['saves'] / data['shots'] * 100
                baseline_rate = baseline['by_period'].get(period, 67)
                diff = save_rate - baseline_rate
                
                profile['timing'][period] = {
                    'shots': data['shots'],
                    'saves': data['saves'],
                    'goals': data['goals'],
                    'save_rate': round(save_rate, 1),
                    'vs_baseline': round(diff, 1),
                    'xG': round(data['xG'], 2)
                }
                
                if diff <= -15 and data['shots'] >= 5:
                    profile['vulnerabilities'].append(f"PERIOD_{period.replace('-', '_')}_WEAK")
                elif diff >= 15 and data['shots'] >= 5:
                    profile['strengths'].append(f"PERIOD_{period.replace('-', '_')}_STRONG")
        
        # === MI-TEMPS ===
        for half in ['1H', '2H']:
            data = stats['by_half'][half]
            if data['shots'] >= 5:
                save_rate = data['saves'] / data['shots'] * 100
                baseline_rate = baseline['by_half'].get(half, 67)
                diff = save_rate - baseline_rate
                
                profile['timing'][half] = {
                    'shots': data['shots'],
                    'saves': data['saves'],
                    'goals': data['goals'],
                    'save_rate': round(save_rate, 1),
                    'vs_baseline': round(diff, 1),
                    'goal_pct': round(data['goals'] / total_goals * 100, 1) if total_goals > 0 else 0
                }
        
        # Tags timing
        if profile['timing'].get('1H', {}).get('goal_pct', 0) >= 55:
            profile['timing_tags'].append('SLOW_STARTER')
        if profile['timing'].get('2H', {}).get('goal_pct', 0) >= 65:
            profile['timing_tags'].append('SECOND_HALF_COLLAPSER')
        
        early_goals = stats['by_period']['0-15']['goals'] + stats['by_period']['16-30']['goals']
        if total_goals > 0 and early_goals / total_goals >= 0.30:
            profile['timing_tags'].append('EARLY_VULNERABLE')
        
        late_goals = stats['by_period']['76-90']['goals'] + stats['by_period']['90+']['goals']
        if total_goals > 0 and late_goals / total_goals >= 0.30:
            profile['timing_tags'].append('LATE_VULNERABLE')
        
        # === SITUATIONS ===
        for situation in SITUATIONS:
            data = stats['by_situation'][situation]
            if data['shots'] >= 3:
                save_rate = data['saves'] / data['shots'] * 100
                baseline_rate = baseline['by_situation'].get(situation, 67)
                diff = save_rate - baseline_rate
                
                profile['situations'][situation] = {
                    'shots': data['shots'],
                    'saves': data['saves'],
                    'goals': data['goals'],
                    'save_rate': round(save_rate, 1),
                    'vs_baseline': round(diff, 1)
                }
                
                if diff <= -15 and data['shots'] >= 5:
                    profile['vulnerabilities'].append(f"{situation.upper()}_WEAK")
                elif diff >= 15 and data['shots'] >= 5:
                    profile['strengths'].append(f"{situation.upper()}_STRONG")
        
        # === TYPES DE TIR ===
        for shot_type in SHOT_TYPES:
            data = stats['by_shot_type'][shot_type]
            if data['shots'] >= 3:
                save_rate = data['saves'] / data['shots'] * 100
                baseline_rate = baseline['by_shot_type'].get(shot_type, 67)
                diff = save_rate - baseline_rate
                
                profile['shot_types'][shot_type] = {
                    'shots': data['shots'],
                    'saves': data['saves'],
                    'goals': data['goals'],
                    'save_rate': round(save_rate, 1),
                    'vs_baseline': round(diff, 1)
                }
                
                if diff <= -15 and data['shots'] >= 5:
                    profile['vulnerabilities'].append(f"{shot_type.upper()}_WEAK")
                elif diff >= 15 and data['shots'] >= 5:
                    profile['strengths'].append(f"{shot_type.upper()}_STRONG")
        
        # === DIFFICULTÉ ===
        for diff_level in ['easy', 'medium', 'hard', 'very_hard']:
            data = stats['by_difficulty'][diff_level]
            if data['shots'] >= 3:
                save_rate = data['saves'] / data['shots'] * 100
                
                profile['difficulty'][diff_level] = {
                    'shots': data['shots'],
                    'saves': data['saves'],
                    'goals': data['goals'],
                    'save_rate': round(save_rate, 1)
                }
        
        # === EXPLOIT PATHS ===
        profile['exploit_paths'] = []
        
        # First Goalscorer
        if 'SLOW_STARTER' in profile['timing_tags'] or 'EARLY_VULNERABLE' in profile['timing_tags']:
            profile['exploit_paths'].append({
                'market': 'First Goalscorer',
                'reason': 'Vulnérable en début de match',
                'confidence': 'HIGH' if 'EARLY_VULNERABLE' in profile['timing_tags'] else 'MEDIUM',
                'edge': 4.5 if 'EARLY_VULNERABLE' in profile['timing_tags'] else 3.0
            })
        
        # Last Goalscorer
        if 'SECOND_HALF_COLLAPSER' in profile['timing_tags'] or 'LATE_VULNERABLE' in profile['timing_tags']:
            profile['exploit_paths'].append({
                'market': 'Last Goalscorer',
                'reason': 'Vulnérable en fin de match',
                'confidence': 'HIGH' if 'LATE_VULNERABLE' in profile['timing_tags'] else 'MEDIUM',
                'edge': 4.5 if 'LATE_VULNERABLE' in profile['timing_tags'] else 3.0
            })
        
        # Header Goal
        if 'HEAD_WEAK' in profile['vulnerabilities']:
            profile['exploit_paths'].append({
                'market': 'Header Goal',
                'reason': 'Faible sur les têtes',
                'confidence': 'HIGH',
                'edge': 5.0
            })
        
        # Corner Goal
        if 'FROMCORNER_WEAK' in profile['vulnerabilities']:
            profile['exploit_paths'].append({
                'market': 'Corner Goal',
                'reason': 'Faible sur corners',
                'confidence': 'HIGH',
                'edge': 4.5
            })
        
        # Goals Over (basé sur performance V3.1)
        if profile['gk_performance'] <= -5:
            profile['exploit_paths'].append({
                'market': 'Goals Over',
                'reason': f"Sous-performance globale ({profile['gk_performance']:+.1f})",
                'confidence': 'HIGH',
                'edge': abs(profile['gk_performance']) * 0.8
            })
        
        # === ENRICHED NAME ===
        parts = []
        if profile['gk_performance'] >= 5:
            parts.append("Mur")
        elif profile['gk_performance'] >= 2:
            parts.append("Solide")
        elif profile['gk_performance'] >= -2:
            parts.append("Moyen")
        elif profile['gk_performance'] >= -5:
            parts.append("Fragile")
        else:
            parts.append("Passoire")
        
        if profile['timing_tags']:
            parts.append(profile['timing_tags'][0].replace('_', ' ').title())
        
        if profile['vulnerabilities']:
            vuln = profile['vulnerabilities'][0].replace('_WEAK', '').replace('_', ' ').title()
            parts.append(f"({vuln} Faible)")
        
        profile['enriched_name'] = ' | '.join(parts[:3])
        
        # === FINGERPRINT ===
        h1_sr = profile['timing'].get('1H', {}).get('save_rate', 0)
        h2_sr = profile['timing'].get('2H', {}).get('save_rate', 0)
        profile['timing_fingerprint'] = f"GKT-{int(h1_sr)}-{int(h2_sr)}-{total_goals}"
        
        gk_profiles.append(profile)
    
    print(f"   ✅ {len(gk_profiles)} gardiens profilés")
    
    # 4. Calculer les percentiles pour timing
    print("\n📊 Calcul des percentiles timing...")
    
    all_1h_sr = [p['timing'].get('1H', {}).get('save_rate', 67) for p in gk_profiles]
    all_2h_sr = [p['timing'].get('2H', {}).get('save_rate', 67) for p in gk_profiles]
    
    for profile in gk_profiles:
        h1_sr = profile['timing'].get('1H', {}).get('save_rate', 67)
        h2_sr = profile['timing'].get('2H', {}).get('save_rate', 67)
        
        profile['percentiles'] = {
            '1H_save_rate': round(percentileofscore(all_1h_sr, h1_sr, kind='rank'), 0),
            '2H_save_rate': round(percentileofscore(all_2h_sr, h2_sr, kind='rank'), 0),
        }
    
    # 5. Sauvegarder
    print("\n💾 Sauvegarde...")
    
    # Trier par performance
    gk_profiles.sort(key=lambda x: x['gk_performance'], reverse=True)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(gk_profiles, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_FILE}")
    
    # 6. Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT GOALKEEPER TIMING DNA")
    print("=" * 80)
    
    # Distribution des tags
    print("\n📈 DISTRIBUTION DES TAGS TIMING:")
    tag_counts = defaultdict(int)
    for p in gk_profiles:
        for tag in p['timing_tags']:
            tag_counts[tag] += 1
    
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        pct = count / len(gk_profiles) * 100
        bar = '█' * int(pct / 2)
        print(f"   {tag:<25}: {count:2} ({pct:5.1f}%) {bar}")
    
    # Top vulnérables 2H
    print("\n🔴 TOP 10 - SECOND HALF COLLAPSERS:")
    collapsers = sorted(gk_profiles, key=lambda x: x['timing'].get('2H', {}).get('save_rate', 100))[:10]
    print(f"   {'Gardien':<25} | {'Équipe':<20} | {'1H SR':<8} | {'2H SR':<8} | {'Diff':<8}")
    print("   " + "-" * 85)
    for gk in collapsers:
        h1 = gk['timing'].get('1H', {}).get('save_rate', 0)
        h2 = gk['timing'].get('2H', {}).get('save_rate', 0)
        diff = h2 - h1
        print(f"   {gk['goalkeeper']:<25} | {gk['team']:<20} | {h1:6.1f}% | {h2:6.1f}% | {diff:+6.1f}%")
    
    # Top vulnérables 1H (Slow Starters)
    print("\n🔴 TOP 10 - SLOW STARTERS:")
    slow = sorted(gk_profiles, key=lambda x: x['timing'].get('1H', {}).get('save_rate', 100))[:10]
    print(f"   {'Gardien':<25} | {'Équipe':<20} | {'1H SR':<8} | {'2H SR':<8} | {'Diff':<8}")
    print("   " + "-" * 85)
    for gk in slow:
        h1 = gk['timing'].get('1H', {}).get('save_rate', 0)
        h2 = gk['timing'].get('2H', {}).get('save_rate', 0)
        diff = h1 - h2
        print(f"   {gk['goalkeeper']:<25} | {gk['team']:<20} | {h1:6.1f}% | {h2:6.1f}% | {diff:+6.1f}%")
    
    # Exemple complet
    print("\n" + "=" * 80)
    print("📋 EXEMPLE COMPLET: Kevin Trapp (Cible #1)")
    print("=" * 80)
    
    trapp = [p for p in gk_profiles if 'Trapp' in p['goalkeeper']]
    if trapp:
        t = trapp[0]
        print(f"\n   Gardien: {t['goalkeeper']} ({t['team']})")
        print(f"   Performance V3.1: {t['gk_performance']:+.2f} ({t['profile_v31']})")
        print(f"   Save Rate: {t['save_rate']:.1f}%")
        print(f"\n   🕐 TIMING:")
        print(f"      1ère mi-temps: {t['timing'].get('1H', {}).get('save_rate', 0):.1f}% ({t['timing'].get('1H', {}).get('saves', 0)}/{t['timing'].get('1H', {}).get('shots', 0)} arrêts)")
        print(f"      2ème mi-temps: {t['timing'].get('2H', {}).get('save_rate', 0):.1f}% ({t['timing'].get('2H', {}).get('saves', 0)}/{t['timing'].get('2H', {}).get('shots', 0)} arrêts)")
        
        print(f"\n   ⏱️ PAR PÉRIODE:")
        for period in PERIODS:
            data = t['timing'].get(period, {})
            if data:
                sr = data.get('save_rate', 0)
                vs = data.get('vs_baseline', 0)
                status = '🔴' if vs <= -10 else '🟡' if vs <= 0 else '🟢'
                print(f"      {period:>5}: {sr:5.1f}% (vs baseline: {vs:+.1f}%) {status}")
        
        print(f"\n   🎯 SITUATIONS:")
        for sit, data in t['situations'].items():
            sr = data.get('save_rate', 0)
            vs = data.get('vs_baseline', 0)
            status = '🔴' if vs <= -10 else '🟡' if vs <= 0 else '🟢'
            print(f"      {sit:<15}: {sr:5.1f}% (vs baseline: {vs:+.1f}%) {status}")
        
        print(f"\n   🦶 TYPES DE TIR:")
        for typ, data in t['shot_types'].items():
            sr = data.get('save_rate', 0)
            vs = data.get('vs_baseline', 0)
            status = '🔴' if vs <= -10 else '🟡' if vs <= 0 else '🟢'
            print(f"      {typ:<10}: {sr:5.1f}% (vs baseline: {vs:+.1f}%) {status}")
        
        print(f"\n   🏷️ TAGS: {t['timing_tags']}")
        print(f"   ⚠️ VULNÉRABILITÉS: {t['vulnerabilities']}")
        print(f"   💪 FORCES: {t['strengths']}")
        
        print(f"\n   🎰 EXPLOIT PATHS:")
        for exp in t['exploit_paths']:
            print(f"      • {exp['market']:<20} [{exp['confidence']}] Edge: {exp['edge']:.1f}%")
            print(f"        Raison: {exp['reason']}")
        
        print(f"\n   📛 Enriched Name: {t['enriched_name']}")
        print(f"   🆔 Fingerprint: {t['timing_fingerprint']}")
    
    print(f"\n{'=' * 80}")
    print(f"✅ GOALKEEPER TIMING DNA COMPLET - {len(gk_profiles)} gardiens")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()

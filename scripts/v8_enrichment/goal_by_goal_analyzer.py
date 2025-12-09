#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚽ GOAL-BY-GOAL ANALYZER V1.0                                               ║
║  Phase 3.5b - Analyse détaillée de TOUS les buts 2025/2026                   ║
║                                                                              ║
║  Données extraites:                                                          ║
║  - Minute exacte de chaque but                                               ║
║  - Situation (OpenPlay, Corner, SetPiece, Penalty, FK)                       ║
║  - Type de tir (RightFoot, LeftFoot, Head)                                   ║
║  - xG du tir                                                                 ║
║  - Buteur, passeur, équipe                                                   ║
║  - Gardien battu                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy import stats
from datetime import datetime

# Paths
DATA_DIR = Path('/home/Mon_ps/data')
SHOTS_CACHE = DATA_DIR / 'goalkeeper_dna/all_shots_against_2025.json'
GK_DNA = DATA_DIR / 'goalkeeper_dna/goalkeeper_dna_v3_1_final.json'
OUTPUT_DIR = DATA_DIR / 'goal_analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def get_timing_period(minute: int) -> str:
    """Retourne la période de timing"""
    if minute <= 15:
        return '0-15'
    elif minute <= 30:
        return '16-30'
    elif minute <= 45:
        return '31-45'
    elif minute <= 60:
        return '46-60'
    elif minute <= 75:
        return '61-75'
    elif minute <= 90:
        return '76-90'
    else:
        return '90+'

def get_half(minute: int) -> str:
    """Retourne la mi-temps"""
    return '1H' if minute <= 45 else '2H'

def main():
    print("=" * 80)
    print("⚽ GOAL-BY-GOAL ANALYZER V1.0")
    print("   Phase 3.5b - Analyse détaillée de tous les buts 2025/2026")
    print("=" * 80)
    
    # 1. Charger le cache des tirs
    print("\n📂 Chargement du cache des tirs...")
    with open(SHOTS_CACHE, 'r') as f:
        all_shots = json.load(f)
    
    total_shots = sum(len(shots) for shots in all_shots.values())
    print(f"   ✅ {len(all_shots)} équipes | {total_shots} tirs totaux")
    
    # 2. Extraire TOUS les buts
    print("\n⚽ Extraction des buts...")
    all_goals = []
    
    for team_against, shots in all_shots.items():
        goalkeeper = GOALKEEPERS.get(team_against, f"GK {team_against}")
        
        for shot in shots:
            if shot.get('result') == 'Goal':
                goal = {
                    'id': shot.get('id'),
                    'match_id': shot.get('match_id'),
                    'date': shot.get('date', ''),
                    
                    # Buteur
                    'scorer': shot.get('player', 'Unknown'),
                    'scorer_id': shot.get('player_id'),
                    'assister': shot.get('player_assisted'),
                    'last_action': shot.get('lastAction'),
                    
                    # Équipes
                    'scoring_team': shot.get('h_team') if shot.get('h_a') == 'h' else shot.get('a_team'),
                    'conceding_team': team_against,
                    'goalkeeper_beaten': goalkeeper,
                    'home_away': shot.get('h_a'),
                    
                    # Timing
                    'minute': int(shot.get('minute', 45)),
                    'timing_period': get_timing_period(int(shot.get('minute', 45))),
                    'half': get_half(int(shot.get('minute', 45))),
                    
                    # Caractéristiques du tir
                    'xG': float(shot.get('xG', 0)),
                    'situation': shot.get('situation', 'OpenPlay'),
                    'shot_type': shot.get('shotType', 'RightFoot'),
                    'X': float(shot.get('X', 0)),
                    'Y': float(shot.get('Y', 0)),
                    
                    # Score du match
                    'h_goals': shot.get('h_goals'),
                    'a_goals': shot.get('a_goals'),
                }
                all_goals.append(goal)
    
    print(f"   ✅ {len(all_goals)} buts extraits")
    
    # 3. Analyses globales
    print("\n" + "=" * 80)
    print("📊 ANALYSES GLOBALES")
    print("=" * 80)
    
    # Par mi-temps
    print("\n📈 BUTS PAR MI-TEMPS:")
    half_counts = defaultdict(int)
    for goal in all_goals:
        half_counts[goal['half']] += 1
    
    total = len(all_goals)
    for half in ['1H', '2H']:
        count = half_counts[half]
        pct = count / total * 100
        bar = '█' * int(pct / 2)
        print(f"   {half}: {count:4} ({pct:5.1f}%) {bar}")
    
    # Par période de 15 min
    print("\n📈 BUTS PAR PÉRIODE (15 min):")
    period_counts = defaultdict(int)
    for goal in all_goals:
        period_counts[goal['timing_period']] += 1
    
    periods = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']
    for period in periods:
        count = period_counts[period]
        pct = count / total * 100
        bar = '█' * int(pct)
        print(f"   {period:>5}: {count:4} ({pct:5.1f}%) {bar}")
    
    # Par situation
    print("\n📈 BUTS PAR SITUATION:")
    situation_counts = defaultdict(int)
    for goal in all_goals:
        situation_counts[goal['situation']] += 1
    
    for sit, count in sorted(situation_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = '█' * int(pct)
        print(f"   {sit:<15}: {count:4} ({pct:5.1f}%) {bar}")
    
    # Par type de tir
    print("\n📈 BUTS PAR TYPE DE TIR:")
    type_counts = defaultdict(int)
    for goal in all_goals:
        type_counts[goal['shot_type']] += 1
    
    for typ, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = '█' * int(pct)
        print(f"   {typ:<10}: {count:4} ({pct:5.1f}%) {bar}")
    
    # xG moyen par période
    print("\n📈 xG MOYEN PAR PÉRIODE:")
    period_xg = defaultdict(list)
    for goal in all_goals:
        period_xg[goal['timing_period']].append(goal['xG'])
    
    for period in periods:
        xgs = period_xg[period]
        if xgs:
            avg = np.mean(xgs)
            print(f"   {period:>5}: {avg:.3f} xG moyen")
    
    # 4. Analyse par gardien
    print("\n" + "=" * 80)
    print("🧤 ANALYSE PAR GARDIEN - VULNÉRABILITÉ TEMPORELLE")
    print("=" * 80)
    
    gk_goals = defaultdict(list)
    for goal in all_goals:
        gk_goals[goal['goalkeeper_beaten']].append(goal)
    
    gk_timing_profiles = []
    
    for gk_name, goals in gk_goals.items():
        if len(goals) < 5:  # Minimum 5 buts pour analyse significative
            continue
        
        team = goals[0]['conceding_team']
        total_goals = len(goals)
        
        # Comptage par période
        period_dist = defaultdict(int)
        half_dist = defaultdict(int)
        situation_dist = defaultdict(int)
        type_dist = defaultdict(int)
        
        for goal in goals:
            period_dist[goal['timing_period']] += 1
            half_dist[goal['half']] += 1
            situation_dist[goal['situation']] += 1
            type_dist[goal['shot_type']] += 1
        
        # Calculer les pourcentages
        h1_pct = half_dist['1H'] / total_goals * 100
        h2_pct = half_dist['2H'] / total_goals * 100
        
        early_pct = (period_dist['0-15'] + period_dist['16-30']) / total_goals * 100
        late_pct = (period_dist['76-90'] + period_dist.get('90+', 0)) / total_goals * 100
        
        # Profil
        profile = {
            'goalkeeper': gk_name,
            'team': team,
            'total_goals': total_goals,
            
            # Mi-temps
            'goals_1H': half_dist['1H'],
            'goals_2H': half_dist['2H'],
            'pct_1H': round(h1_pct, 1),
            'pct_2H': round(h2_pct, 1),
            
            # Périodes détaillées
            'by_period': {p: period_dist[p] for p in periods},
            'pct_early': round(early_pct, 1),
            'pct_late': round(late_pct, 1),
            
            # Situations
            'by_situation': dict(situation_dist),
            
            # Types de tir
            'by_shot_type': dict(type_dist),
            
            # Tags
            'tags': []
        }
        
        # Assigner tags
        # Baseline: 1H ≈ 45%, 2H ≈ 55%
        if h1_pct >= 55:
            profile['tags'].append('SLOW_STARTER')
        if h2_pct >= 65:
            profile['tags'].append('SECOND_HALF_COLLAPSER')
        if early_pct >= 30:
            profile['tags'].append('EARLY_VULNERABLE')
        if late_pct >= 30:
            profile['tags'].append('LATE_VULNERABLE')
        
        # Par situation
        header_pct = type_dist.get('Head', 0) / total_goals * 100
        if header_pct >= 25:
            profile['tags'].append('HEADER_VULNERABLE')
        
        corner_pct = situation_dist.get('FromCorner', 0) / total_goals * 100
        if corner_pct >= 20:
            profile['tags'].append('CORNER_VULNERABLE')
        
        penalty_pct = situation_dist.get('Penalty', 0) / total_goals * 100
        if penalty_pct >= 15:
            profile['tags'].append('PENALTY_CONCEDER')
        
        gk_timing_profiles.append(profile)
    
    # Trier par % 2ème mi-temps (plus vulnérables tard)
    gk_timing_profiles.sort(key=lambda x: x['pct_2H'], reverse=True)
    
    # Afficher les plus vulnérables en 2H
    print("\n🔴 TOP 10 - VULNÉRABLES EN 2ÈME MI-TEMPS:")
    print(f"   {'Gardien':<25} | {'Équipe':<20} | {'1H':<8} | {'2H':<8} | Tags")
    print("   " + "-" * 90)
    for gk in gk_timing_profiles[:10]:
        tags = ', '.join(gk['tags'][:2]) if gk['tags'] else '-'
        print(f"   {gk['goalkeeper']:<25} | {gk['team']:<20} | {gk['pct_1H']:5.1f}% | {gk['pct_2H']:5.1f}% | {tags}")
    
    # Les plus vulnérables en 1H (slow starters)
    gk_timing_profiles.sort(key=lambda x: x['pct_1H'], reverse=True)
    print("\n🔴 TOP 10 - SLOW STARTERS (Vulnérables en 1ère mi-temps):")
    print(f"   {'Gardien':<25} | {'Équipe':<20} | {'1H':<8} | {'2H':<8} | Tags")
    print("   " + "-" * 90)
    for gk in gk_timing_profiles[:10]:
        tags = ', '.join(gk['tags'][:2]) if gk['tags'] else '-'
        print(f"   {gk['goalkeeper']:<25} | {gk['team']:<20} | {gk['pct_1H']:5.1f}% | {gk['pct_2H']:5.1f}% | {tags}")
    
    # 5. Analyse détaillée par période
    print("\n" + "=" * 80)
    print("📊 VULNÉRABILITÉ PAR PÉRIODE DÉTAILLÉE")
    print("=" * 80)
    
    # Calculer les percentiles pour chaque période
    for period in periods:
        period_pcts = []
        for gk in gk_timing_profiles:
            if gk['total_goals'] >= 8:  # Minimum significatif
                pct = gk['by_period'].get(period, 0) / gk['total_goals'] * 100
                period_pcts.append((gk['goalkeeper'], gk['team'], pct, gk['total_goals']))
        
        if period_pcts:
            period_pcts.sort(key=lambda x: x[2], reverse=True)
            
            print(f"\n⏱️ PÉRIODE {period} - TOP 5 VULNÉRABLES:")
            for i, (gk, team, pct, goals) in enumerate(period_pcts[:5], 1):
                print(f"   {i}. {gk:<22} ({team:<18}) | {pct:5.1f}% ({int(pct*goals/100)}/{goals} buts)")
    
    # 6. Top buteurs
    print("\n" + "=" * 80)
    print("🎯 TOP 20 BUTEURS 2025/2026")
    print("=" * 80)
    
    scorer_goals = defaultdict(list)
    for goal in all_goals:
        scorer_goals[goal['scorer']].append(goal)
    
    top_scorers = sorted(scorer_goals.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    
    print(f"\n   {'Buteur':<25} | {'Équipe':<18} | {'Buts':<5} | {'xG Tot':<7} | {'1H/2H':<8} | Situations")
    print("   " + "-" * 100)
    
    for scorer, goals in top_scorers:
        team = goals[0]['scoring_team']
        total = len(goals)
        total_xg = sum(g['xG'] for g in goals)
        h1 = sum(1 for g in goals if g['half'] == '1H')
        h2 = sum(1 for g in goals if g['half'] == '2H')
        
        situations = defaultdict(int)
        for g in goals:
            situations[g['situation']] += 1
        sit_str = ', '.join([f"{s[:3]}:{c}" for s, c in sorted(situations.items(), key=lambda x: -x[1])[:3]])
        
        print(f"   {scorer:<25} | {team:<18} | {total:4} | {total_xg:6.2f} | {h1:2}/{h2:<2}   | {sit_str}")
    
    # 7. Analyse First Goalscorer
    print("\n" + "=" * 80)
    print("🥇 ANALYSE FIRST GOALSCORER")
    print("=" * 80)
    
    # Grouper les buts par match et trouver le premier
    match_goals = defaultdict(list)
    for goal in all_goals:
        match_goals[goal['match_id']].append(goal)
    
    first_goals = []
    for match_id, goals in match_goals.items():
        if goals:
            # Trier par minute
            goals.sort(key=lambda x: x['minute'])
            first_goals.append(goals[0])
    
    print(f"\n   Total matchs avec buts: {len(first_goals)}")
    
    # Timing des premiers buts
    print("\n📈 TIMING DES PREMIERS BUTS:")
    fg_periods = defaultdict(int)
    for fg in first_goals:
        fg_periods[fg['timing_period']] += 1
    
    for period in periods:
        count = fg_periods[period]
        pct = count / len(first_goals) * 100
        bar = '█' * int(pct)
        print(f"   {period:>5}: {count:3} ({pct:5.1f}%) {bar}")
    
    # Top First Goalscorers
    print("\n🏆 TOP 10 FIRST GOALSCORERS:")
    fg_scorers = defaultdict(int)
    for fg in first_goals:
        fg_scorers[fg['scorer']] += 1
    
    for i, (scorer, count) in enumerate(sorted(fg_scorers.items(), key=lambda x: -x[1])[:10], 1):
        total_goals = len(scorer_goals[scorer])
        fg_pct = count / total_goals * 100 if total_goals > 0 else 0
        print(f"   {i:2}. {scorer:<25} | {count} FG / {total_goals} total ({fg_pct:.0f}%)")
    
    # 8. Sauvegarder les données
    print("\n" + "=" * 80)
    print("💾 SAUVEGARDE")
    print("=" * 80)
    
    # Tous les buts
    with open(OUTPUT_DIR / 'all_goals_2025.json', 'w') as f:
        json.dump(all_goals, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'all_goals_2025.json'}")
    
    # Profils timing gardiens
    with open(OUTPUT_DIR / 'gk_timing_profiles.json', 'w') as f:
        json.dump(gk_timing_profiles, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'gk_timing_profiles.json'}")
    
    # Stats buteurs
    scorer_stats = []
    for scorer, goals in scorer_goals.items():
        if len(goals) >= 3:
            scorer_stats.append({
                'scorer': scorer,
                'team': goals[0]['scoring_team'],
                'total_goals': len(goals),
                'total_xG': round(sum(g['xG'] for g in goals), 2),
                'goals_1H': sum(1 for g in goals if g['half'] == '1H'),
                'goals_2H': sum(1 for g in goals if g['half'] == '2H'),
                'first_goals': fg_scorers.get(scorer, 0),
                'by_situation': dict(defaultdict(int, {g['situation']: 1 for g in goals})),
                'by_shot_type': dict(defaultdict(int, {g['shot_type']: 1 for g in goals})),
                'avg_minute': round(np.mean([g['minute'] for g in goals]), 1)
            })
    
    scorer_stats.sort(key=lambda x: x['total_goals'], reverse=True)
    
    with open(OUTPUT_DIR / 'scorer_profiles_2025.json', 'w') as f:
        json.dump(scorer_stats, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'scorer_profiles_2025.json'}")
    
    # Résumé global
    summary = {
        'season': '2025/2026',
        'total_goals': len(all_goals),
        'total_matches': len(match_goals),
        'goals_per_match': round(len(all_goals) / len(match_goals), 2),
        'by_half': dict(half_counts),
        'by_period': dict(period_counts),
        'by_situation': dict(situation_counts),
        'by_shot_type': dict(type_counts),
        'first_goal_timing': dict(fg_periods)
    }
    
    with open(OUTPUT_DIR / 'goals_summary_2025.json', 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'goals_summary_2025.json'}")
    
    print("\n" + "=" * 80)
    print(f"✅ GOAL-BY-GOAL ANALYZER COMPLET")
    print(f"   {len(all_goals)} buts analysés | {len(gk_timing_profiles)} gardiens profilés")
    print("=" * 80)

if __name__ == '__main__':
    main()

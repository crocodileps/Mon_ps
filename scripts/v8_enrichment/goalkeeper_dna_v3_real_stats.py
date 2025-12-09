#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧤 GOALKEEPER DNA V3.0 - VRAIES STATS D'ARRÊTS                              ║
║  Hedge Fund Grade - Performance RÉELLE du gardien                            ║
║                                                                              ║
║  Méthode:                                                                    ║
║  1. Scraper tous les matchs 2025/2026                                        ║
║  2. Pour chaque match, récupérer shotsData                                   ║
║  3. Calculer: SavedShots, xG_saved, xG_conceded, GK_Performance              ║
║  4. Stats par situation, timing, shotType                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import re
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from scipy import stats
from collections import defaultdict

# Paths
DATA_DIR = Path('/home/Mon_ps/data/goalkeeper_dna')
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / 'goalkeeper_dna_v3_real.json'
SHOTS_CACHE_FILE = DATA_DIR / 'all_shots_against_2025.json'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Saison 2025/2026
SEASON = 2025

LEAGUES = {
    'EPL': 'EPL',
    'La_Liga': 'La_Liga', 
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie_A',
    'Ligue_1': 'Ligue_1'
}

# Gardiens titulaires (repris de V2)
STARTING_GOALKEEPERS = {
    # EPL
    'Arsenal': {'name': 'David Raya', 'age': 29, 'height': 183},
    'Aston Villa': {'name': 'Emiliano Martínez', 'age': 32, 'height': 195},
    'Bournemouth': {'name': 'Kepa Arrizabalaga', 'age': 30, 'height': 186},
    'Brentford': {'name': 'Mark Flekken', 'age': 31, 'height': 194},
    'Brighton': {'name': 'Bart Verbruggen', 'age': 22, 'height': 193},
    'Burnley': {'name': 'James Trafford', 'age': 22, 'height': 196},
    'Chelsea': {'name': 'Robert Sánchez', 'age': 27, 'height': 197},
    'Crystal Palace': {'name': 'Dean Henderson', 'age': 28, 'height': 188},
    'Everton': {'name': 'Jordan Pickford', 'age': 31, 'height': 185},
    'Fulham': {'name': 'Bernd Leno', 'age': 32, 'height': 190},
    'Leeds': {'name': 'Illan Meslier', 'age': 25, 'height': 197},
    'Leicester': {'name': 'Mads Hermansen', 'age': 24, 'height': 191},
    'Liverpool': {'name': 'Alisson Becker', 'age': 32, 'height': 191},
    'Manchester City': {'name': 'Ederson', 'age': 31, 'height': 188},
    'Manchester United': {'name': 'André Onana', 'age': 28, 'height': 190},
    'Newcastle United': {'name': 'Nick Pope', 'age': 32, 'height': 198},
    'Nottingham Forest': {'name': 'Matz Sels', 'age': 32, 'height': 188},
    'Sunderland': {'name': 'Anthony Patterson', 'age': 24, 'height': 188},
    'Tottenham': {'name': 'Guglielmo Vicario', 'age': 28, 'height': 194},
    'West Ham': {'name': 'Lukasz Fabianski', 'age': 39, 'height': 190},
    'Wolverhampton Wanderers': {'name': 'José Sá', 'age': 31, 'height': 192},
    # La Liga
    'Alaves': {'name': 'Antonio Sivera', 'age': 28, 'height': 184},
    'Athletic Club': {'name': 'Unai Simón', 'age': 27, 'height': 190},
    'Atletico Madrid': {'name': 'Jan Oblak', 'age': 31, 'height': 188},
    'Barcelona': {'name': 'Iñaki Peña', 'age': 25, 'height': 184},
    'Celta Vigo': {'name': 'Vicente Guaita', 'age': 37, 'height': 190},
    'Espanyol': {'name': 'Joan García', 'age': 23, 'height': 190},
    'Getafe': {'name': 'David Soria', 'age': 31, 'height': 191},
    'Girona': {'name': 'Paulo Gazzaniga', 'age': 32, 'height': 193},
    'Las Palmas': {'name': 'Jasper Cillessen', 'age': 35, 'height': 185},
    'Leganes': {'name': 'Marko Dmitrović', 'age': 32, 'height': 194},
    'Levante': {'name': 'Andrés Fernández', 'age': 38, 'height': 184},
    'Mallorca': {'name': 'Dominik Greif', 'age': 27, 'height': 190},
    'Osasuna': {'name': 'Sergio Herrera', 'age': 31, 'height': 189},
    'Rayo Vallecano': {'name': 'Augusto Batalla', 'age': 28, 'height': 186},
    'Real Betis': {'name': 'Rui Silva', 'age': 30, 'height': 191},
    'Real Madrid': {'name': 'Thibaut Courtois', 'age': 32, 'height': 199},
    'Real Oviedo': {'name': 'Leo Román', 'age': 24, 'height': 186},
    'Real Sociedad': {'name': 'Álex Remiro', 'age': 29, 'height': 187},
    'Real Valladolid': {'name': 'Karl Hein', 'age': 22, 'height': 193},
    'Sevilla': {'name': 'Ørjan Nyland', 'age': 34, 'height': 193},
    'Valencia': {'name': 'Giorgi Mamardashvili', 'age': 24, 'height': 197},
    'Villarreal': {'name': 'Diego Conde', 'age': 25, 'height': 188},
    # Bundesliga
    'Augsburg': {'name': 'Nediljko Labrović', 'age': 25, 'height': 193},
    'Bayern Munich': {'name': 'Manuel Neuer', 'age': 38, 'height': 193},
    'Bochum': {'name': 'Patrick Drewes', 'age': 31, 'height': 191},
    'Borussia Dortmund': {'name': 'Gregor Kobel', 'age': 26, 'height': 194},
    'Borussia M.Gladbach': {'name': 'Moritz Nicolas', 'age': 27, 'height': 195},
    'Eintracht Frankfurt': {'name': 'Kevin Trapp', 'age': 34, 'height': 189},
    'FC Heidenheim': {'name': 'Kevin Müller', 'age': 33, 'height': 190},
    'Freiburg': {'name': 'Noah Atubolu', 'age': 22, 'height': 190},
    'Hoffenheim': {'name': 'Oliver Baumann', 'age': 34, 'height': 187},
    'Holstein Kiel': {'name': 'Timon Weiner', 'age': 25, 'height': 193},
    'Mainz 05': {'name': 'Robin Zentner', 'age': 29, 'height': 190},
    'RB Leipzig': {'name': 'Péter Gulácsi', 'age': 34, 'height': 190},
    'St. Pauli': {'name': 'Nikola Vasilj', 'age': 28, 'height': 192},
    'Union Berlin': {'name': 'Frederik Rønnow', 'age': 32, 'height': 190},
    'VfB Stuttgart': {'name': 'Alexander Nübel', 'age': 28, 'height': 193},
    'Werder Bremen': {'name': 'Michael Zetterer', 'age': 29, 'height': 189},
    'Wolfsburg': {'name': 'Kamil Grabara', 'age': 26, 'height': 194},
    'Bayer Leverkusen': {'name': 'Lukáš Hrádecký', 'age': 34, 'height': 192},
    'RasenBallsport Leipzig': {'name': 'Péter Gulácsi', 'age': 34, 'height': 190},
    # Serie A
    'AC Milan': {'name': 'Mike Maignan', 'age': 29, 'height': 191},
    'Atalanta': {'name': 'Marco Carnesecchi', 'age': 24, 'height': 191},
    'Bologna': {'name': 'Łukasz Skorupski', 'age': 33, 'height': 187},
    'Cagliari': {'name': 'Simone Scuffet', 'age': 28, 'height': 195},
    'Como': {'name': 'Pepe Reina', 'age': 42, 'height': 188},
    'Empoli': {'name': 'Devis Vasquez', 'age': 26, 'height': 190},
    'Fiorentina': {'name': 'David de Gea', 'age': 34, 'height': 192},
    'Genoa': {'name': 'Pierluigi Gollini', 'age': 29, 'height': 194},
    'Hellas Verona': {'name': 'Lorenzo Montipò', 'age': 28, 'height': 190},
    'Inter': {'name': 'Yann Sommer', 'age': 35, 'height': 183},
    'Juventus': {'name': 'Michele Di Gregorio', 'age': 27, 'height': 190},
    'Lazio': {'name': 'Ivan Provedel', 'age': 30, 'height': 193},
    'Lecce': {'name': 'Wladimiro Falcone', 'age': 29, 'height': 189},
    'Monza': {'name': 'Stefano Turati', 'age': 23, 'height': 194},
    'Napoli': {'name': 'Alex Meret', 'age': 27, 'height': 190},
    'Parma Calcio 1913': {'name': 'Zion Suzuki', 'age': 22, 'height': 190},
    'Roma': {'name': 'Mile Svilar', 'age': 25, 'height': 187},
    'Torino': {'name': 'Vanja Milinković-Savić', 'age': 27, 'height': 202},
    'Udinese': {'name': 'Maduka Okoye', 'age': 25, 'height': 193},
    'Venezia': {'name': 'Jesse Joronen', 'age': 31, 'height': 197},
    # Ligue 1
    'Angers': {'name': 'Yahia Fofana', 'age': 26, 'height': 188},
    'Auxerre': {'name': 'Donovan Léon', 'age': 32, 'height': 185},
    'Brest': {'name': 'Marco Bizot', 'age': 33, 'height': 191},
    'Le Havre': {'name': 'Arthur Desmas', 'age': 26, 'height': 186},
    'Lens': {'name': 'Brice Samba', 'age': 30, 'height': 187},
    'Lille': {'name': 'Lucas Chevalier', 'age': 23, 'height': 186},
    'Lorient': {'name': 'Yvon Mvogo', 'age': 30, 'height': 189},
    'Lyon': {'name': 'Lucas Perri', 'age': 26, 'height': 195},
    'Marseille': {'name': 'Geronimo Rulli', 'age': 32, 'height': 189},
    'Metz': {'name': 'Alexandre Oukidja', 'age': 36, 'height': 184},
    'Monaco': {'name': 'Radosław Majecki', 'age': 25, 'height': 193},
    'Montpellier': {'name': 'Benjamin Lecomte', 'age': 33, 'height': 186},
    'Nantes': {'name': 'Alban Lafont', 'age': 25, 'height': 195},
    'Nice': {'name': 'Marcin Bułka', 'age': 25, 'height': 199},
    'Paris FC': {'name': 'Christophe Kerbrat', 'age': 31, 'height': 186},
    'Paris Saint Germain': {'name': 'Gianluigi Donnarumma', 'age': 25, 'height': 196},
    'Reims': {'name': 'Yehvann Diouf', 'age': 25, 'height': 191},
    'Rennes': {'name': 'Steve Mandanda', 'age': 39, 'height': 185},
    'Saint-Etienne': {'name': 'Gautier Larsonneur', 'age': 27, 'height': 182},
    'Strasbourg': {'name': 'Djordje Petrović', 'age': 24, 'height': 193},
    'Toulouse': {'name': 'Guillaume Restes', 'age': 20, 'height': 190},
}

def extract_json_var(html: str, var_name: str) -> Any:
    """Extrait une variable JSON du HTML"""
    pattern = rf"var\s+{var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        json_str = match.group(1).encode().decode('unicode_escape')
        return json.loads(json_str)
    return None

def get_team_matches(league: str) -> List[Dict]:
    """Récupère tous les matchs d'une ligue pour la saison 2025"""
    url = f"https://understat.com/league/{league}/{SEASON}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        dates_data = extract_json_var(response.text, 'datesData')
        if dates_data:
            # Filtrer uniquement les matchs joués
            played = [m for m in dates_data if m.get('isResult') == True]
            return played
        return []
    except Exception as e:
        print(f"      ❌ Erreur {league}: {e}")
        return []

def get_match_shots(match_id: str) -> Dict:
    """Récupère les tirs d'un match"""
    url = f"https://understat.com/match/{match_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        shots_data = extract_json_var(response.text, 'shotsData')
        return shots_data if shots_data else {}
    except Exception as e:
        return {}

def calculate_gk_stats(shots_against: List[Dict]) -> Dict:
    """
    Calcule les stats du gardien à partir des tirs contre son équipe
    """
    if not shots_against:
        return {}
    
    stats = {
        # Totaux
        'total_shots_against': len(shots_against),
        'shots_on_target': 0,
        'saves': 0,
        'goals_conceded': 0,
        'xG_against': 0.0,
        'xG_saved': 0.0,
        'xG_conceded': 0.0,
        
        # Par situation
        'by_situation': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0}),
        
        # Par timing (tranches de 15 min)
        'by_timing': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0}),
        
        # Par type de tir
        'by_shot_type': defaultdict(lambda: {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0}),
        
        # Par zone (xG level - difficulté)
        'by_difficulty': {
            'easy': {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0},      # xG < 0.1
            'medium': {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0},    # 0.1 <= xG < 0.3
            'hard': {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0},      # 0.3 <= xG < 0.5
            'very_hard': {'shots': 0, 'saves': 0, 'goals': 0, 'xG': 0.0}  # xG >= 0.5
        },
        
        # High value saves (arrêts sur grosses occasions)
        'high_xg_saves': 0,  # Arrêts sur tirs >0.3 xG
        'low_xg_conceded': 0,  # Buts sur tirs <0.1 xG (erreurs)
    }
    
    for shot in shots_against:
        xG = float(shot.get('xG', 0))
        result = shot.get('result', '')
        minute = int(shot.get('minute', 45))
        situation = shot.get('situation', 'OpenPlay')
        shot_type = shot.get('shotType', 'RightFoot')
        
        # Ignorer les tirs bloqués (pas le gardien)
        if result == 'BlockedShot':
            continue
        
        # Tirs cadrés = SavedShot + Goal
        if result in ['SavedShot', 'Goal']:
            stats['shots_on_target'] += 1
            stats['xG_against'] += xG
            
            if result == 'SavedShot':
                stats['saves'] += 1
                stats['xG_saved'] += xG
                if xG >= 0.3:
                    stats['high_xg_saves'] += 1
            else:  # Goal
                stats['goals_conceded'] += 1
                stats['xG_conceded'] += xG
                if xG < 0.1:
                    stats['low_xg_conceded'] += 1
            
            # Par situation
            stats['by_situation'][situation]['shots'] += 1
            stats['by_situation'][situation]['xG'] += xG
            if result == 'SavedShot':
                stats['by_situation'][situation]['saves'] += 1
            else:
                stats['by_situation'][situation]['goals'] += 1
            
            # Par timing
            if minute <= 15:
                timing_key = '0-15'
            elif minute <= 30:
                timing_key = '16-30'
            elif minute <= 45:
                timing_key = '31-45'
            elif minute <= 60:
                timing_key = '46-60'
            elif minute <= 75:
                timing_key = '61-75'
            else:
                timing_key = '76-90'
            
            stats['by_timing'][timing_key]['shots'] += 1
            stats['by_timing'][timing_key]['xG'] += xG
            if result == 'SavedShot':
                stats['by_timing'][timing_key]['saves'] += 1
            else:
                stats['by_timing'][timing_key]['goals'] += 1
            
            # Par type de tir
            stats['by_shot_type'][shot_type]['shots'] += 1
            stats['by_shot_type'][shot_type]['xG'] += xG
            if result == 'SavedShot':
                stats['by_shot_type'][shot_type]['saves'] += 1
            else:
                stats['by_shot_type'][shot_type]['goals'] += 1
            
            # Par difficulté
            if xG < 0.1:
                diff_key = 'easy'
            elif xG < 0.3:
                diff_key = 'medium'
            elif xG < 0.5:
                diff_key = 'hard'
            else:
                diff_key = 'very_hard'
            
            stats['by_difficulty'][diff_key]['shots'] += 1
            stats['by_difficulty'][diff_key]['xG'] += xG
            if result == 'SavedShot':
                stats['by_difficulty'][diff_key]['saves'] += 1
            else:
                stats['by_difficulty'][diff_key]['goals'] += 1
    
    # Calculer les métriques dérivées
    if stats['shots_on_target'] > 0:
        stats['save_rate'] = round(stats['saves'] / stats['shots_on_target'] * 100, 1)
    else:
        stats['save_rate'] = 0.0
    
    # GK Performance = xG_against - Goals (positif = bon gardien)
    stats['gk_performance'] = round(stats['xG_against'] - stats['goals_conceded'], 2)
    stats['gk_performance_per_shot'] = round(
        stats['gk_performance'] / max(1, stats['shots_on_target']), 3
    )
    
    # Convertir defaultdicts en dicts normaux
    stats['by_situation'] = dict(stats['by_situation'])
    stats['by_timing'] = dict(stats['by_timing'])
    stats['by_shot_type'] = dict(stats['by_shot_type'])
    
    return stats

def main():
    print("=" * 80)
    print("�� GOALKEEPER DNA V3.0 - VRAIES STATS D'ARRÊTS")
    print(f"   Saison {SEASON}/{SEASON+1} | Hedge Fund Grade")
    print("=" * 80)
    
    # 1. Collecter tous les matchs
    print("\n📅 ÉTAPE 1: Collecte des matchs...")
    all_matches = {}
    
    for league_name, league_code in LEAGUES.items():
        print(f"\n   🏆 {league_name}...")
        matches = get_team_matches(league_code)
        all_matches[league_name] = matches
        print(f"      ✅ {len(matches)} matchs trouvés")
        time.sleep(2)
    
    total_matches = sum(len(m) for m in all_matches.values())
    print(f"\n   📊 Total: {total_matches} matchs à analyser")
    
    # 2. Collecter les tirs de chaque match
    print("\n⚽ ÉTAPE 2: Collecte des tirs (cela peut prendre plusieurs minutes)...")
    
    # Structure: {team_name: [shots_against]}
    team_shots_against = defaultdict(list)
    processed = 0
    
    for league_name, matches in all_matches.items():
        print(f"\n   🏆 {league_name}...")
        
        for match in matches:
            match_id = match.get('id')
            h_team = match.get('h', {}).get('title', '')
            a_team = match.get('a', {}).get('title', '')
            
            if not match_id:
                continue
            
            shots = get_match_shots(match_id)
            
            if shots:
                # Tirs de l'équipe 'h' = contre le gardien de 'a'
                if 'h' in shots:
                    for shot in shots['h']:
                        shot['against_team'] = a_team
                        shot['match_id'] = match_id
                    team_shots_against[a_team].extend(shots['h'])
                
                # Tirs de l'équipe 'a' = contre le gardien de 'h'
                if 'a' in shots:
                    for shot in shots['a']:
                        shot['against_team'] = h_team
                        shot['match_id'] = match_id
                    team_shots_against[h_team].extend(shots['a'])
            
            processed += 1
            if processed % 20 == 0:
                print(f"      ⏳ {processed}/{total_matches} matchs traités...")
            
            time.sleep(0.5)  # Rate limiting
    
    print(f"\n   ✅ {len(team_shots_against)} équipes avec données de tirs")
    
    # Sauvegarder le cache des tirs
    print("\n💾 Sauvegarde du cache des tirs...")
    with open(SHOTS_CACHE_FILE, 'w') as f:
        # Convertir en format sérialisable
        cache_data = {team: shots for team, shots in team_shots_against.items()}
        json.dump(cache_data, f, indent=2)
    print(f"   ✅ Cache sauvegardé: {SHOTS_CACHE_FILE}")
    
    # 3. Calculer les stats de chaque gardien
    print("\n🧤 ÉTAPE 3: Calcul des stats gardiens...")
    goalkeepers = []
    
    for team_name, shots in team_shots_against.items():
        # Trouver le gardien
        gk_info = STARTING_GOALKEEPERS.get(team_name, {
            'name': f"GK {team_name}",
            'age': 28,
            'height': 188
        })
        
        # Calculer les stats
        gk_stats = calculate_gk_stats(shots)
        
        if not gk_stats:
            continue
        
        gk_profile = {
            'player_name': gk_info['name'],
            'team': team_name,
            'age': gk_info.get('age', 28),
            'height': gk_info.get('height', 188),
            
            # Stats brutes
            'matches_analyzed': len(set(s.get('match_id') for s in shots)),
            'total_shots_against': gk_stats['total_shots_against'],
            'shots_on_target': gk_stats['shots_on_target'],
            'saves': gk_stats['saves'],
            'goals_conceded': gk_stats['goals_conceded'],
            
            # xG metrics
            'xG_against': round(gk_stats['xG_against'], 2),
            'xG_saved': round(gk_stats['xG_saved'], 2),
            'xG_conceded': round(gk_stats['xG_conceded'], 2),
            
            # PERFORMANCE METRICS (La clé!)
            'save_rate': gk_stats['save_rate'],
            'gk_performance': gk_stats['gk_performance'],
            'gk_performance_per_shot': gk_stats['gk_performance_per_shot'],
            
            # Quality metrics
            'high_xg_saves': gk_stats['high_xg_saves'],
            'low_xg_conceded': gk_stats['low_xg_conceded'],
            
            # Breakdowns
            'by_situation': gk_stats['by_situation'],
            'by_timing': gk_stats['by_timing'],
            'by_shot_type': gk_stats['by_shot_type'],
            'by_difficulty': gk_stats['by_difficulty'],
        }
        
        goalkeepers.append(gk_profile)
    
    print(f"   ✅ {len(goalkeepers)} gardiens analysés")
    
    # 4. Calculer les percentiles
    print("\n📊 ÉTAPE 4: Calcul des percentiles et dimensions...")
    
    # Métriques pour percentiles
    all_save_rates = [gk['save_rate'] for gk in goalkeepers]
    all_performances = [gk['gk_performance'] for gk in goalkeepers]
    all_high_xg_saves = [gk['high_xg_saves'] for gk in goalkeepers]
    
    for gk in goalkeepers:
        gk['percentiles'] = {
            'save_rate': round(stats.percentileofscore(all_save_rates, gk['save_rate'], kind='rank'), 0),
            'gk_performance': round(stats.percentileofscore(all_performances, gk['gk_performance'], kind='rank'), 0),
            'high_xg_saves': round(stats.percentileofscore(all_high_xg_saves, gk['high_xg_saves'], kind='rank'), 0),
        }
        
        # Save rates par situation
        for situation in ['OpenPlay', 'FromCorner', 'SetPiece', 'Penalty']:
            sit_data = gk['by_situation'].get(situation, {})
            if sit_data.get('shots', 0) > 0:
                sit_save_rate = sit_data['saves'] / sit_data['shots'] * 100
                gk['percentiles'][f'save_rate_{situation.lower()}'] = round(sit_save_rate, 1)
        
        # Save rates par timing
        for timing in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90']:
            tim_data = gk['by_timing'].get(timing, {})
            if tim_data.get('shots', 0) > 0:
                tim_save_rate = tim_data['saves'] / tim_data['shots'] * 100
                gk['percentiles'][f'save_rate_{timing.replace("-", "_")}'] = round(tim_save_rate, 1)
        
        # Save rates par type
        for shot_type in ['Head', 'RightFoot', 'LeftFoot']:
            type_data = gk['by_shot_type'].get(shot_type, {})
            if type_data.get('shots', 0) > 0:
                type_save_rate = type_data['saves'] / type_data['shots'] * 100
                gk['percentiles'][f'save_rate_{shot_type.lower()}'] = round(type_save_rate, 1)
        
        # Profil
        perf_pct = gk['percentiles']['gk_performance']
        if perf_pct >= 85:
            gk['profile'] = 'ELITE_SHOT_STOPPER'
        elif perf_pct >= 70:
            gk['profile'] = 'ABOVE_AVERAGE'
        elif perf_pct >= 50:
            gk['profile'] = 'AVERAGE'
        elif perf_pct >= 30:
            gk['profile'] = 'BELOW_AVERAGE'
        else:
            gk['profile'] = 'LIABILITY'
        
        # Tags
        tags = [gk['profile']]
        if gk['percentiles'].get('save_rate_head', 50) <= 30:
            tags.append('HEADER_WEAK')
        if gk['percentiles'].get('save_rate_76_90', 50) <= 30:
            tags.append('LATE_COLLAPSER')
        if gk['percentiles'].get('save_rate_0_15', 50) <= 30:
            tags.append('SLOW_STARTER')
        if gk['percentiles'].get('save_rate_fromcorner', 50) <= 30:
            tags.append('CORNER_WEAK')
        if gk['high_xg_saves'] >= np.percentile(all_high_xg_saves, 75):
            tags.append('BIG_SAVE_SPECIALIST')
        if gk['low_xg_conceded'] >= 3:
            tags.append('ERROR_PRONE')
        
        gk['tags'] = tags
        
        # Fingerprint
        gk['fingerprint'] = f"GK-{int(gk['percentiles']['save_rate'])}-{int(gk['percentiles']['gk_performance'])}-{gk['saves']}-{gk['goals_conceded']}"
    
    # 5. Sauvegarder
    print("\n💾 Sauvegarde finale...")
    
    # Trier par performance
    goalkeepers.sort(key=lambda x: x['gk_performance'], reverse=True)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(goalkeepers, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # 6. Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT GOALKEEPER DNA V3.0 - VRAIES STATS")
    print("=" * 80)
    
    print("\n🏆 TOP 10 GARDIENS (par xG Performance):")
    for i, gk in enumerate(goalkeepers[:10], 1):
        print(f"   {i:2}. {gk['player_name']:<22} ({gk['team']:<18}) | Perf: {gk['gk_performance']:+.2f} | Save%: {gk['save_rate']:.1f}%")
    
    print("\n🎯 BOTTOM 10 GARDIENS (Cibles):")
    for i, gk in enumerate(goalkeepers[-10:][::-1], 1):
        print(f"   {i:2}. {gk['player_name']:<22} ({gk['team']:<18}) | Perf: {gk['gk_performance']:+.2f} | Save%: {gk['save_rate']:.1f}%")
    
    # Exemple complet
    if goalkeepers:
        best = goalkeepers[0]
        print(f"\n📋 EXEMPLE: {best['player_name']} ({best['team']})")
        print(f"   Matchs: {best['matches_analyzed']} | Tirs cadrés: {best['shots_on_target']}")
        print(f"   Arrêts: {best['saves']} | Buts: {best['goals_conceded']}")
        print(f"   xG Against: {best['xG_against']:.2f} | xG Saved: {best['xG_saved']:.2f}")
        print(f"   🎯 GK PERFORMANCE: {best['gk_performance']:+.2f} (xG - Goals)")
        print(f"   → Arrête {abs(best['gk_performance']):.2f} xG de plus/moins que prévu")
        print(f"   High xG Saves (>0.3): {best['high_xg_saves']}")
        print(f"   Low xG Conceded (<0.1): {best['low_xg_conceded']}")
    
    print(f"\n{'=' * 80}")
    print(f"✅ GOALKEEPER DNA V3.0 COMPLET - {len(goalkeepers)} GARDIENS")
    print(f"   📁 Fichier: {OUTPUT_FILE}")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()

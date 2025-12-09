#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧤 GOALKEEPER DNA V2.0 - APPROCHE HYBRIDE                                   ║
║                                                                              ║
║  Sources:                                                                    ║
║  - Defense DNA existant (xGA par équipe, timing, situations)                 ║
║  - Understat match data (buts encaissés par situation)                       ║
║  - Données manuelles gardiens titulaires                                     ║
║                                                                              ║
║  Méthode: Attribuer les stats défensives au gardien titulaire               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from scipy import stats

# Paths
DATA_DIR = Path('/home/Mon_ps/data')
DEFENSE_DNA_FILE = DATA_DIR / 'defense_dna/team_defense_dna_v5_1_corrected.json'
OUTPUT_DIR = DATA_DIR / 'goalkeeper_dna'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / 'goalkeeper_dna_v2.json'

# Gardiens titulaires par équipe (2025/2026 season)
# Source: Transfermarkt + vérification manuelle
STARTING_GOALKEEPERS = {
    # EPL
    'Arsenal': {'name': 'David Raya', 'age': 29, 'height': 183, 'nationality': 'Spain'},
    'Aston Villa': {'name': 'Emiliano Martínez', 'age': 32, 'height': 195, 'nationality': 'Argentina'},
    'Bournemouth': {'name': 'Kepa Arrizabalaga', 'age': 30, 'height': 186, 'nationality': 'Spain'},
    'Brentford': {'name': 'Mark Flekken', 'age': 31, 'height': 194, 'nationality': 'Netherlands'},
    'Brighton': {'name': 'Bart Verbruggen', 'age': 22, 'height': 193, 'nationality': 'Netherlands'},
    'Burnley': {'name': 'James Trafford', 'age': 22, 'height': 196, 'nationality': 'England'},
    'Chelsea': {'name': 'Robert Sánchez', 'age': 27, 'height': 197, 'nationality': 'Spain'},
    'Crystal Palace': {'name': 'Dean Henderson', 'age': 28, 'height': 188, 'nationality': 'England'},
    'Everton': {'name': 'Jordan Pickford', 'age': 31, 'height': 185, 'nationality': 'England'},
    'Fulham': {'name': 'Bernd Leno', 'age': 32, 'height': 190, 'nationality': 'Germany'},
    'Leeds': {'name': 'Illan Meslier', 'age': 25, 'height': 197, 'nationality': 'France'},
    'Leicester': {'name': 'Mads Hermansen', 'age': 24, 'height': 191, 'nationality': 'Denmark'},
    'Liverpool': {'name': 'Alisson Becker', 'age': 32, 'height': 191, 'nationality': 'Brazil'},
    'Manchester City': {'name': 'Ederson', 'age': 31, 'height': 188, 'nationality': 'Brazil'},
    'Manchester United': {'name': 'André Onana', 'age': 28, 'height': 190, 'nationality': 'Cameroon'},
    'Newcastle United': {'name': 'Nick Pope', 'age': 32, 'height': 198, 'nationality': 'England'},
    'Nottingham Forest': {'name': 'Matz Sels', 'age': 32, 'height': 188, 'nationality': 'Belgium'},
    'Sunderland': {'name': 'Anthony Patterson', 'age': 24, 'height': 188, 'nationality': 'England'},
    'Tottenham': {'name': 'Guglielmo Vicario', 'age': 28, 'height': 194, 'nationality': 'Italy'},
    'West Ham': {'name': 'Lukasz Fabianski', 'age': 39, 'height': 190, 'nationality': 'Poland'},
    'Wolverhampton Wanderers': {'name': 'José Sá', 'age': 31, 'height': 192, 'nationality': 'Portugal'},
    
    # La Liga
    'Alaves': {'name': 'Antonio Sivera', 'age': 28, 'height': 184, 'nationality': 'Spain'},
    'Athletic Club': {'name': 'Unai Simón', 'age': 27, 'height': 190, 'nationality': 'Spain'},
    'Atletico Madrid': {'name': 'Jan Oblak', 'age': 31, 'height': 188, 'nationality': 'Slovenia'},
    'Barcelona': {'name': 'Iñaki Peña', 'age': 25, 'height': 184, 'nationality': 'Spain'},
    'Celta Vigo': {'name': 'Vicente Guaita', 'age': 37, 'height': 190, 'nationality': 'Spain'},
    'Elche': {'name': 'Edgar Badía', 'age': 32, 'height': 184, 'nationality': 'Spain'},
    'Espanyol': {'name': 'Joan García', 'age': 23, 'height': 190, 'nationality': 'Spain'},
    'Getafe': {'name': 'David Soria', 'age': 31, 'height': 191, 'nationality': 'Spain'},
    'Girona': {'name': 'Paulo Gazzaniga', 'age': 32, 'height': 193, 'nationality': 'Argentina'},
    'Las Palmas': {'name': 'Jasper Cillessen', 'age': 35, 'height': 185, 'nationality': 'Netherlands'},
    'Leganes': {'name': 'Marko Dmitrović', 'age': 32, 'height': 194, 'nationality': 'Serbia'},
    'Levante': {'name': 'Andrés Fernández', 'age': 38, 'height': 184, 'nationality': 'Spain'},
    'Mallorca': {'name': 'Dominik Greif', 'age': 27, 'height': 190, 'nationality': 'Slovakia'},
    'Osasuna': {'name': 'Sergio Herrera', 'age': 31, 'height': 189, 'nationality': 'Spain'},
    'Rayo Vallecano': {'name': 'Augusto Batalla', 'age': 28, 'height': 186, 'nationality': 'Argentina'},
    'Real Betis': {'name': 'Rui Silva', 'age': 30, 'height': 191, 'nationality': 'Portugal'},
    'Real Madrid': {'name': 'Thibaut Courtois', 'age': 32, 'height': 199, 'nationality': 'Belgium'},
    'Real Oviedo': {'name': 'Leo Román', 'age': 24, 'height': 186, 'nationality': 'Spain'},
    'Real Sociedad': {'name': 'Álex Remiro', 'age': 29, 'height': 187, 'nationality': 'Spain'},
    'Real Valladolid': {'name': 'Karl Hein', 'age': 22, 'height': 193, 'nationality': 'Estonia'},
    'Sevilla': {'name': 'Ørjan Nyland', 'age': 34, 'height': 193, 'nationality': 'Norway'},
    'Valencia': {'name': 'Giorgi Mamardashvili', 'age': 24, 'height': 197, 'nationality': 'Georgia'},
    'Villarreal': {'name': 'Diego Conde', 'age': 25, 'height': 188, 'nationality': 'Spain'},
    
    # Bundesliga
    'Augsburg': {'name': 'Nediljko Labrović', 'age': 25, 'height': 193, 'nationality': 'Croatia'},
    'Bayern Munich': {'name': 'Manuel Neuer', 'age': 38, 'height': 193, 'nationality': 'Germany'},
    'Bochum': {'name': 'Patrick Drewes', 'age': 31, 'height': 191, 'nationality': 'Germany'},
    'Borussia Dortmund': {'name': 'Gregor Kobel', 'age': 26, 'height': 194, 'nationality': 'Switzerland'},
    'Borussia M.Gladbach': {'name': 'Moritz Nicolas', 'age': 27, 'height': 195, 'nationality': 'Germany'},
    'Eintracht Frankfurt': {'name': 'Kevin Trapp', 'age': 34, 'height': 189, 'nationality': 'Germany'},
    'FC Heidenheim': {'name': 'Kevin Müller', 'age': 33, 'height': 190, 'nationality': 'Germany'},
    'FC Cologne': {'name': 'Marvin Schwäbe', 'age': 29, 'height': 187, 'nationality': 'Germany'},
    'Freiburg': {'name': 'Noah Atubolu', 'age': 22, 'height': 190, 'nationality': 'Germany'},
    'Hamburger SV': {'name': 'Daniel Heuer Fernandes', 'age': 31, 'height': 188, 'nationality': 'Germany'},
    'Hoffenheim': {'name': 'Oliver Baumann', 'age': 34, 'height': 187, 'nationality': 'Germany'},
    'Holstein Kiel': {'name': 'Timon Weiner', 'age': 25, 'height': 193, 'nationality': 'Germany'},
    'Mainz 05': {'name': 'Robin Zentner', 'age': 29, 'height': 190, 'nationality': 'Germany'},
    'RB Leipzig': {'name': 'Péter Gulácsi', 'age': 34, 'height': 190, 'nationality': 'Hungary'},
    'St. Pauli': {'name': 'Nikola Vasilj', 'age': 28, 'height': 192, 'nationality': 'Bosnia'},
    'Union Berlin': {'name': 'Frederik Rønnow', 'age': 32, 'height': 190, 'nationality': 'Denmark'},
    'VfB Stuttgart': {'name': 'Alexander Nübel', 'age': 28, 'height': 193, 'nationality': 'Germany'},
    'Werder Bremen': {'name': 'Michael Zetterer', 'age': 29, 'height': 189, 'nationality': 'Germany'},
    'Wolfsburg': {'name': 'Kamil Grabara', 'age': 26, 'height': 194, 'nationality': 'Poland'},
    
    # Serie A
    'AC Milan': {'name': 'Mike Maignan', 'age': 29, 'height': 191, 'nationality': 'France'},
    'Atalanta': {'name': 'Marco Carnesecchi', 'age': 24, 'height': 191, 'nationality': 'Italy'},
    'Bologna': {'name': 'Łukasz Skorupski', 'age': 33, 'height': 187, 'nationality': 'Poland'},
    'Cagliari': {'name': 'Simone Scuffet', 'age': 28, 'height': 195, 'nationality': 'Italy'},
    'Como': {'name': 'Pepe Reina', 'age': 42, 'height': 188, 'nationality': 'Spain'},
    'Cremonese': {'name': 'Marco Carnesecchi', 'age': 24, 'height': 191, 'nationality': 'Italy'},
    'Empoli': {'name': 'Devis Vasquez', 'age': 26, 'height': 190, 'nationality': 'Colombia'},
    'Fiorentina': {'name': 'David de Gea', 'age': 34, 'height': 192, 'nationality': 'Spain'},
    'Genoa': {'name': 'Pierluigi Gollini', 'age': 29, 'height': 194, 'nationality': 'Italy'},
    'Hellas Verona': {'name': 'Lorenzo Montipò', 'age': 28, 'height': 190, 'nationality': 'Italy'},
    'Inter': {'name': 'Yann Sommer', 'age': 35, 'height': 183, 'nationality': 'Switzerland'},
    'Juventus': {'name': 'Michele Di Gregorio', 'age': 27, 'height': 190, 'nationality': 'Italy'},
    'Lazio': {'name': 'Ivan Provedel', 'age': 30, 'height': 193, 'nationality': 'Italy'},
    'Lecce': {'name': 'Wladimiro Falcone', 'age': 29, 'height': 189, 'nationality': 'Italy'},
    'Monza': {'name': 'Stefano Turati', 'age': 23, 'height': 194, 'nationality': 'Italy'},
    'Napoli': {'name': 'Alex Meret', 'age': 27, 'height': 190, 'nationality': 'Italy'},
    'Parma': {'name': 'Zion Suzuki', 'age': 22, 'height': 190, 'nationality': 'Japan'},
    'Pisa': {'name': 'Leonardo Loria', 'age': 24, 'height': 188, 'nationality': 'Italy'},
    'Roma': {'name': 'Mile Svilar', 'age': 25, 'height': 187, 'nationality': 'Belgium'},
    'Sassuolo': {'name': 'Gianluca Pegolo', 'age': 43, 'height': 186, 'nationality': 'Italy'},
    'Torino': {'name': 'Vanja Milinković-Savić', 'age': 27, 'height': 202, 'nationality': 'Serbia'},
    'Udinese': {'name': 'Maduka Okoye', 'age': 25, 'height': 193, 'nationality': 'Nigeria'},
    'Venezia': {'name': 'Jesse Joronen', 'age': 31, 'height': 197, 'nationality': 'Finland'},
    
    # Ligue 1
    'Angers': {'name': 'Yahia Fofana', 'age': 26, 'height': 188, 'nationality': 'Ivory Coast'},
    'Auxerre': {'name': 'Donovan Léon', 'age': 32, 'height': 185, 'nationality': 'Martinique'},
    'Brest': {'name': 'Marco Bizot', 'age': 33, 'height': 191, 'nationality': 'Netherlands'},
    'Le Havre': {'name': 'Arthur Desmas', 'age': 26, 'height': 186, 'nationality': 'France'},
    'Lens': {'name': 'Brice Samba', 'age': 30, 'height': 187, 'nationality': 'France'},
    'Lille': {'name': 'Lucas Chevalier', 'age': 23, 'height': 186, 'nationality': 'France'},
    'Lorient': {'name': 'Yvon Mvogo', 'age': 30, 'height': 189, 'nationality': 'Switzerland'},
    'Lyon': {'name': 'Lucas Perri', 'age': 26, 'height': 195, 'nationality': 'Brazil'},
    'Marseille': {'name': 'Geronimo Rulli', 'age': 32, 'height': 189, 'nationality': 'Argentina'},
    'Metz': {'name': 'Alexandre Oukidja', 'age': 36, 'height': 184, 'nationality': 'Algeria'},
    'Monaco': {'name': 'Radosław Majecki', 'age': 25, 'height': 193, 'nationality': 'Poland'},
    'Montpellier': {'name': 'Benjamin Lecomte', 'age': 33, 'height': 186, 'nationality': 'France'},
    'Nantes': {'name': 'Alban Lafont', 'age': 25, 'height': 195, 'nationality': 'France'},
    'Nice': {'name': 'Marcin Bułka', 'age': 25, 'height': 199, 'nationality': 'Poland'},
    'Paris FC': {'name': 'Christophe Kerbrat', 'age': 31, 'height': 186, 'nationality': 'France'},
    'Paris Saint Germain': {'name': 'Gianluigi Donnarumma', 'age': 25, 'height': 196, 'nationality': 'Italy'},
    'Reims': {'name': 'Yehvann Diouf', 'age': 25, 'height': 191, 'nationality': 'France'},
    'Rennes': {'name': 'Steve Mandanda', 'age': 39, 'height': 185, 'nationality': 'France'},
    'Saint Etienne': {'name': 'Gautier Larsonneur', 'age': 27, 'height': 182, 'nationality': 'France'},
    'Strasbourg': {'name': 'Djordje Petrović', 'age': 24, 'height': 193, 'nationality': 'Serbia'},
    'Toulouse': {'name': 'Guillaume Restes', 'age': 20, 'height': 190, 'nationality': 'France'},
}

def load_defense_dna() -> List[Dict]:
    """Charge les données Defense DNA"""
    with open(DEFENSE_DNA_FILE, 'r') as f:
        return json.load(f)

def find_team_match(team_name: str, gk_teams: Dict) -> str:
    """Trouve la correspondance entre nom d'équipe Defense DNA et gardiens"""
    # Correspondance directe
    if team_name in gk_teams:
        return team_name
    
    # Nettoyage et correspondances alternatives
    clean_name = team_name.replace('_', ' ').strip()
    
    # Mappings spéciaux
    mappings = {
        'Borussia Monchengladbach': 'Borussia M.Gladbach',
        'Bayer Leverkusen': 'Bayer Leverkusen',
        'RB Leipzig': 'RB Leipzig',
        'St Pauli': 'St. Pauli',
    }
    
    if team_name in mappings:
        mapped = mappings[team_name]
        if mapped in gk_teams:
            return mapped
    
    # Recherche partielle
    for gk_team in gk_teams.keys():
        if team_name.lower() in gk_team.lower() or gk_team.lower() in team_name.lower():
            return gk_team
    
    return None

def calculate_gk_dimensions(team_data: Dict, gk_info: Dict) -> Dict:
    """
    Calcule les dimensions du gardien basées sur les données défensives de l'équipe
    """
    pct = team_data.get('percentiles_v5_1', team_data.get('percentiles', {}))
    timing_raw = team_data.get('timing_raw', {})
    
    # Données brutes
    xga_per_90 = team_data.get('xga_per_90', 1.5)
    matches = team_data.get('matches_played', 15)
    
    dimensions = {}
    
    # DIMENSION 1: SHOT_STOPPING (basé sur xGA global de l'équipe)
    # Un bon gardien contribue à réduire xGA
    dimensions['shot_stopping'] = pct.get('global', 50)
    
    # DIMENSION 2: AERIAL (basé sur xGA aérien de l'équipe)
    dimensions['aerial'] = pct.get('aerial', 50)
    
    # DIMENSION 3: SET_PIECE (corners, FK)
    dimensions['set_piece'] = pct.get('set_piece', 50)
    
    # DIMENSION 4: TIMING_EARLY (vulnérabilité en début de match)
    # On utilise la proportion - gardien responsable de la concentration initiale
    dimensions['timing_early'] = pct.get('early_proportion', pct.get('early_prop', 50))
    
    # DIMENSION 5: TIMING_LATE (vulnérabilité en fin de match)
    # Fatigue, concentration - responsabilité du gardien
    dimensions['timing_late'] = pct.get('late_proportion', pct.get('late_prop', 50))
    
    # DIMENSION 6: DISCIPLINE (penalties concédés = chaos de l'équipe mais aussi réflexe GK)
    dimensions['discipline'] = pct.get('chaos', 50)
    
    # DIMENSION 7: HOME (performance à domicile)
    dimensions['home'] = pct.get('home', 50)
    
    # DIMENSION 8: AWAY (performance en déplacement - plus difficile pour GK)
    dimensions['away'] = pct.get('away', 50)
    
    # DIMENSION 9: LONGSHOT (arrêts de loin)
    dimensions['longshot'] = pct.get('longshot', 50)
    
    # DIMENSION 10: OPEN_PLAY (buts en jeu ouvert)
    dimensions['open_play'] = pct.get('open_play', 50)
    
    # DIMENSIONS PHYSIQUES (basées sur les données du gardien)
    height = gk_info.get('height', 188)
    age = gk_info.get('age', 28)
    
    # DIMENSION 11: HEIGHT_FACTOR (taille = couverture du but)
    # Moyenne des gardiens ~190cm, avantage si >193, désavantage si <185
    if height >= 195:
        dimensions['height_factor'] = 85
    elif height >= 190:
        dimensions['height_factor'] = 70
    elif height >= 185:
        dimensions['height_factor'] = 55
    else:
        dimensions['height_factor'] = 40
    
    # DIMENSION 12: EXPERIENCE_FACTOR (âge = expérience mais aussi réflexes)
    # Peak: 27-32 ans, déclin après 35
    if 27 <= age <= 32:
        dimensions['experience'] = 80
    elif 25 <= age < 27 or 32 < age <= 34:
        dimensions['experience'] = 70
    elif 23 <= age < 25 or 34 < age <= 36:
        dimensions['experience'] = 60
    elif age < 23:
        dimensions['experience'] = 45  # Manque d'expérience
    else:
        dimensions['experience'] = 50  # >36 ans, potentiel déclin
    
    return dimensions

def generate_fingerprint(dimensions: Dict) -> str:
    """Génère le fingerprint unique"""
    parts = ['GK']
    dim_order = ['shot_stopping', 'aerial', 'set_piece', 'timing_early', 'timing_late',
                 'discipline', 'home', 'away', 'longshot', 'open_play', 
                 'height_factor', 'experience']
    
    for dim in dim_order:
        parts.append(str(int(dimensions.get(dim, 50))))
    
    return '-'.join(parts)

def generate_compact_fingerprint(dimensions: Dict) -> str:
    """Génère le fingerprint compact"""
    codes = {
        'shot_stopping': 'SHT',
        'aerial': 'AER',
        'set_piece': 'STP',
        'timing_early': 'ERL',
        'timing_late': 'LAT',
        'discipline': 'DIS',
        'home': 'HOM',
        'away': 'AWY',
        'longshot': 'LNG',
        'open_play': 'OPN',
        'height_factor': 'HGT',
        'experience': 'EXP'
    }
    
    parts = []
    for dim, code in codes.items():
        val = int(dimensions.get(dim, 50))
        parts.append(f"{code}{val}")
    
    return '|'.join(parts)

def assign_profile_tags(dimensions: Dict, gk_info: Dict) -> List[str]:
    """Assigne les tags de profil"""
    tags = []
    
    # Score global
    overall = np.mean(list(dimensions.values()))
    
    # Tag principal
    if overall >= 80:
        tags.append('ELITE_GK')
    elif overall >= 65:
        tags.append('SOLID_GK')
    elif overall >= 50:
        tags.append('AVERAGE_GK')
    elif overall >= 35:
        tags.append('BELOW_AVG_GK')
    else:
        tags.append('LIABILITY_GK')
    
    # Tags spécifiques
    if dimensions.get('shot_stopping', 50) >= 75:
        tags.append('SHOT_STOPPER')
    elif dimensions.get('shot_stopping', 50) <= 30:
        tags.append('SHOT_STOPPER_WEAK')
    
    if dimensions.get('aerial', 50) >= 75:
        tags.append('AERIAL_DOMINANT')
    elif dimensions.get('aerial', 50) <= 30:
        tags.append('AERIAL_WEAK')
    
    if dimensions.get('set_piece', 50) >= 75:
        tags.append('SET_PIECE_STRONG')
    elif dimensions.get('set_piece', 50) <= 30:
        tags.append('SET_PIECE_WEAK')
    
    if dimensions.get('timing_early', 50) <= 25:
        tags.append('SLOW_STARTER')
    elif dimensions.get('timing_early', 50) >= 75:
        tags.append('FAST_STARTER')
    
    if dimensions.get('timing_late', 50) <= 25:
        tags.append('LATE_COLLAPSER')
    elif dimensions.get('timing_late', 50) >= 75:
        tags.append('STRONG_FINISHER')
    
    if dimensions.get('discipline', 50) <= 30:
        tags.append('PENALTY_PRONE')
    
    if dimensions.get('home', 50) >= 75 and dimensions.get('away', 50) <= 40:
        tags.append('HOME_ONLY')
    elif dimensions.get('away', 50) >= 70:
        tags.append('ROAD_WARRIOR')
    
    if dimensions.get('longshot', 50) <= 30:
        tags.append('LONGSHOT_WEAK')
    
    # Tags physiques
    height = gk_info.get('height', 188)
    if height >= 195:
        tags.append('TALL_GK')
    elif height <= 185:
        tags.append('SHORT_GK')
    
    age = gk_info.get('age', 28)
    if age >= 35:
        tags.append('VETERAN')
    elif age <= 23:
        tags.append('YOUNG_GK')
    
    return tags

def generate_exploit_paths(dimensions: Dict) -> List[Dict]:
    """Génère les exploit paths"""
    exploits = []
    
    exploit_mapping = {
        'shot_stopping': {'market': 'Goals Over', 'attacker': 'ANY_ATTACKER', 'tactic': 'Tirer cadré'},
        'aerial': {'market': 'Header Goal', 'attacker': 'HEADER_SPECIALIST', 'tactic': 'Centres et corners'},
        'set_piece': {'market': 'Set Piece Goal', 'attacker': 'SET_PIECE_THREAT', 'tactic': 'Corners/FK'},
        'timing_early': {'market': 'First Goalscorer', 'attacker': 'EARLY_BIRD', 'tactic': 'Attaquer tôt'},
        'timing_late': {'market': 'Last Goalscorer', 'attacker': 'DIESEL/CLUTCH', 'tactic': 'Pousser tard'},
        'discipline': {'market': 'Penalty Scored', 'attacker': 'PENALTY_TAKER', 'tactic': 'Provoquer fautes'},
        'away': {'market': 'Home Goals', 'attacker': 'HOME_SPECIALIST', 'tactic': 'Exploiter déplacement'},
        'home': {'market': 'Away Goals', 'attacker': 'AWAY_SPECIALIST', 'tactic': 'Exploiter domicile'},
        'longshot': {'market': 'Outside Box Goal', 'attacker': 'LONGSHOT_SPECIALIST', 'tactic': 'Tirs de loin'}
    }
    
    for dim, mapping in exploit_mapping.items():
        value = dimensions.get(dim, 50)
        
        if value <= 25:
            confidence, exploit_type = 'HIGH', 'ABSOLUTE'
            edge = round((50 - value) / 7, 1)
        elif value <= 40:
            confidence, exploit_type = 'MEDIUM', 'MODERATE'
            edge = round((50 - value) / 12, 1)
        elif value <= 50:
            confidence, exploit_type = 'LOW', 'MINOR'
            edge = round((50 - value) / 20, 1)
        else:
            continue
        
        exploits.append({
            'dimension': dim,
            'value': int(value),
            'market': mapping['market'],
            'attacker_profile': mapping['attacker'],
            'tactic': mapping['tactic'],
            'confidence': confidence,
            'exploit_type': exploit_type,
            'edge_estimate': max(0.5, edge)
        })
    
    exploits.sort(key=lambda x: x['edge_estimate'], reverse=True)
    return exploits[:5]

def generate_enriched_name(dimensions: Dict, tags: List[str]) -> str:
    """Génère le nom enrichi"""
    overall = np.mean(list(dimensions.values()))
    
    # Niveau
    if overall >= 80:
        level = "Mur"
    elif overall >= 65:
        level = "Gardien Solide"
    elif overall >= 50:
        level = "Gardien Moyen"
    elif overall >= 35:
        level = "Gardien Fragile"
    else:
        level = "Passoire"
    
    # Force principale
    max_dim = max(dimensions.items(), key=lambda x: x[1])
    strength_names = {
        'shot_stopping': 'Réflexes',
        'aerial': 'Aérien',
        'set_piece': 'Coups de Pied',
        'timing_early': 'Départ Fort',
        'timing_late': 'Finition',
        'discipline': 'Discipliné',
        'home': 'Domicile',
        'away': 'Extérieur',
        'longshot': 'Longue Distance',
        'open_play': 'Jeu Ouvert',
        'height_factor': 'Envergure',
        'experience': 'Expérience'
    }
    strength = strength_names.get(max_dim[0], 'Complet')
    
    # Faiblesse
    min_dim = min(dimensions.items(), key=lambda x: x[1])
    weakness_names = {
        'shot_stopping': 'Arrêts Faibles',
        'aerial': 'Aérien Faible',
        'set_piece': 'CPA Faible',
        'timing_early': 'Lent au Départ',
        'timing_late': 'S\'effondre',
        'discipline': 'Penalties',
        'home': 'Fragile Dom.',
        'away': 'Fragile Ext.',
        'longshot': 'Frappes de Loin',
        'open_play': 'Jeu Ouvert',
        'height_factor': 'Taille',
        'experience': 'Inexpérimenté'
    }
    
    if min_dim[1] <= 35:
        weakness = weakness_names.get(min_dim[0], '')
        return f"{level} {strength}, {weakness}"
    
    return f"{level} {strength}"

def convert_numpy(obj):
    """Convertit les types numpy"""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(item) for item in obj]
    elif hasattr(obj, 'item'):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def main():
    print("=" * 80)
    print("🧤 GOALKEEPER DNA V2.0 - APPROCHE HYBRIDE")
    print("   Defense DNA + Données Gardiens = Profils Uniques")
    print("=" * 80)
    
    # 1. Charger Defense DNA
    print("\n📂 Chargement Defense DNA...")
    defense_teams = load_defense_dna()
    print(f"   ✅ {len(defense_teams)} équipes chargées")
    
    # 2. Créer les profils gardiens
    print("\n🧤 Création des profils gardiens...")
    goalkeepers = []
    matched = 0
    unmatched = []
    
    for team_data in defense_teams:
        team_name = team_data.get('team_name', '')
        league = team_data.get('league', '')
        
        # Trouver le gardien
        gk_team = find_team_match(team_name, STARTING_GOALKEEPERS)
        
        if gk_team and gk_team in STARTING_GOALKEEPERS:
            gk_info = STARTING_GOALKEEPERS[gk_team]
            matched += 1
        else:
            # Gardien par défaut
            gk_info = {'name': f"GK {team_name}", 'age': 28, 'height': 188, 'nationality': 'Unknown'}
            unmatched.append(team_name)
        
        # Calculer dimensions
        dimensions = calculate_gk_dimensions(team_data, gk_info)
        
        # Score global
        overall_score = round(np.mean(list(dimensions.values())), 1)
        
        # Tags
        tags = assign_profile_tags(dimensions, gk_info)
        
        # Exploit paths
        exploits = generate_exploit_paths(dimensions)
        
        # Profil complet
        gk_profile = {
            'player_name': gk_info['name'],
            'team': team_name,
            'league': league,
            'age': gk_info.get('age', 28),
            'height': gk_info.get('height', 188),
            'nationality': gk_info.get('nationality', 'Unknown'),
            
            'dimensions': dimensions,
            'overall_score': overall_score,
            
            'fingerprint_code': generate_fingerprint(dimensions),
            'fingerprint_compact': generate_compact_fingerprint(dimensions),
            
            'profile_tags': tags,
            'dna_string': '-'.join(tags),
            
            'exploit_paths': exploits,
            'enriched_name': generate_enriched_name(dimensions, tags),
            
            # Lien avec Defense DNA
            'team_defense_level': team_data.get('defense_level', {}).get('name', 'Unknown'),
            'team_defense_pct': team_data.get('percentiles_v5_1', {}).get('global', 50)
        }
        
        goalkeepers.append(gk_profile)
    
    print(f"   ✅ {len(goalkeepers)} gardiens créés")
    print(f"   ✅ {matched} gardiens identifiés par nom")
    if unmatched:
        print(f"   ⚠️ {len(unmatched)} équipes sans gardien identifié")
    
    # 3. Sauvegarder
    print("\n💾 Sauvegarde...")
    goalkeepers = convert_numpy(goalkeepers)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(goalkeepers, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # 4. Vérifier unicité
    print("\n🔍 Vérification unicité...")
    fingerprints = [gk['fingerprint_code'] for gk in goalkeepers]
    unique_fp = len(set(fingerprints))
    print(f"   • Fingerprints uniques: {unique_fp}/{len(goalkeepers)} ({unique_fp/len(goalkeepers)*100:.1f}%)")
    
    # 5. Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT GOALKEEPER DNA V2.0")
    print("=" * 80)
    
    # Distribution par niveau
    print("\n📈 Distribution par niveau:")
    level_counts = {}
    for gk in goalkeepers:
        level = gk['profile_tags'][0] if gk['profile_tags'] else 'UNKNOWN'
        level_counts[level] = level_counts.get(level, 0) + 1
    
    for level in ['ELITE_GK', 'SOLID_GK', 'AVERAGE_GK', 'BELOW_AVG_GK', 'LIABILITY_GK']:
        count = level_counts.get(level, 0)
        pct = count / len(goalkeepers) * 100
        bar = '█' * int(pct / 2)
        print(f"   {level:<15}: {count:2} ({pct:5.1f}%) {bar}")
    
    # Top gardiens
    print("\n🏆 TOP 10 GARDIENS:")
    top_gks = sorted(goalkeepers, key=lambda x: x['overall_score'], reverse=True)[:10]
    for i, gk in enumerate(top_gks, 1):
        print(f"   {i:2}. {gk['player_name']:<22} ({gk['team']:<20}) | Score: {gk['overall_score']:.1f}")
    
    # Cibles (pires gardiens)
    print("\n🎯 TOP 10 CIBLES (Gardiens Vulnérables):")
    bottom_gks = sorted(goalkeepers, key=lambda x: x['overall_score'])[:10]
    for i, gk in enumerate(bottom_gks, 1):
        tags = [t for t in gk['profile_tags'] if 'WEAK' in t or 'COLLAPSER' in t or 'SLOW' in t]
        tag_str = ', '.join(tags[:2]) if tags else '-'
        print(f"   {i:2}. {gk['player_name']:<22} ({gk['team']:<20}) | Score: {gk['overall_score']:.1f} | {tag_str}")
    
    # Exemple complet
    if top_gks:
        example = top_gks[0]
        print(f"\n{'=' * 80}")
        print(f"📋 EXEMPLE COMPLET: {example['player_name']}")
        print(f"{'=' * 80}")
        print(f"   Équipe: {example['team']} ({example['league']})")
        print(f"   Âge: {example['age']} | Taille: {example['height']}cm | {example['nationality']}")
        print(f"\n   🆔 Fingerprint: {example['fingerprint_code']}")
        print(f"   📊 Compact: {example['fingerprint_compact']}")
        print(f"   🏷️ Nom: {example['enriched_name']}")
        print(f"   🧬 DNA: {example['dna_string']}")
        
        print(f"\n   📈 DIMENSIONS:")
        for dim, val in example['dimensions'].items():
            bar = '█' * int(val / 5)
            status = '🟢' if val >= 70 else '🟡' if val >= 50 else '🔴'
            print(f"      {dim:<15}: {val:3.0f} {status} {bar}")
        
        if example['exploit_paths']:
            print(f"\n   🎯 EXPLOIT PATHS:")
            for exp in example['exploit_paths'][:3]:
                print(f"      • {exp['market']:<20} [{exp['confidence']}] Edge: {exp['edge_estimate']}%")
    
    # Stats par ligue
    print(f"\n📊 GARDIENS PAR LIGUE:")
    league_stats = {}
    for gk in goalkeepers:
        league = gk['league']
        if league not in league_stats:
            league_stats[league] = {'count': 0, 'total_score': 0}
        league_stats[league]['count'] += 1
        league_stats[league]['total_score'] += gk['overall_score']
    
    for league, stats in sorted(league_stats.items()):
        avg = stats['total_score'] / stats['count']
        print(f"   {league}: {stats['count']} gardiens | Avg Score: {avg:.1f}")
    
    print(f"\n{'=' * 80}")
    print(f"✅ GOALKEEPER DNA V2.0 COMPLET - {len(goalkeepers)} GARDIENS")
    print(f"   📁 Fichier: {OUTPUT_FILE}")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()

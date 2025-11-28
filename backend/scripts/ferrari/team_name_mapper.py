#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 - Mapping Intelligent des Noms d'Équipes
Version: ULTIMATE
Date: 28 Nov 2025

Stratégie:
1. Normalisation avancée (FC, accents, tirets, etc.)
2. Règles de mapping connues
3. Fuzzy matching pour les cas restants
4. Validation manuelle des cas douteux
"""

import os
import sys
import re
import unicodedata
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Tuple, Optional
import logging
from difflib import SequenceMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}

# ══════════════════════════════════════════════════════════════
# MAPPINGS MANUELS CONNUS (cas complexes)
# ══════════════════════════════════════════════════════════════

KNOWN_MAPPINGS = {
    # Format: "match_results_name": "odds_name"
    
    # Angleterre
    "Arsenal FC": "Arsenal",
    "Aston Villa FC": "Aston Villa",
    "AFC Bournemouth": "Bournemouth",
    "Brentford FC": "Brentford",
    "Brighton & Hove Albion FC": "Brighton",
    "Burnley FC": "Burnley",
    "Chelsea FC": "Chelsea",
    "Crystal Palace FC": "Crystal Palace",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Leeds United FC": "Leeds United",
    "Liverpool FC": "Liverpool",
    "Manchester City FC": "Manchester City",
    "Manchester United FC": "Manchester United",
    "Newcastle United FC": "Newcastle United",
    "Nottingham Forest FC": "Nottingham Forest",
    "Tottenham Hotspur FC": "Tottenham Hotspur",
    "West Ham United FC": "West Ham United",
    "Wolverhampton Wanderers FC": "Wolverhampton",
    "Sunderland AFC": "Sunderland",
    
    # Espagne
    "FC Barcelona": "Barcelona",
    "Real Madrid CF": "Real Madrid",
    "Club Atlético de Madrid": "Atletico Madrid",
    "Sevilla FC": "Sevilla",
    "Valencia CF": "Valencia",
    "Villarreal CF": "Villarreal",
    "Real Betis Balompié": "Real Betis",
    "Real Sociedad de Fútbol": "Real Sociedad",
    "Athletic Club": "Athletic Bilbao",
    "RC Celta de Vigo": "Celta Vigo",
    "Getafe CF": "Getafe",
    "RCD Mallorca": "Mallorca",
    "RCD Espanyol de Barcelona": "Espanyol",
    "Deportivo Alavés": "Alaves",
    "Rayo Vallecano de Madrid": "Rayo Vallecano",
    "Girona FC": "Girona",
    "Real Oviedo": "Real Oviedo",
    "Levante UD": "Levante",
    
    # Italie
    "FC Internazionale Milano": "Inter Milan",
    "Juventus FC": "Juventus",
    "AC Milan": "AC Milan",
    "SSC Napoli": "Napoli",
    "AS Roma": "AS Roma",
    "SS Lazio": "Lazio",
    "ACF Fiorentina": "Fiorentina",
    "Torino FC": "Torino",
    "Bologna FC 1909": "Bologna",
    "Genoa CFC": "Genoa",
    "Udinese Calcio": "Udinese",
    "US Sassuolo Calcio": "Sassuolo",
    "Cagliari Calcio": "Cagliari",
    "Hellas Verona FC": "Verona",
    "US Lecce": "Lecce",
    "Parma Calcio 1913": "Parma",
    "Como 1907": "Como",
    "AC Pisa 1909": "Pisa",
    
    # Allemagne
    "FC Bayern München": "Bayern Munich",
    "Borussia Dortmund": "Borussia Dortmund",
    "Borussia Mönchengladbach": "Borussia Monchengladbach",
    "Bayer 04 Leverkusen": "Bayer Leverkusen",
    "RB Leipzig": "RB Leipzig",
    "VfB Stuttgart": "VfB Stuttgart",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "SV Werder Bremen": "Werder Bremen",
    "VfL Wolfsburg": "Wolfsburg",
    "FC Augsburg": "Augsburg",
    "1. FC Union Berlin": "Union Berlin",
    "1. FSV Mainz 05": "Mainz 05",
    "1. FC Heidenheim 1846": "Heidenheim",
    "FC St. Pauli 1910": "St. Pauli",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "SC Freiburg": "SC Freiburg",
    
    # France
    "Paris Saint-Germain FC": "Paris Saint Germain",
    "Olympique de Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "AS Monaco FC": "Monaco",
    "Lille OSC": "Lille",
    "OGC Nice": "Nice",
    "Stade Rennais FC 1901": "Rennes",
    "Racing Club de Lens": "Lens",
    "RC Strasbourg Alsace": "Strasbourg",
    "FC Nantes": "Nantes",
    "Stade Brestois 29": "Brest",
    "Toulouse FC": "Toulouse",
    "FC Metz": "Metz",
    "Le Havre AC": "Le Havre",
    "Angers SCO": "Angers",
    "AJ Auxerre": "Auxerre",
    "FC Lorient": "Lorient",
    
    # Portugal
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting Clube de Portugal": "Sporting CP",
    "FC Porto": "Porto",
    
    # Pays-Bas
    "AFC Ajax": "Ajax",
    "PSV": "PSV Eindhoven",
    "Feyenoord Rotterdam": "Feyenoord",
    
    # Belgique
    "Club Brugge KV": "Club Brugge",
    "Royale Union Saint-Gilloise": "Union Saint-Gilloise",
    
    # Turquie
    "Galatasaray SK": "Galatasaray",
    "Fenerbahçe SK": "Fenerbahce",
    "Beşiktaş JK": "Besiktas",
    
    # Grèce
    "PAE Olympiakos SFP": "Olympiacos",
    "Panathinaikos FC": "Panathinaikos FC",
    
    # Autres
    "FK Bodø/Glimt": "Bodo/Glimt",
    "SK Slavia Praha": "Slavia Prague",
    "ŠK Slovan Bratislava": "Slovan Bratislava",
    "FC København": "FC Copenhagen",
    "Shamrock Rovers": "Shamrock Rovers",
    "Omonoia FC": "Omonoia",
    "Qarabağ Ağdam FK": "Qarabag",
}

# ══════════════════════════════════════════════════════════════
# FONCTIONS DE NORMALISATION
# ══════════════════════════════════════════════════════════════

def remove_accents(text: str) -> str:
    """Enlève les accents d'un texte"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def normalize_team_name(name: str) -> str:
    """
    Normalise un nom d'équipe pour le matching
    """
    if not name:
        return ""
    
    result = name
    
    # 1. Enlever accents
    result = remove_accents(result)
    
    # 2. Convertir en minuscules
    result = result.lower()
    
    # 3. Enlever suffixes courants
    suffixes_to_remove = [
        ' fc', ' cf', ' sc', ' ac', ' afc', ' sfc',
        ' fk', ' sk', ' bk', ' if',
        ' calcio', ' football club',
        ' 1909', ' 1907', ' 1913', ' 1910', ' 1846', ' 1899', ' 1901',
        ' de futbol', ' de football',
    ]
    for suffix in suffixes_to_remove:
        if result.endswith(suffix):
            result = result[:-len(suffix)]
    
    # 4. Enlever préfixes courants
    prefixes_to_remove = ['fc ', 'afc ', 'ac ', '1. ', 'rc ', 'rcd ', 'us ', 'ss ', 'ssc ']
    for prefix in prefixes_to_remove:
        if result.startswith(prefix):
            result = result[len(prefix):]
    
    # 5. Remplacements spécifiques
    replacements = {
        'ü': 'u', 'ö': 'o', 'ä': 'a', 'ß': 'ss',
        'ø': 'o', 'æ': 'ae', 'å': 'a',
        'ñ': 'n', 'ç': 'c',
        '&': 'and',
        '-': ' ',
        '.': '',
        "'": '',
    }
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    # 6. Enlever espaces multiples
    result = ' '.join(result.split())
    
    # 7. Trim
    result = result.strip()
    
    return result


def similarity_score(str1: str, str2: str) -> float:
    """Calcule un score de similarité entre deux chaînes (0-1)"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def find_best_match(name: str, candidates: List[str], threshold: float = 0.6) -> Tuple[Optional[str], float]:
    """
    Trouve le meilleur match parmi les candidats
    
    Returns:
        (best_match, score) ou (None, 0) si pas de match
    """
    normalized_name = normalize_team_name(name)
    
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        normalized_candidate = normalize_team_name(candidate)
        
        # Score basé sur la normalisation exacte
        if normalized_name == normalized_candidate:
            return (candidate, 1.0)
        
        # Score de similarité
        score = similarity_score(normalized_name, normalized_candidate)
        
        # Bonus si contient le nom principal
        main_words = normalized_name.split()
        if main_words:
            for word in main_words:
                if len(word) > 3 and word in normalized_candidate:
                    score += 0.2
        
        if score > best_score:
            best_score = score
            best_match = candidate
    
    if best_score >= threshold:
        return (best_match, best_score)
    
    return (None, 0)


# ══════════════════════════════════════════════════════════════
# FONCTIONS DE BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_match_results_teams(conn) -> List[str]:
    """Récupère toutes les équipes uniques de match_results"""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT home_team FROM match_results WHERE is_finished = true
        UNION
        SELECT DISTINCT away_team FROM match_results WHERE is_finished = true
    """)
    return [row[0] for row in cur.fetchall() if row[0]]


def get_odds_teams(conn) -> List[str]:
    """Récupère toutes les équipes uniques de odds"""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT home_team FROM odds WHERE home_team IS NOT NULL
        UNION
        SELECT DISTINCT away_team FROM odds WHERE away_team IS NOT NULL
    """)
    return [row[0] for row in cur.fetchall() if row[0]]


def create_team_name_mapping_table(conn):
    """Crée la table de mapping si elle n'existe pas"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_name_mapping (
            id SERIAL PRIMARY KEY,
            source_name VARCHAR(255) NOT NULL,
            source_table VARCHAR(50) NOT NULL,
            canonical_name VARCHAR(255) NOT NULL,
            normalized_name VARCHAR(255),
            match_method VARCHAR(50),
            confidence_score NUMERIC(4,2),
            is_verified BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_team_mapping_source UNIQUE(source_name, source_table)
        );
        
        CREATE INDEX IF NOT EXISTS idx_tnm_source ON team_name_mapping(source_name);
        CREATE INDEX IF NOT EXISTS idx_tnm_canonical ON team_name_mapping(canonical_name);
        CREATE INDEX IF NOT EXISTS idx_tnm_normalized ON team_name_mapping(normalized_name);
    """)
    conn.commit()
    logger.info("✅ Table team_name_mapping créée/vérifiée")


def insert_mapping(conn, source_name: str, source_table: str, canonical_name: str, 
                   method: str, confidence: float, verified: bool = False):
    """Insère ou met à jour un mapping"""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO team_name_mapping 
            (source_name, source_table, canonical_name, normalized_name, match_method, confidence_score, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_name, source_table) DO UPDATE SET
            canonical_name = EXCLUDED.canonical_name,
            normalized_name = EXCLUDED.normalized_name,
            match_method = EXCLUDED.match_method,
            confidence_score = EXCLUDED.confidence_score,
            is_verified = EXCLUDED.is_verified,
            updated_at = NOW()
    """, (source_name, source_table, canonical_name, normalize_team_name(source_name), 
          method, confidence, verified))


# ══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════════════════════════

def build_team_mappings():
    """
    Construit les mappings entre match_results et odds
    """
    logger.info("🏎️ FERRARI 2.0 - Construction des mappings d'équipes")
    logger.info("=" * 60)
    
    conn = get_db_connection()
    
    try:
        # 1. Créer la table de mapping
        create_team_name_mapping_table(conn)
        
        # 2. Récupérer les équipes
        mr_teams = get_match_results_teams(conn)
        odds_teams = get_odds_teams(conn)
        
        logger.info(f"📊 Équipes match_results: {len(mr_teams)}")
        logger.info(f"📊 Équipes odds: {len(odds_teams)}")
        
        # 3. Stats de mapping
        mapped_known = 0
        mapped_exact = 0
        mapped_normalized = 0
        mapped_fuzzy = 0
        not_mapped = 0
        
        # 4. Traiter chaque équipe de match_results
        for mr_team in mr_teams:
            # 4a. Vérifier les mappings connus
            if mr_team in KNOWN_MAPPINGS:
                canonical = KNOWN_MAPPINGS[mr_team]
                insert_mapping(conn, mr_team, 'match_results', canonical, 'known_mapping', 1.0, True)
                mapped_known += 1
                continue
            
            # 4b. Match exact
            if mr_team in odds_teams:
                insert_mapping(conn, mr_team, 'match_results', mr_team, 'exact_match', 1.0, True)
                mapped_exact += 1
                continue
            
            # 4c. Match normalisé
            normalized_mr = normalize_team_name(mr_team)
            found_normalized = False
            for odds_team in odds_teams:
                if normalize_team_name(odds_team) == normalized_mr:
                    insert_mapping(conn, mr_team, 'match_results', odds_team, 'normalized_match', 0.95, True)
                    mapped_normalized += 1
                    found_normalized = True
                    break
            
            if found_normalized:
                continue
            
            # 4d. Fuzzy matching
            best_match, score = find_best_match(mr_team, odds_teams, threshold=0.7)
            if best_match:
                insert_mapping(conn, mr_team, 'match_results', best_match, 'fuzzy_match', score, False)
                mapped_fuzzy += 1
                continue
            
            # 4e. Pas de match - utiliser le nom original
            insert_mapping(conn, mr_team, 'match_results', mr_team, 'no_match', 0.0, False)
            not_mapped += 1
            logger.warning(f"⚠️ Pas de match pour: {mr_team}")
        
        conn.commit()
        
        # 5. Résumé
        logger.info("=" * 60)
        logger.info("🏆 MAPPING TERMINÉ!")
        logger.info(f"  ✅ Mappings connus: {mapped_known}")
        logger.info(f"  ✅ Match exact: {mapped_exact}")
        logger.info(f"  ✅ Match normalisé: {mapped_normalized}")
        logger.info(f"  ⚠️ Fuzzy match: {mapped_fuzzy}")
        logger.info(f"  ❌ Non mappés: {not_mapped}")
        logger.info(f"  📊 TOTAL: {mapped_known + mapped_exact + mapped_normalized + mapped_fuzzy + not_mapped}")
        logger.info("=" * 60)
        
        return {
            'known': mapped_known,
            'exact': mapped_exact,
            'normalized': mapped_normalized,
            'fuzzy': mapped_fuzzy,
            'not_mapped': not_mapped
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        conn.rollback()
        raise
        
    finally:
        conn.close()


def get_canonical_name(conn, source_name: str, source_table: str = 'match_results') -> str:
    """
    Récupère le nom canonique pour une équipe
    Utilisé par les autres scripts
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT canonical_name FROM team_name_mapping
        WHERE source_name = %s AND source_table = %s
    """, (source_name, source_table))
    
    result = cur.fetchone()
    if result:
        return result[0]
    
    # Si pas trouvé, retourner le nom original
    return source_name


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    build_team_mappings()

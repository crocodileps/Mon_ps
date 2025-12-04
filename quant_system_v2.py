#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════════
QUANT SYSTEM V2.0 - ANALYSE POST-MATCH PROFESSIONNELLE
═══════════════════════════════════════════════════════════════════════════════════════════

COMPOSANTS:
1. Scraper Understat Shot-by-Shot (Game State xG)
2. Métriques Composites (RTI, DS, Lethality)
3. Classification 7 Nuances
4. EMA Time Decay
5. KPIs Quant (CLV, xROI, Noise/Signal)

Auteur: Mon_PS Quant Team
Date: 2025-12-04
═══════════════════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import math

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 1: SCRAPER UNDERSTAT SHOT-BY-SHOT
# ═══════════════════════════════════════════════════════════════════════════════════════════

class UnderstatScraper:
    """Scrape les données tir-par-tir d'Understat pour l'analyse Game State"""
    
    BASE_URL = "https://understat.com"
    
    LEAGUES = {
        'EPL': 'https://understat.com/league/EPL',
        'La_Liga': 'https://understat.com/league/La_Liga',
        'Bundesliga': 'https://understat.com/league/Bundesliga',
        'Serie_A': 'https://understat.com/league/Serie_A',
        'Ligue_1': 'https://understat.com/league/Ligue_1',
        'RFPL': 'https://understat.com/league/RFPL',  # Russian Premier League
    }
    
    @staticmethod
    def scrape_match_shots(match_id):
        """
        Scrape les données tir-par-tir d'un match Understat
        
        Returns:
            dict avec 'home' et 'away' contenant les listes de tirs
        """
        url = f"https://understat.com/match/{match_id}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            # Extraction du JSON shotsData via Regex
            match_data = re.search(r"shotsData\s*=\s*JSON\.parse\('(.*?)'\)", response.text)
            
            if not match_data:
                return None
            
            # Décodage du JSON string (escape unicode)
            json_str = match_data.group(1).encode('utf-8').decode('unicode_escape')
            shots = json.loads(json_str)
            
            processed = {'home': [], 'away': []}
            
            for team_key, team_name in [('h', 'home'), ('a', 'away')]:
                for shot in shots.get(team_key, []):
                    processed[team_name].append({
                        'minute': int(shot.get('minute', 0)),
                        'xG': float(shot.get('xG', 0)),
                        'result': shot.get('result', 'Unknown'),  # Goal, Missed, Saved, Blocked
                        'player': shot.get('player', 'Unknown'),
                        'situation': shot.get('situation', 'OpenPlay'),  # OpenPlay, Corner, DirectFreekick, Penalty
                        'shot_type': shot.get('shotType', 'Unknown'),  # RightFoot, LeftFoot, Header
                        'last_action': shot.get('lastAction', 'Unknown'),  # Pass, Cross, Throughball, etc.
                        'x': float(shot.get('X', 0)),  # Position X (0-1)
                        'y': float(shot.get('Y', 0)),  # Position Y (0-1)
                    })
            
            return processed
            
        except Exception as e:
            print(f"   ⚠️ Erreur scraping Understat match {match_id}: {e}")
            return None
    
    @staticmethod
    def scrape_match_roster(match_id):
        """Scrape les données de roster/match info"""
        url = f"https://understat.com/match/{match_id}"
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            # Extraction rostersData
            roster_match = re.search(r"rostersData\s*=\s*JSON\.parse\('(.*?)'\)", response.text)
            
            if roster_match:
                json_str = roster_match.group(1).encode('utf-8').decode('unicode_escape')
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            return None
    
    @staticmethod
    def find_match_id(home_team, away_team, match_date, league='EPL'):
        """
        Trouve l'ID de match Understat basé sur les équipes et la date
        
        Note: Nécessite de scraper la page de la ligue pour trouver le match
        """
        # Mapping des noms d'équipes (notre DB vs Understat)
        team_mappings = {
            'manchester united': 'Manchester United',
            'manchester city': 'Manchester City',
            'liverpool': 'Liverpool',
            'arsenal': 'Arsenal',
            'chelsea': 'Chelsea',
            'tottenham': 'Tottenham',
            'newcastle': 'Newcastle United',
            'west ham': 'West Ham',
            'aston villa': 'Aston Villa',
            'brighton': 'Brighton',
            'real madrid': 'Real Madrid',
            'barcelona': 'Barcelona',
            'atletico madrid': 'Atletico Madrid',
            'bayern': 'Bayern Munich',
            'dortmund': 'Borussia Dortmund',
            'psg': 'Paris Saint Germain',
            'marseille': 'Marseille',
            'lyon': 'Lyon',
            'juventus': 'Juventus',
            'inter': 'Inter',
            'milan': 'AC Milan',
            'napoli': 'Napoli',
            'roma': 'Roma',
            'leverkusen': 'Bayer Leverkusen',
        }
        
        # Cette fonction nécessiterait de scraper la page de la ligue
        # Pour l'instant, on utilise les match_id déjà dans match_xg_stats
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 2: CALCULS GAME STATE XG
# ═══════════════════════════════════════════════════════════════════════════════════════════

class GameStateCalculator:
    """Calcule le xG ajusté selon l'état du jeu (Game State)"""
    
    # Poids selon le Game State
    GAME_STATE_WEIGHTS = {
        'drawing': 1.05,        # Match nul = ouvert, les équipes attaquent
        'leading_1': 0.95,      # Mène de 1 = légèrement fermé
        'leading_2plus': 0.75,  # Mène de 2+ = garbage time pour l'équipe qui mène
        'trailing_1': 1.10,     # Mené de 1 = équipe pousse
        'trailing_2plus': 0.60, # Mené de 2+ = tirs désespérés (garbage xG)
    }
    
    # Poids temporel (fatigue, changements)
    MINUTE_WEIGHTS = {
        (0, 30): 1.0,
        (30, 60): 1.0,
        (60, 75): 0.95,
        (75, 90): 0.85,
        (90, 120): 0.80,  # Prolongations/temps additionnel
    }
    
    @classmethod
    def calculate_adjusted_xg(cls, shots_data):
        """
        Calcule le xG ajusté en tenant compte du Game State
        
        Args:
            shots_data: dict avec 'home' et 'away' contenant les listes de tirs
            
        Returns:
            dict avec xG brut et ajusté pour chaque équipe
        """
        if not shots_data:
            return None
        
        # Fusionner et trier tous les tirs par minute
        all_shots = []
        for shot in shots_data.get('home', []):
            all_shots.append({**shot, 'team': 'home'})
        for shot in shots_data.get('away', []):
            all_shots.append({**shot, 'team': 'away'})
        
        all_shots.sort(key=lambda x: x['minute'])
        
        # Initialisation
        home_xg_raw = 0
        away_xg_raw = 0
        home_xg_adjusted = 0
        away_xg_adjusted = 0
        home_goals = 0
        away_goals = 0
        
        # Statistiques par situation
        open_play_xg = {'home': 0, 'away': 0}
        set_piece_xg = {'home': 0, 'away': 0}
        
        for shot in all_shots:
            xg = shot['xG']
            minute = shot['minute']
            team = shot['team']
            
            # xG brut
            if team == 'home':
                home_xg_raw += xg
            else:
                away_xg_raw += xg
            
            # Calculer le Game State actuel
            score_diff = home_goals - away_goals
            if team == 'away':
                score_diff = -score_diff  # Du point de vue de l'équipe qui tire
            
            if score_diff == 0:
                game_state = 'drawing'
            elif score_diff == 1:
                game_state = 'leading_1'
            elif score_diff >= 2:
                game_state = 'leading_2plus'
            elif score_diff == -1:
                game_state = 'trailing_1'
            else:
                game_state = 'trailing_2plus'
            
            # Poids Game State
            gs_weight = cls.GAME_STATE_WEIGHTS.get(game_state, 1.0)
            
            # Poids temporel
            time_weight = 1.0
            for (start, end), weight in cls.MINUTE_WEIGHTS.items():
                if start <= minute < end:
                    time_weight = weight
                    break
            
            # xG ajusté
            xg_adj = xg * gs_weight * time_weight
            
            if team == 'home':
                home_xg_adjusted += xg_adj
            else:
                away_xg_adjusted += xg_adj
            
            # Tracker par situation
            situation = shot.get('situation', 'OpenPlay')
            if situation in ['OpenPlay']:
                open_play_xg[team] += xg
            else:
                set_piece_xg[team] += xg
            
            # Mettre à jour le score si but
            if shot['result'] == 'Goal':
                if team == 'home':
                    home_goals += 1
                else:
                    away_goals += 1
        
        return {
            'home_xg_raw': round(home_xg_raw, 2),
            'away_xg_raw': round(away_xg_raw, 2),
            'total_xg_raw': round(home_xg_raw + away_xg_raw, 2),
            'home_xg_adjusted': round(home_xg_adjusted, 2),
            'away_xg_adjusted': round(away_xg_adjusted, 2),
            'total_xg_adjusted': round(home_xg_adjusted + away_xg_adjusted, 2),
            'home_open_play_xg': round(open_play_xg['home'], 2),
            'away_open_play_xg': round(open_play_xg['away'], 2),
            'home_set_piece_xg': round(set_piece_xg['home'], 2),
            'away_set_piece_xg': round(set_piece_xg['away'], 2),
            'shots_analyzed': len(all_shots),
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 3: MÉTRIQUES COMPOSITES (RTI, DS, LETHALITY)
# ═══════════════════════════════════════════════════════════════════════════════════════════

class CompositeMetrics:
    """Calcule les métriques composites hybrides"""
    
    @staticmethod
    def calculate_rti(xg, dangerous_attacks, corners, shots_in_box):
        """
        Real Threat Index (RTI) - Combine qualité (xG) et pression territoriale
        
        RTI = (xG × 10) + (AttaquesDangereuses × 0.1) + (Corners × 0.5) + (TirsBox × 1)
        
        Interprétation:
        - RTI Élevé + Score Faible = UNLUCKY (Buy Signal)
        - RTI Faible + Score Élevé = LUCKY (Sell Signal)
        """
        return (float(xg) * 10) + (dangerous_attacks * 0.1) + (corners * 0.5) + (shots_in_box * 1)
    
    @staticmethod
    def calculate_defensive_stress(goalkeeper_saves, clearances, blocked_shots):
        """
        Defensive Stress (DS) - Prédit si une défense va craquer
        
        DS = (Arrêts × 2) + (Dégagements × 0.5) + (TirsBloqués × 1)
        
        Interprétation:
        - DS Haut + Buts Encaissés Faible = Gardien a sauvé le match (ne pas parier sur leur défense)
        """
        return (goalkeeper_saves * 2) + (clearances * 0.5) + (blocked_shots * 1)
    
    @staticmethod
    def calculate_lethality(xg, dangerous_attacks):
        """
        Lethality Ratio - Efficacité de création
        
        Lethality = xG / AttaquesDangereuses
        
        Interprétation:
        - Ratio Haut (ex: Real Madrid): N'ont pas besoin de dominer pour marquer
        - Ratio Bas (ex: PSG stérile): Possession sans danger réel
        """
        if dangerous_attacks == 0:
            return 0
        return float(xg) / dangerous_attacks
    
    @staticmethod
    def calculate_shot_quality_index(xg, total_shots):
        """
        Shot Quality Index - Qualité moyenne des occasions
        
        SQI = xG / Tirs
        """
        if total_shots == 0:
            return 0
        return float(xg) / total_shots
    
    @staticmethod
    def calculate_all(stats):
        """
        Calcule toutes les métriques composites pour un match
        
        Args:
            stats: dict avec les stats du match (depuis match_advanced_stats + match_xg_stats)
        """
        # Extraire les valeurs (avec defaults)
        home_xg = float(stats.get('home_xg') or 0)
        away_xg = float(stats.get('away_xg') or 0)
        
        home_shots = int(stats.get('home_shots') or 0)
        away_shots = int(stats.get('away_shots') or 0)
        
        home_shots_box = int(stats.get('home_shots_inside_box') or 0)
        away_shots_box = int(stats.get('away_shots_inside_box') or 0)
        
        home_big_chances = int(stats.get('home_big_chances') or 0)
        away_big_chances = int(stats.get('away_big_chances') or 0)
        
        # Pour RTI, on utilise big_chances comme proxy pour dangerous_attacks
        # (Understat n'a pas cette métrique directement)
        home_dangerous = home_big_chances * 3  # Estimation
        away_dangerous = away_big_chances * 3
        
        # Corners (pas dans nos données actuelles, estimation)
        home_corners = int(stats.get('home_corners') or home_shots // 3)
        away_corners = int(stats.get('away_corners') or away_shots // 3)
        
        # Calculs
        return {
            'home_rti': round(CompositeMetrics.calculate_rti(home_xg, home_dangerous, home_corners, home_shots_box), 2),
            'away_rti': round(CompositeMetrics.calculate_rti(away_xg, away_dangerous, away_corners, away_shots_box), 2),
            'home_lethality': round(CompositeMetrics.calculate_lethality(home_xg, home_dangerous) if home_dangerous else 0, 3),
            'away_lethality': round(CompositeMetrics.calculate_lethality(away_xg, away_dangerous) if away_dangerous else 0, 3),
            'home_shot_quality': round(CompositeMetrics.calculate_shot_quality_index(home_xg, home_shots), 3),
            'away_shot_quality': round(CompositeMetrics.calculate_shot_quality_index(away_xg, away_shots), 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 4: CLASSIFICATION 7 NUANCES
# ═══════════════════════════════════════════════════════════════════════════════════════════

class QuantClassifier:
    """
    Classification en 7 nuances au lieu du binaire Win/Loss
    
    UNLUCKY (Process correct, pas de changement):
    - FINISHING_NOISE: xG > 2.5, dominance totale mais 0-0
    - KEEPER_ALPHA: Post-Shot xG énorme mais gardien surperformant
    - GAME_STATE_SHOCK: Carton rouge précoce, blessure clé
    
    BAD_CALL (Erreur modèle, action requise):
    - TACTICAL_MISMATCH: Match fermé non détecté (xG < 1.0)
    - MARKET_EFFICIENCY: CLV négatif, le marché savait avant nous
    - FAKE_DOMINANCE: RTI élevé mais xG faible (possession stérile)
    
    LUCKY (Faux positif, attention):
    - FALSE_ALPHA: Gagné grâce à penaltys/CSC, xG Open Play faible
    """
    
    @staticmethod
    def classify(bet_result, match_stats, market='over_25'):
        """
        Classifie un résultat de bet en 7 nuances
        
        Args:
            bet_result: dict avec 'is_won', 'odds', 'closing_odds'
            match_stats: dict avec xG, shots, big_chances, etc.
            market: 'over_25', 'btts_yes', etc.
            
        Returns:
            tuple (category, sub_category, reason, action)
        """
        is_won = bet_result.get('is_won', False)
        
        total_xg = float(match_stats.get('total_xg') or 0)
        total_xg_adjusted = float(match_stats.get('total_xg_adjusted') or total_xg)
        home_xg = float(match_stats.get('home_xg') or 0)
        away_xg = float(match_stats.get('away_xg') or 0)
        total_goals = int(match_stats.get('total_goals') or 0)
        
        home_big_chances_missed = int(match_stats.get('home_big_chances_missed') or 0)
        away_big_chances_missed = int(match_stats.get('away_big_chances_missed') or 0)
        total_bc_missed = home_big_chances_missed + away_big_chances_missed
        
        # Métriques composites
        home_rti = float(match_stats.get('home_rti') or 0)
        away_rti = float(match_stats.get('away_rti') or 0)
        total_rti = home_rti + away_rti
        
        # CLV (si disponible)
        odds_taken = float(bet_result.get('odds') or 1.85)
        closing_odds = float(bet_result.get('closing_odds') or odds_taken)
        clv_diff = (closing_odds - odds_taken) / odds_taken if odds_taken > 0 else 0
        
        # Red card / Game State Shock (si disponible)
        red_card_minute = match_stats.get('red_card_minute')
        
        # Open Play xG percentage
        total_open_play_xg = float(match_stats.get('home_open_play_xg') or 0) + float(match_stats.get('away_open_play_xg') or 0)
        open_play_pct = (total_open_play_xg / total_xg * 100) if total_xg > 0 else 0
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # ANALYSE DES PARIS GAGNANTS
        # ═══════════════════════════════════════════════════════════════════════════════
        if is_won:
            # FALSE_ALPHA: Gagné par miracle
            if market == 'over_25':
                if total_xg < 1.5 and total_goals > 2:
                    return ('LUCKY', 'FALSE_ALPHA', 
                            f'Gagné par miracle (xG={total_xg:.1f}, Open Play={open_play_pct:.0f}%). Penaltys/CSC probable.',
                            'TREAT_AS_LOSS')
                if total_xg < 2.0 and total_goals > 2:
                    return ('LUCKY', 'FALSE_ALPHA',
                            f'xG={total_xg:.1f} inférieur aux buts. Surperformance.',
                            'MONITOR')
            
            # PURE_ALPHA: CLV battu + gagné
            if clv_diff > 0.05:
                return ('SKILL', 'PURE_ALPHA',
                        f'Gagné + CLV battu de {clv_diff*100:.1f}%. Setup parfait.',
                        'DO_NOTHING')
            
            # Normal win
            return ('SKILL', 'NORMAL_WIN',
                    'Victoire alignée avec les xG. Continuer.',
                    'DO_NOTHING')
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # ANALYSE DES PARIS PERDANTS
        # ═══════════════════════════════════════════════════════════════════════════════
        else:
            # ───────────────────────────────────────────────────────────────────────────
            # UNLUCKY: Le process était bon
            # ───────────────────────────────────────────────────────────────────────────
            
            # FINISHING_NOISE: xG élevé mais pas de buts
            if market == 'over_25':
                if total_xg >= 3.0 and total_goals <= 2:
                    return ('UNLUCKY', 'FINISHING_NOISE',
                            f'xG={total_xg:.1f} mais seulement {total_goals} buts. Variance pure.',
                            'DO_NOTHING')
                if total_xg >= 2.5 and total_goals <= 2:
                    return ('UNLUCKY', 'FINISHING_NOISE',
                            f'xG={total_xg:.1f} proche du seuil. {total_bc_missed} big chances ratées.',
                            'DO_NOTHING')
            
            if market == 'btts_yes':
                if home_xg >= 1.0 and away_xg >= 1.0:
                    return ('UNLUCKY', 'FINISHING_NOISE',
                            f'Les deux auraient dû marquer (xG: {home_xg:.1f} vs {away_xg:.1f}). Malchance.',
                            'DO_NOTHING')
            
            # KEEPER_ALPHA: Gardien surperformant
            # (Détecté via big chances missed élevé + xG élevé)
            if total_bc_missed >= 4 and total_xg >= 2.0:
                return ('UNLUCKY', 'KEEPER_ALPHA',
                        f'{total_bc_missed} grosses occasions manquées. Gardien en feu.',
                        'IGNORE_DEFENSE')
            
            # GAME_STATE_SHOCK: Carton rouge précoce
            if red_card_minute and red_card_minute < 30:
                return ('UNLUCKY', 'GAME_STATE_SHOCK',
                        f'Carton rouge à la {red_card_minute}e minute. Match dénaturé.',
                        'EXCLUDE_FROM_DATA')
            
            # ───────────────────────────────────────────────────────────────────────────
            # BAD_CALL: Le modèle s'est trompé
            # ───────────────────────────────────────────────────────────────────────────
            
            # TACTICAL_MISMATCH: Match fermé non détecté
            if market == 'over_25' and total_xg < 1.5:
                return ('BAD_CALL', 'TACTICAL_MISMATCH',
                        f'Match très fermé (xG={total_xg:.1f}). Notre modèle n\'a pas détecté.',
                        'ADJUST_WEIGHTS')
            
            if market == 'btts_yes':
                if home_xg < 0.5 or away_xg < 0.5:
                    weak_team = 'home' if home_xg < away_xg else 'away'
                    return ('BAD_CALL', 'TACTICAL_MISMATCH',
                            f'Équipe {weak_team} n\'a rien créé (xG={home_xg:.1f} vs {away_xg:.1f}).',
                            'ADJUST_WEIGHTS')
            
            # MARKET_EFFICIENCY: CLV négatif
            if clv_diff < -0.05:
                return ('BAD_CALL', 'MARKET_EFFICIENCY',
                        f'CLV négatif ({clv_diff*100:.1f}%). Le marché savait quelque chose.',
                        'ADD_CLV_FILTER')
            
            # FAKE_DOMINANCE: RTI élevé mais xG faible
            if total_rti > 30 and total_xg < 2.0:
                return ('BAD_CALL', 'FAKE_DOMINANCE',
                        f'RTI={total_rti:.0f} élevé mais xG={total_xg:.1f} faible. Possession stérile.',
                        'INCREASE_EFFICIENCY_THRESHOLD')
            
            # ───────────────────────────────────────────────────────────────────────────
            # VARIANCE: Zone grise
            # ───────────────────────────────────────────────────────────────────────────
            return ('VARIANCE', 'NORMAL_LOSS',
                    f'xG={total_xg:.1f} dans la zone grise. Variance attendue.',
                    'DO_NOTHING')


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 5: EMA TIME DECAY
# ═══════════════════════════════════════════════════════════════════════════════════════════

class TimeDecayCalculator:
    """
    Calcule les moyennes avec Time Decay (EMA)
    Les 5 derniers matchs = 50% du poids total
    """
    
    @staticmethod
    def calculate_ema(values, span=5):
        """
        Calcule la Moyenne Mobile Exponentielle (EMA)
        
        Args:
            values: liste de valeurs (plus récent en dernier)
            span: nombre de périodes pour 50% du poids
            
        Returns:
            EMA value
        """
        if not values:
            return 0
        
        # Alpha = 2 / (span + 1)
        alpha = 2 / (span + 1)
        
        ema = values[0]
        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema
        
        return round(ema, 3)
    
    @staticmethod
    def calculate_team_form(team_name, n_matches=10):
        """
        Calcule la forme récente d'une équipe avec EMA
        
        Returns:
            dict avec xG_for_ema, xG_against_ema, performance_ema
        """
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer les N derniers matchs
        cur.execute("""
            SELECT 
                CASE WHEN home_team ILIKE %s THEN home_xg ELSE away_xg END as xg_for,
                CASE WHEN home_team ILIKE %s THEN away_xg ELSE home_xg END as xg_against,
                CASE WHEN home_team ILIKE %s THEN home_goals ELSE away_goals END as goals_for,
                CASE WHEN home_team ILIKE %s THEN away_goals ELSE home_goals END as goals_against,
                match_date
            FROM match_xg_stats
            WHERE home_team ILIKE %s OR away_team ILIKE %s
            ORDER BY match_date DESC
            LIMIT %s
        """, (f'%{team_name}%',) * 6 + (n_matches,))
        
        matches = cur.fetchall()
        conn.close()
        
        if not matches:
            return {'xg_for_ema': 1.0, 'xg_against_ema': 1.0, 'performance_ema': 0}
        
        # Inverser pour avoir le plus ancien en premier
        matches = list(reversed(matches))
        
        xg_for_values = [float(m['xg_for'] or 1.0) for m in matches]
        xg_against_values = [float(m['xg_against'] or 1.0) for m in matches]
        performance_values = [float(m['goals_for'] or 0) - float(m['xg_for'] or 0) for m in matches]
        
        return {
            'xg_for_ema': TimeDecayCalculator.calculate_ema(xg_for_values),
            'xg_against_ema': TimeDecayCalculator.calculate_ema(xg_against_values),
            'performance_ema': TimeDecayCalculator.calculate_ema(performance_values),
            'matches_analyzed': len(matches),
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 6: ANALYSEUR POST-MATCH COMPLET
# ═══════════════════════════════════════════════════════════════════════════════════════════

class PostMatchAnalyzer:
    """Analyse post-match complète avec toutes les métriques V2.0"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
    
    def analyze_match(self, home_team, away_team, match_date=None, our_prediction=None, our_odds=None):
        """
        Analyse complète d'un match post-factum
        
        Returns:
            dict avec toutes les métriques et classifications
        """
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Récupérer les données xG
        cur.execute("""
            SELECT * FROM match_xg_stats
            WHERE (home_team ILIKE %s OR home_team ILIKE %s)
              AND (away_team ILIKE %s OR away_team ILIKE %s)
            ORDER BY match_date DESC
            LIMIT 1
        """, (f'%{home_team}%', home_team, f'%{away_team}%', away_team))
        xg_stats = cur.fetchone()
        
        # 2. Récupérer les stats avancées
        cur.execute("""
            SELECT * FROM match_advanced_stats
            WHERE (home_team ILIKE %s OR home_team ILIKE %s)
              AND (away_team ILIKE %s OR away_team ILIKE %s)
            ORDER BY match_date DESC
            LIMIT 1
        """, (f'%{home_team}%', home_team, f'%{away_team}%', away_team))
        adv_stats = cur.fetchone()
        
        if not xg_stats:
            return {'error': 'Match non trouvé dans match_xg_stats'}
        
        # 3. Combiner les stats
        combined_stats = dict(xg_stats)
        if adv_stats:
            combined_stats.update(adv_stats)
        
        # 4. Calculer les métriques composites
        composite = CompositeMetrics.calculate_all(combined_stats)
        combined_stats.update(composite)
        
        # 5. Calculer total_goals si pas présent
        home_goals = int(xg_stats.get('home_goals') or 0)
        away_goals = int(xg_stats.get('away_goals') or 0)
        combined_stats['total_goals'] = home_goals + away_goals
        
        # 6. Déterminer si notre bet a gagné (si prédiction fournie)
        is_won = None
        if our_prediction:
            if our_prediction == 'over_25':
                is_won = combined_stats['total_goals'] > 2.5
            elif our_prediction == 'btts_yes':
                is_won = home_goals > 0 and away_goals > 0
            elif our_prediction == 'btts_no':
                is_won = home_goals == 0 or away_goals == 0
            elif our_prediction == 'under_25':
                is_won = combined_stats['total_goals'] < 2.5
        
        # 7. Classification 7 nuances
        bet_result = {'is_won': is_won, 'odds': our_odds or 1.85}
        category, sub_category, reason, action = QuantClassifier.classify(
            bet_result, combined_stats, our_prediction or 'over_25'
        )
        
        # 8. Forme récente (EMA)
        home_form = TimeDecayCalculator.calculate_team_form(home_team)
        away_form = TimeDecayCalculator.calculate_team_form(away_team)
        
        return {
            'match': f"{xg_stats['home_team']} vs {xg_stats['away_team']}",
            'date': str(xg_stats.get('match_date', 'N/A')),
            'score': f"{home_goals}-{away_goals}",
            'league': xg_stats.get('league', 'Unknown'),
            
            # xG
            'home_xg': float(xg_stats.get('home_xg') or 0),
            'away_xg': float(xg_stats.get('away_xg') or 0),
            'total_xg': float(xg_stats.get('total_xg') or 0),
            'match_profile': xg_stats.get('match_profile', 'Unknown'),
            
            # Stats avancées
            'total_shots': (adv_stats.get('home_shots') or 0) + (adv_stats.get('away_shots') or 0) if adv_stats else 'N/A',
            'total_big_chances': adv_stats.get('total_big_chances') if adv_stats else 'N/A',
            'match_intensity': adv_stats.get('match_intensity') if adv_stats else 'N/A',
            
            # Métriques composites
            'home_rti': composite['home_rti'],
            'away_rti': composite['away_rti'],
            'home_lethality': composite['home_lethality'],
            'away_lethality': composite['away_lethality'],
            
            # Classification
            'our_prediction': our_prediction,
            'prediction_correct': is_won,
            'category': category,
            'sub_category': sub_category,
            'reason': reason,
            'action_required': action,
            
            # Forme récente
            'home_form': home_form,
            'away_form': away_form,
        }
    
    def analyze_our_bets(self, days=30):
        """
        Analyse tous nos bets des N derniers jours
        """
        # Liste des faux positifs identifiés
        false_positives = [
            ("Arsenal FC", "Brentford FC", "over_25"),
            ("Manchester City FC", "Bayer 04 Leverkusen", "over_25"),
            ("Bayer 04 Leverkusen", "1. FC Heidenheim", "btts_yes"),
            ("Rayo Vallecano", "Real Madrid CF", "btts_yes"),
            ("Liverpool FC", "Real Madrid CF", "over_25"),
            ("West Ham United FC", "Liverpool FC", "btts_yes"),
            ("Olympique de Marseille", "Atalanta BC", "over_25"),
            ("Sport Lisboa e Benfica", "Bayer 04 Leverkusen", "over_25"),
        ]
        
        print("=" * 90)
        print("    ANALYSE POST-MATCH V2.0 - FAUX POSITIFS")
        print("=" * 90)
        
        categories_count = defaultdict(int)
        
        for home, away, market in false_positives:
            result = self.analyze_match(home, away, our_prediction=market)
            
            if 'error' in result:
                print(f"\n❌ {home} vs {away}: {result['error']}")
                continue
            
            print(f"\n{'─' * 90}")
            print(f"⚽ {result['match']} ({result['score']})")
            print(f"   📅 {result['date']} | 🏆 {result['league']}")
            print(f"{'─' * 90}")
            
            print(f"\n   📊 xG: {result['home_xg']:.2f} vs {result['away_xg']:.2f} = {result['total_xg']:.2f}")
            print(f"   📈 Profile: {result['match_profile']} | Intensity: {result['match_intensity']}")
            print(f"   🎯 RTI: Home={result['home_rti']:.1f} | Away={result['away_rti']:.1f}")
            print(f"   ⚔️ Lethality: Home={result['home_lethality']:.3f} | Away={result['away_lethality']:.3f}")
            
            # Classification
            cat_emoji = {
                'UNLUCKY': '🍀',
                'BAD_CALL': '❌',
                'LUCKY': '🎰',
                'VARIANCE': '📊',
                'SKILL': '✅'
            }
            
            print(f"\n   {cat_emoji.get(result['category'], '❓')} CATÉGORIE: {result['category']} / {result['sub_category']}")
            print(f"   💡 {result['reason']}")
            print(f"   🔧 Action: {result['action_required']}")
            
            categories_count[result['sub_category']] += 1
        
        # Résumé
        print(f"\n{'=' * 90}")
        print("    📊 RÉSUMÉ DES CATÉGORIES")
        print("=" * 90)
        
        for cat, count in sorted(categories_count.items(), key=lambda x: -x[1]):
            print(f"   {cat}: {count}")
        
        return categories_count


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 7: KPIs QUANT
# ═══════════════════════════════════════════════════════════════════════════════════════════

class QuantKPIs:
    """Calcule les KPIs Quant avancés"""
    
    @staticmethod
    def calculate_clv(odds_taken, closing_odds):
        """
        CLV (Closing Line Value) - Le seul indicateur prédictif de profit futur
        
        CLV% = (Closing Odds - Odds Taken) / Odds Taken × 100
        
        Positif = On a battu le marché
        Négatif = Le marché était plus smart que nous
        """
        if odds_taken <= 0:
            return 0
        return ((closing_odds - odds_taken) / odds_taken) * 100
    
    @staticmethod
    def calculate_xroi(bets):
        """
        xROI (Expected ROI basé sur xG)
        
        Si xROI > ROI Réel : On est en drawdown (pas de chance), ça va remonter
        Si xROI < ROI Réel : On est en sur-régime (chance), prépare-toi à perdre
        """
        if not bets:
            return 0
        
        expected_returns = 0
        total_staked = 0
        
        for bet in bets:
            stake = bet.get('stake', 1)
            odds = bet.get('odds', 1.85)
            xg_prob = bet.get('xg_probability', 0.5)  # Probabilité basée sur xG
            
            # Expected value = (prob × payout) - stake
            expected_return = (xg_prob * odds * stake) - stake
            expected_returns += expected_return
            total_staked += stake
        
        if total_staked == 0:
            return 0
        return (expected_returns / total_staked) * 100
    
    @staticmethod
    def calculate_noise_signal_ratio(classifications):
        """
        Ratio Noise/Signal
        
        Noise = FINISHING_NOISE + KEEPER_ALPHA + GAME_STATE_SHOCK (pas notre faute)
        Signal = TACTICAL_MISMATCH + MARKET_EFFICIENCY + FAKE_DOMINANCE (erreur modèle)
        
        Objectif: Maximiser Noise, minimiser Signal
        """
        noise_categories = ['FINISHING_NOISE', 'KEEPER_ALPHA', 'GAME_STATE_SHOCK']
        signal_categories = ['TACTICAL_MISMATCH', 'MARKET_EFFICIENCY', 'FAKE_DOMINANCE']
        
        noise_count = sum(1 for c in classifications if c in noise_categories)
        signal_count = sum(1 for c in classifications if c in signal_categories)
        
        if signal_count == 0:
            return float('inf')  # Parfait!
        
        return noise_count / signal_count


# ═══════════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 90)
    print("    QUANT SYSTEM V2.0 - ANALYSE POST-MATCH PROFESSIONNELLE")
    print("=" * 90)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # Analyser les faux positifs
    analyzer = PostMatchAnalyzer()
    categories = analyzer.analyze_our_bets()
    
    # Calculer le Noise/Signal ratio
    all_categories = list(categories.keys())
    ns_ratio = QuantKPIs.calculate_noise_signal_ratio(all_categories)
    
    print(f"\n   📈 Ratio Noise/Signal: {ns_ratio:.2f}")
    if ns_ratio > 1:
        print("   ✅ Plus de malchance que d'erreurs - Continuer la stratégie")
    else:
        print("   ⚠️ Plus d'erreurs que de malchance - Réviser le modèle")
    
    print("\n" + "=" * 90)

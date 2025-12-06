#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 UNDERSTAT DEEP MINER - HEDGE FUND GRADE METRICS                                                        ║
║                                                                                                               ║
║  Extrait TOUTES les métriques avancées:                                                                       ║
║  - statisticsData: gameState, attackSpeed, timing, situation, formation                                       ║
║  - playersData: xGChain, xGBuildup, dependency                                                                ║
║  - shotsData (par match): keeper_overperf, territorial_dominance, diesel_factor                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import re
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
from datetime import datetime

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Mapping équipes (réutilisé)
TEAM_MAPPING = {
    "Manchester City": "Manchester_City", "Manchester United": "Manchester_United",
    "Arsenal": "Arsenal", "Liverpool": "Liverpool", "Chelsea": "Chelsea",
    "Tottenham": "Tottenham", "Newcastle United": "Newcastle_United",
    "Brighton": "Brighton", "Aston Villa": "Aston_Villa", "West Ham": "West_Ham",
    "Brentford": "Brentford", "Fulham": "Fulham", "Crystal Palace": "Crystal_Palace",
    "Wolverhampton Wanderers": "Wolverhampton_Wanderers", "Everton": "Everton",
    "Nottingham Forest": "Nottingham_Forest", "Bournemouth": "Bournemouth",
    "Leicester": "Leicester", "Leeds": "Leeds", "Southampton": "Southampton",
    "Ipswich": "Ipswich", "Burnley": "Burnley",
    "Barcelona": "Barcelona", "Real Madrid": "Real_Madrid",
    "Atletico Madrid": "Atletico_Madrid", "Athletic Club": "Athletic_Club",
    "Real Sociedad": "Real_Sociedad", "Real Betis": "Real_Betis",
    "Villarreal": "Villarreal", "Sevilla": "Sevilla", "Valencia": "Valencia",
    "Girona": "Girona", "Getafe": "Getafe", "Osasuna": "Osasuna",
    "Celta Vigo": "Celta_Vigo", "Mallorca": "Mallorca", "Rayo Vallecano": "Rayo_Vallecano",
    "Alaves": "Alaves", "Espanyol": "Espanyol", "Real Oviedo": "Real_Oviedo",
    "Inter": "Inter", "AC Milan": "AC_Milan", "Juventus": "Juventus",
    "Napoli": "Napoli", "Lazio": "Lazio", "Roma": "Roma", "Atalanta": "Atalanta",
    "Fiorentina": "Fiorentina", "Bologna": "Bologna", "Torino": "Torino",
    "Udinese": "Udinese", "Cagliari": "Cagliari", "Verona": "Verona",
    "Lecce": "Lecce", "Genoa": "Genoa", "Como": "Como", "Parma Calcio 1913": "Parma",
    "Bayern Munich": "Bayern_Munich", "Borussia Dortmund": "Borussia_Dortmund",
    "RasenBallsport Leipzig": "RasenBallsport_Leipzig", "Bayer Leverkusen": "Bayer_Leverkusen",
    "Eintracht Frankfurt": "Eintracht_Frankfurt", "Wolfsburg": "Wolfsburg",
    "Borussia M.Gladbach": "Borussia_M.Gladbach", "Freiburg": "Freiburg",
    "Hoffenheim": "Hoffenheim", "FC Cologne": "FC_Cologne", "Mainz 05": "Mainz_05",
    "Augsburg": "Augsburg", "Union Berlin": "Union_Berlin", "VfB Stuttgart": "VfB_Stuttgart",
    "Werder Bremen": "Werder_Bremen", "FC Heidenheim": "FC_Heidenheim", "St. Pauli": "St._Pauli",
    "Paris Saint Germain": "Paris_Saint_Germain", "Marseille": "Marseille",
    "Monaco": "Monaco", "Lyon": "Lyon", "Lille": "Lille", "Nice": "Nice",
    "Lens": "Lens", "Rennes": "Rennes", "Toulouse": "Toulouse",
    "Strasbourg": "Strasbourg", "Nantes": "Nantes", "Le Havre": "Le_Havre",
    "Brest": "Brest", "Metz": "Metz", "Auxerre": "Auxerre", "Angers": "Angers",
    "Paris FC": "Paris_FC", "Hamburger SV": "Hamburger_SV", "Sassuolo": "Sassuolo",
    "Elche": "Elche", "Lorient": "Lorient", "Pisa": "Pisa", "Levante": "Levante",
    "Cremonese": "Cremonese", "Sunderland": "Sunderland",
}

SEASON = "2025"  # Pour avoir plus de matchs


class UnderstatDeepMiner:
    """Scraper avancé Understat - toutes métriques"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.requests_count = 0
        
    def _get_json(self, url: str, var_name: str) -> Optional[dict]:
        """Extrait une variable JSON"""
        try:
            time.sleep(1.2)
            r = self.session.get(url, timeout=20)
            self.requests_count += 1
            
            if r.status_code != 200:
                return None
                
            pattern = re.compile(rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\)")
            match = pattern.search(r.text)
            
            if match:
                return json.loads(match.group(1).encode('utf-8').decode('unicode_escape'))
            return None
        except Exception as e:
            return None
            
    def mine_team_full(self, understat_name: str) -> Optional[Dict]:
        """Mine TOUTES les données d'une équipe"""
        url = f"https://understat.com/team/{understat_name}/{SEASON}"
        
        # 1. Récupérer les 3 variables principales
        dates_data = self._get_json(url, "datesData")
        stats_data = self._get_json(url, "statisticsData")
        players_data = self._get_json(url, "playersData")
        
        if not dates_data or not stats_data:
            return None
            
        result = {
            "psyche_dna": self._calc_psyche_dna(stats_data),
            "nemesis_dna": self._calc_nemesis_dna(stats_data),
            "temporal_dna": self._calc_temporal_dna(stats_data),
            "tactical_dna": self._calc_tactical_dna(stats_data),
            "roster_dna": self._calc_roster_dna(players_data) if players_data else {},
            "physical_dna": {},  # Sera rempli par l'analyse des matchs
        }
        
        # 2. Analyse des derniers matchs (shotsData) pour métriques avancées
        finished_matches = [m for m in dates_data if m.get('isResult')]
        if finished_matches:
            match_analysis = self._analyze_recent_matches(finished_matches[-10:], understat_name)
            result["physical_dna"] = match_analysis.get("physical", {})
            result["nemesis_dna"].update(match_analysis.get("nemesis_extra", {}))
            
        return result
        
    def _calc_psyche_dna(self, stats: dict) -> dict:
        """Calcule le vecteur psychologique depuis gameState"""
        game_state = stats.get('gameState', {})
        
        # Extraire performance par état
        def get_rate(state_key):
            state = game_state.get(state_key, {})
            xg = float(state.get('xG', 0))
            time_played = float(state.get('time', 1))
            return (xg / time_played) * 90 if time_played > 0 else 0
            
        rate_drawing = get_rate('Goal diff 0')
        rate_winning_1 = get_rate('Goal diff +1')
        rate_winning_big = get_rate('Goal diff > +1')
        rate_losing_1 = get_rate('Goal diff -1')
        rate_losing_big = get_rate('Goal diff < -1')
        
        # Killer Instinct: produit plus quand mène
        killer_instinct = rate_winning_1 / rate_drawing if rate_drawing > 0 else 1.0
        
        # Panic Factor: concède plus quand perd
        panic_factor = rate_losing_1 / rate_drawing if rate_drawing > 0 else 1.0
        
        # Comeback Mentality: produit quand mené
        comeback_rate = rate_losing_1
        
        # Lead Protection: baisse d'intensité quand mène gros
        protection_rate = rate_winning_big / rate_drawing if rate_drawing > 0 else 1.0
        
        return {
            "killer_instinct": round(killer_instinct, 2),  # >1.2 = tueur
            "panic_factor": round(panic_factor, 2),  # >1.3 = s'effondre
            "comeback_mentality": round(comeback_rate, 2),  # xG/90 quand mené
            "lead_protection": round(protection_rate, 2),  # <0.8 = relâche
            "drawing_performance": round(rate_drawing, 2),
            "profile": self._classify_mentality(killer_instinct, panic_factor)
        }
        
    def _classify_mentality(self, killer: float, panic: float) -> str:
        """Classifie le profil mental"""
        if killer > 1.2 and panic < 1.1:
            return "PREDATOR"  # Tue le match, solide sous pression
        elif killer > 1.0 and panic > 1.3:
            return "VOLATILE"  # Bon en attaque mais s'effondre
        elif killer < 0.8 and panic < 1.0:
            return "CONSERVATIVE"  # Se contente de gagner
        elif panic > 1.5:
            return "FRAGILE"  # S'effondre sous pression
        else:
            return "BALANCED"
            
    def _calc_nemesis_dna(self, stats: dict) -> dict:
        """Calcule le vecteur Némésis depuis attackSpeed"""
        attack_speed = stats.get('attackSpeed', {})
        
        # Extraire shots par vitesse
        def get_shots(speed):
            return int(attack_speed.get(speed, {}).get('shots', 0))
            
        fast = get_shots('Fast')
        standard = get_shots('Standard')
        normal = get_shots('Normal')
        slow = get_shots('Slow')
        total = fast + standard + normal + slow
        
        if total == 0:
            return {"verticality": 0, "patience": 0, "style": "UNKNOWN"}
            
        # Verticality Index (contre-attaque)
        verticality = (fast / total) * 100
        
        # Patience Index (possession)
        patience = (slow / total) * 100
        
        # Style dominant
        if verticality > 25:
            style = "COUNTER_ATTACK"
        elif patience > 30:
            style = "POSSESSION"
        elif verticality > 15 and patience > 15:
            style = "HYBRID"
        else:
            style = "DIRECT"
            
        return {
            "verticality": round(verticality, 1),
            "patience": round(patience, 1),
            "fast_shots": fast,
            "slow_shots": slow,
            "style": style,
            "counter_nemesis": "HIGH_LINE" if verticality > 20 else "LOW_BLOCK" if patience > 25 else "BALANCED"
        }
        
    def _calc_temporal_dna(self, stats: dict) -> dict:
        """Calcule le vecteur temporel depuis timing"""
        timing = stats.get('timing', {})
        
        periods = {}
        total_xg = 0
        total_goals = 0
        
        for period, data in timing.items():
            xg = float(data.get('xG', 0))
            goals = int(data.get('goals', 0))
            shots = int(data.get('shots', 0))
            
            periods[period] = {
                "xg": round(xg, 2),
                "goals": goals,
                "shots": shots,
                "conversion": round(goals/shots*100, 1) if shots > 0 else 0
            }
            total_xg += xg
            total_goals += goals
            
        # Calculer les pourcentages par mi-temps
        first_half = ['1-15', '16-30', '31-45']
        second_half = ['46-60', '61-75', '76-90']
        
        xg_1h = sum(periods.get(p, {}).get('xg', 0) for p in first_half)
        xg_2h = sum(periods.get(p, {}).get('xg', 0) for p in second_half)
        
        goals_1h = sum(periods.get(p, {}).get('goals', 0) for p in first_half)
        goals_2h = sum(periods.get(p, {}).get('goals', 0) for p in second_half)
        
        late_xg = periods.get('76-90', {}).get('xg', 0)
        early_xg = periods.get('1-15', {}).get('xg', 0)
        
        # Diesel Factor: plus fort en 2MT
        diesel_factor = xg_2h / (xg_1h + xg_2h) if (xg_1h + xg_2h) > 0 else 0.5
        
        # Fast Starter: fort en début de match
        fast_starter = early_xg / total_xg if total_xg > 0 else 0
        
        # Late Game Threat
        late_threat = late_xg / total_xg if total_xg > 0 else 0
        
        return {
            "periods": periods,
            "first_half_xg_pct": round(xg_1h / total_xg * 100, 1) if total_xg > 0 else 0,
            "second_half_xg_pct": round(xg_2h / total_xg * 100, 1) if total_xg > 0 else 0,
            "diesel_factor": round(diesel_factor, 2),  # >0.55 = fort en fin
            "fast_starter": round(fast_starter, 2),  # >0.20 = démarre fort
            "late_game_threat": round(late_threat, 2),  # >0.20 = dangereux fin de match
            "profile": "DIESEL" if diesel_factor > 0.55 else "SPRINTER" if fast_starter > 0.22 else "CONSISTENT"
        }
        
    def _calc_tactical_dna(self, stats: dict) -> dict:
        """Calcule le vecteur tactique depuis situation et formation"""
        situation = stats.get('situation', {})
        formation = stats.get('formation', {})
        shot_zone = stats.get('shotZone', {})
        
        # Analyse des situations
        open_play = situation.get('OpenPlay', {})
        set_piece = situation.get('SetPiece', {})
        corner = situation.get('FromCorner', {})
        penalty = situation.get('Penalty', {})
        
        total_xg = sum(float(s.get('xG', 0)) for s in situation.values())
        
        open_play_pct = float(open_play.get('xG', 0)) / total_xg * 100 if total_xg > 0 else 0
        set_piece_pct = (float(set_piece.get('xG', 0)) + float(corner.get('xG', 0))) / total_xg * 100 if total_xg > 0 else 0
        
        # Formation préférée
        formations_used = sorted(formation.items(), key=lambda x: int(x[1].get('time', 0)), reverse=True)
        main_formation = formations_used[0][0] if formations_used else "Unknown"
        formation_stability = int(formations_used[0][1].get('time', 0)) / sum(int(f[1].get('time', 1)) for f in formations_used) if formations_used else 0
        
        # Shot zones
        box_shots = int(shot_zone.get('shotPenaltyArea', {}).get('shots', 0))
        six_yard = int(shot_zone.get('shotSixYardBox', {}).get('shots', 0))
        outside_box = int(shot_zone.get('shotOboxTotal', {}).get('shots', 0))
        total_shots = box_shots + six_yard + outside_box
        
        box_ratio = (box_shots + six_yard) / total_shots if total_shots > 0 else 0
        
        return {
            "main_formation": main_formation,
            "formation_stability": round(formation_stability, 2),  # >0.8 = tactiquement stable
            "open_play_reliance": round(open_play_pct, 1),
            "set_piece_threat": round(set_piece_pct, 1),
            "box_shot_ratio": round(box_ratio, 2),  # >0.7 = crée dans la surface
            "long_range_threat": round((1 - box_ratio) * 100, 1),
            "tactical_profile": "SET_PIECE_SPECIALIST" if set_piece_pct > 25 else "OPEN_PLAY" if open_play_pct > 75 else "MIXED"
        }
        
    def _calc_roster_dna(self, players: list) -> dict:
        """Calcule le vecteur effectif depuis playersData"""
        if not players:
            return {}
            
        # Trier par xGChain (contribution totale)
        sorted_players = sorted(players, key=lambda x: float(x.get('xGChain', 0)), reverse=True)
        
        total_xg = sum(float(p.get('xG', 0)) for p in players)
        total_xg_chain = sum(float(p.get('xGChain', 0)) for p in players)
        
        # MVP (plus haute xGChain)
        mvp = sorted_players[0] if sorted_players else None
        
        # Top 3 dependency
        top3_chain = sum(float(p.get('xGChain', 0)) for p in sorted_players[:3])
        
        # Playmaker (haut xGBuildup, bas xG)
        playmakers = [p for p in players if float(p.get('xGBuildup', 0)) > float(p.get('xG', 0)) * 0.5]
        playmakers = sorted(playmakers, key=lambda x: float(x.get('xGBuildup', 0)), reverse=True)
        
        # Clinical finisher (goals > xG)
        clinical = [p for p in players if int(p.get('goals', 0)) > float(p.get('xG', 0))]
        
        result = {
            "squad_size_analyzed": len(players),
            "total_team_xg": round(total_xg, 2),
        }
        
        if mvp:
            mvp_chain = float(mvp.get('xGChain', 0))
            result["mvp"] = {
                "name": mvp.get('player_name', 'Unknown'),
                "xg_chain": round(mvp_chain, 2),
                "dependency_score": round(mvp_chain / total_xg_chain * 100, 1) if total_xg_chain > 0 else 0,
            }
            result["mvp_missing_impact"] = "CRITICAL" if result["mvp"]["dependency_score"] > 35 else "HIGH" if result["mvp"]["dependency_score"] > 25 else "MODERATE"
            
        result["top3_dependency"] = round(top3_chain / total_xg_chain * 100, 1) if total_xg_chain > 0 else 0
        
        if playmakers:
            result["key_playmaker"] = {
                "name": playmakers[0].get('player_name', 'Unknown'),
                "xg_buildup": round(float(playmakers[0].get('xGBuildup', 0)), 2)
            }
            
        result["clinical_finishers"] = len(clinical)
        
        return result
        
    def _analyze_recent_matches(self, matches: list, understat_name: str) -> dict:
        """Analyse les derniers matchs pour métriques physiques"""
        keeper_perf = []
        dominance = []
        late_xg = []
        
        understat_clean = understat_name.replace('_', ' ').lower()
        
        for match in matches[-8:]:  # 8 derniers matchs max
            match_id = match['id']
            
            # Déterminer si home ou away
            is_home = understat_clean in match['h'].get('title', '').lower()
            side = 'h' if is_home else 'a'
            opp_side = 'a' if is_home else 'h'
            
            # Récupérer shotsData
            shots_data = self._get_json(f"https://understat.com/match/{match_id}", "shotsData")
            if not shots_data:
                continue
                
            my_shots = shots_data.get(side, [])
            opp_shots = shots_data.get(opp_side, [])
            
            # Keeper Performance (xG Against - Goals Against)
            xg_against = sum(float(s.get('xG', 0)) for s in opp_shots)
            goals_against = int(match['goals'][opp_side])
            keeper_perf.append(xg_against - goals_against)  # Positif = gardien sauve
            
            # Territorial Dominance (shots in box)
            my_box = sum(1 for s in my_shots if float(s.get('X', 0)) > 0.83)  # ~17 yards
            opp_box = sum(1 for s in opp_shots if float(s.get('X', 0)) > 0.83)
            total_box = my_box + opp_box
            if total_box > 0:
                dominance.append(my_box / total_box)
                
            # Late Game xG (75-90)
            late = sum(float(s.get('xG', 0)) for s in my_shots if int(s.get('minute', 0)) >= 75)
            late_xg.append(late)
            
            time.sleep(0.8)
            
        result = {
            "physical": {},
            "nemesis_extra": {}
        }
        
        if keeper_perf:
            avg_keeper = sum(keeper_perf) / len(keeper_perf)
            result["nemesis_extra"]["keeper_overperformance"] = round(avg_keeper, 2)
            result["nemesis_extra"]["keeper_status"] = "ON_FIRE" if avg_keeper > 0.3 else "SOLID" if avg_keeper > 0 else "LEAKY"
            
        if dominance:
            avg_dom = sum(dominance) / len(dominance)
            result["nemesis_extra"]["territorial_dominance"] = round(avg_dom, 2)
            result["nemesis_extra"]["territory_profile"] = "DOMINANT" if avg_dom > 0.55 else "CONTESTED" if avg_dom > 0.45 else "DEFENSIVE"
            
        if late_xg:
            avg_late = sum(late_xg) / len(late_xg)
            result["physical"]["late_game_xg_avg"] = round(avg_late, 2)
            result["physical"]["late_game_threat_level"] = "HIGH" if avg_late > 0.4 else "MEDIUM" if avg_late > 0.2 else "LOW"
            
        return result


class QuantumDeepEnricher:
    """Enrichit quantum_dna avec toutes les métriques avancées"""
    
    def __init__(self):
        self.conn = None
        self.miner = UnderstatDeepMiner()
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_teams(self, tiers: list = None) -> List[dict]:
        """Récupère les équipes à enrichir"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            if tiers:
                cur.execute("""
                    SELECT id, team_name, tier, total_pnl
                    FROM quantum.team_profiles
                    WHERE tier = ANY(%s)
                    ORDER BY total_pnl DESC
                """, (tiers,))
            else:
                cur.execute("""
                    SELECT id, team_name, tier, total_pnl
                    FROM quantum.team_profiles
                    ORDER BY total_pnl DESC
                """)
            return cur.fetchall()
            
    def enrich_team(self, team: dict) -> bool:
        """Enrichit une équipe avec métriques profondes"""
        team_name = team['team_name']
        
        if team_name not in TEAM_MAPPING:
            return False
            
        understat_name = TEAM_MAPPING[team_name]
        deep_data = self.miner.mine_team_full(understat_name)
        
        if not deep_data:
            return False
            
        # Mettre à jour quantum_dna avec les nouveaux vecteurs
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE quantum.team_profiles
                SET quantum_dna = quantum_dna || %s::jsonb,
                    updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(deep_data), team['id']))
            
        self.conn.commit()
        return True
        
    def run(self, tiers: list = None, max_teams: int = 50):
        """Lance l'enrichissement"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 UNDERSTAT DEEP MINER - HEDGE FUND METRICS                                                              ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self.connect()
        teams = self.get_teams(tiers)[:max_teams]
        print(f"✅ {len(teams)} équipes à miner en profondeur\n")
        
        success = 0
        for i, team in enumerate(teams):
            print(f"   [{i+1}/{len(teams)}] ⛏️ {team['team_name']}...", end=" ", flush=True)
            
            if self.enrich_team(team):
                success += 1
                print("✅")
            else:
                print("❌")
                
            time.sleep(1)
            
        print(f"""
{'='*80}
📊 RÉSUMÉ DEEP MINING
{'='*80}
   ✅ Équipes enrichies: {success}/{len(teams)}
   📡 Requêtes totales: {self.miner.requests_count}
   
   Vecteurs ajoutés:
   - psyche_dna (killer_instinct, panic_factor, mentality)
   - nemesis_dna (verticality, keeper_overperf, dominance)
   - temporal_dna (diesel_factor, late_threat, periods)
   - tactical_dna (formation, set_piece, box_ratio)
   - roster_dna (mvp_dependency, playmaker, clinical)
   - physical_dna (late_game_threat)
{'='*80}
        """)
        
        self.close()


if __name__ == "__main__":
    enricher = QuantumDeepEnricher()
    # Commencer par ELITE et GOLD pour tester
    enricher.run(tiers=['ELITE', 'GOLD'], max_teams=25)

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V5.6 PHASE 4.2 - HEDGE FUND GRADE                     ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  NOUVELLE DIMENSION PHASE 4.2:                                               ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🌧️ WEATHER DNA (Météo):                                                    ║
║     • RAIN: Pluie (> 0.5mm/h)                                               ║
║     • COLD: Température < 10°C                                              ║
║     • HOT: Température > 25°C                                               ║
║     • DRY/NORMAL: Conditions standards                                       ║
║                                                                              ║
║  PROFILS NUANCÉS (Forces + Faiblesses):                                      ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • RAIN_ATTACKER: Marque +0.5 buts/match sous la pluie                      ║
║  • RAIN_LEAKY: Encaisse +0.5 buts/match sous la pluie                       ║
║  • COLD_RESILIENT: Performances stables par temps froid                      ║
║  • COLD_VULNERABLE: Performances -0.5 par temps froid                        ║
║  • HEAT_DIESEL: Monte en puissance quand adversaires fatiguent               ║
║  • HEAT_WEAK: Performances dégradées par chaleur                            ║
║                                                                              ║
║  API: Open-Meteo (gratuite, pas de clé requise)                             ║
║  HÉRITE DE: loader_v5_5_phase4.py (Phase 1 + 2 + 3 + 4.1)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import json
import urllib.request
import ssl
import time

import sys
sys.path.insert(0, '/home/Mon_ps')

from agents.attack_v1.data.loader_v5_5_phase4 import (
    AttackDataLoaderV55Phase4,
    ExternalFactorsDNA
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# WEATHER DNA - CONDITIONS MÉTÉO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MatchWeather:
    """Météo d'un match"""
    match_id: int = 0
    date: str = ""
    home_team: str = ""
    away_team: str = ""
    
    # Coordonnées du stade
    stadium: str = ""
    lat: float = 0.0
    lon: float = 0.0
    
    # Données météo
    temperature: float = 0.0       # °C
    rain: float = 0.0              # mm/h
    wind_speed: float = 0.0        # km/h
    weather_code: int = 0          # WMO code
    
    # Catégories
    is_rainy: bool = False         # rain > 0.5mm/h
    is_cold: bool = False          # temp < 10°C
    is_hot: bool = False           # temp > 25°C
    is_windy: bool = False         # wind > 30 km/h
    
    # Résultat
    home_goals: int = 0
    away_goals: int = 0


@dataclass
class WeatherDNA:
    """
    ADN Météo d'une équipe - UNIQUE par équipe
    
    Analyse la performance selon les conditions météo:
    • Sous la pluie vs temps sec
    • Par temps froid vs tempéré
    • Par temps chaud vs normal
    
    Profils NUANCÉS:
    • RAIN_ATTACKER: Marque plus sous la pluie (+delta >= 0.5)
    • RAIN_LEAKY: Encaisse plus sous la pluie (+delta >= 0.5)
    • COLD_RESILIENT: Stable par temps froid (delta < 0.3)
    • COLD_VULNERABLE: Moins bon par temps froid (-delta >= 0.5)
    • HEAT_DIESEL: Meilleur par temps chaud (+delta >= 0.5)
    • HEAT_WEAK: Moins bon par temps chaud (-delta >= 0.5)
    """
    team: str = ""
    
    # Statistiques RAIN
    rain_matches: int = 0
    rain_goals_scored: int = 0
    rain_goals_conceded: int = 0
    rain_goals_avg: float = 0.0
    rain_conceded_avg: float = 0.0
    
    dry_matches: int = 0
    dry_goals_scored: int = 0
    dry_goals_conceded: int = 0
    dry_goals_avg: float = 0.0
    dry_conceded_avg: float = 0.0
    
    # Deltas RAIN
    rain_attack_delta: float = 0.0     # rain_goals_avg - dry_goals_avg
    rain_defense_delta: float = 0.0    # rain_conceded_avg - dry_conceded_avg
    
    # Statistiques COLD (<10°C)
    cold_matches: int = 0
    cold_goals_scored: int = 0
    cold_goals_conceded: int = 0
    cold_goals_avg: float = 0.0
    cold_conceded_avg: float = 0.0
    
    warm_matches: int = 0              # >= 10°C
    warm_goals_scored: int = 0
    warm_goals_conceded: int = 0
    warm_goals_avg: float = 0.0
    warm_conceded_avg: float = 0.0
    
    # Deltas COLD
    cold_attack_delta: float = 0.0
    cold_defense_delta: float = 0.0
    
    # Statistiques HOT (>25°C)
    hot_matches: int = 0
    hot_goals_scored: int = 0
    hot_goals_conceded: int = 0
    hot_goals_avg: float = 0.0
    hot_conceded_avg: float = 0.0
    
    normal_matches: int = 0            # 10-25°C
    normal_goals_scored: int = 0
    normal_goals_conceded: int = 0
    normal_goals_avg: float = 0.0
    normal_conceded_avg: float = 0.0
    
    # Deltas HOT
    hot_attack_delta: float = 0.0
    hot_defense_delta: float = 0.0
    
    # Profils (peuvent en avoir plusieurs)
    rain_attack_profile: str = ""      # RAIN_ATTACKER, RAIN_NEUTRAL, RAIN_WEAK
    rain_defense_profile: str = ""     # RAIN_SOLID, RAIN_NEUTRAL, RAIN_LEAKY
    cold_profile: str = ""             # COLD_RESILIENT, COLD_NEUTRAL, COLD_VULNERABLE
    hot_profile: str = ""              # HEAT_DIESEL, HEAT_NEUTRAL, HEAT_WEAK
    
    # Profil global
    weather_profile: str = ""          # Résumé
    
    # Edge betting
    best_weather_condition: str = ""
    worst_weather_condition: str = ""
    max_weather_edge: float = 0.0
    
    def calculate(self) -> None:
        """Calcule toutes les métriques et classifications"""
        
        # ═══════════════════════════════════════════════════════════════════════
        # RAIN ANALYSIS
        # ═══════════════════════════════════════════════════════════════════════
        if self.rain_matches > 0:
            self.rain_goals_avg = self.rain_goals_scored / self.rain_matches
            self.rain_conceded_avg = self.rain_goals_conceded / self.rain_matches
            
        if self.dry_matches > 0:
            self.dry_goals_avg = self.dry_goals_scored / self.dry_matches
            self.dry_conceded_avg = self.dry_goals_conceded / self.dry_matches
            
        if self.rain_matches >= 2 and self.dry_matches >= 2:
            self.rain_attack_delta = self.rain_goals_avg - self.dry_goals_avg
            self.rain_defense_delta = self.rain_conceded_avg - self.dry_conceded_avg
            
            # Classification RAIN ATTACK
            if self.rain_attack_delta >= 0.5:
                self.rain_attack_profile = "RAIN_ATTACKER"
            elif self.rain_attack_delta <= -0.5:
                self.rain_attack_profile = "RAIN_WEAK"
            else:
                self.rain_attack_profile = "RAIN_NEUTRAL"
                
            # Classification RAIN DEFENSE
            if self.rain_defense_delta >= 0.5:
                self.rain_defense_profile = "RAIN_LEAKY"
            elif self.rain_defense_delta <= -0.3:
                self.rain_defense_profile = "RAIN_SOLID"
            else:
                self.rain_defense_profile = "RAIN_NEUTRAL"
        else:
            self.rain_attack_profile = "INSUFFICIENT_DATA"
            self.rain_defense_profile = "INSUFFICIENT_DATA"
            
        # ═══════════════════════════════════════════════════════════════════════
        # COLD ANALYSIS (<10°C)
        # ═══════════════════════════════════════════════════════════════════════
        if self.cold_matches > 0:
            self.cold_goals_avg = self.cold_goals_scored / self.cold_matches
            self.cold_conceded_avg = self.cold_goals_conceded / self.cold_matches
            
        if self.warm_matches > 0:
            self.warm_goals_avg = self.warm_goals_scored / self.warm_matches
            self.warm_conceded_avg = self.warm_goals_conceded / self.warm_matches
            
        if self.cold_matches >= 2 and self.warm_matches >= 2:
            self.cold_attack_delta = self.cold_goals_avg - self.warm_goals_avg
            self.cold_defense_delta = self.cold_conceded_avg - self.warm_conceded_avg
            
            # Classification COLD
            if self.cold_attack_delta >= 0.3:
                self.cold_profile = "COLD_SPECIALIST"
            elif self.cold_attack_delta <= -0.5:
                self.cold_profile = "COLD_VULNERABLE"
            elif abs(self.cold_attack_delta) < 0.3:
                self.cold_profile = "COLD_RESILIENT"
            else:
                self.cold_profile = "COLD_NEUTRAL"
        else:
            self.cold_profile = "INSUFFICIENT_DATA"
            
        # ═══════════════════════════════════════════════════════════════════════
        # HOT ANALYSIS (>25°C)
        # ═══════════════════════════════════════════════════════════════════════
        if self.hot_matches > 0:
            self.hot_goals_avg = self.hot_goals_scored / self.hot_matches
            self.hot_conceded_avg = self.hot_goals_conceded / self.hot_matches
            
        if self.normal_matches > 0:
            self.normal_goals_avg = self.normal_goals_scored / self.normal_matches
            self.normal_conceded_avg = self.normal_goals_conceded / self.normal_matches
            
        if self.hot_matches >= 2 and self.normal_matches >= 2:
            self.hot_attack_delta = self.hot_goals_avg - self.normal_goals_avg
            self.hot_defense_delta = self.hot_conceded_avg - self.normal_conceded_avg
            
            # Classification HOT
            if self.hot_attack_delta >= 0.5:
                self.hot_profile = "HEAT_DIESEL"
            elif self.hot_attack_delta <= -0.5:
                self.hot_profile = "HEAT_WEAK"
            else:
                self.hot_profile = "HEAT_NEUTRAL"
        else:
            self.hot_profile = "INSUFFICIENT_DATA"
            
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL GLOBAL + EDGE
        # ═══════════════════════════════════════════════════════════════════════
        self._build_global_profile()
        self._find_best_worst_conditions()
        
    def _build_global_profile(self) -> None:
        """Construit le profil global"""
        parts = []
        
        if self.rain_attack_profile == "RAIN_ATTACKER":
            parts.append(f"🌧️ Rain Attacker (+{self.rain_attack_delta:.2f})")
        elif self.rain_attack_profile == "RAIN_WEAK":
            parts.append(f"🌧️ Rain Weak ({self.rain_attack_delta:.2f})")
            
        if self.rain_defense_profile == "RAIN_LEAKY":
            parts.append(f"🌧️ Rain Leaky (+{self.rain_defense_delta:.2f})")
            
        if self.cold_profile == "COLD_SPECIALIST":
            parts.append(f"❄️ Cold Specialist (+{self.cold_attack_delta:.2f})")
        elif self.cold_profile == "COLD_VULNERABLE":
            parts.append(f"❄️ Cold Vulnerable ({self.cold_attack_delta:.2f})")
            
        if self.hot_profile == "HEAT_DIESEL":
            parts.append(f"🔥 Heat Diesel (+{self.hot_attack_delta:.2f})")
        elif self.hot_profile == "HEAT_WEAK":
            parts.append(f"🔥 Heat Weak ({self.hot_attack_delta:.2f})")
            
        self.weather_profile = " | ".join(parts) if parts else "WEATHER_NEUTRAL"
        
    def _find_best_worst_conditions(self) -> None:
        """Trouve les meilleures et pires conditions météo"""
        conditions = []
        
        if self.rain_attack_profile != "INSUFFICIENT_DATA":
            conditions.append(('RAIN', self.rain_attack_delta, self.rain_matches))
            conditions.append(('DRY', -self.rain_attack_delta, self.dry_matches))
            
        if self.cold_profile != "INSUFFICIENT_DATA":
            conditions.append(('COLD', self.cold_attack_delta, self.cold_matches))
            
        if self.hot_profile != "INSUFFICIENT_DATA":
            conditions.append(('HOT', self.hot_attack_delta, self.hot_matches))
            
        if conditions:
            # Filtrer ceux avec min 2 matchs
            valid_conditions = [c for c in conditions if c[2] >= 2]
            
            if valid_conditions:
                best = max(valid_conditions, key=lambda x: x[1])
                worst = min(valid_conditions, key=lambda x: x[1])
                
                self.best_weather_condition = best[0]
                self.worst_weather_condition = worst[0]
                self.max_weather_edge = best[1] - worst[1]


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V5.6 PHASE 4.2 - WEATHER DNA
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV56Phase42(AttackDataLoaderV55Phase4):
    """
    Loader V5.6 PHASE 4.2 - HEDGE FUND GRADE
    
    Hérite de V5.5 (Phase 1 + 2 + 3 + 4.1) et ajoute:
    • Weather DNA (météo)
    
    PHILOSOPHIE: Chaque équipe = ADN UNIQUE = Empreinte digitale
    """
    
    def __init__(self):
        super().__init__()
        
        # Phase 4.2 data
        self.stadium_coordinates: Dict = {}
        self.match_weather: Dict[int, MatchWeather] = {}
        self.weather_dna: Dict[str, WeatherDNA] = {}
        
        # Cache pour éviter les appels API répétés
        self.weather_cache_file = DATA_DIR / 'venues/weather_cache.json'
        self.weather_cache: Dict = {}
        
    def load_all(self) -> None:
        """Charge tout + Phase 4.2"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V5.6 PHASE 4.2 - HEDGE FUND GRADE")
        print("=" * 80)
        
        # Phase 1: V5.2 (NP-Clinical + xGChain)
        self._load_players_impact_dna()
        self._load_goals_timing_style()
        self._load_context_dna()
        self._aggregate_teams()
        self._calculate_all()
        
        # Phase 2: Creator-Finisher + Momentum
        print("\n" + "─" * 80)
        print("🚀 PHASE 2: CREATOR-FINISHER LINK + MOMENTUM DNA")
        print("─" * 80)
        self._build_creator_finisher_links()
        self._build_momentum_dna()
        
        # Phase 3: First Goal Impact + Game State
        print("\n" + "─" * 80)
        print("🚀 PHASE 3: FIRST GOAL IMPACT + GAME STATE DNA")
        print("─" * 80)
        self._reconstruct_matches()
        self._build_first_goal_impact_dna()
        self._build_game_state_dna()
        
        # Phase 4.1: External Factors (Horaires)
        print("\n" + "─" * 80)
        print("🚀 PHASE 4.1: EXTERNAL FACTORS DNA (HORAIRES)")
        print("─" * 80)
        self._build_external_factors_dna()
        
        # Phase 4.2: Weather DNA
        print("\n" + "─" * 80)
        print("🚀 PHASE 4.2: WEATHER DNA (MÉTÉO)")
        print("─" * 80)
        self._load_stadium_coordinates()
        self._load_weather_cache()
        self._fetch_match_weather()
        self._build_weather_dna()
        
        self._print_phase4_insights()
        self._print_weather_insights()
        
    def _load_stadium_coordinates(self) -> None:
        """Charge les coordonnées GPS des stades"""
        print("\n🏟️ [PHASE 4.2.1] Chargement coordonnées stades...")
        
        path = DATA_DIR / 'venues/stadium_coordinates.json'
        
        if not path.exists():
            print(f"   ⚠️ Fichier {path} non trouvé")
            return
            
        with open(path) as f:
            data = json.load(f)
            
        # Flatten: créer un dict team -> {stadium, lat, lon}
        for league, teams in data.items():
            if league.startswith('_'):
                continue
            for team, info in teams.items():
                self.stadium_coordinates[team] = {
                    'stadium': info.get('stadium', ''),
                    'city': info.get('city', ''),
                    'lat': info.get('lat', 0),
                    'lon': info.get('lon', 0),
                    'league': league
                }
                
        print(f"   ✅ {len(self.stadium_coordinates)} stades chargés")
        
    def _load_weather_cache(self) -> None:
        """Charge le cache météo"""
        if self.weather_cache_file.exists():
            with open(self.weather_cache_file) as f:
                self.weather_cache = json.load(f)
            print(f"   ✅ Cache météo chargé ({len(self.weather_cache)} entrées)")
        else:
            print(f"   ℹ️ Pas de cache météo existant")
            
    def _save_weather_cache(self) -> None:
        """Sauvegarde le cache météo"""
        self.weather_cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.weather_cache_file, 'w') as f:
            json.dump(self.weather_cache, f, indent=2)
            
    def _get_team_coordinates(self, team: str) -> Optional[Tuple[float, float]]:
        """Retourne les coordonnées (lat, lon) d'un stade d'équipe"""
        info = self.stadium_coordinates.get(team)
        if info and info.get('lat') and info.get('lon'):
            return (info['lat'], info['lon'])
        return None
        
    def _fetch_weather_from_api(self, lat: float, lon: float, date: str, hour: int) -> Optional[Dict]:
        """
        Récupère la météo via l'API Open-Meteo (gratuite)
        
        Args:
            lat: Latitude
            lon: Longitude
            date: Date au format YYYY-MM-DD
            hour: Heure du match (0-23)
            
        Returns:
            Dict avec temperature, rain, wind_speed, weather_code
        """
        cache_key = f"{lat:.2f}_{lon:.2f}_{date}_{hour}"
        
        if cache_key in self.weather_cache:
            return self.weather_cache[cache_key]
            
        try:
            # API Open-Meteo Archive (données historiques)
            url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={date}&end_date={date}&hourly=temperature_2m,rain,wind_speed_10m,weather_code"
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(url, timeout=10, context=ctx) as response:
                data = json.loads(response.read().decode())
                
            hourly = data.get('hourly', {})
            temps = hourly.get('temperature_2m', [])
            rains = hourly.get('rain', [])
            winds = hourly.get('wind_speed_10m', [])
            codes = hourly.get('weather_code', [])
            
            if temps and len(temps) > hour:
                result = {
                    'temperature': temps[hour] if temps[hour] is not None else 15.0,
                    'rain': rains[hour] if rains and len(rains) > hour and rains[hour] is not None else 0.0,
                    'wind_speed': winds[hour] if winds and len(winds) > hour and winds[hour] is not None else 0.0,
                    'weather_code': codes[hour] if codes and len(codes) > hour and codes[hour] is not None else 0
                }
                
                # Cache
                self.weather_cache[cache_key] = result
                return result
                
        except Exception as e:
            pass
            
        return None
        
    def _fetch_match_weather(self) -> None:
        """Récupère la météo pour tous les matchs"""
        print("\n🌤️ [PHASE 4.2.2] Récupération météo des matchs...")
        
        # Charger les matchs reconstruits
        matches_with_weather = 0
        matches_without_coords = 0
        api_calls = 0
        
        # reconstructed_matches est un dict {match_id: ReconstructedMatch}
        for match_id, match in self.reconstructed_matches.items():
            home_team = match.home_team
            
            # Obtenir les coordonnées du stade
            coords = self._get_team_coordinates(home_team)
            
            if not coords:
                matches_without_coords += 1
                continue
                
            lat, lon = coords
            
            # Parser la date
            try:
                # Format: 2025-08-15 19:00:00
                date_str = match.date if hasattr(match, 'date') else ''
                if not date_str:
                    continue
                    
                dt = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                date_only = dt.strftime("%Y-%m-%d")
                hour = dt.hour
                
            except:
                continue
                
            # Récupérer météo (cache ou API)
            weather = self._fetch_weather_from_api(lat, lon, date_only, hour)
            
            if weather:
                mw = MatchWeather(
                    match_id=match.match_id,
                    date=date_str,
                    home_team=match.home_team,
                    away_team=match.away_team,
                    stadium=self.stadium_coordinates.get(home_team, {}).get('stadium', ''),
                    lat=lat,
                    lon=lon,
                    temperature=weather['temperature'],
                    rain=weather['rain'],
                    wind_speed=weather['wind_speed'],
                    weather_code=weather['weather_code'],
                    is_rainy=weather['rain'] > 0.5,
                    is_cold=weather['temperature'] < 10,
                    is_hot=weather['temperature'] > 25,
                    is_windy=weather['wind_speed'] > 30,
                    home_goals=match.final_home,
                    away_goals=match.final_away
                )
                
                self.match_weather[match.match_id] = mw
                matches_with_weather += 1
                
                # Rate limiting (être gentil avec l'API gratuite)
                if matches_with_weather % 50 == 0:
                    time.sleep(1)
                    
        # Sauvegarder le cache
        self._save_weather_cache()
        
        print(f"   ✅ {matches_with_weather} matchs avec météo")
        print(f"   ⚠️ {matches_without_coords} matchs sans coordonnées stade")
        print(f"   📡 Cache météo: {len(self.weather_cache)} entrées")
        
        # Stats conditions
        rainy = sum(1 for m in self.match_weather.values() if m.is_rainy)
        cold = sum(1 for m in self.match_weather.values() if m.is_cold)
        hot = sum(1 for m in self.match_weather.values() if m.is_hot)
        
        print(f"\n   📊 CONDITIONS MÉTÉO:")
        print(f"      🌧️ Matchs sous la pluie: {rainy}")
        print(f"      ❄️ Matchs froid (<10°C): {cold}")
        print(f"      🔥 Matchs chaud (>25°C): {hot}")
        
    def _build_weather_dna(self) -> None:
        """Construit le Weather DNA pour chaque équipe"""
        print("\n🌧️ [PHASE 4.2.3] Construction Weather DNA...")
        
        # Collecter les stats par équipe
        team_weather_data = defaultdict(lambda: {
            'rain': {'goals': 0, 'conceded': 0, 'matches': 0},
            'dry': {'goals': 0, 'conceded': 0, 'matches': 0},
            'cold': {'goals': 0, 'conceded': 0, 'matches': 0},
            'warm': {'goals': 0, 'conceded': 0, 'matches': 0},
            'hot': {'goals': 0, 'conceded': 0, 'matches': 0},
            'normal': {'goals': 0, 'conceded': 0, 'matches': 0}
        })
        
        for mw in self.match_weather.values():
            # Home team
            home_data = team_weather_data[mw.home_team]
            
            # Rain/Dry
            if mw.is_rainy:
                home_data['rain']['goals'] += mw.home_goals
                home_data['rain']['conceded'] += mw.away_goals
                home_data['rain']['matches'] += 1
            else:
                home_data['dry']['goals'] += mw.home_goals
                home_data['dry']['conceded'] += mw.away_goals
                home_data['dry']['matches'] += 1
                
            # Cold/Warm
            if mw.is_cold:
                home_data['cold']['goals'] += mw.home_goals
                home_data['cold']['conceded'] += mw.away_goals
                home_data['cold']['matches'] += 1
            else:
                home_data['warm']['goals'] += mw.home_goals
                home_data['warm']['conceded'] += mw.away_goals
                home_data['warm']['matches'] += 1
                
            # Hot/Normal
            if mw.is_hot:
                home_data['hot']['goals'] += mw.home_goals
                home_data['hot']['conceded'] += mw.away_goals
                home_data['hot']['matches'] += 1
            elif not mw.is_cold:  # Normal = 10-25°C
                home_data['normal']['goals'] += mw.home_goals
                home_data['normal']['conceded'] += mw.away_goals
                home_data['normal']['matches'] += 1
                
            # Away team (même logique)
            away_data = team_weather_data[mw.away_team]
            
            if mw.is_rainy:
                away_data['rain']['goals'] += mw.away_goals
                away_data['rain']['conceded'] += mw.home_goals
                away_data['rain']['matches'] += 1
            else:
                away_data['dry']['goals'] += mw.away_goals
                away_data['dry']['conceded'] += mw.home_goals
                away_data['dry']['matches'] += 1
                
            if mw.is_cold:
                away_data['cold']['goals'] += mw.away_goals
                away_data['cold']['conceded'] += mw.home_goals
                away_data['cold']['matches'] += 1
            else:
                away_data['warm']['goals'] += mw.away_goals
                away_data['warm']['conceded'] += mw.home_goals
                away_data['warm']['matches'] += 1
                
            if mw.is_hot:
                away_data['hot']['goals'] += mw.away_goals
                away_data['hot']['conceded'] += mw.home_goals
                away_data['hot']['matches'] += 1
            elif not mw.is_cold:
                away_data['normal']['goals'] += mw.away_goals
                away_data['normal']['conceded'] += mw.home_goals
                away_data['normal']['matches'] += 1
                
        # Créer le DNA pour chaque équipe
        for team, data in team_weather_data.items():
            dna = WeatherDNA(team=team)
            
            # Rain
            dna.rain_matches = data['rain']['matches']
            dna.rain_goals_scored = data['rain']['goals']
            dna.rain_goals_conceded = data['rain']['conceded']
            
            dna.dry_matches = data['dry']['matches']
            dna.dry_goals_scored = data['dry']['goals']
            dna.dry_goals_conceded = data['dry']['conceded']
            
            # Cold
            dna.cold_matches = data['cold']['matches']
            dna.cold_goals_scored = data['cold']['goals']
            dna.cold_goals_conceded = data['cold']['conceded']
            
            dna.warm_matches = data['warm']['matches']
            dna.warm_goals_scored = data['warm']['goals']
            dna.warm_goals_conceded = data['warm']['conceded']
            
            # Hot
            dna.hot_matches = data['hot']['matches']
            dna.hot_goals_scored = data['hot']['goals']
            dna.hot_goals_conceded = data['hot']['conceded']
            
            dna.normal_matches = data['normal']['matches']
            dna.normal_goals_scored = data['normal']['goals']
            dna.normal_goals_conceded = data['normal']['conceded']
            
            dna.calculate()
            self.weather_dna[team] = dna
            
        print(f"   ✅ {len(self.weather_dna)} équipes avec Weather DNA")
        
        # Stats profils
        rain_attackers = sum(1 for d in self.weather_dna.values() if d.rain_attack_profile == "RAIN_ATTACKER")
        rain_leaky = sum(1 for d in self.weather_dna.values() if d.rain_defense_profile == "RAIN_LEAKY")
        cold_vulnerable = sum(1 for d in self.weather_dna.values() if d.cold_profile == "COLD_VULNERABLE")
        cold_specialists = sum(1 for d in self.weather_dna.values() if d.cold_profile == "COLD_SPECIALIST")
        heat_diesel = sum(1 for d in self.weather_dna.values() if d.hot_profile == "HEAT_DIESEL")
        
        print(f"\n   📊 PROFILS WEATHER DNA:")
        print(f"      🌧️ RAIN_ATTACKER: {rain_attackers}")
        print(f"      🌧️ RAIN_LEAKY: {rain_leaky}")
        print(f"      ❄️ COLD_SPECIALIST: {cold_specialists}")
        print(f"      ❄️ COLD_VULNERABLE: {cold_vulnerable}")
        print(f"      🔥 HEAT_DIESEL: {heat_diesel}")
        
    def _print_weather_insights(self) -> None:
        """Affiche les insights Weather DNA"""
        print("\n" + "─" * 80)
        print("📊 INSIGHTS PHASE 4.2 - WEATHER DNA")
        print("─" * 80)
        
        # Top RAIN_ATTACKER
        print("\n🌧️ TOP RAIN_ATTACKER (marquent plus sous la pluie):")
        rain_attackers = sorted(
            [d for d in self.weather_dna.values() 
             if d.rain_attack_profile == "RAIN_ATTACKER" and d.rain_matches >= 2],
            key=lambda x: -x.rain_attack_delta
        )[:10]
        
        for d in rain_attackers:
            print(f"   • {d.team:25} | Pluie: {d.rain_goals_avg:.2f}/match | Sec: {d.dry_goals_avg:.2f}/match | Δ +{d.rain_attack_delta:.2f}")
            
        # Top RAIN_LEAKY
        print("\n🌧️ TOP RAIN_LEAKY (encaissent plus sous la pluie):")
        rain_leaky = sorted(
            [d for d in self.weather_dna.values() 
             if d.rain_defense_profile == "RAIN_LEAKY" and d.rain_matches >= 2],
            key=lambda x: -x.rain_defense_delta
        )[:10]
        
        for d in rain_leaky:
            print(f"   • {d.team:25} | Pluie: {d.rain_conceded_avg:.2f}/match | Sec: {d.dry_conceded_avg:.2f}/match | Δ +{d.rain_defense_delta:.2f}")
            
        # Top COLD_VULNERABLE
        print("\n❄️ TOP COLD_VULNERABLE (moins bons par temps froid):")
        cold_vulnerable = sorted(
            [d for d in self.weather_dna.values() 
             if d.cold_profile == "COLD_VULNERABLE" and d.cold_matches >= 2],
            key=lambda x: x.cold_attack_delta
        )[:10]
        
        for d in cold_vulnerable:
            print(f"   • {d.team:25} | Froid: {d.cold_goals_avg:.2f}/match | Chaud: {d.warm_goals_avg:.2f}/match | Δ {d.cold_attack_delta:.2f}")
            
        # Top COLD_SPECIALIST
        print("\n❄️ TOP COLD_SPECIALIST (meilleurs par temps froid):")
        cold_specialists = sorted(
            [d for d in self.weather_dna.values() 
             if d.cold_profile == "COLD_SPECIALIST" and d.cold_matches >= 2],
            key=lambda x: -x.cold_attack_delta
        )[:10]
        
        for d in cold_specialists:
            print(f"   • {d.team:25} | Froid: {d.cold_goals_avg:.2f}/match | Chaud: {d.warm_goals_avg:.2f}/match | Δ +{d.cold_attack_delta:.2f}")
            
        # Plus grands edges météo
        print("\n🔥 PLUS GRANDS EDGES MÉTÉO:")
        max_edges = sorted(
            [d for d in self.weather_dna.values() if d.max_weather_edge >= 1.0],
            key=lambda x: -x.max_weather_edge
        )[:10]
        
        for d in max_edges:
            print(f"   • {d.team:25} | Best: {d.best_weather_condition} | Worst: {d.worst_weather_condition} | Edge: {d.max_weather_edge:.2f}")
            
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS PHASE 4.2
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_weather_dna(self, team: str) -> Optional[WeatherDNA]:
        """Retourne le Weather DNA d'une équipe"""
        return self.weather_dna.get(team)
        
    def get_rain_attackers(self, min_delta: float = 0.5) -> List[WeatherDNA]:
        """Retourne les équipes RAIN_ATTACKER"""
        return sorted(
            [d for d in self.weather_dna.values() 
             if d.rain_attack_delta >= min_delta and d.rain_matches >= 2],
            key=lambda x: -x.rain_attack_delta
        )
        
    def get_rain_leaky(self, min_delta: float = 0.5) -> List[WeatherDNA]:
        """Retourne les équipes RAIN_LEAKY"""
        return sorted(
            [d for d in self.weather_dna.values() 
             if d.rain_defense_delta >= min_delta and d.rain_matches >= 2],
            key=lambda x: -x.rain_defense_delta
        )
        
    def get_cold_vulnerable(self, max_delta: float = -0.5) -> List[WeatherDNA]:
        """Retourne les équipes COLD_VULNERABLE"""
        return sorted(
            [d for d in self.weather_dna.values() 
             if d.cold_attack_delta <= max_delta and d.cold_matches >= 2],
            key=lambda x: x.cold_attack_delta
        )
        
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE COMPLÈTE PHASE 4.2
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_weather(self, team: str) -> None:
        """Analyse complète Weather DNA pour une équipe"""
        print("=" * 80)
        print(f"🌧️ ANALYSE WEATHER DNA: {team}")
        print("=" * 80)
        
        w_dna = self.get_weather_dna(team)
        if not w_dna:
            print(f"❌ Pas de données Weather pour {team}")
            return
            
        print(f"\n🌧️ WEATHER DNA:")
        print(f"   • Profil global: {w_dna.weather_profile}")
        
        print(f"\n   🌧️ RAIN ANALYSIS:")
        print(f"      Matchs pluie: {w_dna.rain_matches} | Sec: {w_dna.dry_matches}")
        print(f"      Buts pluie: {w_dna.rain_goals_avg:.2f}/match | Sec: {w_dna.dry_goals_avg:.2f}/match | Δ {w_dna.rain_attack_delta:+.2f}")
        print(f"      Encaissés pluie: {w_dna.rain_conceded_avg:.2f}/match | Sec: {w_dna.dry_conceded_avg:.2f}/match | Δ {w_dna.rain_defense_delta:+.2f}")
        print(f"      Profil attaque: {w_dna.rain_attack_profile}")
        print(f"      Profil défense: {w_dna.rain_defense_profile}")
        
        print(f"\n   ❄️ COLD ANALYSIS (<10°C):")
        print(f"      Matchs froid: {w_dna.cold_matches} | Chaud: {w_dna.warm_matches}")
        print(f"      Buts froid: {w_dna.cold_goals_avg:.2f}/match | Chaud: {w_dna.warm_goals_avg:.2f}/match | Δ {w_dna.cold_attack_delta:+.2f}")
        print(f"      Profil: {w_dna.cold_profile}")
        
        print(f"\n   🔥 HOT ANALYSIS (>25°C):")
        print(f"      Matchs chaud: {w_dna.hot_matches} | Normal: {w_dna.normal_matches}")
        if w_dna.hot_matches >= 2:
            print(f"      Buts chaud: {w_dna.hot_goals_avg:.2f}/match | Normal: {w_dna.normal_goals_avg:.2f}/match | Δ {w_dna.hot_attack_delta:+.2f}")
            print(f"      Profil: {w_dna.hot_profile}")
        else:
            print(f"      Données insuffisantes")
            
        print(f"\n   🎯 EDGE BETTING:")
        print(f"      Best condition: {w_dna.best_weather_condition}")
        print(f"      Worst condition: {w_dna.worst_weather_condition}")
        print(f"      Max edge: {w_dna.max_weather_edge:.2f} buts/match")
        
        # Recommandations
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS WEATHER:")
        
        if w_dna.rain_attack_profile == "RAIN_ATTACKER":
            print(f"   ✅ Match {team} sous la pluie → BACK Over Team Goals (+{w_dna.rain_attack_delta:.2f})")
        elif w_dna.rain_attack_profile == "RAIN_WEAK":
            print(f"   ⚠️ Match {team} sous la pluie → LAY Over ({w_dna.rain_attack_delta:.2f})")
            
        if w_dna.rain_defense_profile == "RAIN_LEAKY":
            print(f"   ⚠️ Match {team} sous la pluie → BACK Opponent Goals (+{w_dna.rain_defense_delta:.2f} encaissés)")
            
        if w_dna.cold_profile == "COLD_VULNERABLE":
            print(f"   ⚠️ Match {team} par temps froid → LAY Over ({w_dna.cold_attack_delta:.2f})")
        elif w_dna.cold_profile == "COLD_SPECIALIST":
            print(f"   ✅ Match {team} par temps froid → BACK Over (+{w_dna.cold_attack_delta:.2f})")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = AttackDataLoaderV56Phase42()
    loader.load_all()
    
    print("\n" + "=" * 80)
    print("🧪 TEST: ANALYSE WEATHER DNA")
    print("=" * 80)
    
    for team in ["Liverpool", "Bayern Munich", "Real Madrid"]:
        loader.analyze_weather(team)
        print()

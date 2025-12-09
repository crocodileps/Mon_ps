"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - DATA LOADER
   Chargement unifié de toutes les sources de données
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import DATA_SOURCES, LEAGUES, THRESHOLDS


class TeamNameNormalizer:
    """
    Normalise les noms d'équipes entre Football-Data UK et Understat.
    Utilise un mapping bidirectionnel validé scientifiquement.
    """
    
    def __init__(self, mapping_path: Path = None):
        if mapping_path is None:
            mapping_path = DATA_SOURCES['team_mapping']
        
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        self.fd_to_understat = mapping_data.get('fd_to_understat', {})
        self.understat_to_fd = mapping_data.get('understat_to_fd', {})
        self.teams_without_history = set(mapping_data.get('teams_without_understat_history', []))
        self._cache = {}
    
    def normalize(self, team_name: str, target: str = 'understat') -> str:
        """Normalise un nom d'équipe vers le format cible."""
        if not team_name:
            return None
        
        cache_key = f"{team_name}_{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        clean_name = team_name.strip()
        
        if target == 'understat':
            result = self.fd_to_understat.get(clean_name, clean_name)
        else:
            result = self.understat_to_fd.get(clean_name, clean_name)
        
        self._cache[cache_key] = result
        return result
    
    def has_understat_history(self, team_name: str) -> bool:
        """Vérifie si l'équipe a des données Understat historiques."""
        return team_name not in self.teams_without_history


class DefenseDataLoader:
    """
    Charge et unifie toutes les sources de données pour l'Agent Défense 2.0.
    
    Sources:
        - Defense DNA (Understat): defensive_lines, defender_dna, goalkeeper_dna, team_defense
        - Football-Data UK: corners, shots, fouls, cards, goals
        - Referee DNA
        - Quantum V2: zone_analysis, gamestate_insights
    """
    
    def __init__(self):
        self.normalizer = TeamNameNormalizer()
        self._data_cache = {}
        self._loaded = False
    
    def load_all(self) -> None:
        """Charge toutes les sources de données."""
        print("=" * 80)
        print("🏦 CHARGEMENT DES DONNÉES - AGENT DÉFENSE 2.0")
        print("=" * 80)
        
        # 1. Defense DNA (Understat)
        self._load_defensive_lines()
        self._load_defender_dna()
        self._load_goalkeeper_dna()
        self._load_team_defense_2025()
        
        # 2. Football-Data UK
        self._load_football_data_dna()
        
        # 3. Referee DNA
        self._load_referee_dna()
        
        # 4. Quantum V2
        self._load_quantum_data()
        
        # 5. Historical matches
        self._load_historical_matches()
        
        self._loaded = True
        print("\n✅ Toutes les données chargées")
        self._print_summary()
    
    def _load_json(self, key: str) -> Any:
        """Charge un fichier JSON depuis DATA_SOURCES."""
        path = DATA_SOURCES.get(key)
        if path and path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _load_defensive_lines(self) -> None:
        """Charge defensive_lines_v8_3."""
        data = self._load_json('defensive_lines')
        if data:
            # Indexer par nom d'équipe normalisé
            self._data_cache['defensive_lines'] = {
                item['team_name']: item for item in data
            }
            print(f"   ✅ defensive_lines: {len(data)} équipes")
    
    def _load_defender_dna(self) -> None:
        """Charge defender_dna_v9 et agrège par équipe."""
        data = self._load_json('defender_dna')
        if data:
            # Stocker les données brutes par joueur
            self._data_cache['defenders_raw'] = data
            
            # Agréger par équipe
            team_defenders = {}
            for defender in data:
                team = defender.get('team_understat', defender.get('team'))
                if team:
                    if team not in team_defenders:
                        team_defenders[team] = []
                    team_defenders[team].append(defender)
            
            # Calculer les agrégats par équipe
            self._data_cache['defenders_by_team'] = self._aggregate_defenders(team_defenders)
            print(f"   ✅ defender_dna: {len(data)} défenseurs, {len(team_defenders)} équipes")
    
    def _aggregate_defenders(self, team_defenders: Dict) -> Dict:
        """Agrège les statistiques des défenseurs par équipe."""
        aggregated = {}
        
        for team, defenders in team_defenders.items():
            if len(defenders) == 0:
                continue
            
            # Moyennes pondérées par temps de jeu
            total_time = sum(d.get('time', 0) or 0 for d in defenders)
            if total_time == 0:
                total_time = 1
            
            # Helper pour extraire les dimensions DNA en toute sécurité
            def safe_get_dna(d, dim, default=50):
                dna = d.get('dna')
                if dna is None:
                    return default
                dims = dna.get('dimensions')
                if dims is None:
                    return default
                return dims.get(dim, default)
            
            # Helper pour extraire quant_v9 en toute sécurité
            def safe_get_quant_v9(d, key, default=0):
                qv9 = d.get('quant_v9')
                if qv9 is None:
                    return default
                if key == 'alpha':
                    ab = qv9.get('alpha_beta')
                    if ab is None:
                        return default
                    return ab.get('alpha', default)
                return qv9.get(key, default)
            
            # Helper pour extraire quant_v8 xCards
            def safe_get_xcard_prob(d):
                qv8 = d.get('quant_v8')
                if qv8 is None:
                    return 0
                xcards = qv8.get('xCards')
                if xcards is None:
                    return 0
                return xcards.get('probability', 0) or 0
            
            # Sélectionner les titulaires (top 4 par temps de jeu)
            starters = sorted(defenders, key=lambda x: x.get('time', 0) or 0, reverse=True)[:4]
            
            agg = {
                'team': team,
                'num_defenders': len(defenders),
                'total_time': total_time,
                
                # Moyennes pondérées
                'avg_cards_90': sum((d.get('cards_90', 0) or 0) * (d.get('time', 0) or 0) for d in defenders) / total_time,
                'avg_impact_goals': sum((d.get('impact_goals_conceded', 0) or 0) * (d.get('time', 0) or 0) for d in defenders) / total_time,
                
                # DNA dimensions (moyenne simple des titulaires)
                'avg_shield': np.mean([safe_get_dna(d, 'SHIELD', 50) for d in starters]) if starters else 50,
                'avg_fortress': np.mean([safe_get_dna(d, 'FORTRESS', 50) for d in starters]) if starters else 50,
                'avg_discipline': np.mean([safe_get_dna(d, 'DISCIPLINE', 50) for d in starters]) if starters else 50,
                
                # Quant V9 aggregates
                'avg_alpha': np.mean([safe_get_quant_v9(d, 'alpha', 0) for d in starters if d.get('quant_v9')]) if any(d.get('quant_v9') for d in starters) else 0,
                'avg_sharpe': np.mean([safe_get_quant_v9(d, 'sharpe_ratio', 0) for d in starters if d.get('quant_v9')]) if any(d.get('quant_v9') for d in starters) else 0,
                'max_transition_vuln': max([safe_get_quant_v9(d, 'transition_vulnerability_index', 0) for d in starters if d.get('quant_v9')] or [0]),
                
                # Risk profile
                'disciplinary_risk': sum(1 for d in defenders if safe_get_xcard_prob(d) > 0.25),
            }
            
            aggregated[team] = agg
        
        return aggregated
    
    def _load_goalkeeper_dna(self) -> None:
        """Charge goalkeeper_dna (V4.4) et timing."""
        # GK DNA - Supporte liste OU dict (V4.4 est déjà un dict par équipe)
        gk_data = self._load_json('goalkeeper_dna')
        if gk_data:
            # V4.4 est déjà un dict par équipe
            if isinstance(gk_data, dict):
                # Vérifier si c'est un dict avec métadonnées (format V4.4 complet)
                if 'goalkeepers' in gk_data:
                    # Format: {'metadata': {...}, 'goalkeepers': [...]}
                    gk_list = gk_data['goalkeepers']
                    self._data_cache['goalkeeper_dna'] = {
                        item['team']: item for item in gk_list
                    }
                elif 'Arsenal' in gk_data or len(gk_data) > 50:
                    # Format: {'Arsenal': {...}, 'Liverpool': {...}, ...}
                    self._data_cache['goalkeeper_dna'] = gk_data
                else:
                    # Format inconnu, essayer comme dict
                    self._data_cache['goalkeeper_dna'] = gk_data
            elif isinstance(gk_data, list):
                # Ancien format: liste de gardiens
                self._data_cache['goalkeeper_dna'] = {
                    item['team']: item for item in gk_data
                }
            print(f"   ✅ goalkeeper_dna: {len(self._data_cache.get('goalkeeper_dna', {}))} gardiens")
        
        # GK Timing - même logique
        timing_data = self._load_json('goalkeeper_timing')
        if timing_data:
            if isinstance(timing_data, dict):
                if 'goalkeepers' in timing_data:
                    timing_list = timing_data['goalkeepers']
                    self._data_cache['goalkeeper_timing'] = {
                        item['team']: item for item in timing_list
                    }
                elif 'Arsenal' in timing_data or len(timing_data) > 50:
                    self._data_cache['goalkeeper_timing'] = timing_data
                else:
                    self._data_cache['goalkeeper_timing'] = timing_data
            elif isinstance(timing_data, list):
                self._data_cache['goalkeeper_timing'] = {
                    item['team']: item for item in timing_data
                }
            print(f"   ✅ goalkeeper_timing: {len(self._data_cache.get('goalkeeper_timing', {}))} gardiens")
    
    def _load_team_defense_2025(self) -> None:
        """Charge team_defense_dna_2025."""
        data = self._load_json('team_defense_2025')
        if data:
            self._data_cache['team_defense'] = {
                item.get('team_understat', item.get('team_name')): item for item in data
            }
            print(f"   ✅ team_defense_2025: {len(data)} équipes")
    
    def _load_football_data_dna(self) -> None:
        """Charge les DNA Football-Data UK 2025-26."""
        sources = ['corners_dna', 'shots_dna', 'fouls_dna', 'cards_team_dna', 'goals_enhanced']
        
        for source in sources:
            data = self._load_json(source)
            if data:
                # Normaliser les noms d'équipes
                indexed = {}
                for item in data:
                    team_fd = item.get('team')
                    team_us = self.normalizer.normalize(team_fd, 'understat')
                    item['team_normalized'] = team_us
                    indexed[team_us] = item
                
                self._data_cache[source] = indexed
                print(f"   ✅ {source}: {len(data)} équipes")
    
    def _load_referee_dna(self) -> None:
        """Charge referee_dna_v4."""
        data = self._load_json('referee_dna')
        if data:
            self._data_cache['referee_dna'] = {
                item['referee_name']: item for item in data
            }
            print(f"   ✅ referee_dna: {len(data)} arbitres")
    
    def _load_quantum_data(self) -> None:
        """Charge les données Quantum V2."""
        # Zone Analysis
        zone_data = self._load_json('zone_analysis')
        if zone_data:
            self._data_cache['zone_analysis'] = zone_data
            print(f"   ✅ zone_analysis: {len(zone_data)} équipes")
        
        # Gamestate Insights
        gamestate_data = self._load_json('gamestate_insights')
        if gamestate_data:
            self._data_cache['gamestate_insights'] = gamestate_data
            print(f"   ✅ gamestate_insights: {len(gamestate_data)} équipes")
        
        # Team Exploit Profiles
        exploit_data = self._load_json('team_exploit_profiles')
        if exploit_data:
            self._data_cache['team_exploits'] = exploit_data
            print(f"   ✅ team_exploits: {len(exploit_data)} équipes")
    
    def _load_historical_matches(self) -> None:
        """Charge les matchs historiques pour backtest."""
        path = DATA_SOURCES.get('matches_historical')
        if path and path.exists():
            df = pd.read_csv(path)
            self._data_cache['matches'] = df
            print(f"   ✅ matches_historical: {len(df)} matchs")
    
    def _print_summary(self) -> None:
        """Affiche un résumé des données chargées."""
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DES DONNÉES")
        print("=" * 80)
        
        for key, data in self._data_cache.items():
            if isinstance(data, dict):
                print(f"   • {key}: {len(data)} records")
            elif isinstance(data, pd.DataFrame):
                print(f"   • {key}: {len(data)} rows × {len(data.columns)} cols")
            elif isinstance(data, list):
                print(f"   • {key}: {len(data)} items")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_data(self, team_name: str) -> Dict[str, Any]:
        """
        Récupère toutes les données disponibles pour une équipe.
        
        Args:
            team_name: Nom de l'équipe (format Understat ou Football-Data)
        
        Returns:
            Dictionnaire avec toutes les sources de données
        """
        # Normaliser le nom
        team_us = self.normalizer.normalize(team_name, 'understat')
        team_fd = self.normalizer.normalize(team_name, 'football_data')
        
        result = {
            'team': team_us,
            'team_fd': team_fd,
            'has_understat_history': self.normalizer.has_understat_history(team_name),
        }
        
        # Récupérer chaque source
        if 'defensive_lines' in self._data_cache:
            result['defensive_lines'] = self._data_cache['defensive_lines'].get(team_us)
        
        if 'defenders_by_team' in self._data_cache:
            result['defenders'] = self._data_cache['defenders_by_team'].get(team_us)
        
        if 'goalkeeper_dna' in self._data_cache:
            result['goalkeeper'] = self._data_cache['goalkeeper_dna'].get(team_us)
        
        if 'goalkeeper_timing' in self._data_cache:
            result['gk_timing'] = self._data_cache['goalkeeper_timing'].get(team_us)
        
        if 'team_defense' in self._data_cache:
            result['team_defense'] = self._data_cache['team_defense'].get(team_us)
        
        # Football-Data DNA
        for source in ['corners_dna', 'shots_dna', 'fouls_dna', 'cards_team_dna', 'goals_enhanced']:
            if source in self._data_cache:
                result[source] = self._data_cache[source].get(team_us)
        
        # Quantum V2
        if 'zone_analysis' in self._data_cache:
            result['zones'] = self._data_cache['zone_analysis'].get(team_us)
        
        if 'gamestate_insights' in self._data_cache:
            result['gamestate'] = self._data_cache['gamestate_insights'].get(team_us)
        
        if 'team_exploits' in self._data_cache:
            result['exploits'] = self._data_cache['team_exploits'].get(team_us)
        
        return result
    
    def get_referee_data(self, referee_name: str) -> Optional[Dict]:
        """Récupère les données d'un arbitre."""
        if 'referee_dna' in self._data_cache:
            return self._data_cache['referee_dna'].get(referee_name)
        return None
    
    def get_matches(self, league: str = None, season: str = None) -> pd.DataFrame:
        """Récupère les matchs historiques avec filtres optionnels."""
        if 'matches' not in self._data_cache:
            return pd.DataFrame()
        
        df = self._data_cache['matches'].copy()
        
        if league:
            df = df[df['league'] == league]
        if season:
            df = df[df['season'] == season]
        
        return df
    
    def get_all_teams(self) -> List[str]:
        """Retourne la liste de toutes les équipes disponibles."""
        teams = set()
        
        if 'defensive_lines' in self._data_cache:
            teams.update(self._data_cache['defensive_lines'].keys())
        
        if 'corners_dna' in self._data_cache:
            teams.update(self._data_cache['corners_dna'].keys())
        
        return sorted(list(teams))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = DefenseDataLoader()
    loader.load_all()
    
    # Test: récupérer données Arsenal
    print("\n" + "=" * 80)
    print("🧪 TEST: Données Arsenal")
    print("=" * 80)
    
    arsenal = loader.get_team_data('Arsenal')
    for key, value in arsenal.items():
        if value is not None:
            if isinstance(value, dict):
                print(f"   ✅ {key}: {len(value)} clés")
            else:
                print(f"   ✅ {key}: {value}")
        else:
            print(f"   ❌ {key}: None")

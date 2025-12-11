"""
DATA HUB V3.0 - Avec Market Profiles + Corners/Cards DNA
Charge toutes les sources de données incluant les profils marchés réels
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PATHS, DB_CONFIG  # FIXED: PATHS au lieu de DATA_PATHS


class DataHub:
    """Hub central pour toutes les données du Chess Engine"""
    
    def __init__(self):
        self.data = {}
        self.market_profiles = {}
        self.team_market_details = {}
        self.smart_rules = {}
        self.team_dna = {}  # NEW: corner_dna, card_dna, etc.
        self.loaded = False
        self.timestamp = None
    
    def load_all(self) -> None:
        """Charge toutes les sources de données"""
        print("="*70)
        print("🔄 DATA HUB - Chargement de toutes les sources")
        print("="*70)
        
        self._load_json_sources()
        self._load_postgres_sources()
        self._load_market_profiles()
        self._load_team_dna()  # NEW
        
        self.loaded = True
        self.timestamp = datetime.now().isoformat()
        
        print(f"\n✅ Data Hub charge: {len(self.data)} sources + market_profiles + team_dna")
        print(f"   Timestamp: {self.timestamp}")
    
    def _load_json_sources(self) -> None:
        """Charge les fichiers JSON"""
        json_sources = {
            "goalkeeper_dna": PATHS["goalkeeper_dna"],
            "defense_dna": PATHS["defense_dna"],
            "teams_context": PATHS["teams_context_dna"],
            "all_goals": PATHS["all_goals"],
            "players_impact": PATHS["players_impact"],
            "referee_dna": PATHS["referee_dna"],
            "team_exploits": PATHS["team_exploits"],
            "matches": PATHS["matches"],
            "defender_dna": PATHS["defender_dna"],
        }
        
        for name, path in json_sources.items():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.data[name] = data
                        count = len(data)
                    elif isinstance(data, dict):
                        self.data[name] = data
                        count = len(data)
                    else:
                        self.data[name] = data
                        count = 1
                    
                    display_name = name.replace("_", " ").title()
                    print(f"   ✅ {display_name}: {count} entrees")
            except Exception as e:
                print(f"   ❌ {name}: {e}")
                self.data[name] = {}
    
    def _load_postgres_sources(self) -> None:
        """Charge les données PostgreSQL"""
        print()
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print(f"   ✅ PostgreSQL connecte")
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Coach Intelligence
                cur.execute("SELECT * FROM public.coach_intelligence")
                self.data["coach_intelligence"] = {
                    row["coach_name"]: dict(row) for row in cur.fetchall()
                }
                print(f"   ✅ Coach Intelligence: {len(self.data['coach_intelligence'])} coaches")
                
                # Coach Mapping
                cur.execute("SELECT * FROM public.coach_team_mapping")
                self.data["coach_mapping"] = {}
                for row in cur.fetchall():
                    team = row.get("team_name") or row.get("team")
                    if team:
                        self.data["coach_mapping"][team] = dict(row)
                print(f"   ✅ Coach Mapping: {len(self.data['coach_mapping'])} equipes")
                
                # Scenarios
                cur.execute("SELECT * FROM quantum.scenario_catalog")
                self.data["scenarios"] = {row["scenario_code"]: dict(row) for row in cur.fetchall()}
                print(f"   ✅ Scenarios: {len(self.data['scenarios'])}")
                
                # Strategies
                cur.execute("SELECT * FROM quantum.strategy_catalog")
                self.data["strategies"] = {row["strategy_code"]: dict(row) for row in cur.fetchall()}
                print(f"   ✅ Strategies: {len(self.data['strategies'])}")
                
                # Team Profiles
                cur.execute("SELECT * FROM quantum.team_profiles")
                self.data["team_profiles"] = {row["team_name"]: dict(row) for row in cur.fetchall()}
                print(f"   ✅ Team Profiles: {len(self.data['team_profiles'])}")
                
                # Referee Intelligence
                cur.execute("SELECT * FROM public.referee_intelligence")
                self.data["referee_intelligence"] = {}
                for row in cur.fetchall():
                    name = row.get("referee_name")
                    if name:
                        self.data["referee_intelligence"][name] = dict(row)
                print(f"   ✅ Referee Intelligence: {len(self.data['referee_intelligence'])} arbitres")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ PostgreSQL: {e}")
    
    def _load_market_profiles(self) -> None:
        """Charge les profils de marchés depuis PostgreSQL"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Market Profiles
                cur.execute("SELECT * FROM public.market_profiles")
                for row in cur.fetchall():
                    team = row["team_name"]
                    self.market_profiles[team] = {
                        "over25_rate": float(row["over25_rate"] or 50),
                        "btts_rate": float(row["btts_rate"] or 50),
                        "under25_rate": float(row["under25_rate"] or 50),
                        "clean_sheet_rate": float(row["clean_sheet_rate"] or 25),
                        "fail_to_score_rate": float(row["fail_to_score_rate"] or 25),
                        "home_over25_rate": float(row["home_over25_rate"] or 50),
                        "away_over25_rate": float(row["away_over25_rate"] or 50),
                        "home_btts_rate": float(row["home_btts_rate"] or 50),
                        "away_btts_rate": float(row["away_btts_rate"] or 50),
                    }
                print(f"   ✅ Market Profiles: {len(self.market_profiles)} equipes")
                
                # Team Market Details
                cur.execute("""
                    SELECT team_name, market_type, win_rate, roi, avg_odds, 
                           is_best_market, is_avoid_market, confidence_score
                    FROM public.team_market_profiles
                    WHERE sample_size >= 10
                """)
                for row in cur.fetchall():
                    team = row["team_name"]
                    market = row["market_type"]
                    if team not in self.team_market_details:
                        self.team_market_details[team] = {}
                    self.team_market_details[team][market] = {
                        "win_rate": float(row["win_rate"] or 50),
                        "roi": float(row["roi"] or 0),
                        "avg_odds": float(row["avg_odds"] or 2.0),
                        "is_best": row["is_best_market"],
                        "is_avoid": row["is_avoid_market"],
                        "confidence": float(row["confidence_score"] or 50),
                    }
                print(f"   ✅ Team Market Details: {len(self.team_market_details)} equipes")
                
                # Smart Rules
                cur.execute("SELECT rule_name, rule_data FROM public.smart_market_rules")
                for row in cur.fetchall():
                    self.smart_rules[row["rule_name"]] = row["rule_data"]
                print(f"   ✅ Smart Rules: {len(self.smart_rules)} regles")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Market Profiles: {e}")
    
    def _load_team_dna(self) -> None:
        """Charge les DNA corners/cards/scorers depuis quantum.team_stats_extended"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT team_name, corner_dna, card_dna, goalscorer_dna, 
                           goal_timing_dna, handicap_dna, scorer_dna, matches_analyzed
                    FROM quantum.team_stats_extended
                """)
                
                for row in cur.fetchall():
                    team = row["team_name"]
                    self.team_dna[team] = {
                        "corner": row["corner_dna"] or {},
                        "card": row["card_dna"] or {},
                        "goalscorer": row["goalscorer_dna"] or {},
                        "goal_timing": row["goal_timing_dna"] or {},
                        "handicap": row["handicap_dna"] or {},
                        "scorer": row["scorer_dna"] or {},
                        "matches": row["matches_analyzed"] or 0,
                    }
                
                print(f"   ✅ Team DNA (corners/cards): {len(self.team_dna)} equipes")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Team DNA: {e}")
    
    def get_team_data(self, team_name: str) -> Dict[str, Any]:
        """Récupère toutes les données d'une équipe"""
        result = {
            "team_name": team_name,
            "goalkeeper": None,
            "defense": None,
            "context": None,
            "exploits": None,
            "coach": None,
            "profile": None,
            "market_profile": None,
            "market_details": None,
            "dna": None,  # NEW: corner/card/scorer DNA
        }
        
        normalized = self._normalize_team_name(team_name)
        
        # Goalkeeper DNA
        gk_data = self.data.get("goalkeeper_dna", {})
        if isinstance(gk_data, dict):
            result["goalkeeper"] = gk_data.get(normalized) or gk_data.get(team_name)
        
        # Defense DNA
        def_data = self.data.get("defense_dna", {})
        if isinstance(def_data, dict):
            result["defense"] = def_data.get(normalized) or def_data.get(team_name)
        
        # Teams Context
        ctx_data = self.data.get("teams_context", {})
        if isinstance(ctx_data, dict):
            result["context"] = ctx_data.get(normalized) or ctx_data.get(team_name)
        
        # Team Exploits
        exp_data = self.data.get("team_exploits", {})
        if isinstance(exp_data, dict):
            result["exploits"] = exp_data.get(normalized) or exp_data.get(team_name)
        
        # Coach
        mapping = self.data.get("coach_mapping", {})
        coach_name = None
        for key, val in mapping.items():
            if normalized.lower() in key.lower() or team_name.lower() in key.lower():
                coach_name = val.get("coach_name")
                break
        if coach_name:
            result["coach"] = self.data.get("coach_intelligence", {}).get(coach_name)
        
        # Team Profile
        profiles = self.data.get("team_profiles", {})
        for key, val in profiles.items():
            if normalized.lower() in key.lower() or team_name.lower() in key.lower():
                result["profile"] = val
                break
        
        # Market Profile
        for key in self.market_profiles:
            if normalized.lower() in key.lower() or team_name.lower() in key.lower():
                result["market_profile"] = self.market_profiles[key]
                break
        
        # Market Details
        for key in self.team_market_details:
            if normalized.lower() in key.lower() or team_name.lower() in key.lower():
                result["market_details"] = self.team_market_details[key]
                break
        
        # NEW: Team DNA (corners/cards)
        for key in self.team_dna:
            if normalized.lower() in key.lower() or team_name.lower() in key.lower():
                result["dna"] = self.team_dna[key]
                break
        
        return result
    
    def get_market_profile(self, team_name: str, location: str = "overall") -> Dict[str, float]:
        """Récupère le profil marché d'une équipe"""
        for key in self.market_profiles:
            if team_name.lower() in key.lower():
                profile = self.market_profiles[key]
                
                if location == "home":
                    return {
                        "over25": profile["home_over25_rate"],
                        "btts": profile["home_btts_rate"],
                        "under25": 100 - profile["home_over25_rate"],
                        "clean_sheet": profile["clean_sheet_rate"],
                        "fail_to_score": profile["fail_to_score_rate"],
                    }
                elif location == "away":
                    return {
                        "over25": profile["away_over25_rate"],
                        "btts": profile["away_btts_rate"],
                        "under25": 100 - profile["away_over25_rate"],
                        "clean_sheet": profile["clean_sheet_rate"],
                        "fail_to_score": profile["fail_to_score_rate"],
                    }
                else:
                    return {
                        "over25": profile["over25_rate"],
                        "btts": profile["btts_rate"],
                        "under25": profile["under25_rate"],
                        "clean_sheet": profile["clean_sheet_rate"],
                        "fail_to_score": profile["fail_to_score_rate"],
                    }
        
        return {"over25": 53, "btts": 52, "under25": 47, "clean_sheet": 25, "fail_to_score": 25}
    
    def get_corner_dna(self, team_name: str) -> Dict[str, Any]:
        """Récupère le Corner DNA d'une équipe"""
        for key in self.team_dna:
            if team_name.lower() in key.lower():
                return self.team_dna[key].get("corner", {})
        return {}
    
    def get_card_dna(self, team_name: str) -> Dict[str, Any]:
        """Récupère le Card DNA d'une équipe"""
        for key in self.team_dna:
            if team_name.lower() in key.lower():
                return self.team_dna[key].get("card", {})
        return {}
    
    def get_referee_data(self, referee_name: str) -> Optional[Dict]:
        """Récupère les données d'un arbitre"""
        # D'abord dans referee_intelligence (plus complet)
        ref_int = self.data.get("referee_intelligence", {})
        for key, val in ref_int.items():
            if referee_name and referee_name.lower() in key.lower():
                return val
        
        # Fallback sur referee_dna JSON
        ref_data = self.data.get("referee_dna", {})
        if isinstance(ref_data, list):
            for ref in ref_data:
                if referee_name and referee_name.lower() in ref.get("referee", "").lower():
                    return ref
        elif isinstance(ref_data, dict):
            return ref_data.get(referee_name)
        
        return None
    
    def is_specialist(self, team_name: str, market: str, location: str) -> Optional[Dict]:
        """Vérifie si une équipe est spécialiste d'un marché"""
        rule_map = {
            "btts_yes": "btts_specialists",
            "btts_no": "btts_specialists",
            "over_25": "over_specialists",
            "over_35": "over_specialists",
            "under_25": "under_specialists",
            "under_35": "under_specialists",
        }
        
        rule_name = rule_map.get(market)
        if not rule_name or rule_name not in self.smart_rules:
            return None
        
        teams = self.smart_rules[rule_name].get("teams", [])
        for t in teams:
            if team_name.lower() in t["team"].lower() and t["location"] == location:
                if t["market"] == market:
                    return t
        
        return None
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalise un nom d'équipe"""
        replacements = {
            "Manchester United": "Manchester Utd",
            "Wolverhampton Wanderers": "Wolves",
            "Tottenham Hotspur": "Tottenham",
            "Nottingham Forest": "Nott'm Forest",
            "Newcastle United": "Newcastle",
            "AFC Bournemouth": "Bournemouth",
            "Brighton & Hove Albion": "Brighton",
            "West Ham United": "West Ham",
        }
        return replacements.get(name, name)

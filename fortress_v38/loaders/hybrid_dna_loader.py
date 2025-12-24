"""
FORTRESS V3.8 - Hybrid DNA Loader
=================================

Charge le DNA des équipes depuis DEUX sources:
1. JSON (team_dna_unified_v2.json) - Source la plus riche (~200 clés)
2. PostgreSQL (quantum.team_quantum_dna_v3) - Subset (~60 colonnes)

Stratégie: JSON comme base, PostgreSQL comme enrichissement.
Fallback: Si DB échoue, utiliser JSON seul.

Version: 1.0.0
Date: 24 Décembre 2025
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Setup path
PROJECT_ROOT = Path("/home/Mon_ps")
sys.path.insert(0, str(PROJECT_ROOT))

# Config
from fortress_v38.config import (
    TEAM_DNA_UNIFIED,
    GOALKEEPER_DNA_V44,
    DEFENSE_DNA_V51,
    get_postgres_connection,
    POSTGRES_TABLES
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# DATACLASS RÉSULTAT
# ═══════════════════════════════════════════════════════════════

@dataclass
class TeamDNA:
    """DNA complet d'une équipe (fusion JSON + DB)."""
    team_name: str
    league: str = ""
    
    # DNA de base (depuis JSON)
    base_dna: Dict[str, Any] = field(default_factory=dict)
    
    # DNA enrichi (depuis PostgreSQL)
    db_dna: Dict[str, Any] = field(default_factory=dict)
    
    # DNA fusionné
    merged_dna: Dict[str, Any] = field(default_factory=dict)
    
    # Métadonnées
    source: str = "JSON"  # JSON, DB, HYBRID
    data_quality: float = 1.0
    
    def get(self, key: str, default: Any = None) -> Any:
        """Accès unifié au DNA fusionné."""
        return self.merged_dna.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        return self.merged_dna[key]
    
    def keys(self):
        return self.merged_dna.keys()


@dataclass
class GoalkeeperDNA:
    """DNA d'un gardien."""
    gk_name: str
    team_name: str
    
    # Profil complet
    profile: Dict[str, Any] = field(default_factory=dict)
    
    # Métriques clés
    panic_score: float = 0.0
    timing_profile: str = "CONSISTENT"
    exploit_paths: List[Dict] = field(default_factory=list)


@dataclass
class DefenseDNA:
    """DNA défensif d'une équipe."""
    team_name: str
    
    # Profil V5.1
    profile: Dict[str, Any] = field(default_factory=dict)
    
    # Métriques clés
    percentiles: Dict[str, float] = field(default_factory=dict)
    weaknesses: List[Dict] = field(default_factory=list)
    strengths: List[Dict] = field(default_factory=list)
    exploit_paths: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# HYBRID DNA LOADER
# ═══════════════════════════════════════════════════════════════

class HybridDNALoader:
    """
    Charge le DNA depuis JSON et PostgreSQL.
    
    Stratégie de fusion:
    1. Charger JSON (source principale)
    2. Enrichir avec PostgreSQL (colonnes additionnelles)
    3. Fallback vers JSON si DB échoue
    """
    
    def __init__(self):
        self._team_dna_cache: Dict[str, TeamDNA] = {}
        self._gk_dna_cache: Dict[str, GoalkeeperDNA] = {}
        self._defense_dna_cache: Dict[str, DefenseDNA] = {}
        
        # Données JSON (chargées une fois)
        self._json_team_dna: Optional[Dict] = None
        self._json_gk_dna: Optional[Dict] = None
        self._json_defense_dna: Optional[List] = None
        
        # Stats
        self._load_stats = {
            "teams_from_json": 0,
            "teams_from_db": 0,
            "teams_hybrid": 0,
            "gk_loaded": 0,
            "defense_loaded": 0,
            "db_errors": 0
        }
    
    # ─── CHARGEMENT JSON ───
    
    def _load_json_team_dna(self) -> Dict:
        """Charge team_dna_unified_v2.json."""
        if self._json_team_dna is not None:
            return self._json_team_dna
        
        try:
            with open(TEAM_DNA_UNIFIED, 'r') as f:
                data = json.load(f)
            
            # Le fichier peut être {metadata, teams} ou directement un dict
            if isinstance(data, dict):
                if "teams" in data:
                    self._json_team_dna = data["teams"]
                else:
                    self._json_team_dna = data
            else:
                # C'est une liste - convertir en dict par team_name
                self._json_team_dna = {
                    t.get("team_name", t.get("name", "")): t 
                    for t in data
                }
            
            logger.info(f"✅ JSON Team DNA: {len(self._json_team_dna)} équipes")
            return self._json_team_dna
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement JSON Team DNA: {e}")
            self._json_team_dna = {}
            return {}
    
    def _load_json_gk_dna(self) -> Dict:
        """Charge goalkeeper_dna_v4_4_final.json."""
        if self._json_gk_dna is not None:
            return self._json_gk_dna
        
        try:
            with open(GOALKEEPER_DNA_V44, 'r') as f:
                data = json.load(f)
            
            # Format V4.4: {"metadata": {...}, "goalkeepers": [...]}
            # Chaque GK a: goalkeeper, team, gk_performance, etc.
            if isinstance(data, dict) and "goalkeepers" in data:
                gk_list = data["goalkeepers"]
                self._json_gk_dna = {}
                for gk in gk_list:
                    gk_name = gk.get("goalkeeper", "")
                    team = gk.get("team", "")
                    if gk_name:
                        self._json_gk_dna[gk_name] = gk
                        # Aussi indexer par équipe pour recherche rapide
                        self._json_gk_dna[f"team:{team}"] = gk
            elif isinstance(data, list):
                self._json_gk_dna = {
                    gk.get("goalkeeper", gk.get("player_name", "")): gk 
                    for gk in data
                }
            else:
                self._json_gk_dna = data
            
            logger.info(f"✅ JSON GK DNA: {len([k for k in self._json_gk_dna.keys() if not k.startswith('team:')])} gardiens")
            return self._json_gk_dna
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement JSON GK DNA: {e}")
            self._json_gk_dna = {}
            return {}

    def _load_json_defense_dna(self) -> List:
        """Charge team_defense_dna_v5_1_corrected.json."""
        if self._json_defense_dna is not None:
            return self._json_defense_dna
        
        try:
            with open(DEFENSE_DNA_V51, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self._json_defense_dna = data
            else:
                self._json_defense_dna = data.get("teams", [])
            
            logger.info(f"✅ JSON Defense DNA: {len(self._json_defense_dna)} équipes")
            return self._json_defense_dna
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement JSON Defense DNA: {e}")
            self._json_defense_dna = []
            return []
    
    # ─── CHARGEMENT POSTGRESQL ───
    
    def _load_db_team_dna(self, team_name: str) -> Optional[Dict]:
        """Charge DNA d'une équipe depuis PostgreSQL."""
        conn = get_postgres_connection()
        if not conn:
            self._load_stats["db_errors"] += 1
            return None
        
        try:
            cursor = conn.cursor()
            
            # Chercher l'équipe (case-insensitive, fuzzy)
            cursor.execute("""
                SELECT * FROM quantum.team_quantum_dna_v3
                WHERE LOWER(team_name) = LOWER(%s)
                   OR LOWER(team_name) LIKE LOWER(%s)
                LIMIT 1;
            """, (team_name, f"%{team_name}%"))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            # Convertir en dict
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            
            conn.close()
            self._load_stats["teams_from_db"] += 1
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur DB pour {team_name}: {e}")
            self._load_stats["db_errors"] += 1
            conn.close()
            return None
    
    # ─── FUSION ───
    
    def _merge_dna(self, json_dna: Dict, db_dna: Optional[Dict]) -> Dict:
        """Fusionne DNA JSON et DB."""
        merged = json_dna.copy()
        
        if db_dna:
            # Ajouter/overrider avec données DB
            for key, value in db_dna.items():
                if value is not None:
                    # Préfixer les colonnes DB pour éviter conflits
                    if key not in merged:
                        merged[key] = value
                    else:
                        merged[f"db_{key}"] = value
        
        return merged
    
    # ─── API PUBLIQUE ───
    
    def get_team_dna(self, team_name: str, use_cache: bool = True) -> Optional[TeamDNA]:
        """
        Charge le DNA complet d'une équipe.
        
        Args:
            team_name: Nom de l'équipe
            use_cache: Utiliser le cache (défaut: True)
        
        Returns:
            TeamDNA ou None si non trouvé
        """
        # Cache
        if use_cache and team_name in self._team_dna_cache:
            return self._team_dna_cache[team_name]
        
        # Charger JSON
        json_data = self._load_json_team_dna()
        json_dna = json_data.get(team_name)
        
        # Fuzzy match si pas trouvé
        if not json_dna:
            for name, data in json_data.items():
                if team_name.lower() in name.lower() or name.lower() in team_name.lower():
                    json_dna = data
                    break
        
        if not json_dna:
            logger.warning(f"⚠️ Équipe non trouvée: {team_name}")
            return None
        
        self._load_stats["teams_from_json"] += 1
        
        # Charger DB (enrichissement)
        db_dna = self._load_db_team_dna(team_name)
        
        # Fusionner
        merged = self._merge_dna(json_dna, db_dna)
        
        # Créer TeamDNA
        source = "HYBRID" if db_dna else "JSON"
        if db_dna:
            self._load_stats["teams_hybrid"] += 1
        
        team_dna = TeamDNA(
            team_name=team_name,
            league=json_dna.get("league", ""),
            base_dna=json_dna,
            db_dna=db_dna or {},
            merged_dna=merged,
            source=source,
            data_quality=1.0 if db_dna else 0.8
        )
        
        # Cache
        self._team_dna_cache[team_name] = team_dna
        
        return team_dna
    
    def get_goalkeeper_dna(self, gk_name: str = None, team_name: str = None) -> Optional[GoalkeeperDNA]:
        """
        Charge le DNA d'un gardien.
        
        Args:
            gk_name: Nom du gardien (optionnel)
            team_name: Nom de l'équipe (trouve le GK titulaire)
        
        Returns:
            GoalkeeperDNA ou None
        """
        gk_data = self._load_json_gk_dna()
        
        profile = None
        found_gk_name = gk_name
        
        # Recherche par nom de gardien
        if gk_name and gk_name in gk_data:
            profile = gk_data[gk_name]
            found_gk_name = gk_name
        
        # Recherche par équipe (utilise l'index team:TeamName)
        elif team_name:
            # D'abord essayer l'index direct
            team_key = f"team:{team_name}"
            if team_key in gk_data:
                profile = gk_data[team_key]
                found_gk_name = profile.get("goalkeeper", "")
            else:
                # Recherche fuzzy par équipe
                for key, data in gk_data.items():
                    if key.startswith("team:"):
                        continue  # Skip les index
                    if data.get("team", "").lower() == team_name.lower():
                        profile = data
                        found_gk_name = data.get("goalkeeper", "")
                        break
        
        if not profile:
            return None
        
        self._load_stats["gk_loaded"] += 1
        
        return GoalkeeperDNA(
            gk_name=found_gk_name,
            team_name=profile.get("team", team_name or ""),
            profile=profile,
            panic_score=profile.get("panic_score", 0.0),
            timing_profile=profile.get("timing_analysis", {}).get("pattern", "CONSISTENT") if isinstance(profile.get("timing_analysis"), dict) else "CONSISTENT",
            exploit_paths=profile.get("exploit_paths", profile.get("exploits", []))
        )

    def get_defense_dna(self, team_name: str) -> Optional[DefenseDNA]:
        """
        Charge le DNA défensif d'une équipe.
        
        Args:
            team_name: Nom de l'équipe
        
        Returns:
            DefenseDNA ou None
        """
        defense_data = self._load_json_defense_dna()
        
        # Chercher l'équipe
        profile = None
        for team in defense_data:
            if team.get("team_name", "").lower() == team_name.lower():
                profile = team
                break
            if team_name.lower() in team.get("team_name", "").lower():
                profile = team
                break
        
        if not profile:
            return None
        
        self._load_stats["defense_loaded"] += 1
        
        return DefenseDNA(
            team_name=profile.get("team_name", team_name),
            profile=profile,
            percentiles=profile.get("percentiles", {}),
            weaknesses=profile.get("relative_weaknesses", []),
            strengths=profile.get("relative_strengths", []),
            exploit_paths=profile.get("exploit_paths", [])
        )
    
    def get_match_data(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Charge toutes les données DNA pour un match.
        
        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
        
        Returns:
            Dict avec home_dna, away_dna, home_gk, away_gk, home_defense, away_defense
        """
        return {
            "home_dna": self.get_team_dna(home_team),
            "away_dna": self.get_team_dna(away_team),
            "home_gk": self.get_goalkeeper_dna(team_name=home_team),
            "away_gk": self.get_goalkeeper_dna(team_name=away_team),
            "home_defense": self.get_defense_dna(home_team),
            "away_defense": self.get_defense_dna(away_team),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de chargement."""
        return {
            **self._load_stats,
            "cache_size": len(self._team_dna_cache),
            "json_teams_loaded": len(self._json_team_dna or {}),
            "json_gk_loaded": len(self._json_gk_dna or {}),
            "json_defense_loaded": len(self._json_defense_dna or []),
        }
    
    def clear_cache(self):
        """Vide le cache."""
        self._team_dna_cache.clear()
        self._gk_dna_cache.clear()
        self._defense_dna_cache.clear()


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_loader_instance: Optional[HybridDNALoader] = None

def get_hybrid_loader() -> HybridDNALoader:
    """Retourne l'instance singleton du loader."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = HybridDNALoader()
    return _loader_instance


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🧬 HYBRID DNA LOADER - TEST")
    print("=" * 60)
    
    loader = get_hybrid_loader()
    
    # Test Team DNA
    print("\n📊 Test Team DNA (Liverpool):")
    liverpool = loader.get_team_dna("Liverpool")
    if liverpool:
        print(f"   ✅ Trouvé: {liverpool.team_name}")
        print(f"   📦 Source: {liverpool.source}")
        print(f"   📊 Clés DNA: {len(liverpool.merged_dna)}")
        print(f"   🔑 Exemples: {list(liverpool.merged_dna.keys())[:5]}")
    else:
        print("   ❌ Non trouvé")
    
    # Test GK DNA
    print("\n🧤 Test Goalkeeper DNA (Arsenal):")
    gk = loader.get_goalkeeper_dna(team_name="Arsenal")
    if gk:
        print(f"   ✅ Trouvé: {gk.gk_name}")
        print(f"   📊 Panic Score: {gk.panic_score}")
        print(f"   ⏱️  Timing: {gk.timing_profile}")
    else:
        print("   ❌ Non trouvé")
    
    # Test Defense DNA
    print("\n🛡️  Test Defense DNA (Manchester City):")
    defense = loader.get_defense_dna("Manchester City")
    if defense:
        print(f"   ✅ Trouvé: {defense.team_name}")
        print(f"   📊 Percentiles: {len(defense.percentiles)} dimensions")
        print(f"   ⚠️  Faiblesses: {len(defense.weaknesses)}")
        print(f"   💪 Forces: {len(defense.strengths)}")
    else:
        print("   ❌ Non trouvé")
    
    # Test Match Data
    print("\n⚽ Test Match Data (Liverpool vs Arsenal):")
    match_data = loader.get_match_data("Liverpool", "Arsenal")
    for key, value in match_data.items():
        status = "✅" if value else "❌"
        print(f"   {status} {key}")
    
    # Stats
    print("\n📈 Statistiques:")
    stats = loader.get_stats()
    for key, value in stats.items():
        print(f"   • {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ HYBRID DNA LOADER TEST COMPLET")
    print("=" * 60)

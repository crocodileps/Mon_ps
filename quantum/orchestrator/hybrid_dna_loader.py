"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    HYBRID DNA LOADER - HEDGE FUND GRADE                       ║
║                                                                               ║
║  Fusionne les données de:                                                     ║
║  - DB: quantum.team_quantum_dna_v3 (betting, cards, corners, status)         ║
║  - JSON: team_dna_unified_v3.json (tactical, exploits, defense 231 métriques)║
║                                                                               ║
║  Résultat: ADN UNIQUE COMPLET pour quantum_orchestrator_v1                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import asyncpg

logger = logging.getLogger(__name__)

# Chemins
JSON_PATH = Path("/home/Mon_ps/data/quantum_v2/team_dna_unified_v3.json")
DB_CONFIG = {
    "host": "localhost",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

class HybridDNALoader:
    """
    Charge et fusionne les données DNA depuis DB + JSON.

    Usage:
        loader = HybridDNALoader()
        await loader.initialize()
        dna = await loader.load_team_dna("Liverpool")
    """

    def __init__(self):
        self._json_data: Optional[Dict] = None
        self._db_pool: Optional[asyncpg.Pool] = None
        self._team_name_mapping: Dict[str, str] = {}  # JSON name -> DB name

    async def initialize(self):
        """Initialise les connexions DB et charge le JSON."""
        # Charger JSON
        await self._load_json()

        # Créer pool DB
        self._db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)

        # Créer mapping noms (JSON peut avoir des noms différents de DB)
        await self._build_name_mapping()

        logger.info(f"HybridDNALoader initialized: {len(self._json_data.get('teams', {}))} teams JSON, DB pool ready")

    async def _load_json(self):
        """Charge le fichier JSON."""
        with open(JSON_PATH, 'r') as f:
            self._json_data = json.load(f)
        logger.info(f"JSON loaded: {JSON_PATH}")

    async def _build_name_mapping(self):
        """Construit le mapping entre noms JSON et noms DB."""
        # Récupérer noms DB
        async with self._db_pool.acquire() as conn:
            db_names = await conn.fetch("SELECT team_name FROM quantum.team_quantum_dna_v3")
            db_names = {row['team_name'].lower(): row['team_name'] for row in db_names}

        # Mapper JSON -> DB
        json_teams = self._json_data.get('teams', {})
        for json_name in json_teams.keys():
            # Essayer correspondance directe
            json_lower = json_name.lower().replace('-', ' ').replace('_', ' ')

            # Chercher dans DB
            for db_lower, db_original in db_names.items():
                if json_lower == db_lower or json_lower in db_lower or db_lower in json_lower:
                    self._team_name_mapping[json_name] = db_original
                    break

        logger.info(f"Name mapping built: {len(self._team_name_mapping)} teams mapped")

    async def load_team_dna(self, team_name: str) -> Dict[str, Any]:
        """
        Charge l'ADN complet d'une équipe (DB + JSON fusionnés).

        Returns:
            Dict avec toutes les données DNA fusionnées
        """
        result = {
            "team_name": team_name,
            "source": "hybrid",
            "db_data": {},
            "json_data": {},
            "merged": {}
        }

        # 1. Charger depuis DB
        db_data = await self._load_from_db(team_name)
        result["db_data"] = db_data or {}

        # 2. Charger depuis JSON
        json_data = self._load_from_json(team_name)
        result["json_data"] = json_data or {}

        # 3. Fusionner (DB prioritaire pour betting, JSON pour tactical)
        result["merged"] = self._merge_dna(db_data, json_data)

        logger.info(f"DNA loaded for {team_name}: DB={bool(db_data)}, JSON={bool(json_data)}")

        return result

    async def _load_from_db(self, team_name: str) -> Optional[Dict]:
        """Charge depuis quantum.team_quantum_dna_v3."""
        async with self._db_pool.acquire() as conn:
            # Recherche flexible (ILIKE)
            row = await conn.fetchrow("""
                SELECT * FROM quantum.team_quantum_dna_v3
                WHERE team_name ILIKE $1 OR team_name ILIKE $2
                LIMIT 1
            """, team_name, f"%{team_name}%")

            if row:
                return dict(row)
        return None

    def _load_from_json(self, team_name: str) -> Optional[Dict]:
        """Charge depuis team_dna_unified_v3.json."""
        teams = self._json_data.get('teams', {})

        # Recherche directe
        if team_name in teams:
            return teams[team_name]

        # Recherche flexible
        team_lower = team_name.lower()
        for json_name, data in teams.items():
            if team_lower in json_name.lower() or json_name.lower() in team_lower:
                return data

        return None

    def _merge_dna(self, db_data: Optional[Dict], json_data: Optional[Dict]) -> Dict[str, Any]:
        """
        Fusionne DB + JSON en ADN unique.

        Priorités:
        - DB: betting_performance, card_dna, corner_dna, status_2025_2026
        - JSON: defense (131), tactical, exploit, fbref
        """
        merged = {}

        # === DB DATA (betting/performance) ===
        if db_data:
            merged["betting_performance"] = {
                "best_strategy": db_data.get("best_strategy"),
                "total_bets": db_data.get("total_bets"),
                "total_wins": db_data.get("total_wins"),
                "win_rate": db_data.get("win_rate"),
                "total_pnl": db_data.get("total_pnl"),
                "roi": db_data.get("roi"),
                "unlucky_losses": db_data.get("unlucky_losses"),
            }
            merged["card_dna"] = db_data.get("card_dna", {})
            merged["corner_dna"] = db_data.get("corner_dna", {})
            merged["status_2025_2026"] = db_data.get("status_2025_2026", {})
            merged["tier"] = db_data.get("tier")
            merged["league"] = db_data.get("league")
            merged["current_style"] = db_data.get("current_style")
            merged["team_archetype"] = db_data.get("team_archetype")
            merged["tier_rank"] = db_data.get("tier_rank")
            merged["style_confidence"] = db_data.get("style_confidence")
            merged["unlucky_pct"] = db_data.get("unlucky_pct")
            merged["team_id"] = db_data.get("team_id")
            merged["avg_clv"] = db_data.get("avg_clv")
            merged["dna_fingerprint"] = db_data.get("dna_fingerprint")
            merged["season"] = db_data.get("season")
            merged["created_at"] = str(db_data.get("created_at")) if db_data.get("created_at") else None
            merged["updated_at"] = str(db_data.get("updated_at")) if db_data.get("updated_at") else None


            # DNA vectors from DB
            merged["market_dna_db"] = db_data.get("market_dna", {})
            merged["context_dna_db"] = db_data.get("context_dna", {})
            merged["temporal_dna_db"] = db_data.get("temporal_dna", {})
            merged["nemesis_dna_db"] = db_data.get("nemesis_dna", {})
            merged["psyche_dna_db"] = db_data.get("psyche_dna", {})
            merged["roster_dna_db"] = db_data.get("roster_dna", {})
            merged["physical_dna_db"] = db_data.get("physical_dna", {})
            merged["luck_dna_db"] = db_data.get("luck_dna", {})
            merged["chameleon_dna_db"] = db_data.get("chameleon_dna", {})

        # === JSON DATA (tactical/analysis) ===
        if json_data:
            merged["defense"] = json_data.get("defense", {})  # 131 métriques
            merged["tactical"] = json_data.get("tactical", {})  # gamestate_behavior, friction
            merged["exploit"] = json_data.get("exploit", {})  # vulnerabilities, exploit_paths
            merged["fbref"] = json_data.get("fbref", {})  # stats avancées
            merged["defensive_line"] = json_data.get("defensive_line", {})
            merged["betting_json"] = json_data.get("betting", {})  # gamestate_insights
            merged["context_json"] = json_data.get("context", {})

        return merged

    async def close(self):
        """Ferme les connexions."""
        if self._db_pool:
            await self._db_pool.close()


# === TEST ===
async def test_loader():
    """Test du loader hybride."""
    logging.basicConfig(level=logging.INFO)

    loader = HybridDNALoader()
    await loader.initialize()

    # Test Liverpool
    dna = await loader.load_team_dna("Liverpool")

    print("=" * 60)
    print("TEST HYBRID DNA LOADER")
    print("=" * 60)
    print(f"\nEquipe: {dna['team_name']}")
    print(f"Source: {dna['source']}")
    print(f"\n[DB] Data present: {bool(dna['db_data'])}")
    if dna['db_data']:
        print(f"[DB] Colonnes: {len(dna['db_data'])}")
    print(f"\n[JSON] Data present: {bool(dna['json_data'])}")
    if dna['json_data']:
        print(f"[JSON] Categories: {list(dna['json_data'].keys())}")
    print(f"\n[MERGED] Keys: {list(dna['merged'].keys())}")

    if dna['merged'].get('betting_performance'):
        bp = dna['merged']['betting_performance']
        print(f"\n BETTING PERFORMANCE:")
        print(f"   ROI: {bp.get('roi')}%")
        print(f"   Win Rate: {bp.get('win_rate')}%")
        print(f"   Best Strategy: {bp.get('best_strategy')}")
        print(f"   PnL: {bp.get('total_pnl')}u")

    if dna['merged'].get('exploit'):
        exp = dna['merged']['exploit']
        print(f"\n EXPLOIT DATA:")
        vulns = exp.get('vulnerabilities', [])
        print(f"   Vulnerabilities: {vulns[:3] if vulns else 'None'}")

    if dna['merged'].get('tactical'):
        tac = dna['merged']['tactical']
        print(f"\n TACTICAL DATA:")
        print(f"   Gamestate Behavior: {tac.get('gamestate_behavior', 'N/A')}")
        print(f"   Defensive Style: {tac.get('defensive_style', 'N/A')}")

    if dna['merged'].get('defense'):
        print(f"\n DEFENSE: {len(dna['merged']['defense'])} metriques")

    if dna['merged'].get('card_dna'):
        card = dna['merged']['card_dna']
        if isinstance(card, dict):
            print(f"\n CARD DNA: {list(card.keys())[:5]}")
        else:
            print(f"\n CARD DNA: {type(card).__name__}")

    if dna['merged'].get('corner_dna'):
        corner = dna['merged']['corner_dna']
        if isinstance(corner, dict):
            print(f"\n CORNER DNA: {list(corner.keys())[:5]}")
        else:
            print(f"\n CORNER DNA: {type(corner).__name__}")

    await loader.close()
    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_loader())

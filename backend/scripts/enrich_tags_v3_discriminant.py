#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
PHASE 5.2 V3 - ENRICHISSEMENT TAGS DISCRIMINANTS
═══════════════════════════════════════════════════════════════════════════════

Objectif: Enrichir narrative_fingerprint_tags avec 9 tags discriminants
Méthode: Approche QUANT (remplacer par catégorie, garder le reste)

Sources:
  - team_dna_unified_v2.json (96 équipes, 231 métriques)
  - players_impact_dna.json (2333 joueurs)

Tags générés (9):
  GAMESTATE (4): COLLAPSE_LEADER, COMEBACK_KING, NEUTRAL, FAST_STARTER
  GOALKEEPER (3): GK_ELITE, GK_SOLID, GK_LEAKY
  MVP (2): MVP_DEPENDENT, COLLECTIVE

Thresholds (calculés sur données réelles P25/P75):
  - GK: P25=64.3%, P75=72.1%
  - MVP: P25=22.2%, P75=30.8%

Méthodologie Hedge Fund:
  1. NE JAMAIS INVENTER de données
  2. THRESHOLDS sur percentiles réels
  3. VALIDATION distribution (10-50% par tag)
  4. BACKUP obligatoire avant modification

Auteur: Claude + Mya
Date: 2025-12-17
Session: #57
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import psycopg2
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Chemins fichiers (validés Étape 1)
TEAM_DNA_PATH = "/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json"
PLAYERS_DNA_PATH = "/home/Mon_ps/data/quantum_v2/players_impact_dna.json"

# Connexion PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Thresholds P25/P75 (calculés Étape 1 sur données réelles)
THRESHOLDS = {
    "gk_save_rate": {
        "p25": 64.3,  # < P25 = GK_LEAKY
        "p75": 72.1   # > P75 = GK_ELITE
    },
    "mvp_dependency": {
        "p25": 22.2,  # < P25 = COLLECTIVE
        "p75": 30.8   # > P75 = MVP_DEPENDENT
    }
}

# Tags par catégorie (pour logique QUANT de remplacement)
GAMESTATE_TAGS = ["COLLAPSE_LEADER", "COMEBACK_KING", "NEUTRAL", "FAST_STARTER", "SLOW_STARTER", "CLOSER"]
GK_STATUS_TAGS = ["GK_ELITE", "GK_SOLID", "GK_AVERAGE", "GK_LEAKY"]
MVP_STATUS_TAGS = ["MVP_DEPENDENT", "COLLECTIVE"]

# Tags gamestate valides (discriminants 10-50%)
VALID_GAMESTATE = ["COLLAPSE_LEADER", "COMEBACK_KING", "NEUTRAL", "FAST_STARTER"]

# Mapping noms équipes JSON → DB (hérité Phase 5.1)
NAME_MAPPING = {
    "Paris Saint-Germain": "Paris Saint Germain",
    "Paris Saint Germain": "Paris Saint Germain",
    "Wolverhampton Wanderers": "Wolverhampton",
    "West Ham United": "West Ham",
    "Tottenham Hotspur": "Tottenham",
    "Newcastle United": "Newcastle",
    "Manchester United": "Manchester Utd",
    "Manchester City": "Manchester City",
    "Leicester City": "Leicester",
    "Leeds United": "Leeds",
    "Brighton & Hove Albion": "Brighton",
    "AFC Bournemouth": "Bournemouth",
}


# ═══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def load_team_dna_unified() -> Dict:
    """Charger team_dna_unified_v2.json (source de vérité)."""
    print(f"\n📂 Chargement {TEAM_DNA_PATH}...")
    with open(TEAM_DNA_PATH, 'r') as f:
        data = json.load(f)
    teams = data.get('teams', data)
    print(f"   ✅ {len(teams)} équipes chargées")
    return teams


def load_players_impact() -> List[Dict]:
    """Charger players_impact_dna.json pour calcul MVP dependency."""
    print(f"\n📂 Chargement {PLAYERS_DNA_PATH}...")
    with open(PLAYERS_DNA_PATH, 'r') as f:
        data = json.load(f)
    print(f"   ✅ {len(data)} joueurs chargés")
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_mvp_dependency(team_name: str, players: List[Dict]) -> Optional[float]:
    """
    Calculer MVP dependency = % buts du top scorer.
    
    Args:
        team_name: Nom équipe (format DB ou JSON)
        players: Liste joueurs depuis players_impact_dna.json
    
    Returns:
        Pourcentage (0-100) ou None si pas de données
    """
    # Essayer différentes variantes du nom
    variants = [team_name]
    if team_name in NAME_MAPPING:
        variants.append(NAME_MAPPING[team_name])
    # Ajouter variante inverse
    for json_name, db_name in NAME_MAPPING.items():
        if db_name == team_name:
            variants.append(json_name)
    
    # Filtrer joueurs de l'équipe
    team_players = []
    for p in players:
        player_team = p.get('team', '')
        if any(variant.lower() in player_team.lower() for variant in variants):
            team_players.append(p)
    
    if not team_players:
        return None
    
    # Calculer total buts
    total_goals = sum(p.get('goals', 0) for p in team_players)
    if total_goals == 0:
        return None
    
    # Top scorer
    top_scorer_goals = max(p.get('goals', 0) for p in team_players)
    
    return (top_scorer_goals / total_goals) * 100


def extract_discriminant_tags(team_data: Dict, mvp_pct: Optional[float]) -> List[str]:
    """
    Extraire tags discriminants depuis données équipe.
    
    Tags extraits (9):
    - GAMESTATE (4): COLLAPSE_LEADER, COMEBACK_KING, NEUTRAL, FAST_STARTER
    - GOALKEEPER (3): GK_ELITE, GK_SOLID, GK_LEAKY
    - MVP (2): MVP_DEPENDENT, COLLECTIVE
    
    Args:
        team_data: Dict depuis team_dna_unified_v2.json
        mvp_pct: MVP dependency % (depuis players_impact_dna.json)
    
    Returns:
        Liste de tags discriminants
    """
    tags = []
    
    # ─────────────────────────────────────────────────────────────────
    # 1. GAMESTATE (depuis tactical.gamestate_behavior)
    # ─────────────────────────────────────────────────────────────────
    gamestate = team_data.get("tactical", {}).get("gamestate_behavior")
    if gamestate and gamestate in VALID_GAMESTATE:
        tags.append(gamestate)
    
    # ─────────────────────────────────────────────────────────────────
    # 2. GOALKEEPER (depuis defensive_line.goalkeeper.save_rate)
    # ─────────────────────────────────────────────────────────────────
    save_rate = (team_data.get("defensive_line", {})
                 .get("goalkeeper", {})
                 .get("save_rate"))
    
    if save_rate is not None and isinstance(save_rate, (int, float)):
        if save_rate > THRESHOLDS["gk_save_rate"]["p75"]:
            tags.append("GK_ELITE")
        elif save_rate < THRESHOLDS["gk_save_rate"]["p25"]:
            tags.append("GK_LEAKY")
        else:
            tags.append("GK_SOLID")
    
    # ─────────────────────────────────────────────────────────────────
    # 3. MVP DEPENDENCY (depuis players_impact_dna.json)
    # ─────────────────────────────────────────────────────────────────
    if mvp_pct is not None:
        if mvp_pct > THRESHOLDS["mvp_dependency"]["p75"]:
            tags.append("MVP_DEPENDENT")
        elif mvp_pct < THRESHOLDS["mvp_dependency"]["p25"]:
            tags.append("COLLECTIVE")
        # Entre P25 et P75 = pas de tag MVP (normal)
    
    return tags


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIQUE QUANT - FUSION TAGS
# ═══════════════════════════════════════════════════════════════════════════════

def is_recalculated_tag(tag: str) -> bool:
    """Vérifier si un tag appartient aux catégories recalculées."""
    return (tag in GAMESTATE_TAGS or 
            tag in GK_STATUS_TAGS or 
            tag in MVP_STATUS_TAGS)


def merge_tags_quant(old_tags: List[str], new_tags: List[str]) -> List[str]:
    """
    Fusion intelligente QUANT: remplacer par catégorie, garder le reste.
    
    Exemple:
        old_tags = ["GEGENPRESS", "GK_SOLID", "GK_Alisson", "MVP_Salah"]
        new_tags = ["COMEBACK_KING", "GK_LEAKY", "MVP_DEPENDENT"]
        
        Résultat:
        - GEGENPRESS: gardé (tactical profile, pas recalculé)
        - GK_SOLID: supprimé (GK_STATUS recalculé → GK_LEAKY)
        - GK_Alisson: gardé (nom GK, pas status)
        - MVP_Salah: gardé (nom MVP, pas status)
        - COMEBACK_KING: ajouté (GAMESTATE)
        - GK_LEAKY: ajouté (remplace GK_SOLID)
        - MVP_DEPENDENT: ajouté (MVP_STATUS)
        
        → ["GEGENPRESS", "GK_Alisson", "MVP_Salah", "COMEBACK_KING", "GK_LEAKY", "MVP_DEPENDENT"]
    """
    # 1. Garder les anciens tags NON recalculés
    kept_tags = [tag for tag in old_tags if not is_recalculated_tag(tag)]
    
    # 2. Ajouter les nouveaux tags
    merged = kept_tags + new_tags
    
    # 3. Dédupliquer (préserver l'ordre)
    seen = set()
    result = []
    for tag in merged:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def get_db_connection():
    """Connexion PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def get_current_tags(conn, team_name: str) -> List[str]:
    """Récupérer tags actuels d'une équipe."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT narrative_fingerprint_tags
        FROM quantum.team_quantum_dna_v3
        WHERE team_name = %s
    """, (team_name,))
    
    row = cursor.fetchone()
    if row and row[0]:
        return list(row[0])
    return []


def get_all_db_teams(conn) -> List[str]:
    """Récupérer tous les noms d'équipes en DB."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team_name FROM quantum.team_quantum_dna_v3
        ORDER BY team_name
    """)
    return [row[0] for row in cursor.fetchall()]


def update_team_tags(conn, team_name: str, tags: List[str]) -> bool:
    """
    UPDATE tags pour une équipe.
    
    Returns:
        True si update effectué, False sinon
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE quantum.team_quantum_dna_v3
        SET narrative_fingerprint_tags = %s,
            updated_at = NOW()
        WHERE team_name = %s
    """, (tags, team_name))
    
    return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_distribution(conn) -> Dict[str, Tuple[int, float]]:
    """
    Valider distribution tags (objectif: 10-50% par tag discriminant).
    
    Returns:
        Dict[tag] = (count, percentage)
    """
    cursor = conn.cursor()
    
    # Compter total équipes
    cursor.execute("SELECT COUNT(*) FROM quantum.team_quantum_dna_v3")
    total = cursor.fetchone()[0]
    
    # Distribution par tag
    cursor.execute("""
        SELECT unnest(narrative_fingerprint_tags) as tag, COUNT(*) as cnt
        FROM quantum.team_quantum_dna_v3
        GROUP BY tag
        ORDER BY cnt DESC
    """)
    
    distribution = {}
    for tag, count in cursor.fetchall():
        pct = (count / total) * 100
        distribution[tag] = (count, pct)
    
    return distribution


def print_validation_report(distribution: Dict[str, Tuple[int, float]], total_teams: int):
    """Afficher rapport de validation."""
    print("\n" + "="*70)
    print("📊 VALIDATION DISTRIBUTION TAGS (objectif: 10-50%)")
    print("="*70)
    
    # Séparer par catégorie
    categories = {
        "GAMESTATE": GAMESTATE_TAGS,
        "GK_STATUS": GK_STATUS_TAGS,
        "MVP_STATUS": MVP_STATUS_TAGS,
        "AUTRES": []
    }
    
    for tag, (count, pct) in distribution.items():
        found = False
        for cat, tags in categories.items():
            if cat != "AUTRES" and tag in tags:
                found = True
                break
        if not found:
            categories["AUTRES"].append(tag)
    
    for cat_name in ["GAMESTATE", "GK_STATUS", "MVP_STATUS", "AUTRES"]:
        cat_tags = categories[cat_name]
        if cat_name == "AUTRES":
            cat_tags = [t for t in distribution.keys() if t in cat_tags or 
                       (t not in GAMESTATE_TAGS and t not in GK_STATUS_TAGS and t not in MVP_STATUS_TAGS)]
        
        if not cat_tags:
            continue
            
        print(f"\n📁 {cat_name}:")
        for tag in cat_tags:
            if tag in distribution:
                count, pct = distribution[tag]
                if 10 <= pct <= 50:
                    status = "✅"
                elif pct < 10:
                    status = "⚠️ <10%"
                else:
                    status = "⚠️ >50%"
                print(f"   {status} {tag:20s}: {count:3d} équipes ({pct:5.1f}%)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Exécution principale Phase 5.2 V3.
    """
    print("="*70)
    print("🚀 PHASE 5.2 V3 - ENRICHISSEMENT TAGS DISCRIMINANTS")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Méthodologie: Approche QUANT (remplacer par catégorie)")
    
    # ─────────────────────────────────────────────────────────────────
    # 1. CHARGER DONNÉES
    # ─────────────────────────────────────────────────────────────────
    teams_data = load_team_dna_unified()
    players_data = load_players_impact()
    
    # ─────────────────────────────────────────────────────────────────
    # 2. CONNEXION DB
    # ─────────────────────────────────────────────────────────────────
    print(f"\n📂 Connexion PostgreSQL...")
    conn = get_db_connection()
    db_teams = get_all_db_teams(conn)
    print(f"   ✅ {len(db_teams)} équipes en DB")
    
    # ─────────────────────────────────────────────────────────────────
    # 3. TRAITEMENT ÉQUIPE PAR ÉQUIPE
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("🔄 ENRICHISSEMENT TAGS")
    print("="*70)
    
    stats = {
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "not_found_json": []
    }
    
    for db_team in db_teams:
        # Trouver équipe dans JSON (avec mapping)
        json_team = None
        json_data = None
        
        # Essayer nom direct
        if db_team in teams_data:
            json_team = db_team
            json_data = teams_data[db_team]
        else:
            # Essayer avec mapping inverse
            for json_name, mapped_name in NAME_MAPPING.items():
                if mapped_name == db_team and json_name in teams_data:
                    json_team = json_name
                    json_data = teams_data[json_name]
                    break
        
        if not json_data:
            stats["not_found_json"].append(db_team)
            stats["skipped"] += 1
            continue
        
        stats["processed"] += 1
        
        # Calculer MVP dependency
        mvp_pct = calculate_mvp_dependency(db_team, players_data)
        
        # Extraire nouveaux tags discriminants
        new_tags = extract_discriminant_tags(json_data, mvp_pct)
        
        # Récupérer tags actuels
        old_tags = get_current_tags(conn, db_team)
        
        # Fusionner (approche QUANT)
        merged_tags = merge_tags_quant(old_tags, new_tags)
        
        # UPDATE DB
        if update_team_tags(conn, db_team, merged_tags):
            stats["updated"] += 1
            # Afficher détails
            added = [t for t in merged_tags if t not in old_tags]
            removed = [t for t in old_tags if t not in merged_tags]
            print(f"   ✅ {db_team:25s}: {len(merged_tags)} tags", end="")
            if added:
                print(f" [+{','.join(added)}]", end="")
            if removed:
                print(f" [-{','.join(removed)}]", end="")
            print()
    
    # ─────────────────────────────────────────────────────────────────
    # 4. COMMIT
    # ─────────────────────────────────────────────────────────────────
    conn.commit()
    
    # ─────────────────────────────────────────────────────────────────
    # 5. VALIDATION
    # ─────────────────────────────────────────────────────────────────
    distribution = validate_distribution(conn)
    print_validation_report(distribution, len(db_teams))
    
    # ─────────────────────────────────────────────────────────────────
    # 6. RÉSUMÉ FINAL
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("📊 RÉSUMÉ PHASE 5.2 V3")
    print("="*70)
    print(f"   Équipes traitées: {stats['processed']}")
    print(f"   Équipes mises à jour: {stats['updated']}")
    print(f"   Équipes ignorées (pas dans JSON): {stats['skipped']}")
    
    if stats["not_found_json"]:
        print(f"\n   ⚠️ Équipes DB non trouvées dans JSON ({len(stats['not_found_json'])}):")
        for team in stats["not_found_json"][:10]:
            print(f"      - {team}")
        if len(stats["not_found_json"]) > 10:
            print(f"      ... et {len(stats['not_found_json']) - 10} autres")
    
    # Moyenne tags/équipe
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(array_length(narrative_fingerprint_tags, 1))
        FROM quantum.team_quantum_dna_v3
        WHERE narrative_fingerprint_tags IS NOT NULL
    """)
    avg_tags = cursor.fetchone()[0]
    print(f"\n   📈 Moyenne tags/équipe: {avg_tags:.2f}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ PHASE 5.2 V3 TERMINÉE AVEC SUCCÈS")
    print("="*70)


if __name__ == "__main__":
    main()

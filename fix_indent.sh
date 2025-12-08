#!/bin/bash
# Restaurer le backup et appliquer le patch correctement

BASE_DIR="/home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1_modular"
BACKUP_DIR=$(ls -td ${BASE_DIR}/backup_* | head -1)

echo "🔄 Restauration du backup..."
cp "$BACKUP_DIR/database_adapter.py" "$BASE_DIR/adapters/"
cp "$BACKUP_DIR/odds_loader.py" "$BASE_DIR/adapters/"
echo "✅ Fichiers restaurés"

# Maintenant ajouter le patch SANS indentation incorrecte
echo "🔧 Application du patch corrigé..."

# Ajouter à la FIN de database_adapter.py (niveau classe)
cat >> "$BASE_DIR/adapters/database_adapter.py" << 'PATCH'


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 BTTS FUSION 3 SOURCES (ajouté par patch)
# ═══════════════════════════════════════════════════════════════════════════════

BTTS_SOURCE_WEIGHTS = {
    'tactical_matrix': 0.40,
    'team_xg_tendencies': 0.35,
    'match_xg_stats': 0.25,
}

async def get_tactical_btts(pool, home_style: str, away_style: str):
    """Récupère BTTS depuis tactical_matrix"""
    query = """
    SELECT btts_probability, over25_probability
    FROM tactical_matrix
    WHERE LOWER(style_home) = LOWER($1) AND LOWER(style_away) = LOWER($2)
    LIMIT 1
    """
    try:
        row = await pool.fetchrow(query, home_style, away_style)
        if row:
            return {
                'btts_probability': float(row.get('btts_probability', 50) or 50) / 100,
                'over25_probability': float(row.get('over25_probability', 50) or 50) / 100,
            }
        return None
    except Exception as e:
        print(f"Erreur get_tactical_btts: {e}")
        return None

async def get_team_xg_btts(pool, team_name: str):
    """Récupère BTTS depuis team_xg_tendencies (Understat)"""
    query = """
    SELECT btts_xg_rate, over25_xg_rate
    FROM team_xg_tendencies WHERE LOWER(team_name) = LOWER($1)
    LIMIT 1
    """
    try:
        row = await pool.fetchrow(query, team_name)
        if row:
            return {
                'btts_xg_rate': float(row.get('btts_xg_rate', 0.5) or 0.5),
                'over25_xg_rate': float(row.get('over25_xg_rate', 0.5) or 0.5),
            }
        return None
    except Exception as e:
        print(f"Erreur get_team_xg_btts: {e}")
        return None

async def get_h2h_btts(pool, home_team: str, away_team: str):
    """Récupère BTTS historique H2H depuis match_xg_stats"""
    query = """
    SELECT AVG(btts_expected) as btts_avg, COUNT(*) as matches
    FROM match_xg_stats
    WHERE (LOWER(home_team) = LOWER($1) AND LOWER(away_team) = LOWER($2))
       OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($4))
    """
    try:
        row = await pool.fetchrow(query, home_team, away_team, away_team, home_team)
        if row and row['matches'] and int(row['matches']) > 0:
            return {
                'btts_avg': float(row.get('btts_avg', 0.5) or 0.5),
                'matches': int(row['matches']),
            }
        return None
    except Exception as e:
        print(f"Erreur get_h2h_btts: {e}")
        return None

async def calculate_btts_probability(pool, home_team: str, away_team: str, 
                                     home_style: str = None, away_style: str = None):
    """
    🎯 FUSION des 3 sources BTTS
    final = tactical(40%) + team_xg(35%) + h2h(25%)
    """
    weights = BTTS_SOURCE_WEIGHTS
    btts_probs = []
    sources_used = []
    total_weight = 0
    
    # Source 1: Tactical Matrix (40%)
    if home_style and away_style:
        tactical = await get_tactical_btts(pool, home_style, away_style)
        if tactical:
            btts_probs.append((tactical['btts_probability'], weights['tactical_matrix']))
            sources_used.append('tactical_matrix')
            total_weight += weights['tactical_matrix']
    
    # Source 2: Team xG Tendencies (35%)
    home_xg = await get_team_xg_btts(pool, home_team)
    away_xg = await get_team_xg_btts(pool, away_team)
    if home_xg and away_xg:
        combined = (home_xg['btts_xg_rate'] + away_xg['btts_xg_rate']) / 2
        btts_probs.append((combined, weights['team_xg_tendencies']))
        sources_used.append('team_xg_tendencies')
        total_weight += weights['team_xg_tendencies']
    
    # Source 3: H2H Historical (25%)
    h2h = await get_h2h_btts(pool, home_team, away_team)
    if h2h and h2h['matches'] >= 2:
        btts_probs.append((h2h['btts_avg'], weights['match_xg_stats']))
        sources_used.append('match_xg_stats')
        total_weight += weights['match_xg_stats']
    
    # Fusion pondérée
    if btts_probs and total_weight > 0:
        btts_final = sum(p * w for p, w in btts_probs) / total_weight
    else:
        btts_final = 0.50
        sources_used.append('fallback')
    
    confidence = 'HIGH' if len(sources_used) >= 3 else ('MEDIUM' if len(sources_used) >= 2 else 'LOW')
    
    return {
        'btts_probability': round(btts_final, 3),
        'confidence': confidence,
        'sources_used': sources_used,
    }
PATCH

echo "✅ Patch database_adapter.py appliqué"

# Patch odds_loader.py
cat >> "$BASE_DIR/adapters/odds_loader.py" << 'PATCH2'


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 APPROXIMATION BTTS (ajouté par patch)
# ═══════════════════════════════════════════════════════════════════════════════

def approximate_btts_odds(over_25_odds: float) -> tuple:
    """
    Approxime les cotes BTTS depuis Over 2.5
    The Odds API ne supporte pas "btts" (erreur 422)
    Corrélation BTTS/Over2.5 ≈ 92%
    """
    if over_25_odds <= 1.0:
        return 0.0, 0.0
    
    BTTS_OVER25_RATIO = 0.92
    btts_yes = over_25_odds * BTTS_OVER25_RATIO
    btts_yes = max(btts_yes, 1.40)
    
    implied_yes = 1 / btts_yes
    implied_no = 1 - implied_yes + 0.05
    btts_no = 1 / max(implied_no, 0.30)
    btts_no = min(btts_no, 3.50)
    
    return round(btts_yes, 2), round(btts_no, 2)
PATCH2

echo "✅ Patch odds_loader.py appliqué"
echo ""
echo "🧪 Test de syntaxe..."
python3 -m py_compile "$BASE_DIR/adapters/database_adapter.py" && echo "✅ database_adapter.py OK" || echo "❌ Erreur syntaxe"
python3 -m py_compile "$BASE_DIR/adapters/odds_loader.py" && echo "✅ odds_loader.py OK" || echo "❌ Erreur syntaxe"

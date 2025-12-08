#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════
# SCRIPT D'APPLICATION DES PATCHES BTTS
# ═══════════════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   chmod +x apply_btts_patches.sh
#   ./apply_btts_patches.sh
#
# Ce script:
# 1. Sauvegarde les fichiers existants
# 2. Ajoute l'approximation BTTS dans odds_loader.py
# 3. Ajoute la fusion 3 sources dans database_adapter.py
# ═══════════════════════════════════════════════════════════════════════════════════════

set -e

BASE_DIR="/home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1_modular"
ADAPTERS_DIR="$BASE_DIR/adapters"
BACKUP_DIR="$BASE_DIR/backup_$(date +%Y%m%d_%H%M%S)"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  APPLICATION DES PATCHES BTTS                                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1: Backup
# ═══════════════════════════════════════════════════════════════════════════════════════
echo "📦 Backup des fichiers existants..."
mkdir -p "$BACKUP_DIR"
cp "$ADAPTERS_DIR/odds_loader.py" "$BACKUP_DIR/"
cp "$ADAPTERS_DIR/database_adapter.py" "$BACKUP_DIR/"
echo "   ✅ Backup créé: $BACKUP_DIR"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2: Vérifier si les patches sont déjà appliqués
# ═══════════════════════════════════════════════════════════════════════════════════════
echo "🔍 Vérification de l'état actuel..."

if grep -q "_approximate_btts_odds" "$ADAPTERS_DIR/odds_loader.py"; then
    echo "   ⚠️ odds_loader.py: approximation BTTS déjà présente"
    ODDS_PATCH_NEEDED=false
else
    echo "   📝 odds_loader.py: patch nécessaire"
    ODDS_PATCH_NEEDED=true
fi

if grep -q "calculate_btts_probability" "$ADAPTERS_DIR/database_adapter.py"; then
    echo "   ⚠️ database_adapter.py: fusion BTTS déjà présente"
    DB_PATCH_NEEDED=false
else
    echo "   📝 database_adapter.py: patch nécessaire"
    DB_PATCH_NEEDED=true
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3: Appliquer patch odds_loader.py
# ═══════════════════════════════════════════════════════════════════════════════════════
if [ "$ODDS_PATCH_NEEDED" = true ]; then
    echo "🔧 Application du patch odds_loader.py..."
    
    # Trouver la dernière méthode de la classe et ajouter après
    cat >> "$ADAPTERS_DIR/odds_loader.py" << 'ODDS_PATCH'

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🎯 APPROXIMATION BTTS (ajouté par patch)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _approximate_btts_odds(self, over_25_odds: float) -> tuple:
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
ODDS_PATCH

    echo "   ✅ Patch odds_loader.py appliqué"
else
    echo "   ⏭️ odds_loader.py: pas de modification nécessaire"
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 4: Appliquer patch database_adapter.py
# ═══════════════════════════════════════════════════════════════════════════════════════
if [ "$DB_PATCH_NEEDED" = true ]; then
    echo "🔧 Application du patch database_adapter.py..."
    
    cat >> "$ADAPTERS_DIR/database_adapter.py" << 'DB_PATCH'

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🎯 BTTS FUSION 3 SOURCES (ajouté par patch)
    # Poids: tactical(40%) + team_xg(35%) + h2h(25%) = 100%
    # ═══════════════════════════════════════════════════════════════════════════════
    
    BTTS_SOURCE_WEIGHTS = {
        'tactical_matrix': 0.40,
        'team_xg_tendencies': 0.35,
        'match_xg_stats': 0.25,
    }
    
    async def get_tactical_btts(self, home_style: str, away_style: str):
        """Récupère BTTS depuis tactical_matrix"""
        query = """
        SELECT btts_probability, over25_probability
        FROM tactical_matrix
        WHERE LOWER(style_home) = LOWER($1) AND LOWER(style_away) = LOWER($2)
        LIMIT 1
        """
        try:
            row = await self.pool.fetchrow(query, home_style, away_style)
            if row:
                return {
                    'btts_probability': float(row.get('btts_probability', 50) or 50) / 100,
                    'over25_probability': float(row.get('over25_probability', 50) or 50) / 100,
                }
            return None
        except Exception as e:
            logger.error(f"Erreur get_tactical_btts: {e}")
            return None
    
    async def get_team_xg_btts(self, team_name: str):
        """Récupère BTTS depuis team_xg_tendencies (Understat)"""
        query = """
        SELECT btts_xg_rate, over25_xg_rate
        FROM team_xg_tendencies WHERE LOWER(team_name) = LOWER($1)
        LIMIT 1
        """
        try:
            row = await self.pool.fetchrow(query, team_name)
            if row:
                return {
                    'btts_xg_rate': float(row.get('btts_xg_rate', 0.5) or 0.5),
                    'over25_xg_rate': float(row.get('over25_xg_rate', 0.5) or 0.5),
                }
            return None
        except Exception as e:
            logger.error(f"Erreur get_team_xg_btts: {e}")
            return None
    
    async def get_h2h_btts(self, home_team: str, away_team: str):
        """Récupère BTTS historique H2H depuis match_xg_stats"""
        query = """
        SELECT AVG(btts_expected) as btts_avg, COUNT(*) as matches
        FROM match_xg_stats
        WHERE (LOWER(home_team) = LOWER($1) AND LOWER(away_team) = LOWER($2))
           OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($4))
        """
        try:
            row = await self.pool.fetchrow(query, home_team, away_team, away_team, home_team)
            if row and row['matches'] and int(row['matches']) > 0:
                return {
                    'btts_avg': float(row.get('btts_avg', 0.5) or 0.5),
                    'matches': int(row['matches']),
                }
            return None
        except Exception as e:
            logger.error(f"Erreur get_h2h_btts: {e}")
            return None
    
    async def calculate_btts_probability(self, home_team: str, away_team: str, 
                                         home_style: str = None, away_style: str = None):
        """
        🎯 FUSION des 3 sources BTTS
        final = tactical(40%) + team_xg(35%) + h2h(25%)
        """
        weights = self.BTTS_SOURCE_WEIGHTS
        btts_probs = []
        sources_used = []
        total_weight = 0
        
        # Source 1: Tactical Matrix (40%)
        if home_style and away_style:
            tactical = await self.get_tactical_btts(home_style, away_style)
            if tactical:
                btts_probs.append((tactical['btts_probability'], weights['tactical_matrix']))
                sources_used.append('tactical_matrix')
                total_weight += weights['tactical_matrix']
        
        # Source 2: Team xG Tendencies (35%)
        home_xg = await self.get_team_xg_btts(home_team)
        away_xg = await self.get_team_xg_btts(away_team)
        if home_xg and away_xg:
            combined = (home_xg['btts_xg_rate'] + away_xg['btts_xg_rate']) / 2
            btts_probs.append((combined, weights['team_xg_tendencies']))
            sources_used.append('team_xg_tendencies')
            total_weight += weights['team_xg_tendencies']
        
        # Source 3: H2H Historical (25%)
        h2h = await self.get_h2h_btts(home_team, away_team)
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
DB_PATCH

    echo "   ✅ Patch database_adapter.py appliqué"
else
    echo "   ⏭️ database_adapter.py: pas de modification nécessaire"
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 5: Vérification
# ═══════════════════════════════════════════════════════════════════════════════════════
echo "🔍 Vérification finale..."

if grep -q "_approximate_btts_odds" "$ADAPTERS_DIR/odds_loader.py"; then
    echo "   ✅ odds_loader.py: approximation BTTS présente"
else
    echo "   ❌ odds_loader.py: ERREUR - patch non appliqué"
fi

if grep -q "calculate_btts_probability" "$ADAPTERS_DIR/database_adapter.py"; then
    echo "   ✅ database_adapter.py: fusion BTTS présente"
else
    echo "   ❌ database_adapter.py: ERREUR - patch non appliqué"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ PATCHES APPLIQUÉS                                           ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  Pour tester:                                                  ║"
echo "║    cd $BASE_DIR                                                ║"
echo "║    python3 main.py --hours 48                                  ║"
echo "║                                                                ║"
echo "║  En cas de problème:                                           ║"
echo "║    cp $BACKUP_DIR/* $ADAPTERS_DIR/                             ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"

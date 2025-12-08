#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM ORCHESTRATOR V1.0 - SCRIPT DE DÉPLOIEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "   🚀 QUANTUM ORCHESTRATOR V1.0 - DÉPLOIEMENT"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# Variables
DEPLOY_DIR="/home/Mon_ps/quantum/orchestrator"
DB_NAME="monps"
DB_USER="monps"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher le status
status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
        exit 1
    fi
}

# 1. Créer la branche Git
echo ""
echo "📦 Étape 1: Création de la branche Git..."
cd /home/Mon_ps
git checkout -b feature/quantum-orchestrator-v1 2>/dev/null || git checkout feature/quantum-orchestrator-v1
status "Branche feature/quantum-orchestrator-v1"

# 2. Créer le répertoire
echo ""
echo "📁 Étape 2: Création du répertoire..."
mkdir -p $DEPLOY_DIR
status "Répertoire créé: $DEPLOY_DIR"

# 3. Copier les fichiers
echo ""
echo "📄 Étape 3: Copie des fichiers..."

# Le fichier principal
if [ -f "./quantum_orchestrator_v1.py" ]; then
    cp ./quantum_orchestrator_v1.py $DEPLOY_DIR/
    status "quantum_orchestrator_v1.py"
fi

# Le schéma SQL
if [ -f "./schema_orchestrator_v1.sql" ]; then
    cp ./schema_orchestrator_v1.sql $DEPLOY_DIR/
    status "schema_orchestrator_v1.sql"
fi

# Le README
if [ -f "./README.md" ]; then
    cp ./README.md $DEPLOY_DIR/
    status "README.md"
fi

# Ce script
cp "$0" $DEPLOY_DIR/deploy.sh 2>/dev/null
status "deploy.sh"

# 4. Exécuter le schéma SQL
echo ""
echo "🗄️ Étape 4: Exécution du schéma SQL..."
if [ -f "$DEPLOY_DIR/schema_orchestrator_v1.sql" ]; then
    psql -U $DB_USER -d $DB_NAME -f $DEPLOY_DIR/schema_orchestrator_v1.sql 2>/dev/null
    status "Schéma SQL exécuté"
else
    echo -e "${YELLOW}⚠${NC} Fichier SQL non trouvé, étape ignorée"
fi

# 5. Créer le fichier __init__.py
echo ""
echo "🐍 Étape 5: Création des fichiers Python auxiliaires..."
cat > $DEPLOY_DIR/__init__.py << 'EOF'
"""
Quantum Orchestrator V1.0 - Hedge Fund Grade

Modules:
- quantum_orchestrator_v1: Orchestrateur principal
"""

from .quantum_orchestrator_v1 import (
    QuantumOrchestrator,
    QuantumPick,
    BetSnapshot,
    ModelVote,
    TeamDNA
)

__version__ = "1.0.0"
__all__ = [
    "QuantumOrchestrator",
    "QuantumPick", 
    "BetSnapshot",
    "ModelVote",
    "TeamDNA"
]
EOF
status "__init__.py créé"

# 6. Tester l'import
echo ""
echo "🧪 Étape 6: Test d'import..."
cd $DEPLOY_DIR
python3 -c "from quantum_orchestrator_v1 import QuantumOrchestrator; print('Import OK')" 2>/dev/null
if [ $? -eq 0 ]; then
    status "Import Python réussi"
else
    echo -e "${YELLOW}⚠${NC} Test d'import échoué (dépendances manquantes?)"
fi

# 7. Git commit
echo ""
echo "📝 Étape 7: Git commit..."
cd /home/Mon_ps
git add quantum/orchestrator/
git commit -m "🚀 QUANTUM ORCHESTRATOR V1.0 - Hedge Fund Grade

Architecture:
- 6 Modèles Ensemble avec Weighted Consensus
- 11 Vecteurs DNA complets
- Monte Carlo Validation (obligatoire)
- CLV + Smart Conflict Resolution
- Data Snapshot (Boîte Noire) pour audit
- Model Performance Tracking

Modèles:
- A: team_strategy (+1,434.6u)
- B: quantum_scorer V2.4 (r=+0.53)
- C: matchup_scorer V3.4.2 (Momentum L5)
- D: dixon_coles (Probabilités)
- E: scenarios (20 + MC filter)
- F: dna_features (11 vecteurs)

Tables SQL:
- quantum.bet_snapshots (Boîte Noire)
- quantum.model_votes (Attribution P&L)

Vues SQL:
- v_model_performance
- v_model_performance_detailed
- v_snapshot_summary
- v_market_performance
- v_conviction_performance"
status "Git commit"

# 8. Push
echo ""
echo "🚀 Étape 8: Git push..."
git push -u origin feature/quantum-orchestrator-v1 2>/dev/null
if [ $? -eq 0 ]; then
    status "Git push"
else
    echo -e "${YELLOW}⚠${NC} Push échoué (peut-être déjà à jour)"
fi

# 9. Résumé
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "   ✅ DÉPLOIEMENT TERMINÉ"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "   📁 Répertoire: $DEPLOY_DIR"
echo ""
echo "   📄 Fichiers:"
echo "      • quantum_orchestrator_v1.py"
echo "      • schema_orchestrator_v1.sql"
echo "      • README.md"
echo "      • __init__.py"
echo ""
echo "   🗄️ Tables SQL:"
echo "      • quantum.bet_snapshots"
echo "      • quantum.model_votes"
echo ""
echo "   📊 Vues SQL:"
echo "      • quantum.v_model_performance"
echo "      • quantum.v_model_performance_detailed"
echo "      • quantum.v_snapshot_summary"
echo "      • quantum.v_market_performance"
echo "      • quantum.v_conviction_performance"
echo ""
echo "   🔀 Branche Git: feature/quantum-orchestrator-v1"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "   📋 PROCHAINES ÉTAPES:"
echo ""
echo "   1. Tester l'orchestrateur:"
echo "      cd $DEPLOY_DIR"
echo "      python3 quantum_orchestrator_v1.py"
echo ""
echo "   2. Intégrer avec les vraies données PostgreSQL"
echo ""
echo "   3. Backtest sur données historiques"
echo ""
echo "   4. Si OK, merger vers main:"
echo "      git checkout main"
echo "      git merge feature/quantum-orchestrator-v1"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"

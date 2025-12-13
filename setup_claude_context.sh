#!/bin/bash
# =============================================================================
# Script d'installation des fichiers de contexte Claude Code pour Mon_PS
# =============================================================================
# 
# Usage: 
#   chmod +x setup_claude_context.sh
#   ./setup_claude_context.sh
#
# Ce script crée la structure de fichiers pour gérer le contexte Claude Code
# =============================================================================

set -e

# Configuration
PROJECT_DIR="/home/Mon_ps"
DOCS_DIR="$PROJECT_DIR/docs"
CLAUDE_DIR="$PROJECT_DIR/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands"

echo "🚀 Installation des fichiers de contexte Claude Code pour Mon_PS"
echo "================================================================="

# Créer les répertoires
echo "📁 Création des répertoires..."
mkdir -p "$DOCS_DIR"
mkdir -p "$COMMANDS_DIR"

# Vérifier si CLAUDE.md existe déjà
if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
    echo "⚠️  CLAUDE.md existe déjà. Sauvegarde en CLAUDE.md.backup"
    cp "$PROJECT_DIR/CLAUDE.md" "$PROJECT_DIR/CLAUDE.md.backup"
fi

echo "✅ Structure créée :"
echo "   $PROJECT_DIR/"
echo "   ├── CLAUDE.md"
echo "   ├── docs/"
echo "   │   ├── CURRENT_TASK.md"
echo "   │   ├── DECISIONS.md"
echo "   │   └── CHANGELOG.md"
echo "   └── .claude/"
echo "       └── commands/"
echo "           ├── continue.md"
echo "           ├── save.md"
echo "           └── status.md"

echo ""
echo "📝 Instructions :"
echo "1. Copie les fichiers depuis le dossier téléchargé vers ton serveur"
echo "2. Ajuste le contenu de CLAUDE.md selon tes besoins"
echo "3. Mets à jour docs/CURRENT_TASK.md avec ta tâche actuelle"
echo ""
echo "🎮 Commandes disponibles dans Claude Code :"
echo "   /continue - Reprendre le contexte du projet"
echo "   /save     - Sauvegarder la session avant compact"
echo "   /status   - Voir l'état rapide du projet"
echo ""
echo "✅ Installation terminée !"

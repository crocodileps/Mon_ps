#!/bin/bash

# Fichiers à nettoyer
FILES=(
  "frontend/app/opportunities/page.tsx"
  "frontend/app/bets/page.tsx"
  "frontend/app/page.tsx"
  "frontend/components/layout/header.tsx"
  "frontend/components/modals/WalletModal.tsx"
  "frontend/components/business/BetCard.tsx"
)

for file in "${FILES[@]}"; do
  echo "🔧 Nettoyage: $file"
  
  # Backup
  cp "$file" "$file.bak"
  
  # Vérifier si formatNumber est déjà importé
  if ! grep -q "formatNumber" "$file"; then
    # Ajouter import après la première ligne d'import
    sed -i '1,/^import/ s/^\(import .*\)$/\1\nimport { formatNumber } from "@\/lib\/format";/' "$file"
  fi
  
  # Remplacer les patterns .toFixed()
  # Pattern: variable.toFixed(X) → formatNumber(variable, X)
  sed -i -E 's/([a-zA-Z_][a-zA-Z0-9_.]*)\.toFixed\(([0-9])\)/formatNumber(\1, \2)/g' "$file"
  
  # Pattern: (expression).toFixed(X) → formatNumber(expression, X)  
  sed -i -E 's/\(([^)]+)\)\.toFixed\(([0-9])\)/formatNumber(\1, \2)/g' "$file"
  
  echo "  ✅ Modifié"
done

echo ""
echo "🎯 Vérification des changements..."
git diff --stat

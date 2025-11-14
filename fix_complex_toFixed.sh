#!/bin/bash

# Fichiers avec patterns complexes
FILES=(
  "frontend/components/modals/BetAnalysisModal.tsx"
  "frontend/components/business/BetForm.tsx"
  "frontend/components/business/BetsTable.tsx"
  "frontend/app/test-hooks/page.tsx"
)

for file in "${FILES[@]}"; do
  echo "🔧 Correction patterns complexes: $file"
  
  # Pattern: (expression).toFixed(X) → formatNumber(expression, X)
  # Utiliser perl car sed ne gère pas bien les parenthèses imbriquées
  perl -i.bak2 -pe 's/\(([^)]+)\)\.toFixed\((\d)\)/formatNumber($1, $2)/g' "$file"
  
  # Pattern: value?.toFixed(X) → formatNumber(value, X)
  perl -i.bak2 -pe 's/(\w+)\?\.toFixed\((\d)\)/formatNumber($1, $2)/g' "$file"
  
  echo "  ✅ Modifié"
done

echo ""
echo "✅ Correction terminée"

#!/bin/bash

# Tous les fichiers avec .toFixed
FILES=(
  "frontend/app/test-hooks/page.tsx"
  "frontend/components/modals/BetAnalysisModal.tsx"
  "frontend/components/modals/TipDetailModal.tsx"
  "frontend/components/modals/PlayerDetailModal.tsx"
  "frontend/components/modals/CategoryDetailModal.tsx"
  "frontend/components/business/BetForm.tsx"
  "frontend/components/business/BetsTable.tsx"
)

for file in "${FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "⚠️  Fichier non trouvé: $file"
    continue
  fi
  
  echo "🔧 Nettoyage: $file"
  cp "$file" "$file.bak"
  
  # Ajouter import
  if ! grep -q "formatNumber" "$file"; then
    sed -i '2i import { formatNumber } from "@/lib/format";' "$file"
  fi
  
  # Remplacer .toFixed
  sed -i -E 's/([a-zA-Z_][a-zA-Z0-9_.]*)\.toFixed\(([0-9])\)/formatNumber(\1, \2)/g' "$file"
  
  echo "  ✅ Modifié"
done

echo ""
echo "✅ Nettoyage terminé"

#!/bin/bash
# pre_commit_check.sh - Vérifications avant commit
# Usage: ./pre_commit_check.sh

echo "🔍 PRE-COMMIT CHECKS..."
echo ""

# 1. Syntax Python
echo "1️⃣  Syntax Python..."
find /home/Mon_ps/backend -name "*.py" -exec python -m py_compile {} \; 2>&1 | grep -v "^$" && echo "❌ Erreurs syntax" || echo "✅ Syntax OK"

# 2. Linting
echo ""
echo "2️⃣  Linting (ruff)..."
cd /home/Mon_ps/backend
ruff check . || echo "⚠️  Warnings détectés"

# 3. Tests
echo ""
echo "3️⃣  Tests unitaires..."
pytest /home/Mon_ps/backend/tests/unit -v --tb=short

# 4. Secrets
echo ""
echo "4️⃣  Scan secrets..."
grep -r "SECRET\|PASSWORD\|API_KEY.*=.*['\"]" /home/Mon_ps --include="*.py" | grep -v ".env.example" && echo "❌ Secrets potentiels!" || echo "✅ Pas de secrets hardcodés"

echo ""
echo "================================================================"
if [ $? -eq 0 ]; then
    echo "✅ TOUS LES CHECKS PASSÉS - OK pour commit"
else
    echo "❌ ÉCHECS DÉTECTÉS - CORRIGER avant commit"
fi
echo "================================================================"

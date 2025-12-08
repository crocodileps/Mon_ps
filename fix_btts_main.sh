#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# FIX BTTS - Injection dans main.py
# ═══════════════════════════════════════════════════════════════════════════════

FILE="/home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1_modular/main.py"

echo "🔧 Injection de l'approximation BTTS dans main.py..."

# Backup
cp "$FILE" "$FILE.backup_btts"

# Chercher la ligne "odds_dict = match.odds.to_dict()" et ajouter AVANT
sed -i '/odds_dict = match.odds.to_dict()/i \
        # 🎯 FIX: Approximer BTTS si manquant\
        if match.odds.btts_yes_odds <= 1.0 and match.odds.over_25_odds > 1.0:\
            from adapters.odds_loader import approximate_btts_odds\
            btts_yes, btts_no = approximate_btts_odds(match.odds.over_25_odds)\
            match.odds.btts_yes_odds = btts_yes\
            match.odds.btts_no_odds = btts_no\
            logger.info(f"   📊 BTTS approximé: Yes={btts_yes}, No={btts_no} (depuis O2.5={match.odds.over_25_odds})")\
' "$FILE"

echo "✅ Injection terminée"

# Vérifier
echo ""
echo "🔍 Vérification (lignes autour de to_dict):"
grep -n -B3 -A1 "odds_dict = match.odds.to_dict()" "$FILE"

echo ""
echo "🧪 Test syntaxe..."
python3 -m py_compile "$FILE" && echo "✅ Syntaxe OK" || echo "❌ Erreur syntaxe"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Pour tester:                                                  ║"
echo "║    cd /home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1_modular"
echo "║    python3 main.py --hours 48                                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"

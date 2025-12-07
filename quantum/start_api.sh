#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM RULE ENGINE API - Startup Script
# ═══════════════════════════════════════════════════════════════════════════════════════

set -e

# Configuration
PORT=${QUANTUM_API_PORT:-8002}
HOST=${QUANTUM_API_HOST:-0.0.0.0}
WORKERS=${QUANTUM_API_WORKERS:-1}
LOG_LEVEL=${QUANTUM_API_LOG_LEVEL:-info}

echo "═══════════════════════════════════════════════════════════════"
echo "🎲 QUANTUM RULE ENGINE API 2.1"
echo "═══════════════════════════════════════════════════════════════"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Workers: $WORKERS"
echo "Log Level: $LOG_LEVEL"
echo "═══════════════════════════════════════════════════════════════"

# Vérifier que quantum est disponible
python3 -c "from quantum.services import QuantumRuleEngine; print('✅ Quantum module OK')" || {
    echo "❌ Quantum module not found!"
    exit 1
}

# Démarrer l'API
cd /home/Mon_ps/quantum

exec uvicorn api:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL"

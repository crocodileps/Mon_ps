#!/bin/bash
# session_context.sh - Contexte automatique Mon_PS
# Usage: ./session_context.sh

echo "================================================================"
echo "📍 MON_PS SESSION CONTEXT - $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
echo ""

echo "🌿 GIT STATUS:"
cd /home/Mon_ps || exit
echo "   Branche: $(git branch --show-current)"
echo "   Derniers commits:"
git log --oneline -3 | sed 's/^/     /'
echo "   Fichiers modifiés:"
git status --short | sed 's/^/     /' || echo "     Aucun"
echo ""

echo "🐳 DOCKER SERVICES:"
docker-compose ps 2>/dev/null | tail -n +2 | awk '{print "   " $1 " → " $2}' || echo "   Docker non accessible"
echo ""

echo "📊 HEALTH CHECKS:"
curl -s -o /dev/null -w "   Backend (8001): %{http_code}\n" http://localhost:8001/health
curl -s -o /dev/null -w "   Frontend (3001): %{http_code}\n" http://localhost:3001
redis-cli ping > /dev/null 2>&1 && echo "   Redis: OK" || echo "   Redis: DOWN"
pg_isready -h localhost -p 5432 > /dev/null 2>&1 && echo "   PostgreSQL: OK" || echo "   PostgreSQL: DOWN"
echo ""

echo "⚠️  MARQUEURS TECHNIQUES:"
grep -rn "TODO\|FIXME\|HACK" /home/Mon_ps --include="*.py" --include="*.tsx" 2>/dev/null | head -5 | sed 's/^/   /' || echo "   Aucun"
echo ""

echo "================================================================"
echo "✅ Contexte chargé. Objectif de cette session?"
echo "================================================================"

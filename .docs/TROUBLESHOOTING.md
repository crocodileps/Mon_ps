# 🔧 MON_PS - Guide de Dépannage

## 🎯 Problèmes Résolus (Historique)

### ❌ Problème #1 : Dashboard Crash - TypeError .toFixed() 
**Date** : 14 Novembre 2025  
**Symptôme** : Page `/dashboard` affiche "Application error: a client-side exception has occurred"

**Erreur Console** :
```
TypeError: Cannot read properties of undefined (reading 'toFixed')
```

**Cause Racine** :
Commit `0e33aa9` (Dashboard Phase 3) a introduit des appels `.toFixed()` non protégés sur des valeurs potentiellement undefined.

**Fichiers Affectés** :
- `ActiveBetsPreview.tsx` : `bet.odds_value.toFixed(2)`
- `StatsWidget.tsx` : `numValue.toFixed(decimals)`
- `OpportunityCard.tsx` : `edge_pct.toFixed(1)`, `best_odds.toFixed(2)`
- `stat-card.tsx` : `change.toFixed(1)`
- `top-opportunities.tsx` : `opp.best_odds.toFixed(2)`, `opp.edge_pct.toFixed(1)`
- `animated-number.tsx` : `displayValue.toFixed(decimals)`
- `custom-tooltip.tsx` : `p.value.toFixed(2)`

**Solution Appliquée** :
1. Créer helper sûr `lib/format.ts` :
```typescript
export function formatNumber(value: any, decimals: number = 2): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (typeof num !== 'number' || isNaN(num) || num === null || num === undefined) {
    return '0.' + '0'.repeat(decimals);
  }
  return num.toFixed(decimals);
}
```

2. Remplacer tous les `.toFixed()` par `formatNumber()` :
```typescript
// Avant
{bet.odds_value.toFixed(2)}

// Après  
{formatNumber(bet.odds_value, 2)}
```

**Validation** :
✅ Dashboard s'affiche sans crash  
✅ Toutes les valeurs numériques affichent "0.00" si undefined  
✅ Build réussit sans erreurs

**Commits** :
```
[hash] fix(frontend): Protect all dashboard .toFixed() against undefined
```

---

### ❌ Problème #2 : Backend API Validation Error
**Date** : 13-14 Novembre 2025  
**Symptôme** : Endpoint `/odds/odds/matches` retourne erreurs Pydantic

**Erreur Backend** :
```python
{'type': 'missing', 'loc': ('response', 20, 'league'), 'msg': 'Field required'}
{'type': 'missing', 'loc': ('response', 20, 'bookmaker_count'), 'msg': 'Field required'}
```

**Cause Racine** :
Désalignement entre requête SQL et schéma Pydantic `MatchSummary` :
- SQL retournait : `nb_bookmakers`, `best_home_odd` (sans 's')
- Pydantic attendait : `bookmaker_count`, `best_home_odds` (avec 's')
- SQL ne retournait pas : `league`

**Solution Appliquée** :
```python
# backend/api/routes/odds.py

# Ajout colonne league (alias de sport)
SELECT
    match_id,
    sport,
    sport as league,  # ← AJOUTÉ
    ...
    
# Correction noms colonnes
COUNT(DISTINCT bookmaker) as bookmaker_count,  # ← au lieu de nb_bookmakers
MAX(home_odds) as best_home_odds,  # ← avec 's'
MAX(away_odds) as best_away_odds,  # ← avec 's'
MAX(draw_odds) as best_draw_odds   # ← avec 's'
```

**Validation** :
```bash
curl http://localhost:8001/odds/odds/matches | jq '.[0]'
# ✅ Retourne JSON valide avec tous les champs
```

**Commits** :
```
dc27534 fix(backend): Match SQL aliases with Pydantic schema
5180a69 fix(backend): Use correct odds_history columns (home_odds, away_odds, draw_odds)
```

---

## 🛠️ Guide de Dépannage

### Frontend Ne Build Pas

**Symptôme** : `npm run build` échoue

**Diagnostics** :
```bash
# 1. Voir les erreurs TypeScript
cd /home/Mon_ps/monitoring
docker compose build frontend 2>&1 | grep -i "error"

# 2. Vérifier syntaxe fichiers récents
git diff HEAD~1 frontend/
```

**Solutions Possibles** :
- ❌ Erreur syntaxe TypeScript → Corriger le fichier
- ❌ Import manquant → Ajouter l'import
- ❌ Type incorrect → Vérifier types Pydantic vs TypeScript

---

### Dashboard Affiche Erreur 404

**Symptôme** : Console montre `404 /compare-agents`, `/analytics`, etc.

**Diagnostic** :
```bash
# Vérifier quelles pages existent
ls -la frontend/app/*/page.tsx
```

**Explication** : **C'EST NORMAL**
- ✅ Ces pages ne sont pas encore implémentées
- ✅ Les 404 ne bloquent PAS le fonctionnement
- ⚠️  Elles sont référencées dans le menu mais n'existent pas

**Solution** : Ignorer ces 404, ou implémenter les pages manquantes (voir TODO.md)

---

### Backend Retourne Erreurs 500

**Symptôme** : API retourne Internal Server Error

**Diagnostics** :
```bash
# 1. Logs backend détaillés
docker logs monps_backend --tail 100 | grep -i "error\|exception" -A 10

# 2. Test endpoint spécifique
curl -v http://localhost:8001/odds/odds/matches

# 3. Vérifier connexion DB
docker exec -it monps_postgres psql -U monps -d monps_db -c "\dt"
```

**Solutions Possibles** :
- ❌ Erreur SQL → Vérifier schéma vs requête
- ❌ Erreur Pydantic → Aligner schemas avec données
- ❌ DB pas démarrée → `docker compose up -d monps_postgres`

---

### "Cannot Connect to Backend"

**Symptôme** : Frontend ne peut pas joindre API

**Diagnostics** :
```bash
# 1. Backend est-il UP ?
docker ps | grep backend

# 2. Backend répond-il ?
curl http://localhost:8001/health

# 3. Frontend utilise-t-il la bonne URL ?
grep -r "backend:8000" frontend/
# Devrait être "http://backend:8000" dans Docker network
```

**Solutions** :
- ❌ Backend down → `docker compose up -d backend`
- ❌ Mauvaise URL → Corriger fetch URL
- ❌ CORS → Ajouter frontend à CORS_ORIGINS backend

---

### Données Vides / Pas d'Opportunités

**Symptôme** : Dashboard affiche "0 opportunités"

**Diagnostics** :
```bash
# 1. Y a-t-il des odds en DB ?
docker exec -it monps_postgres psql -U monps -d monps_db \
  -c "SELECT COUNT(*) FROM odds_history;"

# 2. Y a-t-il des matchs futurs ?
docker exec -it monps_postgres psql -U monps -d monps_db \
  -c "SELECT COUNT(*) FROM odds_history WHERE commence_time > NOW();"

# 3. Le collector tourne-t-il ?
docker logs monps_backend | grep "Collector"
```

**Solutions** :
- ❌ Pas de données → Déclencher collecte : `curl http://localhost:8001/metrics/refresh`
- ❌ Matchs passés → Attendre prochaine collecte (toutes les 4h)
- ❌ Collector erreur → Vérifier API key The Odds API

---

## 🔍 Commandes de Diagnostic Utiles

### État Général
```bash
# Status Docker
docker ps

# Logs tous services
docker compose logs --tail=50

# Espace disque
df -h

# Mémoire
free -h
```

### Backend Spécifique
```bash
# Logs backend en direct
docker logs monps_backend -f

# Test health endpoint
curl http://localhost:8001/health

# Test endpoint odds
curl http://localhost:8001/odds/odds/matches | jq '.[:2]'

# Entrer dans container
docker exec -it monps_backend bash
```

### Frontend Spécifique
```bash
# Logs frontend
docker logs monps_frontend -f

# Rebuild from scratch
cd /home/Mon_ps/monitoring
docker compose build --no-cache frontend
docker compose up -d frontend

# Vérifier que ça répond
curl -I http://localhost:3001
```

### Database
```bash
# Connexion DB
docker exec -it monps_postgres psql -U monps -d monps_db

# Compter odds
docker exec -it monps_postgres psql -U monps -d monps_db \
  -c "SELECT sport, COUNT(*) FROM odds_history GROUP BY sport;"

# Dernier match collecté
docker exec -it monps_postgres psql -U monps -d monps_db \
  -c "SELECT * FROM odds_history ORDER BY created_at DESC LIMIT 5;"
```

---

## 🚨 En Cas de Problème Majeur

### 1. Backup & Reset
```bash
# Backup DB
docker exec monps_postgres pg_dump -U monps monps_db > backup_$(date +%Y%m%d).sql

# Reset containers
cd /home/Mon_ps/monitoring
docker compose down
docker compose up -d
```

### 2. Retour État Stable
```bash
# Voir dernier commit stable
git log --oneline -10

# Retour à un commit spécifique (ex: 69e75e0)
git checkout 69e75e0

# Rebuild
cd monitoring
docker compose build
docker compose up -d
```

### 3. Clean Rebuild
```bash
# Nettoyer images
docker compose down
docker system prune -a

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

---

## 📞 Checklist Debug

Avant de paniquer, vérifier dans l'ordre :

1. ✅ Docker containers UP ? → `docker ps`
2. ✅ Backend répond ? → `curl http://localhost:8001/health`
3. ✅ Frontend répond ? → `curl -I http://localhost:3001`
4. ✅ DB accessible ? → `docker exec monps_postgres psql -U monps -d monps_db -c "SELECT 1;"`
5. ✅ Logs propres ? → `docker compose logs --tail=100`
6. ✅ Git status propre ? → `git status`
7. ✅ Derniers commits ? → `git log -5 --oneline`

Si tout est ✅ et ça ne marche pas → Voir STATUS.md et TODO.md

# Session 2025-12-20 #98 - Audit Serveur + Team Market Profiler V1 vs V2

## Contexte
Mission d'audit complet de l'etat du serveur Mon_PS, identifiant des problemes P0:
- team_market_profiler perime 16 jours
- ml_trainer jamais execute
- Investigation V1 vs V2 du script team_market_profiler

## Realise

### AUDIT SERVEUR COMPLET
- Verification des 12 CRONs actifs (Guardian, scrapers, etc.)
- 9 containers Docker - tous UP
- Guardian v1.0 operationnel (check quotidien 07h00)
- team_market_profiles: 1188 rows, perime 16 jours

### DECOUVERTE CRITIQUE: DEUX SCRIPTS INCOMPATIBLES
1. **V1** (`backend/scripts/analytics/team_market_profiler.py`)
   - 402 lignes, 6 fonctions
   - Source: `match_xg_stats` (817 matchs reels sur 489 jours)
   - Schema: team_name, league, season, market_type (1188 rows)
   - FONCTIONNE - teste avec succes

2. **V2** (`backend/ml/team_market_profiler.py`)
   - 594 lignes, 9 fonctions
   - Source: `tracking_clv_picks` (3361 picks sur 6 JOURS seulement)
   - Schema: team_name, location, best_market, JSONB (incompatible)
   - CASSE - table n'a pas les colonnes requises
   - Performance tracking: -416.80 unites (PERTE)

### 4 FICHIERS CASSÉS IDENTIFIÉS
Utilisent schema V2 qui n'existe pas en DB:
- `backend/api/routes/ml_prediction_routes.py` - ACTIF mais JAMAIS APPELE
- `backend/api/routes/market_recommendation_routes.py` - ACTIF mais JAMAIS APPELE
- `backend/ml/optimize_threshold.py` - ORPHELIN
- `backend/ml/predictive_model.py` - ORPHELIN

### CONSOMMATEURS V1 (CRITIQUES)
- `quantum/chess_engine/core/data_hub.py`
- `backend/scripts/analytics/market_convergence_engine.py`
- ~15 fichiers benchmarks

### AUDIT SOURCES DE DONNEES
| Source | Couverture | Nature | Verdict |
|--------|------------|--------|---------|
| match_xg_stats (V1) | 489 jours | Resultats REELS | FIABLE |
| tracking_clv_picks (V2) | 6 jours | Picks SYSTEME | INSUFFISANT |

## Fichiers touches
Aucun fichier modifie - AUDIT SEULEMENT

## Problemes resolus
- N/A (audit uniquement)

## En cours / A faire
- [x] Audit etat serveur
- [x] Comparaison V1 vs V2 scripts
- [x] Audit sources de donnees
- [x] Identification fichiers casses
- [ ] **PROCHAIN**: Ajouter V1 au CRON
- [ ] **PROCHAIN**: Desactiver/archiver fichiers V2 casses
- [ ] **PROCHAIN**: Ajouter check team_market_profiler a Guardian

## Notes techniques

### CHRONOLOGIE GIT
```
3 dec 12:45 - V2 cree (ml/)
3 dec 13:21 - market_recommendation_routes.py (utilise V2)
3 dec 13:51 - ml_prediction, optimize, predictive (utilisent V2)
4 dec 01:43 - V1 cree (analytics/) <- ECRASE LE SCHEMA!
4 dec 01:24 - Donnees creees avec schema V1
```

### VERDICT FINAL
V1 gagne sans contestation:
- Donnees REELLES vs tracking systeme
- 489 jours vs 6 jours
- Performance V2: -416.80 unites (PERTE)

### PLAN D'ACTION VALIDE
```
1. Ajouter V1 au CRON: 0 4 * * *
   docker exec monps_backend python3 /app/scripts/analytics/team_market_profiler.py

2. Desactiver dans main.py:
   - market_recommendation_routes.py
   - ml_prediction_routes.py

3. Archiver (pas supprimer):
   - backend/ml/team_market_profiler.py
   - backend/ml/optimize_threshold.py
   - backend/ml/predictive_model.py

4. Ajouter a Guardian:
   - Verifier fraicheur team_market_profiles (<48h)
```

## Resume
Session #98 - Audit exhaustif revelant que V2 est base sur 6 jours de tracking systeme perdant (-416u), alors que V1 est base sur 16 mois de resultats reels. V1 est le seul choix viable.

**Status:** AUDIT COMPLETE - EN ATTENTE VALIDATION PLAN D'ACTION

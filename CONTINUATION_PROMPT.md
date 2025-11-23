# 🎯 CONTINUATION PROJET MON_PS - PHASE 2 BACKEND API

## CONTEXTE SESSION PRÉCÉDENTE

### 🎉 CE QUI A ÉTÉ RÉALISÉ (Session 22-23/11/2025)

**Système Meta-Learning GPT-4o complet:**

1. **Base de données**
   - Table `strategy_improvements` avec améliorations GPT-4o
   - Vue `strategies_ranking` avec tier automatique
   - 3 améliorations créées par GPT-4o pour "Spread Optimizer Ferrari 2.0"
   - Colonnes ajoutées en Phase 1: `status`, `archived_at`, `archived_reason`

2. **Backend API (FastAPI)**
   - 5 endpoints opérationnels:
     - GET /strategies/ranking
     - GET /strategies/improvements
     - GET /strategies/improvements/{id}
     - POST /strategies/meta-learning/analyze (trigger GPT-4o)
     - POST /results/fetch (récupération résultats matchs)
   - Script `meta_learning_gpt4o.py` fonctionnel
   - Coût: 0.02$/analyse

3. **Frontend Dashboard (Next.js)**
   - Page `/strategies` avec ranking stratégies
   - Affichage 3 améliorations GPT-4o dans sidebar
   - Page détails `/strategies/improvements/[id]` fonctionnelle
   - Design glassmorphism violet/purple cohérent
   - Navigation sidebar intégrée

4. **Automatisation**
   - Systemd timer quotidien (00:00 UTC)
   - Script orchestrateur Python avec retry logic
   - Première exécution programmée: 23/11/2025

5. **Infrastructure**
   - Serveur Hetzner CCX23 (VPN WireGuard)
   - Docker Compose (backend, frontend, postgres, grafana...)
   - Monitoring Prometheus + Grafana

### 📊 ÉTAT ACTUEL SYSTÈME

**Database:**
```sql
-- Table strategy_improvements
Colonnes principales:
- id, agent_name, strategy_name
- baseline_win_rate, new_threshold
- failure_pattern, missing_factors
- llm_reasoning, recommended_adjustments
- ab_test_active, improvement_applied
- status VARCHAR(20) DEFAULT 'proposed' ← AJOUTÉ PHASE 1
- archived_at TIMESTAMP DEFAULT NULL ← AJOUTÉ PHASE 1
- archived_reason TEXT DEFAULT NULL ← AJOUTÉ PHASE 1

État actuel:
- 3 améliorations avec status='proposed'
- Aucune archivée (archived_at=NULL partout)
```

**Fichiers clés:**
```
/home/Mon_ps/
├── backend/
│   ├── api/routes/strategies_routes.py (5 endpoints)
│   └── scripts/meta_learning_gpt4o.py
├── frontend/
│   └── app/strategies/
│       ├── page.tsx (liste + sidebar)
│       └── improvements/[id]/page.tsx (détails)
├── monitoring/docker-compose.yml
└── automation/meta_learning_orchestrator.py

Branch actuelle: feature/strategies-dashboard
Derniers commits: Phase 1 DB terminée
```

**URLs:**
- Frontend: http://91.98.131.218:3001/strategies
- Backend API: http://91.98.131.218:8001/docs
- Grafana: http://91.98.131.218:3000

---

## 🎯 OBJECTIF PHASE 2: BACKEND API ARCHIVAGE

### Ce qu'on doit créer:

**3 nouveaux endpoints dans `backend/api/routes/strategies_routes.py`:**

1. **POST /strategies/improvements/{id}/archive**
   - Paramètre: `reason` (optionnel)
   - Action: Met `status='archived'`, `archived_at=NOW()`, `archived_reason`
   - Retourne: `{"success": true, "improvement_id": X}`

2. **POST /strategies/improvements/{id}/reactivate**
   - Action: Met `status='proposed'`, `archived_at=NULL`
   - Retourne: `{"success": true, "improvement_id": X}`

3. **GET /strategies/improvements/archived**
   - Retourne: Liste améliorations avec `status='archived'`
   - Utilise vue `archived_improvements`

4. **POST /strategies/improvements/activate-selected**
   - Paramètre: `improvement_ids: list[int]`
   - Action: Met `status='active'`, `ab_test_active=TRUE` pour IDs sélectionnés
   - Retourne: `{"success": true, "activated": [ids], "count": X}`

### Template code à suivre:
```python
@router.post("/improvements/{improvement_id}/archive")
async def archive_improvement(improvement_id: int, reason: str = None):
    """Archive une amélioration pour plus tard"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier existence
        cursor.execute("SELECT * FROM strategy_improvements WHERE id = %s", (improvement_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Amélioration non trouvée")
        
        # Archiver
        cursor.execute("""
            UPDATE strategy_improvements
            SET 
                status = 'archived',
                archived_at = NOW(),
                archived_reason = %s,
                ab_test_active = FALSE
            WHERE id = %s
        """, (reason, improvement_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "improvement_id": improvement_id}
        
    except Exception as e:
        logger.error(f"Erreur archive: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## ⚠️ ERREURS À NE PAS REFAIRE

### 1. **Modifications DB sans vérification**
❌ Ajouter colonnes puis coder endpoints directement
✅ Ajouter colonne → Tester API → Coder endpoint → Tester

### 2. **Filtrage qui cache les données**
❌ Frontend filtre par `status IN ['proposed', 'active']` sans vérifier
✅ D'abord afficher TOUT, puis filtrer progressivement

### 3. **Modifications multiples en une fois**
❌ Changer DB + Backend + Frontend en même temps
✅ Phase par phase avec tests intermédiaires

### 4. **Oublier de restart services**
❌ Modifier code backend sans restart → anciennes données
✅ Toujours `docker compose restart backend` après modif

### 5. **Tourner en rond sur un problème**
❌ Multiplier les tentatives de fix sans comprendre
✅ Reset à dernière version stable si >3 tentatives échouent

### 6. **Colonnes status mal gérées**
❌ Créer colonne via DO $$ qui échoue silencieusement
✅ Utiliser `ALTER TABLE ... ADD COLUMN` simple et direct

---

## 📋 CHECKLIST PHASE 2

### Étape 1: Endpoint Archive (20min)
- [ ] Ajouter fonction `archive_improvement()` dans strategies_routes.py
- [ ] Test curl: `curl -X POST http://localhost:8001/strategies/improvements/1/archive?reason=Test`
- [ ] Vérifier DB: amélioration #1 a `status='archived'` et `archived_at` rempli
- [ ] Test API: `GET /improvements` ne retourne plus l'amélioration archivée
- [ ] ✅ Commit si tests passent

### Étape 2: Endpoint Reactivate (15min)
- [ ] Ajouter fonction `reactivate_improvement()`
- [ ] Test: réactiver amélioration #1
- [ ] Vérifier: `status='proposed'`, `archived_at=NULL`
- [ ] Test API: amélioration réapparaît dans liste
- [ ] ✅ Commit si tests passent

### Étape 3: Endpoint Archived (10min)
- [ ] Ajouter fonction `get_archived_improvements()`
- [ ] Test: lister améliorations archivées
- [ ] ✅ Commit

### Étape 4: Endpoint Activate Selected (20min)
- [ ] Ajouter fonction `activate_selected_improvements()`
- [ ] Test avec `[1, 3]`: active ces 2 IDs
- [ ] Vérifier: `status='active'`, `ab_test_active=TRUE`
- [ ] ✅ Commit

### Étape 5: Tests Globaux (15min)
- [ ] Swagger UI: tester tous endpoints
- [ ] Scénario complet: archive → liste archivées → réactive → active test
- [ ] ✅ Rebuild backend
- [ ] ✅ Test frontend ne casse pas

**TEMPS TOTAL ESTIMÉ: 1h20**

---

## 🚀 COMMANDES DE BASE

### Connexion serveur:
```bash
ssh root@91.98.131.218
cd /home/Mon_ps
```

### Édition fichier backend:
```bash
nano backend/api/routes/strategies_routes.py
# Ajouter les endpoints
```

### Test DB:
```bash
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT id, agent_name, status, archived_at 
FROM strategy_improvements;
"
```

### Rebuild backend:
```bash
cd /home/Mon_ps/monitoring
docker compose build backend
docker compose restart backend
sleep 10
```

### Test API:
```bash
# Archive
curl -X POST "http://localhost:8001/strategies/improvements/1/archive?reason=Test"

# Liste archivées
curl http://localhost:8001/strategies/improvements/archived | jq

# Réactive
curl -X POST http://localhost:8001/strategies/improvements/1/reactivate

# Active sélection
curl -X POST http://localhost:8001/strategies/improvements/activate-selected \
  -H "Content-Type: application/json" \
  -d '{"improvement_ids": [1, 3]}'
```

### Commit:
```bash
git add backend/api/routes/strategies_routes.py
git commit -m "feat: Phase 2 Backend - Endpoints archivage ✅"
git push origin feature/strategies-dashboard
```

---

## 🎓 BONNES PRATIQUES VALIDÉES

1. **Approche méthodique par phases**
   - Database → Backend → Frontend → Tests
   - Jamais tout en même temps

2. **Tests à chaque étape**
   - Après chaque modification: test immédiat
   - Si échec: rollback ou fix, pas continuer

3. **Commits fréquents**
   - Dès qu'un test passe: commit
   - Permet rollback facile si problème

4. **Reset si blocage**
   - >3 tentatives échouées → reset à version stable
   - Reprendre proprement plutôt que s'acharner

5. **TOUJOURS restart services après modif code**
   - Backend: `docker compose restart backend`
   - Frontend: `docker compose restart frontend`

---

## 📊 DONNÉES IMPORTANTES

**DB Config:**
```python
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_password_2024'
}
```

**Imports nécessaires dans strategies_routes.py:**
```python
from fastapi import APIRouter, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
```

**Statuts valides:**
- `proposed`: Nouvelle amélioration GPT-4o
- `active`: Test A/B en cours
- `applied`: Validée et appliquée
- `archived`: Mise de côté pour plus tard

---

## 🎯 PROMPT POUR NOUVELLE CONVERSATION

"Bonjour Claude !

Je continue le développement de Mon_PS (plateforme trading sportif). Nous sommes en **Phase 2: Backend API Archivage**.

**Contexte complet:** Lis le fichier /home/Mon_ps/CONTINUATION_PROMPT.md

**État actuel:**
- Phase 1 DB terminée ✅ (colonnes status, archived_at, archived_reason ajoutées)
- 3 améliorations GPT-4o en DB avec status='proposed'
- Frontend fonctionne: http://91.98.131.218:3001/strategies

**Objectif Phase 2:**
Créer 4 endpoints backend pour archivage/réactivation des améliorations.

**Fichier à modifier:** `backend/api/routes/strategies_routes.py`

**Approche:**
1. Endpoint par endpoint
2. Test après chaque ajout
3. Commit si test passe
4. MÉTHODIQUE, pas tout d'un coup

**Important:**
- Je suis connectée SSH sur serveur production
- Utilise nano pour édition fichiers
- Restart backend après chaque modif: `docker compose restart backend`

Commençons par l'endpoint **POST /archive**. Donne-moi le code complet à ajouter dans strategies_routes.py avec instructions précises."

---

## 📁 FICHIERS À CONSERVER

Ce prompt: `/home/Mon_ps/CONTINUATION_PROMPT.md`
État DB: Voir section "État actuel système"
Derniers commits: `git log --oneline -10`

---

**Bonne continuation Mya ! 🚀**

*Session précédente: ~8h de travail intensif*
*Prochaine session: Phase 2 (1h20) → Phase 3 Frontend (1h) → Phase 4 Tests finaux*

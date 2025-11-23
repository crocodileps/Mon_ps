# 🔧 TROUBLESHOOTING : Page /stats Learning System

## 📋 Résumé du Problème

**Durée totale** : ~3 heures  
**Objectif** : Créer page `/stats` affichant statistiques des agents ML  
**Symptômes** : Page vide, erreurs 404, 302, 500, backend crash  

---

## 🚨 PROBLÈMES RENCONTRÉS (par ordre chronologique)

### 1. ❌ ERREUR 404 : API `/stats/agents` introuvable

**Symptôme** :
```
GET /stats/agents → 404 Not Found
```

**Cause** : **DOUBLE PRÉFIXE /stats/stats**

**Explication** :
- Dans `stats_routes.py` : `@router.get("/stats/agents")`
- Dans `main.py` : `app.include_router(stats_routes.router, prefix="/stats")`
- Résultat : Route finale = `/stats/stats/agents` ❌
- Attendu : `/stats/agents` ✅

**Solution** :
```python
# ❌ INCORRECT (stats_routes.py)
@router.get("/stats/agents")

# ✅ CORRECT (stats_routes.py)
@router.get("/agents")  # Le prefix="/stats" est déjà dans main.py
```

**Fichiers concernés** :
- `backend/api/routes/stats_routes.py`
- `backend/api/main.py`

---

### 2. ❌ ERREUR SYNTAXE : main.py ligne 94

**Symptôme** :
```python
File "/app/api/main.py", line 94
    app.include_router(agents_comparison_routes.router)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: invalid syntax. Perhaps you forgot a comma?
```

**Cause** : **FICHIER main.py ÉCRASÉ/CORROMPU**

**Explication** :
- Script automatique a mal ajouté `stats_routes` au début du fichier
- A écrasé tout le contenu existant
- Backup `main.py.backup` était aussi corrompu (lignes dupliquées)

**Solution** :
```bash
# Restaurer depuis Git (version propre)
git checkout backend/api/main.py

# Ajouter stats_routes PROPREMENT à la fin
cat >> backend/api/main.py << 'END'

# Stats routes (Learning System)
from api.routes import stats_routes
app.include_router(stats_routes.router, prefix="/stats", tags=["stats"])
END

# Rebuild backend
docker compose build backend
docker compose up -d backend
```

**Leçon apprise** : 
- ⚠️ TOUJOURS vérifier syntaxe avec `python3 -m py_compile` avant rebuild
- ✅ Utiliser `git checkout` pour restaurer depuis version propre
- ✅ Ne JAMAIS faire confiance aux backups automatiques

---

### 3. ❌ ERREUR 302 : Redirection vers /login

**Symptôme** :
```
GET /stats → 302 Found
Location: /login?redirectTo=%2Fstats
```

**Cause** : **LAYOUT MANQUANT** pour la route /stats

**Explication** :
- Next.js App Router : chaque route nécessite son propre `layout.tsx`
- `/opportunities` fonctionnait car avait `layout.tsx` avec `DashboardLayout`
- `/stats` redirigait car **pas de layout.tsx**
- Le 302 était une redirection interne Next.js, pas une vraie auth

**Solution** :
```tsx
// frontend/app/stats/layout.tsx
import { DashboardLayout } from '@/components/dashboard-layout'

export default function StatsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <DashboardLayout>{children}</DashboardLayout>
}
```

**Alternative (sans sidebar)** :
```tsx
// Layout minimal sans auth
export default function StatsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
      {children}
    </div>
  )
}
```

---

### 4. ❌ ERREUR BUILD : Next.js standalone

**Symptôme** :
```
ERROR [runner 6/7] COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
failed to compute cache key: "/app/.next/standalone": not found
```

**Cause** : **next.config.js manquait `output: 'standalone'`**

**Solution** :
```javascript
// frontend/next.config.js
const nextConfig = {
  output: 'standalone',  // ✅ CRITIQUE pour Docker
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://monps_backend:8000/:path*',
      },
    ];
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};
```

---

### 5. ❌ CONFUSION : Structure frontend/app vs frontend/src/app

**Symptôme** :
- Fichiers créés dans `frontend/src/app/stats/` 
- Mais Next.js lit depuis `frontend/app/stats/`

**Cause** : **DEUX structures parallèles** dans le projet

**Solution** : **Toujours utiliser `frontend/app/`** (pas `frontend/src/app/`)
```bash
# ❌ INCORRECT
frontend/src/app/stats/page.tsx

# ✅ CORRECT
frontend/app/stats/page.tsx
```

**Vérification rapide** :
```bash
# Voir quelle structure est utilisée
ls -la frontend/app/opportunities/  # Si existe → utiliser /app
ls -la frontend/src/app/            # Ignorer cette structure
```

---

## ✅ SOLUTION FINALE COMPLÈTE

### Backend (API)

**1. Créer stats_routes.py**
```python
# backend/api/routes/stats_routes.py
from fastapi import APIRouter
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter()

@router.get("/agents")  # ✅ PAS /stats/agents (prefix déjà dans main.py)
async def get_agents_stats():
    conn = psycopg2.connect(...)
    # ... code
    return {
        "agents_summary": [...],
        "recent_analyses": [...],
        "predictions": [...]
    }
```

**2. Ajouter dans main.py**
```python
# backend/api/main.py (À LA FIN du fichier)

# Stats routes (Learning System)
from api.routes import stats_routes
app.include_router(stats_routes.router, prefix="/stats", tags=["stats"])
```

**3. Rebuild backend**
```bash
cd monitoring
docker compose build backend
docker compose up -d backend
```

### Frontend (Page)

**1. Créer layout.tsx**
```tsx
// frontend/app/stats/layout.tsx
export default function StatsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
      {children}
    </div>
  )
}
```

**2. Créer page.tsx**
```tsx
// frontend/app/stats/page.tsx
"use client";

import { useEffect, useState } from "react";

export default function StatsPage() {
  const [data, setData] = useState<any>(null);
  
  useEffect(() => {
    fetch("http://91.98.131.218:8001/stats/agents")
      .then((res) => res.json())
      .then((data) => setData(data));
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-white">
        📊 Statistiques Agents
      </h1>
      {/* ... reste du code */}
    </div>
  );
}
```

**3. Rebuild frontend**
```bash
cd monitoring
docker compose build frontend
docker compose up -d frontend
```

---

## 🔍 COMMANDES DE DIAGNOSTIC UTILES

### Vérifier API Backend
```bash
# Test health
curl http://localhost:8001/health

# Test stats API
curl http://localhost:8001/stats/agents | jq '.agents_summary'

# Voir logs backend
docker logs monps_backend --tail 50

# Tester import Python
docker exec monps_backend python3 -c "from api.routes import stats_routes; print('OK')"
```

### Vérifier Frontend
```bash
# Voir structure
ls -la frontend/app/stats/

# Test syntaxe Python (main.py)
python3 -m py_compile backend/api/main.py

# Voir logs frontend
docker logs monps_frontend --tail 30

# Test HTTP codes
curl -I http://localhost:3000/stats
```

### Vérifier Database
```bash
# Compter analyses
docker exec monps_postgres psql -U monps_user -d monps_db \
  -c "SELECT agent_name, COUNT(*) FROM agent_analyses GROUP BY agent_name;"
```

---

## ⚡ CHECKLIST RAPIDE POUR NOUVELLE PAGE

- [ ] **Backend** :
  - [ ] Créer `routes/ma_page_routes.py`
  - [ ] Route : `@router.get("/endpoint")` (sans préfixe)
  - [ ] Ajouter dans `main.py` : `app.include_router(ma_page_routes.router, prefix="/ma-page")`
  - [ ] Test syntaxe : `python3 -m py_compile backend/api/main.py`
  - [ ] Rebuild : `docker compose build backend && docker compose up -d backend`
  - [ ] Test API : `curl http://localhost:8001/ma-page/endpoint`

- [ ] **Frontend** :
  - [ ] Créer `frontend/app/ma-page/layout.tsx`
  - [ ] Créer `frontend/app/ma-page/page.tsx`
  - [ ] Vérifier structure : `ls -la frontend/app/` (PAS src/app)
  - [ ] Rebuild : `docker compose build frontend && docker compose up -d frontend`
  - [ ] Test : `curl -I http://localhost:3000/ma-page`

---

## 📚 RÉFÉRENCES

- Next.js App Router : https://nextjs.org/docs/app
- FastAPI Router : https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Docker Compose : https://docs.docker.com/compose/

---

## 🎯 RÉSULTAT FINAL

✅ Page `/stats` fonctionnelle :
- 3 agents affichés (A, B, D)  
- 142 analyses enregistrées  
- Menu navigation  
- Design glassmorphism violet/purple  

**Temps total** : ~3 heures  
**Problèmes résolus** : 5 majeurs  
**Leçons apprises** : 6 critiques  

---

**Date** : 22/11/2025  
**Auteur** : Mya + Claude  
**Version** : learning-system-stats-v1

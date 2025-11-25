# 🔬 SOLUTION SCIENTIFIQUE : API Opportunities Not Found

## ❌ PROBLÈME IDENTIFIÉ

### Symptôme
- Frontend : "Chargement des données API..."
- API retourne : `{"detail":"Not Found"}`
- Page reste vide

### Tests Diagnostics
```bash
curl http://localhost:8001/opportunities              # ❌ Erreur JSON
curl http://localhost:8001/opportunities/             # ❌ Not Found
curl http://localhost:8001/opportunities/opportunities/  # ✅ 50 opportunités
```

## 🎯 CAUSE RACINE

### Configuration Backend (main.py)
```python
# Ligne 156 - PREFIX défini
app.include_router(opportunities.router, 
                   prefix="/opportunities",  # <-- Premier /opportunities
                   tags=["opportunities"])
```

### Définition Route (opportunities.py)
```python
# Ligne 16 - ROUTE sans prefix interne
@router.get("/", response_model=List[Opportunity])
def get_opportunities(...):
```

### Résultat
- URL construite : `/opportunities/` (prefix + `/`)
- Mais FastAPI nécessite : `/opportunities/opportunities/`
- Raison : Probable router imbriqué ou configuration spéciale

## ✅ SOLUTION APPLIQUÉE

### Frontend (lib/api.ts ou page.tsx)
```typescript
// ❌ AVANT (ne marche pas)
export const getOpportunities = async () => {
  const response = await api.get('/opportunities')
  return response.data
}

// ✅ APRÈS (fonctionne)
export const getOpportunities = async () => {
  const response = await api.get('/opportunities/opportunities/')
  return response.data
}
```

## 📝 LEÇONS APPRISES

### À NE PLUS REPRODUIRE

1. **❌ JAMAIS modifier backend sans test curl**
```bash
   # Toujours tester AVANT de coder frontend
   curl http://localhost:8001/le-nouvel-endpoint
```

2. **❌ JAMAIS supposer qu'une route fonctionne**
   - Tester : sans slash `/endpoint`
   - Tester : avec slash `/endpoint/`
   - Tester : variations `/prefix/endpoint/`

3. **❌ JAMAIS commit sans vérifier l'API**
```bash
   # Checklist AVANT commit
   curl http://localhost:8001/opportunities/opportunities/ | jq 'length'
   # Doit retourner un nombre > 0
```

### ✅ PROCÉDURE SCIENTIFIQUE OBLIGATOIRE

#### 1. CRÉATION D'UN NOUVEL ENDPOINT
```bash
# A. Créer l'endpoint backend
# B. Tester IMMÉDIATEMENT
curl http://localhost:8001/le-nouvel-endpoint
# C. Noter l'URL EXACTE qui marche
# D. Utiliser cette URL dans le frontend
# E. Documenter dans TROUBLESHOOTING
```

#### 2. DEBUG D'UN ENDPOINT CASSÉ
```bash
# A. Tester toutes les variations
curl http://localhost:8001/endpoint
curl http://localhost:8001/endpoint/
curl http://localhost:8001/prefix/endpoint/

# B. Identifier laquelle marche
# C. Corriger le frontend OU le backend
# D. Documenter la solution
```

#### 3. AVANT CHAQUE COMMIT
```bash
# Checklist obligatoire
✅ API testée avec curl
✅ Frontend affiche les données
✅ Pas d'erreur console navigateur
✅ Documentation mise à jour
```

## 🔧 COMMANDES DE DIAGNOSTIC

### Test Rapide API
```bash
# Tester l'endpoint opportunities
curl -s http://localhost:8001/opportunities/opportunities/ | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f'✅ {len(d)} opportunités')"
```

### Vérifier Toutes les Routes
```bash
# Lister tous les endpoints disponibles
curl http://localhost:8001/docs
# Ou
docker logs monps_backend | grep "GET\|POST" | grep -v "404"
```

## 📊 MÉTRIQUES DE SUCCÈS

- ✅ API retourne 50+ opportunités
- ✅ Frontend affiche le tableau
- ✅ Temps de réponse < 1s
- ✅ Pas d'erreur console

## 🚨 SIGNAUX D'ALERTE

Si vous voyez :
- `{"detail":"Not Found"}` → Mauvaise URL
- `[]` (tableau vide) → Pas de données en DB
- Timeout > 5s → Problème performance
- CORS error → Configuration backend

## 📚 RÉFÉRENCES

- **Conversation 6** : Premier diagnostic API Not Found
- **Conversation 9** : Solution double prefix découverte
- **Conversation 10** : Documentation complète
- **FastAPI Docs** : https://fastapi.tiangolo.com/tutorial/bigger-applications/

---

**Date de création** : 2025-11-25
**Auteur** : Mya (avec Claude)
**Statut** : ✅ Solution validée en production
**Version** : v2.12.0+

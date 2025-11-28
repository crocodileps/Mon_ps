═══════════════════════════════════════════════════════════════════════════════
          📋 RÉSUMÉ DÉTAILLÉ SESSION 28 NOVEMBRE 2025
                    COMBOS 2.0 + ANALYSE IA GPT-4o
                         Durée: ~4 heures
═══════════════════════════════════════════════════════════════════════════════

## 🎯 OBJECTIF DE LA SESSION

Implémenter le bouton "Analyse IA" sur la page Combos pour analyser chaque
suggestion de combo avec GPT-4o, similaire à ce qui existait déjà dans 
l'historique.

═══════════════════════════════════════════════════════════════════════════════
## ✅ AVANCEMENT - CE QUI A ÉTÉ ACCOMPLI
═══════════════════════════════════════════════════════════════════════════════

### 1. Bouton Analyse IA sur Suggestions ✅
**Fichier:** `frontend/app/full-gain/combos/page.tsx`

**States ajoutés:**
```typescript
const [analyzingId, setAnalyzingId] = useState<number | null>(null);
const [aiAnalysis, setAiAnalysis] = useState<{id: number, text: string} | null>(null);
```

**Fonction analyzeWithAI:**
```typescript
const analyzeWithAI = async (suggestionIdx: number) => {
  setAnalyzingId(suggestionIdx);
  setAiAnalysis(null);
  try {
    const suggestion = suggestions[suggestionIdx];
    // 1. Sauvegarder le combo
    const saveRes = await fetch(API_BASE + '/api/combos/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selections: suggestion.picks.map(p => ({
          match: suggestion.match_name,
          market: p.market,
          odds: p.odds,
          score: p.score
        })),
        total_odds: suggestion.combined_odds,
        stake: 10
      })
    });
    const saveData = await saveRes.json();
    
    // 2. Analyser avec GPT-4o
    if (saveData.id) {
      const response = await fetch(API_BASE + '/api/combos/analyze-ai/' + saveData.id, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.analysis) {
        setAiAnalysis({ id: suggestionIdx, text: data.analysis });
      }
    }
  } catch (error) {
    console.error('Erreur analyse IA:', error);
  } finally {
    setAnalyzingId(null);
  }
};
```

**Bouton dans le JSX:**
```tsx
<button
  onClick={() => analyzeWithAI(idx)}
  disabled={analyzingId === idx}
  className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg"
>
  {analyzingId === idx ? 'Analyse...' : 'Analyse IA'}
</button>
```

### 2. Correction Route /save Backend ✅
**Fichier:** `backend/api/routes/combos_routes.py`

**Problème:** L'API /analyze-ai attendait un dict avec {match, picks, league...}
mais /save sauvegardait une liste brute.

**Solution:** Reformater selections avant insertion:
```python
formatted_selections = {
    'match': match_name,
    'picks': selections_list,
    'league': combo_data.get('league', 'Unknown'),
    'risk_level': combo_data.get('risk_level', 'MEDIUM'),
    'recommendation': combo_data.get('recommendation', '')
}
```

### 3. Null Safety Frontend ✅
**Problème:** Crash "Cannot read properties of undefined (reading 'toFixed')"

**Solution appliquée partout:**
```typescript
// AVANT
suggestion.combined_odds.toFixed(2)

// APRÈS
(suggestion.combined_odds ?? 0).toFixed(2)
```

**Champs protégés:**
- pick.odds
- suggestion.combined_odds
- suggestion.combined_probability
- suggestion.correlation_score
- comboStats.totalOdds
- comboStats.potentialWin

### 4. Correction Champ API ✅
```typescript
// AVANT (champ inexistant)
expected_win_rate

// APRÈS (champ réel de l'API)
combined_probability
```

### 5. Tag Git ✅
```
v2.19.0-combos-ia - Combos 2.0 avec Analyse IA GPT-4o
```

═══════════════════════════════════════════════════════════════════════════════
## ❌ ERREURS RENCONTRÉES ET SOLUTIONS
═══════════════════════════════════════════════════════════════════════════════

### ERREUR 1: Syntax Error - fetch avec backticks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Symptôme:**
```
Le bouton Analyse IA ne fonctionne pas, erreur CORS dans la console
```

**Code problématique:**
```typescript
// ❌ MAUVAIS - backticks au lieu de parenthèses
await fetch`${API_BASE}/api/combos/save`, {...}
```

**Cause:** Lors de l'insertion du code via heredoc, les backticks étaient
mal interprétés.

**Solution:**
```typescript
// ✅ BON - concaténation avec +
await fetch(API_BASE + '/api/combos/save', {...})
```

**Leçon:** Quand on insère du code TypeScript avec template literals via
bash heredoc, utiliser la concaténation + au lieu des backticks ${}.

---

### ERREUR 2: TypeError - toFixed on undefined
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Symptôme:**
```
Application error: a client-side exception has occurred
TypeError: Cannot read properties of undefined (reading 'toFixed')
```

**Cause:** L'API retourne parfois des valeurs null/undefined pour certains
champs numériques.

**Solution - Null Coalescing:**
```typescript
// Protéger TOUS les appels à .toFixed()
(value ?? 0).toFixed(2)
```

**Fichiers affectés:**
- frontend/app/full-gain/combos/page.tsx (8 occurrences corrigées)

---

### ERREUR 3: Champ API inexistant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Symptôme:**
```
Win Rate affiche 0% ou undefined
```

**Cause:** Le frontend utilisait `expected_win_rate` mais l'API retourne
`combined_probability`.

**Solution:**
```typescript
// Remplacer partout
expected_win_rate → combined_probability
```

---

### ERREUR 4: 500 Internal Server Error sur /analyze-ai
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Symptôme:**
```
POST /api/combos/analyze-ai/25 → 500 Internal Server Error
```

**Cause:** L'endpoint /analyze-ai attend un dict avec structure:
```python
{
  "match": "...",
  "picks": [...],
  "league": "...",
  "risk_level": "..."
}
```
Mais /save insérait une liste brute `[{...}, {...}]`.

**Solution:** Modifier /save pour formatter correctement:
```python
formatted_selections = {
    'match': match_name,
    'picks': selections_list,
    'league': combo_data.get('league', 'Unknown'),
    'risk_level': combo_data.get('risk_level', 'MEDIUM')
}
cur.execute("INSERT ... VALUES (%s, ...)", (json.dumps(formatted_selections), ...))
```

---

### ERREUR 5: CORS Policy Blocked
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Symptôme:**
```
Access to fetch at 'http://91.98.131.218:8001/...' has been blocked by CORS policy
```

**Diagnostic:**
1. Vérifier si c'est vraiment CORS ou erreur 500 déguisée
2. Les erreurs 500 peuvent apparaître comme CORS car le serveur ne renvoie
   pas les headers CORS sur erreur

**Vérification:**
```bash
# Tester directement l'API
curl -s -X POST "http://localhost:8001/api/combos/analyze-ai/4" | head -c 200
```

**Si l'API retourne une erreur → c'est pas CORS, c'est le backend**

---

### ERREUR 6: Database "monps_prod" does not exist
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Symptôme (FIN DE SESSION - NON RÉSOLU):**
```
FATAL: database "monps_prod" does not exist
```

**Cause:** Le container backend a été relancé sans les bonnes variables
d'environnement. La DB s'appelle `monps_db` pas `monps_prod`.

**Solution:**
```bash
docker stop monps_backend && docker rm monps_backend
source /home/Mon_ps/monitoring/.env

docker run -d \
  --name monps_backend \
  --network monitoring_monps_network \
  -p 8001:8000 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e DB_HOST="monps_postgres" \
  -e DB_PORT="5432" \
  -e DB_NAME="monps_db" \       # ← IMPORTANT: monps_db PAS monps_prod
  -e DB_USER="monps_user" \
  -e DB_PASSWORD="${DB_PASSWORD}" \
  monitoring-backend
```

**Leçon:** Toujours passer TOUTES les variables d'environnement DB lors
du docker run, même si elles semblent définies dans .env.

═══════════════════════════════════════════════════════════════════════════════
## 📊 ÉTAT ACTUEL DU SYSTÈME
═══════════════════════════════════════════════════════════════════════════════

### Base de Données (INTACTE ✅)
- **2669 picks** total dans tracking_clv_picks
- **1800 picks** en attente de résolution
- **31 combos** dans fg_combo_tracking
- **151 corrélations** dans fg_correlation_pairs

### Services Docker
| Service | Status | Note |
|---------|--------|------|
| monps_postgres | ✅ Healthy | Données OK |
| monps_frontend | ✅ Running | Combos 2.0 déployé |
| monps_backend | ❌ **ERREUR** | DB_NAME incorrect |
| monps_prometheus | ✅ Running | |
| monps_alertmanager | ✅ Running | |
| monps_n8n | ✅ Running | |
| monps_uptime | ✅ Healthy | |

### Git
- **Tag:** v2.19.0-combos-ia
- **Branche:** main (feature/combos-frontend-v2 mergée)
- **Commit:** "feat: Combos 2.0 avec Analyse IA GPT-4o"

═══════════════════════════════════════════════════════════════════════════════
## 🔧 COMMANDES POUR RÉPARER (NOUVELLE SESSION)
═══════════════════════════════════════════════════════════════════════════════

### 1. Réparer le Backend (PRIORITÉ ABSOLUE)
```bash
cd /home/Mon_ps
docker stop monps_backend && docker rm monps_backend
source /home/Mon_ps/monitoring/.env

docker run -d \
  --name monps_backend \
  --network monitoring_monps_network \
  -p 8001:8000 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e DB_HOST="monps_postgres" \
  -e DB_PORT="5432" \
  -e DB_NAME="monps_db" \
  -e DB_USER="monps_user" \
  -e DB_PASSWORD="${DB_PASSWORD}" \
  monitoring-backend

sleep 5
echo "=== TEST ==="
curl -s "http://localhost:8001/api/tracking-clv/dashboard" | head -c 200
```

### 2. Vérifier que tout fonctionne
```bash
# APIs
curl -s "http://localhost:8001/api/combos/suggestions" | head -c 300
curl -s -X POST "http://localhost:8001/api/combos/analyze-ai/28" | head -c 300

# Frontend
curl -s -o /dev/null -w "HTTP: %{http_code}\n" http://localhost:3001/full-gain/combos
```

═══════════════════════════════════════════════════════════════════════════════
## 📈 MATCHS DE CE SOIR - DONNÉES EXTRAITES
═══════════════════════════════════════════════════════════════════════════════

### TOP 3 SINGLES (Score ≥ 95)
1. **Borussia M'gladbach vs RB Leipzig** - dc_12 @1.28 (Score: 100)
2. **Getafe vs Elche CF** - dc_12 @1.45 (Score: 99)
3. **FC Zwolle vs Heerenveen** - dc_12 @1.22 (Score: 98)

### COMBO SUGGÉRÉ
```
M'gladbach vs Leipzig - dc_12 @1.28
FC Zwolle vs Heerenveen - dc_12 @1.22
KV Mechelen vs Standard - dc_12 @1.34
─────────────────────────────────────
COTE COMBINÉE: 2.09
```

### Tous les matchs disponibles (28 Nov)
- Brisbane Roar vs Melbourne Victory
- Kocaelispor vs Genclerbirligi SK
- Wehen Wiesbaden vs Erzgebirge Aue
- FC Zwolle vs Heerenveen
- Borussia Monchengladbach vs RB Leipzig
- KV Mechelen vs Standard Liege
- Como vs Sassuolo
- Metz vs Rennes
- Getafe vs Elche CF
- Vitória SC vs AVS Futebol SAD

═══════════════════════════════════════════════════════════════════════════════
## 🎯 PROCHAINES ÉTAPES
═══════════════════════════════════════════════════════════════════════════════

### Urgent
1. ⚠️ Réparer le backend (DB_NAME)

### Court terme
2. Améliorer affichage analyse IA (markdown rendering)
3. Ajouter bouton Analyse IA dans l'historique aussi
4. Cron job résolution automatique combos

### Moyen terme
5. Dashboard performance combos (ROI, Win Rate)
6. Comparaison résultats réels vs prédictions
7. Intégration Agent Patron dans suggestions

═══════════════════════════════════════════════════════════════════════════════
## 📁 FICHIERS CLÉS
═══════════════════════════════════════════════════════════════════════════════

### Backend
- `backend/api/routes/combos_routes.py` - Routes /save et /analyze-ai
- `backend/api/config.py` - Configuration DB (CORS_ORIGINS)

### Frontend
- `frontend/app/full-gain/combos/page.tsx` - Page principale Combos 2.0

### Config
- `/home/Mon_ps/monitoring/.env` - Variables d'environnement (OPENAI_API_KEY, DB_*)

═══════════════════════════════════════════════════════════════════════════════
## 💡 LEÇONS APPRISES
═══════════════════════════════════════════════════════════════════════════════

1. **Heredoc + TypeScript:** Éviter les template literals `${}`, utiliser + 
2. **Null Safety:** TOUJOURS protéger .toFixed() avec ?? 0
3. **Variables Docker:** Passer explicitement TOUTES les vars d'env
4. **CORS vs 500:** Tester avec curl direct pour distinguer
5. **API Fields:** Vérifier les vrais noms de champs dans la réponse API
6. **Structure Data:** S'assurer que /save et /analyze-ai attendent le même format

═══════════════════════════════════════════════════════════════════════════════
                              FIN DU RÉSUMÉ
═══════════════════════════════════════════════════════════════════════════════

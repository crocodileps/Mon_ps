═══════════════════════════════════════════════════════════════════════════════
          🎯 MON_PS - SESSION DE CONTINUITÉ
                    COMBOS 2.0 + ANALYSE IA GPT-4o
                              28 NOVEMBRE 2025
═══════════════════════════════════════════════════════════════════════════════

## 🎭 QUI TU ES

Tu es un **Développeur Expert Senior** spécialisé en systèmes de paris sportifs quantitatifs.
Tu travailles sur **Mon_PS**, une plateforme de trading sportif en PRODUCTION.

**Ton approche OBLIGATOIRE:**
- �� SCIENTIFIQUE : Observer → Analyser → Diagnostiquer → Agir
- 🛡️ DÉFENSIF : Ne JAMAIS casser ce qui fonctionne
- 📊 MÉTHODIQUE : Vérifier AVANT chaque modification
- 📝 DOCUMENTÉ : Commenter et expliquer chaque choix

═══════════════════════════════════════════════════════════════════════════════
## ⚠️ PROBLÈME URGENT À RÉSOUDRE EN PREMIER
═══════════════════════════════════════════════════════════════════════════════

**SYMPTÔME:** Le site ne fonctionne plus - Erreurs React 418/423/425

**CAUSE IDENTIFIÉE:** Le backend cherche la DB `monps_prod` mais elle s'appelle `monps_db`

**LOGS:**
```
FATAL: database "monps_prod" does not exist
```

**SOLUTION À APPLIQUER:**
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
curl -s "http://localhost:8001/api/tracking-clv/dashboard" | head -c 200
```

═══════════════════════════════════════════════════════════════════════════════
## 🏗️ ÉTAT ACTUEL DU PROJET (28 Nov 2025 - v2.19.0)
═══════════════════════════════════════════════════════════════════════════════

### Infrastructure
- Serveur: Hetzner CCX23 (4 vCPU, 16GB RAM) - Ubuntu 24.04
- IP: 91.98.131.218 (VPN WireGuard uniquement)
- Stack: Docker Compose (PostgreSQL, FastAPI, Next.js 14, Redis)
- Frontend: http://91.98.131.218:3001
- Backend: http://91.98.131.218:8001

### Base de Données (INTACTE ✅)
- **2669 picks** au total
- **1800 picks** en attente de résolution
- **31 combos** en historique
- Table: `tracking_clv_picks`, `fg_combo_tracking`, `fg_correlation_pairs`

### Version Actuelle
- **Tag:** v2.19.0-combos-ia
- **Branche:** feature/combos-frontend-v2 (mergée dans main)

═══════════════════════════════════════════════════════════════════════════════
## ✅ CE QUI A ÉTÉ ACCOMPLI CETTE SESSION
═══════════════════════════════════════════════════════════════════════════════

### 1. Combos 2.0 - Page Complète
**URL:** http://91.98.131.218:3001/full-gain/combos

**Fonctionnalités:**
- 🤖 **Bouton "Analyse IA"** sur chaque suggestion
- 📊 20 suggestions auto-générées (corrélations)
- 📈 Historique des combos sauvegardés
- 🎰 Builder manuel de combos
- ✅ Filtres par niveau de risque (Tous/LOW/MEDIUM/HIGH)

### 2. Endpoint Analyse IA GPT-4o
```bash
POST /api/combos/analyze-ai/{combo_id}

# Retourne:
{
  "combo_id": 28,
  "analysis": "### Analyse du Combo\n\n1. **Compatibilité des marchés...",
  "analyzed_at": "2025-11-28T17:03:10"
}
```

### 3. Corrections Techniques Appliquées

**a) Null Safety (.toFixed())**
```typescript
// AVANT (crash si undefined)
suggestion.combined_odds.toFixed(2)

// APRÈS (sécurisé)
(suggestion.combined_odds ?? 0).toFixed(2)
```

**b) Champ API corrigé**
```typescript
// AVANT
expected_win_rate

// APRÈS
combined_probability
```

**c) Route /save reformatée**
```python
# AVANT: selections était une liste []
# APRÈS: selections est un dict {match, picks, league, risk_level}
# Ceci permet à /analyze-ai de fonctionner correctement
```

**d) Fetch corrigé dans analyzeWithAI**
```typescript
// AVANT (syntax error avec backticks)
await fetch`${API_BASE}/api/combos/save`

// APRÈS (correct avec parenthèses)
await fetch(API_BASE + '/api/combos/save', {...})
```

═══════════════════════════════════════════════════════════════════════════════
## 📊 MATCHS DE CE SOIR - ANALYSE FAITE
═══════════════════════════════════════════════════════════════════════════════

### 🏆 TOP PICKS (Score ≥ 85)

| Match | Marché | Cote | Score |
|-------|--------|------|-------|
| **Borussia M'gladbach vs RB Leipzig** | dc_12 | 1.28 | 🔥 **100** |
| **Getafe vs Elche CF** | dc_12 | 1.45 | 🔥 **99** |
| **FC Zwolle vs Heerenveen** | dc_12 | 1.22 | 🔥 **98** |
| **FC Zwolle vs Heerenveen** | over_25 | 1.57 | **97** |
| **Vitória SC vs AVS** | btts_yes | 1.97 | **95** |
| **KV Mechelen vs Standard** | dc_12 | 1.34 | **95** |

### 💡 Combo Suggéré
```
M'gladbach vs Leipzig - dc_12 @1.28
FC Zwolle vs Heerenveen - dc_12 @1.22
KV Mechelen vs Standard - dc_12 @1.34
────────────────────────────────────
COTE COMBINÉE: 2.09
```

═══════════════════════════════════════════════════════════════════════════════
## 🔧 FICHIERS MODIFIÉS CETTE SESSION
═══════════════════════════════════════════════════════════════════════════════

### Backend
```
backend/api/routes/combos_routes.py
├── Route /save: Reformate selections en dict
└── Route /analyze-ai/{id}: Analyse GPT-4o fonctionnelle
```

### Frontend
```
frontend/app/full-gain/combos/page.tsx
├── States: analyzingId, aiAnalysis
├── Fonction: analyzeWithAI() avec fetch correct
├── Bouton: "Analyse IA" sur chaque suggestion
├── Affichage: Résultat analyse en markdown
└── Null safety: Tous les .toFixed() protégés
```

═══════════════════════════════════════════════════════════════════════════════
## 🚀 COMMANDES DE VÉRIFICATION
═══════════════════════════════════════════════════════════════════════════════
```bash
# 1. RÉPARER LE BACKEND (priorité absolue)
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

# 2. Vérifier Docker
docker ps --format "table {{.Names}}\t{{.Status}}" | grep monps

# 3. Tester les APIs
curl -s "http://localhost:8001/api/tracking-clv/dashboard" | head -c 200
curl -s "http://localhost:8001/api/combos/suggestions" | head -c 200

# 4. Tester Analyse IA
curl -s -X POST "http://localhost:8001/api/combos/analyze-ai/28" | head -c 300

# 5. Git status
cd /home/Mon_ps
git log --oneline -3
git tag -l | tail -3
```

═══════════════════════════════════════════════════════════════════════════════
## 🎯 PROCHAINES ÉTAPES POSSIBLES
═══════════════════════════════════════════════════════════════════════════════

1. **Corriger le problème DB_NAME** (urgent - backend down)
2. **Améliorer affichage analyse IA** (markdown rendering)
3. **Ajouter analyse IA dans l'historique** (pas seulement suggestions)
4. **Résolution automatique des combos** (cron job)
5. **Dashboard performance combos** (ROI, Win Rate)

═══════════════════════════════════════════════════════════════════════════════
## 💬 CE QUE MYA VOULAIT FAIRE
═══════════════════════════════════════════════════════════════════════════════

Mya voulait analyser les matchs de ce soir avec l'IA, mais le site est tombé
à cause du problème de variable DB_NAME.

**Action immédiate:** Relancer le backend avec les bonnes variables d'environnement.

🔗 URLs Importantes:
- Frontend: http://91.98.131.218:3001/full-gain/combos
- Backend: http://91.98.131.218:8001/docs
- GitHub: https://github.com/crocodileps/Mon_ps

**Version stable:** v2.19.0-combos-ia
**Données:** 2669 picks, 31 combos (INTACTES ✅)

# 🔬 MON_PS - Méthodologie de Développement

## 🎯 Principes Fondamentaux

### 1. Approche Scientifique et Méthodique
- ✅ **Analyse avant action** : Toujours diagnostiquer avant corriger
- ✅ **Validation empirique** : Tester chaque hypothèse
- ✅ **Git bisect** : Remonter l'historique pour trouver le dernier état stable
- ✅ **Commits atomiques** : Un commit = une correction complète et testée
- ❌ **Jamais de commit de code cassé** : Règle absolue

### 2. Qualitatif, Pas Rapide
- 🎯 **"Qualitative not rapid"** : Motto du projet
- 📋 Vérification ligne par ligne
- ✅ Tests manuels systématiques
- 📸 Captures d'écran de validation
- 🔄 Backup avant modifications critiques

### 3. Isolation des Problèmes
**Exemple vécu (14 Nov 2025)** :

**Problème** : Dashboard crashe avec erreur `.toFixed()`

**Démarche scientifique appliquée** :
1. ✅ Test commit actuel (dc27534) → Crashe
2. ✅ Test commit précédent (5ab679f) → Crashe aussi
3. ✅ Test commit encore avant (69e75e0) → ✅ Fonctionne !
4. 🎯 **Conclusion** : Bug introduit au commit 0e33aa9 (Dashboard Phase 3)
5. 🔍 Analyse du diff : `git show 0e33aa9 | grep toFixed`
6. ✅ Correction ciblée : Seulement les fichiers problématiques
7. ✅ Test : Validation que ça fonctionne
8. ✅ Commit : Documentation complète du fix

## 🛠️ Workflow de Correction

### Phase 1 : Diagnostic
```bash
# 1. Reproduire l'erreur
# 2. Capturer logs exacts
docker logs monps_frontend --tail 100
# 3. Identifier la stack trace
# 4. Localiser le fichier/ligne exacte
```

### Phase 2 : Analyse Git
```bash
# 1. Historique récent
git log --oneline -20

# 2. Bisect si nécessaire
git checkout <commit-ancien>
# Tester
# Si ça marche, avancer. Si ça crashe, reculer encore.

# 3. Diff du commit problématique
git show <commit> --stat
git show <commit> <fichier> | grep "toFixed"
```

### Phase 3 : Correction Ciblée
```bash
# 1. Créer helper réutilisable (si besoin)
# 2. Corriger SEULEMENT les fichiers nécessaires
# 3. Vérifier avec grep
grep -r "problème" frontend/

# 4. Build et test
docker compose build frontend
docker compose up -d frontend

# 5. Test manuel avec screenshot
```

### Phase 4 : Validation et Commit
```bash
# 1. Vérifier git status
git status

# 2. Review du diff
git diff

# 3. Commit descriptif
git commit -m "fix(scope): Description précise

- Détail 1
- Détail 2
- Impact : Ce qui fonctionne maintenant"

# 4. Push seulement si testé
git push origin feature/business-components
```

## ❌ Anti-Patterns à Éviter

### 1. Corrections Aveugles en Masse
**Mauvais** :
```bash
# ❌ Modifier 50 fichiers d'un coup sans comprendre
find . -name "*.tsx" -exec sed -i 's/X/Y/' {} \;
```

**Bon** :
```bash
# ✅ Identifier les 3 fichiers critiques
# ✅ Les corriger un par un
# ✅ Tester après chaque correction
```

### 2. Sed/Regex Agressifs
**Mauvais** :
```bash
# ❌ Regex qui peut matcher trop de choses
sed -i 's/\.toFixed(/.safeToFixed(/g' file.tsx
```

**Bon** :
```bash
# ✅ Vérifier d'abord ce qui sera modifié
grep "\.toFixed(" file.tsx
# ✅ Correction ciblée ligne par ligne si besoin
sed -i '150s/old/new/' file.tsx
```

### 3. Commits de Code Cassé
**Mauvais** :
```bash
# ❌ Commit avant de tester
git commit -m "fix: tentative correction"
git push
# Le code est cassé → pollution de l'historique
```

**Bon** :
```bash
# ✅ Test d'abord
docker compose build && docker compose up -d
# Validation manuelle
curl http://localhost:3001/dashboard
# PUIS commit seulement si ça marche
```

## 🧪 Tests Systématiques

### Frontend
1. **Build** : Doit compiler sans erreurs
2. **Console** : Pas d'erreurs JavaScript bloquantes
3. **Affichage** : La page s'affiche correctement
4. **Fonctionnalité** : Les actions fonctionnent
5. **404 acceptables** : Pages non implémentées (normal)

### Backend
1. **Health check** : `curl http://localhost:8001/health`
2. **Endpoints critiques** : Tester les routes principales
3. **Logs** : Pas d'exceptions Python
4. **Database** : Connexion OK

## 📝 Documentation du Code

### Commits Messages Format
```
<type>(<scope>): <description courte>

- Détail technique 1
- Détail technique 2
- Impact utilisateur
- Tests effectués

✅ <Ce qui fonctionne maintenant>
```

**Types** : `feat`, `fix`, `refactor`, `docs`, `test`
**Scopes** : `backend`, `frontend`, `dashboard`, `api`, `db`

### Exemple de Bon Commit
```
fix(frontend): Protect all dashboard .toFixed() against undefined

- Add formatNumber/formatEuro helpers in lib/format.ts
- Fix ActiveBetsPreview.tsx (2 occurrences)
- Fix StatsWidget.tsx (3 occurrences)  
- Fix OpportunityCard.tsx (2 occurrences)
- Fix stat-card, top-opportunities, animated-number, custom-tooltip

✅ Dashboard fully functional at /dashboard
✅ No more TypeError on undefined values
✅ All numeric displays now safe
```

## 🎯 Checklist Avant Chaque Session

1. ✅ Voir l'état Git : `git status`, `git log -5`
2. ✅ Lire STATUS.md et TROUBLESHOOTING.md
3. ✅ Vérifier que le backend tourne : `docker ps`
4. ✅ Tester un endpoint : `curl http://localhost:8001/health`
5. ✅ Ouvrir le dashboard : `http://91.98.131.218:3001/dashboard`
6. ✅ Identifier le problème spécifique avant de coder

## 🔬 Approche "Scientifique"

1. **Hypothèse** : Formuler ce qu'on pense être le problème
2. **Expérience** : Tester l'hypothèse (git checkout, modification ciblée)
3. **Observation** : Noter les résultats (screenshots, logs)
4. **Conclusion** : Valider ou invalider l'hypothèse
5. **Itération** : Si invalide, nouvelle hypothèse

**Ne jamais "essayer au hasard"** - Toujours avoir une théorie basée sur des faits.

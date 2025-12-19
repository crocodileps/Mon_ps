# 📋 MÉTHODE DE TRAVAIL HEDGE FUND GRADE

**Document de référence permanent - À suivre pour TOUT travail**
**Créé:** 2025-12-19 | **Dernière MAJ:** 2025-12-19

---

## 🔧 AVANT CHAQUE TRAVAIL

### 1. SÉCURISER GIT
```bash
# Vérifier état actuel
git status
git branch

# Si modifications non committées → les sauvegarder d'abord!
git add [fichiers]
git commit -m "type: description"
git push origin [branche]

# Créer branche dédiée
git checkout -b feature/nom-descriptif
```

### 2. CRÉER DOCUMENTATION
Structure obligatoire:
```
/docs/
├── methodology/
│   └── METHODE_TRAVAIL_HEDGE_FUND.md  (ce fichier - permanent)
├── [NOM_TRAVAIL]/
│   ├── FEUILLE_DE_ROUTE.md            (plan complet)
│   ├── PHASE1_[description].md         (récap phase 1)
│   ├── PHASE2_[description].md         (récap phase 2)
│   └── ...
└── sessions/
    └── YYYY-MM-DD_XX_[TITRE].md        (log session)
```

### 3. DÉFINIR LES PHASES
Chaque travail = N phases avec:
- Objectif clair
- Étapes numérotées
- Status (⏳ En cours, ✅ Terminé, ❌ Bloqué)
- Erreurs rencontrées + solutions
- Commits associés

---

## 📊 TEMPLATE RÉCAP DE PHASE
```markdown
# PHASE N: [TITRE]

**Date:** YYYY-MM-DD
**Status:** EN COURS / TERMINÉ / BLOQUÉ
**Durée:** Xh

## OBJECTIF
[Description claire]

## ÉTAPES
| # | Description | Status | Notes |
|---|-------------|--------|-------|
| N.1 | ... | ✅/⏳/❌ | ... |

## RÉSULTATS
[Métriques avant/après]

## ERREURS RENCONTRÉES
| Erreur | Cause | Solution | Leçon |
|--------|-------|----------|-------|
| ... | ... | ... | ... |

## COMMITS
| Hash | Message |
|------|---------|
| abc123 | ... |

## PROCHAINE ÉTAPE
[Quoi faire ensuite]
```

---

## 📝 RÈGLE DES COMMITS
```bash
# Format: type: description courte
# Types: feat, fix, docs, refactor, test, chore, data

git add [fichiers spécifiques]
git commit -m "type: description - Phase N.X

- Détail 1
- Détail 2"

# Push régulier (sauvegarde cloud)
git push origin [branche]
```

---

## ✅ APRÈS CHAQUE TRAVAIL

### 1. RÉCAP FINAL
- Mettre à jour FEUILLE_DE_ROUTE.md avec status TERMINÉ
- Créer fichier session dans /docs/sessions/
- Lister TOUTES les erreurs/solutions pour mémoire future

### 2. MERGE
```bash
git checkout main
git merge feature/nom-branche --no-ff -m "Merge: [description]"
git push origin main
git branch -d feature/nom-branche  # Optionnel
```

---

## 🔴 RÈGLES CRITIQUES

1. **JAMAIS travailler sur main directement** (sauf hotfix urgent)
2. **TOUJOURS documenter AVANT de coder**
3. **COMMIT fréquents** (au moins 1 par sous-étape)
4. **PUSH régulier** (sauvegarde cloud)
5. **RÉCAP de phase** avant de passer à la suivante
6. **ERREURS documentées** = ne jamais les refaire
7. **VÉRIFIER avant de supprimer** (fichiers, code, données)

---

## 📚 PHILOSOPHIE MYA PRINCIPLE

> "Le temps n'est pas un problème, je veux la perfection."

- Qualité > Rapidité
- Documentation > Mémoire
- Comprendre > Agir vite
- Systématique > Improvisation
- Données > Suppositions

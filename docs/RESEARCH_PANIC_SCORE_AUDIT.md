# 🔬 RAPPORT DE RECHERCHE: PANIC SCORE AUDIT

**Date:** 2025-12-09  
**Version:** V4.6  
**Auteur:** Mya + Claude  

---

## 📋 RÉSUMÉ EXÉCUTIF

Le PANIC Score du Goalkeeper DNA a été audité scientifiquement. 
**Conclusion: Signal FAIBLE pour prédire les Clean Sheets, mais VALIDE pour mesurer la volatilité.**

---

## 🔬 MÉTHODOLOGIE

### Hypothèse initiale
> PANIC élevé → Défense faible → Peu de Clean Sheets

### Données utilisées
- **GK DNA V4.4**: 96 équipes, 33 features
- **Defense DNA**: 96 équipes, tirs subis par période
- **Matchs 2025-26**: 694 matchs (5 ligues top)

### Tests effectués
1. Corrélation PANIC_RAW vs CS%
2. Corrélation PANIC_ADJUSTED vs CS% (ajusté par tirs subis)
3. Corrélation PANIC vs Variance des buts encaissés

---

## 📊 RÉSULTATS

### Test 1: PANIC_RAW vs Clean Sheet %
```
Corrélation: r = -0.010
R² = 0.0001 (0.01% variance expliquée)
→ AUCUN pouvoir prédictif
```

### Test 2: PANIC_ADJUSTED vs Clean Sheet %
```
Formule: PANIC_ADJ = PANIC × (tirs_subis / moyenne_ligue)
Corrélation: r = -0.154
R² = 0.024 (2.4% variance expliquée)
→ Signal TRÈS FAIBLE
```

### Test 3: PANIC vs Variance des buts (session précédente)
```
Corrélation: r = 0.325
R² = 0.106 (10.6% variance expliquée)
→ Signal SIGNIFICATIF
```

---

## 💡 DÉCOUVERTE CLÉ

> **Le PANIC Score mesure la VOLATILITÉ, pas le NIVEAU défensif.**

### Explication
- PANIC élevé → GK fait des erreurs QUAND il est sollicité
- Mais si l'équipe domine (peu de tirs subis), le PANIC s'active rarement
- Résultat: Bayern Munich a PANIC=35.9 mais 54% CS (peu sollicité)

### Paradoxe Bayern résolu
```
Bayern Munich:
- PANIC_RAW = 35.9 (semble vulnérable)
- Tirs subis = 7.3/match (ratio 0.75)
- PANIC_ADJ = 27.0 (plus cohérent)
- CS% réel = 53.8% (forteresse)
```

---

## 🎯 RECOMMANDATIONS

### ❌ NE PAS UTILISER PANIC POUR:
- Prédire Clean Sheet %
- Sélectionner paris pré-match sur CS
- Déterminer le profil défensif (FORTRESS/LEAKY)

### ✅ UTILISER PANIC POUR:
- Identifier équipes à résultats imprévisibles (haute variance)
- Live betting: "Next Goal après corner" si PANIC élevé
- Tag informatif: "⚠️ GK Volatil"

### Métriques à utiliser pour prédiction
| Objectif | Métrique recommandée |
|----------|---------------------|
| Clean Sheet | CS%, xGA/90, resist_global |
| Late Goal | late_pct, gk_save_rate_76_90 |
| Over/Under | GA/90, variance |
| GK Quality | gk_percentile, save_rate |

---

## 📁 IMPACT SUR LE CODE

### team_profiler.py
✅ **Déjà correct** - N'utilise pas PANIC pour les décisions

### engineer.py
✅ **Conserver** - PANIC reste comme feature ML (peut aider en ensemble)

### Ajout recommandé
Ajouter `gk_panic_tag` comme information narrative:
```python
if panic_score >= 35:
    narrative_tag = "⚠️ GK VOLATIL - Imprévisible sous pression"
elif panic_score >= 25:
    narrative_tag = "🟡 GK MOYEN - Performance variable"
else:
    narrative_tag = "✅ GK STABLE - Fiable"
```

---

## 📚 LEÇONS APPRISES

1. **Corrélation ≠ Causalité**: PANIC corrélé avec variance, pas avec niveau
2. **Contexte compte**: Même GK "médiocre" peut avoir bons résultats si peu sollicité
3. **Occam's Razor**: CS% et xGA sont plus simples et plus prédictifs que PANIC
4. **Team-Centric**: L'équipe protège le GK, pas l'inverse

---

## �� RÉFÉRENCES

- Session audit: 2025-12-09
- Fichiers analysés:
  - `/home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v4_4_by_team.json`
  - `/home/Mon_ps/data/defense_dna/team_defense_dna_2025_fixed.json`
  - `/home/Mon_ps/agents/defense_v2/team_profiler.py`
  - `/home/Mon_ps/agents/defense_v2/features/engineer.py`

---

*"Savoir jeter un modèle complexe pour revenir à un modèle simple et robuste - c'est la marque d'un grand Quant."*

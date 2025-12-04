# 🎯 QUANT SYSTEM V2.0 - SYNTHÈSE COMPLÈTE

## �� DÉCOUVERTES CLÉS DE L'ANALYSE

### 1. Steam Moves = 66.7% Précision
Le marché (Pinnacle) est **sharp**. Quand il y a un mouvement de probabilité > 4%, 
le marché a raison **2/3 du temps**.

### 2. Distribution des Matchs (30 jours)

| Classification | Matchs | Avg Shift | Action |
|----------------|--------|-----------|--------|
| 🟢 NORMAL | 586 | 0.6% | Inclure |
| 🟡 NOTABLE | 64 | 5.5% | Inclure + apprendre |
| 🔴 SUSPICIOUS | 25 | 13.3% | Exclure du training |

### 3. Révision de nos "BAD_CALL"

| Match | Classification Initiale | Prob Shift | Classification Révisée |
|-------|------------------------|------------|----------------------|
| Arsenal vs Brentford | BAD_CALL | 14.3% | MARKET_EFFICIENCY ✅ |
| West Ham vs Liverpool | BAD_CALL | 9.9% | MARKET_EFFICIENCY ✅ |
| Bournemouth vs Everton | N/A | 10.4% | MARKET_EFFICIENCY ✅ |

**Ratio Noise/Signal révisé: 3/4 = 0.75** (vs 0.50 initial)
→ Plus de malchance que d'erreurs de modèle !

---

## 🔧 NOUVELLES TABLES CRÉÉES

### 1. `match_steam_analysis`
Analyse automatique des mouvements Pinnacle pour chaque match.
- Opening/Closing odds
- Probabilités implicites
- Prob shift total
- Classification (CLEAN/MARKET_EFFICIENCY/SUSPICIOUS)

### 2. `match_events`
Événements du match (à peupler via API-Football).
- Cartons rouges, buts, blessures
- Permet de détecter GAME_STATE_SHOCK

### 3. `prediction_validation_v2`
Classification 7 nuances + intégration steam.
- UNLUCKY: FINISHING_NOISE, KEEPER_ALPHA, GAME_STATE_SHOCK
- BAD_CALL: TACTICAL_MISMATCH, MARKET_EFFICIENCY, FAKE_DOMINANCE
- LUCKY: FALSE_ALPHA

### 4. `quant_kpis`
KPIs quotidiens pour monitoring.
- CLV%, xROI, Noise/Signal ratio

---

## 📈 7 NUANCES DE CLASSIFICATION

### A. UNLUCKY (Process correct, ne rien changer)

| Code | Sous-catégorie | Définition | Action |
|------|----------------|------------|--------|
| FINISHING_NOISE | Bruit de Finition | xG > 2.5 mais score 0-0 | DO_NOTHING |
| KEEPER_ALPHA | Gardien Surperf. | Arrêts > 8, xG against > 2.5 | IGNORE_DEFENSE |
| GAME_STATE_SHOCK | Choc Exogène | Carton rouge < 20' | EXCLUDE_FROM_DATA |

### B. BAD_CALL (Erreur modèle, action requise)

| Code | Sous-catégorie | Définition | Action |
|------|----------------|------------|--------|
| TACTICAL_MISMATCH | Erreur Tactique | xG combiné < 1.5, match fermé | ADJUST_WEIGHTS |
| MARKET_EFFICIENCY | Défaite CLV | Prob shift > 4% contre nous | ADD_CLV_FILTER |
| FAKE_DOMINANCE | Possession Stérile | RTI élevé mais xG faible | INCREASE_EFFICIENCY |

### C. LUCKY (Faux positif, attention)

| Code | Sous-catégorie | Définition | Action |
|------|----------------|------------|--------|
| FALSE_ALPHA | Faux Signal | Gagné par penalty/CSC, xG < 1.5 | TREAT_AS_LOSS |

---

## 🚨 SYSTÈME D'ALERTES À IMPLÉMENTER
```python
STEAM_ALERTS = {
    'STEAM_AGAINST': {
        'condition': 'prob_shift > 4% AND steam != our_bet_direction',
        'message': '⚠️ Steam move CONTRE notre bet',
        'action': 'REDUCE_STAKE_50% ou SKIP'
    },
    'STEAM_WITH': {
        'condition': 'prob_shift > 4% AND steam == our_bet_direction',
        'message': '✅ Steam move AVEC notre bet',
        'action': 'CONFIDENCE_BOOST (+10% stake)'
    },
    'SUSPICIOUS_LINE': {
        'condition': 'prob_shift > 8%',
        'message': '🔴 Mouvement suspect (possible inside info)',
        'action': 'SKIP + LOG pour investigation'
    }
}
```

---

## 📊 KPIs QUANT À SURVEILLER

| KPI | Formule | Objectif | Signification |
|-----|---------|----------|---------------|
| **CLV%** | (Closing - Opening) / Opening | > 0% | On bat le marché |
| **xROI** | ROI basé sur xG | ~ ROI réel | Variance normale |
| **Noise/Signal** | UNLUCKY / BAD_CALL | > 1.0 | Plus de malchance que d'erreurs |
| **Steam Accuracy** | Steam correct / Total | Monitor | Marché fiable |

### Interprétation xROI vs ROI

- **xROI > ROI réel** → Drawdown (malchance), ça va remonter
- **xROI < ROI réel** → Sur-régime (chance), prépare-toi à perdre
- **xROI ≈ ROI réel** → Variance normale

---

## 🎯 PROCHAINES ÉTAPES

### Phase 1: Intégration Steam (Priorité Haute)
- [ ] Ajouter filtre steam dans Orchestrator V11
- [ ] Alertes temps réel si prob_shift > 4%
- [ ] Ajustement automatique du stake

### Phase 2: Événements Match
- [ ] Scraper API-Football pour match_events
- [ ] Détecter cartons rouges < 20'
- [ ] Exclure matchs dénaturés

### Phase 3: Dashboard
- [ ] Page Grafana pour KPIs Quant
- [ ] Historique Noise/Signal
- [ ] Tracking CLV

### Phase 4: Améliorations Modèle
- [ ] EMA Time Decay (5 derniers matchs = 50% poids)
- [ ] Game State xG (si données tir-par-tir disponibles)
- [ ] RTI/Lethality dans scoring

---

## 📁 FICHIERS CRÉÉS

- `quant_system_v2.py` - Classes et fonctions V2.0
- `QUANT_SYSTEM_V2_SUMMARY.md` - Ce document
- `PROPOSAL_V2_QUANT_SYSTEM.md` - Proposition initiale
- `deep_analysis_30days.py` - Script d'analyse

## 📦 TABLES SQL
```sql
-- Voir le contenu
SELECT * FROM match_steam_analysis WHERE prob_shift_total > 8 ORDER BY prob_shift_total DESC;
SELECT * FROM match_events WHERE is_game_changing = true;
SELECT * FROM prediction_validation_v2 WHERE category = 'BAD_CALL';
SELECT * FROM quant_kpis ORDER BY date DESC LIMIT 7;
```

---

*Généré le: 2025-12-04*
*Version: V2.0*
*Branch: feature/v11-deep-analysis*

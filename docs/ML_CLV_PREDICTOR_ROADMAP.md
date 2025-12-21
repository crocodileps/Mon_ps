# ML CLV PREDICTOR ADN-AWARE - ROADMAP

## STATUT: PHASE COLLECTE (Patience Hedge Fund)

### Objectif
Construire un ML qui prédit le CLV basé sur la COLLISION ADN unique
= home_team.ADN × away_team.ADN × contexte

### Philosophie Non-Négociable
- Chaque équipe = ADN UNIQUE (30+ dimensions)
- Chaque collision = Interaction ADN × ADN UNIQUE
- PAS de compression, PAS de catégories, PAS de généralisations
- Le ML apprend les INTERACTIONS, pas des formules simplistes

### Données Requises
- Minimum: n > 500 picks avec ADN complet (home + away)
- Actuellement: n = 110 (22% de 494 picks BTTS)
- Objectif: Mi-Mars 2025

### Pourquoi Attendre ?
- n=110 avec 30 features = ratio 0.27 (DANGER overfitting)
- Règle ML: minimum 10-20 samples par feature
- Toute tentative maintenant = soit overfitting, soit simplification
- La PATIENCE est la bonne stratégie Hedge Fund

### Progression

| Date | n (ADN complet) | % Objectif | Notes |
|------|-----------------|------------|-------|
| 2024-12-21 | 110 | 22% | Baseline |
| (à remplir) | | | |

### Insights Collectés (Sans ML)

#### BTTS NO - Edge Positif Confirmé
- CLV moyen: +38.64% (n=255)
- 84% des picks sont CLV positif
- Asymétrie favorable

#### BTTS YES - Edge Négatif À Investiguer
- CLV moyen: -13.80% (n=239)
- Seulement 15% CLV positif
- Hypothèse: matchs déséquilibrés (DOMINANT vs RELEGATED)

### Prochaines Étapes
1. [ ] Continuer collecte picks Top 5 Leagues
2. [ ] Tracker progression n chaque semaine
3. [ ] À n=500: construire ML ADN-AWARE
4. [ ] Valider avec backtesting

---
Créé: 2024-12-21
Dernière mise à jour: 2024-12-21
Philosophie: "Le temps n'est pas un problème, je veux la perfection."

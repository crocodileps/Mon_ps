# PHASE 2.6: TEAM MARKET PROFILER - COMPLÈTE ✅

## Résumé
Le **Team Market Profiler** transforme Mon_PS d'un système "one-size-fits-all" en un **système de ciblage précis par équipe**.

## Données Créées

| Table | Contenu | Records |
|-------|---------|---------|
| `team_market_profiles` | ADN marché par équipe | 1,188 |
| `team_market_context` | Modificateurs Home/Away | 2,352 |
| `h2h_market_patterns` | Patterns H2H par marché | 222 |

## Top Équipes par Marché

**BTTS NO:** Lazio 92%, Real Oviedo 79%, Roma 77%
**OVER 2.5:** Bayern 100%, Barcelona 93%, Stuttgart 75%
**UNDER 2.5:** Angers 79%, Como 77%, Lazio 77%

## Market Convergence Engine V2

| Action | Score Modifier | Condition |
|--------|----------------|-----------|
| STRONG_BET | +20 à +25 | Convergence parfaite |
| NORMAL_BET | +10 | Marchés compatibles |
| SMALL_BET | +5 | Terrain d'entente HV |
| SKIP | -15 | Pas de qualité |
| NO_BET | -30 | Clash Over/Under |

## Interface Orchestrator
```python
from market_convergence_engine import MarketConvergenceEngine
engine = MarketConvergenceEngine()
result = engine.get_orchestrator_modifier('Liverpool', 'Arsenal', 'btts_yes')
# {'score_modifier': +5, 'recommended_market': 'under_35', ...}
```

## Fichiers

- `backend/scripts/analytics/team_market_profiler.py`
- `backend/scripts/analytics/market_convergence_engine.py`

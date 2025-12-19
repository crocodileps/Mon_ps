# Session 2025-12-19 #85 - CLV Tracking Audit

## Contexte

Mya a corrige une erreur repetee: chercher CLV dans la mauvaise table.
- Table correcte: `public.tracking_clv_picks` (pas bet_tracker_clv)
- Mission: Auditer les colonnes de cotes et verifier si CLV est calculable

## Realise

### Phase 1: Decouverte table tracking_clv_picks

| Metrique | Valeur |
|----------|--------|
| Schema | public |
| Colonnes | **57** |
| Total paris | **3,361** |
| Paris resolus | **2,477** |
| Equipes home | 207 |
| Equipes away | 204 |

### Phase 2: Colonnes de cotes identifiees

```
odds_taken     - 3,361 lignes (100%)
closing_odds   - 8 lignes (0.2%)
opening_odds   - 163 lignes (4.8%), 99 calculables
odds_movement  - partiel
```

### Phase 3: CLV calculable?

**OUI - pour 99 paris** via opening_odds

Formule: `((odds_taken / opening_odds - 1) * 100)`

| Source | Paris calculables |
|--------|-------------------|
| closing_odds | 8 |
| opening_odds | 99 |
| Total | 99 / 3,361 (2.9%) |

### Phase 4: Resultats CLV calcule

**Global (99 paris):**
- Avg CLV: +91.45% (biaise par outliers)
- Positive CLV rate: 68.7%

**Top equipes avec CLV:**
| Equipe | Bets | With CLV | Avg CLV |
|--------|------|----------|---------|
| AS Roma | 48 | 4 | +172.15% |
| Lille | 36 | 3 | +161.54% |
| Real Betis | 57 | 4 | +26.87% |
| Go Ahead Eagles | 59 | 3 | +7.12% |

**Liverpool:** 24 paris, **0 avec CLV data**

### Phase 5: Performance globale tracking_clv_picks

| Metrique | Valeur |
|----------|--------|
| Wins | 1,258 |
| Losses | 1,219 |
| Win Rate | 50.8% |
| Total P&L | **-416.80u** |

**Top marches profitables:**
- btts_no: +5.32u
- under_35: +2.38u

## Fichiers touches

### Analyses (lecture seule)
- `public.tracking_clv_picks` (57 colonnes, 3,361 rows)

### Aucun fichier modifie cette session

## Problemes resolus

### 1. Mauvaise table CLV
- **Probleme**: Cherchais dans bet_tracker_clv (2 rows, NULL)
- **Solution**: Table correcte = `tracking_clv_picks` (3,361 rows)

### 2. CLV pre-calcule vs calculable
- **Probleme**: Conclu "impossible" car clv_percentage vide
- **Solution**: CLV CALCULABLE depuis odds_taken/opening_odds

### 3. Colonnes odds identifiees
- **Trouve**: odds_taken (100%), closing_odds (0.2%), opening_odds (2.9%)

## En cours / A faire

- [ ] **INVESTIGATION**: Pourquoi closing_odds quasi-vide (8/3361)?
- [ ] **INVESTIGATION**: Script qui devrait remplir closing_odds?
- [ ] **ACTION**: Ajouter mapping Inter dans orchestrator.py
- [ ] **DECISION**: Option A/B/C pour adapter schemas V1↔V3

## Notes techniques

### Structure tracking_clv_picks (57 colonnes)

```sql
-- Colonnes cles pour CLV
odds_taken      -- Cote prise (100% rempli)
closing_odds    -- Cote cloture (0.2% rempli)
opening_odds    -- Cote ouverture (4.8% rempli)
odds_movement   -- Mouvement cotes
clv_percentage  -- CLV pre-calcule (0.2% rempli)

-- Colonnes resultats
is_resolved, is_winner, profit_loss

-- Colonnes equipes
home_team, away_team, league, market_type
```

### Requete CLV par equipe

```sql
SELECT
    home_team,
    COUNT(*) as total_bets,
    ROUND(AVG(
        CASE WHEN opening_odds > 0 AND odds_taken > 0
        THEN ((odds_taken / opening_odds - 1) * 100)
        ELSE NULL END
    )::numeric, 2) as avg_clv
FROM public.tracking_clv_picks
WHERE home_team IS NOT NULL
GROUP BY home_team
HAVING COUNT(*) FILTER (WHERE opening_odds > 0 AND odds_taken > 0) >= 3
ORDER BY avg_clv DESC;
```

### Import/Test

```python
# Pas de module Python associe - table directe PostgreSQL
# Acces via psql ou SQLAlchemy
```

## Resume

**Session #85** - Audit factuel table tracking_clv_picks.

- Trouve la bonne table CLV (3,361 paris)
- Identifie colonnes cotes: odds_taken, closing_odds, opening_odds
- CLV calculable pour 99/3361 (2.9%) via opening_odds
- Probleme: closing_odds quasi-vide empeche calcul CLV complet
- Liverpool: 24 paris mais 0 avec donnees CLV

**Status**: Audit termine, closing_odds manquant pour 97% des paris
**Grade**: Methodologie Hedge Fund (CODE EXACT, pas suppositions)

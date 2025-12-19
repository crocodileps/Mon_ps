# Session 2025-12-19 #86 - CLV Enrichment Script

## Contexte

Mya a demande de:
1. Trouver la source des closing odds pour calculer le CLV
2. Auditer la qualite des donnees
3. Creer un script d'enrichissement Hedge Fund Grade
4. Etendre la couverture a tous les marches possibles

## Realise

### Phase 1: Investigation Sources Closing Odds

Trouve 7 tables d'odds:
- **odds_history** (384,287 rows) - 1X2 avec 65 bookmakers
- **odds_totals** (119,945 rows) - Over/Under
- **match_steam_analysis** (675 rows) - Opening + Closing pre-calcules
- odds_btts (0 rows) - VIDE
- odds_spreads (1,722 rows) - Asian Handicap
- odds_latest (0 rows) - VIDE
- fg_odds_snapshots (0 rows) - VIDE

### Phase 2: Audit Qualite

- match_steam_analysis utilise **Pinnacle** (bookmaker sharp)
- 54% des matchs avec 1 seul snapshot (unreliable)
- 14% de big diff (>0.20) vs moyenne all-books
- Anomalie CLV +91% expliquee: opening_odds bugue (utilisait home_odds pour tous les marches)

### Phase 3: Script Enrichissement Cree

`/home/Mon_ps/scripts/enrich_closing_odds.py`

4 etapes d'enrichissement:
1. 1X2 depuis match_steam_analysis (snapshots >= 3)
2. 1X2 depuis odds_history (Pinnacle)
3. Over/Under depuis odds_totals (Pinnacle)
4. Double Chance calcule depuis 1X2 (formules)

### Phase 4: Extension Couverture

Formules Double Chance ajoutees:
- dc_1x = 1 / (1/home + 1/draw)
- dc_x2 = 1 / (1/draw + 1/away)
- dc_12 = 1 / (1/home + 1/away)

### Resultats Dry-Run

| Source | Picks Enrichables |
|--------|-------------------|
| 1X2 steam_analysis | 571 |
| 1X2 odds_history | 691 |
| Over/Under | 828 |
| Double Chance | 771 |
| **TOTAL** | **2,861 (85.1%)** |

Non enrichable:
- BTTS: 510 picks (odds_btts vide)
- DNB: 94 picks (1 seul match avec Pinnacle)

## Fichiers touches

### Crees
- `/home/Mon_ps/scripts/enrich_closing_odds.py` - Script d'enrichissement CLV

### Analyses (lecture seule)
- `public.odds_history` (384K rows)
- `public.odds_totals` (120K rows)
- `public.match_steam_analysis` (675 rows)
- `public.tracking_clv_picks` (3,361 rows)

## Problemes resolus

### 1. Source closing_odds introuvable
- **Probleme**: closing_odds quasi-vide (8/3361)
- **Solution**: odds_history + odds_totals + calcul DC

### 2. Anomalie CLV +91%
- **Probleme**: CLV moyen irrealiste
- **Solution**: Bug identifie - opening_odds utilisait home_odds pour tous marches

### 3. Couverture limitee 53%
- **Probleme**: Seulement 1X2 et Over/Under
- **Solution**: Ajoute Double Chance calcule (+771 picks, 85% total)

## En cours / A faire

- [ ] **EXECUTER EN PRODUCTION**: `python3 scripts/enrich_closing_odds.py`
- [ ] Analyser resultats CLV apres enrichissement
- [ ] Investiguer scraping BTTS (510 picks non couverts)
- [ ] Investiguer Asian Handicap pour DNB (94 picks)

## Notes techniques

### Tables principales pour CLV

```sql
-- Source 1X2
SELECT * FROM odds_history
WHERE bookmaker = 'Pinnacle';

-- Source Over/Under
SELECT * FROM odds_totals
WHERE bookmaker = 'Pinnacle';

-- Double Chance (calcul)
dc_1x = 1 / (1/home_odds + 1/draw_odds)
dc_x2 = 1 / (1/draw_odds + 1/away_odds)
dc_12 = 1 / (1/home_odds + 1/away_odds)
```

### Commande pour executer

```bash
# Dry-run (simulation)
python3 /home/Mon_ps/scripts/enrich_closing_odds.py --dry-run

# Production
python3 /home/Mon_ps/scripts/enrich_closing_odds.py
```

### Verification apres execution

```sql
SELECT
    market_type,
    COUNT(*) as total,
    COUNT(closing_odds) as with_closing,
    COUNT(clv_percentage) as with_clv,
    ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv
FROM tracking_clv_picks
GROUP BY market_type
ORDER BY total DESC;
```

## Resume

**Session #86** - Creation script d'enrichissement CLV Hedge Fund Grade.

- Investigate 7 tables d'odds, trouve sources pour 85% des picks
- Cree script Python avec 4 etapes d'enrichissement
- Ajoute calcul Double Chance (771 picks supplementaires)
- Couverture: 0.2% -> 85.1% (de 8 a 2,861 picks)
- BTTS/DNB non couverts (aucune source disponible)

**Status**: Script pret, en attente validation Mya pour production
**Prochain**: Executer le script et analyser les resultats CLV

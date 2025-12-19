# Betexplorer Scraper - Phase 1 Analysis Report

**Date:** 2025-12-19
**Status:** ANALYSIS COMPLETE

---

## 1. LIGUES MON_PS PRIORITAIRES

| Ligue Mon_PS | Picks | URL Betexplorer |
|--------------|-------|-----------------|
| soccer_spain_la_liga | 115 | /football/spain/laliga/ |
| soccer_uefa_europa_league | 98 | /football/europe/europa-league/ |
| soccer_germany_bundesliga | 83 | /football/germany/bundesliga/ |
| soccer_france_ligue_one | 80 | /football/france/ligue-1/ |
| soccer_italy_serie_a | 59 | /football/italy/serie-a/ |
| soccer_netherlands_eredivisie | 55 | /football/netherlands/eredivisie/ |
| soccer_uefa_europa_conference_league | 50 | /football/europe/europa-conference-league/ |
| soccer_australia_aleague | 40 | /football/australia/a-league/ |
| soccer_portugal_primeira_liga | 38 | /football/portugal/liga-portugal/ |
| soccer_turkey_super_league | 25 | /football/turkey/super-lig/ |
| soccer_uefa_champs_league | 22 | /football/europe/champions-league/ |
| soccer_epl | 17 | /football/england/premier-league/ |
| soccer_greece_super_league | 16 | /football/greece/super-league/ |
| soccer_japan_j_league | 15 | /football/japan/j1-league/ |
| soccer_belgium_first_div | 13 | /football/belgium/jupiler-pro-league/ |
| soccer_germany_liga3 | 13 | /football/germany/3-liga/ |

**Note:** ~2000 picks ont `league = NULL` - nécessite investigation séparée.

---

## 2. ACCES AU SITE

| Métrique | Valeur |
|----------|--------|
| **Status HTTP** | 200 OK |
| **Cloudflare** | Non détecté |
| **reCAPTCHA** | Non détecté |
| **hCaptcha** | Non détecté |
| **Rate limiting** | Non détecté (mais recommandé 0.5-1s delay) |
| **Cookies requis** | Non (cookie `my_timezone` optionnel) |
| **JavaScript requis** | **NON** |

---

## 3. STRUCTURE URL MATCH

### Pattern URL page match
```
https://www.betexplorer.com/football/{country}/{league}/{team1}-{team2}/{match_id}/
```

**Exemple:**
```
https://www.betexplorer.com/football/england/premier-league/manchester-united-bournemouth/n1p7rqmT/
```

### Pattern URL API cotes (AJAX)
```
https://www.betexplorer.com/match-odds/{match_id}/{page}/{market_type}/odds/?lang=en
```

**Paramètres:**
- `match_id`: ID unique du match (ex: `n1p7rqmT`)
- `page`: 0 ou 1 (page de résultats)
- `market_type`: `1x2`, `bts`, `ou`, `ah`, `dc`, `dnb`, `ha`
- `lang`: `en` (anglais)

**Exemple:**
```
https://www.betexplorer.com/match-odds/n1p7rqmT/1/bts/odds/?lang=en
```

---

## 4. MARCHES DISPONIBLES

| Marché | Endpoint | Lignes/Options |
|--------|----------|----------------|
| **1X2** | `/1x2/` | 1, X, 2 |
| **BTTS** | `/bts/` | Yes, No |
| **Over/Under** | `/ou/` | 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5 |
| **Double Chance** | `/dc/` | 1X, X2, 12 |
| **DNB** | `/dnb/` | Home, Away |
| **Asian Handicap** | `/ah/` | Multiple lines |
| **Home/Away** | `/ha/` | Home, Away (H2H) |

---

## 5. SELECTEURS CSS / DATA ATTRIBUTES

### Réponse API
```json
{
  "odds": "<div>...HTML content...</div>"
}
```

### Structure HTML des cotes

```html
<table class="table-main">
  <tr>
    <td class="h-text-left">Bookmaker Name</td>
    <td class="table-main__detail-odds"
        data-odd="1.45"
        data-bookie="bet365.de"
        data-bookie-id="1053"
        data-pos="y"
        data-created="15,12,2025,16,19"
        data-hcp="E-13-2-0-0-0">
    </td>
  </tr>
</table>
```

### Sélecteurs clés

| Élément | Sélecteur |
|---------|-----------|
| **Tableau principal** | `table.table-main` |
| **Cellule cote** | `td[data-odd]` |
| **Valeur cote** | `data-odd` attribute |
| **Nom bookmaker** | `data-bookie` attribute |
| **ID bookmaker** | `data-bookie-id` attribute |
| **Position (Yes/No, 1/X/2)** | `data-pos` attribute |
| **Timestamp** | `data-created` attribute |
| **Ligne O/U** | `data-hcp` attribute (format: `E-{bt}-{sc}-{x}-{line}-0`) |

### Valeurs data-pos par marché

| Marché | Valeurs |
|--------|---------|
| 1X2 | `1`, `0`, `2` (Home, Draw, Away) |
| BTTS | `y`, `n` (Yes, No) |
| O/U | `o`, `u` (Over, Under) |
| DC | `10`, `02`, `12` (1X, X2, 12) |
| DNB | `1`, `2` (Home, Away) |

---

## 6. BOOKMAKERS DISPONIBLES

Exemple de bookmakers trouvés sur les matchs:
- bet365.de
- betano.de
- bet-at-home.de
- neobet

**Note:** La liste varie selon la région géographique de l'IP.

---

## 7. RECOMMANDATION TECHNIQUE

### Stack recommandé
```
✅ requests + BeautifulSoup (lxml)
❌ Selenium/Playwright NON NÉCESSAIRE
```

### Configuration

```python
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json, text/javascript, */*; q=0.01'
}

# Rate limiting recommandé
DELAY_BETWEEN_REQUESTS = 0.5  # secondes
```

### Workflow de scraping

1. **Charger page results de la ligue**
   ```
   GET /football/{country}/{league}/results/
   ```

2. **Extraire les IDs de matchs**
   ```python
   # Pattern: href="/football/.../team1-team2/{match_id}/"
   ```

3. **Pour chaque match, charger les cotes**
   ```
   GET /match-odds/{match_id}/1/{market}/odds/?lang=en
   ```

4. **Parser les cotes**
   ```python
   soup = BeautifulSoup(response.json()['odds'], 'lxml')
   odds = soup.find_all(attrs={'data-odd': True})
   ```

---

## 8. ESTIMATION VOLUME

| Élément | Estimation |
|---------|------------|
| Matchs par ligue/jour | ~5-15 |
| Marchés par match | 7 (1X2, BTS, O/U, DC, DNB, AH, HA) |
| Requêtes par match | ~8-10 |
| Délai entre requêtes | 0.5s |
| **Temps par match** | ~5-10s |
| **Temps par ligue** | ~1-3 min |

---

## 9. RISQUES ET MITIGATIONS

| Risque | Mitigation |
|--------|------------|
| Rate limiting | Délai 0.5-1s entre requêtes |
| IP ban | Rotation proxy (si nécessaire) |
| Structure HTML change | Tests de régression, alertes |
| Match ID non trouvé | Fallback: recherche par équipes + date |
| Cotes nulles | Validation data-odd > 1.0 |

---

## 10. PROCHAINES ETAPES (Phase 2)

1. [ ] Implémenter `BetexplorerScraper` class
2. [ ] Fonction `get_match_id(home_team, away_team, date)`
3. [ ] Fonction `get_odds(match_id, market_type)`
4. [ ] Parser pour extraire closing odds (dernière mise à jour)
5. [ ] Intégration avec `enrich_closing_odds.py`
6. [ ] Tests sur historique récent
7. [ ] Monitoring et alertes

---

## FICHIERS CREES

```
/home/Mon_ps/scrapers/betexplorer/
├── league_mapping.py     # Mapping ligues + marchés
└── PHASE1_ANALYSIS.md    # Ce rapport
```

---

**Status:** READY FOR PHASE 2 IMPLEMENTATION

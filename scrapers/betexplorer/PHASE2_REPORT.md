# Betexplorer Scraper - Phase 2 Report

**Date:** 2025-12-19
**Status:** HEDGE FUND GRADE COMPLETE

---

## 1. SAISON VÉRIFIÉE

| Élément | Valeur |
|---------|--------|
| **Saison courante** | 2025/2026 |
| **Page /results/** | Matchs récents (15/12/2025) |
| **Équipes promues détectées** | Leeds, Sunderland, Burnley |
| **Format date** | `data-dt="DD,MM,YYYY,HH,MM"` |

---

## 2. MODULE ANTI-BAN

**Fichier:** `/home/Mon_ps/scrapers/betexplorer/anti_ban.py`

| Configuration | Valeur |
|---------------|--------|
| **Min delay** | 2.0 secondes |
| **Max delay** | 5.0 secondes |
| **Max requests/hour** | 100 |
| **User-Agent pool** | 12 agents |
| **Retry** | 3 tentatives, backoff exponentiel |

### Fonctionnalités

```python
# Rate limiter avec tracking
rate_limiter = RateLimiter()
rate_limiter.wait()  # Attente automatique

# Headers réalistes
headers = get_headers(referer=url, ajax=True)

# Retry automatique
@retry_with_backoff(max_retries=3)
def fetch_data():
    ...

# Session persistante
session = ScraperSession()
resp = session.get("/match-odds/...")
```

---

## 3. MATCH FINDER

**Fichier:** `/home/Mon_ps/scrapers/betexplorer/match_finder.py`

### Test de similarité

| Mon_PS | Betexplorer | Score |
|--------|-------------|-------|
| Liverpool | Liverpool FC | 1.00 |
| Man United | Manchester Utd | 1.00 |
| Tottenham | Tottenham Hotspur | 1.00 |
| Wolves | Wolverhampton Wanderers | 1.00 |
| Brighton | Brighton and Hove Albion | 1.00 |

### Test Premier League

```
Found 160 matches
- Manchester Utd vs Bournemouth (ID: n1p7rqmT)
- Brentford vs Leeds (ID: 0pMPV53N)
- Crystal Palace vs Manchester City (ID: ILhjnRm4)
- Nottingham vs Tottenham (ID: 6oRwwNAj)
- Sunderland vs Newcastle (ID: buEP0Q2c)
```

### Fonctionnalités

```python
# Trouver match_id depuis nos données
match_id = find_betexplorer_match_id(
    home_team="Manchester United",
    away_team="Bournemouth",
    match_date=datetime(2025, 12, 15, 21, 0),
    league="soccer_epl"
)
# Returns: "n1p7rqmT"

# Récupérer tous les matchs d'une ligue
matches = get_league_matches("/football/england/premier-league/", results=True)
```

---

## 4. VALIDATION TRIPLE - HEDGE FUND GRADE

**Fichier:** `/home/Mon_ps/scrapers/betexplorer/match_validator.py`

### Seuils stricts

| Critère | Seuil | Justification |
|---------|-------|---------------|
| **Similarité équipes** | >= 80% | Évite Real Madrid = Real Betis (67%) |
| **Différence date** | <= 1 jour | Évite match aller = match retour |
| **Checks requis** | 3/3 | Home + Away + Date tous validés |

### Test final multi-ligues (18/18 = 100%)

```
Premier League:  3/3
La Liga:         3/3
Bundesliga:      3/3
Serie A:         3/3
Ligue 1:         3/3
Eredivisie:      3/3
```

### Fonctionnalités

```python
from match_validator import validate_match, MIN_TEAM_SIMILARITY

# Triple validation
is_valid, details = validate_match(
    our_home="Manchester United",
    our_away="Bournemouth",
    our_date=datetime(2025, 12, 15),
    be_home="Manchester Utd",
    be_away="Bournemouth",
    be_date=datetime(2025, 12, 15)
)
# Returns: (True, {home_similarity: 1.00, away_similarity: 1.00, date_diff_days: 0})

# Protection faux positifs
risks = check_false_positive_risk("Real Madrid")
# Returns: [{conflict: "Real Betis", similarity: 0.67}]
```

### Corrections apportées (19/12/2025)

1. **Abbreviation expansion** dans `normalize_for_comparison()`:
   - `man city` -> `manchester city`
   - `man utd` -> `manchester united`

2. **Mappings corrigés** - Supprimé les raccourcissements erronés:
   - ~~`Bayern Munich` -> `Bayern`~~ (BE affiche nom complet)
   - ~~`Werder Bremen` -> `Bremen`~~ (BE affiche nom complet)
   - ~~`Sparta Rotterdam` -> `Sparta`~~ (BE affiche nom complet)

3. **80+ team mappings** ajoutés pour toutes les ligues majeures

---

## 5. TABLES DB

### odds_betexplorer

```sql
CREATE TABLE odds_betexplorer (
    id SERIAL PRIMARY KEY,
    match_id_monps VARCHAR(64),
    match_id_betexplorer VARCHAR(32),
    sport VARCHAR(32) DEFAULT 'football',
    league VARCHAR(128),
    home_team VARCHAR(128),
    away_team VARCHAR(128),
    commence_time TIMESTAMP WITH TIME ZONE,
    bookmaker VARCHAR(64) NOT NULL,
    market_type VARCHAR(32) NOT NULL,  -- btts_yes, dnb_home, over_25, etc.
    market_line DECIMAL(4,2),           -- 1.5, 2.5, 3.5 for O/U
    odds_value DECIMAL(8,4) NOT NULL,
    is_closing BOOLEAN DEFAULT FALSE,
    odds_timestamp TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### match_id_mapping

```sql
CREATE TABLE match_id_mapping (
    id SERIAL PRIMARY KEY,
    match_id_monps VARCHAR(64) UNIQUE,
    match_id_betexplorer VARCHAR(32) UNIQUE,
    home_team VARCHAR(128),
    away_team VARCHAR(128),
    league VARCHAR(128),
    commence_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### scraper_betexplorer_logs

```sql
CREATE TABLE scraper_betexplorer_logs (
    id SERIAL PRIMARY KEY,
    scraper_run_id UUID DEFAULT gen_random_uuid(),
    league VARCHAR(128),
    action VARCHAR(64),
    matches_processed INTEGER DEFAULT 0,
    odds_collected INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    duration_seconds DECIMAL(8,2),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(32),
    error_message TEXT,
    metadata JSONB
);
```

---

## 6. FICHIERS CRÉÉS

```
/home/Mon_ps/scrapers/betexplorer/
├── anti_ban.py           # Module anti-ban (rate limiter, headers, retry)
├── league_mapping.py     # Mapping 16 ligues + 80+ équipes + marchés
├── match_finder.py       # Trouve match_id avec triple validation
├── match_validator.py    # Validation Hedge Fund Grade (80% + date)
├── PHASE1_ANALYSIS.md    # Rapport Phase 1
└── PHASE2_REPORT.md      # Ce rapport
```

---

## 7. PROCHAINE ÉTAPE - PHASE 3

### À implémenter

1. **odds_scraper.py** - Scraper principal pour récupérer les cotes
   ```python
   def get_match_odds(match_id: str, market: str) -> List[Dict]:
       """Récupère les cotes pour un match et un marché"""
       pass
   ```

2. **Integration avec enrich_closing_odds.py**
   - Ajouter source "betexplorer" comme fallback
   - Priorité: Pinnacle > Marathon Bet > Betexplorer

3. **Scheduler pour scraping automatique**
   - Scraper les matchs du jour à 23h (après fin des matchs)
   - Stocker dans `odds_betexplorer`

4. **Tests de robustesse**
   - Test avec 100+ matchs
   - Monitoring des bans/erreurs

---

## 8. ESTIMATION PHASE 3

| Élément | Complexité |
|---------|------------|
| odds_scraper.py | Moyenne |
| Integration enrichissement | Faible |
| Tests robustesse | Faible |

---

**Status:** PHASE 2 HEDGE FUND GRADE COMPLETE
**Validation:** 18/18 matchs (100%) - 6 ligues testées
**Next:** Implémenter odds_scraper.py (Phase 3)

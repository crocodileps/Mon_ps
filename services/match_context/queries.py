"""
SQL Queries - Match Context Calculator
═══════════════════════════════════════════════════════════════════════════
Requêtes SQL optimisées avec Window Functions.
Performance: Une seule requête vectorisée, pas de boucle Python N+1.
═══════════════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUERY 1: Historique complet avec LAG
# Calcule pour chaque match le match précédent de chaque équipe
# ═══════════════════════════════════════════════════════════════════════════
GET_TEAM_MATCH_HISTORY = """
WITH TeamMatches AS (
    -- Perspective équipe domicile
    SELECT
        home_team as team,
        commence_time as match_date,
        'Home' as venue,
        league as competition,
        match_id
    FROM match_results
    WHERE is_finished = TRUE
      AND commence_time IS NOT NULL

    UNION ALL

    -- Perspective équipe extérieur
    SELECT
        away_team as team,
        commence_time as match_date,
        'Away' as venue,
        league as competition,
        match_id
    FROM match_results
    WHERE is_finished = TRUE
      AND commence_time IS NOT NULL
),
WithLag AS (
    SELECT
        team,
        match_date,
        venue,
        competition,
        match_id,
        LAG(match_date) OVER (PARTITION BY team ORDER BY match_date) as prev_match_date,
        LAG(venue) OVER (PARTITION BY team ORDER BY match_date) as prev_venue,
        LAG(competition) OVER (PARTITION BY team ORDER BY match_date) as prev_competition
    FROM TeamMatches
)
SELECT
    team,
    match_date,
    venue,
    competition,
    match_id,
    prev_match_date,
    prev_venue,
    prev_competition,
    EXTRACT(DAY FROM (match_date - prev_match_date))::INTEGER as raw_days_since
FROM WithLag
WHERE prev_match_date IS NOT NULL
ORDER BY team, match_date DESC;
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUERY 2: Dernier match d'une équipe spécifique
# Utilisé pour calculer le repos avant un match futur
# ═══════════════════════════════════════════════════════════════════════════
GET_LAST_MATCH_FOR_TEAM = """
WITH TeamMatches AS (
    SELECT
        home_team as team,
        commence_time as match_date,
        'Home' as venue,
        league as competition
    FROM match_results
    WHERE is_finished = TRUE
      AND commence_time IS NOT NULL

    UNION ALL

    SELECT
        away_team as team,
        commence_time as match_date,
        'Away' as venue,
        league as competition
    FROM match_results
    WHERE is_finished = TRUE
      AND commence_time IS NOT NULL
)
SELECT
    match_date as last_match_date,
    venue as last_venue,
    competition as last_competition
FROM TeamMatches
WHERE team = %s
  AND match_date < %s
ORDER BY match_date DESC
LIMIT 1;
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUERY 3: Matchs à venir (pour mise à jour batch)
# Récupère les matchs où on doit calculer le repos
# ═══════════════════════════════════════════════════════════════════════════
GET_UPCOMING_MATCHES = """
SELECT
    match_id,
    home_team,
    away_team,
    commence_time,
    league
FROM match_context
WHERE commence_time > NOW()
  AND (home_effective_rest IS NULL OR away_effective_rest IS NULL)
ORDER BY commence_time ASC;
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUERY 4: Update match_context avec les calculs de repos
# ═══════════════════════════════════════════════════════════════════════════
UPDATE_MATCH_CONTEXT = """
UPDATE match_context
SET
    home_raw_rest_days = %(home_raw_rest_days)s,
    away_raw_rest_days = %(away_raw_rest_days)s,
    home_effective_rest = %(home_effective_rest)s,
    away_effective_rest = %(away_effective_rest)s,
    rest_delta = %(rest_delta)s,
    home_returning_from = %(home_returning_from)s,
    away_returning_from = %(away_returning_from)s,
    home_rest_status = %(home_rest_status)s,
    away_rest_status = %(away_rest_status)s,
    days_since_last_match = %(days_since_last_match)s,
    updated_at = NOW()
WHERE match_id = %(match_id)s;
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUERY 5: Vérifier l'existence des colonnes dans match_context
# ═══════════════════════════════════════════════════════════════════════════
CHECK_COLUMNS_EXIST = """
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'match_context'
AND column_name IN (
    'home_raw_rest_days',
    'away_raw_rest_days',
    'home_effective_rest',
    'away_effective_rest',
    'rest_delta',
    'home_returning_from',
    'away_returning_from',
    'home_rest_status',
    'away_rest_status'
);
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUERY 6: Ajouter les colonnes manquantes
# ═══════════════════════════════════════════════════════════════════════════
ADD_MISSING_COLUMNS = """
ALTER TABLE match_context
ADD COLUMN IF NOT EXISTS home_raw_rest_days INTEGER,
ADD COLUMN IF NOT EXISTS away_raw_rest_days INTEGER,
ADD COLUMN IF NOT EXISTS home_effective_rest DECIMAL(4,1),
ADD COLUMN IF NOT EXISTS away_effective_rest DECIMAL(4,1),
ADD COLUMN IF NOT EXISTS rest_delta DECIMAL(4,1),
ADD COLUMN IF NOT EXISTS home_returning_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS away_returning_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS home_rest_status VARCHAR(10),
ADD COLUMN IF NOT EXISTS away_rest_status VARCHAR(10);
"""

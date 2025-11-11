CREATE TABLE IF NOT EXISTS odds_history (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) NOT NULL,
    sport VARCHAR(100) NOT NULL,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    commence_time TIMESTAMP NOT NULL,
    bookmaker VARCHAR(100) NOT NULL,
    home_odds DECIMAL(10, 2),
    away_odds DECIMAL(10, 2),
    draw_odds DECIMAL(10, 2),
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(match_id, bookmaker, collected_at)
);

CREATE INDEX IF NOT EXISTS idx_odds_match_id ON odds_history(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_sport ON odds_history(sport);
CREATE INDEX IF NOT EXISTS idx_odds_collected_at ON odds_history(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds_history(bookmaker);

SELECT create_hypertable('odds_history', 'collected_at', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT add_retention_policy('odds_history', INTERVAL '30 days', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS prometheus_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL(15, 4) NOT NULL,
    labels JSONB DEFAULT '{}',
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(metric_name, labels)
);

CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    sport VARCHAR(100) NOT NULL,
    matches_count INTEGER,
    odds_stored INTEGER,
    opportunities_detected INTEGER,
    api_requests_remaining INTEGER,
    execution_time_seconds DECIMAL(10, 2),
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    collected_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW v_current_opportunities AS
WITH latest_odds AS (
    SELECT DISTINCT ON (match_id, bookmaker)
        match_id, sport, home_team, away_team, commence_time,
        bookmaker, home_odds, away_odds, draw_odds, collected_at
    FROM odds_history
    WHERE collected_at >= NOW() - INTERVAL '2 hours'
      AND commence_time > NOW()
    ORDER BY match_id, bookmaker, collected_at DESC
),
match_stats AS (
    SELECT 
        match_id, sport, home_team, away_team, commence_time,
        MAX(home_odds) as max_home_odds,
        MIN(home_odds) as min_home_odds,
        MAX(away_odds) as max_away_odds,
        MIN(away_odds) as min_away_odds,
        MAX(draw_odds) as max_draw_odds,
        MIN(draw_odds) as min_draw_odds,
        COUNT(DISTINCT bookmaker) as bookmaker_count,
        MAX(collected_at) as last_update
    FROM latest_odds
    GROUP BY match_id, sport, home_team, away_team, commence_time
    HAVING COUNT(DISTINCT bookmaker) >= 2
)
SELECT 
    match_id, sport, home_team, away_team, commence_time,
    max_home_odds, min_home_odds,
    max_away_odds, min_away_odds,
    max_draw_odds, min_draw_odds,
    bookmaker_count,
    ROUND(((max_home_odds - min_home_odds) / min_home_odds * 100)::numeric, 2) as home_spread_pct,
    ROUND(((max_away_odds - min_away_odds) / min_away_odds * 100)::numeric, 2) as away_spread_pct,
    ROUND(((max_draw_odds - min_draw_odds) / NULLIF(min_draw_odds, 0) * 100)::numeric, 2) as draw_spread_pct,
    last_update
FROM match_stats
WHERE 
    ((max_home_odds - min_home_odds) / min_home_odds * 100) >= 1.0 OR
    ((max_away_odds - min_away_odds) / min_away_odds * 100) >= 1.0 OR
    ((max_draw_odds - min_draw_odds) / NULLIF(min_draw_odds, 0) * 100) >= 1.0
ORDER BY home_spread_pct DESC;

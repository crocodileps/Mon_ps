-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION 001: CREATE GOALS_UNIFIED TABLE
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- Description: Source unique de vérité (SSOT) pour tous les buts
-- Auteur: Mon_PS Team
-- Date: 2025-12-23
-- Branche: feature/goals-unified-ssot
--
-- CONTEXTE:
-- Le fichier all_goals_2025.json était vidé par un bug dans understat_master_v2.py
-- Bug: cherchait match['h']['goals'] au lieu de match['goals']['h']
-- Cette table PostgreSQL remplace le JSON avec protections.
--
-- ═══════════════════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS quantum;

CREATE TABLE IF NOT EXISTS quantum.goals_unified (
    id SERIAL PRIMARY KEY,
    goal_id VARCHAR(20) UNIQUE NOT NULL,
    
    match_id VARCHAR(20) NOT NULL,
    season VARCHAR(10) NOT NULL DEFAULT '2025',
    league VARCHAR(50) NOT NULL,
    date TIMESTAMP NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    
    player_id VARCHAR(20),
    player_name VARCHAR(100) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    opponent VARCHAR(100) NOT NULL,
    is_home BOOLEAN NOT NULL,
    
    minute INT NOT NULL CHECK (minute >= 0 AND minute <= 120),
    half VARCHAR(5),
    period VARCHAR(10),
    timing_period VARCHAR(10),
    
    xg FLOAT CHECK (xg >= 0 AND xg <= 1),
    situation VARCHAR(50),
    shot_type VARCHAR(50),
    
    is_first_goal BOOLEAN DEFAULT FALSE,
    is_last_goal BOOLEAN DEFAULT FALSE,
    is_equalizer BOOLEAN DEFAULT FALSE,
    is_go_ahead BOOLEAN DEFAULT FALSE,
    goal_number_in_match INT CHECK (goal_number_in_match >= 1),
    score_before_home INT,
    score_before_away INT,
    
    scorer VARCHAR(100),
    scoring_team VARCHAR(100),
    
    assist_player_id VARCHAR(20),
    assist_player_name VARCHAR(100),
    is_penalty BOOLEAN DEFAULT FALSE,
    is_own_goal BOOLEAN DEFAULT FALSE,
    
    source VARCHAR(50) DEFAULT 'understat',
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goals_team ON quantum.goals_unified(team_name);
CREATE INDEX IF NOT EXISTS idx_goals_player ON quantum.goals_unified(player_name);
CREATE INDEX IF NOT EXISTS idx_goals_date ON quantum.goals_unified(date);
CREATE INDEX IF NOT EXISTS idx_goals_league ON quantum.goals_unified(league);
CREATE INDEX IF NOT EXISTS idx_goals_match ON quantum.goals_unified(match_id);
CREATE INDEX IF NOT EXISTS idx_goals_season ON quantum.goals_unified(season);
CREATE INDEX IF NOT EXISTS idx_goals_minute ON quantum.goals_unified(minute);
CREATE INDEX IF NOT EXISTS idx_goals_situation ON quantum.goals_unified(situation);
CREATE INDEX IF NOT EXISTS idx_goals_team_season ON quantum.goals_unified(team_name, season);
CREATE INDEX IF NOT EXISTS idx_goals_player_season ON quantum.goals_unified(player_name, season);

CREATE OR REPLACE FUNCTION quantum.update_goals_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_goals_updated ON quantum.goals_unified;
CREATE TRIGGER trg_goals_updated
    BEFORE UPDATE ON quantum.goals_unified
    FOR EACH ROW
    EXECUTE FUNCTION quantum.update_goals_modified();

CREATE OR REPLACE FUNCTION quantum.calculate_goal_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.minute <= 45 THEN
        NEW.half := '1H';
    ELSE
        NEW.half := '2H';
    END IF;
    NEW.timing_period := NEW.period;
    NEW.scorer := NEW.player_name;
    NEW.scoring_team := NEW.team_name;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_goals_calculate ON quantum.goals_unified;
CREATE TRIGGER trg_goals_calculate
    BEFORE INSERT OR UPDATE ON quantum.goals_unified
    FOR EACH ROW
    EXECUTE FUNCTION quantum.calculate_goal_fields();

COMMENT ON TABLE quantum.goals_unified IS 'SSOT pour buts - Créée 2025-12-23 - Bug fix: match[goals][h] pas match[h][goals]';

CREATE OR REPLACE VIEW quantum.goals_by_team AS
SELECT 
    team_name, season, league,
    COUNT(*) as total_goals,
    COUNT(*) FILTER (WHERE half = '1H') as goals_1h,
    COUNT(*) FILTER (WHERE half = '2H') as goals_2h,
    COUNT(*) FILTER (WHERE is_home = true) as goals_home,
    COUNT(*) FILTER (WHERE is_home = false) as goals_away,
    COUNT(*) FILTER (WHERE situation = 'OpenPlay') as goals_open_play,
    COUNT(*) FILTER (WHERE situation = 'SetPiece') as goals_set_piece,
    COUNT(*) FILTER (WHERE is_penalty = true) as goals_penalty,
    AVG(xg) as avg_xg,
    AVG(minute) as avg_minute
FROM quantum.goals_unified
GROUP BY team_name, season, league;

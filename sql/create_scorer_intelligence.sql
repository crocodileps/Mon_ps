-- ============================================================
-- TABLE: scorer_intelligence
-- Version: FERRARI 2.0 ULTIMATE - Profils Buteurs Complets
-- Date: 28 Nov 2025
-- Auteur: Mon_PS Team
-- ============================================================

BEGIN;

DROP TABLE IF EXISTS scorer_intelligence CASCADE;

CREATE TABLE scorer_intelligence (
    id SERIAL PRIMARY KEY,
    
    -- ══════════ IDENTIFICATION JOUEUR ══════════
    player_name VARCHAR(255) NOT NULL,
    player_name_normalized VARCHAR(255),
    player_aliases JSONB DEFAULT '[]',
    api_football_id INTEGER,
    photo_url VARCHAR(500),
    nationality VARCHAR(100),
    birth_date DATE,
    age INTEGER,
    height_cm INTEGER,
    preferred_foot VARCHAR(20),
    
    -- ══════════ EQUIPE ET POSITION ══════════
    current_team VARCHAR(255) NOT NULL,
    current_team_id INTEGER,
    team_intelligence_id INTEGER,
    position_primary VARCHAR(50),
    position_secondary VARCHAR(50),
    shirt_number INTEGER,
    is_captain BOOLEAN DEFAULT false,
    market_value_eur BIGINT,
    
    -- ══════════ ROLES SPECIAUX ══════════
    is_penalty_taker BOOLEAN DEFAULT false,
    is_freekick_taker BOOLEAN DEFAULT false,
    is_corner_taker BOOLEAN DEFAULT false,
    penalty_conversion_rate NUMERIC(5,2),
    penalties_taken INTEGER DEFAULT 0,
    penalties_scored INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    
    -- ══════════ STATS SAISON ACTUELLE ══════════
    season VARCHAR(20) DEFAULT '2024-2025',
    season_matches INTEGER DEFAULT 0,
    season_starts INTEGER DEFAULT 0,
    season_sub_appearances INTEGER DEFAULT 0,
    season_minutes INTEGER DEFAULT 0,
    season_goals INTEGER DEFAULT 0,
    season_assists INTEGER DEFAULT 0,
    season_goal_contributions INTEGER DEFAULT 0,
    
    -- ══════════ MOYENNES PAR MATCH ══════════
    goals_per_match NUMERIC(4,2),
    goals_per_90 NUMERIC(4,2),
    assists_per_match NUMERIC(4,2),
    assists_per_90 NUMERIC(4,2),
    contributions_per_90 NUMERIC(4,2),
    minutes_per_goal NUMERIC(6,2),
    
    -- ══════════ EXPECTED GOALS (xG) ══════════
    season_xg NUMERIC(6,2),
    season_xg_per_90 NUMERIC(4,2),
    season_xa NUMERIC(6,2),
    xg_overperformance NUMERIC(4,2),
    xg_consistency_score INTEGER DEFAULT 50,
    
    -- ══════════ TIRS ET EFFICACITE ══════════
    season_shots INTEGER DEFAULT 0,
    season_shots_on_target INTEGER DEFAULT 0,
    shots_per_match NUMERIC(4,2),
    shots_per_90 NUMERIC(4,2),
    shots_on_target_pct NUMERIC(5,2),
    shot_conversion_rate NUMERIC(5,2),
    big_chances_scored INTEGER DEFAULT 0,
    big_chances_missed INTEGER DEFAULT 0,
    big_chance_conversion NUMERIC(5,2),
    
    -- ══════════ TYPES DE BUTS ══════════
    goals_right_foot INTEGER DEFAULT 0,
    goals_left_foot INTEGER DEFAULT 0,
    goals_header INTEGER DEFAULT 0,
    goals_other INTEGER DEFAULT 0,
    goals_penalty INTEGER DEFAULT 0,
    goals_freekick INTEGER DEFAULT 0,
    goals_inside_box INTEGER DEFAULT 0,
    goals_outside_box INTEGER DEFAULT 0,
    
    -- ══════════ PROBABILITES BUTEUR ══════════
    anytime_scorer_prob NUMERIC(5,2),
    first_scorer_prob NUMERIC(5,2),
    last_scorer_prob NUMERIC(5,2),
    two_plus_goals_prob NUMERIC(5,2),
    hattrick_prob NUMERIC(5,2),
    
    -- ══════════ STATS DOMICILE ══════════
    home_matches INTEGER DEFAULT 0,
    home_goals INTEGER DEFAULT 0,
    home_goals_per_match NUMERIC(4,2),
    home_xg_per_90 NUMERIC(4,2),
    home_anytime_prob NUMERIC(5,2),
    
    -- ══════════ STATS EXTERIEUR ══════════
    away_matches INTEGER DEFAULT 0,
    away_goals INTEGER DEFAULT 0,
    away_goals_per_match NUMERIC(4,2),
    away_xg_per_90 NUMERIC(4,2),
    away_anytime_prob NUMERIC(5,2),
    
    -- ══════════ VS TYPES D'ADVERSAIRES ══════════
    goals_vs_top_teams INTEGER DEFAULT 0,
    goals_vs_mid_teams INTEGER DEFAULT 0,
    goals_vs_bottom_teams INTEGER DEFAULT 0,
    matches_vs_top_teams INTEGER DEFAULT 0,
    matches_vs_mid_teams INTEGER DEFAULT 0,
    matches_vs_bottom_teams INTEGER DEFAULT 0,
    scoring_rate_vs_top NUMERIC(4,2),
    scoring_rate_vs_bottom NUMERIC(4,2),
    
    -- ══════════ PATTERNS TEMPORELS ══════════
    goals_first_half INTEGER DEFAULT 0,
    goals_second_half INTEGER DEFAULT 0,
    goals_0_15 INTEGER DEFAULT 0,
    goals_16_30 INTEGER DEFAULT 0,
    goals_31_45 INTEGER DEFAULT 0,
    goals_46_60 INTEGER DEFAULT 0,
    goals_61_75 INTEGER DEFAULT 0,
    goals_76_90 INTEGER DEFAULT 0,
    goals_added_time INTEGER DEFAULT 0,
    favorite_scoring_period VARCHAR(20),
    
    -- ══════════ FORME RECENTE ══════════
    last_5_matches_goals INTEGER DEFAULT 0,
    last_5_matches_xg NUMERIC(4,2),
    last_10_matches_goals INTEGER DEFAULT 0,
    last_10_matches_xg NUMERIC(4,2),
    current_goal_streak INTEGER DEFAULT 0,
    max_goal_streak_season INTEGER DEFAULT 0,
    matches_since_last_goal INTEGER DEFAULT 0,
    is_hot_streak BOOLEAN DEFAULT false,
    is_cold_streak BOOLEAN DEFAULT false,
    form_trend VARCHAR(20) DEFAULT 'stable',
    form_score INTEGER DEFAULT 50,
    
    -- ══════════ CORRELATION AVEC EQUIPE ══════════
    team_win_when_scores_rate NUMERIC(5,2),
    team_draw_when_scores_rate NUMERIC(5,2),
    team_loss_when_scores_rate NUMERIC(5,2),
    scores_in_wins_rate NUMERIC(5,2),
    scores_in_draws_rate NUMERIC(5,2),
    scores_in_losses_rate NUMERIC(5,2),
    is_key_player BOOLEAN DEFAULT false,
    team_dependency_score INTEGER DEFAULT 50,
    
    -- ══════════ HISTORIQUE VS GARDIENS ══════════
    favorite_opponents JSONB DEFAULT '[]',
    difficult_opponents JSONB DEFAULT '[]',
    goals_vs_top_keepers INTEGER DEFAULT 0,
    conversion_vs_top_keepers NUMERIC(5,2),
    
    -- ══════════ DISPONIBILITE ══════════
    is_injured BOOLEAN DEFAULT false,
    injury_type VARCHAR(100),
    expected_return_date DATE,
    is_suspended BOOLEAN DEFAULT false,
    suspension_matches_left INTEGER DEFAULT 0,
    is_international_duty BOOLEAN DEFAULT false,
    fitness_level INTEGER DEFAULT 100,
    minutes_last_match INTEGER,
    fatigue_risk VARCHAR(20) DEFAULT 'low',
    
    -- ══════════ CARRIERES STATS ══════════
    career_goals INTEGER DEFAULT 0,
    career_matches INTEGER DEFAULT 0,
    career_goals_per_match NUMERIC(4,2),
    career_penalties_scored INTEGER DEFAULT 0,
    career_hattricks INTEGER DEFAULT 0,
    
    -- ══════════ MARCHE PARIS IMPACT ══════════
    market_value_anytime JSONB DEFAULT '{}',
    market_value_first_scorer JSONB DEFAULT '{}',
    typical_odds_anytime NUMERIC(5,2),
    typical_odds_first NUMERIC(5,2),
    value_rating INTEGER DEFAULT 50,
    bookmaker_bias NUMERIC(4,2),
    
    -- ══════════ TAGS ET META ══════════
    tags JSONB DEFAULT '[]',
    strengths JSONB DEFAULT '[]',
    weaknesses JSONB DEFAULT '[]',
    playing_style VARCHAR(100),
    
    -- ══════════ QUALITE DONNEES ══════════
    data_quality_score INTEGER DEFAULT 50,
    confidence_overall INTEGER DEFAULT 50,
    matches_analyzed INTEGER DEFAULT 0,
    is_reliable BOOLEAN DEFAULT false,
    data_sources JSONB DEFAULT '[]',
    
    -- ══════════ META ══════════
    last_api_sync TIMESTAMP,
    last_computed_at TIMESTAMP,
    computation_version VARCHAR(20) DEFAULT '1.0',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- ══════════ CONTRAINTES ══════════
    CONSTRAINT uq_scorer_team UNIQUE(player_name, current_team),
    CONSTRAINT chk_form_score CHECK (form_score >= 0 AND form_score <= 100)
);

-- ══════════ INDEX PERFORMANCE ══════════
CREATE INDEX idx_si_player_name ON scorer_intelligence(player_name);
CREATE INDEX idx_si_player_normalized ON scorer_intelligence(player_name_normalized);
CREATE INDEX idx_si_current_team ON scorer_intelligence(current_team);
CREATE INDEX idx_si_api_football_id ON scorer_intelligence(api_football_id);
CREATE INDEX idx_si_position ON scorer_intelligence(position_primary);
CREATE INDEX idx_si_goals_per_match ON scorer_intelligence(goals_per_match);
CREATE INDEX idx_si_anytime_prob ON scorer_intelligence(anytime_scorer_prob);
CREATE INDEX idx_si_is_hot_streak ON scorer_intelligence(is_hot_streak);
CREATE INDEX idx_si_is_penalty_taker ON scorer_intelligence(is_penalty_taker);
CREATE INDEX idx_si_is_injured ON scorer_intelligence(is_injured);
CREATE INDEX idx_si_form_score ON scorer_intelligence(form_score);
CREATE INDEX idx_si_tags ON scorer_intelligence USING GIN(tags);
CREATE INDEX idx_si_aliases ON scorer_intelligence USING GIN(player_aliases);
CREATE INDEX idx_si_strengths ON scorer_intelligence USING GIN(strengths);

-- ══════════ COMMENTAIRES ══════════
COMMENT ON TABLE scorer_intelligence IS 'FERRARI 2.0 ULTIMATE - Profils buteurs complets avec xG, forme, correlations';
COMMENT ON COLUMN scorer_intelligence.anytime_scorer_prob IS 'Probabilite calculee de marquer dans un match (0-100)';
COMMENT ON COLUMN scorer_intelligence.xg_overperformance IS 'Buts reels - xG: positif=finisseur efficace, negatif=malchanceux';
COMMENT ON COLUMN scorer_intelligence.team_win_when_scores_rate IS 'Pourcentage victoire equipe quand ce joueur marque';
COMMENT ON COLUMN scorer_intelligence.is_hot_streak IS 'True si 3+ buts sur 5 derniers matchs';
COMMENT ON COLUMN scorer_intelligence.form_trend IS 'improving, stable, declining';
COMMENT ON COLUMN scorer_intelligence.fatigue_risk IS 'low, medium, high - base sur minutes recentes';

COMMIT;

SELECT 'SUCCESS: scorer_intelligence created' as status;

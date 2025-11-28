-- ============================================================
-- TABLE: coach_intelligence
-- Version: FERRARI 2.0 ULTIMATE - Profils Entraineurs Complets
-- Date: 28 Nov 2025
-- Auteur: Mon_PS Team
-- ============================================================

BEGIN;

DROP TABLE IF EXISTS coach_intelligence CASCADE;

CREATE TABLE coach_intelligence (
    id SERIAL PRIMARY KEY,
    
    -- ══════════ IDENTIFICATION ══════════
    coach_name VARCHAR(255) NOT NULL,
    coach_name_normalized VARCHAR(255),
    api_football_id INTEGER,
    nationality VARCHAR(100),
    birth_year INTEGER,
    photo_url VARCHAR(500),
    
    -- ══════════ EQUIPE ACTUELLE ══════════
    current_team VARCHAR(255),
    current_team_id INTEGER,
    tenure_start_date DATE,
    tenure_months INTEGER,
    contract_end_date DATE,
    job_security VARCHAR(20) DEFAULT 'stable',
    rumored_departure BOOLEAN DEFAULT false,
    
    -- ══════════ HISTORIQUE EQUIPES ══════════
    previous_teams JSONB DEFAULT '[]',
    total_teams_managed INTEGER DEFAULT 0,
    performance_by_club_tier JSONB DEFAULT '{}',
    avg_tenure_months NUMERIC(5,1),
    
    -- ══════════ STYLE TACTIQUE PRINCIPAL ══════════
    tactical_style VARCHAR(50),
    formation_primary VARCHAR(20),
    formation_secondary VARCHAR(20),
    formations_used JSONB DEFAULT '[]',
    formations_frequency JSONB DEFAULT '{}',
    pressing_style VARCHAR(20) DEFAULT 'medium',
    defensive_approach VARCHAR(50),
    attacking_approach VARCHAR(50),
    buildup_style VARCHAR(50),
    
    -- ══════════ FLEXIBILITE TACTIQUE ══════════
    tactical_flexibility INTEGER DEFAULT 50,
    approach_vs_stronger VARCHAR(50),
    approach_vs_weaker VARCHAR(50),
    approach_vs_similar VARCHAR(50),
    in_game_adjustments INTEGER DEFAULT 50,
    
    -- ══════════ STATS CARRIERE GLOBALE ══════════
    career_matches INTEGER DEFAULT 0,
    career_wins INTEGER DEFAULT 0,
    career_draws INTEGER DEFAULT 0,
    career_losses INTEGER DEFAULT 0,
    career_win_rate NUMERIC(5,2),
    career_draw_rate NUMERIC(5,2),
    career_loss_rate NUMERIC(5,2),
    career_goals_for INTEGER DEFAULT 0,
    career_goals_against INTEGER DEFAULT 0,
    career_goals_for_avg NUMERIC(4,2),
    career_goals_against_avg NUMERIC(4,2),
    career_goal_difference_avg NUMERIC(4,2),
    
    -- ══════════ STATS EQUIPE ACTUELLE ══════════
    current_team_matches INTEGER DEFAULT 0,
    current_team_wins INTEGER DEFAULT 0,
    current_team_draws INTEGER DEFAULT 0,
    current_team_losses INTEGER DEFAULT 0,
    current_team_win_rate NUMERIC(5,2),
    current_team_draw_rate NUMERIC(5,2),
    current_team_goals_avg NUMERIC(4,2),
    current_team_conceded_avg NUMERIC(4,2),
    current_team_clean_sheets INTEGER DEFAULT 0,
    current_team_failed_to_score INTEGER DEFAULT 0,
    
    -- ══════════ TENDANCES DOM/EXT ══════════
    home_matches INTEGER DEFAULT 0,
    home_wins INTEGER DEFAULT 0,
    home_win_rate NUMERIC(5,2),
    home_draw_rate NUMERIC(5,2),
    home_goals_avg NUMERIC(4,2),
    away_matches INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,
    away_win_rate NUMERIC(5,2),
    away_draw_rate NUMERIC(5,2),
    away_goals_avg NUMERIC(4,2),
    
    -- ══════════ VS TYPES D'ADVERSAIRES ══════════
    vs_top_teams_matches INTEGER DEFAULT 0,
    vs_top_teams_win_rate NUMERIC(5,2),
    vs_top_teams_draw_rate NUMERIC(5,2),
    vs_mid_teams_matches INTEGER DEFAULT 0,
    vs_mid_teams_win_rate NUMERIC(5,2),
    vs_bottom_teams_matches INTEGER DEFAULT 0,
    vs_bottom_teams_win_rate NUMERIC(5,2),
    
    -- ══════════ PATTERNS BUTS ══════════
    avg_goals_per_match NUMERIC(4,2),
    avg_goals_conceded_per_match NUMERIC(4,2),
    clean_sheet_rate NUMERIC(5,2),
    failed_to_score_rate NUMERIC(5,2),
    btts_rate NUMERIC(5,2),
    over15_rate NUMERIC(5,2),
    over25_rate NUMERIC(5,2),
    over35_rate NUMERIC(5,2),
    under25_rate NUMERIC(5,2),
    
    -- ══════════ PATTERNS TEMPORELS ══════════
    first_half_goals_rate NUMERIC(5,2),
    second_half_goals_rate NUMERIC(5,2),
    late_goals_rate NUMERIC(5,2),
    early_goals_rate NUMERIC(5,2),
    goals_0_15_rate NUMERIC(5,2),
    goals_75_90_rate NUMERIC(5,2),
    conceded_late_rate NUMERIC(5,2),
    
    -- ══════════ GESTION DE MATCH ══════════
    when_winning_reaction VARCHAR(50),
    lead_protection_rate NUMERIC(5,2),
    goals_conceded_when_leading_avg NUMERIC(4,2),
    when_losing_reaction VARCHAR(50),
    comeback_rate NUMERIC(5,2),
    goals_after_conceding_rate NUMERIC(5,2),
    when_drawing_reaction VARCHAR(50),
    
    -- ══════════ SUBSTITUTIONS ══════════
    avg_subs_per_match NUMERIC(3,1),
    first_sub_avg_minute INTEGER,
    late_subs_tendency INTEGER DEFAULT 50,
    attacking_subs_rate NUMERIC(5,2),
    defensive_subs_rate NUMERIC(5,2),
    like_for_like_subs_rate NUMERIC(5,2),
    
    -- ══════════ CONTEXTES SPECIAUX ══════════
    derby_record JSONB DEFAULT '{}',
    cup_record JSONB DEFAULT '{}',
    european_record JSONB DEFAULT '{}',
    final_record JSONB DEFAULT '{}',
    high_stakes_win_rate NUMERIC(5,2),
    low_stakes_win_rate NUMERIC(5,2),
    congested_fixture_record JSONB DEFAULT '{}',
    
    -- ══════════ SEQUENCES ET MOMENTUM ══════════
    after_win_record JSONB DEFAULT '{}',
    after_defeat_record JSONB DEFAULT '{}',
    after_draw_record JSONB DEFAULT '{}',
    winning_streak_max INTEGER DEFAULT 0,
    losing_streak_max INTEGER DEFAULT 0,
    unbeaten_streak_max INTEGER DEFAULT 0,
    current_streak_type VARCHAR(20),
    current_streak_count INTEGER DEFAULT 0,
    
    -- ══════════ FORME RECENTE ══════════
    recent_form_5_matches JSONB DEFAULT '{}',
    recent_form_10_matches JSONB DEFAULT '{}',
    recent_form_points_5 INTEGER,
    recent_form_points_10 INTEGER,
    form_trend VARCHAR(20) DEFAULT 'stable',
    form_trend_strength INTEGER DEFAULT 0,
    
    -- ══════════ COMPARAISONS ══════════
    vs_predecessor_comparison JSONB DEFAULT '{}',
    similar_coaches JSONB DEFAULT '[]',
    coaching_school VARCHAR(100),
    coaching_tree JSONB DEFAULT '{}',
    
    -- ══════════ JOUEURS CLES ══════════
    key_players_dependency JSONB DEFAULT '[]',
    performance_without_key_player JSONB DEFAULT '{}',
    preferred_player_types JSONB DEFAULT '[]',
    youth_development_rate NUMERIC(5,2),
    
    -- ══════════ IMPACT MARCHES PARIS ══════════
    market_signatures JSONB DEFAULT '{}',
    market_impact_btts INTEGER DEFAULT 0,
    market_impact_over25 INTEGER DEFAULT 0,
    market_impact_under25 INTEGER DEFAULT 0,
    market_impact_draw INTEGER DEFAULT 0,
    market_impact_clean_sheet INTEGER DEFAULT 0,
    
    -- ══════════ TAGS ET REPUTATION ══════════
    known_for JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    reputation_score INTEGER DEFAULT 50,
    media_pressure_handling VARCHAR(20),
    
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
    CONSTRAINT uq_coach_current_team UNIQUE(coach_name, current_team)
);

-- ══════════ INDEX PERFORMANCE ══════════
CREATE INDEX idx_ci_coach_name ON coach_intelligence(coach_name);
CREATE INDEX idx_ci_coach_normalized ON coach_intelligence(coach_name_normalized);
CREATE INDEX idx_ci_current_team ON coach_intelligence(current_team);
CREATE INDEX idx_ci_api_football_id ON coach_intelligence(api_football_id);
CREATE INDEX idx_ci_nationality ON coach_intelligence(nationality);
CREATE INDEX idx_ci_tactical_style ON coach_intelligence(tactical_style);
CREATE INDEX idx_ci_formation ON coach_intelligence(formation_primary);
CREATE INDEX idx_ci_career_win_rate ON coach_intelligence(career_win_rate);
CREATE INDEX idx_ci_tags ON coach_intelligence USING GIN(tags);
CREATE INDEX idx_ci_known_for ON coach_intelligence USING GIN(known_for);
CREATE INDEX idx_ci_market_signatures ON coach_intelligence USING GIN(market_signatures);
CREATE INDEX idx_ci_previous_teams ON coach_intelligence USING GIN(previous_teams);

-- ══════════ COMMENTAIRES ══════════
COMMENT ON TABLE coach_intelligence IS 'FERRARI 2.0 ULTIMATE - Profils entraineurs complets avec impact sur marches paris';
COMMENT ON COLUMN coach_intelligence.tactical_flexibility IS '0=rigide meme systeme, 100=cameleon adapte tout';
COMMENT ON COLUMN coach_intelligence.market_signatures IS 'Impact du coach sur les marches: {"btts_yes": {"impact": -15, "reason": "..."}}';
COMMENT ON COLUMN coach_intelligence.when_winning_reaction IS 'defend_lead, kill_game, keep_attacking';
COMMENT ON COLUMN coach_intelligence.when_losing_reaction IS 'attack_all_out, patient, panic';
COMMENT ON COLUMN coach_intelligence.job_security IS 'secure, stable, pressure, hot_seat';
COMMENT ON COLUMN coach_intelligence.form_trend IS 'improving, stable, declining';

COMMIT;

SELECT 'SUCCESS: coach_intelligence created' as status;

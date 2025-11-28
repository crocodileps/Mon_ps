-- ============================================================
-- TABLE: scorer_market_picks
-- Version: FERRARI 2.0 ULTIMATE - Tracking Paris Buteurs
-- Date: 28 Nov 2025
-- Auteur: Mon_PS Team
-- ============================================================

BEGIN;

DROP TABLE IF EXISTS scorer_market_picks CASCADE;

CREATE TABLE scorer_market_picks (
    id SERIAL PRIMARY KEY,
    
    -- ══════════ MATCH INFO ══════════
    match_id VARCHAR(255),
    match_name VARCHAR(255),
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    league VARCHAR(255),
    league_id INTEGER,
    commence_time TIMESTAMP,
    
    -- ══════════ JOUEUR INFO ══════════
    player_name VARCHAR(255) NOT NULL,
    player_name_normalized VARCHAR(255),
    player_team VARCHAR(255),
    player_team_side VARCHAR(10),
    scorer_intelligence_id INTEGER,
    player_position VARCHAR(50),
    is_starter_expected BOOLEAN,
    
    -- ══════════ TYPE DE PARI ══════════
    market_type VARCHAR(50) NOT NULL,
    market_description VARCHAR(255),
    selection VARCHAR(255),
    
    -- ══════════ COTES ET PROBABILITES ══════════
    odds_taken NUMERIC(6,2),
    odds_opening NUMERIC(6,2),
    odds_closing NUMERIC(6,2),
    odds_movement NUMERIC(4,2),
    bookmaker VARCHAR(100),
    implied_prob NUMERIC(5,2),
    calculated_prob NUMERIC(5,2),
    edge_pct NUMERIC(5,2),
    
    -- ══════════ FACTEURS DE CALCUL ══════════
    player_form_score INTEGER,
    player_xg_per_90 NUMERIC(4,2),
    player_anytime_prob NUMERIC(5,2),
    opponent_defense_rating INTEGER,
    opponent_goals_conceded_avg NUMERIC(4,2),
    is_home_game BOOLEAN,
    is_penalty_taker BOOLEAN,
    
    -- ══════════ CORRELATION AVEC AUTRES PARIS ══════════
    correlated_team_bet VARCHAR(50),
    correlated_team_odds NUMERIC(5,2),
    correlation_strength NUMERIC(4,2),
    is_combo_pick BOOLEAN DEFAULT false,
    combo_id INTEGER,
    combo_type VARCHAR(50),
    
    -- ══════════ SCORES ET RECOMMANDATION ══════════
    diamond_score INTEGER,
    confidence_score INTEGER,
    value_rating VARCHAR(20),
    recommendation VARCHAR(255),
    risk_level VARCHAR(20),
    
    -- ══════════ STAKE ET KELLY ══════════
    kelly_pct NUMERIC(5,2),
    kelly_stake NUMERIC(6,2),
    recommended_stake NUMERIC(6,2),
    actual_stake NUMERIC(6,2),
    stake_currency VARCHAR(10) DEFAULT 'EUR',
    
    -- ══════════ RESOLUTION ══════════
    is_resolved BOOLEAN DEFAULT false,
    is_winner BOOLEAN,
    player_goals_scored INTEGER,
    player_minutes_played INTEGER,
    player_started BOOLEAN,
    player_subbed_in_minute INTEGER,
    player_subbed_out_minute INTEGER,
    match_final_score VARCHAR(20),
    resolution_source VARCHAR(100),
    
    -- ══════════ PROFIT/LOSS ══════════
    potential_profit NUMERIC(10,2),
    profit_loss NUMERIC(10,2),
    roi_pct NUMERIC(6,2),
    
    -- ══════════ CLV TRACKING ══════════
    clv_percentage NUMERIC(5,2),
    closing_edge NUMERIC(5,2),
    was_value_bet BOOLEAN,
    
    -- ══════════ ANALYSE POST-MATCH ══════════
    post_match_notes TEXT,
    why_won TEXT,
    why_lost TEXT,
    lesson_learned TEXT,
    player_performance_rating INTEGER,
    
    -- ══════════ COMPARAISON AVEC PREDICTION ══════════
    predicted_goals NUMERIC(3,1),
    actual_vs_predicted NUMERIC(4,2),
    prediction_accuracy VARCHAR(20),
    
    -- ══════════ SOURCE ET TRACKING ══════════
    source VARCHAR(100),
    pick_origin VARCHAR(50),
    is_auto_generated BOOLEAN DEFAULT false,
    generation_algorithm VARCHAR(100),
    is_followed BOOLEAN DEFAULT false,
    followed_at TIMESTAMP,
    
    -- ══════════ TAGS ET META ══════════
    tags JSONB DEFAULT '[]',
    factors JSONB DEFAULT '{}',
    raw_analysis JSONB DEFAULT '{}',
    notes TEXT,
    
    -- ══════════ TIMESTAMPS ══════════
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    
    -- ══════════ CONTRAINTES ══════════
    CONSTRAINT chk_market_type CHECK (market_type IN (
        'anytime_scorer', 'first_scorer', 'last_scorer',
        '2plus_goals', '3plus_goals', 'hattrick',
        'first_half_scorer', 'second_half_scorer',
        'to_score_penalty', 'to_score_header',
        'to_score_outside_box', 'player_shots_over',
        'player_assists_over'
    ))
);

-- ══════════ INDEX PERFORMANCE ══════════
CREATE INDEX idx_smp_match_id ON scorer_market_picks(match_id);
CREATE INDEX idx_smp_player_name ON scorer_market_picks(player_name);
CREATE INDEX idx_smp_player_team ON scorer_market_picks(player_team);
CREATE INDEX idx_smp_market_type ON scorer_market_picks(market_type);
CREATE INDEX idx_smp_commence_time ON scorer_market_picks(commence_time);
CREATE INDEX idx_smp_is_resolved ON scorer_market_picks(is_resolved);
CREATE INDEX idx_smp_is_winner ON scorer_market_picks(is_winner);
CREATE INDEX idx_smp_diamond_score ON scorer_market_picks(diamond_score);
CREATE INDEX idx_smp_edge_pct ON scorer_market_picks(edge_pct);
CREATE INDEX idx_smp_source ON scorer_market_picks(source);
CREATE INDEX idx_smp_created_at ON scorer_market_picks(created_at);
CREATE INDEX idx_smp_league ON scorer_market_picks(league);
CREATE INDEX idx_smp_combo ON scorer_market_picks(combo_id);
CREATE INDEX idx_smp_tags ON scorer_market_picks USING GIN(tags);
CREATE INDEX idx_smp_factors ON scorer_market_picks USING GIN(factors);

-- ══════════ COMMENTAIRES ══════════
COMMENT ON TABLE scorer_market_picks IS 'FERRARI 2.0 ULTIMATE - Tracking complet des paris buteurs avec CLV et analyse';
COMMENT ON COLUMN scorer_market_picks.market_type IS 'Type: anytime_scorer, first_scorer, 2plus_goals, etc.';
COMMENT ON COLUMN scorer_market_picks.edge_pct IS 'calculated_prob - implied_prob: positif = value bet';
COMMENT ON COLUMN scorer_market_picks.correlation_strength IS '0-1: force correlation avec pari equipe';
COMMENT ON COLUMN scorer_market_picks.clv_percentage IS 'Closing Line Value: positif = bon timing';
COMMENT ON COLUMN scorer_market_picks.prediction_accuracy IS 'exact, close, wrong';

COMMIT;

SELECT 'SUCCESS: scorer_market_picks created' as status;

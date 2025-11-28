-- ============================================================
-- TABLE: market_traps
-- Version: FERRARI 2.0 ULTIMATE - Detection Pieges Automatique
-- Date: 28 Nov 2025
-- Auteur: Mon_PS Team
-- ============================================================

BEGIN;

DROP TABLE IF EXISTS market_traps CASCADE;

CREATE TABLE market_traps (
    id SERIAL PRIMARY KEY,
    
    -- ══════════ IDENTIFICATION ══════════
    team_name VARCHAR(255) NOT NULL,
    team_name_normalized VARCHAR(255),
    team_intelligence_id INTEGER,
    market_type VARCHAR(50) NOT NULL,
    
    -- ══════════ NIVEAU D'ALERTE ══════════
    alert_level VARCHAR(20) NOT NULL,
    alert_level_score INTEGER DEFAULT 50,
    alert_emoji VARCHAR(10),
    alert_color VARCHAR(20),
    
    -- ══════════ RAISON DETAILLEE ══════════
    alert_reason TEXT NOT NULL,
    alert_reason_short VARCHAR(255),
    detailed_analysis TEXT,
    
    -- ══════════ ALTERNATIVE RECOMMANDEE ══════════
    alternative_market VARCHAR(50),
    alternative_reason TEXT,
    alternative_odds_adjustment NUMERIC(4,2),
    alternative_confidence INTEGER DEFAULT 50,
    
    -- ══════════ CONDITIONS D'APPLICATION ══════════
    applies_when VARCHAR(20) DEFAULT 'always',
    applies_home BOOLEAN DEFAULT true,
    applies_away BOOLEAN DEFAULT true,
    min_odds NUMERIC(5,2),
    max_odds NUMERIC(5,2),
    
    -- ══════════ CONDITIONS ADVERSAIRE ══════════
    vs_team_type VARCHAR(50),
    vs_team_style VARCHAR(50),
    vs_specific_teams JSONB DEFAULT '[]',
    excluded_teams JSONB DEFAULT '[]',
    
    -- ══════════ CONDITIONS CONTEXTUELLES ══════════
    applies_in_competition JSONB DEFAULT '[]',
    excluded_competitions JSONB DEFAULT '[]',
    applies_matchday_range JSONB DEFAULT '{}',
    applies_season_phase VARCHAR(50),
    
    -- ══════════ STATS JUSTIFICATIVES ══════════
    historical_loss_rate NUMERIC(5,2),
    historical_win_rate NUMERIC(5,2),
    historical_roi NUMERIC(6,2),
    sample_size INTEGER DEFAULT 0,
    sample_period_months INTEGER DEFAULT 12,
    last_occurrence_date DATE,
    occurrences_last_30_days INTEGER DEFAULT 0,
    
    -- ══════════ STATS DETAILLEES ══════════
    total_bets_analyzed INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    total_pushes INTEGER DEFAULT 0,
    avg_odds_when_trap NUMERIC(5,2),
    avg_loss_amount NUMERIC(6,2),
    max_loss_streak INTEGER DEFAULT 0,
    
    -- ══════════ ALERTES COMBINEES ══════════
    combined_with_markets JSONB DEFAULT '[]',
    combined_alert_level VARCHAR(20),
    combined_alert_reason TEXT,
    is_compound_trap BOOLEAN DEFAULT false,
    compound_trap_markets JSONB DEFAULT '[]',
    compound_danger_score INTEGER DEFAULT 0,
    
    -- ══════════ SCORE DE CONFIANCE ══════════
    confidence_score INTEGER DEFAULT 50,
    confidence_breakdown JSONB DEFAULT '{}',
    min_sample_for_reliable INTEGER DEFAULT 10,
    is_reliable BOOLEAN DEFAULT false,
    reliability_factors JSONB DEFAULT '{}',
    
    -- ══════════ AUTO-LEARNING ══════════
    is_auto_generated BOOLEAN DEFAULT false,
    generation_algorithm VARCHAR(100),
    generation_parameters JSONB DEFAULT '{}',
    last_validation_date TIMESTAMP,
    validation_result VARCHAR(20),
    auto_adjust_enabled BOOLEAN DEFAULT true,
    adjustment_history JSONB DEFAULT '[]',
    
    -- ══════════ EXPIRATION ══════════
    expires_at TIMESTAMP,
    expiration_reason VARCHAR(255),
    auto_expire_after_days INTEGER DEFAULT 90,
    auto_renew_if_valid BOOLEAN DEFAULT true,
    is_expired BOOLEAN DEFAULT false,
    expired_at TIMESTAMP,
    
    -- ══════════ HISTORIQUE ALERTES ══════════
    created_reason VARCHAR(255),
    created_by VARCHAR(50) DEFAULT 'system',
    modification_history JSONB DEFAULT '[]',
    times_modified INTEGER DEFAULT 0,
    last_modified_reason VARCHAR(255),
    
    -- ══════════ PERFORMANCE TRACKING ══════════
    times_triggered INTEGER DEFAULT 0,
    times_saved_user INTEGER DEFAULT 0,
    times_ignored INTEGER DEFAULT 0,
    estimated_savings NUMERIC(10,2) DEFAULT 0,
    false_positive_count INTEGER DEFAULT 0,
    false_negative_count INTEGER DEFAULT 0,
    accuracy_rate NUMERIC(5,2),
    
    -- ══════════ NOTIFICATIONS ══════════
    notify_on_trigger BOOLEAN DEFAULT true,
    notification_priority VARCHAR(20) DEFAULT 'normal',
    notification_channels JSONB DEFAULT '["web"]',
    
    -- ══════════ META ══════════
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    display_order INTEGER DEFAULT 100,
    tags JSONB DEFAULT '[]',
    notes TEXT,
    data_sources JSONB DEFAULT '[]',
    
    -- ══════════ TIMESTAMPS ══════════
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- ══════════ CONTRAINTES ══════════
    CONSTRAINT uq_market_trap UNIQUE(team_name, market_type, applies_when),
    CONSTRAINT chk_alert_level CHECK (alert_level IN ('TRAP', 'CAUTION', 'NEUTRAL', 'VALUE', 'SAFE')),
    CONSTRAINT chk_confidence CHECK (confidence_score >= 0 AND confidence_score <= 100),
    CONSTRAINT chk_applies_when CHECK (applies_when IN ('always', 'home', 'away'))
);

-- ══════════ INDEX PERFORMANCE ══════════
CREATE INDEX idx_mt_team_name ON market_traps(team_name);
CREATE INDEX idx_mt_team_normalized ON market_traps(team_name_normalized);
CREATE INDEX idx_mt_market_type ON market_traps(market_type);
CREATE INDEX idx_mt_alert_level ON market_traps(alert_level);
CREATE INDEX idx_mt_applies_when ON market_traps(applies_when);
CREATE INDEX idx_mt_is_active ON market_traps(is_active);
CREATE INDEX idx_mt_confidence ON market_traps(confidence_score);
CREATE INDEX idx_mt_is_reliable ON market_traps(is_reliable);
CREATE INDEX idx_mt_team_market ON market_traps(team_name, market_type);
CREATE INDEX idx_mt_tags ON market_traps USING GIN(tags);
CREATE INDEX idx_mt_combined ON market_traps USING GIN(combined_with_markets);
CREATE INDEX idx_mt_vs_teams ON market_traps USING GIN(vs_specific_teams);
CREATE INDEX idx_mt_compound ON market_traps USING GIN(compound_trap_markets);

-- ══════════ COMMENTAIRES ══════════
COMMENT ON TABLE market_traps IS 'FERRARI 2.0 ULTIMATE - Detection automatique des pieges paris avec auto-learning';
COMMENT ON COLUMN market_traps.alert_level IS 'TRAP=danger, CAUTION=attention, NEUTRAL=neutre, VALUE=opportunite, SAFE=sur';
COMMENT ON COLUMN market_traps.applies_when IS 'always=toujours, home=domicile seulement, away=exterieur seulement';
COMMENT ON COLUMN market_traps.is_compound_trap IS 'True si piege combine (ex: DC_12 + BTTS = double piege)';
COMMENT ON COLUMN market_traps.confidence_score IS '0-100, basé sur sample_size et historical accuracy';
COMMENT ON COLUMN market_traps.auto_adjust_enabled IS 'Si true, le systeme ajuste automatiquement selon resultats';
COMMENT ON COLUMN market_traps.estimated_savings IS 'Estimation argent economise grace a cette alerte';

COMMIT;

SELECT 'SUCCESS: market_traps created' as status;

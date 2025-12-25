-- ═══════════════════════════════════════════════════════════
-- THE QUANTUM SOVEREIGN V3.8 - SCHEMA SQL
-- Créé le: 23 Décembre 2025
-- ═══════════════════════════════════════════════════════════

-- TABLE 1: pick_audit_trail (Logs complets pour debug)
CREATE TABLE IF NOT EXISTS pick_audit_trail (
    id SERIAL PRIMARY KEY,
    pick_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),

    -- Identité
    match_id VARCHAR(100) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    league VARCHAR(100),
    kickoff_time TIMESTAMP,

    -- Versioning
    model_version VARCHAR(20) NOT NULL DEFAULT 'v3.8.0',
    alpha_weights_version VARCHAR(20),
    trust_status VARCHAR(20) DEFAULT 'TRUSTED',

    -- Data Snapshots (JSONB)
    base_dna JSONB,
    effective_dna JSONB,
    modifiers_applied JSONB,
    data_freshness JSONB,

    -- Analyse
    alpha_hunter_report JSONB,
    convergence_result JSONB,
    tactical_narrative TEXT,
    chess_analysis JSONB,
    mc_results JSONB,

    -- Décision
    filter_level_used VARCHAR(20),
    final_decision VARCHAR(20),
    final_market VARCHAR(100),
    final_odds DECIMAL(5,2),
    final_stake DECIMAL(5,4),
    final_edge DECIMAL(5,4),

    -- Seasonality
    seasonality_adjustment JSONB,

    -- Coûts
    claude_cost JSONB,

    -- Execution
    execution_mode VARCHAR(20),
    processing_time_ms INT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pick_audit_date ON pick_audit_trail (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pick_audit_decision ON pick_audit_trail (final_decision);
CREATE INDEX IF NOT EXISTS idx_pick_audit_trust ON pick_audit_trail (trust_status);

-- TABLE 2: processing_checkpoints (Idempotence)
CREATE TABLE IF NOT EXISTS processing_checkpoints (
    match_id VARCHAR(100) PRIMARY KEY,
    current_node INT NOT NULL DEFAULT 0,
    state_snapshot JSONB NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- TABLE 3: ml_training_dataset (Pour futur ML)
CREATE TABLE IF NOT EXISTS ml_training_dataset (
    id SERIAL PRIMARY KEY,
    pick_id UUID,

    -- Features ADN Home
    home_xg_90 DECIMAL(5,3),
    home_xga_90 DECIMAL(5,3),
    home_cs_pct DECIMAL(5,2),
    home_resist_global DECIMAL(5,2),
    home_possession_pct DECIMAL(5,2),

    -- Features ADN Away
    away_xg_90 DECIMAL(5,3),
    away_xga_90 DECIMAL(5,3),
    away_cs_pct DECIMAL(5,2),
    away_resist_global DECIMAL(5,2),
    away_possession_pct DECIMAL(5,2),

    -- Features Collision
    friction_type VARCHAR(50),
    convergence_score DECIMAL(5,2),

    -- Features Contextuelles
    market_type VARCHAR(50),
    hours_before_match INT,
    seasonality_phase VARCHAR(50),

    -- Target (rempli par Reconciler)
    clv_percentage DECIMAL(6,4),
    actual_result VARCHAR(10),

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW(),
    reconciled_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_clv ON ml_training_dataset (clv_percentage) WHERE clv_percentage IS NOT NULL;

-- TABLE 4: cost_tracking (Budget Claude)
CREATE TABLE IF NOT EXISTS cost_tracking (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    service VARCHAR(50) NOT NULL,
    cost_usd DECIMAL(8,4) NOT NULL,
    input_tokens INT,
    output_tokens INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_tracking (date DESC);

-- ═══════════════════════════════════════════════════════════
-- FIN DU SCHEMA V3.8
-- ═══════════════════════════════════════════════════════════

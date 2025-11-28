-- ============================================================
-- TABLE: team_intelligence_history
-- Version: FERRARI 2.0 ULTIMATE - Audit Trail Adaptatif
-- Date: 28 Nov 2025
-- Auteur: Mon_PS Team
-- ============================================================

BEGIN;

DROP TABLE IF EXISTS team_intelligence_history CASCADE;

CREATE TABLE team_intelligence_history (
    id SERIAL PRIMARY KEY,
    
    -- ══════════ REFERENCE ══════════
    team_intelligence_id INTEGER NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    
    -- ══════════ CHANGEMENT ══════════
    field_changed VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(50),
    change_magnitude NUMERIC(6,2),
    
    -- ══════════ CONTEXTE ══════════
    change_reason VARCHAR(255),
    trigger_event VARCHAR(255),
    matches_since_last_change INTEGER,
    
    -- ══════════ IMPACT ══════════
    impact_on_predictions VARCHAR(50),
    affected_markets JSONB DEFAULT '[]',
    confidence_before INTEGER,
    confidence_after INTEGER,
    
    -- ══════════ SOURCE ══════════
    changed_by VARCHAR(50) DEFAULT 'system',
    change_source VARCHAR(100),
    algorithm_version VARCHAR(20),
    
    -- ══════════ VALIDATION ══════════
    is_validated BOOLEAN DEFAULT false,
    validated_by VARCHAR(50),
    validated_at TIMESTAMP,
    validation_notes TEXT,
    
    -- ══════════ META ══════════
    created_at TIMESTAMP DEFAULT NOW()
);

-- ══════════ INDEX ══════════
CREATE INDEX idx_tih_team_id ON team_intelligence_history(team_intelligence_id);
CREATE INDEX idx_tih_team_name ON team_intelligence_history(team_name);
CREATE INDEX idx_tih_field ON team_intelligence_history(field_changed);
CREATE INDEX idx_tih_created ON team_intelligence_history(created_at);
CREATE INDEX idx_tih_change_type ON team_intelligence_history(change_type);
CREATE INDEX idx_tih_affected ON team_intelligence_history USING GIN(affected_markets);

-- ══════════ COMMENTAIRES ══════════
COMMENT ON TABLE team_intelligence_history IS 'FERRARI 2.0 - Historique des changements de profil equipe pour audit et analyse';
COMMENT ON COLUMN team_intelligence_history.change_magnitude IS 'Amplitude du changement (ex: style_score passe de 30 a 60 = +30)';
COMMENT ON COLUMN team_intelligence_history.trigger_event IS 'Evenement declencheur: nouveau_coach, serie_resultats, blessure_cle, etc.';

COMMIT;

SELECT 'SUCCESS: team_intelligence_history created' as status;

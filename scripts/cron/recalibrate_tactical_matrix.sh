#!/bin/bash
# ==============================================================================
# TACTICAL MATRIX - RECALIBRATION QUANT 2.0
# ==============================================================================
set -e

LOG_FILE="/var/log/monps/tactical_matrix_calibration.log"
CONTAINER="monps_postgres"
DB_USER="monps_user"
DB_NAME="monps_db"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "DÉBUT RECALIBRATION TACTICAL MATRIX"

# 1. Recalculer stats réelles
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
DROP TABLE IF EXISTS tactical_matrix_calibrated;
CREATE TABLE tactical_matrix_calibrated AS
SELECT tc_h.playing_style as style_a, tc_a.playing_style as style_b,
    COUNT(*) as real_sample_size,
    ROUND(AVG(mr.score_home + mr.score_away), 2) as real_avg_goals,
    ROUND(100.0 * SUM(CASE WHEN mr.score_home > mr.score_away THEN 1 ELSE 0 END) / COUNT(*), 2) as real_win_rate_a,
    ROUND(100.0 * SUM(CASE WHEN mr.score_home = mr.score_away THEN 1 ELSE 0 END) / COUNT(*), 2) as real_draw_rate,
    ROUND(100.0 * SUM(CASE WHEN mr.score_home < mr.score_away THEN 1 ELSE 0 END) / COUNT(*), 2) as real_win_rate_b,
    ROUND(100.0 * SUM(CASE WHEN mr.score_home > 0 AND mr.score_away > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as real_btts,
    ROUND(100.0 * SUM(CASE WHEN mr.score_home + mr.score_away > 2.5 THEN 1 ELSE 0 END) / COUNT(*), 2) as real_over25
FROM match_results mr
JOIN team_class tc_h ON LOWER(mr.home_team) = LOWER(tc_h.team_name)
JOIN team_class tc_a ON LOWER(mr.away_team) = LOWER(tc_a.team_name)
WHERE mr.is_finished = true
GROUP BY tc_h.playing_style, tc_a.playing_style;"

# 2. Blend Bayesian
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
UPDATE tactical_matrix tm SET 
    sample_size = tmc.real_sample_size,
    avg_goals_total = CASE WHEN tmc.real_sample_size >= 30 THEN tmc.real_avg_goals WHEN tmc.real_sample_size >= 10 THEN ROUND(0.7 * tmc.real_avg_goals + 0.3 * tm.avg_goals_total, 2) ELSE ROUND(0.5 * tmc.real_avg_goals + 0.5 * tm.avg_goals_total, 2) END,
    win_rate_a = CASE WHEN tmc.real_sample_size >= 30 THEN tmc.real_win_rate_a WHEN tmc.real_sample_size >= 10 THEN ROUND(0.7 * tmc.real_win_rate_a + 0.3 * tm.win_rate_a, 2) ELSE ROUND(0.5 * tmc.real_win_rate_a + 0.5 * tm.win_rate_a, 2) END,
    draw_rate = CASE WHEN tmc.real_sample_size >= 30 THEN tmc.real_draw_rate WHEN tmc.real_sample_size >= 10 THEN ROUND(0.7 * tmc.real_draw_rate + 0.3 * tm.draw_rate, 2) ELSE ROUND(0.5 * tmc.real_draw_rate + 0.5 * tm.draw_rate, 2) END,
    win_rate_b = CASE WHEN tmc.real_sample_size >= 30 THEN tmc.real_win_rate_b WHEN tmc.real_sample_size >= 10 THEN ROUND(0.7 * tmc.real_win_rate_b + 0.3 * tm.win_rate_b, 2) ELSE ROUND(0.5 * tmc.real_win_rate_b + 0.5 * tm.win_rate_b, 2) END,
    btts_probability = CASE WHEN tmc.real_sample_size >= 30 THEN tmc.real_btts WHEN tmc.real_sample_size >= 10 THEN ROUND(0.7 * tmc.real_btts + 0.3 * tm.btts_probability, 2) ELSE ROUND(0.5 * tmc.real_btts + 0.5 * tm.btts_probability, 2) END,
    over_25_probability = CASE WHEN tmc.real_sample_size >= 30 THEN tmc.real_over25 WHEN tmc.real_sample_size >= 10 THEN ROUND(0.7 * tmc.real_over25 + 0.3 * tm.over_25_probability, 2) ELSE ROUND(0.5 * tmc.real_over25 + 0.5 * tm.over_25_probability, 2) END,
    confidence_level = CASE WHEN tmc.real_sample_size >= 30 THEN 'high' WHEN tmc.real_sample_size >= 10 THEN 'medium' ELSE 'low' END,
    updated_at = NOW()
FROM tactical_matrix_calibrated tmc WHERE tm.style_a = tmc.style_a AND tm.style_b = tmc.style_b;"

# 3. Recalcul CI
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
UPDATE tactical_matrix SET under_25_probability = ROUND(100.00 - over_25_probability, 2);
UPDATE tactical_matrix SET 
    win_rate_a_ci_lower = CASE WHEN sample_size > 0 THEN ROUND(GREATEST(0, win_rate_a - 1.96 * SQRT(win_rate_a * (100 - win_rate_a) / sample_size)), 2) ELSE NULL END,
    win_rate_a_ci_upper = CASE WHEN sample_size > 0 THEN ROUND(LEAST(100, win_rate_a + 1.96 * SQRT(win_rate_a * (100 - win_rate_a) / sample_size)), 2) ELSE NULL END,
    over25_ci_lower = CASE WHEN sample_size > 0 THEN ROUND(GREATEST(0, over_25_probability - 1.96 * SQRT(over_25_probability * (100 - over_25_probability) / sample_size)), 2) ELSE NULL END,
    over25_ci_upper = CASE WHEN sample_size > 0 THEN ROUND(LEAST(100, over_25_probability + 1.96 * SQRT(over_25_probability * (100 - over_25_probability) / sample_size)), 2) ELSE NULL END,
    btts_ci_lower = CASE WHEN sample_size > 0 THEN ROUND(GREATEST(0, btts_probability - 1.96 * SQRT(btts_probability * (100 - btts_probability) / sample_size)), 2) ELSE NULL END,
    btts_ci_upper = CASE WHEN sample_size > 0 THEN ROUND(LEAST(100, btts_probability + 1.96 * SQRT(btts_probability * (100 - btts_probability) / sample_size)), 2) ELSE NULL END,
    data_quality_score = CASE WHEN sample_size >= 50 THEN 1.00 WHEN sample_size >= 30 THEN 0.85 WHEN sample_size >= 15 THEN 0.70 ELSE 0.50 END,
    last_calibration = NOW()
WHERE sample_size > 0;"

log "FIN RECALIBRATION - SUCCÈS"

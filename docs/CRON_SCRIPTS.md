# 📅 Scripts CRON - Mon_PS

## Scripts de peuplement automatique

| Script | Fréquence | Description |
|--------|-----------|-------------|
| `update_momentum.py` | 0 6 * * * | MAJ team_momentum quotidienne |
| `update_h2h.py` | 0 7 * * * | Sync head_to_head quotidienne |
| `populate_reality_check_results.py` | 0 8 * * * | Analyse Reality Check matchs terminés |
| `populate_fg_sharp_money.py` | */30 * * * * | Détection steam moves |
| `populate_fg_league_stats.py` | 0 9 * * * | Stats par ligue |
| `populate_market_reality_gap.py` | 0 10 * * * | Gap market/reality |
| `recalibrate_tactical_matrix.sh` | 0 6 * * * | Recalibration Bayesian |

## Configuration crontab recommandée
```bash
# Momentum et H2H
0 6 * * * cd /home/Mon_ps && python3 backend/cron/update_momentum.py >> /var/log/monps/cron.log 2>&1
0 7 * * * cd /home/Mon_ps && python3 backend/cron/update_h2h.py >> /var/log/monps/cron.log 2>&1

# Reality Check et analytics
0 8 * * * cd /home/Mon_ps && python3 backend/cron/populate_reality_check_results.py >> /var/log/monps/cron.log 2>&1
0 9 * * * cd /home/Mon_ps && python3 backend/cron/populate_fg_league_stats.py >> /var/log/monps/cron.log 2>&1
0 10 * * * cd /home/Mon_ps && python3 backend/cron/populate_market_reality_gap.py >> /var/log/monps/cron.log 2>&1

# Sharp money detection (toutes les 30 min)
*/30 * * * * cd /home/Mon_ps && python3 backend/cron/populate_fg_sharp_money.py >> /var/log/monps/cron.log 2>&1

# Tactical matrix recalibration
0 6 * * * cd /home/Mon_ps && bash scripts/cron/recalibrate_tactical_matrix.sh >> /var/log/monps/cron.log 2>&1
```

## Tables peuplées

| Table | Rows | Description |
|-------|------|-------------|
| reality_check_results | 839 | Analyses Reality Check |
| market_reality_gap | 135 | Gap market vs reality |
| fg_league_stats | 7 | Stats par ligue |
| fg_sharp_money | 6 | Steam moves détectés |

## Logs

Tous les logs dans `/var/log/monps/`:
- `reality_check_populate.log`
- `sharp_money_detect.log`
- `league_stats.log`
- `market_reality_gap.log`
- `momentum_update.log`

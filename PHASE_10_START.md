# Phase 10 - Data Collection & Automatisation

**Date de début** : 2025-11-11
**Commit précédent** : aa3ab88
**État système** : Bankroll 1030€, ROI 37.5%, Win Rate 62.5%

## Objectifs
1. Intégrer The Odds API
2. Scraper cotes automatiquement (toutes les heures)
3. Détecter arbitrage automatiquement
4. Alertes sur opportunités (spread > 2%)

## Architecture prévue
- Service Python dédié à la collecte
- Stockage PostgreSQL + TimescaleDB
- Métriques Prometheus pour tracking
- Alertes Alertmanager sur opportunités

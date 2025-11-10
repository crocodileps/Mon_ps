## Analytics Avancés

### Endpoint comprehensive analytics

```bash
curl http://localhost:8001/stats/analytics/comprehensive?period_days=30
```

Cet endpoint génère 21 types de logs avancés :

- CLV par bookmaker/marché/sport
- Kelly sizing analysis
- Bankroll monitoring
- Stratégie Tabac vs Ligne
- Market efficiency
- Losing streak detection
- Sharpe Ratio
- Et 14 autres métriques...

Les logs sont visibles via `journalctl -u monps-api -f`


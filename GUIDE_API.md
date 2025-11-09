# Mon_PS - Guide API

## URLs
- **API** : http://91.98.131.218:8001
- **Swagger** : http://91.98.131.218:8001/docs
- **ReDoc** : http://91.98.131.218:8001/redoc

## Exemples d'utilisation

### Récupérer les matchs
```bash
curl http://91.98.131.218:8001/odds/matches
```

### Voir les opportunités
```bash
curl "http://91.98.131.218:8001/opportunities/?min_spread_pct=10"
```

### Créer un pari
```bash
curl -X POST http://91.98.131.218:8001/bets/ \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": "...",
    "outcome": "Home",
    "bookmaker": "Bet365",
    "odds_value": 2.50,
    "stake": 10.00,
    "bet_type": "value"
  }'
```

### Stats globales
```bash
curl http://91.98.131.218:8001/stats/global
```

## Commandes serveur
```bash
# Redémarrer l'API
sudo systemctl restart monps-api

# Voir les logs
sudo journalctl -u monps-api -f

# Statut
sudo systemctl status monps-api
```

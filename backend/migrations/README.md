# Migrations Mon_PS

## Migration: add_clv_odds_close_market_type_to_bets

**Date:** 2025-11-10

**Révision:** abbc4f65c12b

### Changements

Ajoute 3 nouvelles colonnes à la table `bets` :

1. **clv** (FLOAT, nullable)
   - Closing Line Value
   - Mesure la qualité du pari
   - Formule: `(odds_accepted / odds_close) - 1`
   - Exemple: CLV de +2.5% = bon pari

2. **odds_close** (FLOAT, nullable)
   - Cote de clôture du marché
   - Utilisée pour calculer le CLV
   - Récupérée après le début du match

3. **market_type** (VARCHAR(50), nullable)
   - Type de marché du pari
   - Valeurs possibles: h2h, totals, btts, asian_handicap, etc.
   - Index créé pour optimiser les requêtes analytics

### Appliquer la migration

```bash
# En local
cd backend
alembic upgrade head

# Sur le serveur
ssh root@91.98.131.218
cd /home/Mon_ps/backend
source venv/bin/activate
alembic upgrade head
```

### Rollback (si nécessaire)

```bash
alembic downgrade -1
```

### Vérifier les colonnes

```bash
psql -h localhost -U postgres -d mon_ps -c "\d bets"
```


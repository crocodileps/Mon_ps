# 🎉 CHANGELOG v2.0 - Settlement & CLV Automatique

**Date de release : 19 Novembre 2025**

---

## 🚀 Fonctionnalités Majeures

### Settlement Automatique
- Détection automatique matchs terminés (commence_time + 3h)
- Récupération scores via The Odds API
- Règlement automatique 2x/jour (8h et 20h)
- Mise à jour profit/payout/status automatique
- Marquage `settled_by='auto'`

### Calcul CLV Automatique
- Calcul CLV sans requête API supplémentaire
- Réutilisation flux de collecte d'odds existant
- Exécution automatique 4x/jour (toutes les 4h)
- Formule : CLV = (closing_odds / obtained_odds - 1) * 100

### Frontend P&L 2.0
- Colonne CLV ajoutée au tableau
- Badge vert/rouge selon valeur (positif/négatif)
- Affichage "--" quand non calculé
- 8 paris trackés (107€ de mise)

---

## 🔧 Changements Techniques

### Backend
- **Nouveaux fichiers** :
  - `scripts/auto_settlement.py` - Script settlement auto
  - `scripts/auto_clv.py` - Script calcul CLV
  - `scripts/daily_settlement.sh` - Orchestrateur
  - `api/routes/settlement_routes.py` - Routes API settlement
  - `crontab` - Configuration cron jobs

- **Modifications** :
  - Table `bets` : +3 colonnes (closing_odds, clv_percent, settled_by)
  - Port mapping corrigé (8001 externe → 8000 interne)
  - `/bets/history` retourne nouveaux champs

### Frontend
- **Nouveaux composants** :
  - Colonne CLV dans tableau P&L
  - Badge conditionnel vert/rouge
  
- **Nettoyage** :
  - Suppression 3,207 lignes code obsolète
  - Suppression composants inutilisés
  - Suppression hooks redondants

### Cron Jobs
```cron
# Settlement (8h et 20h)
0 8 * * * cd /app && bash scripts/daily_settlement.sh
0 20 * * * cd /app && bash scripts/daily_settlement.sh

# CLV (toutes les 4h)
0 */4 * * * cd /app && python3 scripts/auto_clv.py
```

---

## 📊 Métriques

### Requêtes API Optimisées
- Collecte odds : 6 req/jour (1 toutes les 4h)
- Settlement : 10-20 req/jour (matchs terminés uniquement)
- CLV : 0 req/jour (réutilise flux existant)
- **Total : ~25 req/jour** (quota 500/mois ✅)

### Paris en Production
- 8 paris pending
- 107€ de mise totale
- Settlement auto actif
- CLV auto actif

---

## 🎯 Prochains Settlements

- **Demain 8h** : Premier settlement automatique
- **Toutes les 4h** : Calcul CLV automatique
- **Logs** : `/var/log/settlement.log` et `/var/log/clv.log`

---

## 📚 Documentation

- `FEUILLE_DE_ROUTE_V2.md` - Roadmap complète
- `ARCHITECTURE_V2.md` - Architecture technique
- `CHANGELOG_V2.0.md` - Ce fichier

---

## 🔗 Pull Requests Mergées

- PR #2 : Settlement & CLV Automatique
- PR #3 : Colonne CLV Frontend

---

**Version stable, prête pour production ! 🚀**

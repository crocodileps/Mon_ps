# 📊 Mon_PS - Système CLV (Closing Line Value)

## 🎯 Vue d'ensemble

Système automatisé de tracking des paris sportifs avec calcul du CLV (Closing Line Value) basé sur Pinnacle. Le CLV mesure la qualité de vos paris en comparant vos cotes obtenues avec la closing line de Pinnacle, considéré comme le marché le plus efficient.

**CLV positif = vous battez le marché = +EV sur le long terme**

---

## 🏗️ Architecture

```
monitoring/collector/
├── odds_collector.py       # Collecteur v3 (h2h + totals)
├── clv_tracker.py          # Calcul automatique du CLV
├── add_bet.py              # Helper CLI pour ajouter des paris
├── .env                    # Configuration API
├── cache/                  # Cache des dernières collectes
└── logs/                   # Logs détaillés
```

---

## 📈 Métriques Clés

| Métrique | Objectif | Description |
|----------|----------|-------------|
| **CLV Moyen** | > 1% | % au-dessus de la closing line Pinnacle |
| **ROI** | > 0% | Return on Investment global |
| **Win Rate** | N/A | Non pertinent si CLV positif |
| **Sharp Ratio** | < 3 | Variance des résultats |

---

## 🔧 Configuration

### Variables d'environnement (.env)

```bash
# API The Odds API
ODDS_API_KEY=your_api_key
ODDS_API_BASE_URL=https://api.the-odds-api.com/v4

# Base de données PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=monps_db
DB_USER=monps_user
DB_PASSWORD=your_password

# Configuration collecteur
MARKETS=h2h,totals
BOOKMAKERS=pinnacle,bet365,unibet,winamax,betclic
SPORTS_LIMIT=3
```

---

## 📅 Cron Jobs (Automatisation)

```bash
# Collecte des cotes (10h, 14h, 18h)
0 10,14,18 * * * cd /home/Mon_ps/monitoring/collector && export $(cat .env | xargs) && /usr/bin/python3 odds_collector.py >> logs/cron.log 2>&1

# Calcul CLV (30 min après chaque collecte)
30 10,14,18 * * * cd /home/Mon_ps/monitoring/collector && export $(cat .env | xargs) && /usr/bin/python3 clv_tracker.py >> logs/clv_tracker.log 2>&1
```

**Quota API** : 9 requêtes/jour = 270/mois (sur 500 disponibles)

---

## 🎰 Workflow Utilisateur

### 1. Identifier une opportunité

```bash
# Via le frontend
http://91.98.131.218:3001/manual-bets
# Cliquer "Nouveau Pari"
```

### 2. Ajouter un pari (CLI alternative)

```bash
cd /home/Mon_ps/monitoring/collector
export $(cat .env | xargs)
python3 add_bet.py
```

### 3. Placer le pari chez le bookmaker

Placer le pari réel chez Bet365, Winamax, Unibet, etc.

### 4. Attendre le kickoff

Le CLV sera calculé APRÈS le kickoff avec la dernière cote Pinnacle.

### 5. Enregistrer le résultat

Via le frontend, cliquer Win ou Loss pour enregistrer le profit/perte.

---

## 📊 Tables PostgreSQL

### odds_history (h2h)
Historique des cotes 1X2 par bookmaker.

### odds_totals (Over/Under)
Historique des cotes Over/Under avec lignes.

### manual_bets
Paris manuels avec tracking CLV.

### manual_bets_stats (Vue)
Statistiques agrégées (CLV moyen, ROI, etc.).

---

## 🔄 Scripts

### odds_collector.py v3
- Collecte h2h ET totals
- Cache intelligent (évite les doublons)
- Priorité : EPL, La Liga, Ligue 1
- Logging structuré

### clv_tracker.py
- Récupère closing line Pinnacle
- Calcule CLV pour chaque pari
- Met à jour automatiquement la base
- Supporte h2h et totals

### add_bet.py
- Interface interactive CLI
- Liste les matchs disponibles
- Validation des données
- Confirmation avant insertion

---

## 🌐 API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/manual-bets/` | Lister les paris |
| GET | `/manual-bets/stats` | Statistiques globales |
| GET | `/manual-bets/{id}` | Détail d'un pari |
| POST | `/manual-bets/` | Créer un pari |
| PUT | `/manual-bets/{id}` | Mettre à jour (résultat) |
| DELETE | `/manual-bets/{id}` | Supprimer |
| POST | `/manual-bets/calculate-clv` | Déclencher calcul CLV |

---

## 📱 Frontend

**URL** : http://91.98.131.218:3001/manual-bets

**Fonctionnalités** :
- Dashboard avec statistiques (CLV moyen, ROI, profit)
- Liste des paris avec détails
- Filtres (Tous, En attente, Terminés, CLV Positif)
- Bouton "Calculer CLV" 
- Formulaire "Nouveau Pari" avec sélection de match
- Boutons Win/Loss pour enregistrer résultats

---

## 🧮 Formule CLV

```
CLV% = (Cote_obtenue - Closing_line) / Closing_line × 100
```

**Exemple** :
- Tu prends Over 3.0 @ **2.05** chez Bet365
- Pinnacle ferme à **1.94**
- CLV = (2.05 - 1.94) / 1.94 × 100 = **+5.67%** ✅

---

## 🚨 Troubleshooting

### "Pas de données Pinnacle"
- Vérifier que le match est dans odds_totals
- Pinnacle doit être collecté AVANT le kickoff

### CLV non calculé
- Le kickoff doit être passé
- Vérifier le match_id correct

### Erreur connexion DB
```bash
export $(cat .env | xargs)
docker ps | grep postgres
```

---

## 📈 Interprétation des Résultats

| CLV Moyen | Interprétation |
|-----------|----------------|
| > 3% | Excellent - Pro level |
| 1-3% | Très bien - Sustainable edge |
| 0-1% | Correct - Marginal edge |
| < 0% | Attention - Losing edge |

**Important** : Un CLV positif ne garantit pas des gains immédiats (variance), mais sur le long terme (1000+ paris), un CLV > 1% devrait générer des profits.

---

## 📁 Fichiers Logs

```bash
# Logs collecteur
tail -f /home/Mon_ps/monitoring/collector/logs/cron.log

# Logs CLV tracker
tail -f /home/Mon_ps/monitoring/collector/logs/clv_tracker_$(date +%Y%m%d).log
```

---

## 🔐 Sécurité

- Accès VPN uniquement (WireGuard)
- Credentials dans .env (non versionnés)
- Pas de données sensibles dans les logs

---

**Version** : 1.0  
**Dernière mise à jour** : 2025-11-17  
**Auteur** : Mon_PS Team

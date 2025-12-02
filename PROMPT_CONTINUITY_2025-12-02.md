═══════════════════════════════════════════════════════════════════════════════
          🎯 MON_PS - SESSION DE CONTINUITÉ
               MARKET TRAPS V4 + STEAM TRACKER V2
                        02 DÉCEMBRE 2025
═══════════════════════════════════════════════════════════════════════════════

## 🎭 QUI TU ES

Tu es un **Développeur Expert Senior Quant** spécialisé en systèmes de paris sportifs.
Tu travailles sur **Mon_PS**, une plateforme de trading sportif en PRODUCTION.

**Ton approche OBLIGATOIRE:**
- 🔬 SCIENTIFIQUE : Observer → Analyser → Diagnostiquer → Agir
- 🛡️ DÉFENSIF : Ne JAMAIS casser ce qui fonctionne
- 📊 MÉTHODIQUE : Vérifier AVANT chaque modification
- 📝 DOCUMENTÉ : Commenter et expliquer chaque choix
- �� QUANT : Raisonner en probabilité, pas en % de cote

**Principe Mya:** "Le temps n'est pas un problème, je veux une page parfaite"

═══════════════════════════════════════════════════════════════════════════════
## 🏗️ INFRASTRUCTURE
═══════════════════════════════════════════════════════════════════════════════

- **Serveur:** Hetzner CCX23 (4 vCPU, 16GB RAM) - Ubuntu 24.04
- **IP:** 91.98.131.218 (VPN WireGuard uniquement)
- **Stack:** Docker Compose (PostgreSQL + TimescaleDB, FastAPI, Next.js 14, Redis)
- **Frontend:** http://91.98.131.218:3001
- **Backend:** http://91.98.131.218:8001

═══════════════════════════════════════════════════════════════════════════════
## ✅ CE QUI A ÉTÉ ACCOMPLI CETTE SESSION (02 Déc 2025)
═══════════════════════════════════════════════════════════════════════════════

### 1. 🎯 MARKET TRAPS V4 - ACCURACY 82.3% (+27.6%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Évolution:**
| Version | Accuracy | Faux Positifs | Amélioration |
|---------|----------|---------------|--------------|
| V1 Initial | 54.7% | 150 | - |
| V2 HOME/AWAY fix | 64.2% | 118 | +9.5% |
| V3 Seuils optimisés | 75.2% | 74 | +11.0% |
| V4 Affinement | **82.3%** | **44** | +7.1% |

**Bugs corrigés:**
1. **Logique HOME/AWAY manquante** - Les traps "nuls domicile" se déclenchaient
   même quand l'équipe jouait à l'extérieur !
```sql
   UPDATE market_traps SET applies_away = false
   WHERE alert_reason LIKE '%domicile%' OR market_type = 'home';
   UPDATE market_traps SET applies_home = false
   WHERE alert_reason LIKE '%extérieur%' OR market_type = 'away';
```

2. **26 picks mal résolus** - Scores API incorrects stockés
   - Exemple: Gladbach vs Leipzig → Score 1-0 stocké vs 0-0 réel
   - Script créé: `/app/scripts/fix_bad_resolutions.py`

**Seuils finaux optimisés:**
```python
ALERT_RULES = {
    "dc_12": CAUTION 48% (était 40%),
    "btts_yes": CAUTION 35% (était 48%),  # Évite faux positifs 40-50%
    "under_25": CAUTION 3.5 buts (était 3.2),
    # Autres inchangés
}
```

**Fichiers modifiés:**
- `/app/scripts/ferrari/populate_team_intelligence_v3.py` - Seuils
- `/app/scripts/trap_feedback_analyzer.py` - Logique HOME/AWAY V2
- `/app/scripts/fix_bad_resolutions.py` - NOUVEAU

---

### 2. 🔥 STEAM TRACKER V2 - QUANT EDITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Critique quant appliquée:**
- ❌ AVANT: Seuil 10% de cote (naïf) 
- ✅ APRÈS: Seuil 3% de probabilité implicite (quant)

**Exemple:**
```
Cote 1.20 → 1.08 = Prob 83% → 93% = +10 points de proba (ÉNORME)
Cote 5.00 → 4.50 = Prob 20% → 22% = +2 points de proba (bruit)
```

**Améliorations V2:**
1. Calcul en probabilité implicite
2. Distinction LATE/EARLY steam
3. Filtre ligues majeures (liquidité)
4. Score normalisé sur 100

**Fichiers créés:**
- `/app/scripts/steam_tracker_v2.py`
- `/app/scripts/steam_validator.py`

---

### 3. 🛡️ STEAM VALIDATOR - CHANGEMENT DE PARADIGME CRUCIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Découverte critique:** Suivre le steam = PERDANT !
```
STRONG STEAM (>3%): 49.4% WR | -30.12€  ← On arrive APRÈS les syndicats
STRONG DRIFT (<-3%): 49.1% WR | -67.14€ ← Même problème
```

**Nouveau paradigme:**
| Avant (Naïf) | Après (Quant) |
|--------------|---------------|
| Steam = Parier | Steam = **Confirmer** |
| Drift = Éviter | Drift = **Bloquer** nos paris |
| Signal autonome | Signal de **validation** |

**Logique du Validator:**
```python
# Notre modèle dit "HOME" + Steam HOME = ✅ CONFIRMÉ (+10 confiance)
# Notre modèle dit "HOME" + Drift HOME = 🛑 BLOQUÉ (marché sait quelque chose)
# Notre modèle dit "HOME" + Steam AWAY = ⚠️ ATTENTION (-20 confiance)
```

**Résultats rétroactifs:**
```
WOULD_BLOCK: 36.5% WR | -15.25€ | 52 picks
→ En bloquant ces paris: +15.25€ économisés !
```

---

### 4. 🔄 INTÉGRATION EN COURS - Steam dans Orchestrator V7
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Branche active:** `feature/integrate-steam-validator`

**État:** PATCH PRÉPARÉ, PAS ENCORE APPLIQUÉ

**Fichier cible:** `/app/agents/clv_tracker/orchestrator_v7_smart.py`

**Modifications à faire:**

1. **Ajouter l'import** (après ligne ~70):
```python
# Steam Validator Integration
try:
    sys.path.append("/app/scripts")
    from steam_validator import validate_prediction, get_steam_score
    STEAM_VALIDATOR_ENABLED = True
except ImportError:
    STEAM_VALIDATOR_ENABLED = False
```

2. **Ajouter la méthode** `validate_with_steam()` dans la classe

3. **Intégrer dans la boucle** (après `scoring = self.calculate_smart_score(...)`):
```python
# === STEAM VALIDATOR INTEGRATION ===
steam_result = self.validate_with_steam(match['match_id'], market, scoring['confidence'], scoring['sweet_score'])

if not steam_result['validated'] and steam_result['action'] == 'BLOCK':
    logger.info(f"🛑 STEAM BLOCK: {match['home_team']} vs {match['away_team']} - {market}")
    self.stats['filtered_out'] += 1
    continue
```

═══════════════════════════════════════════════════════════════════════════════
## 🎯 PROCHAINES ÉTAPES (PRIORITÉ)
═══════════════════════════════════════════════════════════════════════════════

### PRIORITÉ 1: Terminer l'intégration Steam Validator
```bash
# 1. Appliquer le patch dans orchestrator_v7_smart.py
# 2. Tester
docker exec monps_backend python3 /app/agents/clv_tracker/orchestrator_v7_smart.py --hours 24

# 3. Commit
git add -A
git commit -m "feat: Intégration Steam Validator dans Orchestrator V7"
git push origin feature/integrate-steam-validator
git checkout main
git merge feature/integrate-steam-validator
```

### PRIORITÉ 2: Ajouter crons
```bash
# Dans crontab:
08:45 → fix_bad_resolutions.py (après settlement)
12:00 → steam_tracker_v2.py (mise à jour steam scores)
```

### PRIORITÉ 3: Lineup Impact Engine (Notes Mya)
```python
# Ajustement xG selon absences
KEY_PLAYER_IMPACT = {
    'Harry Kane': {'att_impact': -0.35},  # Énorme perte offensive
    'Alisson': {'def_impact': +0.20},     # Encaisse plus sans lui
    'Rodri': {'def_impact': +0.15, 'att_impact': -0.10}
}
# Source: API-Football injuries/lineups
```

### PRIORITÉ 4: Monte Carlo V3 (Notes Mya)
Simulation minute par minute avec:
- Mode "Panic Attack" si favori perd (xG x 1.5)
- Mode "Gestion" si favori gagne +2 (xG x 0.6)
- Money Time 75min+ (xG x 1.2)

═══════════════════════════════════════════════════════════════════════════════
## 📁 FICHIERS CLÉS CRÉÉS/MODIFIÉS
═══════════════════════════════════════════════════════════════════════════════
```
/app/scripts/
├── ferrari/
│   └── populate_team_intelligence_v3.py  # Seuils ALERT_RULES modifiés
├── trap_feedback_analyzer.py             # Logique HOME/AWAY V2
├── fix_bad_resolutions.py                # NOUVEAU - Corrige picks mal résolus
├── steam_tracker_v2.py                   # NOUVEAU - Calcul probabilité implicite
└── steam_validator.py                    # NOUVEAU - Filtre intelligent

/app/agents/clv_tracker/
└── orchestrator_v7_smart.py              # À MODIFIER - Intégration Steam
```

═══════════════════════════════════════════════════════════════════════════════
## �� MÉTRIQUES ACTUELLES
═══════════════════════════════════════════════════════════════════════════════

### Market Traps
| Métrique | Valeur |
|----------|--------|
| Total traps actifs | 196 |
| TRAP level | 106 |
| CAUTION level | 90 |
| Accuracy globale | 82.3% |
| Traps à 0% | 0 |

### Steam Tracker
| Catégorie | Picks | Win Rate | Profit |
|-----------|-------|----------|--------|
| WOULD_BLOCK | 52 | 36.5% | -15.25€ |
| WOULD_REDUCE | 38 | 28.9% | +0.31€ |
| WOULD_BOOST | 30 | 46.7% | -4.11€ |
| NO_CHANGE | 175 | 41.1% | -8.45€ |

### Picks mis à jour
- 2849 picks avec steam_score (odds_movement)
- 26 picks corrigés (résolution incorrecte)

═══════════════════════════════════════════════════════════════════════════════
## 🔧 COMMANDES ESSENTIELLES
═══════════════════════════════════════════════════════════════════════════════

### Régénérer Market Traps
```bash
docker exec monps_backend python3 /app/scripts/ferrari/populate_team_intelligence_v3.py
docker exec monps_postgres psql -U monps_user -d monps_db -c "TRUNCATE market_traps;"
docker exec monps_backend python3 /app/scripts/populate_market_traps.py
docker exec monps_postgres psql -U monps_user -d monps_db -c "
UPDATE market_traps SET applies_away = false
WHERE alert_reason LIKE '%domicile%' OR market_type = 'home';
UPDATE market_traps SET applies_home = false
WHERE alert_reason LIKE '%extérieur%' OR market_type = 'away';"
docker exec monps_backend python3 /app/scripts/trap_feedback_analyzer.py 30
```

### Tester Steam Tracker
```bash
docker exec monps_backend python3 /app/scripts/steam_tracker_v2.py
docker exec monps_backend python3 /app/scripts/steam_validator.py
```

### Corriger picks mal résolus
```bash
docker exec monps_backend python3 /app/scripts/fix_bad_resolutions.py
```

### Git - État actuel
```bash
git branch  # feature/integrate-steam-validator (active)
git log --oneline -5
# 32eb0eb feat: Steam Tracker V2 + Validator - Filtre intelligent
# 52ee277 feat: Market Traps V4 - Accuracy 82.3% (+27.6%)
# b37e546 feat: Market Traps V3 - Seuils optimisés
# ccc484d fix: Market Traps V2 - Logique HOME/AWAY corrigée
# c2abdd4 feat: Activation market_traps - 218 pièges détectés
```

═══════════════════════════════════════════════════════════════════════════════
## 💡 LEÇONS QUANT APPRISES CETTE SESSION
═══════════════════════════════════════════════════════════════════════════════

### 1. Steam Chasing = PERDANT
```
Tu arrives APRÈS les syndicats. À 2.03, la cote est déjà "efficiente".
La valeur a été mangée par les pros qui ont parié à 2.35, 2.30, 2.20.
```

### 2. Calcul probabilité, pas % cote
```python
# ❌ MAUVAIS
drop_percent = (opening_odds - current_odds) / opening_odds

# ✅ BON
prob_open = 1 / opening_odds
prob_curr = 1 / current_odds
steam_score = (prob_curr - prob_open) * 1000  # En points de proba
```

### 3. Steam = Filtre, pas Déclencheur
```
NE PARIE PAS parce que ça a bougé.
UTILISE le mouvement pour VALIDER ou BLOQUER tes autres modèles.
```

### 4. Améliorer > Désactiver
```
Mya: "On ne peut pas les améliorer pour ne pas que le trap se trompe?"
→ Toujours chercher la cause racine avant de désactiver.
```

═══════════════════════════════════════════════════════════════════════════════
## 🏷️ COMMITS GIT CETTE SESSION
═══════════════════════════════════════════════════════════════════════════════

| Hash | Message |
|------|---------|
| 32eb0eb | feat: Steam Tracker V2 + Validator - Filtre intelligent |
| 52ee277 | feat: Market Traps V4 - Accuracy 82.3% (+27.6%) |
| b37e546 | feat: Market Traps V3 - Seuils optimisés - Accuracy 75.2% |
| ccc484d | fix: Market Traps V2 - Logique HOME/AWAY corrigée |

═══════════════════════════════════════════════════════════════════════════════
## 📝 NOTES MYA POUR PROCHAINES SESSIONS
═══════════════════════════════════════════════════════════════════════════════

### Lineup Impact Engine
- Récupérer blessures/compos via API-Football
- Créer table `key_player_impacts`
- Ajuster xG en temps réel

### Monte Carlo V3
- Simulation 10000 matchs × 90 minutes
- Game state factors (panic, gestion, money time)
- Marchés complexes: Home & BTTS, Asian Handicap

### Market Steam Tracker (amélioration)
- Snapshot toutes les 5-10 min (pas 1h)
- Détecter steam à -2% (début), pas -10% (fin)
- Comparer avec "Fair Odds" du modèle

═══════════════════════════════════════════════════════════════════════════════
                         FIN DU PROMPT DE CONTINUITÉ
                              Version: 4.0.0
                           Date: 02 Décembre 2025
═══════════════════════════════════════════════════════════════════════════════

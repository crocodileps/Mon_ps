# 🔄 GUIDE DE CONTINUATION - MON_PS

**Date de création:** 12 Novembre 2025  
**Objectif:** Assurer la continuité du développement sans casser le système en production

---

## 🚨 RÈGLES CRITIQUES (À SUIVRE ABSOLUMENT)

### 1. NE JAMAIS TOUCHER SANS BACKUP
```bash
# TOUJOURS faire un backup avant modification
cp fichier.yml fichier.yml.backup-$(date +%Y%m%d-%H%M%S)

# Vérifier que le backup existe
ls -la *.backup*
```

### 2. TESTER AVANT DE DEPLOYER
```bash
# Valider docker-compose AVANT de restart
docker compose config > /dev/null && echo "✅ Valide" || echo "❌ Erreur"

# Tester collector AVANT d'automatiser
python3 odds_collector.py
```

### 3. COMMITS PROPRES ET DESCRIPTIFS
```bash
# Format de commit :
git commit -m "type: description courte

- Point 1
- Point 2
- Point 3"

# Types: feat, fix, docs, refactor, test
```

---

## 📊 ÉTAT ACTUEL DU SYSTÈME (12 Nov 2025)

### Services Actifs (6)
```
✅ monps_postgres      : 5432 (TimescaleDB)
✅ monps_backend       : 8001 (FastAPI)
✅ monps_frontend      : 3001 (Next.js 14)
✅ monps_prometheus    : 9090 (Métriques)
✅ monps_grafana       : 3000 (Dashboards)
✅ monps_alertmanager  : 9093 (Alertes email) ⭐
```

### Données
```
- 144,042 cotes collectées
- 60 matchs actifs
- 10+ opportunités (jusqu'à 57% spread)
- Quota API: 491/500 restant
```

### Collector v2.0
```
Fichier: /home/Mon_ps/monitoring/collector/odds_collector.py
Status: ✅ OPÉRATIONNEL
Cron: Toutes les 3h (0 */3 * * *)
Cache: /home/Mon_ps/monitoring/collector/cache/*.json
Économie: 97% (3 requêtes au lieu de 500)
```

### Alertes Email
```
Fichier: /home/Mon_ps/monitoring/config/alertmanager/alertmanager.yml
Status: ✅ CONFIGURÉ (test réussi)
Email: karouche.myriam@gmail.com
SMTP: Gmail (vozuzectmdzgfymx)
Repeat: 24h par défaut, 30min pour site down
```

---

## 🔧 FICHIERS CRITIQUES (NE PAS CASSER)

### 1. Docker Compose Principal
```
Fichier: /home/Mon_ps/monitoring/docker-compose.yml
⚠️ CRITIQUE - Contient les 6 services
Backup: docker-compose.yml.backup-*
Test: docker compose config
```

### 2. Collector Optimisé
```
Fichier: /home/Mon_ps/monitoring/collector/odds_collector.py
✅ Fonctionnel - NE PAS modifier sans backup
Backup: odds_collector.py.OLD
Test: python3 odds_collector.py
```

### 3. Config Alertmanager
```
Fichier: /home/Mon_ps/monitoring/config/alertmanager/alertmanager.yml
✅ Templates HTML fonctionnels
Backup: alertmanager.yml.backup-*
Test: docker compose restart alertmanager
```

### 4. Règles Prometheus
```
Fichier: /home/Mon_ps/monitoring/config/prometheus/rules/alerts.yml
Status: Alertes configurées (6)
Reload: curl -X POST http://localhost:9090/-/reload (désactivé)
Alternative: docker compose restart prometheus
```

---

## 🎯 PROCHAINES ACTIONS PRIORITAIRES

### 1. Backend Metrics (URGENT)
**Problème:** Backend ne remonte pas les valeurs des métriques opportunités
**Fichier:** `/home/Mon_ps/backend/api/routes/metrics.py`
**Action:**
```python
# Ajouter un endpoint qui rafraîchit les métriques depuis la DB
@router.get("/metrics/refresh")
def refresh_metrics():
    # Compter opportunités depuis v_current_opportunities
    # Mettre à jour monps_current_opportunities.set(count)
    # Mettre à jour monps_max_spread_percent.set(max_spread)
    return {"updated": True}
```

### 2. Dashboard Grafana
**Problème:** Dashboard pas mis à jour avec nouvelles données
**Action:** Importer dashboard depuis /home/Mon_ps/backend/dashboard_opportunities.json

### 3. Tests Automatisés
**Action:** Créer /home/Mon_ps/monitoring/collector/test_collector.py

### 4. Backups PostgreSQL
**Action:** Automatiser via cron (actuellement à 3h mais script à vérifier)

---

## 📋 COMMANDES ESSENTIELLES

### Vérifier État Système
```bash
# Services Docker
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Dernière collecte
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT sport, MAX(collected_at), COUNT(*)
FROM odds_history
GROUP BY sport;"

# Opportunités actuelles
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT home_team || ' vs ' || away_team, home_spread_pct
FROM v_current_opportunities
WHERE home_spread_pct > 5
ORDER BY home_spread_pct DESC
LIMIT 10;"

# Quota API restant
curl -s http://localhost:8001/metrics | grep monps_api_requests_remaining
```

### Lancer Collector Manuellement
```bash
cd /home/Mon_ps/monitoring/collector
export $(cat .env | xargs)
python3 odds_collector.py
```

### Redémarrer Services (Safe)
```bash
cd /home/Mon_ps/monitoring

# UN service à la fois
docker compose restart backend
docker compose restart alertmanager
docker compose restart prometheus

# JAMAIS restart postgres en production sans backup !
```

### Tester Alertes
```bash
# Envoyer alerte test (changer le nom à chaque fois)
curl -X POST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestNouvelleConversation123"},
    "annotations": {"summary": "Test système alertes"},
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }]'

# Voir logs
docker logs monps_alertmanager --since 2m
```

---

## 🚫 À NE JAMAIS FAIRE

1. ❌ **Supprimer docker-compose.yml sans backup**
2. ❌ **Modifier odds_collector.py sans tester**
3. ❌ **Restart postgres en production**
4. ❌ **Push sur GitHub sans commit propre**
5. ❌ **Exposer credentials dans les commits**
6. ❌ **Utiliser `--break-system-packages` sans réfléchir**
7. ❌ **Remplacer un fichier sans vérifier la structure de la DB**

---

## 🔍 DÉBUGGAGE

### Collector ne démarre pas
```bash
# Vérifier variables d'environnement
cat /home/Mon_ps/monitoring/collector/.env

# Tester connexion DB
docker exec monps_postgres psql -U monps_user -d monps_db -c "SELECT 1;"

# Voir logs complets
python3 odds_collector.py 2>&1 | tee debug.log
```

### Alertes pas reçues
```bash
# Vérifier repeat_interval (24h par défaut)
grep repeat_interval /home/Mon_ps/monitoring/config/alertmanager/alertmanager.yml

# Changer nom de l'alerte pour forcer envoi
# OU attendre 24h
# OU réduire repeat_interval à 1m pour test
```

### Backend ne répond pas
```bash
# Logs backend
docker logs monps_backend --tail 100

# Restart safe
docker compose restart backend

# Tester API
curl http://localhost:8001/health
```

---

## 📚 DOCUMENTATION

- **PLAN_ACTION_MON_PS.md** : Actions prioritaires
- **SYNTHESE_MON_PS.md** : Vue d'ensemble complète
- **GUIDE_CONTINUATION.md** : Ce fichier (continuité)

---

## 🎯 CHECKLIST NOUVELLE SESSION

Avant de commencer une nouvelle session de développement :

- [ ] Lire ce guide
- [ ] Vérifier état système (`docker ps`)
- [ ] Voir dernière collecte (DB)
- [ ] Backup fichiers à modifier
- [ ] Tester en local avant prod
- [ ] Commit propre avec message descriptif
- [ ] Mettre à jour ce guide si nécessaire

---

## 📞 RAPPELS IMPORTANTS
```
Serveur: Hetzner CCX23 (91.98.131.218)
Accès: VPN WireGuard only
DB: PostgreSQL 16 + TimescaleDB
API Key: Dans /home/Mon_ps/monitoring/collector/.env
Email: karouche.myriam@gmail.com
```

---

**Ce guide DOIT être lu au début de chaque nouvelle session de développement !**

**Dernière mise à jour:** 12 Novembre 2025 18:00
**Status:** ✅ Système en production stable

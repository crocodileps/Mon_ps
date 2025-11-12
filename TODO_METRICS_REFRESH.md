# 🎯 TODO: Endpoint /metrics/refresh

**Date:** 13 Novembre 2025  
**Priorité:** MOYENNE (pas critique)

---

## ❌ CE QUI N'A PAS MARCHÉ

Tentative de créer `/metrics/refresh` avec fichier centralisé de métriques.

**Problèmes rencontrés:**
- Métriques dupliquées entre fichiers
- Erreurs d'import dans conteneur
- 2h de debug sans succès
- Risque de casser le système stable

**Leçon:** Ne pas modifier le core backend en production sans environnement de test.

---

## ✅ SOLUTION ALTERNATIVE (Plus simple)

Au lieu de modifier le backend, utiliser **un script externe** qui :
1. Lit la DB directement
2. Met à jour les métriques via l'API Prometheus
3. Tourne en background toutes les 5 minutes

### Script proposé:
```python
# /home/Mon_ps/monitoring/metrics_updater.py
import psycopg2
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import time

while True:
    # Lire DB
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM v_current_opportunities WHERE spread > 5")
    count = cursor.fetchone()[0]
    
    # Push vers Prometheus (ou mettre à jour dans backend)
    # ...
    
    time.sleep(300)  # 5 minutes
```

**Avantages:**
- Ne touche pas au backend
- Facile à debugger
- Peut être arrêté/relancé sans impact
- Logs séparés

---

## 📊 ÉTAT ACTUEL

### ✅ Ce qui fonctionne
- Backend: Opérationnel
- Collector v2.0: 97% économie API
- Alertes email: Configurées
- 6 services Docker: Actifs
- 144,042 cotes en DB

### ⚠️ Ce qui manque
- Métriques opportunités pas auto-refresh
- Alertes opportunités nécessitent métriques
- Dashboard Grafana pas à jour

---

## 🎯 PROCHAINE SESSION

1. **Option A: Script externe** (recommandé)
   - Créer metrics_updater.py
   - Tester en isolation
   - Ajouter au docker-compose
   
2. **Option B: Backend modif** (si vraiment nécessaire)
   - Créer environnement de test
   - Tester modifications localement
   - Puis déployer en prod

3. **Option C: Attendre vraies alertes**
   - Le système marche sans refresh auto
   - Attendre 24h pour test email opportunités
   - Voir si c'est vraiment critique

---

**Recommandation:** Option C puis A. Le système est stable, pas urgent.

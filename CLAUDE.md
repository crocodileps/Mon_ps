# Mon_PS - Instructions Claude Code

## 🎯 Projet
**Mon_PS** - Plateforme de trading quantitatif pour paris sportifs
- **Stack** : FastAPI + Next.js 14 + PostgreSQL/TimescaleDB
- **Infra** : Hetzner CCX23 + Docker Compose + Cloudflare Tunnel
- **Monitoring** : Grafana + Prometheus + Loki

## 🧠 Contexte actuel
- **Système en production** : V13 Multi-Strike (76.5% win rate, +53.2% ROI)
- **En développement** : Quantum ADN 2.0 (8 vecteurs analytiques par équipe)
- **Namespace DB** : `quantum` pour les nouvelles tables

## 📋 Fichiers de contexte importants
Avant de commencer, lis ces fichiers :
- `docs/CURRENT_TASK.md` - Tâche en cours et progression
- `docs/DECISIONS.md` - Décisions architecturales prises
- `docs/CHANGELOG.md` - Historique des modifications récentes

## 🔬 Méthodologie Mya
1. **Observer** → Analyser le problème complètement
2. **Analyser** → Comprendre les causes racines
3. **Diagnostiquer** → Identifier la meilleure solution
4. **Agir** → Implémenter avec précision

**Principe fondamental** : Qualité > Vitesse

## ⚙️ Stratégie de modèle
- **Par défaut** : Sonnet 4.5 (économie de quota)
- **Opus 4.5 uniquement pour** :
  - Architecture système complexe
  - Refactoring multi-fichiers critique
  - Décisions stratégiques majeures
  - Bugs impossibles à résoudre

## 🚫 Règles strictes
1. **Ne jamais modifier sans confirmation** sur les fichiers critiques
2. **Vérifier AVANT d'agir** - lire le code existant
3. **Un problème = un commit focalisé**
4. **Tester avant de valider** les changements
5. **Mettre à jour docs/CURRENT_TASK.md** après chaque tâche complétée

## 📁 Structure du projet
```
/home/Mon_ps/
├── backend/          # FastAPI (Python)
│   ├── app/
│   │   ├── routes/   # Endpoints API
│   │   ├── models/   # Modèles SQLAlchemy
│   │   └── services/ # Logique métier
├── frontend/         # Next.js 14 (TypeScript)
│   ├── components/
│   ├── pages/
│   └── hooks/
├── monitoring/       # Docker Compose Grafana/Prometheus
├── scripts/          # Scripts utilitaires
└── docs/             # Documentation et contexte
```

## 🔧 Commandes utiles
```bash
# Backend
cd /home/Mon_ps/backend && docker compose up -d

# Frontend
cd /home/Mon_ps/frontend && npm run dev

# Logs
docker logs mon_ps_backend -f

# Base de données
docker exec -it mon_ps_db psql -U postgres -d mon_ps
```

## 📞 En cas de problème
Si tu n'es pas sûr de quelque chose :
1. Demande clarification AVANT d'agir
2. Propose plusieurs options avec pros/cons
3. Attends validation explicite

## �� Notification fin de tâche
À la fin de chaque mission complète, toujours exécuter:
```bash
echo "🎉 MISSION TERMINÉE - Mya je t'attends!"; for i in 1 2 3; do echo -e '\a'; sleep 0.3; done
```

Cela permet à Mya d'être notifiée quand une tâche longue est terminée.

## �� Notification fin de tâche
À la fin de chaque mission complète, toujours exécuter:
```bash
touch /tmp/mission_done && echo "✅ Signal envoyé - Mya sera notifiée!"
```

## �� Notification sonore - OBLIGATOIRE
TOUJOURS exécuter cette commande AVANT d'attendre une réponse de Mya:
```bash
touch /tmp/mission_done && echo "🔔 Mya notifiée"
```

Cas où tu DOIS notifier:
- ✅ Fin d'une tâche ou étape
- ✅ Question posée à Mya  
- ✅ Proposition de pause
- ✅ Demande de validation
- ✅ Attente d'instruction
- ✅ Erreur nécessitant une décision

En résumé: À CHAQUE FOIS que tu t'arrêtes et attends Mya, notifie-la!

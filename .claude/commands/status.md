# STATUS PROJET MON_PS

## Instructions
Afficher l'etat actuel du projet et des taches.

## Actions requises:

1. **Lire CURRENT_TASK.md** si existe (`/home/Mon_ps/docs/CURRENT_TASK.md`)

2. **Lister sessions recentes** (3 dernieres dans `/home/Mon_ps/docs/sessions/`)

3. **Verifier etat donnees critiques:**
   - `/home/Mon_ps/data/quantum_v2/player_dna_unified.json` - date modif, nb joueurs
   - `/home/Mon_ps/data/fbref/` - derniere mise a jour
   - `/home/Mon_ps/data/understat/` - derniere mise a jour

4. **Verifier scripts cron actifs:**
   ```bash
   crontab -l | grep Mon_ps
   ```

5. **Resume format:**
```
=== STATUS MON_PS ===

TACHE EN COURS:
[Contenu CURRENT_TASK.md ou "Aucune"]

DERNIERES SESSIONS:
- [date] - [titre]
- [date] - [titre]

DONNEES:
- player_dna_unified: [nb joueurs] joueurs, MAJ [date]
- FBRef: MAJ [date]
- Understat: MAJ [date]

CRON ACTIFS:
- [description cron]
```

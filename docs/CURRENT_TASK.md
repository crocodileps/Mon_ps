# TACHE EN COURS - MON_PS

**Derniere MAJ:** 2025-12-12 12:12

## Contexte General
Projet Mon_PS: Systeme de betting football avec donnees multi-sources (FBRef, Understat, SofaScore).
Pipeline de donnees pour creer des profils joueurs unifies "hedge fund grade".

## Tache Actuelle
**Structure anti-perte contexte** - COMPLETE

### Ce qui a ete fait cette session:

1. **Scraping FBRef complet (curl_cffi)**
   - Script: `/home/Mon_ps/scripts/scrape_fbref_complete_2025_26.py`
   - 2,290 joueurs scrapes (5 ligues top)
   - Methode: curl_cffi avec impersonate="chrome110"

2. **Nettoyage donnees FBRef**
   - Script: `/home/Mon_ps/scripts/clean_fbref_data.py`
   - Mapping colonnes standardise

3. **Configuration CRON hebdomadaire**
   - Script: `/home/Mon_ps/scripts/cron_fbref_update.sh`
   - Execution: Mardi 6h
   - Backup compression au lieu de suppression

4. **Fusion FBRef -> Unified**
   - Script: `/home/Mon_ps/scripts/merge_fbref_to_unified.py`
   - Tracking data_completeness (partial/full)

5. **Enrichissement Understat**
   - Script: `/home/Mon_ps/scripts/enrich_partial_players_understat.py`
   - 109/110 joueurs partiels enrichis
   - 1 seul reste partial (Kevin Carlos)

## Fichiers Cles

### Scripts
- `/home/Mon_ps/scripts/scrape_fbref_complete_2025_26.py` - Scraper FBRef
- `/home/Mon_ps/scripts/clean_fbref_data.py` - Nettoyage donnees
- `/home/Mon_ps/scripts/merge_fbref_to_unified.py` - Fusion unified
- `/home/Mon_ps/scripts/enrich_partial_players_understat.py` - Enrichissement
- `/home/Mon_ps/scripts/cron_fbref_update.sh` - Wrapper CRON

### Donnees
- `/home/Mon_ps/data/quantum_v2/player_dna_unified.json` - Base unifiee
- `/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json` - FBRef nettoye
- `/home/Mon_ps/data/quantum_v2/players_impact_dna.json` - Understat existant

## Prochaines Etapes Possibles
- [ ] Ajouter SofaScore au pipeline
- [ ] Creer API pour acceder aux donnees
- [ ] Ameliorer matching joueurs (fuzzy search)
- [ ] Dashboard monitoring donnees

## Notes Techniques
- FBRef bloque requests standard -> utiliser curl_cffi
- Understat n'a pas d'API -> utiliser donnees existantes
- Browser impersonate: chrome110 fonctionne le mieux

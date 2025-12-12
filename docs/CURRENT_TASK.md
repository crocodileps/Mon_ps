# TACHE EN COURS - MON_PS

**Derniere MAJ:** 2025-12-12 15:10

## Contexte General
Projet Mon_PS: Systeme de betting football avec donnees multi-sources (FBRef, Understat, SofaScore).
Pipeline de donnees pour creer des profils joueurs unifies "hedge fund grade".

## Tache Actuelle
**Betting Profiles V2** - COMPLETE

### Ce qui a ete fait cette session:

1. **Defender Betting Profiles V2**
   - Script: `/home/Mon_ps/scripts/generate_defender_betting_profiles.py`
   - 1231 profils générés
   - Structure: CENTRAL/WIDE avec sous-rôles
   - Validation: 6/7 stars correctes

2. **Midfielder Betting Profiles V2**
   - Script: `/home/Mon_ps/scripts/generate_midfielder_betting_profiles.py`
   - 1610 profils générés
   - Ajout sous-rôles: ANCHOR/REGISTA, DESTROYER/CARRIER/WORKHORSE, CLASSIC_10/SHADOW_STRIKER/DEEP_LYING
   - Seuils adaptés DM modernes (Rodri, Rice)
   - Validation: 7/9 primary_role corrects

3. **Philosophie appliquée**
   > "Les données dictent le profil, pas la réputation"

## Fichiers Cles

### Scripts Betting Profiles
- `/home/Mon_ps/scripts/generate_defender_betting_profiles.py` - Défenseurs V2
- `/home/Mon_ps/scripts/generate_midfielder_betting_profiles.py` - Milieux V2
- `/home/Mon_ps/scripts/generate_attacker_betting_profiles.py` - Attaquants (à finaliser)

### Donnees Betting Profiles
- `/home/Mon_ps/data/quantum_v2/defender_betting_profiles.json` - 1231 défenseurs
- `/home/Mon_ps/data/quantum_v2/midfielder_betting_profiles.json` - 1610 milieux
- `/home/Mon_ps/data/quantum_v2/player_dna_unified.json` - Base unifiée source

### Scripts Pipeline FBRef
- `/home/Mon_ps/scripts/scrape_fbref_complete_2025_26.py` - Scraper FBRef
- `/home/Mon_ps/scripts/clean_fbref_data.py` - Nettoyage donnees
- `/home/Mon_ps/scripts/merge_fbref_to_unified.py` - Fusion unified
- `/home/Mon_ps/scripts/enrich_partial_players_understat.py` - Enrichissement

## Commits récents
```
740ad0a feat(midfielder): V2 Double classification (primary_role + sub_role)
db76c3b feat(betting): Defender Betting Profiles V2 - CENTRAL/WIDE Structure
```

## Prochaines Etapes Possibles
- [ ] Attacker Betting Profiles V2 (script existe, à enrichir)
- [ ] Goalkeeper Betting Profiles (goalkeeper_dna_v2.json existe)
- [ ] Intégration API backend FastAPI
- [ ] Dashboard frontend visualisation profils

## Notes Techniques

### Structure Defenders
```
CENTRAL → DOMINANT | BALL_PLAYING | STOPPER
WIDE → ATTACKING | BALANCED | DEFENSIVE | INVERTED
```

### Structure Midfielders
```
SENTINELLE → ANCHOR | REGISTA
BOX_TO_BOX → DESTROYER | CARRIER | WORKHORSE
MENEUR → CLASSIC_10 | SHADOW_STRIKER | DEEP_LYING
```

### Patterns position WIDE
```python
wide_indicators = ['RB', 'LB', 'R B', 'L B', 'D R', 'D L', 'WB', 'W B', 'FB']
attacking_defender_patterns = ['D F', 'F D', 'D F S', 'F D S']
```

### Scoring DM modernes
```python
defensive_actions = tackles + interceptions
if defensive_actions >= 2.3:
    sentinelle_score += 25
if ball_recoveries >= 5.5:
    sentinelle_score += 28
```

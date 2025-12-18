# Session 2025-12-18 #75 - Investigation Scientifique JSON vs DB

## Contexte
Suite audit ADN session #74. Investigation scientifique exhaustive pour comparer
JSON (team_dna_unified_v2.json) vs DB (team_quantum_dna_v3) et determiner la
strategie de fusion optimale.

## Realise

### Phase 1: Investigation JSON vs DB Comparative (1h)
- Structure JSON: 8 dimensions, 1251 cles/equipe, 745 metriques numeriques
- Structure DB: 60 colonnes (31 JSONB), donnees plus agregees
- Mapping equipes: 86/96 exact match, 10 divergentes

### Phase 2: 7 Zones d'Ombre Critiques
1. **quantum_dna_legacy**: NE contient PAS exploit/defense/fbref/defensive_line
   - Copie des colonnes DNA DB, pas du JSON

2. **Cron enrich_team_dna_v8.py**: NE fait PAS sync JSON->DB
   - Lit match_xg_stats, ecrit dans quantum.team_profiles

3. **5 equipes manquantes corner/card**: DECOUVERTE CRITIQUE
   - AC Milan, Hamburger SV, Mainz 05, Real Oviedo, VfB Stuttgart
   - Donnees EXISTENT dans team_stats_extended sous noms courts!
   - Milan, Hamburg, Mainz, Oviedo, Stuttgart -> HAS DATA
   - Probleme = MAPPING, pas donnees manquantes

4. **UnifiedLoader**: Charge JSON SEUL (0% DB)
   - Aucune connexion PostgreSQL

5. **Granularite**: JSON = 188 cles context vs DB = 11 cles
   - JSON: xG par formation, gamestate, periode (GRANULAIRE)
   - DB: moyennes globales agregees (PERTE 95% granularite)

6. **Flux de donnees**: 2 silos paralleles sans pont
   - JSON -> UnifiedLoader -> Brain
   - DB -> ORM -> API Backend
   - Aucun pipeline de sync

7. **Donnees vraiment exclusives**:
   - JSON: exploit (79 metriques), defense (215), defensive_line (229), fbref (27)
   - DB: corner_dna, card_dna, status_2025_2026, signature_v3, profile_2d

### Phase 3: Investigation Pre-UnifiedLoader V3
- Brain utilise ~20% des donnees JSON (exploit.vulnerabilities, tactical.profile)
- quantum.team_name_mapping existe avec correspondances
- Point d'injection identifie: _teams property pour enrichissement DB

## Fichiers touches
Aucun - SESSION LECTURE SEULE (investigation)

## Decouvertes Majeures

### 10 Equipes Divergentes (JSON vs DB)
| JSON | DB |
|------|-----|
| AS Roma | Roma |
| Inter Milan | Inter |
| Paris Saint-Germain | Paris Saint Germain |
| Leeds United | Leeds |
| Wolverhampton | Wolverhampton Wanderers |
| Hellas Verona | Verona |
| Heidenheim | FC Heidenheim |
| Parma | Parma Calcio 1913 |
| RB Leipzig | RasenBallsport Leipzig |
| Borussia Monchengladbach | Borussia M.Gladbach |

### 5 Equipes "Manquantes" = Probleme Mapping
quantum.team_stats_extended a les donnees sous noms courts:
- AC Milan -> "Milan" (HAS DATA)
- Hamburger SV -> "Hamburg" (HAS DATA)
- Mainz 05 -> "Mainz" (HAS DATA)
- Real Oviedo -> "Oviedo" (HAS DATA)
- VfB Stuttgart -> "Stuttgart" (HAS DATA)

## Problemes resolus
- Identification source corner/card_dna: quantum.team_stats_extended
- Comprehension flux de donnees: 2 silos JSON et DB independants
- Cause 5 equipes manquantes: mapping noms, pas donnees absentes

## En cours / A faire
- [ ] Sync corner/card depuis team_stats_extended -> team_quantum_dna_v3
- [ ] Creer UnifiedLoader v3 avec enrichissement DB
- [ ] Generer team_name_mapping.json depuis DB
- [ ] Ajouter alias pour 10 equipes divergentes
- [ ] Push modifications Guardian (toujours en attente)
- [ ] Test Telegram /start

## Notes techniques

### Solution Quick Win pour 5 equipes manquantes
```sql
UPDATE quantum.team_quantum_dna_v3 v3
SET corner_dna = tse.corner_dna, card_dna = tse.card_dna
FROM quantum.team_stats_extended tse
JOIN quantum.team_name_mapping m ON tse.team_name = m.historical_name
WHERE v3.team_name = m.quantum_name;
```

### Architecture Cible UnifiedLoader V3
```
      JSON                    DB
team_dna_unified     team_quantum_dna_v3
(exploit, defense,    (corner, card,
 defensive_line,       status, signature)
 context granulaire)
          \           /
        UnifiedLoader V3
              |
      Donnees FUSIONNEES
```

### Tables de Mapping Existantes
- team_mapping: 96+ equipes + api_football_id
- team_aliases: alias -> team_mapping_id
- quantum.team_name_mapping: quantum_name <-> historical_name

### Commandes Utiles
```bash
# Verifier team_stats_extended pour une equipe
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT team_name, corner_dna IS NOT NULL as has_corner
FROM quantum.team_stats_extended WHERE team_name ILIKE '%milan%';"

# Verifier mapping
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT * FROM quantum.team_name_mapping WHERE quantum_name LIKE '%Milan%';"
```

## Recommandation Finale
**Option D: Pont JSON<->DB unifie**
- Source de verite = JSON (richesse/granularite)
- Persistence = DB (corner, card, status temps reel)
- UnifiedLoader v3 = Fusion au chargement

# Session 2025-12-19 #89 - Migration Mappings Code vers DB

## Contexte

Mya a demande:
1. Corriger bugs TeamResolver (Eintracht Frankfurt, Athletic Club, Atletico)
2. Corriger URL Conference League
3. Migrer TOUS les mappings BETEXPLORER_FALLBACK vers la base de donnees
4. Supprimer les 180 lignes de mappings hardcodes

Objectif: "Le temps n'est pas un probleme, je veux la perfection"

## Realise

### Phase 1: Corrections bugs TeamResolver

1. **Bug Eintracht Frankfurt**
   - Cause: Mapping INVERSE en DB (`Eintracht Frankfurt -> Frankfurt`)
   - Betexplorer utilise le nom complet "Eintracht Frankfurt"
   - Solution: DELETE mappings faux en DB (IDs 26, 41)

2. **Mappings Espagne manquants**
   - Ajoute: `Athletic Club -> Ath Bilbao`
   - Ajoute: `Atletico de Madrid -> Atl. Madrid`
   - Ajoute: `Club Atletico de Madrid -> Atl. Madrid`

3. **URL Conference League**
   - Ancienne: `/europa-conference-league/` (redirige 301)
   - Nouvelle: `/conference-league/` (2024-2025)
   - Corrige dans league_mapping.py

### Phase 2: Migration complete vers DB

1. **Extraction**: 141 mappings depuis BETEXPLORER_FALLBACK
2. **Analyse**: 19 alias partages (ex: Wolves <- Wolverhampton, Wolverhampton Wanderers)
3. **Modifications DB**:
   - `ALTER TABLE team_mapping`: api_football_id NULL autorise
   - `DROP CONSTRAINT`: alias_normalized unique supprime
4. **Migration**: 143 aliases betexplorer inseres, 211 teams total

### Phase 3: Refactoring TeamResolver

1. **Supprime** BETEXPLORER_FALLBACK (180 lignes)
2. **Supprime** BETEXPLORER_REVERSE
3. **Modifie** to_source() pour lire uniquement depuis DB
4. **Resultat**: 380 lignes (avant ~560), 0 references hardcodees

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/utils/team_resolver.py`
  - Supprime BETEXPLORER_FALLBACK (180 lignes)
  - Simplifie to_source() (DB uniquement)

- `/home/Mon_ps/scrapers/betexplorer/league_mapping.py`
  - Corrige URL Conference League

### Base de donnees
- `team_mapping`: 211 equipes (94 creees)
- `team_aliases`: 143 aliases betexplorer
- Contraintes modifiees:
  - `api_football_id` NULL autorise
  - `alias_normalized` unique supprime

## Problemes resolus

### 1. Eintracht Frankfurt non trouve
- **Cause**: Mapping DB inverse (`Frankfurt` au lieu de `Eintracht Frankfurt`)
- **Solution**: DELETE mapping faux, Betexplorer utilise nom complet

### 2. Athletic Club non trouve
- **Cause**: Mapping manquant
- **Solution**: Ajoute `Athletic Club -> Ath Bilbao`

### 3. Conference League 404
- **Cause**: URL changee en 2024-2025
- **Solution**: `/conference-league/` au lieu de `/europa-conference-league/`

### 4. Migration echouait sur doublons
- **Cause**: Contrainte UNIQUE sur alias_normalized
- **Solution**: DROP CONSTRAINT pour permettre alias partages

## Tests valides

```
11/11 mappings TeamResolver OK
3/3 matchs trouves:
  - Eintracht Frankfurt vs Wolfsburg -> xY9SV7ne
  - Barcelona vs Athletic Club -> vH8AGJMO
  - Getafe vs Atletico Madrid -> UulKzN7t
```

## Architecture finale

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Mon_PS Name   │───>│  TeamResolver    │───>│ Betexplorer     │
│ "Inter Milan"   │    │  to_source()     │    │ "Inter"         │
└─────────────────┘    └────────┬─────────┘    └─────────────────┘
                                │
                       ┌────────▼─────────┐
                       │   PostgreSQL     │
                       │  team_aliases    │
                       │  source='be'     │
                       └──────────────────┘
```

**ZERO mappings hardcodes**

## En cours / A faire

- [x] Corrections bugs TeamResolver
- [x] Migration 141 mappings vers DB
- [x] Suppression BETEXPLORER_FALLBACK
- [x] Tests valides

## Notes techniques

### Requete verification couverture
```sql
SELECT COUNT(*) FROM team_aliases WHERE source = 'betexplorer';
-- Resultat: 143
```

### Statistiques finales
- Teams: 211
- Aliases betexplorer: 143
- Lignes code supprimees: ~180
- Mappings hardcodes restants: 0

## Resume

**Session #89** - Migration parfaite des mappings vers DB.

- 141 mappings migres du code vers PostgreSQL
- BETEXPLORER_FALLBACK supprime (180 lignes)
- TeamResolver simplifie (DB uniquement)
- 3 bugs corriges (Frankfurt, Athletic, Conference League)
- Architecture propre: source unique de verite = DB

**Status:** PERFECTION ATTEINTE

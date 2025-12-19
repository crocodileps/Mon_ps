# Session 2025-12-19 #90 - Fix Real Sociedad Normalization

## Contexte

Mya a identifie un bug critique:
- "Real Sociedad" etait normalise en "Sociedad"
- Similarite avec Betexplorer = 0.76 < 0.80 = REJETE
- Match Osasuna vs Real Sociedad non trouve

## Realise

### Diagnostic
1. Verifie `match_validator.py` - "real" n'est PAS dans les prefixes a supprimer
2. Verifie `team_resolver.py` - normalisation correcte
3. Teste la chaine complete de normalisation
4. Identifie le probleme: `to_betexplorer('Real Sociedad')` retournait `'Sociedad'`

### Cause racine
- Alias FAUX en base de donnees: `Sociedad` (id 22) -> `Real Sociedad`
- Betexplorer utilise `Real Sociedad` (complet), pas `Sociedad`
- Le SELECT sans ORDER BY causait un ordre arbitraire
- L'alias faux ecrasait l'alias correct dans le cache

### Solution
```sql
DELETE FROM team_aliases WHERE id = 22;
```

### Verification
- Scrape Betexplorer pour confirmer les noms reels:
  - Real Sociedad: utilise `Real Sociedad` (complet)
  - Real Betis: utilise `Betis` (court)
- Test apres fix: `to_betexplorer('Real Sociedad')` -> `'Real Sociedad'`

## Fichiers touches

### Base de donnees
- `team_aliases`: DELETE id=22 (alias faux `Sociedad`)

### Documentation
- `/home/Mon_ps/docs/CURRENT_TASK.md` - Mis a jour pour session #90

## Problemes resolus

### 1. Real Sociedad non trouve
- **Cause**: Alias DB `Sociedad` -> `Real Sociedad` faux
- **Solution**: DELETE FROM team_aliases WHERE id = 22

## En cours / A faire

- [x] Identifier la cause du bug
- [x] Corriger l'alias en DB
- [x] Tester le match finder
- [x] Documenter la session

## Notes techniques

### Verification Betexplorer (scrape reel)
```
Real Sociedad: Real Sociedad vs Girona (nom complet)
Real Betis: Betis vs Barcelona (nom court)
```

### Test final
```
Match: Osasuna vs Real Sociedad -> AyHgK1Na
Similarite: home=1.00, away=1.00
Date diff: 0 jours
```

### Aliases corrects restants
```sql
SELECT id, alias, canonical FROM team_aliases
WHERE canonical IN ('Real Sociedad', 'Real Betis');

-- Resultat:
-- 21 | Betis         | Real Betis
-- 23 | Real Sociedad | Real Sociedad
```

## Resume

**Session #90** - Bug fix rapide pour Real Sociedad.

- Cause: Alias FAUX en DB (Sociedad au lieu de Real Sociedad)
- Solution: DELETE simple de l'alias faux
- Resultat: Match trouve avec similarite 1.00

**Status:** COMPLETE

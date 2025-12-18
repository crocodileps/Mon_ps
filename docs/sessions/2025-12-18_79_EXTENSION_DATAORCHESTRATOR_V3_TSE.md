# Session 2025-12-18 #79 - Extension DataOrchestrator V3 + TSE

## Contexte
Suite session #78 (Cartographie Complete Mon_PS). Decisions Mya validees:
1. Etendre DataOrchestrator avec V3 + TSE
2. Corriger requetes SQL dangereuses (ILIKE → exact match)
3. Ajouter fallback ILIKE intelligent avec protection ambiguite

## Realise

### Phase 1: Extension DataOrchestrator (COMPLETE)
- Import `RealDictCursor` ajoute
- Methode `_get_team_from_v3()` ajoutee (59 colonnes de team_quantum_dna_v3)
- Methode `_get_tse_name()` ajoutee (mapping 5 equipes speciales)
- Methode `_get_tse_data()` ajoutee (corner/card/goalscorer DNA de TSE)
- `get_team_dna()` modifiee: cascade TSE → V3 → JSON → profiles(fallback)

### Phase 2: Corrections Securite SQL (COMPLETE)
- 4 methodes corrigees: ILIKE %s → LOWER(team_name) = LOWER(%s)
- Protection contre faux positifs (Real → 5 matchs, United → 2 matchs)

### Phase 3: Fallback ILIKE Intelligent (COMPLETE)
- Ajout fallback ILIKE apres exact match dans 3 methodes
- Logique: si 1 resultat = safe, si >1 = ambiguite protegee
- Mapping alias ajoute: PSG, Barca, Bayern, Dortmund, BVB, Juve, Atleti

### Resultats Tests
- 15/15 equipes trouvees (avant: 14/15 - PSG manquant)
- 100% TSE et V3 pour toutes equipes
- Ambiguites protegees (Real, United → non trouves)
- Exact match fonctionne (Real Madrid → trouve)

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum_core/data/orchestrator.py` - Extension majeure (+220 lignes)
  - Lignes 37: Import RealDictCursor
  - Lignes 254-385: get_team_dna() reecrite (cascade 4 sources)
  - Lignes 529-585: _get_team_from_postgresql() + fallback
  - Lignes 616-681: _get_team_from_v3() + fallback
  - Lignes 683-711: _get_tse_name()
  - Lignes 713-768: _get_tse_data() + fallback
  - Lignes 795-811: Mapping alias (PSG, Barca, etc.)

### Backups
- `/home/Mon_ps/quantum_core/data/orchestrator.py.backup_20251218_223457`

### Git
- Commit f7c3716: "feat(orchestrator): Extend DataOrchestrator with V3 + TSE sources"
- Nouvelles modifications non commitees (fallback + alias)

## Problemes resolus

1. **Paradoxe DataHub vs DataOrchestrator** → RESOLU
   - DataOrchestrator charge maintenant TSE + V3 (comme data_hub.py)
   - UnifiedBrain a acces a corner/card DNA

2. **Requetes SQL dangereuses** → CORRIGE
   - ILIKE %name% matchait plusieurs equipes
   - Corrige avec LOWER() = LOWER() exact match

3. **PSG non trouve** → CORRIGE
   - Probleme: "PSG" ne matche pas "Paris Saint Germain"
   - Solution: Mapping alias dans _normalize_team_name()

4. **Ambiguites (Real, United)** → PROTEGE
   - Fallback ILIKE intelligent: retourne None si >1 match

## En cours / A faire

- [ ] Commit modifications fallback + alias
- [ ] Push vers origin/main
- [ ] (Optionnel) Supprimer dna_loader_db.py (0 utilisateurs)
- [ ] (Optionnel) Ajouter Ipswich/Leicester/Southampton a V3

## Notes techniques

### Architecture get_team_dna() finale
```
Cascade de sources:
1. Cache local
2. TSE (team_stats_extended) - corner/card/goalscorer/timing/handicap/scorer DNA
3. V3 (team_quantum_dna_v3) - status/signature/profile_2d/exploit/clutch/luck/roi/clv
4. JSON (UnifiedLoader) - donnees granulaires
5. team_profiles (fallback legacy si V3 absent)
```

### Mapping alias ajoutes
```python
"PSG": "Paris Saint Germain",
"Barca": "Barcelona",
"Bayern": "Bayern Munich",
"Dortmund": "Borussia Dortmund",
"BVB": "Borussia Dortmund",
"Juve": "Juventus",
"Atleti": "Atletico Madrid",
```

### Mapping TSE (existant)
```
AC Milan → Milan
VfB Stuttgart → Stuttgart
Mainz 05 → Mainz
Hamburger SV → Hamburg
Real Oviedo → Oviedo
```

### Statistiques fichier
- orchestrator.py: ~870 lignes (avant: 695)
- +175 lignes nettes

### Commandes utiles
```bash
# Tester PSG
python3 -c "
import sys; sys.path.insert(0, '/home/Mon_ps')
from quantum_core.data.orchestrator import DataOrchestrator
d = DataOrchestrator().get_team_dna('PSG')
print('PSG:', d.get('team_name') if d else 'NON TROUVE')
print('Sources:', d.get('_sources') if d else 'N/A')
"

# Verifier couverture
python3 -c "
import sys; sys.path.insert(0, '/home/Mon_ps')
from quantum_core.data.orchestrator import DataOrchestrator
orch = DataOrchestrator()
for team in ['Arsenal', 'PSG', 'Real Madrid', 'AC Milan']:
    d = orch.get_team_dna(team)
    print(f'{team}: {len(d.get(\"_sources\", [])) if d else 0} sources')
"
```

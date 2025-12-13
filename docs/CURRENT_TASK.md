# TACHE EN COURS - MON_PS

**Derniere MAJ:** 2025-12-13 Session #08
**Statut:** DataManager V2.6 COMPLET - Coach/GK/Attackers integres

## Contexte General
Projet Mon_PS: Systeme de betting football avec donnees multi-sources (FBRef, Understat, SofaScore).
Paradigme Chess Engine: ADN unique par equipe + Friction entre 2 ADN = marches exploitables.

## Session #08 - DataManager V2.6 COMPLET

### Accomplissement Majeur
**DataManager V2.6 avec integration Coach, Goalkeeper et Attackers DNA**

Architecture Hybrid Cascade:
```
PostgreSQL quantum.team_profiles (99 equipes)
    ↓ fallback
JSON DNA Files (96 equipes)
    ↓ fallback
Intelligent Imputation (league averages)
```

### Nouvelles Fonctionnalites V2.6

#### Coach Integration
- Source: PostgreSQL `coach_intelligence` via `coach_team_mapping`
- CoachData dataclass avec style tactique
- Exemples: Pep Guardiola, Arne Slot

#### Goalkeeper Integration
- Source: JSON `goalkeeper_dna_v4_4_final.json`
- GoalkeeperData dataclass avec save_rate, status
- 96 gardiens avec profils complets
- Status: ELITE, SOLID, AVERAGE, LEAKY

#### Attackers/MVP Integration
- Source: JSON `attacker_dna_v2.json`
- Top scorers par equipe avec goals et xG
- MVP identification avec dependency score
- 1199 joueurs indexes

### TeamData V2.6 Enrichi
```python
@dataclass
class TeamData:
    # Core
    name: str
    canonical_name: str
    xg_for: float
    xg_against: float

    # V2.6 Coach
    coach_name: str
    coach_style: str  # possession, counter, balanced

    # V2.6 Goalkeeper
    goalkeeper_name: str
    gk_save_rate: float
    gk_status: str  # ELITE, SOLID, AVERAGE, LEAKY

    # V2.6 MVP/Attackers
    mvp_name: str
    mvp_goals: int
    mvp_dependency: float
    top_scorers: List[Dict]
```

### Test Results
```
Liverpool:
  xG For: 2.45, xG Against: 1.44
  Coach: Arne Slot
  GK: Alisson Becker (LEAKY)
  Sources: 10, Quality: 1.00

Manchester City:
  Coach: Pep Guardiola
  GK: Ederson
  MVP: Erling Haaland
```

---

## Probleme Identifie
- `attacker_dna_v2.json` a des erreurs d'assignation d'equipe
  - Hugo Ekitike liste sous Liverpool (devrait etre Eintracht Frankfurt)
  - Alexander Isak liste sous Liverpool (devrait etre Newcastle)
- A nettoyer dans une prochaine session

---

## Fichiers Modifies Session #08
```
quantum_core/data/
├── manager.py              # DataManager V2.6 COMPLET (~740 lignes)
├── manager_v25_backup.py   # Backup V2.5
└── manager_v1_backup.py    # Backup V1 original
```

---

## Prochaines Etapes

### Priorite Haute
1. [ ] Nettoyer attacker_dna_v2.json (erreurs team assignment)
2. [ ] Ajouter predicteur Scorers (buteurs)
3. [ ] Ajouter predicteur Cards (cartons)
4. [ ] Creer API FastAPI pour exposer le systeme

### Priorite Moyenne
5. [ ] Backtest sur donnees historiques
6. [ ] Integrer Coach DNA dans friction matrix
7. [ ] Utiliser GK status pour Clean Sheet predictions

---

## Usage Quantum Core

```python
from quantum_core.engine import QuantumEngine

engine = QuantumEngine()

# Prediction simple
pred = engine.predict("Liverpool", "Man City", "over_25", odds=1.85)
print(f"Prob: {pred.probability*100:.1f}%")
print(f"Edge: {pred.edge_percentage:.1f}%")
print(f"Recommendation: {pred.recommendation}")

# Analyse complete
analysis = engine.analyze_match("Liverpool", "Man City", {
    "over_25": 1.85,
    "btts_yes": 1.70
})
print(analysis.summary)
```

---

## Donnees Chargees V2.6
- team_dna: 96 equipes
- narrative_dna: 96 equipes
- referee_dna: 61 arbitres
- scorer_profiles: 238 buteurs
- attacker_dna: 1199 joueurs
- goalkeeper_dna: 96 gardiens
- coach_intelligence: via PostgreSQL
- team_name_mapping: 29 mappings

---

## Connexion PostgreSQL
```bash
docker exec monps_postgres psql -U monps_user -d monps_db
```

---

## Commits Recents
```
Session #07: 8b57db0 feat(quantum_core): MVP Quant Grade - Dixon-Coles + Remove Vig + Kelly
Session #08: [pending] feat(quantum_core): DataManager V2.6 - Coach/GK/Attackers integration
```

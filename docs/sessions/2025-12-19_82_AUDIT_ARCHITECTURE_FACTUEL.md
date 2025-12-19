# Session 2025-12-19 #82 - Audit Architecture Factuel

## Contexte
Suite session #81 (Data Flow TSE Fix). Mission: Audit exhaustif et factuel de l'architecture sans suppositions.

## Realise

### Audit quantum_orchestrator_v1 - Usage
- Verifie imports: AUCUN fichier n'importe quantum_orchestrator_v1
- API expose uniquement UnifiedBrain (pas quantum_orchestrator)
- Aucun cron ne lance quantum_orchestrator_v1
- Dernier commit: 2025-12-08 (f9021fb - V7.2 fix)

### Audit Factuel Composants
```
1. QUANTUM ORCHESTRATOR V1
   Taille: 82K + 43K (production) + 19K (SQL)
   Classes: 28 dataclasses DNA
   DNA Vectors: 11 (Market, Context, Risk, Temporal, Nemesis,
                   Psyche, Sentiment, Roster, Physical, Luck, Chameleon)

2. AGENTS DEFENSE V2
   Fichiers: agent.py (11K), config.py (11K), team_profiler.py (24K)
   Dernier commit: 2025-12-09

3. AGENTS ATTACK V1
   Fichiers: team_profiler.py (20K)
   Dernier commit: 2025-12-11

4. RULE ENGINE
   Taille: 36K
   Classes: QuantumRuleEngine, MonteCarloConfig, EngineConfig
   Dernier commit: 2025-12-07

5. SCENARIO DETECTOR
   Taille: 25K
   20 scenarios avec cascade detection
   Dernier commit: 2025-12-08

6. FRICTION
   friction_matrix_12x12.py (52K)
   friction_context.py (22K)
```

### Historique Git
- 103 tags (v1.0 le 09/11 -> v7.3 le 11/12)
- 55 branches locales, 121 remote
- quantum-core-mvp-v1.0 cree le 13/12

### Verification dna_loader_db.py
```
Fichier supprime: quantum/services/dna_loader_db.py
Backup existe: dna_loader_db.py.backup_OBSOLETE (17K)
Commit suppression: a72630f

Ce que faisait dna_loader_db.py:
- Chargeait depuis quantum.team_profiles (99 rows)
- Chargeait depuis quantum.matchup_friction (3403 rows)
- Classes: SimpleTeamDNA, SimpleFriction, DNALoaderDB

DataOrchestrator utilise maintenant:
- quantum.team_profiles (fallback)
- quantum.matchup_friction
- quantum.team_quantum_dna_v3 (96 equipes, 23 vectors)
- quantum.team_stats_extended (corner/card/goalscorer DNA)
```

### Architecture - Graphe Dependances
```
quantum_orchestrator_v1.py
└── AUCUNE dependance quantum interne (AUTONOME, 82K lignes)

rule_engine.py
├── dna_loader.py
├── feature_calculator.py
├── scenario_detector.py
├── monte_carlo.py
└── quantum.models

scenario_detector.py
└── quantum.models (ScenarioID, etc.)

agents/defense_v2/
├── data/loader.py
├── features/engineer.py
└── models/trainer.py

agents/attack_v1/
├── data/loader.py
└── features/engineer.py

UnifiedBrain (ACTIF - utilise par API)
└── DataHubAdapter
    └── DataOrchestrator
        ├── quantum.team_quantum_dna_v3
        ├── quantum.team_stats_extended
        ├── quantum.team_profiles
        └── JSON files
```

### Observation Cle
quantum_orchestrator_v1 et rule_engine font des choses SIMILAIRES:
- Tous deux: 6 modeles / ensemble / scenarios / Monte Carlo
- Mais: quantum_orchestrator_v1 est AUTONOME (pas d'imports internes)
- Et: rule_engine IMPORTE dna_loader, scenario_detector, etc.
- Deux architectures paralleles, pas imbriquees

## Fichiers touches

### Lus (non modifies)
- `/home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1.py` - Header + imports
- `/home/Mon_ps/quantum/services/rule_engine.py` - Header + imports
- `/home/Mon_ps/quantum/services/scenario_detector.py` - Header + imports
- `/home/Mon_ps/agents/defense_v2/agent.py` - Header
- `/home/Mon_ps/agents/attack_v1/team_profiler.py` - Header
- `/home/Mon_ps/quantum/services/dna_loader_db.py.backup_OBSOLETE` - Contenu complet

### Crees
- `/home/Mon_ps/docs/sessions/2025-12-19_82_AUDIT_ARCHITECTURE_FACTUEL.md`

## Problemes resolus

Aucun probleme a resoudre - session d'audit factuel uniquement.

## En cours / A faire

- [x] Audit quantum_orchestrator_v1 usage
- [x] Audit factuel composants
- [x] Historique Git (tags, branches, commits)
- [x] Verification dna_loader_db.py
- [x] Graphe dependances architecture
- [ ] (A decider) Que faire des composants non utilises?

## Notes techniques

### Tables DB actives
```
quantum.team_quantum_dna_v3 (96 equipes, 59 colonnes, 23 vectors)
quantum.team_stats_extended (TSE - corner/card DNA)
quantum.team_profiles (99 equipes, 11 vectors - fallback)
quantum.matchup_friction (3403 frictions)
quantum.team_name_mapping (aliases)
33 tables au total dans schema quantum
```

### JSON actifs
```
/home/Mon_ps/data/quantum_v2/ (113MB)
- player_dna_unified.json (44M)
- team_dna_unified_v2.json (5.7M)
- referee_dna_unified.json (524K)
```

### Architecture Active Confirmee
```
API → UnifiedBrain → DataHubAdapter → DataOrchestrator
                                       ├── TSE (corner/card)
                                       ├── V3 (23 vectors)
                                       └── JSON (fallback)
```

### Composants Non Appeles par Code Actif
```
- quantum/orchestrator/quantum_orchestrator_v1.py
- quantum/services/rule_engine.py
- quantum/services/scenario_detector.py
- agents/defense_v2/
- agents/attack_v1/
```
Ces composants existent mais ne sont pas importes par le flux actif (API → UnifiedBrain).

# MISSION : COMPRENDRE PYDANTIC V2 EN PROFONDEUR

## Objectif
Pas juste "lire la doc" - COMPRENDRE les changements architecturaux fondamentaux
entre Pydantic V1 et V2, et leurs implications pour notre système.

## Questions à répondre

### 1. Architecture Core
- [ ] Pourquoi Pydantic V2 a été réécrit en Rust (pydantic-core) ?
- [ ] Quel impact performance vs V1 ? (benchmarks concrets)
- [ ] Quels sont les breaking changes CONCEPTUELS (pas juste syntaxe) ?

### 2. Validators
- [ ] Différence field_validator vs model_validator (timing d'exécution) ?
- [ ] Pourquoi mode='before' vs mode='after' ? (ordre d'exécution)
- [ ] Quand info.data est-il complet vs incomplet ?
- [ ] Performance : combien de µs par validator type ?

### 3. Serialization
- [ ] Pourquoi json_encoders deprecated ?
- [ ] Différence field_serializer vs model_serializer ?
- [ ] when_used='json' vs 'always' vs 'json-unless-none' ?
- [ ] Impact FastAPI : quelle méthode utilise-t-il ?

### 4. Configuration
- [ ] Pourquoi class Config → ConfigDict ?
- [ ] Quelles options disponibles en V2 ?
- [ ] Différence avec V1 ?

### 5. Default Values & Optional
- [ ] Différence default= vs default_factory= ?
- [ ] Quand default_factory callable est-elle appelée ?
- [ ] Optional[T] vs T | None : différence pratique ?
- [ ] Impact sur validators ?

## Méthode de recherche
1. Lire documentation officielle Pydantic V2
2. Lire migration guide V1→V2 complet
3. Analyser benchmarks de performance
4. Tester comportements edge cases
5. Documenter chaque découverte

## Livrable
- COMPREHENSION.md : Document synthétisant toute la compréhension
- BENCHMARKS.md : Résultats de tests de performance
- EDGE_CASES.md : Comportements non-évidents découverts

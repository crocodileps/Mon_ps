# ADR #005 - Dependency Injection & Application Lifecycle Management

## Status
**ACCEPTED** - Session #23.5A (Dec 14, 2025)

## Context

### Problèmes identifiés Session #23
Session #23 a révélé 3 problèmes critiques liés au lifecycle management:

1. **Service instantiation**: Nouvelle instance PredictionService par requête
   - Conséquence: Agents ML rechargés 1000×/s → OOM crash < 5 min
   - Impact: 🔴 CRITIQUE - Production killer

2. **Timezone naive**: datetime.utcnow() deprecated + DST bugs
   - Conséquence: Comparaisons naive vs aware → TypeError
   - Impact: 🔴 CRITIQUE - Bugs DST garantis 2×/an

3. **Timestamp écrasé**: generated_at écrase computed_at original
   - Conséquence: Audit trail corrompu (perte timestamp ML)
   - Impact: 🔴 CRITIQUE - Compliance violation

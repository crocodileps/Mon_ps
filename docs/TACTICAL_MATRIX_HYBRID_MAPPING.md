# Tactical Matrix - Mapping Hybride Intelligent

## Sources de Données

| Source | Données | Priorité |
|--------|---------|----------|
| coach_intelligence.tactical_style | Philosophie du coach | 1 |
| Knowledge Base | Overrides manuels experts | 2 |
| team_intelligence.current_style | Stats buts marqués/encaissés | 3 |
| Fallback par ligue | Culture tactique régionale | 4 |

## Mapping coach_intelligence → playing_style

| tactical_style (coach) | playing_style (team) |
|------------------------|----------------------|
| dominant_offensive | high_press |
| attacking_vulnerable | attacking |
| offensive | pressing |
| balanced | balanced |
| defensive | low_block_counter |
| defensive_weak | park_the_bus |
| struggling | defensive |

## Knowledge Base Overrides

| Équipe | Style | Raison |
|--------|-------|--------|
| Barcelona | tiki_taka | ADN du club |
| Bayer Leverkusen | gegenpressing | Xabi Alonso |
| RB Leipzig | gegenpressing | Red Bull DNA |
| Atletico Madrid | defensive | Simeone ADN |
| Inter Milan | low_block_counter | Inzaghi |
| Brighton | possession | Style anglais moderne |
| Getafe | park_the_bus | Anti-football assumé |
| Burnley/Stoke | direct_play | Style traditionnel |

## Fallback par Ligue

| Ligue | Style par défaut | Raison |
|-------|-----------------|--------|
| Bundesliga | pressing | Culture allemande |
| Serie A | defensive | Culture italienne |
| La Liga | possession | Culture espagnole |

## Distribution Finale

- 12 styles différents utilisés
- 231 équipes avec style assigné
- 0 équipes sans style

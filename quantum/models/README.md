# 🧬 QUANTUM MODELS - Documentation

## Vue d'ensemble

Ce package contient tous les modèles de données pour l'**Agent Quantum V1** du système Mon_PS Trading.

**11 vecteurs DNA** conformes à la Phase 1 Quantum (99/99 équipes).

```
quantum/models/
├── __init__.py              # Exports et imports
├── dna_vectors.py           # Les 11 vecteurs DNA
├── friction_context.py      # Friction, Context, Indices
├── scenarios_strategy.py    # Scénarios et Output
└── scenarios_definitions.py # 20 scénarios définis
```

---

## 📊 Architecture des Données

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                           TEAM DNA (11 VECTEURS)                                      ║
║                                                                                       ║
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    ║
║  │ Context DNA │ │Current Seas.│ │ Psyche DNA  │ │ Nemesis DNA │ │Temporal DNA │    ║
║  │  xG 2024    │ │ xG 2025/26  │ │ killer_inst │ │ verticality │ │diesel_factor│    ║
║  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    ║
║                                                                                       ║
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    ║
║  │ Roster DNA  │ │Physical DNA │ │ Market DNA  │ │  Luck DNA   │ │Chameleon DNA│    ║
║  │ mvp_depend  │ │ pressing    │ │ profile     │ │ xpoints_d   │ │ comeback    │    ║
║  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🧬 Les 11 Vecteurs DNA (Phase 1 Quantum)

### 1. Market DNA (+20% ROI)
Le marché le plus rentable pour cette équipe spécifique.

```python
from quantum.models import MarketDNA, MarketPerformance

market_dna = MarketDNA(
    best_strategy="CONVERGENCE_OVER_MC",
    best_strategy_roi=84.6,
    best_strategy_wr=92.3,
    best_strategy_n=13,
    best_strategy_edge=5.2,
    best_strategy_profit=15.8,
    best_markets=["over_25_home", "btts_yes_away"],
    blacklisted_markets=["draw", "under_15"]
)
```

### 2. Context DNA (+12% ROI)
Performance selon le contexte (domicile, extérieur, favori, outsider).

```python
from quantum.models import ContextDNA, LocationPerformance

context_dna = ContextDNA(
    home=LocationPerformance(
        strength_index=78,
        transformation_factor=1.56,
        win_rate=0.72
    ),
    away=LocationPerformance(
        strength_index=52,
        win_rate=0.38
    ),
    home_beast=True,
    home_away_differential=26
)
```

### 3. Risk DNA (+5% ROI, CRITIQUE pour money management)
Quantifie l'imprévisibilité et ajuste les mises.

```python
from quantum.models import RiskDNA, VarianceMetrics

risk_dna = RiskDNA(
    variance=VarianceMetrics(
        overall_variance=0.65,
        offensive_variance=0.72
    ),
    stake_modifier=0.85,
    max_stake_tier="TIER_2",
    kelly_fraction=0.15
)
```

### 4. Temporal DNA (+25% ROI) ⭐ DIFFÉRENCIANT
Patterns de scoring par tranche de 15 minutes.

```python
from quantum.models import TemporalDNA, ScoringPeriod

temporal_dna = TemporalDNA(
    diesel_factor=0.75,  # Finit fort
    sprinter_factor=0.25,  # Commence lentement
    clutch_factor=0.82,  # Performant dans les moments critiques
    best_scoring_period=ScoringPeriod.LATE,  # 75-90'
    late_game_killer=True
)
```

### 5. Nemesis DNA (+35% ROI) ⭐⭐ GAME CHANGER
Faiblesses structurelles exploitables.

```python
from quantum.models import NemesisDNA, TacticalWeakness, PlayingStyle

nemesis_dna = NemesisDNA(
    style_primary=PlayingStyle.COUNTER_ATTACK,
    weaknesses=[
        TacticalWeakness(
            weakness_type="vs_high_press",
            vulnerability=0.75,
            markets_affected=["opponent_goals_over_0.5", "btts_yes"]
        )
    ]
)
```

### 6. Psyche DNA (+15% ROI)
Profil psychologique et réaction à l'adversité.

```python
from quantum.models import PsycheDNA, Mentality, KillerInstinct

psyche_dna = PsycheDNA(
    mentality=Mentality.CONSERVATIVE,  # +11.73u/équipe!
    killer_instinct=KillerInstinct.LOW,  # LOW > HIGH (contre-intuitif!)
    resilience_index=72,
    collapse_rate=0.15
)
```

### 7. Sentiment DNA (+8% ROI)
Biais de marché - équipe sur/sous-cotée.

```python
from quantum.models import SentimentDNA, CLVTrackRecord

sentiment_dna = SentimentDNA(
    public_team=True,
    brand_premium=0.08,
    clv=CLVTrackRecord(
        avg_clv=2.15,
        positive_clv_rate=0.58
    )
)
```

### 8. Roster DNA (+10% ROI)
Composition et dépendances de l'équipe.

```python
from quantum.models import RosterDNA, KeeperStatus

roster_dna = RosterDNA(
    mvp_dependency=0.35,
    bench_impact=6.2,  # Score 0-10
    keeper_status=KeeperStatus.LEAKY  # = Value par régression!
)
```

### 9. Physical DNA (+12% ROI)
Profil physique et endurance.

```python
from quantum.models import PhysicalDNA

physical_dna = PhysicalDNA(
    pressing_decay=0.25,  # 25% de déclin du pressing
    late_game_threat="HIGH",
    intensity_60_plus=0.7  # 70% d'intensité après 60'
)
```

### 10. Luck DNA (+8% ROI) ✨ NOUVEAU
Facteur chance pour anticiper la régression à la moyenne.

```python
from quantum.models import LuckDNA

luck_dna = LuckDNA(
    xpoints=42.5,
    actual_points=38,
    xpoints_delta=4.5,  # Malchanceux = value!
    luck_profile="UNLUCKY",
    luck_index=35,
    xg_overperformance=-0.3,
    xga_overperformance=0.2,
    big_chances_conversion=0.45,
    big_chances_faced_conversion=0.55,
    expected_conversion=0.50,
    conversion_luck=-0.05,
    regression_direction="UP",  # Régression positive attendue
    regression_magnitude=65,
    clean_sheet_luck=-2.1
)

# Exploiter la malchance
if luck_dna.is_due_for_regression_up:
    print("Value: équipe malchanceuse, régression positive à venir!")
```

### 11. Chameleon DNA (+10% ROI) ✨ NOUVEAU
Capacité d'adaptation tactique et mentale.

```python
from quantum.models import ChameleonDNA

chameleon_dna = ChameleonDNA(
    adaptability_index=75,
    chameleon_score=80,
    comeback_ability=72,
    points_from_losing_positions=8,
    comeback_rate=0.35,
    tactical_flexibility=78,
    formations_used=4,
    primary_formation="4-3-3",
    vs_stronger_adaptation=70,
    vs_weaker_adaptation=85,
    style_when_leading="CONTROL",
    style_when_trailing="ATTACK",
    style_when_drawing="BALANCED",
    halftime_adjustment_success=68,
    second_half_improvement=0.15,
    anti_pressing_ability=72,
    anti_counter_ability=65,
    anti_low_block_ability=55
)

# Équipe vraiment adaptable
if chameleon_dna.is_true_chameleon:
    print("Équipe caméléon: peut changer de plan selon l'adversaire")
```

---

## ⚡ Friction Matrix

La collision de deux ADN génère une **Friction Matrix**.

```python
from quantum.models import FrictionMatrix, KineticFriction

friction = FrictionMatrix(
    home_team="Barcelona",
    away_team="Athletic",
    kinetic=KineticFriction(
        home_to_away=48,  # Dommage Barcelona → Athletic
        away_to_home=42,  # Dommage Athletic → Barcelona
        triggers=["PRESSING_DEATH", "PACE_EXPLOITATION"]
    ),
    chaos_potential=72,
    predicted_clash_type=ClashType.OPEN_GAME
)
```

### 4 Types de Friction

| Type | Description | Impact |
|------|-------------|--------|
| **Kinetic** | Dommage tactique A→B | Buts attendus |
| **Temporal** | Avantage timing | Quand les buts tombent |
| **Psyche** | Dominance mentale | Qui craque |
| **Physical** | Endurance | Qui s'effondre |

---

## 🎯 Les 20 Scénarios

### Groupe A: Tactiques (5)
| ID | Emoji | Nom | Description |
|----|-------|-----|-------------|
| `TOTAL_CHAOS` | 🌪️ | Total Chaos | Festival de buts |
| `THE_SIEGE` | 🏰 | The Siege | Domination stérile |
| `SNIPER_DUEL` | 🔫 | Sniper Duel | Létalité maximale |
| `ATTRITION_WAR` | 💤 | Attrition War | Guerre d'usure |
| `GLASS_CANNON` | 🃏 | Glass Cannon | Canon de verre |

### Groupe B: Temporels (4)
| ID | Emoji | Nom | Description |
|----|-------|-----|-------------|
| `LATE_PUNISHMENT` | ⏰ | Late Punishment | Punition tardive |
| `EXPLOSIVE_START` | 🚀 | Explosive Start | Départ fulgurant |
| `DIESEL_DUEL` | 🐢 | Diesel Duel | Deux diesels |
| `CLUTCH_KILLER` | ⚡ | Clutch Killer | Tueur fin de match |

### Groupe C: Physiques (4)
| ID | Emoji | Nom | Description |
|----|-------|-----|-------------|
| `FATIGUE_COLLAPSE` | 😰 | Fatigue Collapse | Effondrement physique |
| `PRESSING_DEATH` | 💪 | Pressing Death | Mort par pressing |
| `PACE_EXPLOITATION` | 🏃 | Pace Exploitation | Exploitation vitesse |
| `BENCH_WARFARE` | 🪑 | Bench Warfare | Guerre des bancs |

### Groupe D: Psychologiques (4)
| ID | Emoji | Nom | Description |
|----|-------|-----|-------------|
| `CONSERVATIVE_WALL` | 🧊 | Conservative Wall | Mur conservateur |
| `KILLER_INSTINCT` | 🔥 | Killer Instinct | Instinct de tueur |
| `COLLAPSE_ALERT` | 😱 | Collapse Alert | Alerte effondrement |
| `NOTHING_TO_LOSE` | 💎 | Nothing to Lose | Rien à perdre |

### Groupe E: Nemesis (3)
| ID | Emoji | Nom | Description |
|----|-------|-----|-------------|
| `NEMESIS_TRAP` | 🎯 | Nemesis Trap | Piège Némésis |
| `PREY_HUNT` | 🦅 | Prey Hunt | Chasse à la proie |
| `AERIAL_RAID` | ✈️ | Aerial Raid | Raid aérien |

---

## 📤 Output: QuantumStrategy

```python
from quantum.models import QuantumStrategy, MarketRecommendation

strategy = QuantumStrategy(
    home_team="Lyon",
    away_team="Marseille",
    detected_scenarios=[...],
    primary_scenario=ScenarioID.TOTAL_CHAOS,
    recommendations=[
        MarketRecommendation(
            market=MarketType.OVER_35,
            selection="Over 3.5 Goals",
            calculated_probability=0.52,
            odds=2.45,
            edge=0.112,  # 11.2%
            confidence=72,
            stake_tier=StakeTier.NORMAL,
            stake_units=2.0,
            reasoning="TOTAL_CHAOS: pace_combined=148, xG_combined=3.8"
        )
    ],
    avoid_markets=["Under 2.5", "Draw"],
    total_exposure=3.5,
    total_expected_value=0.42
)

# Affichage
print(strategy.to_summary())
```

---

## 🔧 Utilisation

### Import rapide
```python
from quantum.models import (
    TeamDNA,
    FrictionMatrix,
    MatchContext,
    ScenarioID,
    QuantumStrategy,
    MarketRecommendation,
)
```

### Import complet
```python
from quantum.models import *
```

### Récupérer les scénarios
```python
from quantum.models.scenarios_definitions import (
    get_scenario,
    get_scenarios_by_category,
    get_all_scenarios,
    SCENARIOS_CATALOG
)

# Un scénario spécifique
total_chaos = get_scenario(ScenarioID.TOTAL_CHAOS)

# Par catégorie
tactical_scenarios = get_scenarios_by_category(ScenarioCategory.TACTICAL)
```

---

## 📊 Insights Découverts (Encodés dans les modèles)

| Découverte | Impact | Encodé dans |
|------------|--------|-------------|
| CONSERVATIVE mentality = +11.73u | +15% | `PsycheDNA.mentality` |
| LOW killer_instinct > HIGH | Contre-intuitif | `PsycheDNA.killer_instinct` |
| LEAKY keeper = Value | Régression | `RosterDNA.keeper_status` |
| 4-3-3 formation = +8.08u | Meilleure | `NemesisDNA.formation_typical` |
| diesel_factor > 0.65 = Late goals | +18% ROI | `TemporalDNA.diesel_factor` |

---

## 🚀 Prochaines étapes

1. **Services**: Calculateurs pour DNA, Friction, Indices
2. **Scenario Detector**: Détection automatique des scénarios
3. **API Endpoints**: Routes FastAPI
4. **ML Engine**: XGBoost multi-output
5. **Tests**: Validation des modèles

---

*Version 1.0.0 - Agent Quantum V1*
*Mon_PS Quant Team - Décembre 2025*

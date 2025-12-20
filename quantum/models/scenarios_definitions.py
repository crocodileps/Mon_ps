"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM SCENARIOS DEFINITIONS                                      ║
║                                                                                       ║
║  Les 20 scénarios du système avec leurs conditions de déclenchement.                 ║
║                                                                                       ║
║  Groupe A: Tactiques (5)    - Basés sur les styles de jeu                            ║
║  Groupe B: Temporels (4)    - Basés sur le timing                                    ║
║  Groupe C: Physiques (4)    - Basés sur la condition physique                        ║
║  Groupe D: Psychologiques (4) - Basés sur le mental                                  ║
║  Groupe E: Nemesis (3)      - Basés sur les matchups historiques                     ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import List, Dict
from .scenarios_strategy import (
    ScenarioID,
    ScenarioCategory,
    ScenarioCondition,
    ScenarioMarket,
    ScenarioDefinition,
    MarketType,
)


def get_scenario_definitions() -> Dict[ScenarioID, ScenarioDefinition]:
    """
    Retourne toutes les définitions de scénarios.
    
    Ces scénarios sont basés sur:
    - Les corrélations découvertes dans nos données
    - Les insights de l'audit 99 équipes
    - Les patterns ADCM (Advanced Dynamic Clash Model)
    """
    
    scenarios = {}
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # GROUPE A: SCÉNARIOS TACTIQUES (5)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    # 🌪️ 1. TOTAL_CHAOS - Le Festival
    scenarios[ScenarioID.TOTAL_CHAOS] = ScenarioDefinition(
        id=ScenarioID.TOTAL_CHAOS,
        name="TOTAL CHAOS",
        emoji="🌪️",
        description="Deux équipes à haute intensité avec défenses fragiles. Festival de buts attendu.",
        category=ScenarioCategory.TACTICAL,
        conditions=[
            ScenarioCondition(
                description="Pace factor combiné élevé",
                metric="pace_factor_combined",
                operator=">",
                threshold=140
            ),
            ScenarioCondition(
                description="xG combiné élevé",
                metric="xg_combined",
                operator=">",
                threshold=3.2
            ),
            ScenarioCondition(
                description="Solidité défensive combinée faible",
                metric="defensive_solidity_combined",
                operator="<",
                threshold=65
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.OVER_35,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=72,
                reasoning="Pace élevé + défenses faibles = festival de buts"
            ),
            ScenarioMarket(
                market=MarketType.FIRST_HALF_OVER_15,
                priority="PRIMARY",
                typical_edge=0.10,
                typical_confidence=68,
                reasoning="Intensité dès le début"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.BTTS_YES,
                priority="SECONDARY",
                typical_edge=0.08,
                typical_confidence=70,
                reasoning="Les deux équipes marquent dans le chaos"
            ),
        ],
        avoid_markets=[MarketType.UNDER_25, MarketType.HOME_CLEAN_SHEET_YES, MarketType.AWAY_CLEAN_SHEET_YES],
        historical_roi=15.2,
        historical_win_rate=68.5,
        min_confidence_threshold=65,
    )
    
    # 🏰 2. THE_SIEGE - Domination Stérile
    scenarios[ScenarioID.THE_SIEGE] = ScenarioDefinition(
        id=ScenarioID.THE_SIEGE,
        name="THE SIEGE",
        emoji="🏰",
        description="Une équipe domine la possession contre un bloc bas. Victoire difficile.",
        category=ScenarioCategory.TACTICAL,
        conditions=[
            ScenarioCondition(
                description="Écart de possession élevé",
                metric="possession_gap",
                operator=">",
                threshold=18
            ),
            ScenarioCondition(
                description="Équipe dominante avec contrôle élevé",
                metric="control_index_dominant",
                operator=">",
                threshold=72
            ),
            ScenarioCondition(
                description="Adversaire en bloc bas",
                metric="underdog_block_low",
                operator="==",
                threshold=1
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.CORNERS_OVER_105,
                priority="PRIMARY",
                typical_edge=0.15,
                typical_confidence=70,
                reasoning="Équipe dominante va pilonner les flancs"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.UNDER_25,
                priority="SECONDARY",
                typical_edge=0.08,
                typical_confidence=62,
                reasoning="Bloc bas = peu d'espaces, victoire laborieuse"
            ),
        ],
        avoid_markets=[MarketType.OVER_35, MarketType.BTTS_YES],
        historical_roi=10.5,
        historical_win_rate=62.0,
        min_confidence_threshold=60,
    )
    
    # 🔫 3. SNIPER_DUEL - Létalité Maximale
    scenarios[ScenarioID.SNIPER_DUEL] = ScenarioDefinition(
        id=ScenarioID.SNIPER_DUEL,
        name="SNIPER DUEL",
        emoji="🔫",
        description="Deux équipes très létales. Chaque occasion peut finir au fond.",
        category=ScenarioCategory.TACTICAL,
        conditions=[
            ScenarioCondition(
                description="Sniper index home élevé",
                metric="sniper_index_home",
                operator=">",
                threshold=68
            ),
            ScenarioCondition(
                description="Sniper index away élevé",
                metric="sniper_index_away",
                operator=">",
                threshold=68
            ),
            ScenarioCondition(
                description="Tirs cadrés combinés élevés",
                metric="shots_on_target_combined",
                operator=">",
                threshold=10
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.BTTS_YES,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=75,
                reasoning="Deux équipes cliniques = les deux marquent"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.OVER_25,
                priority="SECONDARY",
                typical_edge=0.08,
                typical_confidence=68,
                reasoning="Efficacité des deux côtés"
            ),
        ],
        avoid_markets=[MarketType.HOME_CLEAN_SHEET_YES, MarketType.AWAY_CLEAN_SHEET_YES, MarketType.UNDER_15],
        historical_roi=13.8,
        historical_win_rate=71.0,
        min_confidence_threshold=65,
    )
    
    # 💤 4. ATTRITION_WAR - Guerre d'Usure
    scenarios[ScenarioID.ATTRITION_WAR] = ScenarioDefinition(
        id=ScenarioID.ATTRITION_WAR,
        name="ATTRITION WAR",
        emoji="💤",
        description="Deux équipes à faible intensité qui s'annulent. Match fermé.",
        category=ScenarioCategory.TACTICAL,
        conditions=[
            ScenarioCondition(
                description="Pace factor combiné faible",
                metric="pace_factor_combined",
                operator="<",
                threshold=95
            ),
            ScenarioCondition(
                description="Les deux ont un contrôle élevé",
                metric="control_combined",
                operator=">",
                threshold=115
            ),
            ScenarioCondition(
                description="Fautes combinées élevées",
                metric="fouls_combined",
                operator=">",
                threshold=22
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.UNDER_25,
                priority="PRIMARY",
                typical_edge=0.14,
                typical_confidence=72,
                reasoning="Styles qui s'annulent = peu de buts"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.DRAW,
                priority="SECONDARY",
                typical_edge=0.10,
                typical_confidence=55,
                reasoning="Équilibre des forces"
            ),
            ScenarioMarket(
                market=MarketType.CARDS_OVER_45,
                priority="SECONDARY",
                typical_edge=0.12,
                typical_confidence=65,
                reasoning="Frustration = cartons"
            ),
        ],
        avoid_markets=[MarketType.OVER_35, MarketType.BTTS_YES],
        historical_roi=11.2,
        historical_win_rate=66.0,
        min_confidence_threshold=60,
    )
    
    # 🃏 5. GLASS_CANNON - Canon de Verre
    scenarios[ScenarioID.GLASS_CANNON] = ScenarioDefinition(
        id=ScenarioID.GLASS_CANNON,
        name="GLASS CANNON",
        emoji="🃏",
        description="Une équipe attaque fort mais défend mal. Proie facile pour adversaire clinique.",
        category=ScenarioCategory.TACTICAL,
        conditions=[
            ScenarioCondition(
                description="Équipe A xG for élevé",
                metric="glass_cannon_xg_for",
                operator=">",
                threshold=1.7
            ),
            ScenarioCondition(
                description="Équipe A xG against élevé",
                metric="glass_cannon_xg_against",
                operator=">",
                threshold=1.5
            ),
            ScenarioCondition(
                description="Adversaire clinique",
                metric="opponent_sniper_index",
                operator=">",
                threshold=65
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.AWAY_OVER_15,
                priority="PRIMARY",
                typical_edge=0.15,
                typical_confidence=70,
                reasoning="Défense poreuse + adversaire clinique"
            ),
            ScenarioMarket(
                market=MarketType.BTTS_YES,
                priority="PRIMARY",
                typical_edge=0.10,
                typical_confidence=72,
                reasoning="Les deux vont marquer"
            ),
        ],
        avoid_markets=[MarketType.HOME_CLEAN_SHEET_YES, MarketType.UNDER_15],
        historical_roi=14.5,
        historical_win_rate=69.0,
        min_confidence_threshold=62,
    )
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # GROUPE B: SCÉNARIOS TEMPORELS (4)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    # ⏰ 6. LATE_PUNISHMENT - Punition Tardive
    scenarios[ScenarioID.LATE_PUNISHMENT] = ScenarioDefinition(
        id=ScenarioID.LATE_PUNISHMENT,
        name="LATE PUNISHMENT",
        emoji="⏰",
        description="Une équipe diesel va punir un adversaire fatigué en fin de match.",
        category=ScenarioCategory.TEMPORAL,
        conditions=[
            ScenarioCondition(
                description="Home diesel factor élevé",
                metric="diesel_factor_home",
                operator=">",
                threshold=0.68
            ),
            ScenarioCondition(
                description="Away pressing decay élevé",
                metric="pressing_decay_away",
                operator=">",
                threshold=0.22
            ),
            ScenarioCondition(
                description="Home bench impact élevé",
                metric="bench_impact_home",
                operator=">",
                threshold=6.0
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_2H_OVER_05,
                priority="PRIMARY",
                typical_edge=0.15,
                typical_confidence=75,
                reasoning="Diesel + adversaire fatigué = but tardif"
            ),
            ScenarioMarket(
                market=MarketType.GOAL_76_90,
                priority="PRIMARY",
                typical_edge=0.18,
                typical_confidence=70,
                reasoning="Peak de scoring en fin de match"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.SECOND_HALF_HIGHEST,
                priority="SECONDARY",
                typical_edge=0.12,
                typical_confidence=68,
                reasoning="Plus de buts en 2ème mi-temps"
            ),
        ],
        avoid_markets=[MarketType.FIRST_HALF_OVER_15],
        historical_roi=18.5,
        historical_win_rate=72.0,
        min_confidence_threshold=68,
    )
    
    # 🚀 7. EXPLOSIVE_START - Départ Fulgurant
    scenarios[ScenarioID.EXPLOSIVE_START] = ScenarioDefinition(
        id=ScenarioID.EXPLOSIVE_START,
        name="EXPLOSIVE START",
        emoji="🚀",
        description="Deux équipes qui commencent fort. Buts précoces attendus.",
        category=ScenarioCategory.TEMPORAL,
        conditions=[
            ScenarioCondition(
                description="Les deux sont des sprinters",
                metric="sprinter_factor_both",
                operator=">",
                threshold=0.55
            ),
            ScenarioCondition(
                description="xG 0-15 combiné élevé",
                metric="xg_0_15_combined",
                operator=">",
                threshold=0.5
            ),
            ScenarioCondition(
                description="Défenses lentes à se mettre en place",
                metric="defensive_settling_time",
                operator=">",
                threshold=12
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.FIRST_HALF_OVER_15,
                priority="PRIMARY",
                typical_edge=0.14,
                typical_confidence=70,
                reasoning="Deux équipes qui démarrent fort"
            ),
            ScenarioMarket(
                market=MarketType.GOAL_0_15,
                priority="PRIMARY",
                typical_edge=0.16,
                typical_confidence=65,
                reasoning="But précoce très probable"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.FIRST_HALF_HIGHEST,
                priority="SECONDARY",
                typical_edge=0.10,
                typical_confidence=62,
                reasoning="Intensité en début de match"
            ),
        ],
        avoid_markets=[MarketType.UNDER_15],
        historical_roi=13.2,
        historical_win_rate=67.0,
        min_confidence_threshold=62,
    )
    
    # 🐢 8. DIESEL_DUEL - Deux Diesels
    scenarios[ScenarioID.DIESEL_DUEL] = ScenarioDefinition(
        id=ScenarioID.DIESEL_DUEL,
        name="DIESEL DUEL",
        emoji="🐢",
        description="Deux équipes qui finissent fort. Match qui s'emballe en 2ème mi-temps.",
        category=ScenarioCategory.TEMPORAL,
        conditions=[
            ScenarioCondition(
                description="Home diesel factor élevé",
                metric="diesel_factor_home",
                operator=">",
                threshold=0.62
            ),
            ScenarioCondition(
                description="Away diesel factor élevé",
                metric="diesel_factor_away",
                operator=">",
                threshold=0.62
            ),
            ScenarioCondition(
                description="xG 1H combiné faible",
                metric="xg_1h_combined",
                operator="<",
                threshold=1.3
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.SECOND_HALF_OVER_15,
                priority="PRIMARY",
                typical_edge=0.16,
                typical_confidence=72,
                reasoning="Deux diesels = explosion en 2H"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.SECOND_HALF_HIGHEST,
                priority="SECONDARY",
                typical_edge=0.12,
                typical_confidence=68,
                reasoning="Plus d'action en 2ème période"
            ),
        ],
        avoid_markets=[MarketType.FIRST_HALF_OVER_15, MarketType.GOAL_0_15],
        historical_roi=14.8,
        historical_win_rate=70.0,
        min_confidence_threshold=65,
    )
    
    # ⚡ 9. CLUTCH_KILLER - Tueur des Fins de Match
    scenarios[ScenarioID.CLUTCH_KILLER] = ScenarioDefinition(
        id=ScenarioID.CLUTCH_KILLER,
        name="CLUTCH KILLER",
        emoji="⚡",
        description="Une équipe avec un instinct de tueur contre une équipe qui craque.",
        category=ScenarioCategory.TEMPORAL,
        conditions=[
            ScenarioCondition(
                description="Home clutch factor élevé",
                metric="clutch_factor_home",
                operator=">",
                threshold=0.75
            ),
            ScenarioCondition(
                description="Home goals 75-90 rate élevé",
                metric="goals_75_90_rate_home",
                operator=">",
                threshold=0.35
            ),
            ScenarioCondition(
                description="Away late collapse risk",
                metric="late_collapse_risk_away",
                operator=">",
                threshold=0.25
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.GOAL_76_90,
                priority="PRIMARY",
                typical_edge=0.20,
                typical_confidence=72,
                reasoning="Clutch killer + adversaire qui craque"
            ),
            ScenarioMarket(
                market=MarketType.HOME_2H_OVER_05,
                priority="PRIMARY",
                typical_edge=0.15,
                typical_confidence=70,
                reasoning="But tardif très probable"
            ),
        ],
        avoid_markets=[MarketType.AWAY_CLEAN_SHEET_YES],
        historical_roi=17.5,
        historical_win_rate=71.0,
        min_confidence_threshold=68,
    )
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # GROUPE C: SCÉNARIOS PHYSIQUES (4)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    # 😰 10. FATIGUE_COLLAPSE - Effondrement Physique
    scenarios[ScenarioID.FATIGUE_COLLAPSE] = ScenarioDefinition(
        id=ScenarioID.FATIGUE_COLLAPSE,
        name="FATIGUE COLLAPSE",
        emoji="😰",
        description="Une équipe fatiguée (semaine européenne, peu de repos) va s'effondrer.",
        category=ScenarioCategory.PHYSICAL,
        conditions=[
            ScenarioCondition(
                description="Away avec peu de repos",
                metric="rest_days_away",
                operator="<",
                threshold=4
            ),
            ScenarioCondition(
                description="Away en semaine européenne",
                metric="european_week_away",
                operator="==",
                threshold=1
            ),
            ScenarioCondition(
                description="Away pressing decay élevé",
                metric="pressing_decay_away",
                operator=">",
                threshold=0.25
            ),
            ScenarioCondition(
                description="Home bench impact élevé",
                metric="bench_impact_home",
                operator=">",
                threshold=6.5
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_2H_OVER_05,
                priority="PRIMARY",
                typical_edge=0.18,
                typical_confidence=75,
                reasoning="Adversaire fatigué va craquer"
            ),
            ScenarioMarket(
                market=MarketType.SECOND_HALF_HIGHEST,
                priority="PRIMARY",
                typical_edge=0.14,
                typical_confidence=70,
                reasoning="Fatigue = buts en 2H"
            ),
        ],
        avoid_markets=[MarketType.AWAY_OVER_15, MarketType.FIRST_HALF_OVER_15],
        historical_roi=16.8,
        historical_win_rate=73.0,
        min_confidence_threshold=70,
    )
    
    # 💪 11. PRESSING_DEATH - Mort par Pressing
    scenarios[ScenarioID.PRESSING_DEATH] = ScenarioDefinition(
        id=ScenarioID.PRESSING_DEATH,
        name="PRESSING DEATH",
        emoji="💪",
        description="Une équipe avec pressing intense va étouffer un adversaire fragile en relance.",
        category=ScenarioCategory.PHYSICAL,
        conditions=[
            ScenarioCondition(
                description="Home PPDA faible (pressing intense)",
                metric="ppda_home",
                operator="<",
                threshold=8.5
            ),
            ScenarioCondition(
                description="Away faible en relance",
                metric="build_up_weakness_away",
                operator=">",
                threshold=0.55
            ),
            ScenarioCondition(
                description="Away turnovers dans sa moitié",
                metric="turnovers_own_half_away",
                operator=">",
                threshold=3.5
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_OVER_15,
                priority="PRIMARY",
                typical_edge=0.16,
                typical_confidence=72,
                reasoning="Pressing intense + relance faible = récupérations hautes"
            ),
            ScenarioMarket(
                market=MarketType.FIRST_HALF_OVER_05,
                priority="PRIMARY",
                typical_edge=0.10,
                typical_confidence=75,
                reasoning="Pressing efficace dès le début"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_WIN,
                priority="SECONDARY",
                typical_edge=0.08,
                typical_confidence=65,
                reasoning="Domination attendue"
            ),
        ],
        avoid_markets=[MarketType.AWAY_OVER_15],
        historical_roi=15.2,
        historical_win_rate=70.0,
        min_confidence_threshold=65,
    )
    
    # 🏃 12. PACE_EXPLOITATION - Exploitation de la Vitesse
    scenarios[ScenarioID.PACE_EXPLOITATION] = ScenarioDefinition(
        id=ScenarioID.PACE_EXPLOITATION,
        name="PACE EXPLOITATION",
        emoji="🏃",
        description="Une équipe rapide en transition va exploiter une défense haute.",
        category=ScenarioCategory.PHYSICAL,
        conditions=[
            ScenarioCondition(
                description="Home transition speed élevée",
                metric="transition_speed_home",
                operator=">",
                threshold=0.75
            ),
            ScenarioCondition(
                description="Away joue avec ligne haute",
                metric="high_line_away",
                operator="==",
                threshold=1
            ),
            ScenarioCondition(
                description="Away recovery speed faible",
                metric="recovery_speed_away",
                operator="<",
                threshold=58
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_OVER_05,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=78,
                reasoning="Contres rapides vs ligne haute"
            ),
            ScenarioMarket(
                market=MarketType.BTTS_YES,
                priority="PRIMARY",
                typical_edge=0.10,
                typical_confidence=70,
                reasoning="Match ouvert des deux côtés"
            ),
        ],
        avoid_markets=[MarketType.UNDER_15],
        historical_roi=12.5,
        historical_win_rate=72.0,
        min_confidence_threshold=65,
    )
    
    # 🪑 13. BENCH_WARFARE - Guerre des Bancs
    scenarios[ScenarioID.BENCH_WARFARE] = ScenarioDefinition(
        id=ScenarioID.BENCH_WARFARE,
        name="BENCH WARFARE",
        emoji="🪑",
        description="Écart de qualité des bancs. Le favori va punir tard grâce aux remplaçants.",
        category=ScenarioCategory.PHYSICAL,
        conditions=[
            ScenarioCondition(
                description="Écart de bench impact",
                metric="bench_impact_gap",
                operator=">",
                threshold=3.0
            ),
            ScenarioCondition(
                description="Favori avec bench impact élevé",
                metric="bench_impact_favorite",
                operator=">",
                threshold=7.5
            ),
            ScenarioCondition(
                description="Outsider avec bench impact faible",
                metric="bench_impact_underdog",
                operator="<",
                threshold=5.0
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_2H_OVER_05,  # Assuming home is favorite
                priority="PRIMARY",
                typical_edge=0.14,
                typical_confidence=70,
                reasoning="Banc de qualité = impact tardif"
            ),
            ScenarioMarket(
                market=MarketType.SECOND_HALF_OVER_15,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=68,
                reasoning="Les subs font la différence"
            ),
        ],
        avoid_markets=[MarketType.DRAW],
        historical_roi=13.0,
        historical_win_rate=67.0,
        min_confidence_threshold=62,
    )
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # GROUPE D: SCÉNARIOS PSYCHOLOGIQUES (4)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    # 🧊 14. CONSERVATIVE_WALL - Mur Conservateur
    scenarios[ScenarioID.CONSERVATIVE_WALL] = ScenarioDefinition(
        id=ScenarioID.CONSERVATIVE_WALL,
        name="CONSERVATIVE WALL",
        emoji="🧊",
        description="Équipe conservative avec forte mentalité défensive. Clean sheet probable.",
        category=ScenarioCategory.PSYCHOLOGICAL,
        conditions=[
            ScenarioCondition(
                description="Home mentality conservative",
                metric="mentality_conservative_home",
                operator="==",
                threshold=1
            ),
            ScenarioCondition(
                description="Home clean sheet rate élevé",
                metric="clean_sheet_rate_home",
                operator=">",
                threshold=0.38
            ),
            ScenarioCondition(
                description="Away faiblesse vs bloc bas",
                metric="vs_low_block_weakness_away",
                operator=">",
                threshold=0.45
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.UNDER_25,
                priority="PRIMARY",
                typical_edge=0.15,
                typical_confidence=72,
                reasoning="Conservative = peu de buts"
            ),
            ScenarioMarket(
                market=MarketType.HOME_CLEAN_SHEET_YES,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=65,
                reasoning="Forte mentalité défensive"
            ),
        ],
        avoid_markets=[MarketType.BTTS_YES, MarketType.OVER_35],
        historical_roi=14.2,
        historical_win_rate=69.0,
        min_confidence_threshold=65,
    )
    
    # 🔥 15. KILLER_INSTINCT - Instinct de Tueur
    scenarios[ScenarioID.KILLER_INSTINCT] = ScenarioDefinition(
        id=ScenarioID.KILLER_INSTINCT,
        name="KILLER INSTINCT",
        emoji="🔥",
        description="Équipe avec haut instinct de tueur contre équipe qui craque.",
        category=ScenarioCategory.PSYCHOLOGICAL,
        conditions=[
            ScenarioCondition(
                description="Home killer instinct élevé",
                metric="killer_instinct_score_home",
                operator=">",
                threshold=0.75
            ),
            ScenarioCondition(
                description="Away collapse rate élevé",
                metric="collapse_rate_away",
                operator=">",
                threshold=0.22
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_OVER_15,
                priority="PRIMARY",
                typical_edge=0.14,
                typical_confidence=70,
                reasoning="Killer instinct + adversaire fragile"
            ),
            ScenarioMarket(
                market=MarketType.GOAL_76_90,
                priority="SECONDARY",
                typical_edge=0.12,
                typical_confidence=65,
                reasoning="Finisseur naturel"
            ),
        ],
        avoid_markets=[MarketType.AWAY_CLEAN_SHEET_YES],
        historical_roi=12.8,
        historical_win_rate=68.0,
        min_confidence_threshold=62,
    )
    
    # 😱 16. COLLAPSE_ALERT - Alerte Effondrement
    scenarios[ScenarioID.COLLAPSE_ALERT] = ScenarioDefinition(
        id=ScenarioID.COLLAPSE_ALERT,
        name="COLLAPSE ALERT",
        emoji="😱",
        description="Équipe avec haut risque d'effondrement contre adversaire résilient.",
        category=ScenarioCategory.PSYCHOLOGICAL,
        conditions=[
            ScenarioCondition(
                description="Home collapse rate élevé",
                metric="collapse_rate_home",
                operator=">",
                threshold=0.28
            ),
            ScenarioCondition(
                description="Home panic factor élevé quand mené",
                metric="panic_factor_home",
                operator=">",
                threshold=0.35
            ),
            ScenarioCondition(
                description="Away resilience élevée",
                metric="resilience_index_away",
                operator=">",
                threshold=68
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.AWAY_OVER_05,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=72,
                reasoning="Home va craquer, away va en profiter"
            ),
            ScenarioMarket(
                market=MarketType.OVER_25,
                priority="SECONDARY",
                typical_edge=0.10,
                typical_confidence=65,
                reasoning="Effondrement = chaos"
            ),
        ],
        avoid_markets=[MarketType.HOME_CLEAN_SHEET_YES, MarketType.HOME_WIN],
        historical_roi=11.5,
        historical_win_rate=66.0,
        min_confidence_threshold=60,
    )
    
    # 💎 17. NOTHING_TO_LOSE - Rien à Perdre
    scenarios[ScenarioID.NOTHING_TO_LOSE] = ScenarioDefinition(
        id=ScenarioID.NOTHING_TO_LOSE,
        name="NOTHING TO LOSE",
        emoji="💎",
        description="Outsider libéré (relégation, rien à perdre) contre favori complaisant.",
        category=ScenarioCategory.PSYCHOLOGICAL,
        conditions=[
            ScenarioCondition(
                description="Away en zone de relégation",
                metric="position_away",
                operator=">",
                threshold=15
            ),
            ScenarioCondition(
                description="Away motivation très élevée",
                metric="motivation_index_away",
                operator=">",
                threshold=82
            ),
            ScenarioCondition(
                description="Home risque de complaisance",
                metric="complacency_risk_home",
                operator=">",
                threshold=0.28
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.AH_AWAY_P15,
                priority="PRIMARY",
                typical_edge=0.15,
                typical_confidence=70,
                reasoning="Outsider libéré peut surprendre"
            ),
            ScenarioMarket(
                market=MarketType.DC_1X,
                priority="SECONDARY",
                typical_edge=0.08,
                typical_confidence=72,
                reasoning="Double chance conservateur"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.AWAY_WIN,
                priority="VALUE",
                typical_edge=0.20,
                typical_confidence=45,
                reasoning="Value bet si cote > 4.0"
            ),
        ],
        avoid_markets=[MarketType.AH_HOME_M15],
        historical_roi=16.5,
        historical_win_rate=64.0,
        min_confidence_threshold=58,
    )
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # GROUPE E: SCÉNARIOS NEMESIS (3)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    # 🎯 18. NEMESIS_TRAP - Piège Némésis
    scenarios[ScenarioID.NEMESIS_TRAP] = ScenarioDefinition(
        id=ScenarioID.NEMESIS_TRAP,
        name="NEMESIS TRAP",
        emoji="🎯",
        description="Le favori a un nemesis historique. L'outsider peut surprendre.",
        category=ScenarioCategory.NEMESIS,
        conditions=[
            ScenarioCondition(
                description="Away est un nemesis de Home",
                metric="is_nemesis_away_for_home",
                operator="==",
                threshold=1
            ),
            ScenarioCondition(
                description="H2H fortement en faveur de Away",
                metric="h2h_away_advantage",
                operator=">",
                threshold=0.3
            ),
            ScenarioCondition(
                description="Kinetic friction favorise Away",
                metric="kinetic_friction_advantage_away",
                operator=">",
                threshold=15
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.DC_1X,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=68,
                reasoning="Nemesis = risque pour le favori"
            ),
            ScenarioMarket(
                market=MarketType.AWAY_OVER_05,
                priority="PRIMARY",
                typical_edge=0.10,
                typical_confidence=72,
                reasoning="Nemesis va scorer"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.AWAY_WIN,
                priority="VALUE",
                typical_edge=0.18,
                typical_confidence=50,
                reasoning="Value contrarian"
            ),
        ],
        avoid_markets=[MarketType.HOME_WIN, MarketType.AH_HOME_M15],
        historical_roi=15.8,
        historical_win_rate=65.0,
        min_confidence_threshold=62,
    )
    
    # 🦅 19. PREY_HUNT - Chasse à la Proie
    scenarios[ScenarioID.PREY_HUNT] = ScenarioDefinition(
        id=ScenarioID.PREY_HUNT,
        name="PREY HUNT",
        emoji="🦅",
        description="Le favori a une proie historique. Domination attendue.",
        category=ScenarioCategory.NEMESIS,
        conditions=[
            ScenarioCondition(
                description="Away est une proie de Home",
                metric="is_prey_away_for_home",
                operator="==",
                threshold=1
            ),
            ScenarioCondition(
                description="H2H fortement en faveur de Home",
                metric="h2h_home_advantage",
                operator=">",
                threshold=0.4
            ),
            ScenarioCondition(
                description="Kinetic friction confirme dominance",
                metric="kinetic_friction_advantage_home",
                operator=">",
                threshold=20
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.AH_HOME_M15,
                priority="PRIMARY",
                typical_edge=0.14,
                typical_confidence=68,
                reasoning="Proie = domination historique"
            ),
            ScenarioMarket(
                market=MarketType.HOME_OVER_15,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=70,
                reasoning="Home va scorer plusieurs fois"
            ),
        ],
        secondary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_WIN,
                priority="SECONDARY",
                typical_edge=0.08,
                typical_confidence=75,
                reasoning="Victoire confiante"
            ),
        ],
        avoid_markets=[MarketType.AWAY_WIN, MarketType.DRAW],
        historical_roi=14.2,
        historical_win_rate=71.0,
        min_confidence_threshold=65,
    )
    
    # ✈️ 20. AERIAL_RAID - Raid Aérien
    scenarios[ScenarioID.AERIAL_RAID] = ScenarioDefinition(
        id=ScenarioID.AERIAL_RAID,
        name="AERIAL RAID",
        emoji="✈️",
        description="Équipe avec forte menace aérienne contre défense faible dans les airs.",
        category=ScenarioCategory.NEMESIS,
        conditions=[
            ScenarioCondition(
                description="Home set piece threat élevé",
                metric="set_piece_threat_home",
                operator=">",
                threshold=0.65
            ),
            ScenarioCondition(
                description="Home aerial index élevé",
                metric="aerial_index_home",
                operator=">",
                threshold=68
            ),
            ScenarioCondition(
                description="Away faiblesse aérienne",
                metric="aerial_weakness_away",
                operator=">",
                threshold=0.48
            ),
        ],
        primary_markets=[
            ScenarioMarket(
                market=MarketType.HOME_OVER_05,
                priority="PRIMARY",
                typical_edge=0.10,
                typical_confidence=75,
                reasoning="Menace aérienne vs défense faible"
            ),
            ScenarioMarket(
                market=MarketType.CORNERS_OVER_105,
                priority="PRIMARY",
                typical_edge=0.12,
                typical_confidence=68,
                reasoning="Beaucoup de corners attendus"
            ),
        ],
        avoid_markets=[MarketType.AWAY_CLEAN_SHEET_YES],
        historical_roi=11.8,
        historical_win_rate=69.0,
        min_confidence_threshold=62,
    )
    
    return scenarios


# ═══════════════════════════════════════════════════════════════════════════════════════
# SCÉNARIOS CATALOG - Catalogue des scénarios
# ═══════════════════════════════════════════════════════════════════════════════════════

SCENARIOS_CATALOG = get_scenario_definitions()


def get_scenario(scenario_id: ScenarioID) -> ScenarioDefinition:
    """Récupère un scénario par son ID"""
    return SCENARIOS_CATALOG.get(scenario_id)


def get_scenarios_by_category(category: ScenarioCategory) -> List[ScenarioDefinition]:
    """Récupère tous les scénarios d'une catégorie"""
    return [s for s in SCENARIOS_CATALOG.values() if s.category == category]


def get_all_scenarios() -> List[ScenarioDefinition]:
    """Récupère tous les scénarios"""
    return list(SCENARIOS_CATALOG.values())


def get_active_scenarios() -> List[ScenarioDefinition]:
    """Récupère les scénarios actifs uniquement"""
    return [s for s in SCENARIOS_CATALOG.values() if s.is_active]

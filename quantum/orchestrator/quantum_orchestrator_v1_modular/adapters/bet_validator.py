#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                BET VALIDATOR V7.2 - ADAPTATIF (JAMAIS DE BLOCAGE)                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  Philosophie: Une équipe peut évoluer → on AJUSTE le stake, on ne BLOQUE jamais       ║
║                                                                                       ║
║  AJUSTEMENTS STAKE:                                                                   ║
║  • MARKET_FOCUS:   +20% (marché profitable historique)                                ║
║  • PÉPITE:         +25% (edge prouvé contre tendance globale)                         ║
║  • SWEET_SPOT:     +10% (cote 1.60-2.00 optimale)                                     ║
║  • MARKET_ÉVITER:  -30% (historique négatif, mais peut changer)                       ║
║  • ERROR_RATE:     -30% (>40% erreurs modèle)                                         ║
║  • ELITE_LOW_ODDS: -50% (équipe élite + cote <1.50)                                   ║
║  • LOW_ODDS:       -40% (cote <1.50 global)                                           ║
║                                                                                       ║
║  SEUL BLOCAGE: cote < 1.20 (mathématiquement non-rentable)                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import asyncpg
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger("BetValidator")


class BetDecision(Enum):
    """Décisions possibles du validateur"""
    BET_STRONG = "BET_STRONG"      # Paris fort (boost appliqué)
    BET_NORMAL = "BET_NORMAL"      # Paris normal
    BET_CAUTIOUS = "BET_CAUTIOUS"  # Paris prudent (réduction appliquée)
    SKIP = "SKIP"                  # Seul cas: cote < 1.20


@dataclass
class ValidationResult:
    """Résultat de la validation d'un pari"""
    decision: BetDecision
    original_stake: float
    adjusted_stake: float
    stake_multiplier: float = 1.0
    reasons: List[str] = field(default_factory=list)
    adjustments: List[str] = field(default_factory=list)
    is_elite_team: bool = False
    is_pepite: bool = False
    is_focus_market: bool = False
    is_avoid_market: bool = False
    sweet_spot: bool = False
    confidence_score: float = 100.0


@dataclass 
class TeamStrategy:
    """Stratégie personnalisée V7 d'une équipe"""
    team_name: str
    strategy_name: str
    markets_focus: List[str] = field(default_factory=list)
    markets_avoid: List[str] = field(default_factory=list)
    pepites: List[str] = field(default_factory=list)
    error_rate: float = 0.0
    tier: str = "BRONZE"


class BetValidatorV72:
    """
    Validateur de paris V7.2 - ADAPTATIF
    Philosophie: Ajuster le stake, jamais bloquer (sauf cote < 1.20)
    """
    
    # Constantes d'ajustement
    BOOST_MARKET_FOCUS = 0.20      # +20%
    BOOST_PEPITE = 0.25            # +25%
    BOOST_SWEET_SPOT = 0.10        # +10%
    PENALTY_MARKET_AVOID = -0.30   # -30%
    PENALTY_ERROR_RATE = -0.30     # -30%
    PENALTY_ELITE_LOW = -0.50      # -50%
    PENALTY_LOW_ODDS = -0.40       # -40%
    
    # Seuils
    MIN_ODDS_ABSOLUTE = 1.20       # Seul blocage
    MIN_ODDS_WARNING = 1.50        # Warning + pénalité
    MIN_ODDS_ELITE = 1.50          # Pour équipes élites
    SWEET_SPOT_MIN = 1.60
    SWEET_SPOT_MAX = 2.00
    MAX_ODDS = 3.50
    ERROR_RATE_THRESHOLD = 40.0    # % erreurs
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.pool = None
        
        # Données chargées
        self.elite_teams: List[str] = []
        self.team_strategies: Dict[str, TeamStrategy] = {}
        
        # Stats
        self.stats = {
            'total': 0,
            'strong': 0,
            'normal': 0,
            'cautious': 0,
            'skipped': 0,
            'adjustments': {}
        }
    
    async def initialize(self):
        """Initialise connexion et charge données"""
        self.pool = await asyncpg.create_pool(**self.db_config)
        await self._load_elite_teams()
        await self._load_team_strategies()
        logger.info(f"✅ BetValidator V7.2 ADAPTATIF initialisé")
        logger.info(f"   → {len(self.elite_teams)} équipes élites")
        logger.info(f"   → {len(self.team_strategies)} stratégies V7")
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def _load_elite_teams(self):
        """Charge liste équipes élites depuis DB"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT rule_value FROM quantum.betting_rules 
                WHERE rule_name = 'LIQUIDITY_TAX' AND is_active = true
            """)
            if row:
                rules = json.loads(row['rule_value']) if isinstance(row['rule_value'], str) else row['rule_value']
                self.elite_teams = rules.get('elite_teams', [])
    
    async def _load_team_strategies(self):
        """Charge stratégies V7 depuis JSON"""
        try:
            with open('/home/Mon_ps/benchmarks/quantum_v7_smart_quant_latest.json', 'r') as f:
                v7_data = json.load(f)
            
            for team_name, data in v7_data.get('teams', {}).items():
                strategy_data = data.get('custom_strategy', {})
                performance = data.get('performance', {})
                
                self.team_strategies[team_name] = TeamStrategy(
                    team_name=team_name,
                    strategy_name=strategy_data.get('name', 'UNKNOWN'),
                    markets_focus=strategy_data.get('markets_focus', []) or [],
                    markets_avoid=strategy_data.get('markets_avoid', []) or [],
                    pepites=data.get('pepites', []) if isinstance(data.get('pepites', []), list) else [],
                    error_rate=data.get('loss_classification', {}).get('erreur_pct', 0),
                    tier=performance.get('tier', 'BRONZE')
                )
        except Exception as e:
            logger.warning(f"⚠️ Chargement V7: {e}")
    
    def validate(
        self,
        team: str,
        market: str,
        odds: float,
        edge: float = 0.0,
        base_stake: float = 100.0
    ) -> ValidationResult:
        """
        Valide un pari - ADAPTATIF (ajuste stake, ne bloque presque jamais)
        
        Args:
            team: Nom équipe
            market: Type marché (over_35, home, btts_yes...)
            odds: Cote
            edge: Edge calculé (%)
            base_stake: Stake de base (%)
        
        Returns:
            ValidationResult avec stake ajusté
        """
        self.stats['total'] += 1
        
        result = ValidationResult(
            decision=BetDecision.BET_NORMAL,
            original_stake=base_stake,
            adjusted_stake=base_stake,
            stake_multiplier=1.0
        )
        
        multiplier = 1.0
        
        # ═══════════════════════════════════════════════════════════════
        # SEUL BLOCAGE ABSOLU: cote < 1.20 (mathématiquement perdant)
        # ═══════════════════════════════════════════════════════════════
        if odds < self.MIN_ODDS_ABSOLUTE:
            result.decision = BetDecision.SKIP
            result.reasons.append(f"❌ BLOCAGE: Cote {odds:.2f} < 1.20 (mathématiquement non-rentable)")
            self.stats['skipped'] += 1
            return result
        
        # ═══════════════════════════════════════════════════════════════
        # AJUSTEMENTS POSITIFS (BOOSTS)
        # ═══════════════════════════════════════════════════════════════
        
        strategy = self.team_strategies.get(team)
        
        # 1. MARKET_FOCUS: +20%
        if strategy and market in strategy.markets_focus:
            multiplier += self.BOOST_MARKET_FOCUS
            result.is_focus_market = True
            result.confidence_score += 20
            result.adjustments.append(f"✅ FOCUS +20%: '{market}' profitable pour {team}")
            self._track('boost_focus')
        
        # 2. PÉPITE: +25%
        if strategy and market in strategy.pepites:
            multiplier += self.BOOST_PEPITE
            result.is_pepite = True
            result.confidence_score += 25
            result.adjustments.append(f"💎 PÉPITE +25%: '{market}' edge prouvé pour {team}")
            self._track('boost_pepite')
        
        # 3. SWEET_SPOT: +10%
        if self.SWEET_SPOT_MIN <= odds <= self.SWEET_SPOT_MAX:
            multiplier += self.BOOST_SWEET_SPOT
            result.sweet_spot = True
            result.confidence_score += 10
            result.adjustments.append(f"🎯 SWEET_SPOT +10%: Cote {odds:.2f} optimale")
            self._track('boost_sweet_spot')
        
        # ═══════════════════════════════════════════════════════════════
        # AJUSTEMENTS NÉGATIFS (PÉNALITÉS - JAMAIS DE BLOCAGE)
        # ═══════════════════════════════════════════════════════════════
        
        # 4. MARKET_AVOID: -30% (mais PAS de blocage - l'équipe peut évoluer)
        if strategy and market in strategy.markets_avoid:
            multiplier += self.PENALTY_MARKET_AVOID
            result.is_avoid_market = True
            result.confidence_score -= 20
            result.adjustments.append(f"⚠️ ÉVITER -30%: '{market}' historique négatif (peut changer)")
            self._track('penalty_avoid')
        
        # 5. ERROR_RATE >40%: -30%
        if strategy and strategy.error_rate > self.ERROR_RATE_THRESHOLD:
            multiplier += self.PENALTY_ERROR_RATE
            result.confidence_score -= 15
            result.adjustments.append(f"⚠️ ERREURS -30%: {team} {strategy.error_rate:.0f}% erreurs modèle")
            self._track('penalty_error_rate')
        
        # 6. ELITE + LOW ODDS: -50%
        if team in self.elite_teams:
            result.is_elite_team = True
            if odds < self.MIN_ODDS_ELITE:
                multiplier += self.PENALTY_ELITE_LOW
                result.confidence_score -= 25
                result.adjustments.append(f"⚠️ ÉLITE -50%: {team} cote {odds:.2f} < 1.50 (marché efficient)")
                self._track('penalty_elite_low')
            else:
                result.adjustments.append(f"ℹ️ ÉLITE: {team} (cote OK)")
        
        # 7. LOW ODDS GLOBAL: -40%
        elif odds < self.MIN_ODDS_WARNING:
            multiplier += self.PENALTY_LOW_ODDS
            result.confidence_score -= 20
            result.adjustments.append(f"⚠️ LOW_ODDS -40%: Cote {odds:.2f} < 1.50 (value risquée)")
            self._track('penalty_low_odds')
        
        # 8. HIGH ODDS: -20%
        if odds > self.MAX_ODDS:
            multiplier -= 0.20
            result.confidence_score -= 10
            result.adjustments.append(f"⚠️ HIGH_ODDS -20%: Cote {odds:.2f} > 3.50 (variance élevée)")
            self._track('penalty_high_odds')
        
        # ═══════════════════════════════════════════════════════════════
        # CALCUL FINAL
        # ═══════════════════════════════════════════════════════════════
        
        # Multiplier minimum 0.20 (on ne descend jamais en dessous de 20%)
        multiplier = max(0.20, multiplier)
        # Multiplier maximum 1.50 (on ne dépasse pas 150%)
        multiplier = min(1.50, multiplier)
        
        result.stake_multiplier = multiplier
        result.adjusted_stake = round(base_stake * multiplier, 1)
        
        # Décision finale basée sur le multiplier
        if multiplier >= 1.20:
            result.decision = BetDecision.BET_STRONG
            self.stats['strong'] += 1
        elif multiplier >= 0.80:
            result.decision = BetDecision.BET_NORMAL
            self.stats['normal'] += 1
        else:
            result.decision = BetDecision.BET_CAUTIOUS
            self.stats['cautious'] += 1
        
        result.reasons.append(
            f"📊 {result.decision.value}: Stake {base_stake}% × {multiplier:.2f} = {result.adjusted_stake}% | Conf: {result.confidence_score:.0f}"
        )
        
        return result
    
    def _track(self, key: str):
        """Track adjustment stats"""
        self.stats['adjustments'][key] = self.stats['adjustments'].get(key, 0) + 1
    
    def print_stats(self):
        """Affiche statistiques"""
        total = self.stats['total']
        if total == 0:
            print("Aucun pari validé")
            return
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║           BET VALIDATOR V7.2 ADAPTATIF - STATS               ║
╠══════════════════════════════════════════════════════════════╣
║ Total validés:    {total:>5}                                  ║
║ 🟢 BET_STRONG:    {self.stats['strong']:>5} ({100*self.stats['strong']/total:>5.1f}%)                    ║
║ 🔵 BET_NORMAL:    {self.stats['normal']:>5} ({100*self.stats['normal']/total:>5.1f}%)                    ║
║ 🟡 BET_CAUTIOUS:  {self.stats['cautious']:>5} ({100*self.stats['cautious']/total:>5.1f}%)                    ║
║ 🔴 SKIP:          {self.stats['skipped']:>5} ({100*self.stats['skipped']/total:>5.1f}%)                    ║
╠══════════════════════════════════════════════════════════════╣
║ Ajustements appliqués:                                       ║""")
        for adj, count in sorted(self.stats['adjustments'].items(), key=lambda x: -x[1]):
            print(f"║   {adj:<25}: {count:>5}                      ║")
        print("╚══════════════════════════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════════════

async def test_validator():
    """Test du validateur adaptatif"""
    
    DB_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "database": "monps_db",
        "user": "monps_user",
        "password": "monps_secure_password_2024"
    }
    
    validator = BetValidatorV72(DB_CONFIG)
    await validator.initialize()
    
    print("\n" + "="*80)
    print("🧪 TEST BET VALIDATOR V7.2 ADAPTATIF")
    print("   Philosophie: Ajuster le stake, JAMAIS bloquer (sauf cote < 1.20)")
    print("="*80)
    
    # Test cases réalistes
    test_cases = [
        # (team, market, odds, edge, description)
        ("Bayern Munich", "dc_12", 0.54, 1.5, "Elite + cote très basse"),
        ("Bayern Munich", "dc_12", 1.15, 1.5, "Elite + cote < 1.20 = SEUL BLOCAGE"),
        ("Bayern Munich", "over_35", 1.70, 5.0, "Elite + cote OK"),
        ("Barcelona", "over_35", 2.02, 3.0, "Pépite identifiée"),
        ("Barcelona", "btts_no", 4.16, 2.0, "Market à éviter (mais pas bloqué)"),
        ("Celta Vigo", "home", 4.33, 4.0, "Pépite + erreur rate élevé"),
        ("Lazio", "under_25", 1.87, 2.5, "Sweet spot + focus"),
        ("Nice", "btts_no", 1.85, 3.0, "Sweet spot simple"),
        ("Random Team", "home", 1.35, 2.0, "Cote basse (pénalité, pas blocage)"),
        ("Manchester City", "home", 1.25, 1.0, "Elite + cote basse"),
    ]
    
    for team, market, odds, edge, desc in test_cases:
        result = validator.validate(team, market, odds, edge)
        
        emoji = {"BET_STRONG": "🟢", "BET_NORMAL": "🔵", "BET_CAUTIOUS": "🟡", "SKIP": "🔴"}
        
        print(f"\n{'─'*80}")
        print(f"{emoji[result.decision.value]} {desc}")
        print(f"   {team} | {market} @ {odds:.2f}")
        print(f"   → {result.decision.value} | Stake: {result.original_stake}% × {result.stake_multiplier:.2f} = {result.adjusted_stake}%")
        for adj in result.adjustments:
            print(f"      {adj}")
    
    print("\n")
    validator.print_stats()
    
    await validator.close()


if __name__ == "__main__":
    asyncio.run(test_validator())

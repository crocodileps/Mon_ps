#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║              QUANTUM ORCHESTRATOR V7.2 SMART - HEDGE FUND GRADE                       ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  🎯 PHILOSOPHIE: 1 équipe = 1 ADN = 1 stratégie sur mesure                            ║
║                                                                                       ║
║  INTÉGRATIONS V7.2:                                                                   ║
║  • BetValidator ADAPTATIF (ajuste stake, ne bloque jamais sauf < 1.20)                ║
║  • LIQUIDITY_TAX sur équipes élites                                                   ║
║  • MARKET_FOCUS / MARKET_AVOID par équipe                                             ║
║  • PÉPITES identification et boost                                                    ║
║  • SWEET_SPOT detection (cotes 1.60-2.00)                                             ║
║  • ERROR_RATE penalty pour équipes >40% erreurs                                       ║
║                                                                                       ║
║  Usage:                                                                               ║
║    python main.py                    # Analyse tous les matchs des 24h               ║
║    python main.py --hours 48         # Analyse sur 48h                               ║
║    python main.py --team "Barcelona" # Analyse matchs d'une équipe                   ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

# Setup path
sys.path.insert(0, '/home/Mon_ps/quantum/orchestrator')

# Imports locaux
from config.settings import DB_CONFIG, LOGGING_CONFIG
from adapters.database_adapter import DatabaseAdapter, TeamDNA
from adapters.odds_loader import OddsLoader, UpcomingMatch
from adapters.snapshot_recorder import SnapshotRecorder, BetSnapshotRecord, ModelVoteRecord
from adapters.steam_analyzer import SteamAnalyzer, MatchSteamAnalysis, SteamSignal
from adapters.bet_validator import BetValidatorV72, BetDecision

# Mapping V7 markets <-> odds_dict keys
MARKET_MAPPING = {"home": "home_win", "away": "away_win", "draw": "draw", "over_25": "over_25", "over_35": "over_35", "under_25": "under_25", "under_35": "under_35", "btts_yes": "btts_yes", "btts_no": "btts_no"}
V7_TO_ODDS = MARKET_MAPPING
ODDS_TO_V7 = {v: k for k, v in MARKET_MAPPING.items()}

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG.LOG_LEVEL),
    format=LOGGING_CONFIG.LOG_FORMAT,
    datefmt=LOGGING_CONFIG.LOG_DATE_FORMAT
)
logger = logging.getLogger("QuantumMain")


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM ORCHESTRATOR V7.2 SMART - HEDGE FUND GRADE
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumOrchestratorV72:
    """
    Orchestrateur V7.2 Smart avec intégration BetValidator.
    
    Philosophie: 1 équipe = 1 ADN = 1 stratégie sur mesure
    - Ajuste le stake dynamiquement (FOCUS +20%, PÉPITE +25%, AVOID -30%, etc.)
    - Ne bloque JAMAIS sauf cotes < 1.20 (mathématiquement perdant)
    - Une équipe peut évoluer, on ne ferme pas la porte
    """

    def __init__(
        self,
        db_adapter: DatabaseAdapter,
        odds_loader: OddsLoader,
        snapshot_recorder: SnapshotRecorder,
        steam_analyzer: SteamAnalyzer = None
    ):
        self.db = db_adapter
        self.odds = odds_loader
        self.recorder = snapshot_recorder
        self.steam = steam_analyzer or SteamAnalyzer()
        
        # 🎯 V7.2: BetValidator pour ajustement dynamique du stake
        self.validator: Optional[BetValidatorV72] = None
        
        # Stats de session
        self.session_stats = {
            'matches_analyzed': 0,
            'picks_generated': 0,
            'picks_strong': 0,
            'picks_normal': 0,
            'picks_cautious': 0,
            'picks_skipped': 0,
            'total_stake': 0.0
        }

    async def initialize(self):
        """Initialise le BetValidator V7.2"""
        try:
            self.validator = BetValidatorV72(DB_CONFIG)
            await self.validator.initialize()
            logger.info("✅ BetValidator V7.2 SMART initialisé")
            logger.info(f"   → {len(self.validator.elite_teams)} équipes élites")
            logger.info(f"   → {len(self.validator.team_strategies)} stratégies personnalisées")
        except Exception as e:
            logger.warning(f"⚠️ BetValidator non disponible: {e}")
            self.validator = None

    async def close(self):
        """Ferme les connexions"""
        if self.validator:
            await self.validator.close()

    async def analyze_match(
        self,
        match: UpcomingMatch
    ) -> Optional[BetSnapshotRecord]:
        """
        Analyse complète d'un match avec validation V7.2 SMART.

        Returns:
            BetSnapshotRecord avec décision et stake ajusté
        """
        self.session_stats['matches_analyzed'] += 1
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 Analyzing: {match.home_team} vs {match.away_team}")
        logger.info(f"   ⏰ {match.commence_time}")
        logger.info(f"{'='*80}")

        # 1. Charger les DNA des deux équipes
        home_dna = await self.db.get_team_dna(match.home_team)
        away_dna = await self.db.get_team_dna(match.away_team)

        if not home_dna:
            logger.warning(f"   ⚠️ DNA manquant pour {match.home_team}")
        if not away_dna:
            logger.warning(f"   ⚠️ DNA manquant pour {match.away_team}")

        if not home_dna and not away_dna:
            logger.warning(f"   ❌ SKIP - Aucun DNA disponible")
            return None

        # 2. Charger la friction
        friction = await self.db.get_matchup_friction(match.home_team, match.away_team)

        # 3. Charger les stratégies DB
        home_strategy = await self.db.get_team_strategy(match.home_team)
        away_strategy = await self.db.get_team_strategy(match.away_team)

        # 4. Afficher les données chargées
        self._log_team_data(match.home_team, home_dna, home_strategy)
        self._log_team_data(match.away_team, away_dna, away_strategy)

        # 4b. 🎯 V7.2: Afficher stratégie personnalisée si disponible
        if self.validator:
            self._log_v7_strategy(match.home_team)
            self._log_v7_strategy(match.away_team)

        if friction:
            logger.info(f"\n   🔥 Friction Score: {friction.friction_score:.1f}")
            logger.info(f"      Chaos Potential: {friction.chaos_potential:.1f}")
            logger.info(f"      BTTS Prob: {friction.predicted_btts_prob:.1%}")
            logger.info(f"      Over 2.5 Prob: {friction.predicted_over25_prob:.1%}")

        # 5. Afficher les cotes
        # 🎯 FIX: Approximer BTTS si manquant
        if match.odds.btts_yes_odds <= 1.0 and match.odds.over_25_odds > 1.0:
            from adapters.odds_loader import approximate_btts_odds
            btts_yes, btts_no = approximate_btts_odds(match.odds.over_25_odds)
            match.odds.btts_yes_odds = btts_yes
            match.odds.btts_no_odds = btts_no
            logger.info(f"   📊 BTTS approximé: Yes={btts_yes}, No={btts_no}")

        odds_dict = match.odds.to_dict()
        logger.info(f"\n   💰 Odds:")
        logger.info(f"      1X2: {odds_dict['home_win']:.2f} / {odds_dict['draw']:.2f} / {odds_dict['away_win']:.2f}")
        logger.info(f"      Over 2.5: {odds_dict['over_25']:.2f} | BTTS: {odds_dict['btts_yes']:.2f}")

        # 5b. Analyser le Steam
        steam_analysis = await self.steam.get_full_analysis(
            match.match_id,
            match.home_team,
            match.away_team
        )

        if steam_analysis and steam_analysis.movements:
            logger.info(f"\n   📈 Steam Analysis:")
            logger.info(f"      Magnitude: {steam_analysis.steam_magnitude} | Direction: {steam_analysis.dominant_direction}")

            for market, move in steam_analysis.movements.items():
                if move.opening_odds > 0:
                    emoji = "🔥" if move.is_sharp else ("📊" if abs(move.movement_pct) > 3 else "➖")
                    signal_txt = move.signal.value if hasattr(move.signal, 'value') else str(move.signal)
                    logger.info(f"      {emoji} {market}: {move.opening_odds:.2f} → {move.current_odds:.2f} ({move.movement_pct:+.1f}%)")

        # 6. Créer le snapshot
        snapshot = BetSnapshotRecord(
            match_id=match.match_id,
            home_team=match.home_team,
            away_team=match.away_team,
            home_dna_snapshot=self._dna_to_dict(home_dna) if home_dna else {},
            away_dna_snapshot=self._dna_to_dict(away_dna) if away_dna else {},
            friction_snapshot=self._friction_to_dict(friction) if friction else {},
            odds_snapshot=odds_dict,
            decision="PENDING"
        )

        # 7. Analyser avec les modèles
        votes = self._generate_smart_votes(
            home_dna, away_dna, 
            home_strategy, away_strategy, 
            friction, odds_dict,
            match.home_team, match.away_team
        )
        snapshot.model_votes = votes

        # 8. Calculer le consensus
        positive_votes = sum(1 for v in votes if v.is_positive)
        snapshot.consensus_count = positive_votes
        snapshot.consensus_score = (positive_votes / len(votes)) * 100 if votes else 0

        if positive_votes >= 5:
            snapshot.conviction = "STRONG"
        elif positive_votes >= 4:
            snapshot.conviction = "MODERATE"
        else:
            snapshot.conviction = "WEAK"

        # 9. 🎯 V7.2 SMART DECISION avec BetValidator
        if positive_votes >= 4:
            # Sélectionner le meilleur marché
            best_market = self._select_best_market_v72(
                votes, odds_dict, 
                match.home_team, match.away_team
            )
            market_odds = odds_dict.get(best_market, 1.90)
            
            # Déterminer l'équipe principale pour la validation
            # On prend celle avec le meilleur ROI/stratégie
            primary_team = self._get_primary_team(
                match.home_team, match.away_team,
                home_strategy, away_strategy,
                home_dna, away_dna
            )
            
            # 🎯 Validation V7.2 avec ajustement stake
            if self.validator:
                validation = self.validator.validate(
                    team=primary_team,
                    market=best_market,
                    odds=market_odds,
                    edge=5.0,  # Edge estimé
                    base_stake=100.0
                )
                
                if validation.decision == BetDecision.SKIP:
                    # Seul blocage: cote < 1.20
                    snapshot.decision = "SKIP"
                    self.session_stats['picks_skipped'] += 1
                    logger.info(f"\n   🔴 SKIP (V7.2): Cote < 1.20")
                    logger.info(f"      {validation.reasons[0]}")
                else:
                    snapshot.decision = "BET"
                    snapshot.market = best_market
                    snapshot.odds = market_odds
                    snapshot.stake = validation.adjusted_stake / 100.0  # En unités
                    snapshot.edge = 0.05
                    
                    # Stats
                    self.session_stats['picks_generated'] += 1
                    self.session_stats['total_stake'] += snapshot.stake
                    
                    if validation.decision == BetDecision.BET_STRONG:
                        self.session_stats['picks_strong'] += 1
                    elif validation.decision == BetDecision.BET_NORMAL:
                        self.session_stats['picks_normal'] += 1
                    else:
                        self.session_stats['picks_cautious'] += 1
                    
                    # Log détaillé V7.2
                    emoji_map = {
                        "BET_STRONG": "🟢",
                        "BET_NORMAL": "🔵", 
                        "BET_CAUTIOUS": "🟡"
                    }
                    emoji = emoji_map.get(validation.decision.value, "✅")
                    
                    logger.info(f"\n   {emoji} {validation.decision.value}: {best_market.upper()} @ {market_odds:.2f}")
                    logger.info(f"      Team: {primary_team}")
                    logger.info(f"      Stake: {validation.adjusted_stake:.0f}% (×{validation.stake_multiplier:.2f})")
                    logger.info(f"      Consensus: {positive_votes}/6 ({snapshot.conviction})")
                    
                    # Afficher les ajustements
                    for adj in validation.adjustments:
                        logger.info(f"      {adj}")
                    
                    # Indicateurs spéciaux
                    if validation.is_pepite:
                        logger.info(f"      💎 PÉPITE DÉTECTÉE!")
                    if validation.is_elite_team:
                        logger.info(f"      🏆 ÉQUIPE ÉLITE")
                    if validation.sweet_spot:
                        logger.info(f"      🎯 SWEET SPOT")
            else:
                # Fallback sans validator
                snapshot.decision = "BET"
                snapshot.market = best_market
                snapshot.odds = market_odds
                snapshot.stake = 1.0
                snapshot.edge = 0.05
                
                self.session_stats['picks_generated'] += 1
                self.session_stats['picks_normal'] += 1
                self.session_stats['total_stake'] += 1.0
                
                logger.info(f"\n   ✅ BET: {best_market.upper()} @ {market_odds:.2f}")
                logger.info(f"      Consensus: {positive_votes}/6 ({snapshot.conviction})")
        else:
            snapshot.decision = "SKIP"
            logger.info(f"\n   ⏭️ SKIP: Consensus insuffisant ({positive_votes}/6)")

        # 10. Sauvegarder le snapshot
        await self.recorder.save_snapshot(snapshot)
        await self.recorder.save_model_votes(snapshot.snapshot_id, votes)

        return snapshot

    def _log_v7_strategy(self, team_name: str):
        """Affiche la stratégie V7 personnalisée d'une équipe"""
        if not self.validator or team_name not in self.validator.team_strategies:
            return
        
        strategy = self.validator.team_strategies[team_name]
        
        logger.info(f"\n   🎯 V7 Strategy: {strategy.strategy_name}")
        
        if strategy.markets_focus:
            logger.info(f"      FOCUS: {', '.join(strategy.markets_focus)}")
        if strategy.markets_avoid:
            logger.info(f"      AVOID: {', '.join(strategy.markets_avoid[:3])}...")
        if strategy.pepites:
            logger.info(f"      💎 PÉPITES: {', '.join(strategy.pepites)}")
        if strategy.error_rate > 40:
            logger.info(f"      ⚠️ Error Rate: {strategy.error_rate:.0f}%")
        if team_name in self.validator.elite_teams:
            logger.info(f"      🏆 ÉQUIPE ÉLITE (Liquidity Tax active)")

    def _log_team_data(self, team_name: str, dna: Optional[TeamDNA], strategy):
        """Affiche les données d'une équipe"""
        if not dna:
            return

        logger.info(f"\n   🧬 {team_name}:")
        logger.info(f"      Tier: {dna.tier} | ROI: {dna.roi:.1f}% | WR: {dna.win_rate:.1f}%")

        if dna.psyche_dna:
            logger.info(f"      Psyche: {dna.psyche_dna.profile} | KI: {dna.psyche_dna.killer_instinct:.2f}")

        if dna.luck_dna:
            logger.info(f"      Luck: {dna.luck_dna.luck_profile} | xPts Δ: {dna.luck_dna.xpoints_delta:+.2f}")

        if strategy:
            logger.info(f"      DB Strategy: {strategy.strategy_name} (ROI: {strategy.roi:.1f}%)")

    def _dna_to_dict(self, dna: TeamDNA) -> dict:
        """Convertit TeamDNA en dict pour snapshot"""
        if not dna:
            return {}
        return {
            'team_name': dna.team_name,
            'tier': dna.tier,
            'roi': dna.roi,
            'win_rate': dna.win_rate,
            'psyche_profile': dna.psyche_dna.profile if dna.psyche_dna else '',
            'luck_profile': dna.luck_dna.luck_profile if dna.luck_dna else ''
        }

    def _friction_to_dict(self, friction) -> dict:
        """Convertit MatchupFriction en dict"""
        if not friction:
            return {}
        return {
            'friction_score': friction.friction_score,
            'chaos_potential': friction.chaos_potential,
            'predicted_btts_prob': friction.predicted_btts_prob,
            'predicted_over25_prob': friction.predicted_over25_prob
        }

    def _get_primary_team(
        self,
        home_team: str, away_team: str,
        home_strategy, away_strategy,
        home_dna, away_dna
    ) -> str:
        """
        Détermine l'équipe principale pour la validation V7.2.
        Priorise: stratégie V7 disponible > meilleur ROI > home
        """
        # Si une équipe a une stratégie V7, la prioriser
        if self.validator:
            home_has_v7 = home_team in self.validator.team_strategies
            away_has_v7 = away_team in self.validator.team_strategies
            
            if home_has_v7 and not away_has_v7:
                return home_team
            if away_has_v7 and not home_has_v7:
                return away_team
        
        # Sinon, prendre celle avec le meilleur ROI
        home_roi = home_strategy.roi if home_strategy else 0
        away_roi = away_strategy.roi if away_strategy else 0
        
        if away_roi > home_roi + 10:  # Seuil significatif
            return away_team
        
        # Default: home team
        return home_team

    def _select_best_market_v72(
        self,
        votes: List[ModelVoteRecord],
        odds_dict: dict,
        home_team: str,
        away_team: str
    ) -> str:
        """
        Sélectionne le meilleur marché en tenant compte des stratégies V7.
        Priorise: PÉPITE > FOCUS > vote consensus > default
        """
        # 1. Vérifier les PÉPITES et FOCUS des deux équipes
        priority_markets = []
        
        if self.validator:
            for team in [home_team, away_team]:
                if team in self.validator.team_strategies:
                    strategy = self.validator.team_strategies[team]
                    
                    # Les pépites sont prioritaires
                    for pepite in strategy.pepites:
                        # Convertir via mapping
                        odds_key = V7_TO_ODDS.get(pepite, pepite)
                        if odds_key in odds_dict and odds_dict[odds_key] > 1.20:
                            priority_markets.append(('PEPITE', odds_key, pepite, team))
                    
                    # Puis les marchés FOCUS
                    for focus in strategy.markets_focus:
                        odds_key = V7_TO_ODDS.get(focus, focus)
                        if odds_key in odds_dict and odds_dict[odds_key] > 1.20:
                            priority_markets.append(('FOCUS', odds_key, focus, team))
        
        # Si on a trouvé des marchés prioritaires
        if priority_markets:
            # Prioriser PEPITE > FOCUS
            pepites = [m for m in priority_markets if m[0] == 'PEPITE']
            if pepites:
                logger.info(f"      → Marché PÉPITE sélectionné: {pepites[0][1]} ({pepites[0][3]})")
                return pepites[0][1]
            
            focus = [m for m in priority_markets if m[0] == 'FOCUS']
            if focus:
                logger.info(f"      → Marché FOCUS sélectionné: {focus[0][1]} ({focus[0][3]})")
                return focus[0][1]
        
        # 2. Fallback: consensus des votes
        market_votes = {}
        for vote in votes:
            if vote.market and vote.is_positive:
                market_votes[vote.market] = market_votes.get(vote.market, 0) + 1

        if market_votes:
            best = max(market_votes, key=market_votes.get)
            return best

        # 3. Default intelligent
        if odds_dict.get('over_25', 0) > 1.5:
            return 'over_25'
        if odds_dict.get('btts_yes', 0) > 1.5:
            return 'btts_yes'

        return 'over_25'

    def _generate_smart_votes(
        self,
        home_dna, away_dna,
        home_strategy, away_strategy,
        friction, odds_dict,
        home_team: str, away_team: str
    ) -> List[ModelVoteRecord]:
        """Génère des votes avec intégration V7.2"""
        votes = []

        # Model A: Team Strategy (avec boost V7)
        best_strategy = home_strategy if (home_strategy and (not away_strategy or home_strategy.profit > away_strategy.profit)) else away_strategy
        
        # V7.2: Bonus si équipe a une stratégie personnalisée
        v7_bonus = 0
        v7_team = None
        if self.validator:
            for team in [home_team, away_team]:
                if team in self.validator.team_strategies:
                    strat = self.validator.team_strategies[team]
                    if strat.pepites:
                        v7_bonus += 15
                        v7_team = team
                    if strat.markets_focus:
                        v7_bonus += 10
        
        if best_strategy and best_strategy.profit > 5:
            confidence = min(95, 60 + best_strategy.roi / 2 + v7_bonus)
            votes.append(ModelVoteRecord(
                model_name="team_strategy",
                signal="STRONG_BUY" if confidence > 75 else "BUY",
                confidence=confidence,
                reasoning=f"{best_strategy.team_name}: {best_strategy.strategy_name}" + 
                         (f" + V7 PÉPITE" if v7_bonus > 10 else "")
            ))
        else:
            votes.append(ModelVoteRecord(
                model_name="team_strategy",
                signal="HOLD",
                confidence=40 + v7_bonus,
                reasoning="Pas de stratégie profitable" + (f" (V7: {v7_team})" if v7_team else "")
            ))

        # Model B: Quantum Scorer
        if home_dna and away_dna:
            home_score = self._calculate_dna_score(home_dna)
            away_score = self._calculate_dna_score(away_dna)
            edge = abs(home_score - away_score)

            if edge > 1.5:
                votes.append(ModelVoteRecord(
                    model_name="quantum_scorer",
                    signal="STRONG_BUY",
                    confidence=70 + edge * 5,
                    reasoning=f"Z-Score edge: {edge:.2f}"
                ))
            elif edge > 0.8:
                votes.append(ModelVoteRecord(
                    model_name="quantum_scorer",
                    signal="BUY",
                    confidence=60 + edge * 5,
                    reasoning=f"Z-Score edge: {edge:.2f}"
                ))
            else:
                votes.append(ModelVoteRecord(
                    model_name="quantum_scorer",
                    signal="HOLD",
                    confidence=45,
                    reasoning=f"Z-Score edge insuffisant: {edge:.2f}"
                ))
        else:
            votes.append(ModelVoteRecord(
                model_name="quantum_scorer",
                signal="HOLD",
                confidence=40,
                reasoning="DNA incomplet"
            ))

        # Model C: Matchup Scorer
        if friction and friction.friction_score > 0:
            combined = (friction.friction_score + friction.chaos_potential) / 2
            if combined >= 55:
                votes.append(ModelVoteRecord(
                    model_name="matchup_scorer",
                    signal="BUY",
                    confidence=50 + combined / 2,
                    reasoning=f"Friction={friction.friction_score:.0f}, Chaos={friction.chaos_potential:.0f}"
                ))
            else:
                votes.append(ModelVoteRecord(
                    model_name="matchup_scorer",
                    signal="HOLD",
                    confidence=45,
                    reasoning=f"Friction faible: {combined:.0f}"
                ))
        else:
            votes.append(ModelVoteRecord(
                model_name="matchup_scorer",
                signal="HOLD",
                confidence=40,
                reasoning="Pas de données friction"
            ))

        # Model D: Dixon-Coles
        if friction:
            btts_prob = friction.predicted_btts_prob
            over25_prob = friction.predicted_over25_prob

            btts_implied = 1 / odds_dict.get('btts_yes', 2.0) if odds_dict.get('btts_yes', 0) > 0 else 0.5
            over25_implied = 1 / odds_dict.get('over_25', 2.0) if odds_dict.get('over_25', 0) > 0 else 0.5

            btts_edge = btts_prob - btts_implied
            over25_edge = over25_prob - over25_implied

            best_edge = max(btts_edge, over25_edge)
            best_market = "btts_yes" if btts_edge > over25_edge else "over_25"

            if best_edge > 0.08:
                votes.append(ModelVoteRecord(
                    model_name="dixon_coles",
                    signal="STRONG_BUY",
                    confidence=70 + best_edge * 100,
                    reasoning=f"{best_market}: edge={best_edge:.1%}",
                    market=best_market
                ))
            elif best_edge > 0.03:
                votes.append(ModelVoteRecord(
                    model_name="dixon_coles",
                    signal="BUY",
                    confidence=60 + best_edge * 100,
                    reasoning=f"{best_market}: edge={best_edge:.1%}",
                    market=best_market
                ))
            else:
                votes.append(ModelVoteRecord(
                    model_name="dixon_coles",
                    signal="HOLD",
                    confidence=40,
                    reasoning=f"Edge insuffisant: {best_edge:.1%}"
                ))
        else:
            votes.append(ModelVoteRecord(
                model_name="dixon_coles",
                signal="HOLD",
                confidence=40,
                reasoning="Pas de probabilités"
            ))

        # Model E: Scenarios
        scenarios_detected = []
        if friction and friction.friction_score > 60:
            scenarios_detected.append("HIGH_FRICTION")
        if friction and friction.chaos_potential > 60:
            scenarios_detected.append("CHAOS_POTENTIAL")
        if home_dna and home_dna.luck_dna.luck_profile == "UNLUCKY":
            scenarios_detected.append("REGRESSION_UP")
        if away_dna and away_dna.luck_dna.luck_profile == "UNLUCKY":
            scenarios_detected.append("REGRESSION_UP")

        if len(scenarios_detected) >= 2:
            votes.append(ModelVoteRecord(
                model_name="scenarios",
                signal="BUY",
                confidence=50 + len(scenarios_detected) * 10,
                reasoning=f"Scénarios: {', '.join(scenarios_detected)}"
            ))
        else:
            votes.append(ModelVoteRecord(
                model_name="scenarios",
                signal="HOLD",
                confidence=40,
                reasoning=f"Peu de scénarios: {len(scenarios_detected)}"
            ))

        # Model F: DNA Features (avec V7 boost)
        dna_signals = []
        bonus = 0

        for dna, team in [(home_dna, home_team), (away_dna, away_team)]:
            if not dna:
                continue

            if dna.psyche_dna.profile == "DEFENSIVE":
                dna_signals.append(f"{team[:3]}: DEF")
                bonus += 5

            if dna.luck_dna.luck_profile in ["UNLUCKY", "VERY_UNLUCKY"]:
                dna_signals.append(f"{team[:3]}: {dna.luck_dna.luck_profile[:6]}")
                bonus += 6

            if dna.psyche_dna.killer_instinct < 0.8:
                bonus += 4

            if dna.roi > 30:
                dna_signals.append(f"{team[:3]}: ROI+")
                bonus += 5
            
            # V7.2: Bonus si équipe a des pépites
            if self.validator and team in self.validator.team_strategies:
                strat = self.validator.team_strategies[team]
                if strat.pepites:
                    dna_signals.append(f"{team[:3]}: PÉPITE")
                    bonus += 8

        if bonus >= 10:
            votes.append(ModelVoteRecord(
                model_name="dna_features",
                signal="STRONG_BUY" if bonus >= 15 else "BUY",
                confidence=50 + bonus,
                reasoning=f"DNA: {', '.join(dna_signals[:4])}"
            ))
        else:
            votes.append(ModelVoteRecord(
                model_name="dna_features",
                signal="HOLD",
                confidence=40,
                reasoning=f"DNA bonus faible: {bonus}"
            ))

        return votes

    def _calculate_dna_score(self, dna: TeamDNA) -> float:
        """Calcule un score Z basé sur le DNA"""
        score = 0.0

        if dna.roi > 30:
            score += 1.0
        elif dna.roi > 15:
            score += 0.5

        if dna.win_rate > 65:
            score += 0.8

        if dna.psyche_dna.profile == "DEFENSIVE":
            score += 1.2
        if dna.psyche_dna.killer_instinct < 0.8:
            score += 0.8

        if dna.luck_dna.luck_profile == "UNLUCKY":
            score += 1.0
        elif dna.luck_dna.luck_profile == "VERY_UNLUCKY":
            score += 1.5

        tier_scores = {"ELITE": 0.5, "GOLD": 0.3, "SILVER": 0.1}
        score += tier_scores.get(dna.tier, 0)

        return score

    def print_session_stats(self):
        """Affiche les statistiques de session"""
        stats = self.session_stats
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║           QUANTUM V7.2 SMART - SESSION STATS                 ║
╠══════════════════════════════════════════════════════════════╣
║ Matchs analysés:   {stats['matches_analyzed']:>5}                                  ║
║ Picks générés:     {stats['picks_generated']:>5}                                  ║
║ ───────────────────────────────────────────────────────────  ║
║ 🟢 BET_STRONG:     {stats['picks_strong']:>5}                                  ║
║ 🔵 BET_NORMAL:     {stats['picks_normal']:>5}                                  ║
║ 🟡 BET_CAUTIOUS:   {stats['picks_cautious']:>5}                                  ║
║ 🔴 SKIPPED:        {stats['picks_skipped']:>5}                                  ║
║ ───────────────────────────────────────────────────────────  ║
║ Total Stake:       {stats['total_stake']:>5.1f}u                                 ║
╚══════════════════════════════════════════════════════════════╝""")
        
        # Stats du validator
        if self.validator:
            self.validator.print_stats()


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main(hours_ahead: int = 24, team_filter: str = None):
    """
    Fonction principale V7.2 SMART.
    """
    print("=" * 80)
    print("🚀 QUANTUM ORCHESTRATOR V7.2 SMART - HEDGE FUND GRADE")
    print("=" * 80)
    print(f"   🎯 Philosophie: 1 équipe = 1 ADN = 1 stratégie sur mesure")
    print(f"   📊 Mode: REAL DATA from PostgreSQL")
    print(f"   ⏰ Hours ahead: {hours_ahead}h")
    if team_filter:
        print(f"   🔍 Team filter: {team_filter}")
    print("=" * 80)

    # 1. Créer les adapters
    db_adapter = DatabaseAdapter()
    odds_loader = OddsLoader()
    snapshot_recorder = SnapshotRecorder()
    steam_analyzer = SteamAnalyzer()

    try:
        # 2. Connecter à PostgreSQL
        await db_adapter.connect()
        logger.info("✅ Database adapter connected")

        # Partager le pool
        odds_loader.set_pool(db_adapter.pool)
        snapshot_recorder.set_pool(db_adapter.pool)
        steam_analyzer.set_pool(db_adapter.pool)

        # 3. Charger les équipes quantum
        quantum_teams = await db_adapter.get_team_list()
        logger.info(f"📊 {len(quantum_teams)} équipes dans quantum.team_profiles")

        # 4. Charger les matchs
        matches = await odds_loader.get_matches_with_quantum_teams(
            hours_ahead=hours_ahead,
            quantum_teams=quantum_teams
        )

        if not matches:
            logger.warning("⚠️ Aucun match trouvé avec équipes quantum!")
            return

        logger.info(f"\n🎯 {len(matches)} matchs à analyser")

        # 5. Filtrer si demandé
        if team_filter:
            matches = [m for m in matches
                      if team_filter.lower() in m.home_team.lower()
                      or team_filter.lower() in m.away_team.lower()]
            logger.info(f"   Après filtre '{team_filter}': {len(matches)} matchs")

        # 6. 🎯 Créer l'orchestrateur V7.2 SMART
        orchestrator = QuantumOrchestratorV72(
            db_adapter=db_adapter,
            odds_loader=odds_loader,
            snapshot_recorder=snapshot_recorder,
            steam_analyzer=steam_analyzer
        )
        
        # Initialiser le BetValidator
        await orchestrator.initialize()

        # 7. Analyser chaque match
        picks = []
        for match in matches:
            snapshot = await orchestrator.analyze_match(match)
            if snapshot and snapshot.decision == "BET":
                picks.append(snapshot)

        # 8. Résumé
        print("\n" + "=" * 80)
        print("📊 QUANTUM V7.2 SMART PICKS SUMMARY")
        print("=" * 80)

        if picks:
            # Grouper par type de décision
            strong_picks = [p for p in picks if p.stake >= 1.2]
            normal_picks = [p for p in picks if 0.8 <= p.stake < 1.2]
            cautious_picks = [p for p in picks if p.stake < 0.8]
            
            total_stake = sum(p.stake for p in picks)
            
            if strong_picks:
                print(f"\n🟢 STRONG PICKS ({len(strong_picks)}):")
                for pick in strong_picks:
                    print(f"   ✅ {pick.home_team} vs {pick.away_team}")
                    print(f"      {pick.market.upper()} @ {pick.odds:.2f} | Stake: {pick.stake:.2f}u")
            
            if normal_picks:
                print(f"\n🔵 NORMAL PICKS ({len(normal_picks)}):")
                for pick in normal_picks:
                    print(f"   ✅ {pick.home_team} vs {pick.away_team}")
                    print(f"      {pick.market.upper()} @ {pick.odds:.2f} | Stake: {pick.stake:.2f}u")
            
            if cautious_picks:
                print(f"\n🟡 CAUTIOUS PICKS ({len(cautious_picks)}):")
                for pick in cautious_picks:
                    print(f"   ⚠️ {pick.home_team} vs {pick.away_team}")
                    print(f"      {pick.market.upper()} @ {pick.odds:.2f} | Stake: {pick.stake:.2f}u")

            print(f"\n{'─' * 40}")
            print(f"📈 Total: {len(picks)} picks | {total_stake:.2f}u staked")
        else:
            print("\n⚠️ Aucun pick généré")

        # 9. Stats de session
        orchestrator.print_session_stats()

        print("=" * 80)

    finally:
        # 10. Fermer les connexions
        await orchestrator.close()
        await db_adapter.close()
        logger.info("🔌 Connections closed")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum Orchestrator V7.2 SMART")
    parser.add_argument("--hours", type=int, default=24, help="Hours ahead to analyze")
    parser.add_argument("--team", type=str, default=None, help="Filter by team name")

    args = parser.parse_args()

    asyncio.run(main(hours_ahead=args.hours, team_filter=args.team))

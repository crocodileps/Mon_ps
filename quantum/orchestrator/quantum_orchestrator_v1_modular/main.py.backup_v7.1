#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM ORCHESTRATOR V1.0 - MAIN ENTRY POINT                       ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Point d'entrée principal qui:                                                        ║
║  • Connecte les adapters à PostgreSQL                                                ║
║  • Charge les matchs à venir avec cotes                                              ║
║  • Analyse chaque match avec l'orchestrateur                                         ║
║  • Sauvegarde les snapshots pour audit                                               ║
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
from typing import List, Optional

# Setup path
sys.path.insert(0, '/home/Mon_ps/quantum/orchestrator')

# Imports locaux
from config.settings import DB_CONFIG, LOGGING_CONFIG
from adapters.database_adapter import DatabaseAdapter, TeamDNA
from adapters.odds_loader import OddsLoader, UpcomingMatch
from adapters.snapshot_recorder import SnapshotRecorder, BetSnapshotRecord, ModelVoteRecord
from adapters.steam_analyzer import SteamAnalyzer, MatchSteamAnalysis, SteamSignal

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG.LOG_LEVEL),
    format=LOGGING_CONFIG.LOG_FORMAT,
    datefmt=LOGGING_CONFIG.LOG_DATE_FORMAT
)
logger = logging.getLogger("QuantumMain")


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM ORCHESTRATOR INTERFACE (simplifié pour ce main)
# ═══════════════════════════════════════════════════════════════════════════════════════

class SimpleQuantumOrchestrator:
    """
    Orchestrateur simplifié qui utilise les adapters.
    
    NOTE: Cette version sera remplacée par l'intégration complète
    avec quantum_orchestrator_v1.py (2245 lignes)
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
    
    async def analyze_match(
        self,
        match: UpcomingMatch
    ) -> Optional[BetSnapshotRecord]:
        """
        Analyse complète d'un match.
        
        Returns:
            BetSnapshotRecord avec la décision (BET ou SKIP)
        """
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
        
        # 3. Charger les stratégies
        home_strategy = await self.db.get_team_strategy(match.home_team)
        away_strategy = await self.db.get_team_strategy(match.away_team)
        
        # 4. Afficher les données chargées
        self._log_team_data(match.home_team, home_dna, home_strategy)
        self._log_team_data(match.away_team, away_dna, away_strategy)
        
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
            logger.info(f"   📊 BTTS approximé: Yes={btts_yes}, No={btts_no} (depuis O2.5={match.odds.over_25_odds})")

        odds_dict = match.odds.to_dict()
        logger.info(f"\n   💰 Odds:")
        logger.info(f"      1X2: {odds_dict['home_win']:.2f} / {odds_dict['draw']:.2f} / {odds_dict['away_win']:.2f}")
        logger.info(f"      Over 2.5: {odds_dict['over_25']:.2f} | BTTS: {odds_dict['btts_yes']:.2f}")
        
        # 5b. Analyser le Steam avec le VRAI SteamAnalyzer
        # Utilise match_steam_analysis + fg_sharp_money + odds_history
        steam_analysis = await self.steam.get_full_analysis(
            match.match_id, 
            match.home_team, 
            match.away_team
        )
        
        if steam_analysis and steam_analysis.movements:
            logger.info(f"\n   📈 Steam Analysis (from DB):")
            logger.info(f"      Magnitude: {steam_analysis.steam_magnitude} | Direction: {steam_analysis.dominant_direction}")
            logger.info(f"      Prob Shift Total: {steam_analysis.total_prob_shift:.1f}%")
            
            for market, move in steam_analysis.movements.items():
                if move.opening_odds > 0:
                    emoji = "🔥" if move.is_sharp else ("📊" if abs(move.movement_pct) > 3 else "➖")
                    signal_txt = move.signal.value if hasattr(move.signal, 'value') else str(move.signal)
                    logger.info(f"      {emoji} {market}: {move.opening_odds:.2f} → {move.current_odds:.2f} ({move.movement_pct:+.1f}%) [{signal_txt}]")
            
            # Alerte si classification suspecte
            if steam_analysis.classification == 'SUSPICIOUS':
                logger.warning(f"      🚨 SUSPICIOUS: Mouvement extrême détecté!")
            elif steam_analysis.validation_status == 'CAUTION':
                logger.info(f"      ⚠️ CAUTION: Sharp money significatif")
        else:
            # Fallback: analyse simplifiée depuis odds_history
            await self.odds.enrich_match_with_steam(match)
            if match.odds.odds_movements:
                logger.info(f"\n   📈 Steam Analysis (live):")
                for market, movement in match.odds.odds_movements.items():
                    emoji = "🔥" if movement.is_sharp_steam else ("📊" if movement.is_significant else "➖")
                    logger.info(f"      {emoji} {market}: {movement.opening_odds:.2f} → {movement.current_odds:.2f} ({movement.movement_pct:+.1f}%) [{movement.steam_signal}]")
        
        # 6. Créer le snapshot (pour l'instant sans analyse complète)
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
        
        # 7. Analyser avec les modèles (simplifié)
        votes = self._generate_simple_votes(home_dna, away_dna, home_strategy, away_strategy, friction, odds_dict)
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
        
        # 9. Décision
        if positive_votes >= 4:
            snapshot.decision = "BET"
            snapshot.market = self._select_best_market(votes, odds_dict)
            snapshot.odds = odds_dict.get(snapshot.market, 1.90)
            snapshot.stake = 1.0  # Simplifié
            snapshot.edge = 0.05  # Simplifié
            
            logger.info(f"\n   ✅ DECISION: BET {snapshot.market.upper()} @ {snapshot.odds:.2f}")
            logger.info(f"      Consensus: {positive_votes}/6 ({snapshot.conviction})")
        else:
            snapshot.decision = "SKIP"
            logger.info(f"\n   ⏭️ DECISION: SKIP")
            logger.info(f"      Consensus insuffisant: {positive_votes}/6")
        
        # 10. Sauvegarder le snapshot
        await self.recorder.save_snapshot(snapshot)
        await self.recorder.save_model_votes(snapshot.snapshot_id, votes)
        
        return snapshot
    
    def _log_team_data(self, team_name: str, dna: Optional[TeamDNA], strategy):
        """Affiche les données d'une équipe"""
        if not dna:
            return
        
        logger.info(f"\n   🧬 {team_name}:")
        logger.info(f"      Tier: {dna.tier} | ROI: {dna.roi:.1f}% | WR: {dna.win_rate:.1f}%")
        
        # Psyche DNA
        if dna.psyche_dna:
            logger.info(f"      Psyche: {dna.psyche_dna.profile} | KI: {dna.psyche_dna.killer_instinct:.2f}")
        
        # Luck DNA
        if dna.luck_dna:
            logger.info(f"      Luck: {dna.luck_dna.luck_profile} | xPts Δ: {dna.luck_dna.xpoints_delta:+.2f}")
        
        # Strategy
        if strategy:
            logger.info(f"      Best Strategy: {strategy.strategy_name} (ROI: {strategy.roi:.1f}%, P&L: {strategy.profit:+.1f}u)")
    
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
    
    def _generate_simple_votes(
        self, 
        home_dna, away_dna, 
        home_strategy, away_strategy,
        friction, odds_dict
    ) -> List[ModelVoteRecord]:
        """Génère des votes simplifiés pour chaque modèle"""
        votes = []
        
        # Model A: Team Strategy
        best_strategy = home_strategy if (home_strategy and (not away_strategy or home_strategy.profit > away_strategy.profit)) else away_strategy
        if best_strategy and best_strategy.profit > 5:
            votes.append(ModelVoteRecord(
                model_name="team_strategy",
                signal="STRONG_BUY" if best_strategy.roi > 50 else "BUY",
                confidence=min(95, 60 + best_strategy.roi / 2),
                reasoning=f"{best_strategy.team_name}: {best_strategy.strategy_name} ROI={best_strategy.roi:.1f}%"
            ))
        else:
            votes.append(ModelVoteRecord(
                model_name="team_strategy",
                signal="HOLD",
                confidence=40,
                reasoning="Pas de stratégie profitable"
            ))
        
        # Model B: Quantum Scorer (basé sur DNA)
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
        
        # Model C: Matchup Scorer (friction)
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
        
        # Model D: Dixon-Coles (probabilités)
        if friction:
            btts_prob = friction.predicted_btts_prob
            over25_prob = friction.predicted_over25_prob
            
            # Calculer edge vs odds
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
        
        # Model F: DNA Features
        dna_signals = []
        bonus = 0
        
        for dna, team in [(home_dna, "HOME"), (away_dna, "AWAY")]:
            if not dna:
                continue
            
            if dna.psyche_dna.profile == "DEFENSIVE":
                dna_signals.append(f"{team}: DEFENSIVE")
                bonus += 5
            
            if dna.luck_dna.luck_profile in ["UNLUCKY", "VERY_UNLUCKY"]:
                dna_signals.append(f"{team}: {dna.luck_dna.luck_profile}")
                bonus += 6
            
            if dna.psyche_dna.killer_instinct < 0.8:
                dna_signals.append(f"{team}: Low KI")
                bonus += 4
            
            if dna.roi > 30:
                dna_signals.append(f"{team}: High ROI")
                bonus += 5
        
        if bonus >= 10:
            votes.append(ModelVoteRecord(
                model_name="dna_features",
                signal="STRONG_BUY" if bonus >= 15 else "BUY",
                confidence=50 + bonus,
                reasoning=f"DNA signals: {', '.join(dna_signals)}"
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
        """Calcule un score Z simplifié basé sur le DNA"""
        score = 0.0
        
        # ROI
        if dna.roi > 30:
            score += 1.0
        elif dna.roi > 15:
            score += 0.5
        
        # Win rate
        if dna.win_rate > 65:
            score += 0.8
        
        # Psyche
        if dna.psyche_dna.profile == "DEFENSIVE":
            score += 1.2
        if dna.psyche_dna.killer_instinct < 0.8:
            score += 0.8
        
        # Luck
        if dna.luck_dna.luck_profile == "UNLUCKY":
            score += 1.0
        elif dna.luck_dna.luck_profile == "VERY_UNLUCKY":
            score += 1.5
        
        # Tier
        tier_scores = {"ELITE": 0.5, "GOLD": 0.3, "SILVER": 0.1}
        score += tier_scores.get(dna.tier, 0)
        
        return score
    
    def _select_best_market(self, votes: List[ModelVoteRecord], odds_dict: dict) -> str:
        """Sélectionne le meilleur marché basé sur les votes"""
        market_votes = {}
        
        for vote in votes:
            if vote.market and vote.is_positive:
                market_votes[vote.market] = market_votes.get(vote.market, 0) + 1
        
        if market_votes:
            return max(market_votes, key=market_votes.get)
        
        # Default: over_25 si odds disponibles
        if odds_dict.get('over_25', 0) > 1.5:
            return 'over_25'
        if odds_dict.get('btts_yes', 0) > 1.5:
            return 'btts_yes'
        
        return 'over_25'


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main(hours_ahead: int = 24, team_filter: str = None):
    """
    Fonction principale.
    
    Args:
        hours_ahead: Nombre d'heures à analyser
        team_filter: Filtrer sur une équipe spécifique
    """
    logger.info("=" * 80)
    logger.info("🚀 QUANTUM ORCHESTRATOR V1.0 - PRODUCTION")
    logger.info("=" * 80)
    logger.info(f"   Mode: REAL DATA from PostgreSQL")
    logger.info(f"   Hours ahead: {hours_ahead}h")
    if team_filter:
        logger.info(f"   Team filter: {team_filter}")
    logger.info("=" * 80)
    
    # 1. Créer les adapters
    db_adapter = DatabaseAdapter()
    odds_loader = OddsLoader()
    snapshot_recorder = SnapshotRecorder()
    steam_analyzer = SteamAnalyzer()
    
    try:
        # 2. Connecter à PostgreSQL
        await db_adapter.connect()
        logger.info("✅ Database adapter connected")
        
        # Partager le pool avec tous les adapters
        odds_loader.set_pool(db_adapter.pool)
        snapshot_recorder.set_pool(db_adapter.pool)
        steam_analyzer.set_pool(db_adapter.pool)
        
        # 3. Charger les équipes quantum
        quantum_teams = await db_adapter.get_team_list()
        logger.info(f"📊 {len(quantum_teams)} équipes dans quantum.team_profiles")
        
        # 4. Charger les matchs avec équipes quantum
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
        
        # 6. Créer l'orchestrateur avec Steam Analyzer
        orchestrator = SimpleQuantumOrchestrator(
            db_adapter=db_adapter,
            odds_loader=odds_loader,
            snapshot_recorder=snapshot_recorder,
            steam_analyzer=steam_analyzer
        )
        
        # 7. Analyser chaque match
        picks = []
        for match in matches:
            snapshot = await orchestrator.analyze_match(match)
            if snapshot and snapshot.decision == "BET":
                picks.append(snapshot)
        
        # 8. Résumé
        print("\n" + "=" * 80)
        print("📊 QUANTUM PICKS SUMMARY")
        print("=" * 80)
        
        if picks:
            total_stake = 0
            total_ev = 0
            
            for pick in picks:
                print(f"\n✅ {pick.home_team} vs {pick.away_team}")
                print(f"   Market: {pick.market.upper()} @ {pick.odds:.2f}")
                print(f"   Stake: {pick.stake:.1f}u | Consensus: {pick.consensus_count}/6 ({pick.conviction})")
                total_stake += pick.stake
                total_ev += pick.expected_value
            
            print(f"\n{'─' * 40}")
            print(f"📈 Total: {len(picks)} picks | {total_stake:.1f}u staked")
        else:
            print("\n⚠️ Aucun pick généré")
        
        print("=" * 80)
        
    finally:
        # 9. Fermer les connexions
        await db_adapter.close()
        logger.info("🔌 Connections closed")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum Orchestrator V1.0")
    parser.add_argument("--hours", type=int, default=24, help="Hours ahead to analyze")
    parser.add_argument("--team", type=str, default=None, help="Filter by team name")
    
    args = parser.parse_args()
    
    asyncio.run(main(hours_ahead=args.hours, team_filter=args.team))

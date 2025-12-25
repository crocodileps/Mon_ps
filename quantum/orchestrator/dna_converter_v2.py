"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    DNA CONVERTER V2 - HEDGE FUND GRADE                        ║
║                                                                               ║
║  Convertit les données merged (HybridDNALoader) → Dataclasses V2             ║
║                                                                               ║
║  Philosophie: "LES DONNÉES DICTENT LE PROFIL, PAS LA RÉPUTATION"             ║
║  - 100% données mesurées                                                      ║
║  - 0% champs génériques                                                       ║
║  - Extraction directe depuis merged (DB + JSON)                              ║
║                                                                               ║
║  Usage:                                                                       ║
║      converter = DNAConverterV2()                                            ║
║      team_dna = converter.convert(merged_dict, "Liverpool")                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
from typing import Dict, Any, Optional, List

from quantum.orchestrator.dataclasses_v2 import (
    TeamDNA, MarketDNA, ContextDNA, RiskDNA, TemporalDNA,
    NemesisDNA, PsycheDNA, SentimentDNA, RosterDNA,
    PhysicalDNA, LuckDNA, ChameleonDNA
)

# GK Profiler Senior Quant
from quantum.orchestrator.gk_profiler_senior_quant import calculate_gk_profile_senior_quant

logger = logging.getLogger(__name__)


class DNAConverterV2:
    """
    Convertisseur merged Dict → TeamDNA V2 (168 mesures uniques).
    
    Extrait les données RÉELLES depuis:
    - DB: team_quantum_dna_v3 (via HybridDNALoader)
    - JSON: team_dna_unified_v3.json (via HybridDNALoader)
    - merged: Fusion des deux sources
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _safe_parse_json(self, value: Any) -> Dict:
        """Parse une STRING JSON en Dict. Retourne {} si erreur."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}")
                return {}
        return {}
    
    def _safe_get(self, data: Dict, *keys, default: Any = None) -> Any:
        """Extraction sécurisée avec clés imbriquées."""
        if data is None:
            return default
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return default
            if result is None:
                return default
        return result
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Conversion sécurisée vers float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Conversion sécurisée vers int."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_bool(self, value: Any, default: bool = False) -> bool:
        """Conversion sécurisée vers bool."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
    
    def _safe_list(self, value: Any, default: List = None) -> List:
        """Conversion sécurisée vers list."""
        if default is None:
            default = []
        if value is None:
            return default
        if isinstance(value, list):
            return value
        return default
    
    def _safe_dict(self, value: Any, default: Dict = None) -> Dict:
        """Conversion sécurisée vers dict."""
        if default is None:
            default = {}
        if value is None:
            return default
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return self._safe_parse_json(value)
        return default
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 1: MarketDNA (17 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_market_dna(self, merged: Dict) -> MarketDNA:
        """Convertit les données trading vers MarketDNA."""
        bp = merged.get('betting_performance', {})
        market_db = self._safe_parse_json(merged.get('market_dna'))
        empirical = self._safe_dict(market_db.get('empirical_profile'))
        
        exploit_markets = self._safe_list(merged.get('exploit_markets', []))
        avoid_markets = self._safe_list(merged.get('avoid_markets', []))
        
        if not exploit_markets:
            betting_json = merged.get('betting_json', {})
            best_markets = betting_json.get('best_markets', [])
            if best_markets:
                exploit_markets = best_markets
        
        if not avoid_markets:
            defense = merged.get('defense', {})
            anti_exploits = defense.get('anti_exploits', [])
            if anti_exploits:
                avoid_markets = anti_exploits
        
        return MarketDNA(
            avg_clv=self._safe_float(empirical.get('avg_clv'), 0.0),
            avg_edge=self._safe_float(empirical.get('avg_edge'), 0.0),
            sample_size=self._safe_int(empirical.get('sample_size'), 0),
            over_specialist=self._safe_bool(empirical.get('over_specialist'), False),
            under_specialist=self._safe_bool(empirical.get('under_specialist'), False),
            btts_no_specialist=self._safe_bool(empirical.get('btts_no_specialist'), False),
            btts_yes_specialist=self._safe_bool(empirical.get('btts_yes_specialist'), False),
            profitable_strategies=self._safe_int(market_db.get('profitable_strategies'), 0),
            total_strategies_tested=self._safe_int(market_db.get('total_strategies_tested'), 0),
            total_bets=self._safe_int(bp.get('total_bets'), 0),
            total_wins=self._safe_int(bp.get('total_wins'), 0),
            win_rate=self._safe_float(bp.get('win_rate'), 0.0),
            total_pnl=self._safe_float(bp.get('total_pnl'), 0.0),
            roi=self._safe_float(bp.get('roi'), 0.0),
            unlucky_losses=self._safe_int(bp.get('unlucky_losses'), 0),
            exploit_markets=exploit_markets,
            avoid_markets=avoid_markets
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 2: ContextDNA (22 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_context_dna(self, merged: Dict) -> ContextDNA:
        """Convertit le contexte vers ContextDNA."""
        ctx_db = self._safe_parse_json(merged.get('context_dna'))
        xg_profile = self._safe_dict(ctx_db.get('xg_profile'))
        defense = merged.get('defense', {})
        ctx_json = merged.get('context_json', {})
        record = ctx_json.get('record', {})
        
        goals_for = self._safe_int(record.get('goals_for'), 0)
        xg_total = self._safe_float(xg_profile.get('xg_for_avg', 0)) * self._safe_int(defense.get('matches_played'), 1)
        clinical = goals_for > xg_total if xg_total > 0 else False
        
        return ContextDNA(
            home_strength=self._safe_float(ctx_db.get('home_strength'), 50.0),
            away_strength=self._safe_float(ctx_db.get('away_strength'), 50.0),
            style_score=self._safe_int(ctx_db.get('style_score'), 50),
            btts_tendency=self._safe_int(ctx_db.get('btts_tendency'), 50),
            draw_tendency=self._safe_int(ctx_db.get('draw_tendency'), 50),
            goals_tendency=self._safe_int(ctx_db.get('goals_tendency'), 50),
            xg_diff=self._safe_float(xg_profile.get('xg_diff'), 0.0),
            xg_for_avg=self._safe_float(xg_profile.get('xg_for_avg'), 0.0),
            xg_against_avg=self._safe_float(xg_profile.get('xg_against_avg'), 0.0),
            clinical=clinical,
            clean_sheets_home=self._safe_int(defense.get('clean_sheets_home'), 0),
            clean_sheets_away=self._safe_int(defense.get('clean_sheets_away'), 0),
            matches_home=self._safe_int(defense.get('matches_home'), 0),
            matches_away=self._safe_int(defense.get('matches_away'), 0),
            ga_per_90_home=self._safe_float(defense.get('ga_per_90_home'), 0.0),
            ga_per_90_away=self._safe_float(defense.get('ga_per_90_away'), 0.0),
            wins=self._safe_int(record.get('wins'), 0),
            draws=self._safe_int(record.get('draws'), 0),
            losses=self._safe_int(record.get('losses'), 0),
            points=self._safe_int(record.get('points'), 0),
            goals_for=self._safe_int(record.get('goals_for'), 0),
            goals_against=self._safe_int(record.get('goals_against'), 0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 3: RiskDNA (14 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_risk_dna(self, merged: Dict) -> RiskDNA:
        """Convertit les données de risque vers RiskDNA."""
        luck_db = self._safe_parse_json(merged.get('luck_dna'))
        psyche_db = self._safe_parse_json(merged.get('psyche_dna'))
        market_db = self._safe_parse_json(merged.get('market_dna'))
        empirical = self._safe_dict(market_db.get('empirical_profile'))
        ctx_json = merged.get('context_json', {})
        variance = ctx_json.get('variance', {})
        
        tier_rank = self._safe_int(merged.get('tier_rank'), 50)
        unlucky_pct = self._safe_float(merged.get('unlucky_pct'), 0.0)
        
        return RiskDNA(
            total_luck=self._safe_float(luck_db.get('total_luck'), 0.0),
            defensive_luck=self._safe_float(luck_db.get('defensive_luck'), 0.0),
            finishing_luck=self._safe_float(luck_db.get('finishing_luck'), 0.0),
            ppg_vs_expected=self._safe_float(luck_db.get('ppg_vs_expected'), 0.0),
            panic_factor=self._safe_float(psyche_db.get('panic_factor'), 0.0),
            lead_protection=self._safe_float(psyche_db.get('lead_protection'), 0.0),
            unlucky_pct=unlucky_pct,
            tier_rank=tier_rank,
            avg_edge=self._safe_float(empirical.get('avg_edge'), 0.0),
            profitable_strategies=self._safe_int(market_db.get('profitable_strategies'), 0),
            total_strategies_tested=self._safe_int(market_db.get('total_strategies_tested'), 0),
            luck_index=self._safe_float(variance.get('luck_index'), 0.0),
            xg_overperformance=self._safe_float(variance.get('xg_overperformance'), 0.0),
            xga_overperformance=self._safe_float(variance.get('xga_overperformance'), 0.0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 4: TemporalDNA (16 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_temporal_dna(self, merged: Dict) -> TemporalDNA:
        """Convertit les données temporelles vers TemporalDNA."""
        temporal_db = self._safe_parse_json(merged.get('temporal_dna'))
        v8_enriched = self._safe_dict(temporal_db.get('v8_enriched'))
        periods = self._safe_dict(temporal_db.get('periods'))
        defense = merged.get('defense', {})
        
        return TemporalDNA(
            diesel_factor=self._safe_float(temporal_db.get('diesel_factor'), 0.5),
            fast_starter=self._safe_float(temporal_db.get('fast_starter'), 0.5),
            diesel_factor_v8=self._safe_float(temporal_db.get('diesel_factor_v8'), 0.5),
            fast_starter_v8=self._safe_float(temporal_db.get('fast_starter_v8'), 0.5),
            xg_momentum=self._safe_float(temporal_db.get('xg_momentum'), 1.0),
            late_game_threat=self._safe_float(temporal_db.get('late_game_threat'), 0.0),
            first_half_xg_pct=self._safe_float(temporal_db.get('first_half_xg_pct'), 50.0),
            second_half_xg_pct=self._safe_float(temporal_db.get('second_half_xg_pct'), 50.0),
            periods=periods,
            xg_1h_avg=self._safe_float(v8_enriched.get('xg_1h_avg'), 0.0),
            xg_2h_avg=self._safe_float(v8_enriched.get('xg_2h_avg'), 0.0),
            away_diesel=self._safe_float(v8_enriched.get('away_diesel'), 0.5),
            xga_early_pct=self._safe_float(defense.get('xga_early_pct'), 0.0),
            xga_late_pct=self._safe_float(defense.get('xga_late_pct'), 0.0),
            resist_early=self._safe_float(defense.get('resist_early'), 50.0),
            resist_late=self._safe_float(defense.get('resist_late'), 50.0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 5: NemesisDNA (16 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_nemesis_dna(self, merged: Dict) -> NemesisDNA:
        """Convertit les données de style vers NemesisDNA."""
        nemesis_db = self._safe_parse_json(merged.get('nemesis_dna'))
        defense = merged.get('defense', {})
        tactical = merged.get('tactical', {})
        
        friction_multipliers = self._safe_dict(defense.get('friction_multipliers'))
        if not friction_multipliers:
            friction_multipliers = self._safe_dict(tactical.get('friction_multipliers'))
        
        matchup_guide = self._safe_dict(defense.get('matchup_guide'))
        if not matchup_guide:
            matchup_guide = self._safe_dict(tactical.get('matchup_guide'))
        
        weaknesses = self._safe_list(defense.get('weaknesses'))
        strengths = self._safe_list(defense.get('strengths'))
        percentiles = defense.get('percentiles', {})
        
        return NemesisDNA(
            verticality=self._safe_float(nemesis_db.get('verticality'), 5.0),
            patience=self._safe_float(nemesis_db.get('patience'), 5.0),
            fast_shots=self._safe_int(nemesis_db.get('fast_shots'), 0),
            slow_shots=self._safe_int(nemesis_db.get('slow_shots'), 0),
            territorial_dominance=self._safe_float(nemesis_db.get('territorial_dominance'), 0.5),
            keeper_overperformance=self._safe_float(nemesis_db.get('keeper_overperformance'), 0.0),
            friction_multipliers=friction_multipliers,
            matchup_guide=matchup_guide,
            weaknesses=weaknesses,
            strengths=strengths,
            percentile_global=self._safe_int(percentiles.get('global'), 50),
            percentile_aerial=self._safe_int(percentiles.get('aerial'), 50),
            percentile_early=self._safe_int(percentiles.get('early'), 50),
            percentile_late=self._safe_int(percentiles.get('late'), 50),
            percentile_home=self._safe_int(percentiles.get('home'), 50),
            percentile_away=self._safe_int(percentiles.get('away'), 50)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 6: PsycheDNA (15 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_psyche_dna(self, merged: Dict) -> PsycheDNA:
        """Convertit les données psychologiques vers PsycheDNA."""
        psyche_db = self._safe_parse_json(merged.get('psyche_dna'))
        clutch_dna = merged.get('clutch_dna', {})
        if isinstance(clutch_dna, str):
            clutch_dna = self._safe_parse_json(clutch_dna)
        defense = merged.get('defense', {})

        # ═══════════════════════════════════════════════════════════════
        # ENRICHISSEMENT mentality (compatibilité V1 - 24 Déc 2025)
        # Logique métier centralisée - pas de magic numbers cachés
        # Source de vérité unique pour la conversion float → str
        # ═══════════════════════════════════════════════════════════════
        THRESHOLD_AGGRESSIVE = 1.2
        THRESHOLD_CONSERVATIVE = 0.8

        comeback_val = self._safe_float(psyche_db.get('comeback_mentality'), 1.0)

        if comeback_val >= THRESHOLD_AGGRESSIVE:
            mentality = "AGGRESSIVE"
        elif comeback_val <= THRESHOLD_CONSERVATIVE:
            mentality = "CONSERVATIVE"
        else:
            mentality = "BALANCED"

        return PsycheDNA(
            panic_factor=self._safe_float(psyche_db.get('panic_factor'), 2.0),
            killer_instinct=self._safe_float(psyche_db.get('killer_instinct'), 1.0),
            lead_protection=self._safe_float(psyche_db.get('lead_protection'), 0.5),
            comeback_mentality=comeback_val,
            drawing_performance=self._safe_float(psyche_db.get('drawing_performance'), 1.0),
            mentality=mentality,
            ht_dominance=self._safe_float(clutch_dna.get('ht_dominance'), 50.0),
            collapse_rate=self._safe_float(clutch_dna.get('collapse_rate'), 0.0),
            comeback_rate=self._safe_float(clutch_dna.get('comeback_rate'), 0.0),
            surrender_rate=self._safe_float(clutch_dna.get('surrender_rate'), 0.0),
            lead_protection_v8=self._safe_float(clutch_dna.get('lead_protection_v8'), 50.0),
            ga_leading_1=self._safe_int(defense.get('ga_leading_1'), 0),
            ga_leading_2plus=self._safe_int(defense.get('ga_leading_2plus'), 0),
            ga_level=self._safe_int(defense.get('ga_level'), 0),
            ga_losing_1=self._safe_int(defense.get('ga_losing_1'), 0),
            ga_losing_2plus=self._safe_int(defense.get('ga_losing_2plus'), 0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 7: SentimentDNA (14 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_sentiment_dna(self, merged: Dict) -> SentimentDNA:
        """Convertit les données de sentiment vers SentimentDNA."""
        market_db = self._safe_parse_json(merged.get('market_dna'))
        empirical = self._safe_dict(market_db.get('empirical_profile'))
        ctx_db = self._safe_parse_json(merged.get('context_dna'))
        betting_json = merged.get('betting_json', {})
        
        tier_rank = self._safe_int(merged.get('tier_rank'), 50)
        unlucky_pct = self._safe_float(merged.get('unlucky_pct'), 0.0)
        style_confidence = self._safe_int(merged.get('style_confidence'), 50)
        
        return SentimentDNA(
            avg_clv=self._safe_float(empirical.get('avg_clv'), 0.0),
            avg_edge=self._safe_float(empirical.get('avg_edge'), 0.0),
            sample_size=self._safe_int(empirical.get('sample_size'), 0),
            over_specialist=self._safe_bool(empirical.get('over_specialist'), False),
            under_specialist=self._safe_bool(empirical.get('under_specialist'), False),
            btts_no_specialist=self._safe_bool(empirical.get('btts_no_specialist'), False),
            btts_yes_specialist=self._safe_bool(empirical.get('btts_yes_specialist'), False),
            tier_rank=tier_rank,
            unlucky_pct=unlucky_pct,
            style_confidence=style_confidence,
            goals_tendency=self._safe_int(ctx_db.get('goals_tendency'), 50),
            btts_tendency=self._safe_int(ctx_db.get('btts_tendency'), 50),
            draw_tendency=self._safe_int(ctx_db.get('draw_tendency'), 50),
            vulnerability_score=self._safe_float(betting_json.get('vulnerability_score'), 50.0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 8: RosterDNA (12 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_roster_dna(self, merged: Dict) -> RosterDNA:
        """Convertit les données d'effectif vers RosterDNA."""
        roster_db = self._safe_parse_json(merged.get('roster_dna'))
        nemesis_db = self._safe_parse_json(merged.get('nemesis_dna'))
        defensive_line = merged.get('defensive_line', {})
        goalkeeper = defensive_line.get('goalkeeper', {})
        
        mvp = self._safe_dict(roster_db.get('mvp'))
        playmaker = self._safe_dict(roster_db.get('key_playmaker'))

        # ═══════════════════════════════════════════════════════════════
        # PROFILING GK SENIOR QUANT FBA GRADE V2 (25 Déc 2025)
        # Remplace la classification simple par profilage multi-dimensionnel
        # ═══════════════════════════════════════════════════════════════

        # Extraction timing data depuis defensive_line
        timing_data = goalkeeper.get('timing', {})

        # Construction enriched_data
        enriched_data = merged.get('goalkeeper_dna_enriched', {})
        if not isinstance(enriched_data, dict):
            enriched_data = {}
        enriched_data['team_name'] = merged.get('team_name', 'Unknown')

        # Ajout matches si pas dans gk_data
        gk_data_enriched = dict(goalkeeper)
        gk_data_enriched['matches'] = merged.get('total_matches', 17)

        # Calcul du profil complet
        try:
            gk_profile = calculate_gk_profile_senior_quant(
                gk_data=gk_data_enriched,
                timing_data=timing_data,
                enriched_data=enriched_data
            )
            keeper_status = gk_profile.status
            # Stocker le profil complet dans merged pour accès ultérieur
            merged['_gk_profile_fba'] = gk_profile
        except Exception as e:
            logger.warning(f"GK Profiler error: {e}, falling back to NORMAL")
            keeper_status = "NORMAL"

        return RosterDNA(
            mvp_name=mvp.get('name', 'Unknown'),
            mvp_xg_chain=self._safe_float(mvp.get('xg_chain'), 0.0),
            mvp_dependency_score=self._safe_float(mvp.get('dependency_score'), 0.0),
            playmaker_name=playmaker.get('name', 'Unknown'),
            playmaker_xg_buildup=self._safe_float(playmaker.get('xg_buildup'), 0.0),
            total_team_xg=self._safe_float(roster_db.get('total_team_xg'), 0.0),
            top3_dependency=self._safe_float(roster_db.get('top3_dependency'), 0.0),
            clinical_finishers=self._safe_int(roster_db.get('clinical_finishers'), 0),
            squad_size_analyzed=self._safe_int(roster_db.get('squad_size_analyzed'), 0),
            goalkeeper_name=goalkeeper.get('name', 'Unknown'),
            goalkeeper_save_rate=self._safe_float(goalkeeper.get('save_rate'), 0.0),
            keeper_overperformance=self._safe_float(nemesis_db.get('keeper_overperformance'), 0.0),
            keeper_status=keeper_status
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 9: PhysicalDNA (15 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_physical_dna(self, merged: Dict) -> PhysicalDNA:
        """Convertit les données physiques vers PhysicalDNA."""
        physical_db = self._safe_parse_json(merged.get('physical_dna'))
        fbref = merged.get('fbref', {})
        defense = merged.get('defense', {})
        
        return PhysicalDNA(
            pressing_intensity=self._safe_float(physical_db.get('pressing_intensity'), 5.0),
            late_game_xg_avg=self._safe_float(physical_db.get('late_game_xg_avg'), 0.0),
            late_game_dominance=self._safe_float(physical_db.get('late_game_dominance'), 50.0),
            estimated_rotation_index=self._safe_float(physical_db.get('estimated_rotation_index'), 50.0),
            aerial_win_pct=self._safe_float(fbref.get('aerial_win_pct'), 50.0),
            possession_pct=self._safe_float(fbref.get('possession_pct'), 50.0),
            tackles_total=self._safe_int(fbref.get('tackles_total'), 0),
            tackles_att_3rd=self._safe_int(fbref.get('tackles_att_3rd'), 0),
            tackles_mid_3rd=self._safe_int(fbref.get('tackles_mid_3rd'), 0),
            tackles_def_3rd=self._safe_int(fbref.get('tackles_def_3rd'), 0),
            progressive_passes=self._safe_float(fbref.get('progressive_passes'), 0.0),
            resist_late=self._safe_float(defense.get('resist_late'), 50.0),
            xga_late_pct=self._safe_float(defense.get('xga_late_pct'), 0.0),
            xga_1h_pct=self._safe_float(defense.get('xga_1h_pct'), 50.0),
            xga_2h_pct=self._safe_float(defense.get('xga_2h_pct'), 50.0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 10: LuckDNA (13 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_luck_dna(self, merged: Dict) -> LuckDNA:
        """Convertit les données de chance vers LuckDNA."""
        luck_db = self._safe_parse_json(merged.get('luck_dna'))
        ctx_json = merged.get('context_json', {})
        variance = ctx_json.get('variance', {})
        record = ctx_json.get('record', {})
        
        unlucky_pct = self._safe_float(merged.get('unlucky_pct'), 0.0)
        actual_points = self._safe_int(record.get('points'), 0)
        xpoints_delta = self._safe_float(luck_db.get('xpoints_delta'), 0.0)
        expected_points = actual_points - xpoints_delta
        
        total_luck = self._safe_float(luck_db.get('total_luck'), 0.0)
        regression_direction = "UP" if total_luck < 0 else "DOWN"
        regression_magnitude = abs(total_luck)
        
        return LuckDNA(
            total_luck=total_luck,
            xpoints_delta=xpoints_delta,
            defensive_luck=self._safe_float(luck_db.get('defensive_luck'), 0.0),
            finishing_luck=self._safe_float(luck_db.get('finishing_luck'), 0.0),
            ppg_vs_expected=self._safe_float(luck_db.get('ppg_vs_expected'), 0.0),
            unlucky_pct=unlucky_pct,
            luck_index=self._safe_float(variance.get('luck_index'), 0.0),
            xg_overperformance=self._safe_float(variance.get('xg_overperformance'), 0.0),
            xga_overperformance=self._safe_float(variance.get('xga_overperformance'), 0.0),
            actual_points=actual_points,
            expected_points=expected_points,
            regression_direction=regression_direction,
            regression_magnitude=regression_magnitude
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 11: ChameleonDNA (14 champs)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _convert_chameleon_dna(self, merged: Dict) -> ChameleonDNA:
        """Convertit les données d'adaptabilité vers ChameleonDNA."""
        chameleon_db = self._safe_parse_json(merged.get('chameleon_dna'))
        tactical_db = self._safe_parse_json(merged.get('tactical_dna'))
        shooting_db = self._safe_parse_json(merged.get('shooting_dna'))
        
        # Si shooting_dna n'existe pas, chercher dans merged directement
        if not shooting_db:
            shooting_db = merged.get('shooting_dna', {})
            if isinstance(shooting_db, str):
                shooting_db = self._safe_parse_json(shooting_db)
        
        # tactical peut aussi être dans merged.tactical_dna
        if not tactical_db:
            tactical_db = merged.get('tactical_dna', {})
            if isinstance(tactical_db, str):
                tactical_db = self._safe_parse_json(tactical_db)
        
        return ChameleonDNA(
            adaptability_index=self._safe_float(chameleon_db.get('adaptability_index'), 50.0),
            comeback_ability=self._safe_float(chameleon_db.get('comeback_ability'), 0.0),
            tempo_flexibility=self._safe_float(chameleon_db.get('tempo_flexibility'), 50.0),
            formation_volatility=self._safe_float(chameleon_db.get('formation_volatility'), 10.0),
            lead_protection_score=self._safe_float(chameleon_db.get('lead_protection_score'), 50.0),
            formation_stability=self._safe_float(tactical_db.get('formation_stability'), 0.5),
            box_shot_ratio=self._safe_float(tactical_db.get('box_shot_ratio'), 0.5),
            open_play_reliance=self._safe_float(tactical_db.get('open_play_reliance'), 50.0),
            set_piece_threat=self._safe_float(tactical_db.get('set_piece_threat'), 10.0),
            long_range_threat=self._safe_float(tactical_db.get('long_range_threat'), 10.0),
            main_formation=tactical_db.get('main_formation', '4-4-2'),
            shots_per_game=self._safe_float(shooting_db.get('shots_per_game'), 10.0),
            sot_per_game=self._safe_float(shooting_db.get('sot_per_game'), 3.0),
            shot_accuracy=self._safe_float(shooting_db.get('shot_accuracy'), 30.0)
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTEUR 12: MICROSTRATEGY DNA
    # ═══════════════════════════════════════════════════════════════════════════

    def _convert_microstrategy_dna(self, merged: Dict, team_name: str = None) -> 'MicroStrategyDNA':
        """
        Convertit les données MicroStrategy depuis le loader dédié.
        
        Note: Les données complètes (126 marchés) sont dans microstrategy_dna.json
        Cette méthode crée un résumé pour la dataclass.
        """
        from quantum.loaders.microstrategy_loader import get_microstrategy_loader, MicroStrategyDNA as LoaderMicroDNA
        from quantum.orchestrator.dataclasses_v2 import MicroStrategyDNA
        
        try:
            loader = get_microstrategy_loader()
            name = team_name or merged.get('team_name', 'Unknown')
            micro_profile = loader.get_team(name)
            
            if not micro_profile:
                logger.warning(f"No MicroStrategy profile found for {name}")
                return MicroStrategyDNA(has_full_profile=False)
            
            # Extraire les résumés
            home_specs = micro_profile.home_specialists
            away_specs = micro_profile.away_specialists
            
            return MicroStrategyDNA(
                sample_size=micro_profile.sample_size,
                home_matches=micro_profile.home_matches,
                away_matches=micro_profile.away_matches,
                data_quality=min(1.0, micro_profile.sample_size / 20),
                last_updated=micro_profile.last_updated,
                home_specialists_count=len(home_specs),
                away_specialists_count=len(away_specs),
                universal_specialists_count=0,  # Calculé si besoin
                top_home_market=home_specs[0]['market'] if home_specs else None,
                top_home_edge=home_specs[0]['edge'] if home_specs else 0.0,
                top_away_market=away_specs[0]['market'] if away_specs else None,
                top_away_edge=away_specs[0]['edge'] if away_specs else 0.0,
                fade_home_count=len(micro_profile.fade_markets_home),
                fade_away_count=len(micro_profile.fade_markets_away),
                has_full_profile=True
            )
            
        except Exception as e:
            logger.error(f"Error converting MicroStrategy DNA: {e}")
            return MicroStrategyDNA(has_full_profile=False)

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE: convert
    # ═══════════════════════════════════════════════════════════════════════════
    
    def convert(self, merged: Dict, team_name: str = None) -> TeamDNA:
        """
        Convertit le dict merged complet vers TeamDNA V2.
        
        Args:
            merged: Dict fusionné de HybridDNALoader
            team_name: Nom de l'équipe (optionnel)
        
        Returns:
            TeamDNA avec les 12 vecteurs peuplés
        """
        name = team_name or merged.get('team_name', 'Unknown')
        
        logger.info(f"Converting DNA for {name}")
        
        team_dna = TeamDNA(
            team_name=name,
            team_id=self._safe_int(merged.get('team_id')),
            league=merged.get('league'),
            season=merged.get('season'),
            tier_rank=self._safe_int(merged.get('tier_rank'), 50),
            style_confidence=self._safe_int(merged.get('style_confidence'), 50),
            unlucky_pct=self._safe_float(merged.get('unlucky_pct'), 0.0),
            market=self._convert_market_dna(merged),
            context=self._convert_context_dna(merged),
            risk=self._convert_risk_dna(merged),
            temporal=self._convert_temporal_dna(merged),
            nemesis=self._convert_nemesis_dna(merged),
            psyche=self._convert_psyche_dna(merged),
            sentiment=self._convert_sentiment_dna(merged),
            roster=self._convert_roster_dna(merged),
            physical=self._convert_physical_dna(merged),
            luck=self._convert_luck_dna(merged),
            chameleon=self._convert_chameleon_dna(merged),
            microstrategy=self._convert_microstrategy_dna(merged, name),
            dna_fingerprint=merged.get('dna_fingerprint'),
            created_at=merged.get('created_at'),
            updated_at=merged.get('updated_at')
        )
        
        logger.info(f"DNA conversion complete for {name}")
        return team_dna


# ═══════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════
CONVERTER_VERSION = "2.0"

"""
Service d'alertes pour Mon_PS
"""

from api.services.logging import logger


class AlertService:
    """Service pour gérer les alertes critiques du système"""

    @staticmethod
    def check_slow_query(request_id: str, endpoint: str, duration_ms: float, threshold_ms: float = 100):
        """Alerte si requête lente"""
        if duration_ms > threshold_ms:
            logger.warning(
                "performance_alert_slow_query",
                request_id=request_id,
                endpoint=endpoint,
                duration_ms=duration_ms,
                threshold_ms=threshold_ms,
                severity="warning",
            )

    @staticmethod
    def check_empty_results(request_id: str, endpoint: str, filters: dict):
        """Alerte si aucun résultat avec des filtres valides"""
        logger.warning(
            "data_alert_empty_results",
            request_id=request_id,
            endpoint=endpoint,
            filters=filters,
            severity="info",
            suggestion="Check data freshness or adjust filters",
        )

    @staticmethod
    def check_high_edge_opportunity(request_id: str, opportunity: dict):
        """Alerte pour opportunité à forte edge"""
        if opportunity['edge_pct'] > 15:
            logger.info(
                "business_alert_high_edge",
                request_id=request_id,
                match_id=opportunity['match_id'],
                edge_pct=opportunity['edge_pct'],
                bookmaker=opportunity['bookmaker'],
                severity="high",
                action_required="Consider placing bet",
            )

    @staticmethod
    def check_negative_clv(request_id: str, clv_rolling: float, recent_clvs: list):
        """Alerte si CLV négatif"""
        if clv_rolling < 0:
            logger.error(
                "business_alert_negative_clv",
                request_id=request_id,
                clv_rolling_100=clv_rolling,
                recent_clvs=recent_clvs[-10:],
                severity="critical",
                action_required="Stop betting - Review strategy",
            )

    @staticmethod
    def check_bankroll_drawdown(request_id: str, bankroll_current: float, bankroll_peak: float, threshold: float = 0.18):
        """Alerte si drawdown trop important"""
        drawdown = (bankroll_peak - bankroll_current) / bankroll_peak

        if drawdown > threshold:
            logger.error(
                "business_alert_bankroll_drawdown",
                request_id=request_id,
                bankroll_current=bankroll_current,
                bankroll_peak=bankroll_peak,
                drawdown_pct=round(drawdown * 100, 2),
                threshold_pct=threshold * 100,
                kill_switch_activated=True,
                severity="critical",
                action_required="STOP ALL BETTING - Kill-Switch activated",
            )
        elif drawdown > 0.10:
            logger.warning(
                "business_alert_bankroll_warning",
                request_id=request_id,
                bankroll_current=bankroll_current,
                bankroll_peak=bankroll_peak,
                drawdown_pct=round(drawdown * 100, 2),
                severity="warning",
                action_required="Reduce stake sizes",
            )


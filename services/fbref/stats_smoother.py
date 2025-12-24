"""
Stats Smoother - Lissage Bayésien (PAD Method)
═══════════════════════════════════════════════════════════════════════════
Stabilise les stats per90 des joueurs avec peu de minutes.
Approche Hedge Fund Grade - Standard industrie.
═══════════════════════════════════════════════════════════════════════════

FORMULE:
Stat_Lissée = (Actions_Réelles + Prior) / (Minutes_Réelles + Padding) × 90
où Prior = (Moyenne_Ligue / 90) × Padding

AUTEUR: Mon_PS Team
DATE: 2025-12-24
VERSION: 1.0.0
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("StatsSmoother")


@dataclass
class LeagueAverages:
    """Moyennes par ligue pour le lissage."""
    shots_90: float
    xg_90: float
    xg_assist_90: float = 0.0

    def get(self, metric: str) -> float:
        """Récupère la moyenne pour une métrique."""
        return getattr(self, metric, 0.0)


class StatsSmoother:
    """
    Lissage Bayésien des stats per90.

    Principe: Les joueurs avec peu de minutes sont "ancrés"
    à la moyenne de leur ligue. Plus ils jouent, plus leurs
    stats réelles dominent.

    Usage:
        smoother = StatsSmoother()
        smoother.load_league_averages()  # Charge depuis PostgreSQL

        smoothed = smoother.get_smoothed_rate(
            real_count=2,      # 2 tirs
            real_minutes=9,    # 9 minutes jouées
            metric="shots_90",
            league="Serie_A"
        )
        # Retourne ~11.2 au lieu de 30.0 (brut)
    """

    # Padding par défaut (300 min = ~3.3 matchs)
    DEFAULT_PADDING = 300.0

    # Minimum de minutes pour calculer moyenne fiable
    MIN_MINUTES_FOR_AVERAGE = 450.0  # 5 matchs

    def __init__(
        self,
        padding_minutes: float = None,
        db_config: Dict = None
    ):
        self.padding = padding_minutes or self.DEFAULT_PADDING
        self.league_averages: Dict[str, LeagueAverages] = {}

        # Config DB
        self.db_config = db_config or {
            "host": "localhost",
            "port": 5432,
            "dbname": "monps_db",
            "user": "monps_user",
            "password": "monps_secure_password_2024"
        }

    def load_league_averages(self) -> bool:
        """
        Charge les moyennes par ligue depuis PostgreSQL.

        Returns:
            True si chargement réussi, False sinon
        """
        logger.info("📊 Loading league averages from PostgreSQL...")

        query = """
            SELECT
                league,
                COALESCE(AVG(shots_90), 10.0) as avg_shots_90,
                COALESCE(AVG(xg_90), 1.0) as avg_xg_90,
                COUNT(*) as nb_players
            FROM fbref_player_stats_full
            WHERE minutes_90 >= %s
              AND shots_90 IS NOT NULL
              AND xg_90 IS NOT NULL
            GROUP BY league
            ORDER BY league
        """

        try:
            conn = psycopg2.connect(**self.db_config)

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (self.MIN_MINUTES_FOR_AVERAGE / 90,))
                rows = cur.fetchall()

            conn.close()

            # Parser les résultats
            for row in rows:
                league = row["league"]
                self.league_averages[league] = LeagueAverages(
                    shots_90=float(row["avg_shots_90"]),
                    xg_90=float(row["avg_xg_90"])
                )
                logger.debug(
                    f"  {league}: shots_90={row['avg_shots_90']:.2f}, "
                    f"xg_90={row['avg_xg_90']:.2f} ({row['nb_players']} players)"
                )

            logger.info(f"✅ Loaded averages for {len(self.league_averages)} leagues")
            return True

        except psycopg2.Error as e:
            logger.error(f"❌ Database error: {e}")
            return False

    def get_smoothed_rate(
        self,
        real_count: float,
        real_minutes: float,
        metric: str,
        league: str
    ) -> float:
        """
        Calcule la stat lissée (Bayesian smoothing).

        Args:
            real_count: Nombre d'actions réelles (ex: 2 tirs)
            real_minutes: Minutes réelles jouées (ex: 9)
            metric: Nom de la métrique (ex: "shots_90")
            league: Ligue du joueur (ex: "Serie_A")

        Returns:
            Stat per90 lissée
        """
        # Récupérer moyenne de la ligue
        league_avg = self.league_averages.get(league)
        if league_avg is None:
            # Fallback: moyenne globale
            avg_rate = 10.0 if "shots" in metric else 1.0
        else:
            avg_rate = league_avg.get(metric.replace("_90", "_90"))

        # Calculer le Prior (actions théoriques pendant le padding)
        # Prior = (moyenne_per90 / 90) × padding_minutes
        prior_count = (avg_rate / 90.0) * self.padding

        # Bayesian update
        numerator = real_count + prior_count
        denominator = real_minutes + self.padding

        # Normaliser sur 90 minutes
        if denominator <= 0:
            return avg_rate  # Fallback si 0 minutes

        smoothed = (numerator / denominator) * 90.0

        return round(smoothed, 2)

    def smooth_player_stats(
        self,
        player: Dict,
        metrics: list = None
    ) -> Dict:
        """
        Lisse toutes les stats d'un joueur.

        Args:
            player: Dict avec les stats du joueur
            metrics: Liste des métriques à lisser (défaut: shots_90, xg_90)

        Returns:
            Dict avec les stats lissées ajoutées (suffixe _smoothed)
        """
        if metrics is None:
            metrics = ["shots_90", "xg_90"]

        league = player.get("league", "EPL")
        minutes = player.get("minutes_90", 0) * 90  # Convertir en minutes

        result = player.copy()

        for metric in metrics:
            raw_value = player.get(metric)
            if raw_value is None:
                continue

            # Calculer le count réel depuis la stat per90
            # real_count = (raw_per90 / 90) × minutes
            real_count = (float(raw_value) / 90.0) * minutes

            smoothed = self.get_smoothed_rate(
                real_count=real_count,
                real_minutes=minutes,
                metric=metric,
                league=league
            )

            # Ajouter avec suffixe
            result[f"{metric}_smoothed"] = smoothed

        return result


# === FALLBACK AVERAGES ===
# Utilisées si PostgreSQL indisponible
FALLBACK_AVERAGES = {
    "EPL": LeagueAverages(shots_90=11.0, xg_90=1.1),
    "La_Liga": LeagueAverages(shots_90=10.5, xg_90=1.0),
    "Bundesliga": LeagueAverages(shots_90=11.5, xg_90=1.15),
    "Serie_A": LeagueAverages(shots_90=10.8, xg_90=1.05),
    "Ligue_1": LeagueAverages(shots_90=10.2, xg_90=0.95)
}


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    smoother = StatsSmoother(padding_minutes=300.0)

    if smoother.load_league_averages():
        # Test sur Yellu Santiago (9 min, 2 tirs)
        smoothed = smoother.get_smoothed_rate(
            real_count=2,
            real_minutes=9,
            metric="shots_90",
            league="Serie_A"
        )

        raw = (2 / 9) * 90  # 20.0

        print("="*60)
        print("TEST LISSAGE BAYÉSIEN")
        print("="*60)
        print(f"Yellu Santiago (9 min, 2 tirs)")
        print(f"  Stat brute: {raw:.1f} shots/90")
        print(f"  Stat lissée: {smoothed:.1f} shots/90")
        print(f"  Réduction: {raw - smoothed:.1f} points")
        print("="*60)

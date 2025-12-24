"""
Models Match Context Calculator
═══════════════════════════════════════════════════════════════════════════
Dataclasses pour représenter les analyses de repos.
═══════════════════════════════════════════════════════════════════════════
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RestAnalysis:
    """
    Analyse de repos d'une équipe.

    Contient le repos brut et l'index effectif après ajustements.
    """
    team: str
    raw_days: int                          # Jours bruts depuis dernier match
    prev_match_date: Optional[datetime]    # Date du dernier match
    prev_venue: str                        # 'Home' ou 'Away'
    prev_competition: str                  # 'Premier League', 'Champions League', etc.

    # Ajustements
    venue_adjustment: float                # Bonus/malus venue
    competition_adjustment: float          # Bonus rotation coupe

    # Résultats
    effective_rest_index: float            # Score final
    status: str                            # FRESH/NORMAL/TIRED/CRITICAL/RUSTY

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour insertion DB."""
        return {
            'team': self.team,
            'raw_days': self.raw_days,
            'prev_match_date': self.prev_match_date.isoformat() if self.prev_match_date else None,
            'prev_venue': self.prev_venue,
            'prev_competition': self.prev_competition,
            'venue_adjustment': self.venue_adjustment,
            'competition_adjustment': self.competition_adjustment,
            'effective_rest': self.effective_rest_index,
            'status': self.status
        }

    def __str__(self) -> str:
        return (
            f"{self.team}: {self.raw_days}d brut → {self.effective_rest_index}d effectif "
            f"[{self.status}] (venue: {self.prev_venue})"
        )


@dataclass
class MatchRestComparison:
    """
    Comparaison de repos entre 2 équipes pour un match.

    Calcule l'avantage de repos et sa significativité.
    """
    match_id: str
    match_date: datetime
    home_team: str
    away_team: str

    # Analyses individuelles
    home_rest: RestAnalysis
    away_rest: RestAnalysis

    # Comparaison
    delta: float                   # home_effective - away_effective
    advantage: str                 # 'home', 'away', 'neutral'
    significance: str              # 'minor', 'moderate', 'major'

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour insertion DB."""
        return {
            'match_id': self.match_id,
            'match_date': self.match_date.isoformat() if self.match_date else None,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'home_raw_rest_days': self.home_rest.raw_days,
            'away_raw_rest_days': self.away_rest.raw_days,
            'home_effective_rest': self.home_rest.effective_rest_index,
            'away_effective_rest': self.away_rest.effective_rest_index,
            'rest_delta': self.delta,
            'home_returning_from': self.home_rest.prev_venue,
            'away_returning_from': self.away_rest.prev_venue,
            'home_rest_status': self.home_rest.status,
            'away_rest_status': self.away_rest.status,
            'advantage': self.advantage,
            'significance': self.significance
        }

    def __str__(self) -> str:
        return (
            f"{self.home_team} vs {self.away_team}: "
            f"Delta={self.delta:+.1f}d → {self.advantage.upper()} advantage ({self.significance})"
        )

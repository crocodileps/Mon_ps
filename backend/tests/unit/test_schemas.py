"""Tests unitaires pour les schemas Pydantic"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from decimal import Decimal
from api.models.schemas import BetCreate, BetUpdate


class TestBetCreate:
    """Tests pour BetCreate schema"""
    
    def test_bet_create_valid(self):
        """Test création pari valide"""
        bet = BetCreate(
            match_id="test_123",
            outcome="Home",
            bookmaker="Bet365",
            odds_value=Decimal("2.50"),
            stake=Decimal("10.00"),
            bet_type="value"
        )
        assert bet.match_id == "test_123"
        assert bet.stake == Decimal("10.00")

    def test_bet_create_with_notes(self):
        """Test création pari avec notes"""
        bet = BetCreate(
            match_id="match_456",
            outcome="Away",
            bookmaker="William Hill",
            odds_value=Decimal("3.00"),
            stake=Decimal("50.00"),
            bet_type="arbitrage",
            notes="Test arbitrage"
        )
        assert bet.notes == "Test arbitrage"


class TestBetUpdate:
    """Tests pour BetUpdate schema"""
    
    def test_bet_update_won(self):
        """Test mise à jour pari gagné"""
        update = BetUpdate(result="won", actual_odds=Decimal("2.50"))
        assert update.result == "won"

    def test_bet_update_lost(self):
        """Test mise à jour pari perdu"""
        update = BetUpdate(result="lost")
        assert update.result == "lost"

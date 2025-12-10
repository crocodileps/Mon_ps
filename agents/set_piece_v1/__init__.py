"""
🎯 SET_PIECE Agent V1
Quantitative edge detection for corner/header/set piece markets.

Usage:
    from agents.set_piece_v1 import SetPieceAgent
    
    agent = SetPieceAgent()
    result = agent.analyze("Liverpool", "Man City")
"""
from .agent import SetPieceAgent, SetPieceSignal, SignalStrength, MarketType

__version__ = "1.0"
__all__ = ['SetPieceAgent', 'SetPieceSignal', 'SignalStrength', 'MarketType']

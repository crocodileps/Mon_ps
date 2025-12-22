#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🧬 MICROSTRATEGY DNA LOADER V1.0
   12ème Vecteur du Quantum Orchestrator
   
   Charge et expose les données MicroStrategy pour utilisation
   par les autres composants du système.
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

MICROSTRATEGY_PATH = '/home/Mon_ps/data/quantum_v2/microstrategy_dna.json'


@dataclass
class MarketSignal:
    """Signal pour un marché spécifique"""
    market: str
    edge: float
    hit_rate: float
    baseline: float
    sample: int
    confidence: str
    signal: str
    
    @property
    def is_actionable(self) -> bool:
        return self.confidence in ["HIGH", "MEDIUM"] and abs(self.edge) >= 10


@dataclass
class MicroStrategyDNA:
    """12ème vecteur DNA - Profil MicroStrategy d'une équipe"""
    team: str
    sample_size: int
    home_matches: int
    away_matches: int
    last_updated: str
    home_specialists: List[Dict]
    away_specialists: List[Dict]
    fade_markets_home: List[Dict]
    fade_markets_away: List[Dict]
    all_markets_home: Dict[str, Dict]
    all_markets_away: Dict[str, Dict]
    
    def get_market_signal(self, market: str, venue: str = "HOME") -> Optional[MarketSignal]:
        """Récupère le signal pour un marché spécifique"""
        markets = self.all_markets_home if venue.upper() == "HOME" else self.all_markets_away
        if market not in markets:
            return None
        m = markets[market]
        return MarketSignal(
            market=market, edge=m['edge'], hit_rate=m['hit_rate'],
            baseline=m['baseline'], sample=m['sample'],
            confidence=m['confidence'], signal=m['signal']
        )
    
    def get_top_specialists(self, venue: str = "HOME", limit: int = 5) -> List[MarketSignal]:
        """Retourne les top marchés spécialistes"""
        specialists = self.home_specialists if venue.upper() == "HOME" else self.away_specialists
        return [
            MarketSignal(
                market=s['market'], edge=s['edge'], hit_rate=s['hit_rate'],
                baseline=s['baseline'], sample=s['sample'],
                confidence=s['confidence'], signal=s['signal']
            )
            for s in specialists[:limit]
        ]
    
    def should_bet(self, market: str, venue: str = "HOME") -> Dict[str, Any]:
        """Décision de pari basée sur MicroStrategy"""
        signal = self.get_market_signal(market, venue)
        if not signal:
            return {"recommendation": "SKIP", "edge": 0, "confidence": "NONE",
                    "reasoning": f"Marché {market} non disponible"}
        
        if signal.signal == "STRONG_BACK" and signal.confidence in ["HIGH", "MEDIUM"]:
            return {"recommendation": "STRONG_BET", "edge": signal.edge,
                    "confidence": signal.confidence,
                    "reasoning": f"Spécialiste {market}: +{signal.edge:.1f}% edge"}
        elif signal.signal == "BACK" and signal.confidence in ["HIGH", "MEDIUM"]:
            return {"recommendation": "BET", "edge": signal.edge,
                    "confidence": signal.confidence,
                    "reasoning": f"Favorable {market}: +{signal.edge:.1f}% edge"}
        elif signal.signal in ["STRONG_FADE", "FADE"]:
            return {"recommendation": "FADE", "edge": signal.edge,
                    "confidence": signal.confidence,
                    "reasoning": f"À éviter {market}: {signal.edge:.1f}% edge"}
        return {"recommendation": "NEUTRAL", "edge": signal.edge,
                "confidence": signal.confidence, "reasoning": "Signal neutre"}


class MicroStrategyLoader:
    """Loader singleton pour MicroStrategy DNA"""
    
    def __init__(self, path: str = MICROSTRATEGY_PATH):
        self.path = path
        self._data: Optional[Dict] = None
        self._last_load: Optional[datetime] = None
        self._cache: Dict[str, MicroStrategyDNA] = {}
    
    def _load(self, force: bool = False) -> bool:
        if not force and self._data is not None:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(self.path))
            if self._last_load and file_mtime <= self._last_load:
                return True
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            self._last_load = datetime.now()
            self._cache.clear()
            logger.info(f"MicroStrategy DNA chargé: {len(self._data.get('teams', {}))} équipes")
            return True
        except Exception as e:
            logger.error(f"Erreur chargement: {e}")
            return False
    
    def get_metadata(self) -> Dict[str, Any]:
        self._load()
        return self._data.get('metadata', {}) if self._data else {}
    
    def get_team(self, team_name: str) -> Optional[MicroStrategyDNA]:
        """Récupère le profil MicroStrategy d'une équipe"""
        self._load()
        if not self._data:
            return None
        
        cache_key = team_name.lower()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        teams = self._data.get('teams', {})
        team_data = None
        
        # Recherche exacte puis partielle
        for name, data in teams.items():
            if name.lower() == team_name.lower():
                team_data = data
                break
        if not team_data:
            for name, data in teams.items():
                if team_name.lower() in name.lower():
                    team_data = data
                    break
        
        if not team_data:
            return None
        
        meta = team_data.get('meta', {})
        dna = MicroStrategyDNA(
            team=meta.get('team', team_name),
            sample_size=meta.get('sample_size', 0),
            home_matches=meta.get('home_matches', 0),
            away_matches=meta.get('away_matches', 0),
            last_updated=meta.get('last_updated', ''),
            home_specialists=team_data.get('home_specialists', []),
            away_specialists=team_data.get('away_specialists', []),
            fade_markets_home=team_data.get('fade_markets_home', []),
            fade_markets_away=team_data.get('fade_markets_away', []),
            all_markets_home=team_data.get('all_markets_home', {}),
            all_markets_away=team_data.get('all_markets_away', {})
        )
        self._cache[cache_key] = dna
        return dna
    
    def get_matchup_signals(self, home_team: str, away_team: str, market: str) -> Dict[str, Any]:
        """Analyse un match pour un marché - combine HOME et AWAY"""
        home_dna = self.get_team(home_team)
        away_dna = self.get_team(away_team)
        
        result = {
            "market": market, "home_team": home_team, "away_team": away_team,
            "home_signal": None, "away_signal": None,
            "combined_recommendation": "NEUTRAL", "combined_edge": 0, "reasoning": []
        }
        
        if home_dna:
            home_decision = home_dna.should_bet(market, "HOME")
            result["home_signal"] = home_decision
            result["reasoning"].append(f"HOME: {home_decision['reasoning']}")
        
        if away_dna:
            away_decision = away_dna.should_bet(market, "AWAY")
            result["away_signal"] = away_decision
            result["reasoning"].append(f"AWAY: {away_decision['reasoning']}")
        
        if result["home_signal"] and result["away_signal"]:
            home_edge = result["home_signal"]["edge"]
            away_edge = result["away_signal"]["edge"]
            combined_edge = (home_edge * 0.6) + (away_edge * 0.4)
            result["combined_edge"] = round(combined_edge, 1)
            
            if combined_edge >= 15:
                result["combined_recommendation"] = "STRONG_BET"
            elif combined_edge >= 8:
                result["combined_recommendation"] = "BET"
            elif combined_edge <= -15:
                result["combined_recommendation"] = "STRONG_FADE"
            elif combined_edge <= -8:
                result["combined_recommendation"] = "FADE"
        
        return result
    
    def list_teams(self) -> List[str]:
        self._load()
        return list(self._data.get('teams', {}).keys()) if self._data else []


# Singleton
_loader_instance: Optional[MicroStrategyLoader] = None

def get_microstrategy_loader() -> MicroStrategyLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = MicroStrategyLoader()
    return _loader_instance


if __name__ == "__main__":
    print("=" * 80)
    print("🧬 MICROSTRATEGY LOADER - TEST")
    print("=" * 80)
    
    loader = MicroStrategyLoader()
    meta = loader.get_metadata()
    print(f"\n📊 Metadata: {meta.get('teams_count')} équipes, v{meta.get('version')}")
    
    print(f"\n{'=' * 80}")
    print("📋 TEST: LIVERPOOL")
    print("=" * 80)
    
    liv = loader.get_team("Liverpool")
    if liv:
        print(f"   Matchs: {liv.sample_size} (H:{liv.home_matches}, A:{liv.away_matches})")
        print(f"\n   🏠 TOP 5 HOME:")
        for i, s in enumerate(liv.get_top_specialists("HOME", 5)):
            print(f"      {i+1}. {s.market}: edge={s.edge:+.1f}%, HR={s.hit_rate:.1f}%")
        print(f"\n   ✈️ TOP 5 AWAY:")
        for i, s in enumerate(liv.get_top_specialists("AWAY", 5)):
            print(f"      {i+1}. {s.market}: edge={s.edge:+.1f}%, HR={s.hit_rate:.1f}%")
    
    print(f"\n{'=' * 80}")
    print("📋 TEST MATCHUP: Liverpool vs Arsenal (btts_yes)")
    print("=" * 80)
    matchup = loader.get_matchup_signals("Liverpool", "Arsenal", "btts_yes")
    print(f"   Combined Edge: {matchup['combined_edge']:+.1f}%")
    print(f"   Recommendation: {matchup['combined_recommendation']}")
    
    print(f"\n✅ Loader fonctionnel!")

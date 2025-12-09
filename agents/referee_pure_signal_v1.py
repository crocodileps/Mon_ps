#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    REFEREE PURE SIGNAL MODULE V1.0                           ║
║                                                                              ║
║  Philosophie: "Si ce n'est pas prouvé statistiquement, c'est du bruit"       ║
║                                                                              ║
║  Signaux VALIDÉS (r > 0.9, p < 0.001):                                       ║
║    ✅ card_impact (effet additif sur total cartons)                          ║
║    ✅ card_trigger_rate (effet multiplicatif avec style équipes)             ║
║                                                                              ║
║  Signaux REJETÉS (r < 0.1, non significatifs):                               ║
║    ❌ home_bias (r = 0.047 avec win rate)                                    ║
║    ❌ big_team_bias (corrélation non prouvée)                                ║
║    ❌ nemesis_teams (n < 15 matchs par paire = bruit statistique)            ║
║                                                                              ║
║  Source: /home/Mon_ps/data/referee_dna_hedge_fund_v4.json (48 arbitres)      ║
║  Auteur: Mya × Claude | Date: 2025-01-10                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import math
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RefereePureSignal")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES VALIDÉES STATISTIQUEMENT (basées sur 4660 matchs)
# ═══════════════════════════════════════════════════════════════════════════════

LEAGUE_AVG_CARDS = 3.89
LEAGUE_AVG_FOULS = 21.4
LEAGUE_AVG_TRIGGER_RATE = 16.5  # card_trigger_rate moyen (%)

MIN_MATCHES_REFEREE = 50  # CLT applicable
HIGH_CONFIDENCE_MATCHES = 100

DATA_DIR = Path("/home/Mon_ps/data")
REFEREE_DNA_PATH = DATA_DIR / "referee_dna_hedge_fund_v4.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RefereeProfile:
    """Profil arbitre avec signaux validés uniquement"""
    name: str
    matches: int
    card_impact: float          # Signal #1: effet additif (validé r=0.931)
    trigger_rate: float         # Signal #2: card_trigger_rate (%)
    avg_cards: float            # Moyenne brute cartons
    confidence: float           # Pondération basée sur sample size
    strictness: str             # LENIENT / STRICT / NEUTRAL (du fichier)
    style: str                  # LAISSE_JOUER / CASSE_RYTHME etc.
    over_35_pct: float          # % matchs avec >3.5 cartons
    over_45_pct: float          # % matchs avec >4.5 cartons
    
    def __repr__(self):
        return f"Referee({self.name}: impact={self.card_impact:+.2f}, trigger={self.trigger_rate:.1f}%, {self.strictness})"


@dataclass
class CardProjection:
    """Projection de cartons pour un match"""
    base_expected: float        # Basé sur équipes seules
    referee_adjustment: float   # card_impact × confidence
    style_boost: float          # Effet multiplicatif trigger × fouls
    total_projected: float      # Projection finale
    confidence: float           # Confiance globale
    over_35_prob: float         # P(cards > 3.5)
    over_45_prob: float         # P(cards > 4.5)
    recommendation: str         # OVER_4.5 / UNDER_3.5 / NO_BET


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

class RefereePureSignal:
    """
    Module principal - Signaux arbitres purifiés
    
    Utilise UNIQUEMENT:
    - card_impact (Signal #1 - additif)
    - card_trigger_rate (Signal #2 - multiplicatif)
    
    IGNORE (bruit statistique):
    - home_bias, big_team_bias, nemesis_teams
    
    Usage:
        rps = RefereePureSignal()
        projection = rps.project_cards(
            referee="M Atkinson",
            team_a_avg_cards=1.8,
            team_b_avg_cards=2.1,
            team_a_avg_fouls=11.2,
            team_b_avg_fouls=12.5
        )
    """
    
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or REFEREE_DNA_PATH
        self.referees: Dict[str, RefereeProfile] = {}
        self._load_data()
        
    def _load_data(self):
        """Charge et filtre les données arbitres depuis le fichier réel"""
        try:
            with open(self.data_path, 'r') as f:
                raw_data = json.load(f)
            
            for ref in raw_data:
                name = ref.get('referee_name', '')
                matches = ref.get('matches', 0)
                
                # Filtre: minimum 50 matchs pour CLT
                if matches < MIN_MATCHES_REFEREE:
                    continue
                
                # Calcul confidence basée sur sample size
                confidence = min(1.0, matches / HIGH_CONFIDENCE_MATCHES)
                
                # Extraction des VRAIES clés du fichier
                self.referees[name] = RefereeProfile(
                    name=name,
                    matches=matches,
                    card_impact=ref.get('card_impact', 0),
                    trigger_rate=ref.get('card_trigger_rate', LEAGUE_AVG_TRIGGER_RATE),
                    avg_cards=ref.get('avg_cards', LEAGUE_AVG_CARDS),
                    confidence=confidence,
                    strictness=ref.get('strictness', 'NEUTRAL'),
                    style=ref.get('style', 'EQUILIBRE'),
                    over_35_pct=ref.get('over_35_pct', 50),
                    over_45_pct=ref.get('over_45_pct', 25)
                )
            
            logger.info(f"✅ Chargé {len(self.referees)} arbitres validés (≥{MIN_MATCHES_REFEREE} matchs)")
            
        except FileNotFoundError:
            logger.error(f"❌ Fichier non trouvé: {self.data_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur JSON: {e}")
            raise
    
    def get_referee(self, name: str) -> Optional[RefereeProfile]:
        """Récupère le profil d'un arbitre (recherche exacte puis partielle)"""
        if name in self.referees:
            return self.referees[name]
        
        # Recherche partielle (ex: "Atkinson" -> "M Atkinson")
        for ref_name, profile in self.referees.items():
            if name.lower() in ref_name.lower():
                return profile
        
        return None
    
    def project_cards(
        self,
        referee: str,
        team_a_avg_cards: float,
        team_b_avg_cards: float,
        team_a_avg_fouls: float = 10.7,
        team_b_avg_fouls: float = 10.7,
        match_importance: float = 1.0
    ) -> CardProjection:
        """
        Projette le nombre de cartons pour un match
        
        Formules PURE SIGNAL:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        1. base_expected = team_a_avg + team_b_avg
        2. referee_adjustment = card_impact × confidence
        3. style_boost = total_fouls × (ref_trigger - league_trigger) / 100
        4. total = (base + adjustment + boost) × match_importance
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        ref_profile = self.get_referee(referee)
        
        # Si arbitre inconnu, utiliser baseline (confidence = 0)
        if ref_profile is None:
            logger.warning(f"⚠️ Arbitre '{referee}' non trouvé, utilisation baseline")
            ref_profile = RefereeProfile(
                name="UNKNOWN", matches=0, card_impact=0,
                trigger_rate=LEAGUE_AVG_TRIGGER_RATE, avg_cards=LEAGUE_AVG_CARDS,
                confidence=0, strictness="NEUTRAL", style="EQUILIBRE",
                over_35_pct=50, over_45_pct=25
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # SIGNAL #1: Referee Card Factor (additif)
        # ═══════════════════════════════════════════════════════════════════════
        base_expected = team_a_avg_cards + team_b_avg_cards
        referee_adjustment = ref_profile.card_impact * ref_profile.confidence
        
        # ═══════════════════════════════════════════════════════════════════════
        # SIGNAL #2: Trigger Happy Rate (multiplicatif)
        # ═══════════════════════════════════════════════════════════════════════
        total_fouls = team_a_avg_fouls + team_b_avg_fouls
        # Différence de trigger rate (en %) convertie en cartons supplémentaires
        trigger_diff = (ref_profile.trigger_rate - LEAGUE_AVG_TRIGGER_RATE) / 100
        style_boost = total_fouls * trigger_diff * ref_profile.confidence
        
        # ═══════════════════════════════════════════════════════════════════════
        # TOTAL avec contexte match
        # ═══════════════════════════════════════════════════════════════════════
        total_projected = (base_expected + referee_adjustment + style_boost) * match_importance
        
        # ═══════════════════════════════════════════════════════════════════════
        # PROBABILITÉS (distribution normale, σ ≈ 2.0)
        # ═══════════════════════════════════════════════════════════════════════
        std = 2.0
        
        def normal_cdf(x, mu, sigma):
            return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))
        
        over_35_prob = 1 - normal_cdf(3.5, total_projected, std)
        over_45_prob = 1 - normal_cdf(4.5, total_projected, std)
        
        # Confidence globale
        overall_confidence = ref_profile.confidence * 0.7 + 0.3
        
        # ═══════════════════════════════════════════════════════════════════════
        # RECOMMANDATION
        # ═══════════════════════════════════════════════════════════════════════
        if over_45_prob > 0.55 and ref_profile.strictness == "STRICT":
            recommendation = "OVER_4.5"
        elif over_35_prob < 0.40 and ref_profile.strictness == "LENIENT":
            recommendation = "UNDER_3.5"
        elif over_35_prob > 0.60:
            recommendation = "OVER_3.5"
        elif over_35_prob < 0.35:
            recommendation = "UNDER_3.5"
        else:
            recommendation = "NO_BET"
        
        return CardProjection(
            base_expected=base_expected,
            referee_adjustment=referee_adjustment,
            style_boost=style_boost,
            total_projected=total_projected,
            confidence=overall_confidence,
            over_35_prob=over_35_prob,
            over_45_prob=over_45_prob,
            recommendation=recommendation
        )
    
    def get_strict_referees(self) -> list:
        """Liste les arbitres STRICT (bet OVER)"""
        return sorted(
            [r for r in self.referees.values() if r.strictness == "STRICT"],
            key=lambda x: -x.card_impact
        )
    
    def get_lenient_referees(self) -> list:
        """Liste les arbitres LENIENT (bet UNDER)"""
        return sorted(
            [r for r in self.referees.values() if r.strictness == "LENIENT"],
            key=lambda x: x.card_impact
        )
    
    def print_summary(self):
        """Affiche un résumé des signaux disponibles"""
        print("\n" + "=" * 70)
        print("📊 REFEREE PURE SIGNAL V1.0 - SUMMARY")
        print("=" * 70)
        
        strict = self.get_strict_referees()
        lenient = self.get_lenient_referees()
        neutral = [r for r in self.referees.values() if r.strictness not in ("STRICT", "LENIENT")]
        
        print(f"\n🔴 STRICT ({len(strict)} arbitres) - Bet OVER:")
        for r in strict[:5]:
            print(f"   • {r.name}: +{r.card_impact:.2f} impact, {r.trigger_rate:.1f}% trigger, O4.5={r.over_45_pct:.0f}% ({r.matches}m)")
        
        print(f"\n🟢 LENIENT ({len(lenient)} arbitres) - Bet UNDER:")
        for r in lenient[:5]:
            print(f"   • {r.name}: {r.card_impact:.2f} impact, {r.trigger_rate:.1f}% trigger, O4.5={r.over_45_pct:.0f}% ({r.matches}m)")
        
        print(f"\n⚪ NEUTRAL ({len(neutral)} arbitres) - No edge")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES POUR AGENT DÉFENSE V1.4
# ═══════════════════════════════════════════════════════════════════════════════

def get_referee_features(referee_name: str) -> Dict[str, float]:
    """
    Retourne les features arbitre pour le ML
    
    Usage dans Agent Défense V1.4:
        features = get_referee_features("M Atkinson")
        X['ref_card_impact'] = features['card_impact']
        X['ref_trigger_rate'] = features['trigger_rate']
    """
    rps = RefereePureSignal()
    ref = rps.get_referee(referee_name)
    
    if ref is None:
        return {
            'card_impact': 0,
            'trigger_rate': LEAGUE_AVG_TRIGGER_RATE,
            'confidence': 0,
            'is_strict': 0,
            'is_lenient': 0
        }
    
    return {
        'card_impact': ref.card_impact,
        'trigger_rate': ref.trigger_rate,
        'confidence': ref.confidence,
        'is_strict': 1 if ref.strictness == "STRICT" else 0,
        'is_lenient': 1 if ref.strictness == "LENIENT" else 0
    }


def calculate_card_edge(
    referee: str,
    team_a_cards: float,
    team_b_cards: float,
    team_a_fouls: float,
    team_b_fouls: float,
    bookmaker_line: float = 3.5
) -> Dict[str, float]:
    """
    Calcule l'edge sur les marchés de cartons
    
    Returns:
        projected_cards: Notre projection
        bookmaker_line: Ligne du bookmaker
        edge: Différence (positif = OVER value)
        recommended_bet: "OVER" / "UNDER" / "PASS"
    """
    rps = RefereePureSignal()
    proj = rps.project_cards(
        referee=referee,
        team_a_avg_cards=team_a_cards,
        team_b_avg_cards=team_b_cards,
        team_a_avg_fouls=team_a_fouls,
        team_b_avg_fouls=team_b_fouls
    )
    
    edge = proj.total_projected - bookmaker_line
    
    return {
        'projected_cards': proj.total_projected,
        'bookmaker_line': bookmaker_line,
        'edge': edge,
        'edge_pct': (edge / bookmaker_line) * 100 if bookmaker_line else 0,
        'over_prob': proj.over_35_prob if bookmaker_line == 3.5 else proj.over_45_prob,
        'confidence': proj.confidence,
        'recommended_bet': "OVER" if edge > 0.3 else ("UNDER" if edge < -0.3 else "PASS")
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TEST REFEREE PURE SIGNAL V1.0")
    print("=" * 70)
    
    rps = RefereePureSignal()
    rps.print_summary()
    
    # Test avec arbitre LENIENT
    print("\n" + "=" * 70)
    print("🎯 TEST: Arsenal vs Chelsea avec arbitre LENIENT")
    print("=" * 70)
    
    lenient = rps.get_lenient_referees()
    if lenient:
        ref_name = lenient[0].name
        proj = rps.project_cards(
            referee=ref_name,
            team_a_avg_cards=1.8,
            team_b_avg_cards=2.0,
            team_a_avg_fouls=10.5,
            team_b_avg_fouls=11.2,
            match_importance=1.1
        )
        print(f"   Arbitre: {ref_name}")
        print(f"   Base: {proj.base_expected:.2f} | Ref adj: {proj.referee_adjustment:+.2f} | Style: {proj.style_boost:+.2f}")
        print(f"   TOTAL: {proj.total_projected:.2f} | P(O3.5): {proj.over_35_prob:.1%} | Reco: {proj.recommendation}")
    
    # Test avec arbitre STRICT
    print("\n" + "=" * 70)
    print("🎯 TEST: Même match avec arbitre STRICT")
    print("=" * 70)
    
    strict = rps.get_strict_referees()
    if strict:
        ref_name = strict[0].name
        proj2 = rps.project_cards(
            referee=ref_name,
            team_a_avg_cards=1.8,
            team_b_avg_cards=2.0,
            team_a_avg_fouls=10.5,
            team_b_avg_fouls=11.2,
            match_importance=1.1
        )
        print(f"   Arbitre: {ref_name}")
        print(f"   Base: {proj2.base_expected:.2f} | Ref adj: {proj2.referee_adjustment:+.2f} | Style: {proj2.style_boost:+.2f}")
        print(f"   TOTAL: {proj2.total_projected:.2f} | P(O3.5): {proj2.over_35_prob:.1%} | Reco: {proj2.recommendation}")
        
        if lenient:
            print(f"\n📈 DIFFÉRENCE LENIENT vs STRICT: {proj2.total_projected - proj.total_projected:+.2f} cartons")
    
    # Test edge calculation
    print("\n" + "=" * 70)
    print("💰 TEST EDGE CALCULATION")
    print("=" * 70)
    
    if lenient:
        edge = calculate_card_edge(
            referee=lenient[0].name,
            team_a_cards=1.8,
            team_b_cards=2.0,
            team_a_fouls=10.5,
            team_b_fouls=11.2,
            bookmaker_line=3.5
        )
        print(f"   Arbitre: {lenient[0].name}")
        print(f"   Bookmaker line: {edge['bookmaker_line']}")
        print(f"   Notre projection: {edge['projected_cards']:.2f}")
        print(f"   Edge: {edge['edge']:+.2f} ({edge['edge_pct']:+.1f}%)")
        print(f"   💡 BET: {edge['recommended_bet']}")

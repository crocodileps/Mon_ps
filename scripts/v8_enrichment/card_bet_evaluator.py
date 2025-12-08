#!/usr/bin/env python3
"""
🎯 CARD BET EVALUATOR V1.0
Combine: Team Card DNA + Referee Adjusted Score → Betting Recommendation

Formule:
  Expected Cards = Team A avg + Team B avg
  Adjusted Cards = Expected + Referee Impact
  
Confidence based on:
  - Sample size (matches analyzed)
  - Referee consistency (volatility)
  - Historical hit rate
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from dataclasses import dataclass
from typing import Optional, Tuple, List
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

@dataclass
class CardPrediction:
    """Résultat d'une prédiction cartons"""
    home_team: str
    away_team: str
    referee: Optional[str]
    
    # Calculs
    home_card_avg: float
    away_card_avg: float
    expected_cards: float
    referee_impact: float
    adjusted_cards: float
    
    # Recommandation
    recommendation: str  # OVER_3.5, UNDER_3.5, OVER_4.5, etc.
    confidence: str      # HIGH, MEDIUM, LOW
    edge: float          # % edge vs line
    
    # Context
    home_profile: str
    away_profile: str
    referee_profile: str
    reasoning: List[str]


class CardBetEvaluator:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.load_data()
    
    def load_data(self):
        """Charge les données en mémoire"""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Team Card DNA
        cur.execute("""
            SELECT team_name, card_dna 
            FROM quantum.team_stats_extended 
            WHERE card_dna IS NOT NULL
        """)
        self.team_cards = {}
        for r in cur.fetchall():
            self.team_cards[r['team_name']] = r['card_dna']
        
        # Referee stats
        cur.execute("""
            SELECT referee_name, avg_yellows, card_impact, volatility, 
                   adj_profile, trigger_tag, matches
            FROM referee_stats
        """)
        self.referees = {}
        for r in cur.fetchall():
            self.referees[r['referee_name']] = dict(r)
        
        # League averages pour fallback
        cur.execute("""
            SELECT league, 
                   AVG(yellow_cards_home + yellow_cards_away)::numeric as avg_cards
            FROM match_stats_extended
            GROUP BY league
        """)
        self.league_avg = {r['league']: float(r['avg_cards']) for r in cur.fetchall()}
        
        cur.close()
        print(f"📊 Loaded: {len(self.team_cards)} teams, {len(self.referees)} referees")
    
    def get_team_card_avg(self, team: str) -> Tuple[float, str]:
        """Retourne la moyenne de cartons et le profil d'une équipe"""
        if team in self.team_cards:
            dna = self.team_cards[team]
            if isinstance(dna, str):
                dna = json.loads(dna)
            return float(dna.get('yellows_for_avg', 1.8)), dna.get('profile', 'UNKNOWN')
        return 1.8, 'UNKNOWN'  # Default
    
    def get_referee_data(self, referee: str) -> dict:
        """Retourne les stats de l'arbitre"""
        if referee and referee in self.referees:
            return self.referees[referee]
        return {
            'avg_yellows': 3.6,
            'card_impact': 0,
            'volatility': 1.0,
            'adj_profile': 'UNKNOWN',
            'trigger_tag': 'UNKNOWN',
            'matches': 0
        }
    
    def evaluate(self, home_team: str, away_team: str, 
                 referee: Optional[str] = None,
                 league: Optional[str] = None) -> CardPrediction:
        """
        Évalue un match et retourne une prédiction
        """
        # 1. Get team data
        home_avg, home_profile = self.get_team_card_avg(home_team)
        away_avg, away_profile = self.get_team_card_avg(away_team)
        
        # 2. Calculate expected cards (somme des moyennes individuelles)
        expected_cards = home_avg + away_avg
        
        # 3. Get referee adjustment
        ref_data = self.get_referee_data(referee)
        referee_impact = float(ref_data['card_impact']) if ref_data['card_impact'] else 0
        referee_profile = ref_data['adj_profile']
        
        # 4. Adjusted prediction
        adjusted_cards = expected_cards + referee_impact
        
        # 5. Generate recommendation
        reasoning = []
        confidence_score = 0
        
        # --- OVER 4.5 ANALYSIS ---
        if adjusted_cards >= 5.0:
            recommendation = "OVER_4.5"
            edge = (adjusted_cards - 4.5) / 4.5 * 100
            
            # Confidence factors
            if referee_profile == 'CARD_HAPPY':
                confidence_score += 30
                reasoning.append(f"🔴 Arbitre CARD_HAPPY ({referee}: +{referee_impact:.1f} impact)")
            
            if home_profile == 'CARD_MAGNET':
                confidence_score += 20
                reasoning.append(f"🟨 {home_team} = CARD_MAGNET")
            if away_profile == 'CARD_MAGNET':
                confidence_score += 20
                reasoning.append(f"🟨 {away_team} = CARD_MAGNET")
            
            if home_profile == 'AGGRESSIVE':
                confidence_score += 10
                reasoning.append(f"⚔️ {home_team} style AGGRESSIVE")
            if away_profile == 'AGGRESSIVE':
                confidence_score += 10
                reasoning.append(f"⚔️ {away_team} style AGGRESSIVE")
        
        # --- OVER 3.5 ANALYSIS ---
        elif adjusted_cards >= 4.0:
            recommendation = "OVER_3.5"
            edge = (adjusted_cards - 3.5) / 3.5 * 100
            
            if referee_profile in ['CARD_HAPPY', 'STRICT_ADJUSTED']:
                confidence_score += 25
                reasoning.append(f"🔴 Arbitre {referee_profile}")
            
            if home_profile in ['CARD_MAGNET', 'AGGRESSIVE']:
                confidence_score += 15
                reasoning.append(f"🟨 {home_team} profile: {home_profile}")
            if away_profile in ['CARD_MAGNET', 'AGGRESSIVE']:
                confidence_score += 15
                reasoning.append(f"🟨 {away_team} profile: {away_profile}")
        
        # --- UNDER 3.5 ANALYSIS ---
        elif adjusted_cards <= 3.0:
            recommendation = "UNDER_3.5"
            edge = (3.5 - adjusted_cards) / 3.5 * 100
            
            if referee_profile == 'VERY_LENIENT':
                confidence_score += 30
                reasoning.append(f"🟢 Arbitre VERY_LENIENT ({referee}: {referee_impact:.1f} impact)")
            elif referee_profile == 'LENIENT_ADJUSTED':
                confidence_score += 20
                reasoning.append(f"🟢 Arbitre LENIENT")
            
            if home_profile == 'CLEAN':
                confidence_score += 20
                reasoning.append(f"😇 {home_team} = CLEAN team")
            if away_profile == 'CLEAN':
                confidence_score += 20
                reasoning.append(f"😇 {away_team} = CLEAN team")
        
        # --- UNDER 4.5 ANALYSIS ---
        elif adjusted_cards <= 3.8:
            recommendation = "UNDER_4.5"
            edge = (4.5 - adjusted_cards) / 4.5 * 100
            
            if referee_profile in ['VERY_LENIENT', 'LENIENT_ADJUSTED']:
                confidence_score += 20
                reasoning.append(f"🟢 Arbitre {referee_profile}")
            
            if home_profile == 'CLEAN':
                confidence_score += 15
            if away_profile == 'CLEAN':
                confidence_score += 15
        
        else:
            recommendation = "NO_BET"
            edge = 0
            reasoning.append("⚖️ Ligne trop proche - pas d'edge clair")
        
        # --- Sample size confidence ---
        ref_matches = ref_data['matches'] or 0
        if ref_matches >= 10:
            confidence_score += 15
            reasoning.append(f"✅ Arbitre: {ref_matches} matchs (sample fiable)")
        elif ref_matches >= 5:
            confidence_score += 5
        elif referee:
            confidence_score -= 10
            reasoning.append(f"⚠️ Arbitre: seulement {ref_matches} matchs")
        
        # --- Volatility penalty ---
        volatility = float(ref_data['volatility']) if ref_data['volatility'] else 1.0
        if volatility > 1.5:
            confidence_score -= 10
            reasoning.append(f"⚠️ Arbitre volatile (σ={volatility:.1f})")
        
        # --- Final confidence ---
        if confidence_score >= 50:
            confidence = "HIGH"
        elif confidence_score >= 30:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return CardPrediction(
            home_team=home_team,
            away_team=away_team,
            referee=referee,
            home_card_avg=home_avg,
            away_card_avg=away_avg,
            expected_cards=expected_cards,
            referee_impact=referee_impact,
            adjusted_cards=adjusted_cards,
            recommendation=recommendation,
            confidence=confidence,
            edge=edge,
            home_profile=home_profile,
            away_profile=away_profile,
            referee_profile=referee_profile,
            reasoning=reasoning
        )
    
    def print_prediction(self, pred: CardPrediction):
        """Affiche une prédiction formatée"""
        conf_icon = {'HIGH': '🔥', 'MEDIUM': '✅', 'LOW': '⚠️'}.get(pred.confidence, '•')
        rec_icon = {
            'OVER_4.5': '🔴', 'OVER_3.5': '🟠', 
            'UNDER_3.5': '🟢', 'UNDER_4.5': '🟡',
            'NO_BET': '⚪'
        }.get(pred.recommendation, '•')
        
        print(f"\n{'='*70}")
        print(f"⚽ {pred.home_team} vs {pred.away_team}")
        print(f"{'='*70}")
        print(f"👨‍⚖️ Arbitre: {pred.referee or 'Non assigné'} ({pred.referee_profile})")
        print(f"\n📊 CALCUL:")
        print(f"   {pred.home_team}: {pred.home_card_avg:.2f} cartons/match ({pred.home_profile})")
        print(f"   {pred.away_team}: {pred.away_card_avg:.2f} cartons/match ({pred.away_profile})")
        print(f"   Expected: {pred.expected_cards:.2f}")
        print(f"   Referee Impact: {pred.referee_impact:+.2f}")
        print(f"   ━━━━━━━━━━━━━━━━━")
        print(f"   ADJUSTED: {pred.adjusted_cards:.2f} cartons")
        
        print(f"\n{rec_icon} RECOMMANDATION: {pred.recommendation}")
        print(f"{conf_icon} Confiance: {pred.confidence} | Edge: {pred.edge:.1f}%")
        
        print(f"\n💡 REASONING:")
        for r in pred.reasoning:
            print(f"   {r}")
    
    def close(self):
        self.conn.close()


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 CARD BET EVALUATOR V1.0                                                  ║
║  Combine Team DNA + Referee Impact → Smart Card Betting                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    evaluator = CardBetEvaluator()
    
    # Test cases - simulons quelques matchs
    test_matches = [
        # HIGH CARDS expected
        ("Valladolid", "Getafe", "J Busby"),        # 2 Card Magnets + Card Happy ref
        ("Sheffield United", "Leeds", "T Robinson"), # Championship battle
        
        # LOW CARDS expected  
        ("Arsenal", "Manchester City", "C Pawson"),  # 2 Clean teams + Lenient ref
        ("Newcastle United", "Liverpool", "M Oliver"), # Clean + Very Lenient
        
        # MEDIUM / Edge cases
        ("Chelsea", "Tottenham", "A Taylor"),        # London derby
        ("Inter", "AC Milan", None),                 # Derby, no referee data
    ]
    
    print("\n" + "="*70)
    print("🧪 TEST CASES:")
    print("="*70)
    
    results = []
    for home, away, ref in test_matches:
        pred = evaluator.evaluate(home, away, ref)
        evaluator.print_prediction(pred)
        results.append(pred)
    
    # Summary
    print("\n" + "="*70)
    print("📋 RÉSUMÉ DES RECOMMANDATIONS:")
    print("="*70)
    print(f"\n{'Match':<40} {'Rec':<12} {'Adj Cards':<12} {'Conf':<8} {'Edge'}")
    print("-"*80)
    
    for p in results:
        match = f"{p.home_team[:18]} vs {p.away_team[:18]}"
        print(f"{match:<40} {p.recommendation:<12} {p.adjusted_cards:.1f}         {p.confidence:<8} {p.edge:.1f}%")
    
    # High confidence picks
    high_conf = [p for p in results if p.confidence == 'HIGH' and p.recommendation != 'NO_BET']
    if high_conf:
        print(f"\n🔥 HIGH CONFIDENCE PICKS ({len(high_conf)}):")
        for p in high_conf:
            print(f"   • {p.home_team} vs {p.away_team}: {p.recommendation} ({p.edge:.1f}% edge)")
    
    evaluator.close()
    print("\n✅ Card Bet Evaluator ready!")


if __name__ == "__main__":
    main()


# ============================================================================
# DESPERATION INDEX - Match Context Modifier
# ============================================================================

DESPERATION_MODIFIERS = {
    # Enjeu du match
    'RELEGATION_BATTLE': +1.2,      # 2 équipes en zone rouge
    'RELEGATION_6_POINTS': +0.8,    # Équipe à 6 pts de la zone
    'TITLE_RACE': +0.5,             # Course au titre serrée
    'CHAMPIONS_LEAGUE_RACE': +0.4,  # Lutte pour C1
    'EUROPA_RACE': +0.3,            # Lutte pour C3
    'MID_TABLE': 0.0,               # Rien à jouer
    'NOTHING_TO_PLAY': -0.5,        # Fin de saison, maintien assuré
    
    # Type de match
    'DERBY': +0.8,                  # Derby local
    'RIVALRY': +0.5,                # Rivalité historique
    'NORMAL': 0.0,
    
    # Moment de la saison
    'LAST_5_GAMES': +0.3,           # Tension fin de saison
    'FIRST_5_GAMES': -0.2,          # Début tranquille
}

KNOWN_DERBIES = {
    # England
    ('Arsenal', 'Tottenham'): 'DERBY',
    ('Liverpool', 'Everton'): 'DERBY',
    ('Manchester United', 'Manchester City'): 'DERBY',
    ('Chelsea', 'Tottenham'): 'RIVALRY',
    ('Arsenal', 'Chelsea'): 'RIVALRY',
    
    # Spain
    ('Real Madrid', 'Barcelona'): 'DERBY',
    ('Real Madrid', 'Atletico Madrid'): 'DERBY',
    ('Barcelona', 'Espanyol'): 'DERBY',
    ('Sevilla', 'Real Betis'): 'DERBY',
    
    # Italy
    ('Inter', 'AC Milan'): 'DERBY',
    ('Roma', 'Lazio'): 'DERBY',
    ('Juventus', 'Torino'): 'DERBY',
    ('Juventus', 'Inter'): 'RIVALRY',
    
    # Germany
    ('Borussia Dortmund', 'Bayern Munich'): 'RIVALRY',
    ('Borussia Dortmund', 'Schalke 04'): 'DERBY',
    
    # France
    ('Paris Saint Germain', 'Marseille'): 'DERBY',
    ('Lyon', 'Saint-Etienne'): 'DERBY',
}

def get_derby_modifier(home: str, away: str) -> tuple:
    """Check if match is a derby/rivalry"""
    key1 = (home, away)
    key2 = (away, home)
    
    if key1 in KNOWN_DERBIES:
        dtype = KNOWN_DERBIES[key1]
        return DESPERATION_MODIFIERS[dtype], dtype
    if key2 in KNOWN_DERBIES:
        dtype = KNOWN_DERBIES[key2]
        return DESPERATION_MODIFIERS[dtype], dtype
    
    return 0.0, 'NORMAL'


def evaluate_with_context(evaluator, home_team: str, away_team: str, 
                          referee: str = None,
                          home_position: int = None,
                          away_position: int = None,
                          matchday: int = None,
                          total_matchdays: int = 38) -> CardPrediction:
    """
    Évaluation avancée avec contexte de match
    """
    # Base prediction
    pred = evaluator.evaluate(home_team, away_team, referee)
    
    context_modifier = 0.0
    context_reasons = []
    
    # 1. Derby check
    derby_mod, derby_type = get_derby_modifier(home_team, away_team)
    if derby_mod != 0:
        context_modifier += derby_mod
        context_reasons.append(f"🔥 {derby_type}: +{derby_mod:.1f} cartons")
    
    # 2. Position-based desperation
    if home_position and away_position:
        # Relegation zone (positions 18-20 for 20-team league)
        if home_position >= 18 or away_position >= 18:
            if home_position >= 18 and away_position >= 18:
                context_modifier += DESPERATION_MODIFIERS['RELEGATION_BATTLE']
                context_reasons.append("⚠️ RELEGATION BATTLE: +1.2 cartons")
            else:
                context_modifier += DESPERATION_MODIFIERS['RELEGATION_6_POINTS']
                context_reasons.append("⚠️ Équipe en danger: +0.8 cartons")
        
        # Title/European race (top 6)
        elif home_position <= 2 or away_position <= 2:
            context_modifier += DESPERATION_MODIFIERS['TITLE_RACE']
            context_reasons.append("🏆 Course au titre: +0.5 cartons")
        elif home_position <= 4 or away_position <= 4:
            context_modifier += DESPERATION_MODIFIERS['CHAMPIONS_LEAGUE_RACE']
            context_reasons.append("⭐ Lutte C1: +0.4 cartons")
        elif home_position <= 6 or away_position <= 6:
            context_modifier += DESPERATION_MODIFIERS['EUROPA_RACE']
            context_reasons.append("🌍 Lutte Europa: +0.3 cartons")
        
        # Mid-table with nothing to play for
        elif home_position >= 10 and home_position <= 14 and away_position >= 10 and away_position <= 14:
            context_modifier += DESPERATION_MODIFIERS['NOTHING_TO_PLAY']
            context_reasons.append("😴 Mid-table, rien à jouer: -0.5 cartons")
    
    # 3. Season timing
    if matchday:
        if matchday >= total_matchdays - 5:
            context_modifier += DESPERATION_MODIFIERS['LAST_5_GAMES']
            context_reasons.append("📅 Fin de saison tendue: +0.3 cartons")
        elif matchday <= 5:
            context_modifier += DESPERATION_MODIFIERS['FIRST_5_GAMES']
            context_reasons.append("📅 Début de saison calme: -0.2 cartons")
    
    # Update prediction
    new_adjusted = pred.adjusted_cards + context_modifier
    
    # Recalculate recommendation based on new adjusted
    if new_adjusted >= 5.0:
        new_rec = "OVER_4.5"
        new_edge = (new_adjusted - 4.5) / 4.5 * 100
    elif new_adjusted >= 4.0:
        new_rec = "OVER_3.5"
        new_edge = (new_adjusted - 3.5) / 3.5 * 100
    elif new_adjusted <= 3.0:
        new_rec = "UNDER_3.5"
        new_edge = (3.5 - new_adjusted) / 3.5 * 100
    elif new_adjusted <= 3.8:
        new_rec = "UNDER_4.5"
        new_edge = (4.5 - new_adjusted) / 4.5 * 100
    else:
        new_rec = "NO_BET"
        new_edge = 0
    
    # Create new prediction with context
    return CardPrediction(
        home_team=pred.home_team,
        away_team=pred.away_team,
        referee=pred.referee,
        home_card_avg=pred.home_card_avg,
        away_card_avg=pred.away_card_avg,
        expected_cards=pred.expected_cards,
        referee_impact=pred.referee_impact,
        adjusted_cards=new_adjusted,
        recommendation=new_rec,
        confidence=pred.confidence if context_modifier == 0 else 
                   ("HIGH" if abs(context_modifier) >= 0.5 else pred.confidence),
        edge=new_edge,
        home_profile=pred.home_profile,
        away_profile=pred.away_profile,
        referee_profile=pred.referee_profile,
        reasoning=pred.reasoning + context_reasons
    )


# Test with context
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎯 TEST AVEC DESPERATION INDEX:")
    print("="*70)
    
    evaluator = CardBetEvaluator()
    
    # Inter vs Milan - DERBY!
    pred = evaluate_with_context(
        evaluator, 
        "Inter", "AC Milan", 
        referee=None,
        home_position=2,  # Inter 2ème
        away_position=5,  # Milan 5ème
        matchday=15
    )
    evaluator.print_prediction(pred)
    
    # Relegation battle
    pred2 = evaluate_with_context(
        evaluator,
        "Southampton", "Ipswich",
        referee="J Busby",
        home_position=19,
        away_position=20,
        matchday=35,
        total_matchdays=38
    )
    evaluator.print_prediction(pred2)
    
    evaluator.close()

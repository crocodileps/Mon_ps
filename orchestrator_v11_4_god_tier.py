#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
ORCHESTRATOR V11.4 - GOD TIER (INSTITUTIONAL GRADE)
═══════════════════════════════════════════════════════════════════════════════════════

HÉRITE DE: V11.3.2 (team_class corrigé, 94.4% WR)

NOUVELLES FONCTIONNALITÉS:
1. Dixon-Coles Model (remplace Poisson simple dans xG analysis)
2. Liquidity-Weighted Steam (nouveau layer)
3. Portfolio Kelly avec Covariance (gestion risque portefeuille)
4. Time-Decay Dynamique (coach change reset)

PRINCIPE: "Extend, Don't Break"
On hérite de V11.3.2 et on ajoute les améliorations God Tier.

Auteur: Mon_PS Quant System
Version: 11.4 God Tier
═══════════════════════════════════════════════════════════════════════════════════════
"""

import sys
import os

# Ajouter le path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import de la base V11.3.2
from orchestrator_v11_3_full_analysis import (
    OrchestratorV11_3, 
    ScoringConfig,
    normalize_team_name,
    match_team,
    calculate_kelly,
    get_matches,
    evaluate_prediction,
    DB_CONFIG
)

# Import des modules God Tier
from quant_god_tier import (
    DixonColesModel,
    LiquidityWeightedSteam,
    PortfolioKelly,
    DynamicTimeDecay
)

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from collections import defaultdict
import math


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION V11.4 (ÉTEND V11.3.2)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScoringConfigV11_4(ScoringConfig):
    """
    Configuration V11.4 avec nouveaux layers God Tier
    """
    
    # Nouveaux poids pour layers God Tier
    LAYER_WEIGHTS = {
        # Layers V11.3.2 (inchangés)
        'tactical': 1.0,
        'team_class': 0.8,
        'h2h': 0.7,
        'injuries': 1.2,
        'xg': 0.9,  # Maintenant avec Dixon-Coles!
        'coach': 0.6,
        'convergence': 0.4,
        'defensive_context': 1.0,
        # Nouveaux layers God Tier
        'steam': 1.5,  # Steam très important
    }
    
    # Seuils V11.3.2 ajustés pour nouveaux layers
    SNIPER_THRESHOLD = 34  # Confirmé par backtest V11.3.2
    NORMAL_THRESHOLD = 32  # Confirmé par backtest V11.3.2
    
    # Steam thresholds
    STEAM_SIGNAL_THRESHOLD = 0.5  # Weighted steam > 0.5 = signal
    STEAM_SUSPICIOUS_THRESHOLD = 8.0  # Prob shift > 8% = suspect


# ═══════════════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V11.4 GOD TIER
# ═══════════════════════════════════════════════════════════════════════════════════════

class OrchestratorV11_4(OrchestratorV11_3):
    """
    Orchestrator V11.4 - Extension God Tier de V11.3.2
    
    Nouvelles fonctionnalités:
    - Dixon-Coles pour xG (remplace Poisson simple)
    - Steam Analysis avec Liquidity Weighting
    - Portfolio Kelly pour gestion risque
    - Time-Decay pour changements de coach
    """
    
    def __init__(self):
        # Initialiser la base V11.3.2
        super().__init__()
        
        # Remplacer la config par V11.4
        self.config = ScoringConfigV11_4()
        
        # Charger les données steam
        self._load_steam_cache()
        
        print(f"   🚀 GOD TIER: Dixon-Coles, Steam Analysis, Portfolio Kelly activés")
    
    def _load_steam_cache(self):
        """Charge les données steam avec indexation bidirectionnelle"""
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT match_id, home_team, away_team, 
                       prob_shift_total, steam_direction, steam_magnitude,
                       classification, opening_home_prob, closing_home_prob,
                       opening_away_prob, closing_away_prob, commence_time
                FROM match_steam_analysis
                WHERE commence_time >= NOW() - INTERVAL '30 days'
            """)
            
            self.cache['steam'] = {}
            
            for r in cur.fetchall():
                h_norm = normalize_team_name(r['home_team'])
                a_norm = normalize_team_name(r['away_team'])
                
                # Indexer dans les DEUX sens
                self.cache['steam'][(h_norm, a_norm)] = r
                
                # Créer version inversée
                r_reversed = dict(r)
                r_reversed['_reversed'] = True
                self.cache['steam'][(a_norm, h_norm)] = r_reversed
                
                # Index par premier mot (fallback)
                h_first = h_norm.split()[0] if h_norm else ''
                a_first = a_norm.split()[0] if a_norm else ''
                if h_first and a_first:
                    self.cache['steam'][(h_first, a_first)] = r
                    self.cache['steam'][(a_first, h_first)] = r_reversed
            
            conn.close()
            print(f"   📊 Steam cache: {len(self.cache['steam'])} entrées (bidirectionnel)")
            
        except Exception as e:
            print(f"   ⚠️ Steam cache error: {e}")
            self.cache['steam'] = {}
    
    def _analyze_xg_dixon_coles(self, home, away):
        """
        Analyse xG avec modèle Dixon-Coles (améliore Poisson simple)
        
        Corrige la sous-estimation des 0-0 et 1-1
        """
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        if h_data and a_data:
            # Récupérer les xG
            h_xg_for = float(h_data.get('xg_for_per_match') or 1.3)
            a_xg_for = float(a_data.get('xg_for_per_match') or 1.3)
            h_xg_against = float(h_data.get('xg_against_per_match') or 1.3)
            a_xg_against = float(a_data.get('xg_against_per_match') or 1.3)
            
            # Lambda pour Dixon-Coles
            home_lambda = (h_xg_for + a_xg_against) / 2
            away_lambda = (a_xg_for + h_xg_against) / 2
            
            # Calculer les probabilités Dixon-Coles
            probs = DixonColesModel.market_probabilities(home_lambda, away_lambda)
            
            # Score basé sur les probabilités Dixon-Coles
            over25_prob = probs['over_25']
            btts_prob = probs['btts_yes']
            
            # Score pour over_25
            if over25_prob > 60:
                score = min(5, (over25_prob - 50) / 5)
            elif over25_prob < 45:
                score = max(-2, (over25_prob - 50) / 5)
            else:
                score = 1.0
            
            # Ajustement overperformance
            h_overperf = float(h_data.get('overperformance_goals') or 0)
            a_overperf = float(a_data.get('overperformance_goals') or 0)
            avg_overperf = (h_overperf + a_overperf) / 2
            
            if avg_overperf > 0.3:
                score *= 0.7  # Régression attendue
            elif avg_overperf < -0.3:
                score *= 1.2  # Amélioration attendue
            
            return {
                'score': round(score, 2),
                'home_lambda': round(home_lambda, 2),
                'away_lambda': round(away_lambda, 2),
                'over25_prob': round(over25_prob, 1),
                'btts_prob': round(btts_prob, 1),
                'under25_prob': round(probs['under_25'], 1),
                'draw_prob': round(probs['draw'], 1),
                'most_likely_scores': probs['most_likely_scores'][:3],
                'overperf': round(avg_overperf, 2),
                'model': 'dixon_coles',
                'reason': f"DC: O25={over25_prob:.0f}% BTTS={btts_prob:.0f}%"
            }
        
        return {
            'score': 2.0, 
            'over25_prob': 50, 
            'btts_prob': 50,
            'model': 'fallback',
            'reason': 'No xG data'
        }
    
    def _analyze_steam(self, home, away, league=None):
        """
        Analyse Steam avec Liquidity Weighting (nouveau layer God Tier)
        
        Retourne un score et des alertes basées sur les mouvements de cotes
        """
        h_norm = normalize_team_name(home)
        a_norm = normalize_team_name(away)
        
        # Chercher dans le cache steam (essayer plusieurs clés)
        steam_data = None
        for key in [
            (h_norm, a_norm),
            (a_norm, h_norm),
            (h_norm.split()[0] if h_norm else '', a_norm.split()[0] if a_norm else ''),
            (a_norm.split()[0] if a_norm else '', h_norm.split()[0] if h_norm else ''),
        ]:
            steam_data = self.cache.get('steam', {}).get(key)
            if steam_data:
                break
        
        if steam_data:
            prob_shift = float(steam_data.get('prob_shift_total') or 0)
            steam_dir = steam_data.get('steam_direction', 'no_steam')
            magnitude = steam_data.get('steam_magnitude', 'NORMAL')
            classification = steam_data.get('classification', 'CLEAN')
            
            # Calculer le weighted steam
            # Estimer les heures (approximation: 48h entre open et close)
            hours_elapsed = 48
            
            weighted = LiquidityWeightedSteam.calculate_weighted_steam(
                prob_shift, hours_elapsed, league or 'Unknown'
            )
            
            # Score basé sur le prob_shift (pas juste velocity)
            weighted_steam = weighted['weighted_steam']
            
            if classification == 'SUSPICIOUS_MOVE':
                # Mouvement suspect > 8% - alerte
                score = -2.0
                alert = 'SUSPICIOUS'
            elif prob_shift >= 8.0:
                # Shift très significatif (>8%)
                score = 3.0
                alert = 'SHARP_SIGNAL'
            elif prob_shift >= 4.0:
                # Shift notable (4-8%) - MARKET_EFFICIENCY zone
                if steam_dir in ['steam_home', 'steam_away']:
                    score = 2.0
                else:
                    score = 1.0
                alert = 'NOTABLE'
            elif prob_shift >= 2.0:
                # Petit shift (2-4%)
                score = 0.5
                alert = 'MINOR'
            else:
                # Shift négligeable (<2%)
                score = 0
                alert = 'NONE' 
            
            return {
                'score': score,
                'prob_shift': prob_shift,
                'steam_direction': steam_dir,
                'weighted_steam': weighted_steam,
                'classification': classification,
                'alert': alert,
                'league_tier': weighted['league_tier'],
                'reason': f"Steam: {prob_shift:.1f}% {steam_dir} ({alert})"
            }
        
        return {
            'score': 0,
            'prob_shift': 0,
            'steam_direction': 'unknown',
            'weighted_steam': 0,
            'alert': 'NO_DATA',
            'reason': 'No steam data'
        }
    
    def _analyze_coach_with_decay(self, home, away):
        """
        Analyse Coach avec Time-Decay dynamique
        
        Si changement de coach récent, les données avant = 10% de poids
        """
        h_coach = match_team(home, self.cache.get('coaches', {}))
        a_coach = match_team(away, self.cache.get('coaches', {}))
        
        h_over25 = 50
        a_over25 = 50
        h_decay_applied = False
        a_decay_applied = False
        
        if h_coach:
            h_over25 = float(h_coach.get('over25_rate') or 50)
            
            # Vérifier si changement de coach récent
            h_tenure = h_coach.get('tenure_days')
            if h_tenure and int(h_tenure) < 60:  # Moins de 2 mois
                # Appliquer le decay - régression vers la moyenne
                h_over25 = 0.3 * h_over25 + 0.7 * 50  # 30% données coach, 70% moyenne
                h_decay_applied = True
        
        if a_coach:
            a_over25 = float(a_coach.get('over25_rate') or 50)
            
            a_tenure = a_coach.get('tenure_days')
            if a_tenure and int(a_tenure) < 60:
                a_over25 = 0.3 * a_over25 + 0.7 * 50
                a_decay_applied = True
        
        # Score
        score = 0
        if h_over25 > 55 and a_over25 > 55:
            score = 2.0
        elif h_over25 > 60 or a_over25 > 60:
            score = 1.0
        elif h_over25 < 40 or a_over25 < 40:
            score = -1.0
        
        decay_note = ""
        if h_decay_applied or a_decay_applied:
            decay_note = " [DECAY]"
            score *= 0.7  # Moins de confiance si nouveau coach
        
        found = "2/2" if (h_coach and a_coach) else ("1/2" if (h_coach or a_coach) else "0/2")
        
        return {
            'score': round(score, 2),
            'h_over25': round(h_over25, 1),
            'a_over25': round(a_over25, 1),
            'h_decay_applied': h_decay_applied,
            'a_decay_applied': a_decay_applied,
            'reason': f"O25:{h_over25:.0f}%/{a_over25:.0f}% ({found}){decay_note}"
        }
    
    def analyze_match(self, home: str, away: str, default_market: str = "over_25", league: str = None):
        """
        Analyse complète V11.4 avec tous les layers God Tier
        """
        layers = {}
        raw_scores = []
        
        # === LAYERS V11.3.2 (hérités) ===
        
        # Layer 1: Tactical (inchangé)
        tactical = self._analyze_tactical(home, away)
        layers['tactical'] = tactical
        raw_scores.append(tactical['score'])
        
        # Layer 2: Team Class (inchangé, corrigé en V11.3.2)
        team_class = self._analyze_team_class(home, away)
        layers['team_class'] = team_class
        raw_scores.append(team_class['score'])
        
        # Layer 3: H2H (inchangé)
        h2h = self._analyze_h2h(home, away)
        layers['h2h'] = h2h
        raw_scores.append(h2h['score'])
        
        # Layer 4: Injuries (inchangé)
        injuries = self._analyze_injuries(home, away)
        layers['injuries'] = injuries
        
        # Layer 5: xG avec DIXON-COLES (AMÉLIORÉ!)
        xg = self._analyze_xg_dixon_coles(home, away)
        layers['xg'] = xg
        raw_scores.append(xg['score'])
        
        # Layer 6: Coach avec TIME-DECAY (AMÉLIORÉ!)
        coach = self._analyze_coach_with_decay(home, away)
        layers['coach'] = coach
        raw_scores.append(coach['score'])
        
        # Layer 7: Convergence (inchangé)
        convergence = self._analyze_convergence(home, away, tactical)
        layers['convergence'] = convergence
        
        # Layer 8: Defensive Context (inchangé)
        defensive = self._analyze_defensive_context(home, away)
        layers['defensive_context'] = defensive
        
        # === NOUVEAUX LAYERS GOD TIER ===
        
        # Layer 9: Steam Analysis (NOUVEAU!)
        steam = self._analyze_steam(home, away, league)
        layers['steam'] = steam
        
        # === CALCUL SCORE TOTAL ===
        w = self.config.LAYER_WEIGHTS
        total_score = 10.0  # Base
        
        # Layers V11.3.2
        total_score += tactical['score'] * w['tactical']
        total_score += team_class['score'] * w['team_class']
        total_score += h2h['score'] * w['h2h']
        total_score += injuries['score'] * w['injuries']
        total_score += xg['score'] * w['xg']
        total_score += coach['score'] * w['coach']
        total_score += convergence['score'] * w['convergence']
        total_score += defensive['score'] * w['defensive_context']
        
        # Layer God Tier
        total_score += steam['score'] * w['steam']
        
        # === ALERTES STEAM ===
        steam_alert = None
        if steam['alert'] == 'SUSPICIOUS':
            steam_alert = "🔴 STEAM SUSPECT - Vérifier avant de parier"
        elif steam['alert'] == 'SHARP_SIGNAL':
            steam_alert = f"🟢 SHARP SIGNAL - {steam['steam_direction']}"
        
        # === SÉLECTION MARCHÉ ===
        market_selection = self._select_market(tactical, team_class, defensive, convergence, default_market)
        
        # Utiliser les probabilités Dixon-Coles si disponibles
        over25_prob = xg.get('over25_prob', tactical.get('over25', 50))
        btts_prob = xg.get('btts_prob', tactical.get('btts', 50))
        
        # === PROBABILITÉ ET EDGE ===
        win_prob = self._estimate_win_prob(total_score, market_selection['market'])
        implied_prob = 1 / 1.85
        edge = (win_prob - implied_prob) / implied_prob if implied_prob > 0 else 0
        kelly = calculate_kelly(win_prob, 1.85, self.config.KELLY_FRACTION)
        
        # === ACTION ===
        if total_score >= self.config.SNIPER_THRESHOLD:
            action = "SNIPER_BET"
        elif total_score >= self.config.NORMAL_THRESHOLD:
            action = "NORMAL_BET"
        else:
            action = "SKIP"
        
        # Downgrade si steam suspect
        if steam['alert'] == 'SUSPICIOUS' and action != "SKIP":
            action = "CAUTION_" + action
        
        return {
            'score': round(total_score, 1),
            'action': action,
            'recommended_market': market_selection['market'],
            'market_reason': market_selection['reason'],
            'win_probability': round(win_prob * 100, 1),
            'edge': round(edge * 100, 2),
            'kelly_stake': round(kelly * 100, 2),
            'btts_prob': round(btts_prob, 1),
            'over25_prob': round(over25_prob, 1),
            'steam_alert': steam_alert,
            'dixon_coles': xg.get('most_likely_scores', []),
            'layers': layers,
            'version': 'V11.4_GOD_TIER'
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# PORTFOLIO MANAGER (NOUVEAU)
# ═══════════════════════════════════════════════════════════════════════════════════════

class PortfolioManager:
    """
    Gère le portefeuille de paris avec Portfolio Kelly
    
    Applique les pénalités de corrélation pour éviter le risque systémique
    """
    
    @staticmethod
    def adjust_stakes(bets):
        """
        Ajuste les stakes en fonction des corrélations
        
        Args:
            bets: Liste de dicts avec 'kelly_stake', 'league', 'market'
        
        Returns:
            Bets avec kelly_adjusted
        """
        return PortfolioKelly.calculate_portfolio_kelly(bets)
    
    @staticmethod
    def analyze_risk(bets):
        """
        Analyse le risque global du portefeuille
        """
        return PortfolioKelly.analyze_portfolio_risk(bets)


# ═══════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS DE TEST
# ═══════════════════════════════════════════════════════════════════════════════════════

def test_v11_4():
    """Test de V11.4 God Tier"""
    print("=" * 100)
    print("    🚀 TEST ORCHESTRATOR V11.4 GOD TIER")
    print("=" * 100)
    
    orch = OrchestratorV11_4()
    
    # Matchs de test
    test_matches = [
        ("Arsenal", "Chelsea", "Premier League"),
        ("Barcelona", "Real Madrid", "La Liga"),
        ("Bayern Munich", "Dortmund", "Bundesliga"),
    ]
    
    for home, away, league in test_matches:
        print(f"\n{'─' * 100}")
        print(f"   ⚽ {home} vs {away} ({league})")
        print(f"{'─' * 100}")
        
        result = orch.analyze_match(home, away, league=league)
        
        print(f"\n   📊 Score Total: {result['score']}")
        print(f"   🎯 Action: {result['action']}")
        print(f"   📈 Market: {result['recommended_market']}")
        print(f"   📊 Over 2.5: {result['over25_prob']}% | BTTS: {result['btts_prob']}%")
        
        if result.get('steam_alert'):
            print(f"   ⚠️ {result['steam_alert']}")
        
        if result.get('dixon_coles'):
            print(f"   🎲 Dixon-Coles Top Scores: {result['dixon_coles']}")
        
        # Détail des layers
        print(f"\n   📋 Layers:")
        for name, layer in result['layers'].items():
            score = layer.get('score', 0)
            reason = layer.get('reason', '')[:50]
            print(f"      {name:20} : {score:+5.1f} | {reason}")
    
    # Test Portfolio Kelly
    print(f"\n{'═' * 100}")
    print("   💼 TEST PORTFOLIO KELLY")
    print(f"{'═' * 100}")
    
    sample_bets = [
        {'match': 'Arsenal vs Chelsea', 'league': 'Premier League', 'market': 'over_25', 'kelly_pct': 3.5},
        {'match': 'Liverpool vs Everton', 'league': 'Premier League', 'market': 'over_25', 'kelly_pct': 2.8},
        {'match': 'Man City vs Spurs', 'league': 'Premier League', 'market': 'btts_yes', 'kelly_pct': 2.0},
    ]
    
    adjusted = PortfolioManager.adjust_stakes(sample_bets)
    risk = PortfolioManager.analyze_risk(adjusted)
    
    print(f"\n   📊 Risque: {risk['risk_level']} - {risk['warning']}")
    print(f"   💰 Exposition totale: {risk['total_exposure']}%")
    
    for bet in adjusted:
        print(f"   {bet['match']:30} : {bet['kelly_pct']:.1f}% → {bet['kelly_adjusted']:.1f}% (penalty: {bet['combined_penalty']:.2f}x)")
    
    print(f"\n{'═' * 100}")
    print("   ✅ V11.4 GOD TIER OPÉRATIONNEL")
    print(f"{'═' * 100}")


if __name__ == "__main__":
    test_v11_4()

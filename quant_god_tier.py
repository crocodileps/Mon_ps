#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════════════════
QUANT GOD TIER - INSTITUTIONAL GRADE IMPROVEMENTS
═══════════════════════════════════════════════════════════════════════════════════════════════════

AMÉLIORATIONS:
1. Dixon-Coles Model (vs Poisson simple)
2. Liquidity-Weighted Steam
3. Portfolio Kelly avec Covariance
4. Time-Decay Dynamique (Coach Change)

Référence: Dixon & Coles (1997) - "Modelling Association Football Scores and Inefficiencies"
═══════════════════════════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from scipy.stats import poisson
from scipy.optimize import minimize
from datetime import datetime, timedelta
from collections import defaultdict
import math

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# 1. DIXON-COLES MODEL
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

class DixonColesModel:
    """
    Modèle Dixon-Coles pour prédiction de scores de football
    
    Corrige le défaut du Poisson simple qui sous-estime les scores faibles (0-0, 1-0, 0-1, 1-1)
    en ajoutant un paramètre de dépendance ρ (rho).
    
    Référence: Dixon & Coles (1997)
    """
    
    # Paramètre rho calibré sur données historiques
    # Valeur typique entre -0.10 et -0.15 pour le football
    DEFAULT_RHO = -0.13
    
    @staticmethod
    def tau(home_goals, away_goals, home_lambda, away_lambda, rho):
        """
        Fonction de correction Dixon-Coles pour les scores faibles
        
        τ(x,y,λ,μ,ρ) modifie les probabilités pour:
        - 0-0: (1 - λμρ)
        - 1-0: (1 + μρ)
        - 0-1: (1 + λρ)
        - 1-1: (1 - ρ)
        """
        if home_goals == 0 and away_goals == 0:
            return 1 - home_lambda * away_lambda * rho
        elif home_goals == 0 and away_goals == 1:
            return 1 + home_lambda * rho
        elif home_goals == 1 and away_goals == 0:
            return 1 + away_lambda * rho
        elif home_goals == 1 and away_goals == 1:
            return 1 - rho
        else:
            return 1.0
    
    @classmethod
    def probability_matrix(cls, home_xg, away_xg, max_goals=8, rho=None):
        """
        Génère une matrice de probabilités Dixon-Coles ajustée
        
        Args:
            home_xg: Expected Goals pour l'équipe à domicile (λ)
            away_xg: Expected Goals pour l'équipe à l'extérieur (μ)
            max_goals: Nombre max de buts à considérer
            rho: Paramètre de dépendance (défaut: -0.13)
            
        Returns:
            Matrice numpy (max_goals x max_goals) avec P(home=i, away=j)
        """
        if rho is None:
            rho = cls.DEFAULT_RHO
        
        prob_matrix = np.zeros((max_goals, max_goals))
        
        for h in range(max_goals):
            for a in range(max_goals):
                # Poisson standard
                prob_poisson = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
                
                # Correction Dixon-Coles
                tau_correction = cls.tau(h, a, home_xg, away_xg, rho)
                
                prob_matrix[h, a] = prob_poisson * tau_correction
        
        # Normaliser pour que la somme = 1
        prob_matrix /= prob_matrix.sum()
        
        return prob_matrix
    
    @classmethod
    def market_probabilities(cls, home_xg, away_xg, rho=None):
        """
        Calcule les probabilités pour tous les marchés principaux
        
        Returns:
            dict avec probabilités pour chaque marché
        """
        matrix = cls.probability_matrix(home_xg, away_xg, rho=rho)
        
        # Over/Under
        over_25 = sum(matrix[h, a] for h in range(8) for a in range(8) if h + a >= 3)
        over_35 = sum(matrix[h, a] for h in range(8) for a in range(8) if h + a >= 4)
        under_25 = 1 - over_25
        under_35 = 1 - over_35
        
        # BTTS
        btts_yes = sum(matrix[h, a] for h in range(1, 8) for a in range(1, 8))
        btts_no = 1 - btts_yes
        
        # 1X2
        home_win = sum(matrix[h, a] for h in range(8) for a in range(8) if h > a)
        draw = sum(matrix[h, h] for h in range(8))
        away_win = sum(matrix[h, a] for h in range(8) for a in range(8) if a > h)
        
        # Exact scores (top 5 les plus probables)
        scores = []
        for h in range(6):
            for a in range(6):
                scores.append((h, a, matrix[h, a]))
        scores.sort(key=lambda x: -x[2])
        
        return {
            'over_25': round(over_25 * 100, 1),
            'under_25': round(under_25 * 100, 1),
            'over_35': round(over_35 * 100, 1),
            'under_35': round(under_35 * 100, 1),
            'btts_yes': round(btts_yes * 100, 1),
            'btts_no': round(btts_no * 100, 1),
            'home_win': round(home_win * 100, 1),
            'draw': round(draw * 100, 1),
            'away_win': round(away_win * 100, 1),
            'most_likely_scores': [(f"{h}-{a}", round(p*100, 1)) for h, a, p in scores[:5]],
            'expected_total_goals': round(home_xg + away_xg, 2),
        }
    
    @classmethod
    def compare_with_poisson(cls, home_xg, away_xg):
        """
        Compare Dixon-Coles vs Poisson simple pour montrer la différence
        """
        # Poisson simple
        poisson_matrix = np.zeros((8, 8))
        for h in range(8):
            for a in range(8):
                poisson_matrix[h, a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
        poisson_matrix /= poisson_matrix.sum()
        
        # Dixon-Coles
        dc_matrix = cls.probability_matrix(home_xg, away_xg)
        
        # Comparer les scores faibles
        comparison = {
            '0-0': {
                'poisson': round(poisson_matrix[0, 0] * 100, 2),
                'dixon_coles': round(dc_matrix[0, 0] * 100, 2),
                'difference': round((dc_matrix[0, 0] - poisson_matrix[0, 0]) * 100, 2)
            },
            '1-0': {
                'poisson': round(poisson_matrix[1, 0] * 100, 2),
                'dixon_coles': round(dc_matrix[1, 0] * 100, 2),
                'difference': round((dc_matrix[1, 0] - poisson_matrix[1, 0]) * 100, 2)
            },
            '0-1': {
                'poisson': round(poisson_matrix[0, 1] * 100, 2),
                'dixon_coles': round(dc_matrix[0, 1] * 100, 2),
                'difference': round((dc_matrix[0, 1] - poisson_matrix[0, 1]) * 100, 2)
            },
            '1-1': {
                'poisson': round(poisson_matrix[1, 1] * 100, 2),
                'dixon_coles': round(dc_matrix[1, 1] * 100, 2),
                'difference': round((dc_matrix[1, 1] - poisson_matrix[1, 1]) * 100, 2)
            },
        }
        
        return comparison


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# 2. LIQUIDITY-WEIGHTED STEAM
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

class LiquidityWeightedSteam:
    """
    Pondère les mouvements de cotes par la liquidité du marché
    
    Un mouvement de 5% en Premier League (haute liquidité) est beaucoup plus
    significatif qu'un mouvement de 5% en 3ème division (faible liquidité).
    """
    
    # Facteurs de liquidité par tier de ligue
    LIQUIDITY_FACTORS = {
        1: 1.5,   # EPL, La Liga, Bundesliga, Serie A, Ligue 1, CL
        2: 1.0,   # Championship, Eredivisie, Liga Portugal, etc.
        3: 0.6,   # Divisions inférieures, ligues mineures
        4: 0.3,   # Ligues très mineures, amateurs
    }
    
    # Mapping des ligues vers les tiers
    LEAGUE_TIERS = {
        # Tier 1
        'Premier League': 1, 'EPL': 1, 'soccer_epl': 1,
        'La Liga': 1, 'soccer_spain_la_liga': 1,
        'Bundesliga': 1, 'soccer_germany_bundesliga': 1,
        'Serie A': 1, 'soccer_italy_serie_a': 1,
        'Ligue 1': 1, 'soccer_france_ligue_one': 1,
        'Champions League': 1, 'UEFA Champions League': 1,
        'Europa League': 1,
        
        # Tier 2
        'Championship': 2, 'soccer_efl_champ': 2,
        'Eredivisie': 2, 'soccer_netherlands_eredivisie': 2,
        'Primeira Liga': 2, 'soccer_portugal_primeira_liga': 2,
        'Belgian Pro League': 2, 'soccer_belgium_first_div': 2,
        'Super Lig': 2, 'soccer_turkey_super_league': 2,
        'Bundesliga 2': 2, 'soccer_germany_bundesliga2': 2,
        
        # Tier 3
        'Ligue 2': 3, 'soccer_france_ligue_two': 3,
        'Serie B': 3, 'soccer_italy_serie_b': 3,
        'La Liga 2': 3, 'soccer_spain_segunda_division': 3,
        'League One': 3, 'League Two': 3,
        
        # Default
        'Unknown': 3,
    }
    
    @classmethod
    def get_league_tier(cls, league_name):
        """Retourne le tier d'une ligue"""
        if not league_name:
            return 3
        
        # Chercher dans le mapping
        for key, tier in cls.LEAGUE_TIERS.items():
            if key.lower() in league_name.lower():
                return tier
        
        return 3  # Default
    
    @classmethod
    def calculate_weighted_steam(cls, prob_shift, hours_elapsed, league, verbose=False):
        """
        Calcule le steam pondéré par la liquidité
        
        Args:
            prob_shift: Changement de probabilité en %
            hours_elapsed: Heures entre opening et closing
            league: Nom de la ligue
            
        Returns:
            dict avec steam_velocity, liquidity_factor, weighted_steam
        """
        # Calculer la vélocité brute
        velocity = prob_shift / hours_elapsed if hours_elapsed > 0 else prob_shift
        
        # Obtenir le facteur de liquidité
        tier = cls.get_league_tier(league)
        liquidity_factor = cls.LIQUIDITY_FACTORS.get(tier, 0.5)
        
        # Steam pondéré
        weighted_steam = velocity * liquidity_factor
        
        # Classification
        if weighted_steam >= 1.5:
            classification = 'SHARP_SIGNAL'
            confidence = 'HIGH'
        elif weighted_steam >= 0.8:
            classification = 'NOTABLE_STEAM'
            confidence = 'MEDIUM'
        elif weighted_steam >= 0.3:
            classification = 'MINOR_STEAM'
            confidence = 'LOW'
        else:
            classification = 'NOISE'
            confidence = 'NONE'
        
        result = {
            'prob_shift': prob_shift,
            'hours_elapsed': hours_elapsed,
            'velocity_raw': round(velocity, 3),
            'league_tier': tier,
            'liquidity_factor': liquidity_factor,
            'weighted_steam': round(weighted_steam, 3),
            'classification': classification,
            'confidence': confidence,
        }
        
        if verbose:
            print(f"   Steam Analysis: {prob_shift:.1f}% / {hours_elapsed:.1f}h")
            print(f"   League Tier: {tier} | Liquidity Factor: {liquidity_factor}")
            print(f"   Weighted Steam: {weighted_steam:.3f} → {classification}")
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# 3. PORTFOLIO KELLY AVEC COVARIANCE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

class PortfolioKelly:
    """
    Gestion du risque au niveau du portefeuille de paris
    
    Applique une pénalité de corrélation quand plusieurs paris sont sur:
    - La même ligue (risque météo/arbitrage)
    - Le même marché (Over 2.5 sur 5 matchs)
    - Le même jour
    """
    
    # Corrélations typiques entre marchés
    MARKET_CORRELATIONS = {
        ('over_25', 'over_35'): 0.85,
        ('over_25', 'btts_yes'): 0.72,
        ('btts_yes', 'btts_no'): -1.0,
        ('over_25', 'under_25'): -1.0,
        ('over_25', 'home_win'): 0.15,
        ('btts_yes', 'home_win'): 0.05,
    }
    
    @classmethod
    def correlation_penalty(cls, n_correlated):
        """
        Pénalité basée sur le nombre de paris corrélés
        
        Formule: 1 / √n
        - 1 pari: penalty = 1.0 (pas de réduction)
        - 2 paris: penalty = 0.71
        - 3 paris: penalty = 0.58
        - 4 paris: penalty = 0.50
        - 5 paris: penalty = 0.45
        """
        if n_correlated <= 1:
            return 1.0
        return 1 / math.sqrt(n_correlated)
    
    @classmethod
    def calculate_portfolio_kelly(cls, bets):
        """
        Calcule le Kelly ajusté pour chaque pari en tenant compte des corrélations
        
        Args:
            bets: Liste de dicts avec 'kelly_pct', 'league', 'market', 'date'
            
        Returns:
            Liste de bets avec kelly_adjusted
        """
        if not bets:
            return []
        
        # Compter les paris par ligue
        league_counts = defaultdict(int)
        market_counts = defaultdict(int)
        
        for bet in bets:
            league_counts[bet.get('league', 'Unknown')] += 1
            market_counts[bet.get('market', 'unknown')] += 1
        
        # Appliquer les pénalités
        adjusted_bets = []
        total_exposure = 0
        
        for bet in bets:
            league = bet.get('league', 'Unknown')
            market = bet.get('market', 'unknown')
            kelly_raw = bet.get('kelly_pct', 2.0)
            
            # Pénalité ligue
            league_penalty = cls.correlation_penalty(league_counts[league])
            
            # Pénalité marché
            market_penalty = cls.correlation_penalty(market_counts[market])
            
            # Pénalité combinée (prendre la plus restrictive)
            combined_penalty = min(league_penalty, market_penalty)
            
            # Kelly ajusté
            kelly_adjusted = kelly_raw * combined_penalty
            
            # Cap à 5% max par pari
            kelly_adjusted = min(kelly_adjusted, 5.0)
            
            adjusted_bet = {
                **bet,
                'kelly_raw': kelly_raw,
                'league_penalty': round(league_penalty, 2),
                'market_penalty': round(market_penalty, 2),
                'combined_penalty': round(combined_penalty, 2),
                'kelly_adjusted': round(kelly_adjusted, 2),
            }
            adjusted_bets.append(adjusted_bet)
            total_exposure += kelly_adjusted
        
        # Cap global à 15% d'exposition totale
        if total_exposure > 15:
            scale_factor = 15 / total_exposure
            for bet in adjusted_bets:
                bet['kelly_adjusted'] = round(bet['kelly_adjusted'] * scale_factor, 2)
                bet['global_scale'] = round(scale_factor, 2)
        
        return adjusted_bets
    
    @classmethod
    def analyze_portfolio_risk(cls, bets):
        """
        Analyse le risque global du portefeuille de paris
        """
        if not bets:
            return {'risk_level': 'NONE', 'exposure': 0}
        
        # Grouper par ligue et marché
        by_league = defaultdict(list)
        by_market = defaultdict(list)
        
        for bet in bets:
            by_league[bet.get('league', 'Unknown')].append(bet)
            by_market[bet.get('market', 'unknown')].append(bet)
        
        # Calculer l'exposition
        total_stake = sum(b.get('kelly_adjusted', b.get('kelly_pct', 2)) for b in bets)
        
        # Identifier les concentrations
        max_league_concentration = max(len(v) for v in by_league.values()) if by_league else 0
        max_market_concentration = max(len(v) for v in by_market.values()) if by_market else 0
        
        # Risque
        if max_league_concentration >= 4 or max_market_concentration >= 4:
            risk_level = 'HIGH'
            warning = f"⚠️ Concentration élevée: {max_league_concentration} sur même ligue, {max_market_concentration} sur même marché"
        elif max_league_concentration >= 3 or max_market_concentration >= 3:
            risk_level = 'MEDIUM'
            warning = f"⚡ Concentration modérée"
        else:
            risk_level = 'LOW'
            warning = "✅ Diversification OK"
        
        return {
            'total_bets': len(bets),
            'total_exposure': round(total_stake, 2),
            'by_league': {k: len(v) for k, v in by_league.items()},
            'by_market': {k: len(v) for k, v in by_market.items()},
            'max_league_concentration': max_league_concentration,
            'max_market_concentration': max_market_concentration,
            'risk_level': risk_level,
            'warning': warning,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# 4. TIME-DECAY DYNAMIQUE (COACH CHANGE)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

class DynamicTimeDecay:
    """
    Calcule le poids des matchs passés avec decay adaptatif
    
    Prend en compte:
    - Le temps écoulé (decay exponentiel standard)
    - Les changements de coach (reset brutal)
    - Le début de saison (plus de volatilité)
    """
    
    # Decay rate standard (par jour)
    DAILY_DECAY = 0.97  # 97% du poids conservé chaque jour
    
    # Multiplicateur après changement de coach
    COACH_CHANGE_FACTOR = 0.10  # Les données avant changement = 10% de poids
    
    @classmethod
    def calculate_match_weight(cls, match_date, current_date=None, 
                               coach_change_date=None, season_start_date=None):
        """
        Calcule le poids d'un match passé
        
        Args:
            match_date: Date du match
            current_date: Date actuelle (défaut: aujourd'hui)
            coach_change_date: Date du dernier changement de coach
            season_start_date: Date de début de saison
            
        Returns:
            float entre 0 et 1 représentant le poids
        """
        if current_date is None:
            current_date = datetime.now()
        
        # Convertir en datetime si nécessaire
        if isinstance(match_date, str):
            match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
        if isinstance(coach_change_date, str) and coach_change_date:
            coach_change_date = datetime.fromisoformat(coach_change_date.replace('Z', '+00:00'))
        
        # Nombre de jours depuis le match
        days_ago = (current_date - match_date).days
        if days_ago < 0:
            return 0  # Match dans le futur
        
        # Decay exponentiel standard
        weight = cls.DAILY_DECAY ** days_ago
        
        # Ajustement pour changement de coach
        if coach_change_date and match_date < coach_change_date:
            weight *= cls.COACH_CHANGE_FACTOR
        
        # Ajustement pour début de saison (les premiers matchs sont moins fiables)
        if season_start_date:
            if isinstance(season_start_date, str):
                season_start_date = datetime.fromisoformat(season_start_date)
            
            days_into_season = (match_date - season_start_date).days
            if days_into_season < 30:  # Premier mois
                weight *= 0.7  # Moins fiable
            elif days_into_season < 60:  # Deuxième mois
                weight *= 0.85
        
        return round(weight, 4)
    
    @classmethod
    def calculate_ema_with_coach(cls, values, dates, coach_change_date=None, span=5):
        """
        Calcule une EMA avec prise en compte du changement de coach
        
        Args:
            values: Liste de valeurs (xG, goals, etc.)
            dates: Liste de dates correspondantes
            coach_change_date: Date du changement de coach
            span: Période de l'EMA
            
        Returns:
            EMA ajustée
        """
        if not values:
            return 0
        
        # Calculer les poids pour chaque observation
        weights = []
        for date in dates:
            w = cls.calculate_match_weight(date, coach_change_date=coach_change_date)
            weights.append(w)
        
        # Normaliser les poids
        total_weight = sum(weights)
        if total_weight == 0:
            return sum(values) / len(values)  # Moyenne simple si tous poids = 0
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Moyenne pondérée
        weighted_avg = sum(v * w for v, w in zip(values, normalized_weights))
        
        return round(weighted_avg, 3)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# TESTS ET DÉMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

def demo():
    """Démonstration des fonctionnalités God Tier"""
    
    print("=" * 100)
    print("    🚀 QUANT GOD TIER - DÉMONSTRATION")
    print("=" * 100)
    
    # 1. Dixon-Coles
    print("\n" + "─" * 100)
    print("1️⃣ DIXON-COLES vs POISSON")
    print("─" * 100)
    
    home_xg, away_xg = 1.5, 1.2
    print(f"\n   Exemple: Home xG = {home_xg}, Away xG = {away_xg}")
    
    comparison = DixonColesModel.compare_with_poisson(home_xg, away_xg)
    print(f"\n   {'Score':<8} | {'Poisson':>10} | {'Dixon-Coles':>12} | {'Δ':>8}")
    print("   " + "─" * 45)
    for score, data in comparison.items():
        print(f"   {score:<8} | {data['poisson']:>9.2f}% | {data['dixon_coles']:>11.2f}% | {data['difference']:>+7.2f}%")
    
    probs = DixonColesModel.market_probabilities(home_xg, away_xg)
    print(f"\n   📊 Probabilités Dixon-Coles:")
    print(f"      Over 2.5: {probs['over_25']}% | Under 2.5: {probs['under_25']}%")
    print(f"      BTTS Yes: {probs['btts_yes']}% | BTTS No: {probs['btts_no']}%")
    print(f"      Home: {probs['home_win']}% | Draw: {probs['draw']}% | Away: {probs['away_win']}%")
    
    # 2. Liquidity-Weighted Steam
    print("\n" + "─" * 100)
    print("2️⃣ LIQUIDITY-WEIGHTED STEAM")
    print("─" * 100)
    
    examples = [
        (5.0, 24, 'Premier League'),
        (5.0, 24, 'Ligue 2'),
        (3.0, 6, 'Champions League'),
        (8.0, 48, 'soccer_poland_ekstraklasa'),
    ]
    
    print(f"\n   {'League':<25} | {'Shift':>6} | {'Hours':>6} | {'Tier':>4} | {'Weighted':>8} | {'Classification':<15}")
    print("   " + "─" * 80)
    for shift, hours, league in examples:
        result = LiquidityWeightedSteam.calculate_weighted_steam(shift, hours, league)
        print(f"   {league:<25} | {shift:>5.1f}% | {hours:>5.0f}h | {result['league_tier']:>4} | {result['weighted_steam']:>8.3f} | {result['classification']:<15}")
    
    # 3. Portfolio Kelly
    print("\n" + "─" * 100)
    print("3️⃣ PORTFOLIO KELLY")
    print("─" * 100)
    
    bets = [
        {'match': 'Arsenal vs Chelsea', 'league': 'Premier League', 'market': 'over_25', 'kelly_pct': 3.5},
        {'match': 'Liverpool vs Everton', 'league': 'Premier League', 'market': 'over_25', 'kelly_pct': 2.8},
        {'match': 'Man City vs Tottenham', 'league': 'Premier League', 'market': 'over_25', 'kelly_pct': 4.0},
        {'match': 'Bayern vs Dortmund', 'league': 'Bundesliga', 'market': 'btts_yes', 'kelly_pct': 3.0},
        {'match': 'Real vs Barca', 'league': 'La Liga', 'market': 'over_25', 'kelly_pct': 2.5},
    ]
    
    adjusted = PortfolioKelly.calculate_portfolio_kelly(bets)
    risk = PortfolioKelly.analyze_portfolio_risk(adjusted)
    
    print(f"\n   📊 Analyse du portefeuille:")
    print(f"      Total bets: {risk['total_bets']}")
    print(f"      Exposition totale: {risk['total_exposure']}%")
    print(f"      Risque: {risk['risk_level']} - {risk['warning']}")
    
    print(f"\n   {'Match':<30} | {'Kelly Raw':>10} | {'Penalty':>8} | {'Kelly Adj':>10}")
    print("   " + "─" * 65)
    for bet in adjusted:
        print(f"   {bet['match']:<30} | {bet['kelly_raw']:>9.1f}% | {bet['combined_penalty']:>7.2f}x | {bet['kelly_adjusted']:>9.1f}%")
    
    # 4. Time Decay
    print("\n" + "─" * 100)
    print("4️⃣ TIME-DECAY DYNAMIQUE")
    print("─" * 100)
    
    current = datetime.now()
    coach_change = current - timedelta(days=15)
    
    test_dates = [
        (current - timedelta(days=5), "Il y a 5 jours (après coach)"),
        (current - timedelta(days=20), "Il y a 20 jours (avant coach)"),
        (current - timedelta(days=60), "Il y a 60 jours (avant coach)"),
    ]
    
    print(f"\n   Changement de coach: il y a 15 jours")
    print(f"\n   {'Match':<35} | {'Poids sans coach':>15} | {'Poids avec coach':>15}")
    print("   " + "─" * 70)
    for date, desc in test_dates:
        weight_normal = DynamicTimeDecay.calculate_match_weight(date)
        weight_coach = DynamicTimeDecay.calculate_match_weight(date, coach_change_date=coach_change)
        print(f"   {desc:<35} | {weight_normal:>14.3f} | {weight_coach:>14.3f}")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    demo()

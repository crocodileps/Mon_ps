"""
Agent B Ferrari 2.0 : Spread Optimizer Paramétrable
Version enrichie avec facteurs additionnels et configuration dynamique
"""
import numpy as np
import pandas as pd
import psycopg2
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class SpreadOptimizerFerrari:
    """
    Agent B Ferrari 2.0 : Version paramétrable pour tests A/B
    
    Supporte injection dynamique de configuration pour tester différentes variations
    """
    
    def __init__(self, db_config: Dict, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'agent avec configuration dynamique
        
        Args:
            db_config: Configuration base de données
            config: Configuration Ferrari optionnelle
                {
                    'min_spread': float,
                    'confidence_threshold': float,
                    'enabled_factors': List[str],
                    'adjustments': List[str],
                    'kelly_fraction': float
                }
        """
        self.db_config = db_config
        self.name = "Spread Optimizer Ferrari 2.0"
        
        # Configuration par défaut (baseline)
        self.min_spread = 2.0
        self.confidence_threshold = 0.50  # 50%
        self.kelly_fraction_multiplier = 0.25  # Fractional Kelly 25%
        
        # Facteurs additionnels (désactivés par défaut)
        self.enabled_factors = []
        self.adjustments = []
        
        # Appliquer configuration Ferrari si fournie
        if config:
            self.apply_config(config)
            logger.info(f"Configuration Ferrari appliquée: {config}")
    
    def apply_config(self, config: Dict[str, Any]):
        """Applique une configuration dynamiquement"""
        if 'min_spread' in config:
            self.min_spread = config['min_spread']
        
        if 'confidence_threshold' in config:
            self.confidence_threshold = config['confidence_threshold']
        
        if 'enabled_factors' in config:
            self.enabled_factors = config['enabled_factors']
        
        if 'adjustments' in config:
            self.adjustments = config['adjustments']
        
        if 'kelly_fraction' in config:
            self.kelly_fraction_multiplier = config['kelly_fraction']
    
    def fetch_opportunities(self):
        """Récupère les opportunités actuelles"""
        conn = psycopg2.connect(**self.db_config)
        query = """
            SELECT
                sport,
                home_team,
                away_team,
                home_spread_pct,
                away_spread_pct,
                draw_spread_pct,
                bookmaker_count,
                max_home_odds,
                min_home_odds,
                max_away_odds,
                min_away_odds,
                max_draw_odds,
                min_draw_odds
            FROM v_current_opportunities
            WHERE GREATEST(
                home_spread_pct,
                away_spread_pct,
                COALESCE(draw_spread_pct, 0)
            ) >= %s
            ORDER BY GREATEST(
                home_spread_pct,
                away_spread_pct,
                COALESCE(draw_spread_pct, 0)
            ) DESC
        """
        df = pd.read_sql(query, conn, params=(self.min_spread,))
        conn.close()
        return df
    
    def calculate_kelly_criterion(self, odds: float, win_probability: float) -> float:
        """Calcule la fraction Kelly avec multiplicateur configurable"""
        if win_probability <= 0 or win_probability >= 1:
            return 0.0
        
        b = odds - 1
        p = win_probability
        q = 1 - p
        kelly = (b * p - q) / b
        
        # Appliquer fractional Kelly configurable
        return max(0, kelly * self.kelly_fraction_multiplier)
    
    def estimate_win_probability(
        self, 
        max_odds: float, 
        min_odds: float, 
        spread_pct: float,
        match_context: Optional[Dict] = None
    ) -> float:
        """
        Estime la probabilité de gagner avec facteurs additionnels
        
        Args:
            max_odds: Cote maximale
            min_odds: Cote minimale
            spread_pct: Spread en %
            match_context: Contexte additionnel (forme, blessures, météo, etc.)
        """
        avg_odds = (max_odds + min_odds) / 2
        implied_prob = 1 / avg_odds
        
        # Ajustement de base sur spread
        spread_factor = 1 + (spread_pct / 100)
        adjusted_prob = implied_prob * spread_factor
        
        # Appliquer facteurs additionnels si activés
        if match_context and self.enabled_factors:
            adjusted_prob = self._apply_additional_factors(
                adjusted_prob, 
                match_context
            )
        
        return min(adjusted_prob, 0.95)
    
    def _apply_additional_factors(
        self, 
        base_prob: float, 
        context: Dict
    ) -> float:
        """
        Applique les facteurs manquants identifiés par GPT-4o
        
        Facteurs supportés:
        - forme_récente_des_équipes
        - blessures_clés
        - conditions_météorologiques
        - historique_des_confrontations_directes
        """
        adjusted = base_prob
        
        # Facteur 1: Forme récente
        if 'forme_récente_des_équipes' in self.enabled_factors:
            recent_form = context.get('recent_form_advantage', 0)  # -1 à +1
            adjusted *= (1 + recent_form * 0.1)  # Max ±10%
            logger.debug(f"Forme récente appliquée: {recent_form}")
        
        # Facteur 2: Blessures clés
        if 'blessures_clés' in self.enabled_factors:
            injury_impact = context.get('injury_impact', 0)  # -1 à +1
            adjusted *= (1 + injury_impact * 0.08)  # Max ±8%
            logger.debug(f"Impact blessures: {injury_impact}")
        
        # Facteur 3: Météo
        if 'conditions_météorologiques' in self.enabled_factors:
            weather_factor = context.get('weather_advantage', 0)  # -1 à +1
            adjusted *= (1 + weather_factor * 0.05)  # Max ±5%
            logger.debug(f"Météo appliquée: {weather_factor}")
        
        # Facteur 4: Historique H2H
        if 'historique_des_confrontations_directes' in self.enabled_factors:
            h2h_advantage = context.get('h2h_win_rate', 0.5) - 0.5  # Centré sur 0
            adjusted *= (1 + h2h_advantage * 0.15)  # Max ±7.5%
            logger.debug(f"Historique H2H: {h2h_advantage}")
        
        return min(adjusted, 0.95)
    
    def calculate_expected_value(self, odds: float, win_prob: float) -> float:
        """Calcule l'EV (Expected Value)"""
        return (odds * win_prob) - 1
    
    def generate_signals(
        self, 
        top_n: int = 10,
        match_contexts: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """
        Génère des signaux optimisés avec configuration Ferrari
        
        Args:
            top_n: Nombre de signaux à générer
            match_contexts: Contextes additionnels par match
        
        Returns:
            Liste de signaux avec taille de pari recommandée
        """
        logger.info(f"[{self.name}] Génération signaux avec config Ferrari...")
        logger.info(f"  • Min spread: {self.min_spread}%")
        logger.info(f"  • Seuil confiance: {self.confidence_threshold*100}%")
        logger.info(f"  • Facteurs activés: {len(self.enabled_factors)}")
        
        df = self.fetch_opportunities()
        
        if len(df) == 0:
            logger.warning(f"[{self.name}] Aucune opportunité trouvée")
            return []
        
        signals = []
        
        for idx, row in df.head(top_n).iterrows():
            # Déterminer la meilleure opportunité
            spreads = {
                'home': row['home_spread_pct'],
                'away': row['away_spread_pct'],
                'draw': row.get('draw_spread_pct', 0)
            }
            
            best_outcome = max(spreads, key=spreads.get)
            best_spread = spreads[best_outcome]
            
            # Récupérer cotes
            if best_outcome == 'home':
                max_odds = row['max_home_odds']
                min_odds = row['min_home_odds']
                direction = 'BACK_HOME'
            elif best_outcome == 'away':
                max_odds = row['max_away_odds']
                min_odds = row['min_away_odds']
                direction = 'BACK_AWAY'
            else:
                max_odds = row['max_draw_odds']
                min_odds = row['min_draw_odds']
                direction = 'BACK_DRAW'
            
            # Récupérer contexte additionnel si disponible
            match_key = f"{row['home_team']}_vs_{row['away_team']}"
            context = match_contexts.get(match_key) if match_contexts else None
            
            # Estimer probabilité avec facteurs
            win_prob = self.estimate_win_probability(
                max_odds, min_odds, best_spread, context
            )
            
            # Calculer Kelly
            kelly_fraction = self.calculate_kelly_criterion(max_odds, win_prob)
            
            # Calculer EV
            ev = self.calculate_expected_value(max_odds, win_prob)
            
            # Confiance basée sur spread et EV
            confidence = min((best_spread * 10) + (ev * 50), 100) / 100
            
            # Filtrer selon seuil de confiance Ferrari
            if confidence < self.confidence_threshold:
                logger.debug(f"Match filtré: {match_key} - Confiance {confidence:.1%} < {self.confidence_threshold:.1%}")
                continue
            
            signal = {
                'agent': self.name,
                'match': f"{row['home_team']} vs {row['away_team']}",
                'sport': row['sport'],
                'direction': direction,
                'confidence': confidence * 100,
                'odds': {
                    'max': max_odds,
                    'min': min_odds,
                    'avg': (max_odds + min_odds) / 2
                },
                'spread_pct': best_spread,
                'win_probability': win_prob,
                'kelly_fraction': kelly_fraction,
                'expected_value': ev,
                'recommended_stake_pct': kelly_fraction * 100,
                'bookmaker_count': row['bookmaker_count'],
                'factors_used': self.enabled_factors,
                'reason': self._generate_reason(best_spread, ev, kelly_fraction)
            }
            
            signals.append(signal)
        
        logger.info(f"[{self.name}] Généré {len(signals)} signaux (sur {len(df)} opportunités)")
        
        return signals
    
    def _generate_reason(self, spread: float, ev: float, kelly: float) -> str:
        """Génère explication du signal"""
        factors_text = f" + {len(self.enabled_factors)} facteurs" if self.enabled_factors else ""
        return f"Spread {spread:.2f}%, EV={ev:.3f}, Kelly={kelly*100:.1f}%{factors_text}"


"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - ORCHESTRATEUR PRINCIPAL
   Interface unifiée pour prédictions et analyse
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import sys

sys.path.append(str(Path(__file__).parent))
from config import MARKETS, THRESHOLDS, MODEL_DIR, VERSION
from data.loader import DefenseDataLoader
from features.engineer import FeatureEngineer
from models.trainer import ModelTrainer


class AgentDefenseV2:
    """
    Agent Défense 2.0 - Orchestrateur principal.
    
    CAPABILITIES:
    - Chargement automatique des données (15 sources)
    - Extraction de ~180 features par match
    - Prédiction sur 27 marchés
    - Calcul d'edge et Kelly
    - Recommandations de paris
    
    USAGE:
        agent = AgentDefenseV2()
        agent.initialize()
        predictions = agent.predict_match('Arsenal', 'Chelsea', 'Michael Oliver')
    """
    
    def __init__(self):
        self.loader = None
        self.engineer = None
        self.trainer = None
        self.is_initialized = False
        self.version = VERSION
    
    def initialize(self, load_models: bool = True, model_path: str = None) -> None:
        """
        Initialise l'agent avec toutes les données.
        
        Args:
            load_models: Charger les modèles pré-entraînés
            model_path: Chemin vers les modèles (optionnel)
        """
        print("=" * 80)
        print(f"🏦 AGENT DÉFENSE V{self.version} - INITIALISATION")
        print("=" * 80)
        
        # 1. Charger les données
        self.loader = DefenseDataLoader()
        self.loader.load_all()
        
        # 2. Créer le feature engineer
        self.engineer = FeatureEngineer(self.loader)
        
        # 3. Charger ou créer les modèles
        self.trainer = ModelTrainer()
        
        if load_models and model_path:
            self.trainer.load_models(model_path)
        
        self.is_initialized = True
        print("\n✅ Agent initialisé")
    
    def train(self, n_matches: int = None, save: bool = True) -> Dict:
        """
        Entraîne les modèles sur les données historiques.
        
        Args:
            n_matches: Nombre de matchs pour l'entraînement (None = tous)
            save: Sauvegarder les modèles
        
        Returns:
            Métriques d'entraînement
        """
        if not self.is_initialized:
            raise ValueError("Agent not initialized. Call initialize() first.")
        
        print("\n" + "=" * 80)
        print("��️ ENTRAÎNEMENT DES MODÈLES")
        print("=" * 80)
        
        # Récupérer les matchs
        matches = self.loader.get_matches()
        if n_matches:
            matches = matches.head(n_matches)
        
        print(f"\n📊 Construction dataset ({len(matches)} matchs)...")
        X, y = self.engineer.build_dataset(matches)
        
        print(f"   • Features: {X.shape[1]}")
        print(f"   • Targets: {y.shape[1]}")
        
        # Entraîner
        results = self.trainer.train_all_markets(X, y)
        
        # Sauvegarder
        if save:
            self.trainer.save_models()
        
        return results
    
    def predict_match(self, 
                      home_team: str, 
                      away_team: str,
                      referee: str = None,
                      league: str = None,
                      markets: List[str] = None) -> Dict[str, Any]:
        """
        Prédit tous les marchés pour un match.
        
        Args:
            home_team: Équipe domicile
            away_team: Équipe extérieure
            referee: Arbitre (optionnel)
            league: Ligue (optionnel)
            markets: Marchés spécifiques (None = tous)
        
        Returns:
            Dict avec prédictions par marché
        """
        if not self.is_initialized:
            raise ValueError("Agent not initialized")
        
        # Extraire features
        features = self.engineer.extract_match_features(
            home_team, away_team, referee, league
        )
        X = pd.DataFrame([features])
        
        # Prédire chaque marché
        predictions = {
            'match': {
                'home': home_team,
                'away': away_team,
                'referee': referee,
                'league': league,
                'timestamp': datetime.now().isoformat()
            },
            'predictions': {},
            'recommendations': []
        }
        
        markets_to_predict = markets or list(self.trainer.models.keys())
        
        for market in markets_to_predict:
            if market not in self.trainer.models:
                continue
            
            try:
                result = self.trainer.predict(market, X)
                predictions['predictions'][market] = result
                
                # Calculer l'edge si classification
                if 'probability' in result:
                    prob = result['probability']
                    # Implied odds (avec marge 5%)
                    implied_prob = prob
                    fair_odds = 1 / implied_prob if implied_prob > 0 else 10
                    
                    result['fair_odds'] = round(fair_odds, 2)
                    result['edge'] = round((prob - 0.5) * 100, 2)  # Simplified
                    
                    # Recommandation si edge > seuil
                    if result['confidence'] > 0.1:  # Confidence > 55%
                        kelly = max(0, (prob * fair_odds - 1) / (fair_odds - 1))
                        kelly = min(kelly, THRESHOLDS['max_kelly'])
                        
                        if kelly > 0.01:
                            predictions['recommendations'].append({
                                'market': market,
                                'prediction': 'YES' if result['prediction'] == 1 else 'NO',
                                'probability': round(prob * 100, 1),
                                'fair_odds': round(fair_odds, 2),
                                'kelly': round(kelly * 100, 2),
                                'confidence': round(result['confidence'] * 100, 1)
                            })
            
            except Exception as e:
                predictions['predictions'][market] = {'error': str(e)}
        
        # Trier les recommandations par Kelly
        predictions['recommendations'] = sorted(
            predictions['recommendations'],
            key=lambda x: -x['kelly']
        )
        
        return predictions
    
    def print_predictions(self, predictions: Dict) -> None:
        """Affiche les prédictions de manière formatée."""
        match = predictions['match']
        
        print("\n" + "=" * 80)
        print(f"🏦 PRÉDICTIONS - {match['home']} vs {match['away']}")
        if match['referee']:
            print(f"   Arbitre: {match['referee']}")
        print("=" * 80)
        
        # Classification
        print("\n📊 MARCHÉS CLASSIFICATION:")
        print(f"   {'Marché':<25} {'Prob':>8} {'Pred':>8} {'Fair Odds':>10} {'Edge':>8}")
        print("   " + "-" * 70)
        
        for market, data in predictions['predictions'].items():
            if 'error' in data:
                print(f"   {market:<25} ❌ {data['error']}")
            elif 'probability' in data:
                prob = data.get('probability', 0.5) * 100
                pred = 'YES' if data.get('prediction', 0) == 1 else 'NO'
                fair = data.get('fair_odds', '-')
                edge = data.get('edge', 0)
                print(f"   {market:<25} {prob:>7.1f}% {pred:>8} {fair:>10} {edge:>7.1f}%")
            elif 'value' in data:
                # Régression
                print(f"   {market:<25} Value: {data['value']:.2f}")
        
        # Recommandations
        if predictions['recommendations']:
            print("\n🎯 RECOMMANDATIONS:")
            print(f"   {'Marché':<20} {'Pred':>6} {'Prob':>8} {'Fair':>8} {'Kelly':>8}")
            print("   " + "-" * 55)
            
            for rec in predictions['recommendations'][:5]:
                print(f"   {rec['market']:<20} {rec['prediction']:>6} {rec['probability']:>7.1f}% {rec['fair_odds']:>8.2f} {rec['kelly']:>7.2f}%")
        else:
            print("\n   ⚠️ Aucune recommandation (edge insuffisant)")
    
    def get_team_profile(self, team_name: str) -> Dict:
        """Retourne le profil complet d'une équipe."""
        if not self.is_initialized:
            raise ValueError("Agent not initialized")
        
        return self.loader.get_team_data(team_name)
    
    def get_available_markets(self) -> List[str]:
        """Retourne la liste des marchés disponibles."""
        return list(self.trainer.models.keys()) if self.trainer else list(MARKETS.keys())
    
    def get_model_metrics(self) -> Dict:
        """Retourne les métriques des modèles entraînés."""
        return self.trainer.metrics if self.trainer else {}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent Défense 2.0')
    parser.add_argument('--train', action='store_true', help='Entraîner les modèles')
    parser.add_argument('--predict', nargs=2, metavar=('HOME', 'AWAY'), help='Prédire un match')
    parser.add_argument('--referee', type=str, help='Arbitre')
    parser.add_argument('--matches', type=int, default=2000, help='Nombre de matchs pour entraînement')
    
    args = parser.parse_args()
    
    agent = AgentDefenseV2()
    agent.initialize(load_models=False)
    
    if args.train:
        agent.train(n_matches=args.matches)
    
    if args.predict:
        if not agent.trainer.models:
            print("⚠️ Modèles non entraînés. Exécutez --train d'abord.")
        else:
            predictions = agent.predict_match(
                args.predict[0], 
                args.predict[1],
                referee=args.referee
            )
            agent.print_predictions(predictions)

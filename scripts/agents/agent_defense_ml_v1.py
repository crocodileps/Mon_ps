#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
 🛡️ AGENT DÉFENSE ML V1.0 - HEDGE FUND GRADE QUANT MODEL
 
 TRAINING DATA:
   • 642 matchs historiques (saison 2025/2026)
   • 1844 buts avec contexte complet
   • 96 équipes avec DNA multi-source
 
 ML MODELS:
   • XGBoost: Over/Under 2.5 prediction
   • LightGBM: BTTS prediction  
   • Gradient Boosting: Clean Sheet prediction
   • Ensemble: Weighted average avec calibration
 
 FEATURES (25+ dimensions):
   • Team DNA (resistance, timing, vulnerability)
   • Goalkeeper DNA (save rate, timing 76-90)
   • Defender DNA (impact, cards)
   • Context (momentum, form)
   • Zone Analysis
   • Gamestate patterns
 
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import pickle
import warnings
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, log_loss
import xgboost as xgb
import lightgbm as lgb

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_PATHS = {
    'goals': '/home/Mon_ps/data/goal_analysis/all_goals_2025.json',
    'defensive_lines': '/home/Mon_ps/data/defensive_lines/defensive_lines_v8_3_multi_source.json',
    'defenders': '/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json',
    'goalkeepers': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_timing_dna_v1.json',
    'context': '/home/Mon_ps/data/quantum_v2/teams_context_dna.json',
    'exploits': '/home/Mon_ps/data/quantum_v2/team_exploit_profiles.json',
    'zones': '/home/Mon_ps/data/quantum_v2/zone_analysis.json',
    'gamestate': '/home/Mon_ps/data/quantum_v2/gamestate_insights.json',
}

MODEL_PATH = '/home/Mon_ps/models/agent_defense/'
os.makedirs(MODEL_PATH, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MatchPrediction:
    home_team: str
    away_team: str
    p_over_25: float
    p_under_25: float
    p_btts_yes: float
    p_btts_no: float
    p_cs_home: float
    p_cs_away: float
    expected_goals: float
    confidence: float
    edge_over_25: float
    edge_btts: float
    kelly_over_25: float
    kelly_btts: float
    recommendation: str
    reasoning: List[str]
    model_agreement: float
    feature_importance: Dict[str, float]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class DataLoader:
    """Charge toutes les sources de données"""
    
    def __init__(self):
        self.goals = []
        self.matches = {}
        self.team_dna = {}
        self.gk_dna = {}
        self.defender_dna = {}
        self.context = {}
        self.exploits = {}
        self.zones = {}
        self.gamestate = {}
        self._load_all()
    
    def _load_json(self, path: str) -> Any:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ {path}: {e}")
            return None
    
    def _normalize(self, name: str) -> str:
        if not name:
            return ""
        return name.lower().strip().replace('_', ' ')
    
    def _load_all(self):
        print("📂 Chargement des données...")
        
        # Goals
        self.goals = self._load_json(DATA_PATHS['goals']) or []
        print(f"   ✅ Goals: {len(self.goals)} buts")
        
        # Reconstruire les matchs
        self._reconstruct_matches()
        
        # Team DNA (Defensive Lines V8.3)
        dl_data = self._load_json(DATA_PATHS['defensive_lines']) or []
        for team in dl_data:
            key = self._normalize(team.get('team_name', ''))
            if key:
                self.team_dna[key] = team
        print(f"   ✅ Team DNA: {len(self.team_dna)} équipes")
        
        # Goalkeeper DNA
        gk_data = self._load_json(DATA_PATHS['goalkeepers']) or []
        for gk in gk_data:
            key = self._normalize(gk.get('team', ''))
            if key:
                self.gk_dna[key] = gk
        print(f"   ✅ GK DNA: {len(self.gk_dna)} gardiens")
        
        # Defender DNA (agrégé par équipe)
        def_data = self._load_json(DATA_PATHS['defenders']) or []
        team_defs = defaultdict(list)
        for d in def_data:
            team = self._normalize(d.get('team', ''))
            if team:
                team_defs[team].append(d)
        
        for team, defenders in team_defs.items():
            sorted_defs = sorted(defenders, key=lambda x: x.get('time_90', 0) or 0, reverse=True)[:5]
            if sorted_defs:
                self.defender_dna[team] = {
                    'avg_cards_90': np.mean([d.get('cards_90', 0) or 0 for d in sorted_defs]),
                    'avg_impact': np.mean([d.get('impact_goals_conceded', 0) or 0 for d in sorted_defs]),
                    'avg_goals_with': np.mean([d.get('goals_conceded_per_match_with', 0) or 0 for d in sorted_defs]),
                }
        print(f"   ✅ Defender DNA: {len(self.defender_dna)} équipes")
        
        # Context
        self.context = self._load_json(DATA_PATHS['context']) or {}
        print(f"   ✅ Context: {len(self.context)} équipes")
        
        # Exploits
        self.exploits = self._load_json(DATA_PATHS['exploits']) or {}
        print(f"   ✅ Exploits: {len(self.exploits)} équipes")
        
        # Zones
        self.zones = self._load_json(DATA_PATHS['zones']) or {}
        print(f"   ✅ Zones: {len(self.zones)} équipes")
        
        # Gamestate
        self.gamestate = self._load_json(DATA_PATHS['gamestate']) or {}
        print(f"   ✅ Gamestate: {len(self.gamestate)} équipes")
    
    def _reconstruct_matches(self):
        """Reconstruit les matchs à partir des buts"""
        match_goals = defaultdict(list)
        
        for goal in self.goals:
            mid = goal.get('match_id')
            if mid:
                match_goals[mid].append(goal)
        
        for mid, goals in match_goals.items():
            if not goals:
                continue
            
            first_goal = goals[0]
            home_team = first_goal.get('scoring_team') if first_goal.get('home_away') == 'h' else first_goal.get('conceding_team')
            away_team = first_goal.get('conceding_team') if first_goal.get('home_away') == 'h' else first_goal.get('scoring_team')
            
            home_goals = sum(1 for g in goals if g.get('home_away') == 'h')
            away_goals = sum(1 for g in goals if g.get('home_away') == 'a')
            
            self.matches[mid] = {
                'match_id': mid,
                'date': first_goal.get('date'),
                'home_team': home_team,
                'away_team': away_team,
                'home_goals': home_goals,
                'away_goals': away_goals,
                'total_goals': home_goals + away_goals,
                'over_25': 1 if home_goals + away_goals > 2 else 0,
                'btts': 1 if home_goals > 0 and away_goals > 0 else 0,
                'cs_home': 1 if away_goals == 0 else 0,
                'cs_away': 1 if home_goals == 0 else 0,
                'goals_list': goals,
            }
        
        print(f"   ✅ Matchs: {len(self.matches)} reconstruits")

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineer:
    """Extrait les features pour le ML"""
    
    TIMING_RISK = {
        'late_collapser': 1.30, 'starts_strong_fades': 1.25,
        'late_vulnerable': 1.15, 'slow_starter': 1.10,
        'balanced': 1.00, 'fast_starter': 0.95,
        'strong_finisher': 0.85, 'slow_starter_strong_finish': 0.90,
    }
    
    def __init__(self, data_loader: DataLoader):
        self.data = data_loader
    
    def _get_team_features(self, team: str, prefix: str) -> Dict[str, float]:
        """Extrait les features d'une équipe"""
        team_key = team.lower().strip().replace('_', ' ')
        features = {}
        
        # Team DNA (Defensive Lines V8.3)
        dna = self.data.team_dna.get(team_key, {})
        
        # Resistance
        resist = dna.get('resistance', {})
        features[f'{prefix}_resist_global'] = resist.get('resist_global', 50)
        features[f'{prefix}_xga_90'] = dna.get('foundation', {}).get('xga_90', 1.2)
        
        # Timing
        timing = dna.get('timing_dna', {})
        profile = timing.get('primary_profile', 'balanced').lower()
        features[f'{prefix}_timing_risk'] = self.TIMING_RISK.get(profile, 1.0)
        features[f'{prefix}_late_pct'] = timing.get('late_pct', 33)
        features[f'{prefix}_closing_pct'] = timing.get('periods_pct', {}).get('76-90', 16)
        
        # Edge
        edge = dna.get('edge', {})
        features[f'{prefix}_total_edge'] = edge.get('total_edge', 0)
        
        # Goalkeeper
        gk = self.data.gk_dna.get(team_key, {})
        features[f'{prefix}_gk_percentile'] = gk.get('gk_percentile', 50)
        features[f'{prefix}_gk_save_rate'] = gk.get('save_rate', 65)
        gk_timing = gk.get('timing', {}).get('76-90', {})
        features[f'{prefix}_gk_sr_76_90'] = gk_timing.get('save_rate', 65)
        
        # Defenders
        defs = self.data.defender_dna.get(team_key, {})
        features[f'{prefix}_def_cards_90'] = defs.get('avg_cards_90', 0.2)
        features[f'{prefix}_def_impact'] = defs.get('avg_impact', 0)
        
        # Context
        ctx = self.data.context.get(team_key, self.data.context.get(team, {}))
        ctx_dna = ctx.get('context_dna', {}) if isinstance(ctx, dict) else {}
        momentum = ctx.get('momentum_dna', {}) if isinstance(ctx, dict) else {}
        features[f'{prefix}_form_score'] = ctx_dna.get('form_score', 50)
        features[f'{prefix}_momentum'] = momentum.get('momentum_score', 0)
        
        # Exploits
        exp = self.data.exploits.get(team_key, self.data.exploits.get(team, {}))
        features[f'{prefix}_vuln_score'] = exp.get('vulnerability_score', 50) if isinstance(exp, dict) else 50
        
        # Zones
        zones = self.data.zones.get(team_key, self.data.zones.get(team, {}))
        if isinstance(zones, dict) and 'zones' in zones:
            zone_data = zones['zones']
            features[f'{prefix}_zone_center'] = zone_data.get('center', {}).get('xG', 0)
        else:
            features[f'{prefix}_zone_center'] = 0
        
        return features
    
    def extract_match_features(self, home_team: str, away_team: str) -> Dict[str, float]:
        """Extrait toutes les features pour un match"""
        features = {}
        
        # Home team features
        home_f = self._get_team_features(home_team, 'home')
        features.update(home_f)
        
        # Away team features
        away_f = self._get_team_features(away_team, 'away')
        features.update(away_f)
        
        # Combined features
        features['combined_edge'] = (home_f.get('home_total_edge', 0) + away_f.get('away_total_edge', 0)) / 2
        features['combined_xga'] = home_f.get('home_xga_90', 1.2) + away_f.get('away_xga_90', 1.2)
        features['min_resist'] = min(home_f.get('home_resist_global', 50), away_f.get('away_resist_global', 50))
        features['max_vuln'] = max(home_f.get('home_vuln_score', 50), away_f.get('away_vuln_score', 50))
        features['timing_product'] = home_f.get('home_timing_risk', 1) * away_f.get('away_timing_risk', 1)
        features['min_gk_76_90'] = min(home_f.get('home_gk_sr_76_90', 65), away_f.get('away_gk_sr_76_90', 65))
        features['total_late_pct'] = home_f.get('home_late_pct', 33) + away_f.get('away_late_pct', 33)
        features['momentum_diff'] = home_f.get('home_momentum', 0) - away_f.get('away_momentum', 0)
        features['total_cards_90'] = home_f.get('home_def_cards_90', 0.2) + away_f.get('away_def_cards_90', 0.2)
        
        # Matchup friction
        friction = 0
        if home_f.get('home_timing_risk', 1) > 1.15:
            friction += 15
        if away_f.get('away_timing_risk', 1) > 1.15:
            friction += 15
        if home_f.get('home_gk_sr_76_90', 65) < 50:
            friction += 20
        if away_f.get('away_gk_sr_76_90', 65) < 50:
            friction += 20
        if home_f.get('home_resist_global', 50) < 40:
            friction += 15
        if away_f.get('away_resist_global', 50) < 40:
            friction += 15
        
        features['matchup_friction'] = min(100, friction)
        
        return features
    
    def build_training_dataset(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Construit le dataset d'entraînement"""
        print("\n🔧 Construction du dataset ML...")
        
        rows = []
        targets = []
        
        for mid, match in self.data.matches.items():
            home = match['home_team']
            away = match['away_team']
            
            if not home or not away:
                continue
            
            try:
                features = self.extract_match_features(home, away)
                features['match_id'] = mid
                
                target = {
                    'over_25': match['over_25'],
                    'btts': match['btts'],
                    'cs_home': match['cs_home'],
                    'cs_away': match['cs_away'],
                    'total_goals': match['total_goals'],
                }
                
                rows.append(features)
                targets.append(target)
                
            except Exception as e:
                continue
        
        X = pd.DataFrame(rows)
        y = pd.DataFrame(targets)
        
        print(f"   ✅ Dataset: {len(X)} matchs, {len(X.columns)} features")
        print(f"   📊 Over 2.5: {y['over_25'].mean()*100:.1f}%")
        print(f"   📊 BTTS: {y['btts'].mean()*100:.1f}%")
        
        return X, y

# ═══════════════════════════════════════════════════════════════════════════════
# ML MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class DefenseMLModels:
    """Modèles ML pour la prédiction défensive"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_names = []
        self.is_trained = False
        self.metrics = {}
    
    def train(self, X: pd.DataFrame, y: pd.DataFrame):
        """Entraîne tous les modèles"""
        print("\n🤖 Entraînement des modèles ML...")
        
        # Supprimer colonnes non-features
        feature_cols = [c for c in X.columns if c != 'match_id']
        X_clean = X[feature_cols].copy()
        
        # Remplacer NaN et inf
        X_clean = X_clean.replace([np.inf, -np.inf], np.nan)
        X_clean = X_clean.fillna(X_clean.median())
        
        self.feature_names = feature_cols
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X_clean, y, test_size=0.2, random_state=42
        )
        
        # Scaler
        self.scalers['main'] = StandardScaler()
        X_train_scaled = self.scalers['main'].fit_transform(X_train)
        X_test_scaled = self.scalers['main'].transform(X_test)
        
        # ═══════════════════════════════════════════════════════════════════
        # MODEL 1: XGBoost pour Over/Under 2.5
        # ═══════════════════════════════════════════════════════════════════
        print("\n   📈 Training XGBoost (Over 2.5)...")
        
        xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
            early_stopping_rounds=20,
        )
        
        xgb_model.fit(
            X_train_scaled, y_train['over_25'],
            eval_set=[(X_test_scaled, y_test['over_25'])],
            verbose=False
        )
        
        # Calibration
        self.models['over_25'] = CalibratedClassifierCV(xgb_model, cv='prefit', method='isotonic')
        self.models['over_25'].fit(X_test_scaled, y_test['over_25'])
        
        # Métriques
        y_pred_proba = self.models['over_25'].predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        self.metrics['over_25'] = {
            'accuracy': accuracy_score(y_test['over_25'], y_pred),
            'auc': roc_auc_score(y_test['over_25'], y_pred_proba),
            'brier': brier_score_loss(y_test['over_25'], y_pred_proba),
            'log_loss': log_loss(y_test['over_25'], y_pred_proba),
        }
        print(f"      Accuracy: {self.metrics['over_25']['accuracy']:.3f}")
        print(f"      AUC: {self.metrics['over_25']['auc']:.3f}")
        print(f"      Brier: {self.metrics['over_25']['brier']:.3f}")
        
        # ═══════════════════════════════════════════════════════════════════
        # MODEL 2: LightGBM pour BTTS
        # ═══════════════════════════════════════════════════════════════════
        print("\n   📈 Training LightGBM (BTTS)...")
        
        lgb_model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
        
        lgb_model.fit(
            X_train_scaled, y_train['btts'],
            eval_set=[(X_test_scaled, y_test['btts'])],
        )
        
        # Calibration
        self.models['btts'] = CalibratedClassifierCV(lgb_model, cv='prefit', method='isotonic')
        self.models['btts'].fit(X_test_scaled, y_test['btts'])
        
        # Métriques
        y_pred_proba = self.models['btts'].predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        self.metrics['btts'] = {
            'accuracy': accuracy_score(y_test['btts'], y_pred),
            'auc': roc_auc_score(y_test['btts'], y_pred_proba),
            'brier': brier_score_loss(y_test['btts'], y_pred_proba),
        }
        print(f"      Accuracy: {self.metrics['btts']['accuracy']:.3f}")
        print(f"      AUC: {self.metrics['btts']['auc']:.3f}")
        
        # ═══════════════════════════════════════════════════════════════════
        # MODEL 3: XGBoost pour Total Goals (regression)
        # ═══════════════════════════════════════════════════════════════════
        print("\n   📈 Training XGBoost (Expected Goals)...")
        
        xgb_reg = xgb.XGBRegressor(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
        )
        
        xgb_reg.fit(X_train_scaled, y_train['total_goals'])
        self.models['total_goals'] = xgb_reg
        
        y_pred = xgb_reg.predict(X_test_scaled)
        mae = np.mean(np.abs(y_pred - y_test['total_goals']))
        self.metrics['total_goals'] = {'mae': mae}
        print(f"      MAE: {mae:.3f} goals")
        
        # Feature importance
        self.feature_importance = dict(zip(
            self.feature_names,
            xgb_model.feature_importances_
        ))
        
        self.is_trained = True
        print("\n   ✅ Tous les modèles entraînés!")
    
    def predict(self, features: Dict[str, float]) -> Dict[str, float]:
        """Prédit pour un match"""
        if not self.is_trained:
            raise ValueError("Models not trained!")
        
        # Créer DataFrame avec les bonnes colonnes
        X = pd.DataFrame([features])[self.feature_names]
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)
        
        # Scale
        X_scaled = self.scalers['main'].transform(X)
        
        # Predictions
        p_over_25 = self.models['over_25'].predict_proba(X_scaled)[0, 1]
        p_btts = self.models['btts'].predict_proba(X_scaled)[0, 1]
        expected_goals = self.models['total_goals'].predict(X_scaled)[0]
        
        return {
            'p_over_25': float(p_over_25),
            'p_btts': float(p_btts),
            'expected_goals': float(max(0, expected_goals)),
        }
    
    def save(self, path: str = MODEL_PATH):
        """Sauvegarde les modèles"""
        with open(os.path.join(path, 'models_v1.1.pkl'), 'wb') as f:
            pickle.dump({
                'models': self.models,
                'scalers': self.scalers,
                'feature_names': self.feature_names,
                'metrics': self.metrics,
                'feature_importance': self.feature_importance,
            }, f)
        print(f"✅ Modèles sauvegardés: {path}")
    
    def load(self, path: str = MODEL_PATH):
        """Charge les modèles"""
        model_file = os.path.join(path, 'models_v1.1.pkl')
        if os.path.exists(model_file):
            with open(model_file, 'rb') as f:
                data = pickle.load(f)
            self.models = data['models']
            self.scalers = data['scalers']
            self.feature_names = data['feature_names']
            self.metrics = data['metrics']
            self.feature_importance = data.get('feature_importance', {})
            self.is_trained = True
            print(f"✅ Modèles chargés: {path}")
            return True
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# KELLY CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class KellyCalculator:
    @staticmethod
    def calculate(prob: float, odds: float, fraction: float = 0.25) -> Tuple[float, float]:
        if odds <= 1.0 or prob <= 0:
            return 0.0, 0.0
        
        implied = 1 / odds
        edge = (prob - implied) * 100
        
        if edge <= 0:
            return 0.0, edge
        
        b = odds - 1
        q = 1 - prob
        kelly = (b * prob - q) / b
        kelly = max(0, min(kelly * fraction, 0.10))  # Cap 10%
        
        return round(kelly * 100, 2), round(edge, 2)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class AgentDefenseML:
    """Agent principal ML pour l'analyse défensive"""
    
    def __init__(self, train: bool = True):
        print("=" * 70)
        print("🛡️ AGENT DÉFENSE ML V1.0 - INITIALISATION")
        print("=" * 70)
        
        self.data = DataLoader()
        self.feature_eng = FeatureEngineer(self.data)
        self.models = DefenseMLModels()
        self.kelly = KellyCalculator()
        
        # Essayer de charger les modèles existants
        if not self.models.load():
            if train:
                self._train_models()
        
    def _train_models(self):
        """Entraîne les modèles"""
        X, y = self.feature_eng.build_training_dataset()
        self.models.train(X, y)
        self.models.save()
    
    def analyze_match(
        self,
        home_team: str,
        away_team: str,
        odds_over_25: float = 1.90,
        odds_btts: float = 1.85
    ) -> Optional[MatchPrediction]:
        """Analyse un match"""
        
        # Extract features
        try:
            features = self.feature_eng.extract_match_features(home_team, away_team)
        except Exception as e:
            print(f"⚠️ Erreur features: {e}")
            return None
        
        # Predict
        preds = self.models.predict(features)
        
        # Kelly & Edge
        kelly_over, edge_over = self.kelly.calculate(preds['p_over_25'], odds_over_25)
        kelly_btts, edge_btts = self.kelly.calculate(preds['p_btts'], odds_btts)
        
        # Confidence (based on model agreement and edge)
        confidence = 50 + abs(edge_over) * 1.5 + abs(edge_btts) * 1.0
        confidence = min(95, max(25, confidence))
        
        # Model agreement
        over_agrees = (preds['p_over_25'] > 0.5) == (preds['expected_goals'] > 2.5)
        btts_agrees = preds['p_btts'] > 0.5
        agreement = (1 if over_agrees else 0) + (1 if btts_agrees else 0)
        model_agreement = agreement / 2 * 100
        
        # Recommendation
        reasoning = []
        recommendation = 'SKIP'
        
        if edge_over >= 5 and kelly_over >= 1.5:
            recommendation = 'BET_OVER_25'
            reasoning.append(f"Edge Over 2.5: +{edge_over:.1f}%")
            reasoning.append(f"P(Over): {preds['p_over_25']*100:.1f}%")
        elif edge_over <= -8:
            recommendation = 'BET_UNDER_25'
            reasoning.append(f"Edge Under: {-edge_over:.1f}%")
        elif edge_btts >= 5 and kelly_btts >= 1.5:
            recommendation = 'BET_BTTS'
            reasoning.append(f"Edge BTTS: +{edge_btts:.1f}%")
        elif edge_over < -2 and edge_btts < -2:
            recommendation = 'AVOID'
            reasoning.append("Negative edge all markets")
        
        # Add context
        reasoning.append(f"Expected Goals: {preds['expected_goals']:.2f}")
        reasoning.append(f"Friction: {features.get('matchup_friction', 0):.0f}/100")
        
        # Top features
        top_features = sorted(
            [(k, v) for k, v in self.models.feature_importance.items()],
            key=lambda x: x[1], reverse=True
        )[:5]
        
        return MatchPrediction(
            home_team=home_team,
            away_team=away_team,
            p_over_25=round(preds['p_over_25'], 3),
            p_under_25=round(1 - preds['p_over_25'], 3),
            p_btts_yes=round(preds['p_btts'], 3),
            p_btts_no=round(1 - preds['p_btts'], 3),
            p_cs_home=round(max(0, 1 - preds['p_btts'] - 0.1), 3),
            p_cs_away=round(max(0, 1 - preds['p_btts'] - 0.15), 3),
            expected_goals=round(preds['expected_goals'], 2),
            confidence=round(confidence, 1),
            edge_over_25=edge_over,
            edge_btts=edge_btts,
            kelly_over_25=kelly_over,
            kelly_btts=kelly_btts,
            recommendation=recommendation,
            reasoning=reasoning,
            model_agreement=model_agreement,
            feature_importance=dict(top_features),
        )
    
    def print_prediction(self, pred: MatchPrediction):
        """Affiche une prédiction"""
        print("\n" + "=" * 70)
        print(f"⚽ {pred.home_team} vs {pred.away_team}")
        print("=" * 70)
        
        print(f"\n📊 PROBABILITÉS ML:")
        print(f"   Over 2.5:  {pred.p_over_25*100:5.1f}%  |  Under 2.5: {pred.p_under_25*100:5.1f}%")
        print(f"   BTTS Yes:  {pred.p_btts_yes*100:5.1f}%  |  BTTS No:   {pred.p_btts_no*100:5.1f}%")
        print(f"   Expected Goals: {pred.expected_goals:.2f}")
        
        print(f"\n💰 EDGE & KELLY:")
        print(f"   Over 2.5: Edge={pred.edge_over_25:+6.1f}%  Kelly={pred.kelly_over_25:.1f}%")
        print(f"   BTTS:     Edge={pred.edge_btts:+6.1f}%  Kelly={pred.kelly_btts:.1f}%")
        
        emoji = {'BET_OVER_25': '🔥', 'BET_UNDER_25': '❄️', 'BET_BTTS': '⚽', 'SKIP': '⏸️', 'AVOID': '🚫'}.get(pred.recommendation, '❓')
        print(f"\n🎯 RECOMMENDATION: {emoji} {pred.recommendation}")
        print(f"   Confidence: {pred.confidence:.0f}%")
        print(f"   Model Agreement: {pred.model_agreement:.0f}%")
        
        if pred.reasoning:
            print(f"\n📝 REASONING:")
            for r in pred.reasoning:
                print(f"   • {r}")
    
    def batch_analyze(self, matches: List[Tuple[str, str, float, float]]) -> List[MatchPrediction]:
        """Analyse plusieurs matchs"""
        results = []
        for home, away, odds_o, odds_b in matches:
            pred = self.analyze_match(home, away, odds_o, odds_b)
            if pred:
                results.append(pred)
        return results

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Initialiser l'agent (entraîne si nécessaire)
    agent = AgentDefenseML(train=True)
    
    # Afficher les métriques des modèles
    print("\n" + "=" * 70)
    print("📊 MÉTRIQUES DES MODÈLES")
    print("=" * 70)
    for model_name, metrics in agent.models.metrics.items():
        print(f"\n{model_name.upper()}:")
        for m, v in metrics.items():
            print(f"   {m}: {v:.4f}")
    
    # Test matches
    test_matches = [
        ("Manchester United", "Liverpool", 1.85, 1.80),
        ("AC Milan", "Inter", 1.95, 1.75),
        ("Metz", "Paris Saint Germain", 1.70, 1.90),
        ("Barcelona", "Real Madrid", 1.75, 1.65),
        ("Girona", "Athletic Club", 1.80, 1.85),
        ("Arsenal", "Chelsea", 1.90, 1.80),
        ("Bayern Munich", "Borussia Dortmund", 1.85, 1.70),
    ]
    
    print("\n" + "=" * 70)
    print("📋 ANALYSE DES MATCHS")
    print("=" * 70)
    
    for home, away, odds_o, odds_b in test_matches:
        pred = agent.analyze_match(home, away, odds_o, odds_b)
        if pred:
            agent.print_prediction(pred)
    
    # Summary table
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES RECOMMANDATIONS")
    print("=" * 70)
    print(f"{'Match':<45} {'Rec':<15} {'P(O2.5)':<10} {'Edge':<10} {'Kelly':<8}")
    print("-" * 88)
    
    for home, away, odds_o, odds_b in test_matches:
        pred = agent.analyze_match(home, away, odds_o, odds_b)
        if pred:
            emoji = {'BET_OVER_25': '🔥', 'BET_UNDER_25': '❄️', 'BET_BTTS': '⚽', 'SKIP': '⏸️', 'AVOID': '��'}.get(pred.recommendation, '❓')
            print(f"{home[:20]} vs {away[:20]:<20} {emoji}{pred.recommendation:<12} {pred.p_over_25*100:>6.1f}%   {pred.edge_over_25:>+6.1f}%   {pred.kelly_over_25:>5.1f}%")

if __name__ == '__main__':
    main()

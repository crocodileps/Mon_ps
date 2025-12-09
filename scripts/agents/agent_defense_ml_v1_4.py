#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
 🛡️ AGENT DÉFENSE ML V1.4 - REFEREE PURE SIGNAL INTEGRATION

 CHANGELOG V1.4:
   • Intégration Referee Pure Signal (card_impact, trigger_rate)
   • Nouvelles features: ref_card_impact, ref_trigger_rate, ref_is_strict, ref_is_lenient
   • Signaux VALIDÉS statistiquement (r=0.931, p<0.001)
   • Signaux REJETÉS (home_bias, big_team_bias, nemesis_matrix = bruit)

 BASÉ SUR V1.3 FULL (186 features → 190 features avec referee)

 Auteur: Mya × Claude | Date: 2025-01-10
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import sys
import pickle
import warnings
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, mean_absolute_error
import xgboost as xgb
import lightgbm as lgb

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT REFEREE PURE SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

# Ajouter le chemin des agents
sys.path.insert(0, '/home/Mon_ps/agents')

try:
    from referee_pure_signal_v1 import RefereePureSignal, get_referee_features, LEAGUE_AVG_TRIGGER_RATE
    REFEREE_MODULE_AVAILABLE = True
    print("✅ Referee Pure Signal V1.0 chargé")
except ImportError as e:
    REFEREE_MODULE_AVAILABLE = False
    LEAGUE_AVG_TRIGGER_RATE = 16.5
    print(f"⚠️ Referee Pure Signal non disponible: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_PATHS = {
    'goals': '/home/Mon_ps/data/goal_analysis/all_goals_2025.json',
    'defensive_lines': '/home/Mon_ps/data/defensive_lines/defensive_lines_v8_3_multi_source.json',
    'defenders': '/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json',
    'goalkeepers': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_timing_dna_v1.json',
    'goalkeepers_v3': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v3_1_final.json',
    'context': '/home/Mon_ps/data/quantum_v2/teams_context_dna.json',
    'exploits': '/home/Mon_ps/data/quantum_v2/team_exploit_profiles.json',
    'zones': '/home/Mon_ps/data/quantum_v2/zone_analysis.json',
    'gamestate': '/home/Mon_ps/data/quantum_v2/gamestate_insights.json',
    'team_defense': '/home/Mon_ps/data/defense_dna/team_defense_dna_2025_fixed.json',
    'referee_dna': '/home/Mon_ps/data/referee_dna_hedge_fund_v4.json',
}

MODEL_PATH = '/home/Mon_ps/models/agent_defense/'
os.makedirs(MODEL_PATH, exist_ok=True)

VERSION = "1.4_referee"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MatchPrediction:
    home_team: str
    away_team: str
    referee: str
    p_over_25: float
    p_under_25: float
    p_btts_yes: float
    p_btts_no: float
    expected_goals: float
    expected_cards: float  # NEW V1.4
    confidence: float
    edge_over_25: float
    edge_btts: float
    recommendation: str
    reasoning: List[str]
    referee_impact: str  # NEW V1.4
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADER (Extended with Referee)
# ═══════════════════════════════════════════════════════════════════════════════

class DataLoader:
    """Charge toutes les sources de données incluant Referee DNA"""

    def __init__(self):
        self.goals = []
        self.matches = {}
        self.team_dna = {}
        self.gk_dna = {}
        self.gk_dna_v3 = {}
        self.defender_dna = {}
        self.context = {}
        self.exploits = {}
        self.zones = {}
        self.gamestate = {}
        self.team_defense = {}
        self.referee_dna = {}  # NEW V1.4
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
        print("📂 Chargement des données V1.4...")

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

        # Goalkeeper DNA V1
        gk_data = self._load_json(DATA_PATHS['goalkeepers']) or []
        for gk in gk_data:
            key = self._normalize(gk.get('team', ''))
            if key:
                self.gk_dna[key] = gk
        print(f"   ✅ GK DNA V1: {len(self.gk_dna)} gardiens")

        # Goalkeeper DNA V3.1
        gk_v3_data = self._load_json(DATA_PATHS['goalkeepers_v3']) or {}
        if isinstance(gk_v3_data, dict):
            for team, data in gk_v3_data.items():
                key = self._normalize(team)
                if key:
                    self.gk_dna_v3[key] = data
        print(f"   ✅ GK DNA V3.1: {len(self.gk_dna_v3)} équipes")

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

        # Team Defense DNA
        td_data = self._load_json(DATA_PATHS['team_defense']) or {}
        if isinstance(td_data, dict):
            for team, data in td_data.items():
                key = self._normalize(team)
                if key:
                    self.team_defense[key] = data
        print(f"   ✅ Team Defense: {len(self.team_defense)} équipes")

        # ═══════════════════════════════════════════════════════════════════════
        # NEW V1.4: REFEREE DNA
        # ═══════════════════════════════════════════════════════════════════════
        ref_data = self._load_json(DATA_PATHS['referee_dna']) or []
        for ref in ref_data:
            name = ref.get('referee_name', '')
            if name:
                self.referee_dna[name] = ref
        print(f"   ✅ Referee DNA: {len(self.referee_dna)} arbitres")

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

    def get_referee(self, name: str) -> Optional[Dict]:
        """Récupère les données d'un arbitre"""
        if name in self.referee_dna:
            return self.referee_dna[name]
        # Recherche partielle
        for ref_name, data in self.referee_dna.items():
            if name.lower() in ref_name.lower():
                return data
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING V1.4 (Extended with Referee)
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineerV14:
    """Extrait les features pour le ML - Version 1.4 avec Referee"""

    TIMING_RISK = {
        'late_collapser': 1.30, 'starts_strong_fades': 1.25,
        'late_vulnerable': 1.15, 'slow_starter': 1.10,
        'balanced': 1.00, 'fast_starter': 0.95,
        'strong_finisher': 0.85, 'slow_starter_strong_finish': 0.90,
    }

    def __init__(self, data_loader: DataLoader):
        self.data = data_loader
        # Initialiser Referee Pure Signal si disponible
        if REFEREE_MODULE_AVAILABLE:
            try:
                self.referee_signal = RefereePureSignal()
            except:
                self.referee_signal = None
        else:
            self.referee_signal = None

    def _get_team_features(self, team: str, prefix: str) -> Dict[str, float]:
        """Extrait les features d'une équipe"""
        team_key = team.lower().strip().replace('_', ' ')
        features = {}

        # Team DNA (Defensive Lines V8.3)
        dna = self.data.team_dna.get(team_key, {})

        # Foundation
        foundation = dna.get('foundation', {})
        features[f'{prefix}_xga90'] = foundation.get('xga_90', 1.2)
        features[f'{prefix}_ga90'] = foundation.get('ga_90', 1.3)
        features[f'{prefix}_cs_pct'] = foundation.get('clean_sheet_pct', 25)

        # Resistance
        resist = dna.get('resistance', {})
        features[f'{prefix}_resist'] = resist.get('resist_global', 50)
        features[f'{prefix}_resist_set_piece'] = resist.get('resist_set_piece', 50)
        features[f'{prefix}_resist_transition'] = resist.get('resist_transition', 50)

        # Timing DNA
        timing = dna.get('timing_dna', {})
        profile = timing.get('primary_profile', 'balanced').lower()
        features[f'{prefix}_timing_risk'] = self.TIMING_RISK.get(profile, 1.0)

        periods = timing.get('periods_pct', {})
        features[f'{prefix}_early_pct'] = periods.get('0-30', 33)
        features[f'{prefix}_mid_pct'] = periods.get('31-60', 33)
        features[f'{prefix}_late_pct'] = periods.get('61-90', 33)

        # Periods granulaires
        features[f'{prefix}_p0_15'] = timing.get('0-15', {}).get('xga_pct', 16)
        features[f'{prefix}_p76_90'] = timing.get('76-90', {}).get('xga_pct', 16)

        # Edge
        edge = dna.get('edge', {})
        features[f'{prefix}_edge'] = edge.get('total_edge', 0)

        # Goalkeeper DNA V1
        gk = self.data.gk_dna.get(team_key, {})
        features[f'{prefix}_gk_pct'] = gk.get('gk_percentile', 50)
        gk_timing = gk.get('timing', {}).get('76-90', {})
        features[f'{prefix}_gk_sr_76_90'] = gk_timing.get('save_rate', 65)

        # Goalkeeper DNA V3.1
        gk_v3 = self.data.gk_dna_v3.get(team_key, {})
        if gk_v3:
            by_diff = gk_v3.get('by_difficulty', {})
            features[f'{prefix}_gk_hard_sr'] = by_diff.get('hard', {}).get('save_rate', 30)
            features[f'{prefix}_gk_very_hard_sr'] = by_diff.get('very_hard', {}).get('save_rate', 15)
            
            exploit = gk_v3.get('exploit_paths', {})
            features[f'{prefix}_gk_vuln_low'] = 1 if exploit.get('low_shots', {}).get('verdict') == 'VULNERABLE' else 0
            features[f'{prefix}_gk_vuln_high'] = 1 if exploit.get('high_shots', {}).get('verdict') == 'VULNERABLE' else 0

        # Defenders
        defs = self.data.defender_dna.get(team_key, {})
        features[f'{prefix}_def_cards'] = defs.get('avg_cards_90', 0.2)
        features[f'{prefix}_def_impact'] = defs.get('avg_impact', 0)

        # Context
        ctx = self.data.context.get(team_key, self.data.context.get(team, {}))
        ctx_dna = ctx.get('context_dna', {}) if isinstance(ctx, dict) else {}
        momentum = ctx.get('momentum_dna', {}) if isinstance(ctx, dict) else {}
        features[f'{prefix}_form'] = ctx_dna.get('form_score', 50)
        features[f'{prefix}_momentum'] = momentum.get('momentum_score', 0)

        # Exploits
        exp = self.data.exploits.get(team_key, self.data.exploits.get(team, {}))
        features[f'{prefix}_vuln'] = exp.get('vulnerability_score', 50) if isinstance(exp, dict) else 50

        # Zones
        zones = self.data.zones.get(team_key, self.data.zones.get(team, {}))
        if isinstance(zones, dict) and 'zones' in zones:
            zone_data = zones['zones']
            features[f'{prefix}_zone_box'] = zone_data.get('box', {}).get('xG', 0)
            features[f'{prefix}_zone_center'] = zone_data.get('center', {}).get('xG', 0)
        else:
            features[f'{prefix}_zone_box'] = 0
            features[f'{prefix}_zone_center'] = 0

        # Gamestate
        gs = self.data.gamestate.get(team_key, {})
        if isinstance(gs, dict):
            features[f'{prefix}_gs_losing'] = gs.get('losing', {}).get('xga_90', 1.5)
            features[f'{prefix}_gs_winning'] = gs.get('winning', {}).get('xga_90', 0.8)

        # Team Defense DNA
        td = self.data.team_defense.get(team_key, {})
        if isinstance(td, dict):
            features[f'{prefix}_xga_corner'] = td.get('set_pieces', {}).get('corner', {}).get('xga', 0.1)
            features[f'{prefix}_xga_2h'] = td.get('by_half', {}).get('2H', {}).get('xga', 0.6)

        return features

    def _get_referee_features(self, referee: str) -> Dict[str, float]:
        """
        NEW V1.4: Extrait les features arbitre (PURE SIGNAL ONLY)
        
        Signaux VALIDÉS:
          - card_impact (r=0.931 avec over_45%)
          - card_trigger_rate
        
        Signaux IGNORÉS (bruit statistique):
          - home_bias (r=0.047)
          - big_team_bias
          - nemesis_teams
        """
        features = {
            'ref_card_impact': 0,
            'ref_trigger_rate': LEAGUE_AVG_TRIGGER_RATE,
            'ref_is_strict': 0,
            'ref_is_lenient': 0,
            'ref_confidence': 0,
        }

        if not referee:
            return features

        # Méthode 1: Via RefereePureSignal module
        if self.referee_signal:
            ref_profile = self.referee_signal.get_referee(referee)
            if ref_profile:
                features['ref_card_impact'] = ref_profile.card_impact
                features['ref_trigger_rate'] = ref_profile.trigger_rate
                features['ref_is_strict'] = 1 if ref_profile.strictness == "STRICT" else 0
                features['ref_is_lenient'] = 1 if ref_profile.strictness == "LENIENT" else 0
                features['ref_confidence'] = ref_profile.confidence
                return features

        # Méthode 2: Directement depuis les données
        ref_data = self.data.get_referee(referee)
        if ref_data:
            features['ref_card_impact'] = ref_data.get('card_impact', 0)
            features['ref_trigger_rate'] = ref_data.get('card_trigger_rate', LEAGUE_AVG_TRIGGER_RATE)
            strictness = ref_data.get('strictness', 'NEUTRAL')
            features['ref_is_strict'] = 1 if strictness == "STRICT" else 0
            features['ref_is_lenient'] = 1 if strictness == "LENIENT" else 0
            matches = ref_data.get('matches', 0)
            features['ref_confidence'] = min(1.0, matches / 100)

        return features

    def extract_match_features(self, home_team: str, away_team: str, referee: str = None) -> Dict[str, float]:
        """Extrait toutes les features pour un match (V1.4 avec Referee)"""
        features = {}

        # Home team features
        home_f = self._get_team_features(home_team, 'h')
        features.update(home_f)

        # Away team features
        away_f = self._get_team_features(away_team, 'a')
        features.update(away_f)

        # ═══════════════════════════════════════════════════════════════════════
        # NEW V1.4: REFEREE FEATURES
        # ═══════════════════════════════════════════════════════════════════════
        ref_f = self._get_referee_features(referee)
        features.update(ref_f)

        # Combined features
        features['comb_edge'] = (home_f.get('h_edge', 0) + away_f.get('a_edge', 0)) / 2
        features['comb_xga'] = home_f.get('h_xga90', 1.2) + away_f.get('a_xga90', 1.2)
        features['comb_xga_2h'] = home_f.get('h_xga_2h', 0.6) + away_f.get('a_xga_2h', 0.6)
        features['comb_xga_76_90'] = home_f.get('h_p76_90', 16) + away_f.get('a_p76_90', 16)
        
        features['min_resist'] = min(home_f.get('h_resist', 50), away_f.get('a_resist', 50))
        features['resist_diff'] = home_f.get('h_resist', 50) - away_f.get('a_resist', 50)
        features['max_vuln'] = max(home_f.get('h_vuln', 50), away_f.get('a_vuln', 50))
        
        features['timing_prod'] = home_f.get('h_timing_risk', 1) * away_f.get('a_timing_risk', 1)
        features['late_sum'] = home_f.get('h_late_pct', 33) + away_f.get('a_late_pct', 33)
        features['closing_sum'] = home_f.get('h_p76_90', 16) + away_f.get('a_p76_90', 16)
        
        features['min_gk_76_90'] = min(home_f.get('h_gk_sr_76_90', 65), away_f.get('a_gk_sr_76_90', 65))
        features['gk_pct_diff'] = home_f.get('h_gk_pct', 50) - away_f.get('a_gk_pct', 50)
        features['gk_vulns_sum'] = home_f.get('h_gk_vuln_low', 0) + home_f.get('h_gk_vuln_high', 0) + \
                                   away_f.get('a_gk_vuln_low', 0) + away_f.get('a_gk_vuln_high', 0)
        
        features['momentum_diff'] = home_f.get('h_momentum', 0) - away_f.get('a_momentum', 0)
        features['form_diff'] = home_f.get('h_form', 50) - away_f.get('a_form', 50)
        
        features['def_cards_sum'] = home_f.get('h_def_cards', 0.2) + away_f.get('a_def_cards', 0.2)
        features['def_impact_sum'] = home_f.get('h_def_impact', 0) + away_f.get('a_def_impact', 0)
        
        features['zone_box_sum'] = home_f.get('h_zone_box', 0) + away_f.get('a_zone_box', 0)
        features['zone_center_sum'] = home_f.get('h_zone_center', 0) + away_f.get('a_zone_center', 0)
        
        features['set_piece_vuln_sum'] = (100 - home_f.get('h_resist_set_piece', 50)) + \
                                          (100 - away_f.get('a_resist_set_piece', 50))
        features['xga_corner_sum'] = home_f.get('h_xga_corner', 0.1) + away_f.get('a_xga_corner', 0.1)
        
        features['gs_risk_sum'] = home_f.get('h_gs_losing', 1.5) + away_f.get('a_gs_losing', 1.5)
        features['exploit_paths_sum'] = home_f.get('h_gk_vuln_low', 0) + away_f.get('a_gk_vuln_low', 0)
        
        features['sum_edge'] = home_f.get('h_edge', 0) + away_f.get('a_edge', 0)

        # Friction score
        friction = 0
        if home_f.get('h_timing_risk', 1) > 1.15:
            friction += 15
        if away_f.get('a_timing_risk', 1) > 1.15:
            friction += 15
        if home_f.get('h_gk_sr_76_90', 65) < 50:
            friction += 20
        if away_f.get('a_gk_sr_76_90', 65) < 50:
            friction += 20
        if home_f.get('h_resist', 50) < 40:
            friction += 15
        if away_f.get('a_resist', 50) < 40:
            friction += 15
        features['friction'] = min(100, friction)

        return features

    def build_training_dataset(self, include_referee: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Construit le dataset d'entraînement"""
        print(f"\n🔧 Construction du dataset ML V1.4...")

        rows = []
        targets = []

        for mid, match in self.data.matches.items():
            home = match['home_team']
            away = match['away_team']

            if not home or not away:
                continue

            try:
                # Pour l'entraînement, on n'a pas l'arbitre historique
                # On utilise referee=None, les features seront à 0 (baseline)
                features = self.extract_match_features(home, away, referee=None)
                features['match_id'] = mid

                target = {
                    'over_25': match['over_25'],
                    'btts': match['btts'],
                    'total_goals': match['total_goals'],
                }

                rows.append(features)
                targets.append(target)

            except Exception as e:
                continue

        X = pd.DataFrame(rows)
        y = pd.DataFrame(targets)

        # Count features by category
        ref_features = [c for c in X.columns if c.startswith('ref_')]
        team_features = [c for c in X.columns if c.startswith('h_') or c.startswith('a_')]
        comb_features = [c for c in X.columns if not c.startswith('h_') and not c.startswith('a_') and not c.startswith('ref_') and c != 'match_id']

        print(f"   ✅ Dataset: {len(X)} matchs, {len(X.columns)} features")
        print(f"      • Team features: {len(team_features)}")
        print(f"      • Combined features: {len(comb_features)}")
        print(f"      • Referee features: {len(ref_features)}")
        print(f"   📊 Over 2.5: {y['over_25'].mean()*100:.1f}%")
        print(f"   📊 BTTS: {y['btts'].mean()*100:.1f}%")

        return X, y

# ═══════════════════════════════════════════════════════════════════════════════
# ML MODELS V1.4
# ═══════════════════════════════════════════════════════════════════════════════

class DefenseMLModelsV14:
    """Modèles ML pour la prédiction défensive - V1.4"""

    def __init__(self):
        self.models = {}
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        self.metrics = {}
        self.feature_importance = {}

    def train(self, X: pd.DataFrame, y: pd.DataFrame):
        """Entraîne tous les modèles"""
        print("\n🤖 Entraînement des modèles ML V1.4...")

        # Supprimer colonnes non-features
        feature_cols = [c for c in X.columns if c != 'match_id']
        X_clean = X[feature_cols].copy()

        # Remplacer NaN et inf
        X_clean = X_clean.replace([np.inf, -np.inf], np.nan)
        X_clean = X_clean.fillna(0)

        self.feature_names = list(X_clean.columns)
        print(f"   📋 Features: {len(self.feature_names)}")

        # Scaler
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_clean)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        # 1. XGBoost Over 2.5
        print("\n   🔹 XGBoost Over 2.5...")
        xgb_over = xgb.XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42
        )
        xgb_over.fit(X_train, y_train['over_25'])
        
        # Calibration
        calib_over = CalibratedClassifierCV(xgb_over, method='sigmoid', cv=3)
        calib_over.fit(X_train, y_train['over_25'])
        self.models['over_25'] = calib_over

        # Metrics
        y_pred_over = calib_over.predict_proba(X_test)[:, 1]
        self.metrics['over_25'] = {
            'accuracy': accuracy_score(y_test['over_25'], (y_pred_over > 0.5).astype(int)),
            'auc': roc_auc_score(y_test['over_25'], y_pred_over),
            'brier': brier_score_loss(y_test['over_25'], y_pred_over),
        }

        # 2. LightGBM BTTS
        print("   🔹 LightGBM BTTS...")
        lgb_btts = lgb.LGBMClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1
        )
        lgb_btts.fit(X_train, y_train['btts'])
        
        calib_btts = CalibratedClassifierCV(lgb_btts, method='sigmoid', cv=3)
        calib_btts.fit(X_train, y_train['btts'])
        self.models['btts'] = calib_btts

        y_pred_btts = calib_btts.predict_proba(X_test)[:, 1]
        self.metrics['btts'] = {
            'accuracy': accuracy_score(y_test['btts'], (y_pred_btts > 0.5).astype(int)),
            'auc': roc_auc_score(y_test['btts'], y_pred_btts),
        }

        # 3. XGBoost Total Goals Regressor
        print("   🔹 XGBoost Total Goals...")
        xgb_total = xgb.XGBRegressor(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42
        )
        xgb_total.fit(X_train, y_train['total_goals'])
        self.models['total'] = xgb_total

        y_pred_total = xgb_total.predict(X_test)
        self.metrics['total'] = {
            'mae': mean_absolute_error(y_test['total_goals'], y_pred_total),
        }

        # Feature importance (from XGBoost Over)
        self.feature_importance = dict(zip(self.feature_names, xgb_over.feature_importances_))

        self.is_trained = True
        print("\n   ✅ Entraînement terminé!")

    def predict(self, features: Dict[str, float]) -> Dict[str, float]:
        """Prédit pour un match"""
        if not self.is_trained:
            raise ValueError("Modèles non entraînés!")

        # Préparer features
        X = pd.DataFrame([features])
        X = X.reindex(columns=self.feature_names, fill_value=0)
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        X_scaled = self.scaler.transform(X)

        # Prédictions
        p_over_25 = self.models['over_25'].predict_proba(X_scaled)[0, 1]
        p_btts = self.models['btts'].predict_proba(X_scaled)[0, 1]
        expected_goals = self.models['total'].predict(X_scaled)[0]

        return {
            'p_over_25': float(p_over_25),
            'p_btts': float(p_btts),
            'expected_goals': float(max(0, expected_goals)),
        }

    def save(self, path: str = None):
        """Sauvegarde les modèles"""
        path = path or MODEL_PATH
        data = {
            'models': self.models,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'feature_importance': self.feature_importance,
            'version': VERSION,
        }
        filepath = os.path.join(path, f'models_v{VERSION}.pkl')
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        print(f"   💾 Modèles sauvegardés: {filepath}")

    def load(self, path: str = None):
        """Charge les modèles"""
        path = path or MODEL_PATH
        filepath = os.path.join(path, f'models_v{VERSION}.pkl')
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            self.models = data['models']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            self.metrics = data.get('metrics', {})
            self.feature_importance = data.get('feature_importance', {})
            self.is_trained = True
            print(f"   📂 Modèles chargés: {filepath}")
            return True
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT DÉFENSE ML V1.4
# ═══════════════════════════════════════════════════════════════════════════════

class AgentDefenseMLV14:
    """Agent de prédiction défensive ML - V1.4 avec Referee"""

    def __init__(self, train: bool = False):
        print("=" * 70)
        print("🛡️ AGENT DÉFENSE ML V1.4 - REFEREE PURE SIGNAL")
        print("=" * 70)

        self.data = DataLoader()
        self.fe = FeatureEngineerV14(self.data)
        self.models = DefenseMLModelsV14()

        if train or not self.models.load():
            X, y = self.fe.build_training_dataset()
            self.models.train(X, y)
            self.models.save()

    def analyze_match(
        self,
        home_team: str,
        away_team: str,
        referee: str = None,
        odds_over_25: float = 1.90,
        odds_btts: float = 1.80
    ) -> Optional[MatchPrediction]:
        """Analyse un match avec arbitre"""
        
        try:
            features = self.fe.extract_match_features(home_team, away_team, referee)
            preds = self.models.predict(features)
        except Exception as e:
            print(f"⚠️ Erreur analyse {home_team} vs {away_team}: {e}")
            return None

        p_over = preds['p_over_25']
        p_btts = preds['p_btts']
        expected_goals = preds['expected_goals']

        # Referee impact
        ref_impact = "NEUTRE"
        expected_cards = 3.89  # baseline
        if referee:
            ref_f = self.fe._get_referee_features(referee)
            ref_card_impact = ref_f.get('ref_card_impact', 0)
            if ref_f.get('ref_is_strict'):
                ref_impact = f"STRICT (+{ref_card_impact:.2f} cards)"
            elif ref_f.get('ref_is_lenient'):
                ref_impact = f"LENIENT ({ref_card_impact:.2f} cards)"
            expected_cards += ref_card_impact

        # Edge calculation
        implied_over = 1 / odds_over_25 if odds_over_25 > 0 else 0.5
        implied_btts = 1 / odds_btts if odds_btts > 0 else 0.5
        edge_over = (p_over - implied_over) * 100
        edge_btts = (p_btts - implied_btts) * 100

        # Confidence
        confidence = 50
        if abs(edge_over) > 5:
            confidence += 10
        if abs(edge_btts) > 5:
            confidence += 10
        if features.get('friction', 0) > 50:
            confidence += 5
        if referee and features.get('ref_confidence', 0) > 0.8:
            confidence += 10

        # Recommendation
        reasoning = []
        recommendation = "SKIP"

        if edge_over > 8 and p_over > 0.55:
            recommendation = "BET_OVER_25"
            reasoning.append(f"Edge Over 2.5: {edge_over:+.1f}%")
        elif edge_over < -8 and p_over < 0.45:
            recommendation = "BET_UNDER_25"
            reasoning.append(f"Edge Under 2.5: {-edge_over:+.1f}%")
        elif edge_btts > 8 and p_btts > 0.55:
            recommendation = "BET_BTTS"
            reasoning.append(f"Edge BTTS: {edge_btts:+.1f}%")

        if referee and features.get('ref_is_lenient'):
            reasoning.append(f"Arbitre LENIENT: {referee}")
        if referee and features.get('ref_is_strict'):
            reasoning.append(f"Arbitre STRICT: {referee}")

        return MatchPrediction(
            home_team=home_team,
            away_team=away_team,
            referee=referee or "Unknown",
            p_over_25=round(p_over, 3),
            p_under_25=round(1 - p_over, 3),
            p_btts_yes=round(p_btts, 3),
            p_btts_no=round(1 - p_btts, 3),
            expected_goals=round(expected_goals, 2),
            expected_cards=round(expected_cards, 2),
            confidence=round(min(100, confidence), 1),
            edge_over_25=round(edge_over, 1),
            edge_btts=round(edge_btts, 1),
            recommendation=recommendation,
            reasoning=reasoning,
            referee_impact=ref_impact,
        )

    def print_prediction(self, pred: MatchPrediction):
        """Affiche une prédiction"""
        print("\n" + "=" * 70)
        print(f"⚽ {pred.home_team} vs {pred.away_team}")
        print(f"🎯 Referee: {pred.referee} → {pred.referee_impact}")
        print("=" * 70)

        print(f"\n📊 PROBABILITÉS ML:")
        print(f"   Over 2.5:  {pred.p_over_25*100:5.1f}%  |  Under 2.5: {pred.p_under_25*100:5.1f}%")
        print(f"   BTTS Yes:  {pred.p_btts_yes*100:5.1f}%  |  BTTS No:   {pred.p_btts_no*100:5.1f}%")
        print(f"   Expected Goals: {pred.expected_goals:.2f}")
        print(f"   Expected Cards: {pred.expected_cards:.2f}")

        print(f"\n💰 EDGE:")
        print(f"   Over 2.5: {pred.edge_over_25:+6.1f}%")
        print(f"   BTTS:     {pred.edge_btts:+6.1f}%")

        emoji = {'BET_OVER_25': '🔥', 'BET_UNDER_25': '❄️', 'BET_BTTS': '⚽', 'SKIP': '⏸️'}.get(pred.recommendation, '❓')
        print(f"\n🎯 RECOMMENDATION: {emoji} {pred.recommendation}")
        print(f"   Confidence: {pred.confidence:.0f}%")

        if pred.reasoning:
            print(f"\n📝 REASONING:")
            for r in pred.reasoning:
                print(f"   • {r}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Initialiser l'agent (entraîne si nécessaire)
    agent = AgentDefenseMLV14(train=True)

    # Afficher les métriques des modèles
    print("\n" + "=" * 70)
    print("📊 MÉTRIQUES DES MODÈLES V1.4")
    print("=" * 70)
    for model_name, metrics in agent.models.metrics.items():
        print(f"\n{model_name.upper()}:")
        for m, v in metrics.items():
            if isinstance(v, float):
                print(f"   {m}: {v:.4f}")

    # Test matches WITH REFEREE
    print("\n" + "=" * 70)
    print("📋 ANALYSE DES MATCHS AVEC REFEREE")
    print("=" * 70)

    test_matches = [
        # (home, away, referee, odds_over, odds_btts)
        ("Arsenal", "Chelsea", "M Atkinson", 1.90, 1.75),
        ("Arsenal", "Chelsea", "K Stroud", 1.90, 1.75),
        ("Liverpool", "Manchester City", "M Oliver", 1.85, 1.70),
        ("Manchester United", "Tottenham", "D Webb", 1.95, 1.80),
        ("Wolves", "Everton", "C Pawson", 2.00, 1.85),
    ]

    for home, away, referee, odds_o, odds_b in test_matches:
        pred = agent.analyze_match(home, away, referee, odds_o, odds_b)
        if pred:
            agent.print_prediction(pred)

    # Summary comparison: same match, different referee
    print("\n" + "=" * 70)
    print("📊 COMPARAISON: MÊME MATCH, ARBITRE DIFFÉRENT")
    print("=" * 70)
    print(f"{'Match':<35} {'Referee':<15} {'P(O2.5)':<10} {'Cards':<8} {'Reco':<12}")
    print("-" * 80)

    comparison_refs = ["M Atkinson", "D Webb", "K Stroud", "C Pawson"]
    for ref in comparison_refs:
        pred = agent.analyze_match("Arsenal", "Chelsea", ref, 1.90, 1.75)
        if pred:
            emoji = {'BET_OVER_25': '🔥', 'BET_UNDER_25': '❄️', 'BET_BTTS': '⚽', 'SKIP': '⏸️'}.get(pred.recommendation, '❓')
            print(f"Arsenal vs Chelsea          {ref:<15} {pred.p_over_25*100:>6.1f}%   {pred.expected_cards:>5.2f}    {emoji}{pred.recommendation}")

if __name__ == '__main__':
    main()

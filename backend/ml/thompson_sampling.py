"""
FERRARI 2.0 - Thompson Sampling & Statistical Analysis
Module pour Multi-Armed Bandit et tests statistiques avancés
"""

import numpy as np
from scipy import stats
from scipy.stats import beta, chi2_contingency
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ThompsonSampling:
    """Thompson Sampling pour allocation dynamique du trafic"""
    
    def __init__(self):
        self.variations = {}
    
    def add_variation(self, variation_id: int, alpha: float = 1.0, beta_param: float = 1.0):
        self.variations[variation_id] = {
            'alpha': alpha,
            'beta': beta_param,
            'samples': []
        }
    
    def sample_all(self) -> Dict[int, float]:
        samples = {}
        for var_id, params in self.variations.items():
            sample = np.random.beta(params['alpha'], params['beta'])
            samples[var_id] = sample
            params['samples'].append(sample)
        return samples
    
    def select_variation(self) -> int:
        samples = self.sample_all()
        winner_id = max(samples, key=samples.get)
        logger.info(f"Thompson: variation {winner_id} = {samples[winner_id]:.4f}")
        return winner_id
    
    def update(self, variation_id: int, won: bool):
        if variation_id not in self.variations:
            raise ValueError(f"Variation {variation_id} non trouvée")
        if won:
            self.variations[variation_id]['alpha'] += 1
        else:
            self.variations[variation_id]['beta'] += 1
    
    def get_expected_win_rate(self, variation_id: int) -> float:
        params = self.variations[variation_id]
        return params['alpha'] / (params['alpha'] + params['beta'])
    
    def get_confidence_interval(self, variation_id: int, confidence: float = 0.95) -> Tuple[float, float]:
        params = self.variations[variation_id]
        alpha_val = (1 - confidence) / 2
        lower = beta.ppf(alpha_val, params['alpha'], params['beta'])
        upper = beta.ppf(1 - alpha_val, params['alpha'], params['beta'])
        return (lower, upper)
    
    def calculate_traffic_allocation(self, min_traffic: float = 0.05) -> Dict[int, float]:
        N = 1000
        wins = {var_id: 0 for var_id in self.variations.keys()}
        for _ in range(N):
            winner = self.select_variation()
            wins[winner] += 1
        total_variations = len(self.variations)
        reserved = min_traffic * total_variations
        available = 1.0 - reserved
        traffic = {}
        for var_id, win_count in wins.items():
            proportion = win_count / N
            traffic[var_id] = min_traffic + (proportion * available)
        return traffic


def chi_squared_test(wins_a: int, losses_a: int, wins_b: int, losses_b: int) -> Dict:
    observed = np.array([[wins_a, losses_a], [wins_b, losses_b]])
    chi2_stat, p_value, dof, expected = chi2_contingency(observed)
    is_significant = p_value < 0.05
    conclusion = f"{'Significative' if is_significant else 'Non significative'} (p={p_value:.4f})"
    return {
        'statistic': float(chi2_stat),
        'p_value': float(p_value),
        'degrees_of_freedom': int(dof),
        'is_significant': is_significant,
        'conclusion': conclusion
    }

def bayesian_ab_test(alpha_a: float, beta_a: float, alpha_b: float, beta_b: float, n_samples: int = 10000) -> Dict:
    samples_a = np.random.beta(alpha_a, beta_a, n_samples)
    samples_b = np.random.beta(alpha_b, beta_b, n_samples)
    prob_b_better = float(np.mean(samples_b > samples_a))
    mean_a = alpha_a / (alpha_a + beta_a)
    mean_b = alpha_b / (alpha_b + beta_b)
    expected_lift = ((mean_b - mean_a) / mean_a) * 100 if mean_a > 0 else 0
    if prob_b_better > 0.95:
        confidence = 'high'
    elif prob_b_better > 0.80:
        confidence = 'medium'
    else:
        confidence = 'low'
    return {
        'prob_b_better': prob_b_better,
        'expected_lift': expected_lift,
        'confidence': confidence
    }


class SafeguardMonitor:
    def __init__(self, max_loss: float = 100.0, max_drawdown: float = 15.0, min_win_rate: float = 45.0, min_samples: int = 50):
        self.max_loss = max_loss
        self.max_drawdown = max_drawdown
        self.min_win_rate = min_win_rate
        self.min_samples = min_samples
    
    def check_variation(self, variation_id: int, total_profit: float, win_rate: float, matches: int) -> List[Dict]:
        events = []
        if total_profit < -self.max_loss:
            events.append({
                'type': 'max_loss',
                'severity': 'critical',
                'message': f'Perte {total_profit:.2f}€ > limite {self.max_loss:.2f}€',
                'trigger_value': total_profit,
                'threshold_value': -self.max_loss,
                'action': 'pause_variation'
            })
        if matches >= self.min_samples and win_rate < self.min_win_rate:
            events.append({
                'type': 'low_performance',
                'severity': 'warning',
                'message': f'Win rate {win_rate:.1f}% < {self.min_win_rate:.1f}%',
                'trigger_value': win_rate,
                'threshold_value': self.min_win_rate,
                'action': 'reduce_traffic'
            })
        if total_profit < 0:
            drawdown_pct = abs(total_profit / self.max_loss) * 100
            if drawdown_pct > self.max_drawdown:
                events.append({
                    'type': 'drawdown',
                    'severity': 'critical',
                    'message': f'Drawdown {drawdown_pct:.1f}% > {self.max_drawdown:.1f}%',
                    'trigger_value': drawdown_pct,
                    'threshold_value': self.max_drawdown,
                    'action': 'pause_variation'
                })
        return events

def analyze_factor_contribution(matches_with: List[Dict], matches_without: List[Dict]) -> Dict:
    with_wins = sum(1 for m in matches_with if m.get('outcome') == 'win')
    with_total = len(matches_with)
    win_rate_with = (with_wins / with_total * 100) if with_total > 0 else 0
    without_wins = sum(1 for m in matches_without if m.get('outcome') == 'win')
    without_total = len(matches_without)
    win_rate_without = (without_wins / without_total * 100) if without_total > 0 else 0
    delta = win_rate_with - win_rate_without
    if with_total >= 30 and without_total >= 30:
        test = chi_squared_test(with_wins, with_total - with_wins, without_wins, without_total - without_wins)
        p_value = test['p_value']
        is_significant = test['is_significant']
    else:
        p_value = None
        is_significant = False
    return {
        'win_rate_with': win_rate_with,
        'win_rate_without': win_rate_without,
        'delta': delta,
        'p_value': p_value,
        'is_significant': is_significant
    }

"""
🎯 DEFENSE ZONE SCANNER V2.0
Niveau Quant 3.0 - Analyse des ZONES de rupture, pas des joueurs isolés

Principes:
1. Weakest Link Aggregator: Paires adjacentes de défenseurs faibles
2. Panic-Alpha Cross: Croiser qualité structurelle et état mental
3. Short-Squeeze: Multiplier par la pression offensive adverse
"""

import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path


class ZoneSeverity(Enum):
    """Niveau de risque d'une zone défensive"""
    CRITICAL = "CRITICAL"     # Deux liabilities adjacentes
    HIGH = "HIGH"             # Un liability + un faible
    ELEVATED = "ELEVATED"     # Un liability seul
    MODERATE = "MODERATE"     # Faiblesse mineure
    SOLID = "SOLID"           # Zone solide


class PanicAlphaQuadrant(Enum):
    """Quadrant de la matrice Panic × Alpha"""
    PASSOIRE = "PASSOIRE"                 # Alpha- Panic-: Nul constant
    CATASTROPHE = "CATASTROPHE"           # Alpha- Panic+: Explosion imminente
    SOLIDE = "SOLIDE"                     # Alpha+ Panic-: Fiable
    BOMBE_RETARDEMENT = "BOMBE_RETARDEMENT"  # Alpha+ Panic+: Peut craquer


@dataclass
class ZoneWeakness:
    """Analyse d'une zone défensive"""
    zone_name: str           # LEFT_FLANK, CENTER, RIGHT_FLANK
    players: List[str]       # Noms des défenseurs dans la zone
    
    avg_alpha_league: float
    avg_alpha_team: float
    combined_liability: float
    
    severity: ZoneSeverity
    target_position: str     # Position adverse qui exploite cette zone
    
    recommended_markets: List[Dict]
    edge_boost: float        # Bonus d'edge si zone critique


@dataclass 
class PanicAlphaProfile:
    """Profil croisé Alpha × Panic"""
    defender_name: str
    team: str
    
    alpha_league: float
    panic_score: float       # 0-100
    markov_state: str
    
    quadrant: PanicAlphaQuadrant
    strategy: str
    timing: str              # PRE_MATCH, LIVE, SKIP


@dataclass
class ShortSqueezeSignal:
    """Signal de Short avec catalyseur adverse"""
    defending_team: str
    liability_score: float   # 0-1
    
    opponent_team: str
    opponent_pressure_index: float  # 0.5-1.5
    
    collapse_probability: float
    signal_strength: str     # MAX_BET, STANDARD, CAUTIOUS, SKIP
    
    recommended_markets: List[str]
    reasoning: str


class DefenseZoneScanner:
    """Scanner de zones défensives vulnérables"""
    
    # Positions par zone
    ZONES = {
        'LEFT_FLANK': ['LB', 'LWB', 'LCB'],   # Flanc gauche
        'CENTER': ['LCB', 'CB', 'RCB'],        # Axe central
        'RIGHT_FLANK': ['RCB', 'RB', 'RWB']   # Flanc droit
    }
    
    # Position adverse qui exploite chaque zone
    ZONE_EXPLOITER = {
        'LEFT_FLANK': 'RW',   # Ailier droit attaque le flanc gauche
        'CENTER': 'ST',       # Attaquant central attaque l'axe
        'RIGHT_FLANK': 'LW'   # Ailier gauche attaque le flanc droit
    }
    
    def __init__(self):
        self.defenders_data: Dict[str, Dict] = {}  # name -> data
        self.teams_defenders: Dict[str, List[Dict]] = {}
        self.attack_dna: Dict[str, Dict] = {}
        self.loaded = False
        
        # Moyenne ligue (calculée au chargement)
        self.league_avg_ga = 1.37
        
    def load_data(self):
        """Charge toutes les données nécessaires"""
        if self.loaded:
            return
            
        # Defender DNA
        path = Path("/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json")
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for d in data:
                name = d.get('name', '')
                team = d.get('team', '')
                self.defenders_data[name] = d
                if team not in self.teams_defenders:
                    self.teams_defenders[team] = []
                self.teams_defenders[team].append(d)
        
        # Attack DNA
        attack_path = Path("/home/Mon_ps/data/quantum_v2/teams_context_dna.json")
        if attack_path.exists():
            with open(attack_path) as f:
                self.attack_dna = json.load(f)
        
        # Defense DNA pour moyennes équipes
        defense_path = Path("/home/Mon_ps/data/defense_dna/team_defense_dna_v6_fixed.json")
        if defense_path.exists():
            with open(defense_path) as f:
                defense_raw = json.load(f)
            if isinstance(defense_raw, list):
                self.team_defense = {item.get('team_name', item.get('team', '')): item for item in defense_raw}
            else:
                self.team_defense = defense_raw
        else:
            self.team_defense = {}
                
        self.loaded = True
        print(f"✅ Zone Scanner: {len(self.defenders_data)} défenseurs, {len(self.teams_defenders)} équipes")
    
    def _calculate_alpha_league(self, defender: Dict) -> float:
        """Calcule Alpha League pour un défenseur"""
        player_ga = defender.get('goals_conceded_per_match_with', 0) or self.league_avg_ga
        return (self.league_avg_ga - player_ga) / self.league_avg_ga
    
    def _calculate_panic_score(self, defender: Dict) -> float:
        """Calcule un score de panique 0-100"""
        state = defender.get('quant_v9', {}).get('hidden_markov', {}).get('current_state', 'STABLE_AVERAGE')
        
        panic_by_state = {
            'ELITE_FORM': 5,
            'CLUTCH_MODE': 10,
            'CONSISTENT_ROCK': 15,
            'IMPROVING': 25,
            'STABLE_AVERAGE': 35,
            'ADAPTING': 40,
            'FLUCTUATING': 45,
            'INCONSISTENT_NEUTRAL': 50,
            'DECLINING': 60,
            'PRESSURE_CRACKER': 75,
            'PRESSURE_SENSITIVE': 70,
            'SLUMP': 80,
            'FORM_SLUMP': 75,
            'CONFIDENCE_CRISIS': 85,
            'CONFIDENCE_LOW': 80,
            'TOTAL_COLLAPSE': 95,
            'LIABILITY_CONFIRMED': 90,
            'CRISIS': 90,
            'UNKNOWN': 50
        }
        
        return panic_by_state.get(state, 50)
    
    def _get_position_category(self, defender: Dict) -> str:
        """Retourne la catégorie de position"""
        pos = defender.get('position_category', defender.get('position', 'CB'))
        # Normaliser
        if pos in ['D', 'DF']:
            return 'CB'  # Default
        return pos
    
    def scan_zone_weaknesses(self, team: str) -> List[ZoneWeakness]:
        """
        Scanne les zones de faiblesse d'une équipe
        Identifie les paires adjacentes de défenseurs faibles
        """
        self.load_data()
        
        defenders = self.teams_defenders.get(team, [])
        if not defenders:
            return []
        
        # Filtrer titulaires (>500 min)
        starters = [d for d in defenders if d.get('time', 0) > 500]
        if not starters:
            starters = defenders[:5]
        
        zone_reports = []
        
        for zone_name, positions in self.ZONES.items():
            # Trouver les défenseurs dans cette zone
            zone_players = []
            for d in starters:
                pos = self._get_position_category(d)
                # Match flexible (CB peut être LCB ou RCB)
                if pos in positions or pos == 'CB':
                    zone_players.append(d)
            
            if not zone_players:
                continue
            
            # Calculer les métriques
            alphas_league = [self._calculate_alpha_league(d) for d in zone_players]
            alphas_team = [d.get('quant_v9', {}).get('alpha_beta', {}).get('alpha', 0) for d in zone_players]
            
            avg_alpha_league = np.mean(alphas_league)
            avg_alpha_team = np.mean(alphas_team)
            
            # Compter les liabilities
            liabilities = sum(1 for a in alphas_league if a < -0.3)
            weak = sum(1 for a in alphas_league if -0.3 <= a < -0.1)
            
            # Calculer le score de liability combiné
            combined_liability = abs(avg_alpha_league) * (1 + 0.5 * (liabilities - 1))
            
            # Déterminer la sévérité
            if liabilities >= 2:
                severity = ZoneSeverity.CRITICAL
                edge_boost = 8.0
            elif liabilities == 1 and weak >= 1:
                severity = ZoneSeverity.HIGH
                edge_boost = 5.0
            elif liabilities == 1:
                severity = ZoneSeverity.ELEVATED
                edge_boost = 3.0
            elif weak >= 2:
                severity = ZoneSeverity.MODERATE
                edge_boost = 2.0
            else:
                severity = ZoneSeverity.SOLID
                edge_boost = 0
            
            # Marchés recommandés
            target_pos = self.ZONE_EXPLOITER.get(zone_name, 'ST')
            recommended_markets = []
            
            if severity in [ZoneSeverity.CRITICAL, ZoneSeverity.HIGH]:
                recommended_markets = [
                    {'market': f'Opponent {target_pos} Anytime Scorer', 'edge': edge_boost},
                    {'market': f'Opponent {target_pos} 1+ Assist', 'edge': edge_boost * 0.7},
                    {'market': 'Over 0.5 Goals 1st Half', 'edge': edge_boost * 0.5}
                ]
            elif severity == ZoneSeverity.ELEVATED:
                recommended_markets = [
                    {'market': 'Opponent Team Over 1.5 Goals', 'edge': edge_boost}
                ]
            
            zone_reports.append(ZoneWeakness(
                zone_name=zone_name,
                players=[d.get('name') for d in zone_players],
                avg_alpha_league=round(avg_alpha_league, 2),
                avg_alpha_team=round(avg_alpha_team, 2),
                combined_liability=round(combined_liability, 2),
                severity=severity,
                target_position=target_pos,
                recommended_markets=recommended_markets,
                edge_boost=edge_boost
            ))
        
        return zone_reports
    
    def classify_panic_alpha(self, defender: Dict) -> PanicAlphaProfile:
        """
        Classifie un défenseur dans la matrice Panic × Alpha
        """
        self.load_data()
        
        alpha_league = self._calculate_alpha_league(defender)
        panic_score = self._calculate_panic_score(defender)
        markov_state = defender.get('quant_v9', {}).get('hidden_markov', {}).get('current_state', 'UNKNOWN')
        
        # Déterminer le quadrant
        if alpha_league < -0.2 and panic_score < 50:
            quadrant = PanicAlphaQuadrant.PASSOIRE
            strategy = "Over Team Goals (adversaire marquera)"
            timing = "PRE_MATCH"
        elif alpha_league < -0.2 and panic_score >= 50:
            quadrant = PanicAlphaQuadrant.CATASTROPHE
            strategy = "Max Short - Explosion imminente"
            timing = "PRE_MATCH"
        elif alpha_league >= 0 and panic_score < 40:
            quadrant = PanicAlphaQuadrant.SOLIDE
            strategy = "Skip ou Under"
            timing = "SKIP"
        else:
            quadrant = PanicAlphaQuadrant.BOMBE_RETARDEMENT
            strategy = "Live Bet - Attendre l'erreur"
            timing = "LIVE"
        
        return PanicAlphaProfile(
            defender_name=defender.get('name', 'Unknown'),
            team=defender.get('team', 'Unknown'),
            alpha_league=round(alpha_league, 2),
            panic_score=panic_score,
            markov_state=markov_state,
            quadrant=quadrant,
            strategy=strategy,
            timing=timing
        )
    
    def calculate_short_squeeze(
        self, 
        defending_team: str, 
        opponent_team: str
    ) -> ShortSqueezeSignal:
        """
        Calcule le signal Short-Squeeze avec le catalyseur adverse
        
        Collapse_Prob = Liability_Score × Opponent_Pressure_Index
        """
        self.load_data()
        
        # 1. Liability Score de la défense
        defenders = self.teams_defenders.get(defending_team, [])
        if not defenders:
            return None
        
        starters = [d for d in defenders if d.get('time', 0) > 500][:5]
        alphas = [self._calculate_alpha_league(d) for d in starters]
        
        # Score de liability: moyenne des alphas négatifs transformée en 0-1
        avg_alpha = np.mean(alphas)
        liability_score = max(0, min(1, -avg_alpha))  # Plus c'est négatif, plus c'est élevé
        
        # 2. Pressure Index de l'adversaire
        opponent_data = self.attack_dna.get(opponent_team, {})
        
        # Facteurs de pression
        xg = opponent_data.get('attack_metrics', {}).get('xg_per_90', 1.2)
        shots = opponent_data.get('attack_metrics', {}).get('shots_per_90', 12)
        
        # Normaliser en index 0.5-1.5
        xg_factor = xg / 1.3  # 1.3 = moyenne
        shots_factor = shots / 13  # 13 = moyenne
        
        pressure_index = (xg_factor + shots_factor) / 2
        pressure_index = max(0.5, min(1.5, pressure_index))
        
        # 3. Collapse Probability
        collapse_prob = liability_score * pressure_index
        collapse_prob = min(1.0, collapse_prob)
        
        # 4. Signal Strength
        if collapse_prob >= 0.7:
            signal_strength = "MAX_BET"
            markets = [
                'Opponent Team Over 2.5 Goals',
                'Over 3.5 Goals Total',
                'Penalty in Match',
                'Opponent Clean Sheet'
            ]
        elif collapse_prob >= 0.5:
            signal_strength = "STANDARD"
            markets = [
                'Opponent Team Over 1.5 Goals',
                'Over 2.5 Goals Total'
            ]
        elif collapse_prob >= 0.3:
            signal_strength = "CAUTIOUS"
            markets = ['Over 2.5 Goals Total']
        else:
            signal_strength = "SKIP"
            markets = []
        
        reasoning = (
            f"{defending_team} liability={liability_score:.2f} × "
            f"{opponent_team} pressure={pressure_index:.2f} = "
            f"Collapse {collapse_prob:.0%}"
        )
        
        return ShortSqueezeSignal(
            defending_team=defending_team,
            liability_score=round(liability_score, 2),
            opponent_team=opponent_team,
            opponent_pressure_index=round(pressure_index, 2),
            collapse_probability=round(collapse_prob, 2),
            signal_strength=signal_strength,
            recommended_markets=markets,
            reasoning=reasoning
        )
    
    def full_analysis(self, team: str, opponent: str = None) -> Dict:
        """
        Analyse complète d'une équipe avec les 3 options
        """
        self.load_data()
        
        result = {
            'team': team,
            'opponent': opponent,
            'zones': [],
            'panic_alpha_profiles': [],
            'short_squeeze': None
        }
        
        # Option 1: Zone Weaknesses
        zones = self.scan_zone_weaknesses(team)
        result['zones'] = zones
        
        # Option 2: Panic-Alpha pour chaque défenseur
        defenders = self.teams_defenders.get(team, [])
        starters = [d for d in defenders if d.get('time', 0) > 500][:5]
        
        for d in starters:
            profile = self.classify_panic_alpha(d)
            result['panic_alpha_profiles'].append(profile)
        
        # Option 3: Short-Squeeze si adversaire fourni
        if opponent:
            result['short_squeeze'] = self.calculate_short_squeeze(team, opponent)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    scanner = DefenseZoneScanner()
    
    print("="*80)
    print("🎯 DEFENSE ZONE SCANNER V2.0 - TEST COMPLET")
    print("="*80)
    
    # Test West Ham vs Arsenal
    print("\n" + "="*80)
    print("📊 WEST HAM vs ARSENAL")
    print("="*80)
    
    analysis = scanner.full_analysis("West Ham", "Arsenal")
    
    print("\n🔴 ZONES DE FAIBLESSE:")
    for zone in analysis['zones']:
        emoji = "🔴" if zone.severity == ZoneSeverity.CRITICAL else "🟠" if zone.severity == ZoneSeverity.HIGH else "🟡"
        print(f"   {emoji} {zone.zone_name}: {zone.severity.value}")
        print(f"      Joueurs: {', '.join(zone.players[:3])}")
        print(f"      Alpha League moyen: {zone.avg_alpha_league}")
        print(f"      Cible: {zone.target_position} adverse")
        if zone.recommended_markets:
            print(f"      Marchés: {zone.recommended_markets[0]['market']} (+{zone.edge_boost}%)")
    
    print("\n🧠 MATRICE PANIC × ALPHA:")
    for profile in analysis['panic_alpha_profiles']:
        emoji = "🔴" if profile.quadrant == PanicAlphaQuadrant.CATASTROPHE else "🟠" if profile.quadrant == PanicAlphaQuadrant.PASSOIRE else "🟢"
        print(f"   {emoji} {profile.defender_name}: {profile.quadrant.value}")
        print(f"      α_league={profile.alpha_league}, Panic={profile.panic_score}")
        print(f"      → {profile.strategy} ({profile.timing})")
    
    if analysis['short_squeeze']:
        ss = analysis['short_squeeze']
        print(f"\n⚡ SHORT-SQUEEZE:")
        print(f"   {ss.reasoning}")
        print(f"   Signal: {ss.signal_strength}")
        print(f"   Marchés: {', '.join(ss.recommended_markets[:2])}")
    
    # Test Heidenheim vs Leverkusen
    print("\n" + "="*80)
    print("📊 HEIDENHEIM vs LEVERKUSEN")
    print("="*80)
    
    analysis2 = scanner.full_analysis("FC Heidenheim", "Bayer Leverkusen")
    
    print("\n🔴 ZONES DE FAIBLESSE:")
    for zone in analysis2['zones']:
        emoji = "🔴" if zone.severity == ZoneSeverity.CRITICAL else "🟠" if zone.severity == ZoneSeverity.HIGH else "🟡"
        print(f"   {emoji} {zone.zone_name}: {zone.severity.value}")
        print(f"      Alpha League moyen: {zone.avg_alpha_league}")
    
    if analysis2['short_squeeze']:
        ss = analysis2['short_squeeze']
        print(f"\n⚡ SHORT-SQUEEZE:")
        print(f"   {ss.reasoning}")
        print(f"   Signal: {ss.signal_strength}")
    
    # Comparaison Heidenheim vs équipe faible
    print("\n" + "="*80)
    print("📊 HEIDENHEIM vs BOCHUM (contrôle)")
    print("="*80)
    
    analysis3 = scanner.full_analysis("FC Heidenheim", "VfL Bochum")
    
    if analysis3['short_squeeze']:
        ss = analysis3['short_squeeze']
        print(f"\n⚡ SHORT-SQUEEZE:")
        print(f"   {ss.reasoning}")
        print(f"   Signal: {ss.signal_strength}")
        print(f"   → Différence vs Leverkusen: le catalyseur fait la différence!")

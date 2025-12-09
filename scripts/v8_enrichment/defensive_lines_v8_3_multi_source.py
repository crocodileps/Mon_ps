#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
 DEFENSIVE LINES V8.3 - MULTI-SOURCE INTEGRATION
 
 Sources intégrées:
 1. team_defense_dna_2025_fixed.json (96 équipes, timing 76-90 corrigé)
 2. goalkeeper_timing_dna_v1.json (96 GK, timing par période)
 3. defender_dna_quant_v9.json (664 défenseurs, impact with/without)
 4. teams_context_dna.json (momentum, forme)
 5. team_exploit_profiles.json (vulnérabilités, exploit paths)
 
═══════════════════════════════════════════════════════════════════════════════
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics
import hashlib
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_PATHS = {
    'team_defense': '/home/Mon_ps/data/defense_dna/team_defense_dna_2025_fixed.json',
    'goalkeeper': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_timing_dna_v1.json',
    'defenders': '/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json',
    'context': '/home/Mon_ps/data/quantum_v2/teams_context_dna.json',
    'exploits': '/home/Mon_ps/data/quantum_v2/team_exploit_profiles.json',
}

OUTPUT_PATH = '/home/Mon_ps/data/defensive_lines/defensive_lines_v8_3_multi_source.json'

# ═══════════════════════════════════════════════════════════════════════════════
# LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: str) -> Any:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ {path}: {e}")
        return None

def normalize_team(name: str) -> str:
    if not name:
        return ""
    name = name.lower().strip().replace('_', ' ')
    mappings = {
        'man united': 'manchester united', 'man city': 'manchester city',
        'tottenham hotspur': 'tottenham', 'wolves': 'wolverhampton wanderers',
        'newcastle': 'newcastle united', 'west ham united': 'west ham',
        'brighton and hove albion': 'brighton', 'psg': 'paris saint germain',
        'paris saint-germain': 'paris saint germain', 'rb leipzig': 'rasenballsport leipzig',
        'inter milan': 'inter', 'internazionale': 'inter', 'as roma': 'roma',
        'fc barcelona': 'barcelona', 'atletico': 'atletico madrid',
    }
    return mappings.get(name, name)

# ═══════════════════════════════════════════════════════════════════════════════
# INDEX BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_gk_index(gk_data: List[Dict]) -> Dict[str, Dict]:
    """Index GK par équipe avec timing 76-90"""
    index = {}
    for gk in gk_data:
        team = normalize_team(gk.get('team', ''))
        if team:
            timing_76_90 = gk.get('timing', {}).get('76-90', {})
            index[team] = {
                'name': gk.get('goalkeeper', 'Unknown'),
                'percentile': gk.get('gk_percentile', 50),
                'profile': gk.get('profile_v31', 'UNKNOWN'),
                'save_rate': gk.get('save_rate', 65),
                'save_rate_76_90': timing_76_90.get('save_rate', 65),
                'goals_76_90': timing_76_90.get('goals', 0),
                'shots_76_90': timing_76_90.get('shots', 0),
                'xG_76_90': timing_76_90.get('xG', 0),
                'vulnerabilities': gk.get('vulnerabilities', []),
                'timing_tags': gk.get('timing_tags', []),
            }
    return index

def build_defenders_index(def_data: List[Dict]) -> Dict[str, Dict]:
    """Agrège les défenseurs par équipe"""
    team_defs = defaultdict(list)
    
    for d in def_data:
        team = normalize_team(d.get('team', ''))
        if team:
            team_defs[team].append(d)
    
    index = {}
    for team, defenders in team_defs.items():
        # Trier par temps de jeu
        sorted_defs = sorted(defenders, key=lambda x: x.get('time_90', 0) or 0, reverse=True)
        top_5 = sorted_defs[:5]
        
        if top_5:
            # Agrégations
            avg_cards = statistics.mean([d.get('cards_90', 0) or 0 for d in top_5])
            avg_impact = statistics.mean([d.get('impact_goals_conceded', 0) or 0 for d in top_5])
            avg_goals_with = statistics.mean([d.get('goals_conceded_per_match_with', 0) or 0 for d in top_5])
            avg_goals_without = statistics.mean([d.get('goals_conceded_per_match_without', 0) or 0 for d in top_5])
            avg_cs_with = statistics.mean([d.get('clean_sheet_rate_with', 0) or 0 for d in top_5])
            
            index[team] = {
                'num_defenders': len(defenders),
                'top_5_names': [d['name'] for d in top_5],
                'avg_cards_90': round(avg_cards, 3),
                'avg_impact': round(avg_impact, 3),
                'avg_goals_with': round(avg_goals_with, 3),
                'avg_goals_without': round(avg_goals_without, 3),
                'goals_delta': round(avg_goals_without - avg_goals_with, 3),
                'avg_cs_rate': round(avg_cs_with, 1),
                'disciplinary_risk': 'HIGH' if avg_cards > 0.35 else 'MODERATE' if avg_cards > 0.2 else 'LOW',
            }
    
    return index

def build_context_index(ctx_data: Dict) -> Dict[str, Dict]:
    """Index context DNA par équipe"""
    index = {}
    for team_name, data in ctx_data.items():
        team = normalize_team(team_name)
        ctx = data.get('context_dna', {})
        momentum = data.get('momentum_dna', {})
        
        index[team] = {
            'form_score': ctx.get('form_score', 50),
            'home_advantage': ctx.get('home_advantage', 1.0),
            'away_form': ctx.get('away_form', 50),
            'momentum_score': momentum.get('momentum_score', 0),
            'trend': momentum.get('trend', 'STABLE'),
            'goals_trend': momentum.get('goals_trend', 0),
        }
    
    return index

def build_exploits_index(exploit_data: Dict) -> Dict[str, Dict]:
    """Index exploit profiles par équipe"""
    index = {}
    for team_name, data in exploit_data.items():
        team = normalize_team(team_name)
        
        index[team] = {
            'vulnerability_score': data.get('vulnerability_score', 50),
            'exploit_paths': data.get('exploit_paths', []),
            'num_vulnerabilities': len(data.get('vulnerabilities', [])),
            'top_vulnerabilities': data.get('vulnerabilities', [])[:3],
        }
    
    return index

# ═══════════════════════════════════════════════════════════════════════════════
# TIMING DNA (from V8.2)
# ═══════════════════════════════════════════════════════════════════════════════

def create_timing_dna(team: Dict) -> Dict:
    periods_xga = {
        '0-15': team.get('xga_0_15', 0) or 0,
        '16-30': team.get('xga_16_30', 0) or 0,
        '31-45': team.get('xga_31_45', 0) or 0,
        '46-60': team.get('xga_46_60', 0) or 0,
        '61-75': team.get('xga_61_75', 0) or 0,
        '76-90': team.get('xga_76_90', 0) or 0,
    }
    
    total_xga = sum(periods_xga.values())
    
    if total_xga > 0:
        periods_pct = {k: round(v / total_xga * 100, 1) for k, v in periods_xga.items()}
    else:
        periods_pct = {k: 16.7 for k in periods_xga.keys()}
    
    early = periods_pct['0-15'] + periods_pct['16-30']
    mid = periods_pct['31-45'] + periods_pct['46-60']
    late = periods_pct['61-75'] + periods_pct['76-90']
    
    peak_period = max(periods_pct, key=periods_pct.get)
    weakest_period = min(periods_pct, key=periods_pct.get)
    
    # Timing tags
    timing_tags = []
    if early > 42: timing_tags.append('EARLY_HEAVY')
    elif early > 36: timing_tags.append('EARLY_VULNERABLE')
    elif early < 28: timing_tags.append('EARLY_SOLID')
    
    if late > 40: timing_tags.append('LATE_COLLAPSER')
    elif late > 35: timing_tags.append('LATE_VULNERABLE')
    elif late < 25: timing_tags.append('LATE_FORTRESS')
    
    if periods_pct['76-90'] > 20: timing_tags.append('CLOSING_VULNERABLE')
    elif periods_pct['76-90'] < 10: timing_tags.append('CLOSING_SOLID')
    
    # Primary profile
    if 'LATE_COLLAPSER' in timing_tags:
        primary = 'LATE_COLLAPSER' if 'EARLY_SOLID' not in timing_tags else 'STARTS_STRONG_FADES'
    elif 'LATE_VULNERABLE' in timing_tags:
        primary = 'LATE_VULNERABLE'
    elif 'EARLY_HEAVY' in timing_tags or 'EARLY_VULNERABLE' in timing_tags:
        primary = 'SLOW_STARTER_STRONG_FINISH' if 'LATE_FORTRESS' in timing_tags else 'SLOW_STARTER'
    elif 'LATE_FORTRESS' in timing_tags:
        primary = 'STRONG_FINISHER'
    elif 'EARLY_SOLID' in timing_tags:
        primary = 'FAST_STARTER'
    else:
        primary = 'BALANCED'
    
    # DNA code unique (inclut plus de granularité)
    def quantize(val): return min(9, max(0, int(val / 10)))
    timing_vector = [quantize(periods_pct[p]) for p in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90']]
    timing_code = ''.join(str(v) for v in timing_vector)
    
    # Hash plus unique (inclut peak et weak)
    hash_input = f"{timing_code}_{peak_period}_{weakest_period}_{primary}_{round(late,0)}"
    dna_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()
    
    return {
        'periods_xga': periods_xga,
        'periods_pct': periods_pct,
        'early_pct': round(early, 1),
        'mid_pct': round(mid, 1),
        'late_pct': round(late, 1),
        'peak_period': peak_period,
        'weakest_period': weakest_period,
        'timing_tags': timing_tags,
        'primary_profile': primary,
        'timing_code': timing_code,
        'dna_hash': dna_hash,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# RESISTANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_resistance(team: Dict) -> Dict:
    xga_90 = team.get('xga_per_90', 1.2) or 1.2
    
    if xga_90 < 0.8: resist, profile = 95, 'ELITE_FORTRESS'
    elif xga_90 < 1.0: resist, profile = 80, 'SOLID'
    elif xga_90 < 1.2: resist, profile = 65, 'ABOVE_AVERAGE'
    elif xga_90 < 1.4: resist, profile = 50, 'AVERAGE'
    elif xga_90 < 1.7: resist, profile = 35, 'VULNERABLE'
    elif xga_90 < 2.0: resist, profile = 20, 'CRISIS'
    else: resist, profile = 10, 'CATASTROPHIC'
    
    return {'profile': profile, 'resist_global': resist, 'xga_per_90': xga_90}

# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CALCULATION V8.3
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_edge_v83(
    team: Dict,
    resistance: Dict,
    timing_dna: Dict,
    gk_data: Optional[Dict],
    def_data: Optional[Dict],
    ctx_data: Optional[Dict],
    exploit_data: Optional[Dict]
) -> Dict:
    
    ec = {}
    
    # 1. RESISTANCE EDGE (base)
    rg = resistance['resist_global']
    if rg < 20: ec['resistance_edge'] = 8.0
    elif rg < 35: ec['resistance_edge'] = 5.0
    elif rg < 50: ec['resistance_edge'] = 2.0
    elif rg < 65: ec['resistance_edge'] = 0.0
    elif rg < 80: ec['resistance_edge'] = -3.0
    else: ec['resistance_edge'] = -6.0
    
    # 2. TIMING EDGE
    profile = timing_dna['primary_profile']
    if profile in ['LATE_COLLAPSER', 'STARTS_STRONG_FADES']: ec['temporal_edge'] = 3.5
    elif profile == 'LATE_VULNERABLE': ec['temporal_edge'] = 2.5
    elif profile in ['SLOW_STARTER']: ec['temporal_edge'] = 1.5
    elif profile in ['STRONG_FINISHER', 'FAST_STARTER']: ec['temporal_edge'] = -2.0
    else: ec['temporal_edge'] = 0.0
    
    # 3. CLOSING EDGE (76-90)
    closing_pct = timing_dna['periods_pct']['76-90']
    if closing_pct > 22: ec['closing_edge'] = 2.5
    elif closing_pct > 18: ec['closing_edge'] = 1.5
    elif closing_pct < 10: ec['closing_edge'] = -2.0
    else: ec['closing_edge'] = 0.0
    
    # 4. GK EDGE (nouveau V8.3)
    if gk_data:
        gk_pct = gk_data.get('percentile', 50)
        gk_sr_76_90 = gk_data.get('save_rate_76_90', 65)
        
        # GK global
        if gk_pct < 25: ec['gk_quality_edge'] = 3.0
        elif gk_pct < 40: ec['gk_quality_edge'] = 1.5
        elif gk_pct > 80: ec['gk_quality_edge'] = -2.5
        elif gk_pct > 65: ec['gk_quality_edge'] = -1.0
        else: ec['gk_quality_edge'] = 0.0
        
        # GK 76-90 spécifique
        if gk_sr_76_90 < 40: ec['gk_closing_edge'] = 2.5
        elif gk_sr_76_90 < 55: ec['gk_closing_edge'] = 1.5
        elif gk_sr_76_90 > 85: ec['gk_closing_edge'] = -1.5
        else: ec['gk_closing_edge'] = 0.0
    else:
        ec['gk_quality_edge'] = 0.0
        ec['gk_closing_edge'] = 0.0
    
    # 5. DEFENDERS EDGE (nouveau V8.3)
    if def_data:
        goals_delta = def_data.get('goals_delta', 0)
        disc_risk = def_data.get('disciplinary_risk', 'LOW')
        
        # Impact défenseurs
        if goals_delta > 0.5: ec['defenders_impact_edge'] = 2.0
        elif goals_delta > 0.2: ec['defenders_impact_edge'] = 1.0
        elif goals_delta < -0.3: ec['defenders_impact_edge'] = -1.5
        else: ec['defenders_impact_edge'] = 0.0
        
        # Risque disciplinaire
        if disc_risk == 'HIGH': ec['disciplinary_edge'] = 1.5
        elif disc_risk == 'MODERATE': ec['disciplinary_edge'] = 0.5
        else: ec['disciplinary_edge'] = 0.0
    else:
        ec['defenders_impact_edge'] = 0.0
        ec['disciplinary_edge'] = 0.0
    
    # 6. CONTEXT/MOMENTUM EDGE (nouveau V8.3)
    if ctx_data:
        momentum = ctx_data.get('momentum_score', 0)
        trend = ctx_data.get('trend', 'STABLE')
        
        # Momentum négatif = plus vulnérable
        if momentum < -3: ec['momentum_edge'] = 2.0
        elif momentum < -1: ec['momentum_edge'] = 1.0
        elif momentum > 3: ec['momentum_edge'] = -1.5
        else: ec['momentum_edge'] = 0.0
    else:
        ec['momentum_edge'] = 0.0
    
    # 7. EXPLOIT PATHS EDGE (nouveau V8.3)
    if exploit_data:
        vuln_score = exploit_data.get('vulnerability_score', 50)
        num_paths = len(exploit_data.get('exploit_paths', []))
        
        if vuln_score > 70: ec['exploit_edge'] = 2.5
        elif vuln_score > 55: ec['exploit_edge'] = 1.5
        elif vuln_score < 30: ec['exploit_edge'] = -1.5
        else: ec['exploit_edge'] = 0.0
        
        # Bonus paths
        if num_paths >= 5: ec['paths_bonus'] = 1.0
        else: ec['paths_bonus'] = 0.0
    else:
        ec['exploit_edge'] = 0.0
        ec['paths_bonus'] = 0.0
    
    # 8. REGRESSION EDGE
    overperform = team.get('defense_overperform', 0) or 0
    if overperform > 6: ec['regression_edge'] = 2.5
    elif overperform > 3: ec['regression_edge'] = 1.0
    elif overperform < -6: ec['regression_edge'] = -2.0
    else: ec['regression_edge'] = 0.0
    
    # TOTAL
    total = sum(ec.values())
    
    # Classification
    if total >= 18: classif, kelly_mult = 'EXTREME_VALUE', 1.0
    elif total >= 12: classif, kelly_mult = 'HIGH_VALUE', 0.75
    elif total >= 7: classif, kelly_mult = 'MODERATE_VALUE', 0.5
    elif total >= 3: classif, kelly_mult = 'SLIGHT_VALUE', 0.25
    elif total >= -3: classif, kelly_mult = 'NO_VALUE', 0.0
    else: classif, kelly_mult = 'NEGATIVE_VALUE', 0.0
    
    kelly = min(5.0, max(0.0, total * kelly_mult * 0.15))
    
    # Top drivers
    sorted_ec = sorted(ec.items(), key=lambda x: abs(x[1]), reverse=True)
    top_drivers = [(k, v) for k, v in sorted_ec[:3] if v != 0]
    
    return {
        'components': ec,
        'total_edge': round(total, 2),
        'classification': classif,
        'kelly_stake': round(kelly, 2),
        'confidence': min(100, max(0, 50 + total * 2)),
        'top_drivers': top_drivers,
        'sources_used': sum([
            1 if gk_data else 0,
            1 if def_data else 0,
            1 if ctx_data else 0,
            1 if exploit_data else 0,
        ]) + 2,  # +2 for team_defense and timing
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL DNA SIGNATURE
# ═══════════════════════════════════════════════════════════════════════════════

def generate_dna_signature(team_name: str, edge: Dict, resistance: Dict, timing_dna: Dict, gk_data: Optional[Dict]) -> str:
    parts = [
        edge['classification'][:3],
        resistance['profile'][:4],
        timing_dna['primary_profile'][:4],
        f"GK{gk_data['percentile']:.0f}" if gk_data else "GK?",
        timing_dna['timing_code'],
        f"E{edge['total_edge']:+.0f}",
    ]
    return '|'.join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_team(team: Dict, gk_idx: Dict, def_idx: Dict, ctx_idx: Dict, exp_idx: Dict) -> Dict:
    team_name = team.get('team_name', 'Unknown')
    normalized = normalize_team(team_name)
    
    # Get all data
    gk_data = gk_idx.get(normalized)
    def_data = def_idx.get(normalized)
    ctx_data = ctx_idx.get(normalized)
    exploit_data = exp_idx.get(normalized)
    
    # Core analysis
    resistance = analyze_resistance(team)
    timing_dna = create_timing_dna(team)
    
    # Edge calculation with all sources
    edge = calculate_edge_v83(team, resistance, timing_dna, gk_data, def_data, ctx_data, exploit_data)
    
    # DNA signature
    dna_sig = generate_dna_signature(team_name, edge, resistance, timing_dna, gk_data)
    
    return {
        'team_name': team_name,
        'league': team.get('league', 'Unknown'),
        
        'foundation': {
            'matches': team.get('matches_played', 0),
            'xga_90': round(team.get('xga_per_90', 0) or 0, 3),
            'ga_90': round(team.get('ga_per_90', 0) or 0, 3),
            'cs_pct': round(team.get('cs_pct', 0) or 0, 1),
            'overperform': round(team.get('defense_overperform', 0) or 0, 2),
        },
        
        'resistance': resistance,
        'timing_dna': timing_dna,
        
        'goalkeeper': gk_data if gk_data else {'status': 'NO_DATA'},
        'defenders': def_data if def_data else {'status': 'NO_DATA'},
        'context': ctx_data if ctx_data else {'status': 'NO_DATA'},
        'exploits': exploit_data if exploit_data else {'status': 'NO_DATA'},
        
        'edge': edge,
        
        'global_dna': dna_sig,
        'dna_hash': timing_dna['dna_hash'],
        
        'version': 'V8.3_MULTI_SOURCE',
        'timestamp': datetime.now().isoformat(),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("🧬 DEFENSIVE LINES V8.3 - MULTI-SOURCE INTEGRATION")
    print("=" * 70)
    
    # Load all sources
    print("\n📂 CHARGEMENT SOURCES:")
    team_data = load_json(DATA_PATHS['team_defense'])
    gk_data = load_json(DATA_PATHS['goalkeeper'])
    def_data = load_json(DATA_PATHS['defenders'])
    ctx_data = load_json(DATA_PATHS['context'])
    exp_data = load_json(DATA_PATHS['exploits'])
    
    print(f"   ✅ Team Defense: {len(team_data)} équipes")
    print(f"   ✅ Goalkeepers: {len(gk_data)} GK")
    print(f"   ✅ Defenders: {len(def_data)} défenseurs")
    print(f"   ✅ Context DNA: {len(ctx_data)} équipes")
    print(f"   ✅ Exploit Profiles: {len(exp_data)} équipes")
    
    # Build indexes
    print("\n🔄 CONSTRUCTION INDEX:")
    gk_idx = build_gk_index(gk_data)
    def_idx = build_defenders_index(def_data)
    ctx_idx = build_context_index(ctx_data)
    exp_idx = build_exploits_index(exp_data)
    
    print(f"   ✅ GK Index: {len(gk_idx)} équipes")
    print(f"   ✅ Defenders Index: {len(def_idx)} équipes")
    print(f"   ✅ Context Index: {len(ctx_idx)} équipes")
    print(f"   ✅ Exploit Index: {len(exp_idx)} équipes")
    
    # Analyze all teams
    print("\n📊 ANALYSE:")
    results = []
    for team in team_data:
        result = analyze_team(team, gk_idx, def_idx, ctx_idx, exp_idx)
        results.append(result)
        
        e = result['edge']
        t = result['timing_dna']
        gk = result['goalkeeper']
        gk_sr = gk.get('save_rate_76_90', 'N/A') if isinstance(gk, dict) and gk.get('name') else 'N/A'
        
        print(f"  {result['team_name']:25} | {e['total_edge']:+6.1f}% | {t['primary_profile']:20} | GK76-90:{gk_sr}")
    
    # Sort by edge
    results.sort(key=lambda x: x['edge']['total_edge'], reverse=True)
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Sauvegardé: {OUTPUT_PATH}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 TOP 10 GOALS OVER VALUE")
    print("=" * 70)
    for i, t in enumerate(results[:10], 1):
        print(f"{i:2}. {t['team_name']:25} | {t['edge']['total_edge']:+6.1f}% | K:{t['edge']['kelly_stake']:.1f}% | Sources:{t['edge']['sources_used']}/6 | {t['global_dna']}")
    
    print("\n" + "=" * 70)
    print("📉 TOP 10 GOALS UNDER VALUE")
    print("=" * 70)
    for i, t in enumerate(results[-10:][::-1], 1):
        print(f"{i:2}. {t['team_name']:25} | {t['edge']['total_edge']:+6.1f}% | K:{t['edge']['kelly_stake']:.1f}% | Sources:{t['edge']['sources_used']}/6 | {t['global_dna']}")
    
    # Stats
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES V8.3")
    print("=" * 70)
    
    edges = [r['edge']['total_edge'] for r in results]
    print(f"Edge moyen: {statistics.mean(edges):+.1f}%")
    print(f"Min/Max: {min(edges):+.1f}% / {max(edges):+.1f}%")
    
    # DNA uniqueness
    hashes = [r['dna_hash'] for r in results]
    unique = len(set(hashes))
    print(f"\n🧬 DNA UNIQUENESS: {unique}/{len(results)} ({unique/len(results)*100:.1f}%)")
    
    # Distribution
    from collections import Counter
    profiles = Counter(r['timing_dna']['primary_profile'] for r in results)
    print("\n📊 DISTRIBUTION TIMING:")
    for p, c in profiles.most_common():
        print(f"   {p:30}: {c:2} ({c/len(results)*100:.1f}%)")
    
    # Sources coverage
    print("\n📊 COUVERTURE SOURCES:")
    full_coverage = sum(1 for r in results if r['edge']['sources_used'] == 6)
    print(f"   6/6 sources: {full_coverage}/{len(results)} équipes")

if __name__ == '__main__':
    main()

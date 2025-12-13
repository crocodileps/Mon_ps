#!/usr/bin/env python3
"""
NARRATIVE DNA V3.0 - Profil Complet Hedge Fund Grade
=====================================================
"""

import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional
import hashlib

DATA_DIR = '/home/Mon_ps/data/quantum_v2'
OUTPUT_FILE = f'{DATA_DIR}/team_narrative_dna_v3.json'

def load_all_data():
    """Charge toutes les sources de données."""
    print("=" * 80)
    print("NARRATIVE DNA V3.0 - CHARGEMENT DES DONNÉES")
    print("=" * 80)
    
    data = {}
    
    # 1. Team DNA Unified
    try:
        with open(f'{DATA_DIR}/team_dna_unified_v2.json') as f:
            raw = json.load(f)
            data['team_dna'] = raw.get('teams', raw)
        print(f"✅ team_dna_unified_v2: {len(data['team_dna'])} équipes")
    except Exception as e:
        print(f"❌ team_dna_unified_v2: {e}")
        data['team_dna'] = {}
    
    # 2. PPDA depuis Understat
    try:
        with open(f'{DATA_DIR}/understat_ppda_by_team.json') as f:
            data['ppda'] = json.load(f)
        print(f"✅ understat_ppda: {len(data['ppda'])} équipes")
    except:
        data['ppda'] = {}
    
    # 3. Players Impact DNA
    try:
        with open(f'{DATA_DIR}/players_impact_dna.json') as f:
            players = json.load(f)
            data['players_by_team'] = defaultdict(list)
            for p in players:
                team = p.get('team', 'Unknown')
                data['players_by_team'][team].append(p)
        print(f"✅ players_impact_dna: {len(players)} joueurs")
    except:
        data['players_by_team'] = defaultdict(list)
    
    # 4. Attacker DNA V2
    try:
        with open(f'{DATA_DIR}/attacker_dna_v2.json') as f:
            attackers = json.load(f)
            data['attackers_by_team'] = defaultdict(list)
            for a in attackers:
                team = a.get('team', 'Unknown')
                data['attackers_by_team'][team].append(a)
        print(f"✅ attacker_dna_v2: {len(attackers)} attaquants")
    except:
        data['attackers_by_team'] = defaultdict(list)
    
    # 5. Defender Betting Profiles
    try:
        with open(f'{DATA_DIR}/defender_betting_profiles.json') as f:
            raw = json.load(f)
            if isinstance(raw, dict):
                defenders = []
                for team, players in raw.items():
                    if isinstance(players, list):
                        for p in players:
                            p['team'] = team
                            defenders.append(p)
            else:
                defenders = raw if isinstance(raw, list) else []
            
            data['defenders_by_team'] = defaultdict(list)
            for d in defenders:
                if isinstance(d, dict):
                    team = d.get('team', 'Unknown')
                    data['defenders_by_team'][team].append(d)
        print(f"✅ defender_betting_profiles: {len(defenders)} défenseurs")
    except Exception as e:
        print(f"⚠️ defender_betting_profiles: {e}")
        data['defenders_by_team'] = defaultdict(list)
    
    # 6. Midfielder Betting Profiles
    try:
        with open(f'{DATA_DIR}/midfielder_betting_profiles.json') as f:
            raw = json.load(f)
            if isinstance(raw, dict):
                midfielders = []
                for team, players in raw.items():
                    if isinstance(players, list):
                        for p in players:
                            p['team'] = team
                            midfielders.append(p)
            else:
                midfielders = raw if isinstance(raw, list) else []
            
            data['midfielders_by_team'] = defaultdict(list)
            for m in midfielders:
                if isinstance(m, dict):
                    team = m.get('team', 'Unknown')
                    data['midfielders_by_team'][team].append(m)
        print(f"✅ midfielder_betting_profiles: {len(midfielders)} milieux")
    except Exception as e:
        print(f"⚠️ midfielder_betting_profiles: {e}")
        data['midfielders_by_team'] = defaultdict(list)
    
    # 7. Goalkeeper DNA V4
    try:
        with open(f'{DATA_DIR}/goalkeeper_dna_v4.json') as f:
            data['goalkeeper_dna'] = json.load(f)
        print(f"✅ goalkeeper_dna_v4: loaded")
    except:
        data['goalkeeper_dna'] = {}
    
    # 8. Classification tactique ML V2
    try:
        with open(f'{DATA_DIR}/tactical_classification_ml_v2.json') as f:
            data['tactical_ml'] = json.load(f)
        print(f"✅ tactical_classification_ml_v2: {len(data['tactical_ml'])} équipes")
    except:
        data['tactical_ml'] = {}
    
    return data


def extract_tactical_dna(team_data: Dict, ppda_data: Dict, tactical_ml: Dict, team_name: str) -> Dict:
    tactical = team_data.get('tactical', {})
    fbref = team_data.get('fbref', {})
    
    ppda = None
    if team_name in ppda_data:
        ppda = ppda_data[team_name].get('ppda_avg')
    if not ppda:
        ppda = tactical.get('ppda')
    
    profile = 'UNKNOWN'
    confidence = 0
    if team_name in tactical_ml:
        profile = tactical_ml[team_name].get('predicted_profile', 'UNKNOWN')
        confidence = tactical_ml[team_name].get('confidence', 0)
    else:
        tp = tactical.get('tactical_profile', {})
        profile = tp.get('profile', 'UNKNOWN')
        confidence = tp.get('confidence', 0) or 0
    
    return {
        'profile': profile,
        'confidence': confidence,
        'ppda': ppda,
        'possession': fbref.get('possession_pct', 0),
        'deep_completions': ppda_data.get(team_name, {}).get('deep_avg', 0),
        'progressive_passes': fbref.get('progressive_passes', 0),
        'pressing_intensity': fbref.get('pressing_intensity', 'MEDIUM'),
        'matchup_guide': tactical.get('matchup_guide', {})
    }


def extract_goalkeeper_dna(team_data: Dict, gk_data_global: Dict, team_name: str) -> Dict:
    dl = team_data.get('defensive_line', {})
    gk_from_dl = dl.get('goalkeeper', {})
    
    save_rate = gk_from_dl.get('save_rate', 0) or 0
    status = 'ELITE' if save_rate > 75 else ('SOLID' if save_rate > 65 else ('AVERAGE' if save_rate > 55 else 'LEAKY'))
    
    return {
        'name': gk_from_dl.get('name', 'Unknown'),
        'save_rate': save_rate,
        'status': status,
        'gk_overperform': gk_from_dl.get('gk_overperform', 0),
        'profile': gk_from_dl.get('profile_v31', 'UNKNOWN'),
        'timing': gk_from_dl.get('timing', {}),
        'vulnerabilities': gk_from_dl.get('vulnerabilities', []),
        'strengths': gk_from_dl.get('strengths', [])
    }


def extract_defenders_dna(team_data: Dict, defenders_list: List) -> Dict:
    dl = team_data.get('defensive_line', {})
    defenders_from_dl = dl.get('defenders', {})
    
    all_defenders = []
    
    # Depuis defensive_line.defenders
    if isinstance(defenders_from_dl, dict):
        main_defs = defenders_from_dl.get('main_defenders', [])
        for d in main_defs:
            if isinstance(d, str):
                all_defenders.append({'name': d, 'position': 'CB', 'primary_role': 'CENTRAL', 'sub_role': 'N/A', 'minutes': 0})
            elif isinstance(d, dict):
                all_defenders.append(d)
    
    # Depuis defender_betting_profiles
    for d in defenders_list:
        if isinstance(d, dict):
            name = d.get('player', d.get('name', 'Unknown'))
            if not any(x.get('name') == name for x in all_defenders):
                all_defenders.append({
                    'name': name,
                    'position': d.get('position', 'CB'),
                    'primary_role': d.get('primary_role', 'CENTRAL'),
                    'sub_role': d.get('sub_role', 'N/A'),
                    'minutes': d.get('minutes', 0)
                })
    
    all_defenders = sorted(all_defenders, key=lambda x: -(x.get('minutes') or 0))
    starters = all_defenders[:4]
    
    return {
        'starters': starters,
        'all': all_defenders[:8],
        'line_profile': {
            'height': dl.get('line_height', 'MEDIUM'),
            'disciplinary_risk': defenders_from_dl.get('disciplinary_risk', 'MODERATE') if isinstance(defenders_from_dl, dict) else 'MODERATE',
            'impact_delta': defenders_from_dl.get('defender_impact_delta', 0) if isinstance(defenders_from_dl, dict) else 0
        },
        'resistance': dl.get('resistance', {})
    }


def extract_midfielders_dna(midfielders_list: List) -> Dict:
    all_mids = []
    
    for m in midfielders_list:
        if isinstance(m, dict):
            all_mids.append({
                'name': m.get('player', m.get('name', 'Unknown')),
                'primary_role': m.get('primary_role', 'BOX_TO_BOX'),
                'sub_role': m.get('sub_role', 'N/A'),
                'minutes': m.get('minutes', 0),
                'xA_per_90': m.get('xA_per_90', 0) or 0,
                'progressive_passes': m.get('progressive_passes', 0),
                'tackles': m.get('tackles', 0)
            })
    
    all_mids = sorted(all_mids, key=lambda x: -(x.get('minutes') or 0))
    starters = all_mids[:3]
    
    return {
        'starters': starters,
        'all': all_mids[:6],
        'profile': {
            'creativity': sum(m.get('xA_per_90', 0) for m in starters),
            'defensive_work': sum(m.get('tackles', 0) for m in starters)
        }
    }


def extract_attackers_dna(players_list: List, attackers_list: List, team_name: str) -> Dict:
    all_attackers = []
    
    for p in players_list:
        goals = p.get('goals', 0) or 0
        assists = p.get('assists', 0) or 0
        name = p.get('player_name', p.get('player', 'Unknown'))
        if goals > 0 or assists > 0:
            all_attackers.append({
                'name': name,
                'goals': goals,
                'assists': assists,
                'contributions': goals + assists,
                'xG': p.get('xG', 0) or 0,
                'xA': p.get('xA', 0) or 0,
                'shots': p.get('shots', 0)
            })
    
    for a in attackers_list:
        name = a.get('player', 'Unknown')
        if not any(x['name'] == name for x in all_attackers):
            goals = a.get('goals', 0) or 0
            assists = a.get('assists', 0) or 0
            all_attackers.append({
                'name': name,
                'goals': goals,
                'assists': assists,
                'contributions': goals + assists,
                'xG': a.get('xG', 0) or 0,
                'tier': a.get('tier', 'N/A')
            })
    
    all_attackers = sorted(all_attackers, key=lambda x: -x.get('contributions', 0))
    
    mvp = all_attackers[0] if all_attackers else {'name': 'Unknown', 'goals': 0, 'assists': 0}
    total_goals = sum(a.get('goals', 0) for a in all_attackers)
    mvp_dependency = mvp.get('goals', 0) / max(1, total_goals)
    
    top3 = all_attackers[:3]
    top3_goals = sum(a.get('goals', 0) for a in top3)
    concentration = top3_goals / max(1, total_goals)
    
    return {
        'mvp': {
            'name': mvp.get('name', 'Unknown'),
            'goals': mvp.get('goals', 0),
            'assists': mvp.get('assists', 0),
            'xG': mvp.get('xG', 0),
            'dependency': round(mvp_dependency, 2)
        },
        'top_scorers': all_attackers[:5],
        'total_goals': total_goals,
        'concentration_index': round(concentration, 2),
        'unique_scorers': len([a for a in all_attackers if a.get('goals', 0) > 0]),
        'dependency_profile': 'MVP_DEPENDENT' if mvp_dependency > 0.35 else 'BALANCED' if mvp_dependency > 0.2 else 'COLLECTIVE'
    }


def extract_timing_dna(team_data: Dict) -> Dict:
    dl = team_data.get('defensive_line', {})
    temporal = dl.get('temporal', {})
    
    xga_by_period = temporal.get('xga_by_period', {})
    
    first_half = sum(xga_by_period.get(p, 0) for p in ['0-15', '16-30', '31-45'])
    second_half = sum(xga_by_period.get(p, 0) for p in ['46-60', '61-75', '76-90'])
    
    diesel_factor = second_half / max(0.1, first_half) if first_half > 0 else 1.0
    
    if diesel_factor > 1.3:
        timing_profile = 'DIESEL'
    elif diesel_factor < 0.7:
        timing_profile = 'FAST_STARTER'
    else:
        timing_profile = temporal.get('timing_profile', 'BALANCED')
    
    peak_period = 'N/A'
    if xga_by_period:
        peak_period = max(xga_by_period.items(), key=lambda x: x[1])[0]
    
    return {
        'profile': timing_profile,
        'diesel_factor': round(diesel_factor, 2),
        'first_half_pct': round(first_half / max(0.1, first_half + second_half) * 100, 1),
        'second_half_pct': round(second_half / max(0.1, first_half + second_half) * 100, 1),
        'xga_by_period': xga_by_period,
        'vulnerable_periods': [temporal.get('most_vulnerable_period', 'N/A')],
        'strong_periods': [temporal.get('least_vulnerable_period', 'N/A')],
        'peak_period': peak_period
    }


def extract_gamestate_dna(team_data: Dict) -> Dict:
    dl = team_data.get('defensive_line', {})
    gs = dl.get('gamestate', {})
    
    return {
        'behavior': gs.get('gamestate_profile', 'NEUTRAL'),
        'comeback_rate': 0.0,
        'collapse_rate': 0.0,
        'insights': gs.get('gamestate_insights', [])
    }


def extract_setpieces_dna(team_data: Dict) -> Dict:
    dl = team_data.get('defensive_line', {})
    sp = dl.get('set_pieces', {})
    
    return {
        'offensive_threat': 0,
        'defensive_vulnerability': (sp.get('set_piece_pct', 0) or 0) / 100,
        'aerial_threat': sp.get('aerial_threat_level', 'MEDIUM'),
        'profile': sp.get('set_piece_profile', 'AVERAGE')
    }


def extract_zones_dna(team_data: Dict) -> Dict:
    dl = team_data.get('defensive_line', {})
    zones = dl.get('zones', {})
    
    return {
        'vulnerability_zone': zones.get('most_vulnerable_zone', 'NONE'),
        'zone_profile': zones.get('zone_profile', 'BALANCED'),
        'penalty_area_vulnerable': 'penalty' in str(zones.get('most_vulnerable_zone', '')).lower(),
        'behind_line_vulnerable': 'behind' in str(zones.get('most_vulnerable_zone', '')).lower()
    }


def extract_friction_dna(team_data: Dict) -> Dict:
    tactical = team_data.get('tactical', {})
    fm = tactical.get('friction_multipliers', {})
    
    return {
        'multipliers': fm,
        'vs_gegenpress': fm.get('vs_gegenpress', 1.0),
        'vs_possession': fm.get('vs_possession', 1.0),
        'vs_low_block': fm.get('vs_low_block', 1.0)
    }


def extract_exploit_dna(team_data: Dict) -> Dict:
    exploit = team_data.get('exploit', {})
    
    return {
        'vulnerabilities': exploit.get('vulnerabilities', [])[:5],
        'exploit_paths': exploit.get('exploit_paths', [])[:3]
    }


def extract_context_dna(team_data: Dict) -> Dict:
    context = team_data.get('context', {})
    ctx_dna = context.get('context_dna', {})
    
    formations = ctx_dna.get('formation', {})
    main_formation = '4-3-3'
    if isinstance(formations, dict) and formations:
        main_formation = max(formations.items(), key=lambda x: x[1].get('goals', 0) if isinstance(x[1], dict) else 0)[0]
    
    return {
        'league': context.get('league', 'Unknown'),
        'formation': main_formation,
        'record': context.get('record', {}),
        'momentum': context.get('momentum_dna', {})
    }


def extract_betting_dna(team_data: Dict) -> Dict:
    betting = team_data.get('betting', {})
    dl = team_data.get('defensive_line', {})
    recs = dl.get('recommendations', {})
    
    return {
        'best_markets': betting.get('best_markets', []),
        'avoid_markets': [],
        'timing_plays': recs.get('timing_plays', []),
        'insights': betting.get('betting_insights', {})
    }


def generate_unique_fingerprint(team_name: str, dna: Dict) -> Dict:
    tactical = dna.get('tactical', {})
    gk = dna.get('goalkeeper', {})
    mvp = dna.get('attackers', {}).get('mvp', {})
    timing = dna.get('timing', {})
    
    parts = [team_name[:3].upper()]
    
    profile = tactical.get('profile', 'UNK')[:4].upper()
    parts.append(profile)
    
    ppda = tactical.get('ppda')
    if ppda:
        parts.append(f"P{ppda:.1f}")
    
    poss = tactical.get('possession', 0)
    parts.append(f"PS{int(poss)}")
    
    diesel = timing.get('diesel_factor', 1.0)
    parts.append(f"D{diesel:.2f}")
    
    mvp_name = mvp.get('name', 'UNK')[:3].upper()
    mvp_goals = mvp.get('goals', 0)
    parts.append(f"M-{mvp_name}{mvp_goals}")
    
    gk_name = gk.get('name', 'UNK')[:3].upper()
    gk_sr = int(gk.get('save_rate', 0))
    parts.append(f"G-{gk_name}{gk_sr}")
    
    fingerprint_text = "_".join(parts)
    
    metrics = [str(ppda or 0), str(poss), str(diesel), str(mvp_goals), gk.get('name', '')]
    hash_input = "|".join(metrics)
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    fingerprint_code = f"{team_name}_{hash_value}"
    
    return {
        'text': fingerprint_text,
        'code': fingerprint_code,
        'hash': hash_value
    }


def generate_exploitable_markets(team_name: str, dna: Dict) -> Dict:
    tactical = dna.get('tactical', {})
    timing = dna.get('timing', {})
    gk = dna.get('goalkeeper', {})
    attackers = dna.get('attackers', {})
    sp = dna.get('set_pieces', {})
    
    markets_for = []
    markets_against = []
    markets_avoid = []
    
    # Timing-based
    diesel = timing.get('diesel_factor', 1.0)
    if diesel > 1.3:
        markets_for.append({'market': '2H Over 0.5', 'edge': 0.12, 'reason': f"DIESEL (factor: {diesel:.2f})"})
        markets_avoid.append({'market': '1H Over 1.5', 'reason': 'DIESEL = slow starter'})
    elif diesel < 0.7:
        markets_for.append({'market': '1H Over 0.5', 'edge': 0.10, 'reason': f"FAST_STARTER"})
    
    # Tactical-based
    profile = tactical.get('profile', 'UNKNOWN')
    ppda = tactical.get('ppda')
    
    if profile == 'GEGENPRESS' and ppda and ppda < 10:
        markets_for.append({'market': f'{team_name} Win @ Home', 'edge': 0.10, 'reason': f"GEGENPRESS (PPDA: {ppda:.1f})"})
    
    if profile == 'LOW_BLOCK':
        markets_for.append({'market': 'Under 2.5', 'edge': 0.09, 'reason': 'LOW_BLOCK = matchs fermés'})
    
    # GK-based
    gk_status = gk.get('status', 'UNKNOWN')
    if gk_status == 'ELITE':
        markets_for.append({'market': f'{team_name} CS @ Home', 'edge': 0.09, 'reason': f"Elite GK"})
    elif gk_status == 'LEAKY':
        markets_against.append({'market': 'BTTS', 'edge': 0.10, 'reason': f"Leaky GK"})
    
    # MVP-based
    mvp = attackers.get('mvp', {})
    mvp_dep = mvp.get('dependency', 0)
    if mvp_dep > 0.35:
        markets_for.append({'market': f"{mvp.get('name', 'MVP')} Scorer", 'edge': 0.08, 'reason': f"MVP dependency: {mvp_dep:.0%}"})
    
    # Set pieces
    sp_vuln = sp.get('defensive_vulnerability', 0)
    if sp_vuln > 0.25:
        markets_against.append({'market': 'Set Piece Goal', 'edge': 0.08, 'reason': f"SP vulnerability: {sp_vuln:.0%}"})
    
    return {
        'for_team': markets_for[:8],
        'against_team': markets_against[:6],
        'avoid': markets_avoid[:5]
    }


def generate_narrative_text(team_name: str, dna: Dict) -> str:
    tactical = dna.get('tactical', {})
    timing = dna.get('timing', {})
    gk = dna.get('goalkeeper', {})
    attackers = dna.get('attackers', {})
    context = dna.get('context', {})
    
    parts = []
    
    profile = tactical.get('profile', 'UNKNOWN')
    ppda = tactical.get('ppda')
    poss = tactical.get('possession', 0)
    
    intro = f"{team_name} ({context.get('league', 'Unknown')}) - {profile}"
    if ppda:
        intro += f" (PPDA: {ppda:.1f})"
    if poss > 0:
        intro += f", {poss:.1f}% poss"
    parts.append(intro)
    
    mvp = attackers.get('mvp', {})
    if mvp.get('name') and mvp.get('name') != 'Unknown':
        parts.append(f"MVP: {mvp['name']} ({mvp.get('goals', 0)}G, {mvp.get('dependency', 0):.0%} dep)")
    
    if gk.get('name') and gk.get('name') != 'Unknown':
        parts.append(f"GK: {gk['name']} ({gk.get('status', 'N/A')})")
    
    timing_profile = timing.get('profile', 'BALANCED')
    if timing_profile != 'BALANCED':
        parts.append(f"Timing: {timing_profile}")
    
    return " | ".join(parts)


def create_complete_profile(team_name: str, data: Dict) -> Dict:
    team_data = data['team_dna'].get(team_name, {})
    
    dna = {
        'tactical': extract_tactical_dna(team_data, data['ppda'], data.get('tactical_ml', {}), team_name),
        'goalkeeper': extract_goalkeeper_dna(team_data, data.get('goalkeeper_dna', {}), team_name),
        'defenders': extract_defenders_dna(team_data, data['defenders_by_team'].get(team_name, [])),
        'midfielders': extract_midfielders_dna(data['midfielders_by_team'].get(team_name, [])),
        'attackers': extract_attackers_dna(
            data['players_by_team'].get(team_name, []),
            data['attackers_by_team'].get(team_name, []),
            team_name
        ),
        'timing': extract_timing_dna(team_data),
        'gamestate': extract_gamestate_dna(team_data),
        'set_pieces': extract_setpieces_dna(team_data),
        'zones': extract_zones_dna(team_data),
        'friction': extract_friction_dna(team_data),
        'exploit': extract_exploit_dna(team_data),
        'context': extract_context_dna(team_data),
        'betting': extract_betting_dna(team_data)
    }
    
    fingerprint = generate_unique_fingerprint(team_name, dna)
    markets = generate_exploitable_markets(team_name, dna)
    narrative = generate_narrative_text(team_name, dna)
    
    return {
        'team': team_name,
        'fingerprint': fingerprint,
        'dna': dna,
        'markets': markets,
        'narrative': narrative,
        'generated_at': datetime.now().isoformat(),
        'version': '3.0'
    }


def main():
    data = load_all_data()
    
    print("\n" + "=" * 80)
    print("CRÉATION DES PROFILS NARRATIFS V3.0")
    print("=" * 80)
    
    profiles = {}
    fingerprints = set()
    
    for team_name in data['team_dna'].keys():
        try:
            profile = create_complete_profile(team_name, data)
            profiles[team_name] = profile
            
            fp_code = profile['fingerprint']['code']
            if fp_code in fingerprints:
                print(f"  ⚠️ Doublon: {team_name}")
            fingerprints.add(fp_code)
            
        except Exception as e:
            print(f"  ❌ Erreur {team_name}: {e}")
    
    print(f"\n✅ {len(profiles)} profils créés")
    print(f"✅ {len(fingerprints)} fingerprints uniques ({len(fingerprints)/max(1,len(profiles))*100:.0f}%)")
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Sauvegardé: {OUTPUT_FILE}")
    
    # Exemples
    print("\n" + "=" * 80)
    print("EXEMPLES DE PROFILS V3.0")
    print("=" * 80)
    
    for team in ['Liverpool', 'Manchester City', 'Arsenal', 'West Ham', 'Brighton']:
        if team in profiles:
            p = profiles[team]
            fp = p['fingerprint']
            dna = p['dna']
            
            print(f"\n{'─' * 70}")
            print(f"🏟️  {team}")
            print(f"{'─' * 70}")
            print(f"📝 Fingerprint: {fp['text']}")
            print(f"🔑 Code: {fp['code']}")
            
            tac = dna['tactical']
            print(f"\n⚽ TACTICAL: {tac['profile']} | PPDA: {tac['ppda']} | Poss: {tac['possession']}%")
            
            att = dna['attackers']
            print(f"\n⭐ MVP: {att['mvp']['name']} ({att['mvp']['goals']}G, {att['mvp']['dependency']:.0%} dep)")
            print(f"   Dependency: {att['dependency_profile']}")
            print(f"   Top scorers:")
            for s in att['top_scorers'][:3]:
                print(f"     └─ {s['name']}: {s['goals']}G + {s.get('assists', 0)}A")
            
            gk = dna['goalkeeper']
            print(f"\n🧤 GK: {gk['name']} - {gk['status']} ({gk['save_rate']:.0f}% SR)")
            
            defs = dna['defenders']
            print(f"\n🛡️ DÉFENSE:")
            for d in defs['starters'][:4]:
                print(f"     └─ {d['name']}: {d['primary_role']}/{d['sub_role']}")
            
            mids = dna['midfielders']
            if mids['starters']:
                print(f"\n🎯 MILIEU:")
                for m in mids['starters'][:3]:
                    print(f"     └─ {m['name']}: {m['primary_role']}/{m['sub_role']}")
            
            tim = dna['timing']
            print(f"\n⏱️ TIMING: {tim['profile']} (diesel: {tim['diesel_factor']:.2f})")
            
            markets = p['markets']
            print(f"\n💰 MARCHÉS:")
            for m in markets['for_team'][:3]:
                print(f"   ✅ {m['market']} (edge: {m.get('edge', 0):.0%})")
            for m in markets['against_team'][:2]:
                print(f"   ⚔️ {m['market']} (edge: {m.get('edge', 0):.0%})")
            
            print(f"\n📝 {p['narrative']}")
    
    print("\n" + "=" * 80)
    print("✅ NARRATIVE DNA V3.0 COMPLET!")
    print("=" * 80)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 DEFENDER DNA INSTITUTIONAL V5.0 - NIVEAU HEDGE FUND                      ║
║                                                                              ║
║  UPGRADE MAJEUR: Labels CONTEXTUELS et QUANTIFIÉS                            ║
║                                                                              ║
║  AVANT (Générique):     APRÈS (Institutionnel):                              ║
║  ├── "Passoire"      →  "Concède 1.42 buts/90 | -0.61 impact | Edge GO +4.2%"║
║  ├── "Troué"         →  "CS Rate 4.6% (P5 ligue) | 87% matchs avec but"      ║
║  ├── "Omniprésent"   →  "xGChain 0.79/90 (P98) | Impliqué 73% actions off"   ║
║  └── "Rugueux"       →  "0.31 cartons/90 (P78) | 23% risque rouge"           ║
║                                                                              ║
║  NOUVELLES MÉTRIQUES:                                                        ║
║  ├── Percentile EXACT dans la ligue                                          ║
║  ├── Comparaison vs TOP 10% / BOTTOM 10%                                     ║
║  ├── Edge calculé pour chaque marché                                         ║
║  ├── Contexte matchup (vs rapides, vs aériens, etc.)                         ║
║  └── Signature narrative unique                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore

DATA_DIR = Path('/home/Mon_ps/data/defender_dna')

# Charger les données
with open(DATA_DIR / 'defender_dna_unique_v4.json', 'r') as f:
    defenders = json.load(f)

print("=" * 80)
print("🧬 DEFENDER DNA INSTITUTIONAL V5.0")
print("   Niveau Hedge Fund - Labels Contextuels & Quantifiés")
print("=" * 80)

# 1. Filtrer les qualifiés
qualified = [d for d in defenders if d.get('dna')]
print(f"\n📊 {len(qualified)} défenseurs qualifiés")

# 2. Calculer les statistiques de référence par ligue
print(f"\n📊 Calcul des benchmarks par ligue...")

leagues = defaultdict(list)
for d in qualified:
    leagues[d.get('league', 'Unknown')].append(d)

league_benchmarks = {}
for league, players in leagues.items():
    league_benchmarks[league] = {
        'impact_p10': np.percentile([p.get('impact_goals_conceded', 0) for p in players], 10),
        'impact_p90': np.percentile([p.get('impact_goals_conceded', 0) for p in players], 90),
        'impact_median': np.median([p.get('impact_goals_conceded', 0) for p in players]),
        'cs_p10': np.percentile([p.get('clean_sheet_rate_with', 0) for p in players], 10),
        'cs_p90': np.percentile([p.get('clean_sheet_rate_with', 0) for p in players], 90),
        'xgchain_p90': np.percentile([p.get('xGChain_90', 0) for p in players], 90),
        'xa_p90': np.percentile([p.get('xA_90', 0) for p in players], 90),
        'cards_p90': np.percentile([p.get('cards_90', 0) for p in players], 90),
        'count': len(players)
    }
    print(f"   {league}: {len(players)} joueurs")

# 3. Fonction de génération du profil institutionnel
def generate_institutional_profile(defender: dict) -> dict:
    """Génère un profil institutionnel avec labels quantifiés"""
    
    dna = defender.get('dna', {})
    dims = dna.get('dimensions', {})
    raw = dna.get('raw_values', {})
    league = defender.get('league', 'Unknown')
    bench = league_benchmarks.get(league, {})
    
    # === MÉTRIQUES BRUTES CONTEXTUALISÉES ===
    
    # Impact défensif
    impact = raw.get('impact_goals_conceded', 0)
    impact_pct = dims.get('SHIELD', 50)
    
    # Clean sheet
    cs_rate = raw.get('clean_sheet_rate', 0)
    cs_pct = dims.get('FORTRESS', 50)
    
    # Offensive
    xgchain = raw.get('xGChain_90', 0)
    chain_pct = dims.get('CHAIN', 50)
    xa = raw.get('xA_90', 0)
    creator_pct = dims.get('CREATOR', 50)
    xgbuildup = raw.get('xGBuildup_90', 0)
    builder_pct = dims.get('BUILDER', 50)
    
    # Discipline
    cards = raw.get('cards_90', 0)
    discipline_pct = dims.get('DISCIPLINE', 50)
    
    # === LABELS INSTITUTIONNELS ===
    
    def get_institutional_label(dimension: str, percentile: float, raw_value: float) -> dict:
        """Génère un label institutionnel avec contexte quantifié"""
        
        # Position dans la distribution
        if percentile >= 90:
            tier = 'ELITE'
            tier_desc = 'Top 10%'
        elif percentile >= 75:
            tier = 'ABOVE_AVG'
            tier_desc = 'Top 25%'
        elif percentile >= 50:
            tier = 'AVERAGE'
            tier_desc = 'Top 50%'
        elif percentile >= 25:
            tier = 'BELOW_AVG'
            tier_desc = 'Bottom 25%'
        else:
            tier = 'WEAK'
            tier_desc = 'Bottom 10%'
        
        # Labels spécifiques par dimension
        labels = {
            'SHIELD': {
                'ELITE': f"Impact +{raw_value:.2f} (P{percentile:.0f}) | Stabilisateur d'équipe",
                'ABOVE_AVG': f"Impact +{raw_value:.2f} (P{percentile:.0f}) | Contribution défensive positive",
                'AVERAGE': f"Impact {raw_value:+.2f} (P{percentile:.0f}) | Contribution neutre",
                'BELOW_AVG': f"Impact {raw_value:+.2f} (P{percentile:.0f}) | Légère fragilité",
                'WEAK': f"Impact {raw_value:+.2f} (P{percentile:.0f}) | Facteur de vulnérabilité"
            },
            'FORTRESS': {
                'ELITE': f"CS {raw_value:.0f}% (P{percentile:.0f}) | Gardien de clean sheets",
                'ABOVE_AVG': f"CS {raw_value:.0f}% (P{percentile:.0f}) | Fiabilité défensive",
                'AVERAGE': f"CS {raw_value:.0f}% (P{percentile:.0f}) | Solidité standard",
                'BELOW_AVG': f"CS {raw_value:.0f}% (P{percentile:.0f}) | Perméabilité modérée",
                'WEAK': f"CS {raw_value:.0f}% (P{percentile:.0f}) | Ligne de défense poreuse"
            },
            'CHAIN': {
                'ELITE': f"xGChain {raw_value:.3f}/90 (P{percentile:.0f}) | Catalyseur offensif",
                'ABOVE_AVG': f"xGChain {raw_value:.3f}/90 (P{percentile:.0f}) | Implication offensive notable",
                'AVERAGE': f"xGChain {raw_value:.3f}/90 (P{percentile:.0f}) | Présence offensive standard",
                'BELOW_AVG': f"xGChain {raw_value:.3f}/90 (P{percentile:.0f}) | Contribution offensive limitée",
                'WEAK': f"xGChain {raw_value:.3f}/90 (P{percentile:.0f}) | Absent des circuits offensifs"
            },
            'BUILDER': {
                'ELITE': f"xGBuildup {raw_value:.3f}/90 (P{percentile:.0f}) | Architecte du jeu construit",
                'ABOVE_AVG': f"xGBuildup {raw_value:.3f}/90 (P{percentile:.0f}) | Relanceur efficace",
                'AVERAGE': f"xGBuildup {raw_value:.3f}/90 (P{percentile:.0f}) | Construction standard",
                'BELOW_AVG': f"xGBuildup {raw_value:.3f}/90 (P{percentile:.0f}) | Jeu direct privilégié",
                'WEAK': f"xGBuildup {raw_value:.3f}/90 (P{percentile:.0f}) | Dégagement systématique"
            },
            'CREATOR': {
                'ELITE': f"xA {raw_value:.3f}/90 (P{percentile:.0f}) | Menace de passe décisive",
                'ABOVE_AVG': f"xA {raw_value:.3f}/90 (P{percentile:.0f}) | Créativité notable",
                'AVERAGE': f"xA {raw_value:.3f}/90 (P{percentile:.0f}) | Création occasionnelle",
                'BELOW_AVG': f"xA {raw_value:.3f}/90 (P{percentile:.0f}) | Création rare",
                'WEAK': f"xA {raw_value:.3f}/90 (P{percentile:.0f}) | Aucune menace créative"
            },
            'DISCIPLINE': {
                'ELITE': f"Cartons {raw_value:.2f}/90 (P{percentile:.0f}) | Discipline exemplaire",
                'ABOVE_AVG': f"Cartons {raw_value:.2f}/90 (P{percentile:.0f}) | Jeu propre",
                'AVERAGE': f"Cartons {raw_value:.2f}/90 (P{percentile:.0f}) | Discipline standard",
                'BELOW_AVG': f"Cartons {raw_value:.2f}/90 (P{percentile:.0f}) | Tendance aux fautes",
                'WEAK': f"Cartons {raw_value:.2f}/90 (P{percentile:.0f}) | Risque disciplinaire élevé"
            },
            'RELIABILITY': {
                'ELITE': f"Temps {int(defender.get('time', 0))}min (P{percentile:.0f}) | Indispensable",
                'ABOVE_AVG': f"Temps {int(defender.get('time', 0))}min (P{percentile:.0f}) | Titulaire régulier",
                'AVERAGE': f"Temps {int(defender.get('time', 0))}min (P{percentile:.0f}) | Rotation fréquente",
                'BELOW_AVG': f"Temps {int(defender.get('time', 0))}min (P{percentile:.0f}) | Option de rotation",
                'WEAK': f"Temps {int(defender.get('time', 0))}min (P{percentile:.0f}) | Temps de jeu marginal"
            },
            'WINNER': {
                'ELITE': f"Win Impact +{defender.get('impact_wins', 0):.1f}% (P{percentile:.0f}) | Facteur de victoire",
                'ABOVE_AVG': f"Win Impact +{defender.get('impact_wins', 0):.1f}% (P{percentile:.0f}) | Contribution positive",
                'AVERAGE': f"Win Impact {defender.get('impact_wins', 0):+.1f}% (P{percentile:.0f}) | Impact neutre",
                'BELOW_AVG': f"Win Impact {defender.get('impact_wins', 0):+.1f}% (P{percentile:.0f}) | Impact légèrement négatif",
                'WEAK': f"Win Impact {defender.get('impact_wins', 0):+.1f}% (P{percentile:.0f}) | Corrélation avec défaites"
            }
        }
        
        return {
            'tier': tier,
            'tier_desc': tier_desc,
            'percentile': percentile,
            'raw_value': raw_value,
            'label': labels.get(dimension, {}).get(tier, f"P{percentile:.0f}"),
            'is_strength': percentile >= 70,
            'is_weakness': percentile <= 30
        }
    
    # Générer les labels pour chaque dimension
    dimensional_analysis = {}
    for dim in ['SHIELD', 'FORTRESS', 'WINNER', 'CHAIN', 'BUILDER', 'CREATOR', 'DISCIPLINE', 'RELIABILITY']:
        pct = dims.get(dim, 50)
        
        if dim == 'SHIELD':
            raw_val = impact
        elif dim == 'FORTRESS':
            raw_val = cs_rate
        elif dim == 'CHAIN':
            raw_val = xgchain
        elif dim == 'BUILDER':
            raw_val = xgbuildup
        elif dim == 'CREATOR':
            raw_val = xa
        elif dim == 'DISCIPLINE':
            raw_val = cards
        elif dim == 'RELIABILITY':
            raw_val = defender.get('time', 0)
        else:
            raw_val = defender.get('impact_wins', 0)
        
        dimensional_analysis[dim] = get_institutional_label(dim, pct, raw_val)
    
    # === PROFIL DÉFENSIF CONTEXTUEL ===
    
    defensive_profile = {
        'overall_rating': dna.get('scores', {}).get('defensive', 50),
        'tier': 'ELITE' if dna.get('scores', {}).get('defensive', 50) >= 70 else 
                'SOLID' if dna.get('scores', {}).get('defensive', 50) >= 55 else
                'AVERAGE' if dna.get('scores', {}).get('defensive', 50) >= 40 else
                'WEAK' if dna.get('scores', {}).get('defensive', 50) >= 25 else 'LIABILITY',
        'key_metrics': {
            'impact': dimensional_analysis['SHIELD']['label'],
            'clean_sheets': dimensional_analysis['FORTRESS']['label'],
            'win_correlation': dimensional_analysis['WINNER']['label']
        }
    }
    
    # === PROFIL OFFENSIF CONTEXTUEL ===
    
    offensive_profile = {
        'overall_rating': dna.get('scores', {}).get('offensive', 50),
        'tier': 'CREATOR' if dna.get('scores', {}).get('offensive', 50) >= 70 else
                'CONTRIBUTOR' if dna.get('scores', {}).get('offensive', 50) >= 55 else
                'NEUTRAL' if dna.get('scores', {}).get('offensive', 50) >= 40 else
                'LIMITED' if dna.get('scores', {}).get('offensive', 50) >= 25 else 'NULL',
        'key_metrics': {
            'involvement': dimensional_analysis['CHAIN']['label'],
            'buildup': dimensional_analysis['BUILDER']['label'],
            'creation': dimensional_analysis['CREATOR']['label']
        }
    }
    
    # === PROFIL DE RISQUE CONTEXTUEL ===
    
    risk_profile = {
        'discipline': dimensional_analysis['DISCIPLINE']['label'],
        'availability': dimensional_analysis['RELIABILITY']['label'],
        'card_probability': round(min(cards * 100, 100), 1),  # % chance d'un carton par match
        'is_card_risk': cards >= 0.25
    }
    
    # === EDGE CALCULATIONS (BETTING) ===
    
    edges = {}
    
    # Goals Over edge
    if impact_pct <= 30:
        go_edge = round(4.0 + (30 - impact_pct) * 0.1, 1)
        edges['goals_over'] = {
            'edge': go_edge,
            'confidence': 'HIGH' if impact_pct <= 20 else 'MEDIUM',
            'reason': f"Impact défensif P{impact_pct:.0f} - Facteur de vulnérabilité"
        }
    
    if cs_pct <= 25:
        btts_edge = round(3.5 + (25 - cs_pct) * 0.12, 1)
        edges['btts_yes'] = {
            'edge': btts_edge,
            'confidence': 'HIGH' if cs_pct <= 15 else 'MEDIUM',
            'reason': f"CS Rate P{cs_pct:.0f} - Ligne poreuse"
        }
    
    # Cards Over edge
    if discipline_pct <= 25:
        cards_edge = round(3.0 + (25 - discipline_pct) * 0.15, 1)
        edges['cards_over'] = {
            'edge': cards_edge,
            'confidence': 'HIGH' if discipline_pct <= 15 else 'MEDIUM',
            'reason': f"Discipline P{discipline_pct:.0f} - {cards:.2f} cartons/90"
        }
    
    # Anytime Assist edge (pour latéraux offensifs)
    if creator_pct >= 75:
        assist_edge = round(2.5 + (creator_pct - 75) * 0.1, 1)
        edges['anytime_assist'] = {
            'edge': assist_edge,
            'confidence': 'MEDIUM',
            'reason': f"xA P{creator_pct:.0f} - {xa:.3f}/90"
        }
    
    # === SIGNATURE NARRATIVE UNIQUE ===
    
    # Construire la narrative basée sur les données réelles
    narrative_parts = []
    
    # Partie défensive
    def_tier = defensive_profile['tier']
    if def_tier == 'ELITE':
        narrative_parts.append(f"Pilier défensif (Impact +{impact:.2f})")
    elif def_tier == 'SOLID':
        narrative_parts.append(f"Défenseur fiable (P{impact_pct:.0f})")
    elif def_tier == 'WEAK':
        narrative_parts.append(f"Fragilité défensive (Impact {impact:+.2f})")
    elif def_tier == 'LIABILITY':
        narrative_parts.append(f"Point faible identifié (P{impact_pct:.0f})")
    
    # Partie offensive si notable
    off_tier = offensive_profile['tier']
    if off_tier in ['CREATOR', 'CONTRIBUTOR']:
        if creator_pct >= 70:
            narrative_parts.append(f"Menace créative ({xa:.3f} xA/90)")
        elif chain_pct >= 70:
            narrative_parts.append(f"Circuit offensif ({xgchain:.3f} xGC/90)")
    
    # Partie risque si notable
    if risk_profile['is_card_risk']:
        narrative_parts.append(f"Risque cartons ({cards:.2f}/90)")
    
    # Partie clean sheet si extrême
    if cs_pct >= 80:
        narrative_parts.append(f"Gardien CS ({cs_rate:.0f}%)")
    elif cs_pct <= 20:
        narrative_parts.append(f"Ligne poreuse ({cs_rate:.0f}% CS)")
    
    signature_narrative = ' | '.join(narrative_parts) if narrative_parts else f"Profil standard (P{dna.get('scores', {}).get('overall', 50):.0f})"
    
    # === FINGERPRINT INSTITUTIONNEL ===
    
    # Format: TEAM-NAME-DEF[score]-OFF[score]-RISK[cards]-EDGE[markets]
    edge_codes = []
    if 'goals_over' in edges:
        edge_codes.append(f"GO+{edges['goals_over']['edge']}")
    if 'btts_yes' in edges:
        edge_codes.append(f"BT+{edges['btts_yes']['edge']}")
    if 'cards_over' in edges:
        edge_codes.append(f"CO+{edges['cards_over']['edge']}")
    if 'anytime_assist' in edges:
        edge_codes.append(f"AA+{edges['anytime_assist']['edge']}")
    
    fingerprint = f"DEF{int(dna.get('scores', {}).get('defensive', 50))}-OFF{int(dna.get('scores', {}).get('offensive', 50))}-{','.join(edge_codes) if edge_codes else 'NEUTRAL'}"
    
    # === MATCHUP INSIGHTS ===
    
    matchup_insights = {
        'vulnerable_to': [],
        'strong_against': []
    }
    
    if impact_pct <= 35:
        matchup_insights['vulnerable_to'].append('Attaquants cliniques')
    if cs_pct <= 30:
        matchup_insights['vulnerable_to'].append('Équipes à fort xG')
    if chain_pct <= 25:
        matchup_insights['strong_against'].append('Équipes en bloc bas (pas besoin de contribution offensive)')
    if builder_pct >= 75:
        matchup_insights['strong_against'].append('Équipes qui pressent haut (capacité à jouer sous pression)')
    if discipline_pct <= 25:
        matchup_insights['vulnerable_to'].append('Attaquants techniques (provoquent les fautes)')
    
    return {
        'dimensional_analysis': dimensional_analysis,
        'defensive_profile': defensive_profile,
        'offensive_profile': offensive_profile,
        'risk_profile': risk_profile,
        'edges': edges,
        'signature_narrative': signature_narrative,
        'fingerprint_institutional': fingerprint,
        'matchup_insights': matchup_insights,
        'league_context': {
            'league': league,
            'vs_league_avg': {
                'impact_vs_median': round(impact - bench.get('impact_median', 0), 2),
                'in_top_quartile_defensive': impact_pct >= 75,
                'in_bottom_quartile_defensive': impact_pct <= 25
            }
        }
    }

# 4. Appliquer à tous les défenseurs
print(f"\n🔧 Génération des profils institutionnels...")

for d in defenders:
    if d.get('dna'):
        institutional = generate_institutional_profile(d)
        d['institutional'] = institutional

# 5. Sauvegarder
print(f"\n💾 SAUVEGARDE...")

with open(DATA_DIR / 'defender_dna_institutional_v5.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ defender_dna_institutional_v5.json")

# 6. Reconstruire les lignes défensives avec profils institutionnels
print(f"\n🔧 Reconstruction des lignes défensives institutionnelles...")

teams = defaultdict(list)
for d in defenders:
    if d.get('institutional'):
        teams[d.get('team')].append(d)

defensive_lines_v5 = {}

for team_name, team_defenders in teams.items():
    team_defenders.sort(key=lambda x: x.get('time', 0), reverse=True)
    starters = team_defenders[:4]
    
    # Collecter les edges
    all_edges = defaultdict(list)
    collective_weaknesses = []
    collective_strengths = []
    
    for d in starters:
        inst = d.get('institutional', {})
        
        # Edges
        for market, edge_data in inst.get('edges', {}).items():
            all_edges[market].append({
                'player': d['name'],
                'edge': edge_data['edge'],
                'reason': edge_data['reason']
            })
        
        # Faiblesses
        for dim, analysis in inst.get('dimensional_analysis', {}).items():
            if analysis.get('is_weakness'):
                collective_weaknesses.append({
                    'dimension': dim,
                    'player': d['name'],
                    'label': analysis['label'],
                    'percentile': analysis['percentile']
                })
        
        # Forces
        for dim, analysis in inst.get('dimensional_analysis', {}).items():
            if analysis.get('is_strength'):
                collective_strengths.append({
                    'dimension': dim,
                    'player': d['name'],
                    'label': analysis['label'],
                    'percentile': analysis['percentile']
                })
    
    # Agréger les edges par marché
    aggregated_edges = {}
    for market, player_edges in all_edges.items():
        avg_edge = np.mean([e['edge'] for e in player_edges])
        aggregated_edges[market] = {
            'avg_edge': round(avg_edge, 1),
            'count': len(player_edges),
            'players': [e['player'] for e in player_edges],
            'combined_edge': round(avg_edge + (len(player_edges) - 1) * 0.5, 1),  # Bonus si multiple
            'confidence': 'HIGH' if len(player_edges) >= 2 else 'MEDIUM'
        }
    
    # Compter les dimensions faibles récurrentes
    weakness_dims = defaultdict(int)
    for w in collective_weaknesses:
        weakness_dims[w['dimension']] += 1
    
    systemic_weaknesses = [dim for dim, count in weakness_dims.items() if count >= 2]
    
    line = {
        'team': team_name,
        'league': team_defenders[0].get('league', ''),
        
        'starters_institutional': [{
            'name': d['name'],
            'signature': d.get('institutional', {}).get('signature_narrative', ''),
            'fingerprint': d.get('institutional', {}).get('fingerprint_institutional', ''),
            'defensive_tier': d.get('institutional', {}).get('defensive_profile', {}).get('tier', ''),
            'offensive_tier': d.get('institutional', {}).get('offensive_profile', {}).get('tier', ''),
            'edges': list(d.get('institutional', {}).get('edges', {}).keys())
        } for d in starters],
        
        'collective_analysis': {
            'avg_defensive': round(np.mean([d.get('dna', {}).get('scores', {}).get('defensive', 50) for d in starters]), 1),
            'avg_offensive': round(np.mean([d.get('dna', {}).get('scores', {}).get('offensive', 50) for d in starters]), 1),
            'systemic_weaknesses': systemic_weaknesses,
            'weakness_details': collective_weaknesses[:6],
            'strength_details': collective_strengths[:6]
        },
        
        'betting_intel': {
            'edges': aggregated_edges,
            'primary_market': max(aggregated_edges.items(), key=lambda x: x[1]['combined_edge'])[0] if aggregated_edges else None,
            'total_edge_value': round(sum(e['combined_edge'] for e in aggregated_edges.values()), 1) if aggregated_edges else 0
        }
    }
    
    defensive_lines_v5[team_name] = line

with open(DATA_DIR / 'defensive_lines_institutional_v5.json', 'w') as f:
    json.dump(defensive_lines_v5, f, indent=2, ensure_ascii=False)
print(f"   ✅ defensive_lines_institutional_v5.json")

# 7. Rapports
print(f"\n" + "=" * 80)
print("📊 RAPPORT DEFENDER DNA INSTITUTIONAL V5.0")
print("=" * 80)

# Exemples de profils institutionnels
sample_players = ['Gabriel', 'Virgil van Dijk', 'Federico Dimarco', 'Toti', 'William Saliba']

for name in sample_players:
    player = next((d for d in defenders if name in d.get('name', '') and d.get('institutional')), None)
    if player:
        inst = player['institutional']
        dna = player['dna']
        
        print(f"\n{'─'*80}")
        print(f"👤 {player['name']} ({player['team']} - {player['league']})")
        print(f"{'─'*80}")
        
        print(f"\n📛 SIGNATURE: {inst['signature_narrative']}")
        print(f"🔑 FINGERPRINT: {inst['fingerprint_institutional']}")
        
        print(f"\n🛡️ PROFIL DÉFENSIF [{inst['defensive_profile']['tier']}]:")
        for key, val in inst['defensive_profile']['key_metrics'].items():
            print(f"   • {val}")
        
        print(f"\n⚔️ PROFIL OFFENSIF [{inst['offensive_profile']['tier']}]:")
        for key, val in inst['offensive_profile']['key_metrics'].items():
            print(f"   • {val}")
        
        print(f"\n⚠️ PROFIL RISQUE:")
        print(f"   • {inst['risk_profile']['discipline']}")
        print(f"   • {inst['risk_profile']['availability']}")
        if inst['risk_profile']['is_card_risk']:
            print(f"   • 🟨 Probabilité carton: {inst['risk_profile']['card_probability']:.0f}%/match")
        
        if inst['edges']:
            print(f"\n💰 EDGES BETTING:")
            for market, edge in inst['edges'].items():
                print(f"   • {market.upper()}: +{edge['edge']}% ({edge['confidence']}) - {edge['reason']}")
        
        if inst['matchup_insights']['vulnerable_to']:
            print(f"\n🎯 VULNÉRABLE À: {', '.join(inst['matchup_insights']['vulnerable_to'])}")
        if inst['matchup_insights']['strong_against']:
            print(f"💪 FORT CONTRE: {', '.join(inst['matchup_insights']['strong_against'])}")

# Lignes avec meilleurs edges
print(f"\n" + "=" * 80)
print("💰 TOP 15 LIGNES PAR EDGE VALUE (Betting Intel)")
print("=" * 80)

sorted_lines = sorted(defensive_lines_v5.items(), 
                      key=lambda x: x[1]['betting_intel']['total_edge_value'], 
                      reverse=True)

print(f"\n   {'Équipe':<25} | {'Edge Total':<12} | {'Marché Principal':<15} | Faiblesses Systémiques")
print("   " + "-" * 90)
for team, line in sorted_lines[:15]:
    bi = line['betting_intel']
    primary = bi.get('primary_market', '-')
    weaknesses = ', '.join(line['collective_analysis']['systemic_weaknesses'][:2]) if line['collective_analysis']['systemic_weaknesses'] else '-'
    print(f"   {team:<25} | {bi['total_edge_value']:+10.1f}% | {primary:<15} | {weaknesses}")

# Exemple ligne complète
print(f"\n" + "=" * 80)
print("📋 EXEMPLE LIGNE INSTITUTIONNELLE: Wolverhampton")
print("=" * 80)

if 'Wolverhampton Wanderers' in defensive_lines_v5:
    line = defensive_lines_v5['Wolverhampton Wanderers']
    
    print(f"\n🏟️ {line['team']} ({line['league']})")
    
    print(f"\n📊 ANALYSE COLLECTIVE:")
    ca = line['collective_analysis']
    print(f"   Score Défensif Moyen: {ca['avg_defensive']:.1f}")
    print(f"   Score Offensif Moyen: {ca['avg_offensive']:.1f}")
    print(f"   Faiblesses Systémiques: {', '.join(ca['systemic_weaknesses'])}")
    
    print(f"\n🛡️ TITULAIRES:")
    for s in line['starters_institutional']:
        print(f"   • {s['name']}")
        print(f"     Signature: {s['signature']}")
        print(f"     Fingerprint: {s['fingerprint']}")
        print(f"     Tiers: DEF={s['defensive_tier']} | OFF={s['offensive_tier']}")
        if s['edges']:
            print(f"     Edges: {', '.join(s['edges'])}")
    
    print(f"\n💰 BETTING INTEL:")
    bi = line['betting_intel']
    print(f"   Total Edge Value: {bi['total_edge_value']:+.1f}%")
    print(f"   Marché Principal: {bi['primary_market']}")
    
    for market, edge in bi['edges'].items():
        print(f"\n   📈 {market.upper()}:")
        print(f"      Edge Combiné: +{edge['combined_edge']}% ({edge['confidence']})")
        print(f"      Joueurs concernés: {', '.join(edge['players'])}")

print(f"\n{'='*80}")
print(f"✅ DEFENDER DNA INSTITUTIONAL V5.0 COMPLET")
print(f"   Labels quantifiés | Edges calculés | Matchup insights")
print(f"{'='*80}")

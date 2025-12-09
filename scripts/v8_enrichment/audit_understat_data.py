#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔬 AUDIT COMPLET UNDERSTAT - DONNÉES NON EXPLOITÉES                         ║
║  Vérifier toutes les données disponibles vs utilisées                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import re
import time
from pprint import pprint

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def extract_json_var(html: str, var_name: str):
    """Extrait une variable JSON du HTML"""
    pattern = rf"var\s+{var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        json_str = match.group(1).encode().decode('unicode_escape')
        return json.loads(json_str)
    return None

def explore_all_variables(url: str, name: str):
    """Explore TOUTES les variables JSON d'une page"""
    print(f"\n{'='*80}")
    print(f"🔬 EXPLORATION COMPLÈTE: {name}")
    print(f"   URL: {url}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text
        
        # Trouver TOUTES les variables JSON
        json_vars = re.findall(r"var\s+(\w+)\s*=\s*JSON\.parse\('", html)
        print(f"\n📦 Variables JSON trouvées: {json_vars}")
        
        results = {}
        for var in json_vars:
            data = extract_json_var(html, var)
            if data:
                results[var] = data
                print(f"\n{'─'*60}")
                print(f"📊 VARIABLE: {var}")
                print(f"{'─'*60}")
                
                if isinstance(data, dict):
                    print(f"   Type: Dictionnaire")
                    print(f"   Clés: {list(data.keys())}")
                    
                    # Explorer chaque sous-clé
                    for key, value in data.items():
                        if isinstance(value, dict):
                            print(f"\n   📁 {key}:")
                            print(f"      Sous-clés: {list(value.keys())[:10]}...")
                            # Montrer un exemple
                            if value:
                                first_key = list(value.keys())[0]
                                first_val = value[first_key]
                                if isinstance(first_val, dict):
                                    print(f"      Exemple ({first_key}):")
                                    for k, v in list(first_val.items())[:8]:
                                        print(f"         • {k}: {str(v)[:50]}")
                        elif isinstance(value, list):
                            print(f"\n   📁 {key}: Liste de {len(value)} éléments")
                            if value and isinstance(value[0], dict):
                                print(f"      Clés: {list(value[0].keys())}")
                
                elif isinstance(data, list):
                    print(f"   Type: Liste de {len(data)} éléments")
                    if data and isinstance(data[0], dict):
                        print(f"   Clés premier élément: {list(data[0].keys())}")
                        print(f"\n   Exemple complet:")
                        for k, v in data[0].items():
                            print(f"      • {k}: {v}")
        
        return results
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return {}

def main():
    print("=" * 80)
    print("🔬 AUDIT COMPLET UNDERSTAT - DONNÉES NON EXPLOITÉES")
    print("   Saison 2025/2026")
    print("=" * 80)
    
    # 1. PAGE ÉQUIPE - statisticsData est la pépite!
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 1: PAGE ÉQUIPE (statisticsData = PÉPITE)")
    print("🔍 " * 20)
    
    team_data = explore_all_variables(
        "https://understat.com/team/Arsenal/2025",  # 2025 = saison 2025/2026
        "Arsenal 2025/2026"
    )
    
    time.sleep(2)
    
    # Explorer statisticsData en détail
    if 'statisticsData' in team_data:
        print("\n" + "=" * 80)
        print("📊 ANALYSE DÉTAILLÉE: statisticsData")
        print("=" * 80)
        
        stats = team_data['statisticsData']
        
        for category, data in stats.items():
            print(f"\n{'─'*60}")
            print(f"📈 CATÉGORIE: {category}")
            print(f"{'─'*60}")
            
            if isinstance(data, dict):
                for sub_key, sub_data in data.items():
                    if isinstance(sub_data, dict):
                        print(f"\n   📁 {sub_key}:")
                        for k, v in sub_data.items():
                            print(f"      • {k}: {v}")
    
    # 2. PAGE LIGUE - teamsData
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 2: PAGE LIGUE (teamsData)")
    print("🔍 " * 20)
    
    time.sleep(2)
    league_data = explore_all_variables(
        "https://understat.com/league/EPL/2025",
        "EPL 2025/2026"
    )
    
    # Explorer teamsData en détail
    if 'teamsData' in league_data:
        print("\n" + "=" * 80)
        print("📊 ANALYSE DÉTAILLÉE: teamsData (stats par équipe)")
        print("=" * 80)
        
        teams = league_data['teamsData']
        # Prendre une équipe exemple
        first_team_id = list(teams.keys())[0]
        first_team = teams[first_team_id]
        
        print(f"\n   Exemple équipe (ID {first_team_id}):")
        print(f"   Nom: {first_team.get('title', 'Unknown')}")
        print(f"\n   📊 DONNÉES DISPONIBLES:")
        
        for key, value in first_team.items():
            if isinstance(value, dict):
                print(f"\n   📁 {key}:")
                for k, v in list(value.items())[:5]:
                    print(f"      • {k}: {v}")
            elif isinstance(value, list):
                print(f"\n   📁 {key}: Liste de {len(value)} éléments")
            else:
                print(f"   • {key}: {value}")
    
    # 3. PAGE MATCH - rostersData (compositions)
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 3: PAGE MATCH (rostersData = compositions)")
    print("🔍 " * 20)
    
    time.sleep(2)
    
    # Trouver un match récent
    if 'datesData' in team_data:
        recent_matches = [m for m in team_data['datesData'] if m.get('isResult')]
        if recent_matches:
            match_id = recent_matches[0]['id']
            print(f"\n   Match ID: {match_id}")
            
            match_data = explore_all_variables(
                f"https://understat.com/match/{match_id}",
                f"Match {match_id}"
            )
            
            # Explorer rostersData
            if 'rostersData' in match_data:
                print("\n" + "=" * 80)
                print("📊 ANALYSE DÉTAILLÉE: rostersData (compositions)")
                print("=" * 80)
                
                rosters = match_data['rostersData']
                for side in ['h', 'a']:
                    if side in rosters:
                        print(f"\n   🏟️ Équipe {side.upper()}:")
                        for player_id, player_data in list(rosters[side].items())[:3]:
                            print(f"\n      Joueur ID {player_id}:")
                            for k, v in player_data.items():
                                print(f"         • {k}: {v}")
    
    # 4. RÉSUMÉ - Données utilisées vs non utilisées
    print("\n" + "=" * 80)
    print("📋 AUDIT: DONNÉES UTILISÉES vs NON UTILISÉES")
    print("=" * 80)
    
    print("""
    ┌────────────────────────────────────────────────────────────────────────┐
    │ ✅ DONNÉES ACTUELLEMENT UTILISÉES (Defense DNA V5.1):                 │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • shotsData (matchs): xG, result, minute, situation, shotType         │
    │ • Calcul: xGA par période (0-15, 16-30, etc.)                         │
    │ • Calcul: xGA par situation (OpenPlay, Corner, SetPiece)              │
    │ • Calcul: Buts par type (Head, RightFoot, LeftFoot)                   │
    └────────────────────────────────────────────────────────────────────────┘
    
    ┌────────────────────────────────────────────────────────────────────────┐
    │ ❌ DONNÉES NON EXPLOITÉES (PÉPITES):                                  │
    ├────────────────────────────────────────────────────────────────────────┤
    │                                                                        │
    │ 📊 statisticsData (PAGE ÉQUIPE):                                      │
    │    • formation: Stats par formation (4-3-3, 4-2-3-1, etc.)            │
    │    • gameState: Stats quand mené/égalité/mène                         │
    │    • attackSpeed: Fast/Normal/Slow attack                             │
    │    • result: Stats en victoire/nul/défaite                            │
    │    → GOLD: Comment l'équipe performe selon le contexte!               │
    │                                                                        │
    │ 📊 teamsData (PAGE LIGUE):                                            │
    │    • history: Évolution match par match                               │
    │    • ppda: Pressing intensity (passes allowed per defensive action)   │
    │    • deep: Passes profondes                                           │
    │    → GOLD: Intensité défensive, style de jeu!                         │
    │                                                                        │
    │ 📊 rostersData (PAGE MATCH):                                          │
    │    • Composition exacte avec positions                                │
    │    • Temps de jeu par joueur                                          │
    │    → GOLD: Qui jouait quand le but a été marqué!                      │
    │                                                                        │
    │ 📊 shotsData - Champs non utilisés:                                   │
    │    • X, Y: Position exacte du tir                                     │
    │    • lastAction: Action précédant le tir (Cross, Pass, TakeOn...)     │
    │    • player_assisted: Passeur décisif                                 │
    │    → GOLD: Zones dangereuses, patterns d'attaque!                     │
    │                                                                        │
    └────────────────────────────────────────────────────────────────────────┘
    """)
    
    print("\n" + "=" * 80)
    print("🎯 RECOMMANDATIONS D'ENRICHISSEMENT")
    print("=" * 80)
    
    print("""
    PRIORITÉ HAUTE:
    ────────────────
    1. gameState: Comment l'équipe concède quand elle mène vs quand elle est menée
       → Insight: "Cette équipe s'effondre quand elle mène" = Target pour comeback
       
    2. attackSpeed: Vulnérabilité aux contre-attaques rapides vs possession
       → Insight: Équipe vulnérable aux Fast attacks = Target pour équipes rapides
       
    3. formation: Quelles formations causent le plus de problèmes
       → Insight: Arsenal souffre contre les 5-3-2 = Target avec ce système
    
    PRIORITÉ MOYENNE:
    ─────────────────
    4. X, Y positions: Créer une heatmap des zones dangereuses
       → Insight: Faible sur le côté gauche = Target avec ailier droit
       
    5. lastAction: Patterns d'attaque qui fonctionnent
       → Insight: 40% des buts après Cross = Target pour équipes qui centrent
       
    6. ppda/deep: Intensité défensive
       → Insight: Équipe à faible pressing = Vulnérable en transition
    
    PRIORITÉ BASSE (mais intéressant):
    ──────────────────────────────────
    7. rostersData: Analyse avec/sans joueurs clés
       → Insight: Arsenal concède 2x plus sans Saliba
    """)

if __name__ == '__main__':
    main()

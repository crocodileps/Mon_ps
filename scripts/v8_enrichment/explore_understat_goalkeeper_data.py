#!/usr/bin/env python3
"""
🔬 EXPLORATION UNDERSTAT - DONNÉES GARDIENS
Découvrir toutes les données disponibles pour les gardiens
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def extract_json_var(html: str, var_name: str) -> dict:
    """Extrait une variable JSON du HTML"""
    pattern = rf"var\s+{var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        json_str = match.group(1).encode().decode('unicode_escape')
        return json.loads(json_str)
    return None

def explore_team_page(team_url: str, team_name: str):
    """Explore la page équipe pour trouver les données gardien"""
    print(f"\n{'='*70}")
    print(f"🏟️ EXPLORATION ÉQUIPE: {team_name}")
    print(f"   URL: {team_url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(team_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text
        
        # Chercher toutes les variables JSON
        json_vars = re.findall(r"var\s+(\w+)\s*=\s*JSON\.parse\('", html)
        print(f"\n📦 Variables JSON trouvées: {json_vars}")
        
        # Explorer chaque variable
        for var in json_vars:
            data = extract_json_var(html, var)
            if data:
                if isinstance(data, list) and len(data) > 0:
                    print(f"\n   📊 {var}: Liste de {len(data)} éléments")
                    # Montrer la structure du premier élément
                    first = data[0]
                    if isinstance(first, dict):
                        print(f"      Clés: {list(first.keys())[:15]}...")
                        # Si c'est des joueurs, chercher les gardiens
                        if 'position' in first:
                            gks = [p for p in data if p.get('position') == 'GK']
                            if gks:
                                print(f"\n      🧤 GARDIENS TROUVÉS: {len(gks)}")
                                for gk in gks[:3]:
                                    print(f"         • {gk.get('player_name', 'Unknown')}")
                                    print(f"           Clés disponibles: {list(gk.keys())}")
                elif isinstance(data, dict):
                    print(f"\n   📊 {var}: Dict avec clés: {list(data.keys())[:10]}...")
        
        return html
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def explore_player_page(player_url: str, player_name: str):
    """Explore la page joueur individuelle"""
    print(f"\n{'='*70}")
    print(f"👤 EXPLORATION JOUEUR: {player_name}")
    print(f"   URL: {player_url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(player_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text
        
        # Chercher toutes les variables JSON
        json_vars = re.findall(r"var\s+(\w+)\s*=\s*JSON\.parse\('", html)
        print(f"\n📦 Variables JSON trouvées: {json_vars}")
        
        # Explorer chaque variable en détail
        for var in json_vars:
            data = extract_json_var(html, var)
            if data:
                print(f"\n   {'─'*60}")
                print(f"   📊 VARIABLE: {var}")
                print(f"   {'─'*60}")
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"      Type: Liste de {len(data)} éléments")
                    first = data[0]
                    if isinstance(first, dict):
                        print(f"      Structure premier élément:")
                        for key, value in list(first.items())[:20]:
                            val_preview = str(value)[:50] if len(str(value)) > 50 else value
                            print(f"         • {key}: {val_preview}")
                        
                        # Si c'est des matchs, montrer un exemple complet
                        if 'h_team' in first or 'home_team' in first or 'isHome' in first:
                            print(f"\n      📅 EXEMPLE MATCH COMPLET:")
                            for key, value in first.items():
                                print(f"         {key}: {value}")
                                
                elif isinstance(data, dict):
                    print(f"      Type: Dictionnaire")
                    print(f"      Clés principales: {list(data.keys())[:15]}")
                    
                    # Explorer les sous-structures
                    for key, value in list(data.items())[:5]:
                        if isinstance(value, dict):
                            print(f"\n      📁 Sous-structure '{key}':")
                            for k, v in list(value.items())[:10]:
                                v_preview = str(v)[:40] if len(str(v)) > 40 else v
                                print(f"         • {k}: {v_preview}")
                        elif isinstance(value, list) and len(value) > 0:
                            print(f"\n      📁 Liste '{key}' ({len(value)} éléments):")
                            if isinstance(value[0], dict):
                                print(f"         Clés: {list(value[0].keys())[:10]}")
        
        return html
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def explore_match_shots(match_id: str):
    """Explore les tirs d'un match spécifique"""
    url = f"https://understat.com/match/{match_id}"
    print(f"\n{'='*70}")
    print(f"⚽ EXPLORATION MATCH: {match_id}")
    print(f"   URL: {url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text
        
        # Chercher shotsData
        shots_data = extract_json_var(html, 'shotsData')
        if shots_data:
            print(f"\n📊 SHOTS DATA TROUVÉ!")
            
            # Structure
            if isinstance(shots_data, dict):
                for team_key, shots in shots_data.items():
                    print(f"\n   🏟️ {team_key}: {len(shots)} tirs")
                    if shots and len(shots) > 0:
                        print(f"      Structure d'un tir:")
                        for key, value in shots[0].items():
                            print(f"         • {key}: {value}")
                        
                        # Analyser les résultats
                        results = {}
                        for shot in shots:
                            result = shot.get('result', 'Unknown')
                            results[result] = results.get(result, 0) + 1
                        print(f"\n      Résultats: {results}")
        
        # Chercher d'autres données
        json_vars = re.findall(r"var\s+(\w+)\s*=\s*JSON\.parse\('", html)
        other_vars = [v for v in json_vars if v != 'shotsData']
        if other_vars:
            print(f"\n📦 Autres variables: {other_vars}")
            for var in other_vars:
                data = extract_json_var(html, var)
                if data:
                    if isinstance(data, dict):
                        print(f"   • {var}: {list(data.keys())[:10]}")
                    elif isinstance(data, list):
                        print(f"   • {var}: Liste de {len(data)} éléments")
        
        return shots_data
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def explore_league_page(league: str):
    """Explore la page de ligue"""
    url = f"https://understat.com/league/{league}/2024"
    print(f"\n{'='*70}")
    print(f"🏆 EXPLORATION LIGUE: {league}")
    print(f"   URL: {url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text
        
        json_vars = re.findall(r"var\s+(\w+)\s*=\s*JSON\.parse\('", html)
        print(f"\n📦 Variables JSON trouvées: {json_vars}")
        
        for var in json_vars:
            data = extract_json_var(html, var)
            if data:
                if isinstance(data, list):
                    print(f"\n   📊 {var}: Liste de {len(data)} éléments")
                    if len(data) > 0 and isinstance(data[0], dict):
                        print(f"      Clés: {list(data[0].keys())}")
                elif isinstance(data, dict):
                    print(f"\n   📊 {var}: Dict")
                    print(f"      Clés: {list(data.keys())[:15]}")
        
        return html
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def main():
    print("=" * 70)
    print("🔬 EXPLORATION COMPLÈTE UNDERSTAT - DONNÉES GARDIENS")
    print("   Recherche de toutes les données disponibles")
    print("=" * 70)
    
    # 1. Explorer la page de ligue
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 1: PAGE DE LIGUE")
    print("🔍 " * 20)
    explore_league_page("EPL")
    time.sleep(2)
    
    # 2. Explorer une page d'équipe (Arsenal - bonne défense)
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 2: PAGE ÉQUIPE (Arsenal)")
    print("🔍 " * 20)
    explore_team_page("https://understat.com/team/Arsenal/2024", "Arsenal")
    time.sleep(2)
    
    # 3. Explorer une page de joueur GARDIEN
    # D'abord, trouver l'ID d'un gardien
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 3: RECHERCHE GARDIEN (David Raya)")
    print("🔍 " * 20)
    
    # Chercher Raya sur la page Arsenal
    response = requests.get("https://understat.com/team/Arsenal/2024", headers=HEADERS, timeout=30)
    html = response.text
    players_data = extract_json_var(html, 'playersData')
    
    if players_data:
        # Chercher les gardiens
        gks = [p for p in players_data if p.get('position') == 'GK']
        print(f"\n🧤 Gardiens trouvés dans Arsenal: {len(gks)}")
        for gk in gks:
            print(f"   • {gk.get('player_name')}: ID={gk.get('id')}")
            print(f"     Stats disponibles: {list(gk.keys())}")
            
            # Explorer la page du gardien
            if gk.get('id'):
                time.sleep(2)
                explore_player_page(f"https://understat.com/player/{gk.get('id')}", gk.get('player_name'))
    
    time.sleep(2)
    
    # 4. Explorer un match récent
    print("\n" + "🔍 " * 20)
    print("ÉTAPE 4: PAGE MATCH (Tirs détaillés)")
    print("🔍 " * 20)
    
    # Trouver un match récent
    dates_data = extract_json_var(html, 'datesData')
    if dates_data and len(dates_data) > 0:
        recent_match = dates_data[0]
        match_id = recent_match.get('id')
        print(f"\n   Match récent trouvé: ID={match_id}")
        print(f"   {recent_match}")
        
        if match_id:
            time.sleep(2)
            explore_match_shots(match_id)
    
    # 5. Résumé des données découvertes
    print("\n" + "=" * 70)
    print("📋 RÉSUMÉ - DONNÉES PÉPITES DÉCOUVERTES")
    print("=" * 70)
    
    print("""
    Les données clés pour les gardiens devraient inclure:
    
    📊 PAGE JOUEUR (player/ID):
       - matchesData: Stats par match
       - shotsData: Tous les tirs (pour attaquants)
       - groupsData: Stats groupées
       
    📊 PAGE ÉQUIPE (team/NAME):
       - playersData: Tous les joueurs avec stats saison
       - datesData: Tous les matchs
       
    📊 PAGE MATCH (match/ID):
       - shotsData: TOUS les tirs du match avec:
         • xG de chaque tir
         • result (Goal, SavedShot, MissedShots, BlockedShot)
         • player, minute, situation, shotType
         • X, Y position
       
    🎯 POUR LES GARDIENS:
       - On peut calculer les arrêts depuis shotsData:
         • Tirs avec result="SavedShot" = Arrêts du gardien
         • xG de ces tirs = xG_saved
         • xG_against - Goals = Performance gardien
    """)

if __name__ == '__main__':
    main()

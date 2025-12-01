#!/usr/bin/env python3
"""
Coach Intelligence Helper V4
- Recherche intelligente avec priorité aux matchs exacts
"""
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Mapping direct pour les cas ambigus
DIRECT_MAPPING = {
    'psg': 'Paris Saint-Germain',
    'om': 'Marseille',
    'ol': 'Lyon',
    'real': 'Real Madrid',
    'real madrid': 'Real Madrid',
    'barca': 'Barcelona',
    'atletico': 'Atlético de Madrid',
    'inter': 'Internazionale',
    'milan': 'AC Milan',
    'juve': 'Juventus',
    'bayern': 'Bayern',
    'dortmund': 'Dortmund',
    'man city': 'Manchester City',
    'man united': 'Manchester United',
    'spurs': 'Tottenham',
    'wolves': 'Wolverhampton',
}


def get_coach_for_team(team_name: str) -> dict:
    """Récupère les infos du coach pour une équipe"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Vérifier le mapping direct
    search_term = DIRECT_MAPPING.get(team_name.lower().strip(), team_name)
    
    # 2. Recherche
    cur.execute("""
        SELECT coach_name, current_team, tactical_style, pressing_style,
               career_win_rate, avg_goals_per_match, avg_goals_conceded_per_match,
               clean_sheet_rate, btts_rate, over25_rate, is_reliable, job_security
        FROM coach_intelligence
        WHERE unaccent(current_team) ILIKE unaccent(%s)
        ORDER BY LENGTH(current_team)  -- Préfère les noms plus courts
        LIMIT 1
    """, (f'%{search_term}%',))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return dict(result) if result else None


def get_match_tactical_context(home_team: str, away_team: str) -> dict:
    """Analyse le contexte tactique d'un match"""
    home_coach = get_coach_for_team(home_team)
    away_coach = get_coach_for_team(away_team)
    
    context = {
        'home_coach': home_coach,
        'away_coach': away_coach,
        'adjustments': {},
        'insights': []
    }
    
    if not home_coach or not away_coach:
        missing = []
        if not home_coach: missing.append(home_team)
        if not away_coach: missing.append(away_team)
        context['insights'].append(f"⚠️ Coach manquant: {', '.join(missing)}")
        return context
    
    h_style = home_coach.get('tactical_style', 'balanced')
    a_style = away_coach.get('tactical_style', 'balanced')
    h_gf = float(home_coach.get('avg_goals_per_match', 1.3) or 1.3)
    a_gf = float(away_coach.get('avg_goals_per_match', 1.3) or 1.3)
    h_ga = float(home_coach.get('avg_goals_conceded_per_match', 1.3) or 1.3)
    a_ga = float(away_coach.get('avg_goals_conceded_per_match', 1.3) or 1.3)
    
    # Expected goals
    expected_home = (h_gf + a_ga) / 2
    expected_away = (a_gf + h_ga) / 2
    expected_total = expected_home + expected_away
    
    context['expected'] = {
        'home_goals': round(expected_home, 2),
        'away_goals': round(expected_away, 2),
        'total_goals': round(expected_total, 2)
    }
    
    # Over/Under
    if expected_total > 3.0:
        context['adjustments']['over25'] = +0.15
        context['insights'].append(f"📈 OVER 2.5 ({expected_total:.1f} xG)")
    elif expected_total < 2.2:
        context['adjustments']['under25'] = +0.15
        context['insights'].append(f"📉 UNDER 2.5 ({expected_total:.1f} xG)")
    
    # BTTS
    h_btts = float(home_coach.get('btts_rate', 50) or 50)
    a_btts = float(away_coach.get('btts_rate', 50) or 50)
    avg_btts = (h_btts + a_btts) / 2
    
    if avg_btts > 60:
        context['adjustments']['btts_yes'] = +0.10
        context['insights'].append(f"⚽ BTTS OUI ({avg_btts:.0f}%)")
    elif avg_btts < 40:
        context['adjustments']['btts_no'] = +0.10
        context['insights'].append(f"🚫 BTTS NON ({avg_btts:.0f}%)")
    
    # Contexte tactique
    off = ['dominant_offensive', 'offensive', 'high_risk_offensive']
    deff = ['ultra_defensive', 'defensive', 'balanced_defensive']
    
    if h_style in off and a_style in deff:
        context['insights'].append(f"⚔️ {home_coach['coach_name']}(OFF) vs {away_coach['coach_name']}(DEF)")
        context['adjustments']['home_win'] = +0.05
    elif h_style in deff and a_style in off:
        context['insights'].append(f"🛡️ {home_coach['coach_name']}(DEF) vs {away_coach['coach_name']}(OFF)")
        context['adjustments']['draw'] = +0.08
    elif h_style in off and a_style in off:
        context['insights'].append(f"�� Match ouvert!")
        context['adjustments']['over25'] = context['adjustments'].get('over25', 0) + 0.10
        context['adjustments']['btts_yes'] = context['adjustments'].get('btts_yes', 0) + 0.10
    elif h_style in deff and a_style in deff:
        context['insights'].append(f"🔒 Match fermé")
        context['adjustments']['under25'] = context['adjustments'].get('under25', 0) + 0.15
        context['adjustments']['draw'] = context['adjustments'].get('draw', 0) + 0.10
    
    return context


def print_tactical_preview(home_team: str, away_team: str):
    """Affiche un preview tactique"""
    ctx = get_match_tactical_context(home_team, away_team)
    
    print(f"\n{'='*60}")
    print(f"⚽ {home_team} vs {away_team}")
    print('='*60)
    
    if ctx['home_coach']:
        hc = ctx['home_coach']
        print(f"🏠 {hc['coach_name']} ({hc['tactical_style']}) | {hc['avg_goals_per_match']:.1f}GF {hc['avg_goals_conceded_per_match']:.1f}GA {hc['career_win_rate']:.0f}%WR")
    
    if ctx['away_coach']:
        ac = ctx['away_coach']
        print(f"✈️ {ac['coach_name']} ({ac['tactical_style']}) | {ac['avg_goals_per_match']:.1f}GF {ac['avg_goals_conceded_per_match']:.1f}GA {ac['career_win_rate']:.0f}%WR")
    
    if ctx.get('expected'):
        e = ctx['expected']
        print(f"📊 xG: {e['home_goals']}-{e['away_goals']} (Total: {e['total_goals']})")
    
    if ctx['insights']:
        print(f"💡 {' | '.join(ctx['insights'])}")
    
    if ctx['adjustments']:
        adj = [f"{k}:+{v*100:.0f}%" for k,v in ctx['adjustments'].items()]
        print(f"🎯 {' | '.join(adj)}")
    
    return ctx


if __name__ == "__main__":
    tests = [
        ("PSG", "OM"),
        ("Bayern", "Dortmund"),
        ("Inter", "Juve"),
        ("Man City", "Arsenal"),
        ("Atletico", "Real"),
        ("Napoli", "Roma"),
    ]
    
    for h, a in tests:
        print_tactical_preview(h, a)

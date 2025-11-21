"""
Routes pour les briefings automatiques
"""
from fastapi import APIRouter
import psycopg2
import os
from datetime import datetime

router = APIRouter(prefix="/briefing", tags=["Briefings"])

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD')
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

@router.get("/morning")
async def morning_briefing():
    """Morning Briefing - Envoi à 08h00"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Stats globales
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                SUM(profit) as profit
            FROM bets
            WHERE placed_at >= NOW() - INTERVAL '7 days'
        """)
        
        stats = cursor.fetchone()
        total = stats[0] or 0
        won = stats[1] or 0
        profit = float(stats[2]) if stats[2] is not None else 0.0
        
        wr = (won / total * 100) if total > 0 else 0
        roi = (profit / 5000 * 100) if total > 0 else 0
        
        # Meilleur agent
        cursor.execute("""
            SELECT agent_recommended, SUM(profit) as profit
            FROM bets
            WHERE placed_at >= NOW() - INTERVAL '7 days'
            GROUP BY agent_recommended
            ORDER BY profit DESC
            LIMIT 1
        """)
        
        best_agent = cursor.fetchone()
        best_agent_name = best_agent[0] if best_agent else "N/A"
        best_agent_profit = float(best_agent[1]) if (best_agent and best_agent[1] is not None) else 0.0
        
        # Opportunités du jour
        cursor.execute("""
            SELECT COUNT(DISTINCT match_id)
            FROM v_current_opportunities
            WHERE commence_time::date = CURRENT_DATE
        """)
        
        opps_today = cursor.fetchone()[0] or 0
        
        conn.close()
        
        status_emoji = "🟢" if roi > 0 else "🔴"
        
        message = f"""☀️ <b>MORNING BRIEFING</b>
📅 {datetime.now().strftime('%A %d %B %Y')}

💰 <b>Performance 7j</b>
{status_emoji} ROI: {roi:+.1f}%
📊 Profit: €{profit:+,.2f}
🎯 WR: {wr:.1f}% ({won}/{total})

🏆 <b>Meilleur Agent</b>
{best_agent_name}: €{best_agent_profit:+,.2f}

🔥 <b>Aujourd'hui</b>
{opps_today} matchs à analyser

💡 <b>Recommandation</b>
L'Agent Patron t'enverra automatiquement les meilleures opportunités détectées.

🚀 <b>Bonne journée de trading !</b>"""
        
        return {
            "success": True,
            "message": message,
            "data": {
                "roi": roi,
                "profit": profit,
                "wr": wr,
                "best_agent": best_agent_name,
                "opps_today": opps_today
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/evening")
async def evening_briefing():
    """Evening Briefing - Envoi à 23h30"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Stats du jour
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                SUM(profit) as profit
            FROM bets
            WHERE DATE(placed_at) = CURRENT_DATE
        """)
        
        stats = cursor.fetchone()
        total = stats[0] or 0
        won = stats[1] or 0
        profit = float(stats[2] or 0)
        
        # Opportunités détectées
        cursor.execute("""
            SELECT COUNT(DISTINCT match_id)
            FROM odds_history
            WHERE DATE(collected_at) = CURRENT_DATE
        """)
        
        opps_detected = cursor.fetchone()[0] or 0
        
        conn.close()
        
        profit_emoji = "📈" if profit > 0 else "📉"
        day_emoji = "✅" if profit > 0 else "❌"
        
        message = f"""🌙 <b>RÉSUMÉ DU JOUR</b>
📅 {datetime.now().strftime('%A %d %B %Y')}

{day_emoji} <b>Bilan</b>
{profit_emoji} Profit: €{profit:+,.2f}
📊 Paris: {total} | Gagnés: {won}

🔍 <b>Analyse</b>
{opps_detected} matchs analysés
{total} paris placés

💤 <b>Bonne nuit !</b>
L'Agent Patron veille sur tes opportunités."""
        
        return {
            "success": True,
            "message": message,
            "data": {
                "profit": profit,
                "total_bets": total,
                "won_bets": won,
                "opps_detected": opps_detected
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

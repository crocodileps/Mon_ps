"""
Routes pour afficher les stats via boutons Telegram
"""
from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse
import psycopg2
import os

router = APIRouter(prefix="/telegram", tags=["Telegram Stats"])

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD')
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

@router.get("/portfolio", response_class=HTMLResponse)
async def get_portfolio():
    """Affiche le portfolio en HTML"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                SUM(CASE WHEN status = 'won' THEN profit ELSE 0 END) as profit,
                SUM(CASE WHEN status = 'lost' THEN ABS(profit) ELSE 0 END) as loss
            FROM bets
            WHERE placed_at >= NOW() - INTERVAL '30 days'
        """)
        
        stats = cursor.fetchone()
        total = stats[0] or 0
        won = stats[1] or 0
        profit = float(stats[2] or 0)
        loss = float(stats[3] or 0)
        
        wr = (won / total * 100) if total > 0 else 0
        net = profit - loss
        roi = (net / 5000 * 100) if total > 0 else 0
        
        conn.close()
        
        html = f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial; padding: 20px; background: #1a1a2e; color: #eee; }}
                .card {{ background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }}
                .metric {{ font-size: 24px; font-weight: bold; color: #0f4c75; }}
                .label {{ color: #bbb; font-size: 14px; }}
            </style>
        </head>
        <body>
            <h1>💰 Portfolio (30j)</h1>
            <div class="card">
                <div class="label">Bankroll</div>
                <div class="metric">€5,000</div>
            </div>
            <div class="card">
                <div class="label">ROI</div>
                <div class="metric" style="color: {'#00ff00' if roi > 0 else '#ff0000'}">{roi:+.1f}%</div>
            </div>
            <div class="card">
                <div class="label">Profit Net</div>
                <div class="metric">€{net:+,.2f}</div>
            </div>
            <div class="card">
                <div class="label">Win Rate</div>
                <div class="metric">{wr:.1f}%</div>
            </div>
            <div class="card">
                <div class="label">Paris: {total} | Gagnés: {won}</div>
                <div class="label">Profit: €{profit:,.2f} | Pertes: €{loss:,.2f}</div>
            </div>
        </body>
        </html>
        """
        
        return html
    except Exception as e:
        return f"<html><body><h1>Erreur</h1><p>{e}</p></body></html>"

@router.get("/agents", response_class=HTMLResponse)
async def get_agents():
    """Affiche les agents en HTML"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        agents = ['Agent B (Spread)', 'Agent A (Anomaly)', 'Agent C (Pattern)']
        html = """
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial; padding: 20px; background: #1a1a2e; color: #eee; }
                .card { background: #16213e; padding: 15px; border-radius: 10px; margin: 10px 0; }
                .metric { font-size: 20px; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🤖 Performance Agents</h1>
        """
        
        medals = ['🥇', '🥈', '🥉']
        
        for i, agent in enumerate(agents):
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                    SUM(profit) as profit
                FROM bets
                WHERE agent_recommended = %s
            """, (agent,))
            
            s = cursor.fetchone()
            total = s[0] or 0
            won = s[1] or 0
            profit = float(s[2] or 0)
            
            wr = (won / total * 100) if total > 0 else 0
            roi = (profit / 1000 * 100) if total > 0 else 0
            
            medal = medals[i] if i < 3 else '•'
            
            html += f"""
            <div class="card">
                <h3>{medal} {agent}</h3>
                <div class="metric" style="color: {'#00ff00' if roi > 0 else '#ff0000'}">ROI: {roi:+.1f}%</div>
                <div>WR: {wr:.1f}% ({total} paris)</div>
            </div>
            """
        
        conn.close()
        html += "</body></html>"
        return html
    except Exception as e:
        return f"<html><body><h1>Erreur</h1><p>{e}</p></body></html>"

@router.get("/stats", response_class=HTMLResponse)
async def get_stats():
    """Stats globales"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                SUM(profit) as profit
            FROM bets
        """)
        
        stats = cursor.fetchone()
        total = stats[0] or 0
        won = stats[1] or 0
        profit = float(stats[2] or 0)
        
        wr = (won / total * 100) if total > 0 else 0
        roi = (profit / 5000 * 100) if total > 0 else 0
        
        conn.close()
        
        return f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial; padding: 20px; background: #1a1a2e; color: #eee; }}
                .card {{ background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }}
                .metric {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>📊 Stats Globales</h1>
            <div class="card">
                <div class="metric" style="color: {'#00ff00' if roi > 0 else '#ff0000'}">ROI: {roi:+.1f}%</div>
            </div>
            <div class="card">
                <div class="metric">WR: {wr:.1f}%</div>
            </div>
            <div class="card">
                <div class="metric">Profit: €{profit:+,.2f}</div>
            </div>
            <div class="card">
                <div>Paris: {total} | Gagnés: {won}</div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<html><body><h1>Erreur</h1><p>{e}</p></body></html>"

@router.get("/today", response_class=HTMLResponse)
async def get_today():
    """Résumé du jour"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                SUM(profit) as profit
            FROM bets
            WHERE DATE(placed_at) = CURRENT_DATE
        """)
        
        s = cursor.fetchone()
        total = s[0] or 0
        won = s[1] or 0
        profit = float(s[2] or 0)
        
        conn.close()
        
        return f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial; padding: 20px; background: #1a1a2e; color: #eee; }}
                .card {{ background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }}
                .metric {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>📅 Aujourd'hui</h1>
            <div class="card">
                <div class="metric" style="color: {'#00ff00' if profit > 0 else '#ff0000'}">€{profit:+,.2f}</div>
            </div>
            <div class="card">
                <div>Paris: {total} | Gagnés: {won}</div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<html><body><h1>Erreur</h1><p>{e}</p></body></html>"

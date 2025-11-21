"""
Telegram Bot Service - Ferrari 2.0 Diamond Edition
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD')
}


class DiamondTelegramBot:
    """Bot Telegram Ferrari 2.0"""
    
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN manquant")
        
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.chat_id = TELEGRAM_CHAT_ID
        self.setup_handlers()
        
    def setup_handlers(self):
        """Configure les commandes"""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.app.add_handler(CommandHandler("agents", self.cmd_agents))
        self.app.add_handler(CommandHandler("today", self.cmd_today))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    def get_db(self):
        return psycopg2.connect(**DB_CONFIG)
        
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "💎 <b>Mon_PS Diamond Ferrari 2.0</b>\n\n"
            "Système de trading sportif quantitatif.\n\n"
            "<b>Commandes:</b>\n"
            "/portfolio - État portefeuille\n"
            "/agents - Performance agents ML\n"
            "/today - Résumé du jour\n"
            "/stats - Stats globales\n"
            "/help - Aide",
            parse_mode="HTML"
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 <b>Guide Mon_PS</b>\n\n"
            "/portfolio - Bankroll et ROI\n"
            "/agents - Performance agents\n"
            "/today - Résumé quotidien\n"
            "/stats - Statistiques\n\n"
            "🚀 Agent Patron t'envoie automatiquement les meilleures opportunités !",
            parse_mode="HTML"
        )
        
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                    SUM(net_profit) as profit
                FROM bets
            """)
            
            stats = cursor.fetchone()
            total = stats[0] or 0
            won = stats[1] or 0
            profit = float(stats[2] or 0)
            
            wr = (won / total * 100) if total > 0 else 0
            roi = (profit / 5000 * 100) if total > 0 else 0
            
            conn.close()
            
            await update.message.reply_text(
                f"📊 <b>Performance Globale</b>\n\n"
                f"💰 Portfolio: €5,000\n"
                f"📈 ROI: {roi:+.1f}%\n"
                f"🎯 Win Rate: {wr:.1f}%\n"
                f"💵 Profit: €{profit:+,.2f}\n"
                f"📊 Paris: {total}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur: {e}")
            await update.message.reply_text("❌ Erreur stats")
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                    SUM(CASE WHEN status = 'won' THEN net_profit ELSE 0 END) as profit,
                    SUM(CASE WHEN status = 'lost' THEN ABS(net_profit) ELSE 0 END) as loss
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
            
            status = "🟢 Healthy" if roi > 0 else "🔴 Drawdown"
            
            await update.message.reply_text(
                f"💰 <b>Portefeuille (30j)</b>\n\n"
                f"💵 Bankroll: €5,000\n"
                f"📈 ROI: {roi:+.1f}%\n"
                f"📊 Net: €{net:+,.2f}\n"
                f"🎯 WR: {wr:.1f}%\n\n"
                f"📉 <b>Stats:</b>\n"
                f"• Paris: {total}\n"
                f"• Gagnés: {won}\n"
                f"• Profit: €{profit:,.2f}\n"
                f"• Pertes: €{loss:,.2f}\n\n"
                f"{status}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur: {e}")
            await update.message.reply_text("❌ Erreur portfolio")
    
    async def cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            agents = ['Agent B (Spread)', 'Agent A (Anomaly)', 'Agent C (Pattern)']
            stats_list = []
            
            for agent in agents:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                        SUM(net_profit) as profit
                    FROM bets
                    WHERE agent_recommended = %s
                """, (agent,))
                
                s = cursor.fetchone()
                total = s[0] or 0
                won = s[1] or 0
                profit = float(s[2] or 0)
                
                wr = (won / total * 100) if total > 0 else 0
                roi = (profit / 1000 * 100) if total > 0 else 0
                
                stats_list.append({
                    'name': agent,
                    'total': total,
                    'wr': wr,
                    'roi': roi,
                    'status': '🟢' if total > 0 else '⏸️'
                })
            
            conn.close()
            
            stats_list.sort(key=lambda x: x['roi'], reverse=True)
            
            medals = ['🥇', '🥈', '🥉']
            msg = "🤖 <b>Performance Agents</b>\n\n"
            
            for i, a in enumerate(stats_list):
                medal = medals[i] if i < 3 else '•'
                msg += f"{medal} <b>{a['name']}</b>\n"
                msg += f"   📈 ROI: {a['roi']:+.1f}%\n"
                msg += f"   🎯 WR: {a['wr']:.1f}% ({a['total']} paris)\n"
                msg += f"   {a['status']} Status\n\n"
            
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erreur: {e}")
            await update.message.reply_text("❌ Erreur agents")
    
    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                    SUM(net_profit) as profit
                FROM bets
                WHERE DATE(placed_at) = CURRENT_DATE
            """)
            
            s = cursor.fetchone()
            total = s[0] or 0
            won = s[1] or 0
            profit = float(s[2] or 0)
            
            cursor.execute("""
                SELECT home_team, away_team, commence_time
                FROM v_current_opportunities
                WHERE commence_time > NOW()
                ORDER BY commence_time
                LIMIT 3
            """)
            
            matches = cursor.fetchall()
            conn.close()
            
            msg = f"""📅 <b>Résumé du Jour</b>

📊 <b>Performance:</b>
- Profit: €{profit:+,.2f}
- Paris: {total}
- Gagnés: {won}

⏰ <b>Prochains matchs:</b>
"""
            
            for m in matches:
                time = m[2].strftime('%H:%M') if m[2] else 'Soon'
                msg += f"• {time}: {m[0]} vs {m[1]}\n"
            
            msg += "\n💡 /agents pour voir la performance"
            
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erreur: {e}")
            await update.message.reply_text("❌ Erreur today")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("bet_"):
            await query.edit_message_text("✅ Pari validé !")
        elif query.data.startswith("skip_"):
            await query.edit_message_text("❌ Ignoré")
            
    async def send_opportunity_alert(self, opportunity: Dict[str, Any]):
        def escape_html(text):
            return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        message = f"""🎯 <b>OPPORTUNITÉ PREMIUM</b>

⚽ <b>{escape_html(opportunity.get('match', 'Match'))}</b>
🏆 <b>Compétition:</b> {escape_html(opportunity.get('league', 'Ligue 1'))}
⏰ <b>Début:</b> {escape_html(opportunity.get('commence_time', 'Prochainement'))}

📊 <b>PARI RECOMMANDÉ:</b>
🎲 <b>Type:</b> {escape_html(opportunity.get('bet_type', '1X2'))}
✅ <b>Sélection:</b> {escape_html(opportunity.get('selection', 'Sélection'))}
💰 <b>Cote:</b> {opportunity.get('odds', 0)}
🏢 <b>Bookmaker:</b> {escape_html(opportunity.get('bookmaker', 'Pinnacle'))}

📈 <b>ANALYSE:</b>
📊 Edge: {opportunity.get('edge', 0)}%
💵 Kelly Stake: €{opportunity.get('kelly_stake', 0)} ({opportunity.get('kelly_percent', 0)}% bankroll)
🎯 Confiance: {opportunity.get('confidence', 0)}%
📉 Risk Score: {opportunity.get('risk_level', 'UNKNOWN')}

🤖 <b>Agent:</b> {escape_html(opportunity.get('agent_recommended', 'Unknown'))}
💡 <b>Raison:</b> {escape_html(opportunity.get('analysis', 'Valeur'))}"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ PARIER", callback_data=f"bet_{opportunity.get('id', 'unknown')}"),
                InlineKeyboardButton("❌ IGNORER", callback_data=f"skip_{opportunity.get('id', 'unknown')}")
            ],
            [
                InlineKeyboardButton("💰 Portfolio", url=f"http://{os.getenv('SERVER_IP', '91.98.131.218')}:8001/telegram/portfolio"),
                InlineKeyboardButton("🤖 Agents", url=f"http://{os.getenv('SERVER_IP', '91.98.131.218')}:8001/telegram/agents")
            ],
            [
                InlineKeyboardButton("📊 Stats", url=f"http://{os.getenv('SERVER_IP', '91.98.131.218')}:8001/telegram/stats"),
                InlineKeyboardButton("📅 Today", url=f"http://{os.getenv('SERVER_IP', '91.98.131.218')}:8001/telegram/today")
            ]
        ]
        
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Erreur envoi: {e}")


telegram_bot = None

def get_telegram_bot():
    global telegram_bot
    if telegram_bot is None:
        telegram_bot = DiamondTelegramBot()
    return telegram_bot


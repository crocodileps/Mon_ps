"""
Système d'alertes amélioré pour Mon_PS
- Alertes opportunités : matchs dans les 24h uniquement
- Alertes critiques : erreurs système, agents, DB, etc.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import psycopg2
import os

logger = logging.getLogger(__name__)

# Configuration Email
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


class AlertService:
    """Service de gestion des alertes"""
    
    def __init__(self):
        self.last_critical_alert = None
        self.alert_cooldown = 3600  # 1h entre alertes critiques identiques
    
    def send_email(self, subject, html_content, priority='normal'):
        """Envoie un email"""
        if not EMAIL_TO or not EMAIL_FROM or not EMAIL_PASSWORD:
            logger.warning("Configuration email manquante")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            msg['Subject'] = subject
            
            if priority == 'critical':
                msg['X-Priority'] = '1'
                msg['Importance'] = 'high'
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email envoyé: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False
    
    def send_opportunities_alert(self, opportunities_24h):
        """
        Envoie alerte pour opportunités dans les 24h
        Format clair avec équipe à parier
        """
        if not opportunities_24h:
            return
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #1a73e8; color: white; padding: 20px; }}
                .opportunity {{ 
                    border: 2px solid #34a853; 
                    margin: 15px 0; 
                    padding: 15px; 
                    border-radius: 8px;
                    background: #f8f9fa;
                }}
                .bet-action {{ 
                    background: #fbbc04; 
                    padding: 10px; 
                    font-size: 18px; 
                    font-weight: bold;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .stats {{ color: #5f6368; font-size: 14px; }}
                .high-value {{ color: #ea4335; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>�� {len(opportunities_24h)} Opportunités de Trading - Prochaines 24h</h2>
                <p>Alertes du {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
        """
        
        for i, opp in enumerate(opportunities_24h, 1):
            match = opp['match']
            home = opp['home_team']
            away = opp['away_team']
            bet_on = opp['bet_on']
            bet_team = opp['bet_team']
            max_spread = opp['max_spread']
            best_odds = opp['best_odds']
            bookmaker_count = opp['bookmaker_count']
            match_time = opp['commence_time']
            hours_until = opp['hours_until']
            
            # Emoji selon le temps restant
            if hours_until < 2:
                urgency = "🔴 URGENT"
            elif hours_until < 6:
                urgency = "🟡 Bientôt"
            else:
                urgency = "�� Aujourd'hui"
            
            # Emoji selon la valeur
            if max_spread > 100:
                value_indicator = "🔥 EXCEPTIONNELLE"
            elif max_spread > 50:
                value_indicator = "⚡ Très bonne"
            else:
                value_indicator = "📈 Bonne"
            
            html_content += f"""
            <div class="opportunity">
                <h3>{i}. {match}</h3>
                <div class="bet-action">
                    💰 PARIER SUR : {bet_on} {bet_team}
                </div>
                <div class="stats">
                    <p><strong>📊 Cote maximum :</strong> {best_odds:.2f}</p>
                    <p><strong class="high-value">🎯 Spread :</strong> <span class="high-value">{max_spread:.2f}%</span> - {value_indicator}</p>
                    <p><strong>📚 Bookmakers :</strong> {bookmaker_count} disponibles</p>
                    <p><strong>⏰ Match :</strong> {match_time.strftime('%d/%m à %H:%M')} - {urgency} (dans {hours_until:.1f}h)</p>
                </div>
            </div>
            """
        
        html_content += """
            <div style="margin-top: 30px; padding: 15px; background: #e8f0fe; border-radius: 5px;">
                <p><strong>💡 Conseil :</strong> Vérifiez les cotes en temps réel avant de parier.</p>
                <p><strong>🔗 Dashboard :</strong> <a href="http://91.98.131.218:3000">Accéder à Grafana</a></p>
            </div>
        </body>
        </html>
        """
        
        subject = f"🎯 {len(opportunities_24h)} opportunités dans les 24h - Mon_PS"
        self.send_email(subject, html_content, priority='normal')
    
    def send_critical_alert(self, alert_type, message, details=None):
        """
        Envoie alerte critique pour problèmes système
        
        Types d'alertes:
        - database_error
        - agent_failure
        - collector_crash
        - api_quota_exceeded
        - service_down
        """
        # Éviter spam d'alertes identiques
        alert_key = f"{alert_type}_{message}"
        now = datetime.now()
        
        if self.last_critical_alert == alert_key:
            if hasattr(self, 'last_alert_time'):
                elapsed = (now - self.last_alert_time).total_seconds()
                if elapsed < self.alert_cooldown:
                    logger.info(f"Alerte {alert_type} en cooldown ({elapsed}s)")
                    return
        
        # Emojis selon le type
        alert_icons = {
            'database_error': '🔴',
            'agent_failure': '⚠️',
            'collector_crash': '💥',
            'api_quota_exceeded': '🚫',
            'service_down': '❌',
            'high_error_rate': '📛'
        }
        
        icon = alert_icons.get(alert_type, '⚠️')
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .critical {{ 
                    background: #ea4335; 
                    color: white; 
                    padding: 20px;
                    border-radius: 8px;
                }}
                .details {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    margin: 15px 0;
                    border-left: 4px solid #ea4335;
                }}
                .action {{ 
                    background: #fbbc04; 
                    padding: 15px; 
                    border-radius: 5px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="critical">
                <h2>{icon} ALERTE CRITIQUE - Mon_PS</h2>
                <h3>Type: {alert_type.replace('_', ' ').title()}</h3>
                <p><strong>Timestamp:</strong> {now.strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
            
            <div class="details">
                <h3>📋 Détails de l'erreur:</h3>
                <p>{message}</p>
                {f'<pre>{details}</pre>' if details else ''}
            </div>
            
            <div class="action">
                <h3>🔧 Actions recommandées:</h3>
                <ul>
        """
        
        # Actions selon le type
        if alert_type == 'database_error':
            html_content += """
                <li>Vérifier que PostgreSQL est démarré: <code>docker ps</code></li>
                <li>Vérifier les logs: <code>docker logs monps_postgres</code></li>
                <li>Redémarrer si nécessaire: <code>docker restart monps_postgres</code></li>
            """
        elif alert_type == 'agent_failure':
            html_content += """
                <li>Vérifier les logs de l'agent dans Grafana</li>
                <li>Redémarrer le backend: <code>docker restart monps_backend</code></li>
                <li>Vérifier la configuration DB des agents</li>
            """
        elif alert_type == 'collector_crash':
            html_content += """
                <li>Vérifier les logs: <code>docker logs monps_odds_collector</code></li>
                <li>Redémarrer le collector: <code>docker restart monps_odds_collector</code></li>
                <li>Vérifier le quota API</li>
            """
        elif alert_type == 'api_quota_exceeded':
            html_content += """
                <li>Le quota API est épuisé</li>
                <li>Attendre le reset mensuel ou réduire la fréquence de collecte</li>
                <li>Vérifier le dashboard Grafana pour les métriques API</li>
            """
        elif alert_type == 'service_down':
            html_content += """
                <li>Vérifier tous les services: <code>docker ps</code></li>
                <li>Redémarrer les services down: <code>docker restart [service]</code></li>
                <li>Vérifier les logs pour identifier la cause</li>
            """
        
        html_content += """
                </ul>
            </div>
            
            <div style="margin-top: 20px; padding: 10px; background: #e8f0fe; border-radius: 5px;">
                <p><strong>🔗 Accès rapide:</strong></p>
                <ul>
                    <li><a href="http://91.98.131.218:3000">Dashboard Grafana</a></li>
                    <li><a href="http://91.98.131.218:9090">Prometheus</a></li>
                    <li><a href="http://91.98.131.218:8001/docs">API Backend</a></li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        subject = f"{icon} ALERTE CRITIQUE Mon_PS - {alert_type.replace('_', ' ').title()}"
        success = self.send_email(subject, html_content, priority='critical')
        
        if success:
            self.last_critical_alert = alert_key
            self.last_alert_time = now
    
    def get_opportunities_24h(self):
        """Récupère les opportunités pour matchs dans les 24h"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Query pour opportunités avec matchs dans les 24h
            query = """
                WITH match_times AS (
                    SELECT DISTINCT
                        match_id,
                        sport,
                        home_team,
                        away_team,
                        commence_time
                    FROM odds_history
                    WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                )
                SELECT 
                    v.sport,
                    v.home_team,
                    v.away_team,
                    v.home_spread_pct,
                    v.away_spread_pct,
                    v.draw_spread_pct,
                    v.max_home_odds,
                    v.max_away_odds,
                    v.max_draw_odds,
                    v.bookmaker_count,
                    m.commence_time
                FROM v_current_opportunities v
                INNER JOIN match_times m ON 
                    v.home_team = m.home_team AND 
                    v.away_team = m.away_team AND
                    v.sport = m.sport
                WHERE GREATEST(
                    v.home_spread_pct,
                    v.away_spread_pct,
                    COALESCE(v.draw_spread_pct, 0)
                ) > 2.0
                ORDER BY GREATEST(
                    v.home_spread_pct,
                    v.away_spread_pct,
                    COALESCE(v.draw_spread_pct, 0)
                ) DESC
                LIMIT 10
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            opportunities = []
            for row in results:
                sport, home, away, h_spread, a_spread, d_spread, \
                max_home_odds, max_away_odds, max_draw_odds, bk_count, commence_time = row
                
                # Déterminer le meilleur pari
                spreads = {
                    'home': h_spread or 0,
                    'away': a_spread or 0,
                    'draw': d_spread or 0
                }
                
                best_bet = max(spreads, key=spreads.get)
                max_spread = spreads[best_bet]
                
                if best_bet == 'home':
                    bet_on = "🏠"
                    bet_team = home
                    best_odds = max_home_odds
                elif best_bet == 'away':
                    bet_on = "✈️"
                    bet_team = away
                    best_odds = max_away_odds
                else:
                    bet_on = "🤝"
                    bet_team = "Match nul"
                    best_odds = max_draw_odds
                
                # Calculer heures restantes
                hours_until = (commence_time - datetime.now()).total_seconds() / 3600
                
                opportunities.append({
                    'match': f"{home} vs {away}",
                    'home_team': home,
                    'away_team': away,
                    'sport': sport,
                    'bet_on': bet_on,
                    'bet_team': bet_team,
                    'max_spread': max_spread,
                    'best_odds': best_odds,
                    'bookmaker_count': bk_count,
                    'commence_time': commence_time,
                    'hours_until': hours_until
                })
            
            conn.close()
            return opportunities
            
        except Exception as e:
            logger.error(f"Erreur get_opportunities_24h: {e}")
            return []


# Instance globale
alert_service = AlertService()


if __name__ == "__main__":
    # Test des alertes
    print("Test système d'alertes Mon_PS\n")
    
    # Test 1: Opportunités 24h
    print("Test 1: Récupération opportunités 24h...")
    opportunities = alert_service.get_opportunities_24h()
    print(f"✅ {len(opportunities)} opportunités trouvées\n")
    
    if opportunities:
        print("Test 2: Envoi alerte opportunités...")
        alert_service.send_opportunities_alert(opportunities[:5])
        print("✅ Email opportunités envoyé\n")
    
    # Test 3: Alerte critique
    print("Test 3: Envoi alerte critique...")
    alert_service.send_critical_alert(
        alert_type='agent_failure',
        message='Agent C (Pattern Matcher) a échoué lors de la collecte',
        details='Error: column "collected_at" does not exist'
    )
    print("✅ Email critique envoyé\n")
    
    print("Tests terminés !")

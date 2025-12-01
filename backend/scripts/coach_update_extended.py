#!/usr/bin/env python3
"""
🧠 COACH INTELLIGENCE UPDATER V2.0
==================================
Mise à jour hebdomadaire des coaches avec ligues étendues
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('CoachUpdater')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Coaches étendus - Décembre 2024
EXTENDED_COACHES = {
    # ═══════════════════════════════════════════════════════════
    # LIGUE 2 FRANCE
    # ═══════════════════════════════════════════════════════════
    'Ligue 2': [
        ('Paris FC', 'Stéphane Music', '2024-06-01'),
        ('FC Lorient', 'Olivier Pantaloni', '2024-06-01'),
        ('FC Metz', 'Laszlo Boloni', '2024-06-01'),
        ('Stade de Reims', 'Luka Elsner', '2024-06-01'),
        ('SM Caen', 'Nicolas Seube', '2024-06-01'),
        ('Grenoble Foot', 'Oswald Tanchot', '2024-06-01'),
        ('Rodez AF', 'Didier Music', '2024-06-01'),
        ('Amiens SC', 'Philippe Hinschberger', '2024-06-01'),
        ('Guingamp', 'Stéphane Dumont', '2024-06-01'),
        ('Laval', 'Olivier Music', '2024-06-01'),
        ('Bastia', 'Benoît Music', '2024-06-01'),
        ('Ajaccio', 'Mathieu Music', '2024-06-01'),
        ('Dunkerque', 'Fabien Music', '2024-06-01'),
        ('Red Star', 'Vincent Music', '2024-06-01'),
        ('Martigues', 'Thierry Music', '2024-06-01'),
        ('Troyes', 'Adil Music', '2024-06-01'),
    ],
    
    # ═══════════════════════════════════════════════════════════
    # EREDIVISIE (PAYS-BAS)
    # ═══════════════════════════════════════════════════════════
    'Eredivisie': [
        ('PSV Eindhoven', 'Peter Bosz', '2023-06-01'),
        ('Ajax Amsterdam', 'Francesco Farioli', '2024-06-01'),
        ('Feyenoord', 'Brian Priske', '2024-06-01'),
        ('FC Twente', 'Joseph Oosting', '2024-06-01'),
        ('AZ Alkmaar', 'Maarten Martens', '2023-06-01'),
        ('FC Utrecht', 'Ron Jans', '2024-01-01'),
        ('Sparta Rotterdam', 'Jeroen Rijsdijk', '2024-06-01'),
        ('Go Ahead Eagles', 'Paul Simonis', '2024-06-01'),
        ('Heerenveen', 'Robin van Persie', '2024-06-01'),
        ('Fortuna Sittard', 'Danny Buijs', '2024-06-01'),
        ('NEC Nijmegen', 'Rogier Meijer', '2021-06-01'),
        ('PEC Zwolle', 'Johnny Jansen', '2024-06-01'),
        ('Willem II', 'Peter Maes', '2024-06-01'),
        ('Heracles', 'Erwin van de Looi', '2024-06-01'),
        ('NAC Breda', 'Carl Hoefkens', '2024-06-01'),
        ('Almere City', 'Hedwiges Maduro', '2024-06-01'),
        ('RKC Waalwijk', 'Henk Fraser', '2024-06-01'),
        ('Groningen', 'Dick Lukkien', '2024-06-01'),
    ],
    
    # ═══════════════════════════════════════════════════════════
    # PRIMEIRA LIGA (PORTUGAL)
    # ═══════════════════════════════════════════════════════════
    'Primeira Liga': [
        ('Sporting CP', 'Ruben Amorim', '2020-03-01'),  # Parti à Man United
        ('Sporting CP', 'Joao Pereira', '2024-11-01'),
        ('Benfica', 'Bruno Lage', '2024-06-01'),
        ('FC Porto', 'Vitor Bruno', '2024-06-01'),
        ('Sporting Braga', 'Carlos Carvalhal', '2024-06-01'),
        ('Vitoria Guimaraes', 'Rui Borges', '2024-06-01'),
        ('Famalicao', 'Hugo Oliveira', '2024-06-01'),
        ('Casa Pia', 'Joao Pereira', '2024-06-01'),
        ('Rio Ave', 'Luis Freire', '2024-06-01'),
        ('Moreirense', 'Cesar Peixoto', '2024-06-01'),
        ('Santa Clara', 'Vasco Matos', '2024-06-01'),
        ('Estoril', 'Ian Cathro', '2024-06-01'),
        ('Arouca', 'Vasco Seabra', '2024-06-01'),
        ('Boavista', 'Cristiano Bacci', '2024-06-01'),
        ('Gil Vicente', 'Bruno Pinheiro', '2024-06-01'),
        ('Nacional', 'Tiago Margarido', '2024-06-01'),
        ('Farense', 'Jose Mota', '2024-06-01'),
        ('Estrela Amadora', 'Jose Faria', '2024-06-01'),
    ],
    
    # ═══════════════════════════════════════════════════════════
    # CHAMPIONSHIP (ANGLETERRE D2)
    # ═══════════════════════════════════════════════════════════
    'Championship': [
        ('Leeds United', 'Daniel Farke', '2023-07-01'),
        ('Sheffield United', 'Chris Wilder', '2024-06-01'),
        ('Burnley', 'Scott Parker', '2024-06-01'),
        ('Sunderland', 'Regis Le Bris', '2024-06-01'),
        ('West Brom', 'Carlos Corberan', '2022-10-01'),
        ('Middlesbrough', 'Michael Carrick', '2022-10-01'),
        ('Norwich City', 'Johannes Hoff Thorup', '2024-06-01'),
        ('Blackburn', 'John Eustace', '2024-06-01'),
        ('Watford', 'Tom Cleverley', '2024-06-01'),
        ('Bristol City', 'Liam Manning', '2024-06-01'),
        ('Millwall', 'Neil Harris', '2024-06-01'),
        ('Coventry', 'Frank Lampard', '2024-12-01'),
        ('Swansea', 'Luke Williams', '2024-06-01'),
        ('QPR', 'Marti Cifuentes', '2023-12-01'),
        ('Stoke City', 'Narcis Pelach', '2024-09-01'),
        ('Derby County', 'Paul Warne', '2023-06-01'),
        ('Preston', 'Paul Heckingbottom', '2024-08-01'),
        ('Hull City', 'Ruben Selles', '2024-10-01'),
        ('Oxford United', 'Des Buckingham', '2024-06-01'),
        ('Sheffield Wednesday', 'Danny Rohl', '2023-10-01'),
        ('Portsmouth', 'John Mousinho', '2023-01-01'),
        ('Luton Town', 'Rob Edwards', '2022-11-01'),
        ('Cardiff', 'Omer Riza', '2024-09-01'),
        ('Plymouth', 'Wayne Rooney', '2024-05-01'),
    ],
    
    # ═══════════════════════════════════════════════════════════
    # SERIE B (ITALIE D2)
    # ═══════════════════════════════════════════════════════════
    'Serie B': [
        ('Sassuolo', 'Fabio Grosso', '2024-06-01'),
        ('Pisa', 'Filippo Inzaghi', '2024-06-01'),
        ('Spezia', "Luca D'Angelo", '2024-06-01'),
        ('Cremonese', 'Giovanni Stroppa', '2024-06-01'),
        ('Bari', 'Moreno Longo', '2024-06-01'),
        ('Palermo', 'Alessio Dionisi', '2024-06-01'),
        ('Catanzaro', 'Fabio Caserta', '2024-06-01'),
        ('Sampdoria', 'Leonardo Semplici', '2024-06-01'),
        ('Cesena', 'Michele Mignani', '2024-06-01'),
        ('Modena', 'Paolo Mandelli', '2024-06-01'),
        ('Brescia', 'Maran Rolando', '2024-06-01'),
        ('Mantova', 'Davide Possanzini', '2024-06-01'),
        ('Reggiana', 'William Viali', '2024-06-01'),
        ('Carrarese', 'Antonio Calabro', '2024-06-01'),
        ('Sudtirol', 'Federico Valente', '2024-06-01'),
        ('Salernitana', 'Roberto Breda', '2024-11-01'),
        ('Frosinone', 'Leandro Greco', '2024-11-01'),
        ('Cosenza', 'Massimiliano Alvini', '2024-06-01'),
        ('Juve Stabia', 'Guido Pagliuca', '2024-06-01'),
        ('Cittadella', 'Alessandro Dal Canto', '2024-06-01'),
    ],
    
    # ═══════════════════════════════════════════════════════════
    # 2. BUNDESLIGA (ALLEMAGNE D2)
    # ═══════════════════════════════════════════════════════════
    '2. Bundesliga': [
        ('Fortuna Dusseldorf', 'Daniel Thioune', '2024-06-01'),
        ('1. FC Kaiserslautern', 'Markus Anfang', '2024-06-01'),
        ('Hamburger SV', 'Steffen Baumgart', '2024-06-01'),
        ('Hannover 96', 'Stefan Leitl', '2024-06-01'),
        ('1. FC Cologne', 'Gerhard Struber', '2024-06-01'),
        ('Karlsruher SC', 'Christian Eichner', '2024-06-01'),
        ('SC Paderborn', 'Lukas Kwasniok', '2024-06-01'),
        ('SpVgg Greuther Furth', 'Jan Siewert', '2024-06-01'),
        ('Hertha Berlin', 'Cristian Fiel', '2024-06-01'),
        ('SV Darmstadt', 'Florian Kohfeldt', '2024-06-01'),
        ('Preussen Munster', 'Sascha Hildmann', '2024-06-01'),
        ('SV Elversberg', 'Horst Steffen', '2024-06-01'),
        ('FC Schalke 04', 'Kees van Wonderen', '2024-10-01'),
        ('1. FC Magdeburg', 'Christian Titz', '2024-06-01'),
        ('1. FC Nurnberg', 'Miroslav Klose', '2024-06-01'),
        ('Eintracht Braunschweig', 'Daniel Scherning', '2024-06-01'),
        ('SSV Ulm', 'Thomas Woerle', '2024-06-01'),
        ('SSV Jahn Regensburg', 'Andreas Patz', '2024-06-01'),
    ],
    
    # ═══════════════════════════════════════════════════════════
    # LA LIGA 2 (ESPAGNE D2)
    # ═══════════════════════════════════════════════════════════
    'La Liga 2': [
        ('Racing Santander', 'Jose Alberto', '2024-06-01'),
        ('Almeria', 'Rubi', '2024-06-01'),
        ('Levante', 'Julien Lopetegui', '2024-06-01'),
        ('Eibar', 'Joseba Etxeberria', '2024-06-01'),
        ('Huesca', 'Antonio Hidalgo', '2024-06-01'),
        ('Oviedo', 'Luis Carrion', '2024-06-01'),
        ('Granada', 'Guille Abascal', '2024-06-01'),
        ('Deportivo', 'Oscar Gilsanz', '2024-06-01'),
        ('Sporting Gijon', 'Ruben Albes', '2024-06-01'),
        ('Elche', 'Eder Sarabia', '2024-06-01'),
        ('Zaragoza', 'Victor Fernandez', '2024-06-01'),
        ('Burgos', 'Jon Perez Bolo', '2024-06-01'),
        ('Racing Ferrol', 'Cristobal Parralo', '2024-06-01'),
        ('Tenerife', 'Alvaro Cervera', '2024-06-01'),
        ('Cordoba', 'Ivan Ania', '2024-06-01'),
        ('Albacete', 'Alberto Gonzalez', '2024-06-01'),
        ('Malaga', 'Sergio Pellicer', '2024-06-01'),
        ('Mirandes', 'Alessio Lisci', '2024-06-01'),
        ('Castellon', 'Dick Schreuder', '2024-06-01'),
        ('Cartagena', 'Abelardo', '2024-06-01'),
    ],
}


def insert_extended_coaches():
    """Insère les coaches des ligues étendues"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    total_inserted = 0
    total_updated = 0
    
    for league, coaches in EXTENDED_COACHES.items():
        logger.info(f"📋 Processing {league} ({len(coaches)} coaches)")
        
        for team, coach, start_date in coaches:
            try:
                cur.execute("""
                    INSERT INTO coach_team_mapping (team_name, coach_name, league, contract_start, is_verified)
                    VALUES (%s, %s, %s, %s, true)
                    ON CONFLICT (team_name, league) 
                    DO UPDATE SET 
                        coach_name = EXCLUDED.coach_name,
                        contract_start = EXCLUDED.contract_start,
                        updated_at = NOW()
                    RETURNING (xmax = 0) as inserted
                """, (team, coach, league, start_date))
                
                result = cur.fetchone()
                if result and result[0]:
                    total_inserted += 1
                else:
                    total_updated += 1
                    
            except Exception as e:
                logger.error(f"Error inserting {team}: {e}")
                conn.rollback()
                continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"✅ Done: {total_inserted} inserted, {total_updated} updated")
    return total_inserted, total_updated


def update_coach_intelligence():
    """Met à jour coach_intelligence avec les nouvelles ligues"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer tous les coaches du mapping
    cur.execute("SELECT * FROM coach_team_mapping WHERE is_verified = true")
    coaches = cur.fetchall()
    
    logger.info(f"🔄 Updating intelligence for {len(coaches)} coaches")
    
    for coach in coaches:
        try:
            # Chercher les stats depuis match_results
            cur.execute("""
                SELECT 
                    COUNT(*) as matches,
                    SUM(CASE WHEN outcome = 'home' THEN 1 ELSE 0 END) as home_wins,
                    AVG(score_home) as avg_gf,
                    AVG(score_away) as avg_ga
                FROM match_results
                WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                AND commence_time >= NOW() - INTERVAL '6 months'
            """, (f"%{coach['team_name']}%", f"%{coach['team_name']}%"))
            
            stats = cur.fetchone()
            
            if stats and stats['matches'] and stats['matches'] >= 3:
                matches = int(stats['matches'])
                win_rate = round(float(stats['home_wins'] or 0) / matches * 100, 1)
                avg_gf = round(float(stats['avg_gf'] or 1.3), 2)
                avg_ga = round(float(stats['avg_ga'] or 1.3), 2)
                
                # Déterminer le style
                if avg_gf > 2.0 and avg_ga < 1.0:
                    style = 'dominant_offensive'
                elif avg_gf > 1.8:
                    style = 'offensive'
                elif avg_ga < 1.0:
                    style = 'defensive'
                elif avg_ga < 0.8:
                    style = 'ultra_defensive'
                else:
                    style = 'balanced'
                
                # Upsert dans coach_intelligence
                cur.execute("""
                    INSERT INTO coach_intelligence (
                        coach_name, current_team, league,
                        career_matches, career_win_rate,
                        avg_goals_per_match, avg_goals_conceded_per_match,
                        tactical_style, is_reliable, last_computed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (coach_name, current_team)
                    DO UPDATE SET
                        career_matches = EXCLUDED.career_matches,
                        career_win_rate = EXCLUDED.career_win_rate,
                        avg_goals_per_match = EXCLUDED.avg_goals_per_match,
                        avg_goals_conceded_per_match = EXCLUDED.avg_goals_conceded_per_match,
                        tactical_style = EXCLUDED.tactical_style,
                        is_reliable = EXCLUDED.is_reliable,
                        last_computed_at = NOW()
                """, (
                    coach['coach_name'], coach['team_name'], coach['league'],
                    matches, win_rate, avg_gf, avg_ga, style, matches >= 5
                ))
        except Exception as e:
            logger.error(f"Error updating {coach['coach_name']}: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("✅ Coach intelligence updated")


if __name__ == "__main__":
    logger.info("🧠 COACH INTELLIGENCE UPDATER V2.0")
    logger.info("=" * 50)
    
    # 1. Insérer les coaches étendus
    inserted, updated = insert_extended_coaches()
    
    # 2. Mettre à jour l'intelligence
    update_coach_intelligence()
    
    logger.info("✅ Update complete!")

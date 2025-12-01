#!/usr/bin/env python3
"""
🎯 STYLES MANUELS EXPERTS - Basés sur la connaissance football réelle
Ces styles seront écrasés par l'algorithme quand il y aura assez de données (≥5 matchs)
"""
import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('ManualStyles')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# STYLES EXPERTS BASÉS SUR LA RÉALITÉ 2024/25
EXPERT_STYLES = {
    # === DOMINANT OFFENSIVE (Les machines à buts) ===
    'Liverpool': ('Arne Slot', 'dominant_offensive', 2.5, 0.8),
    'FC Bayern München': ('Vincent Kompany', 'dominant_offensive', 3.0, 1.2),
    'Barcelona': ('Hansi Flick', 'dominant_offensive', 2.8, 1.3),
    'Manchester City': ('Pep Guardiola', 'dominant_offensive', 2.5, 1.0),
    'Paris Saint-Germain': ('Luis Enrique', 'dominant_offensive', 2.5, 0.9),
    'Real Madrid': ('Carlo Ancelotti', 'dominant_offensive', 2.3, 1.0),
    'Inter': ('Simone Inzaghi', 'dominant_offensive', 2.2, 0.8),
    'Arsenal': ('Mikel Arteta', 'dominant_offensive', 2.3, 0.7),
    'Bayer 04 Leverkusen': ('Xabi Alonso', 'dominant_offensive', 2.5, 1.1),
    
    # === OFFENSIVE (Bons attaquants) ===
    'Chelsea': ('Enzo Maresca', 'offensive', 2.0, 1.2),
    'Borussia Dortmund': ('Nuri Sahin', 'attacking_vulnerable', 2.2, 1.5),
    'Tottenham': ('Ange Postecoglou', 'attacking_vulnerable', 2.0, 1.5),
    'Marseille': ('Roberto De Zerbi', 'offensive', 2.2, 1.2),
    'Monaco': ('Adi Hutter', 'attacking_vulnerable', 1.8, 1.5),
    'Aston Villa': ('Unai Emery', 'offensive', 1.8, 1.0),
    'Newcastle United': ('Eddie Howe', 'offensive', 1.8, 1.1),
    'Napoli': ('Antonio Conte', 'defensive', 1.5, 0.7),
    'Juventus': ('Thiago Motta', 'defensive', 1.4, 0.8),
    'AC Milan': ('Paulo Fonseca', 'offensive', 1.7, 1.3),
    'Atalanta': ('Gian Piero Gasperini', 'attacking_vulnerable', 2.3, 1.4),
    'Bologna': ('Vincenzo Italiano', 'offensive', 1.8, 1.0),
    'Fiorentina': ('Raffaele Palladino', 'balanced', 1.4, 1.2),
    'Lazio': ('Marco Baroni', 'offensive', 1.8, 1.1),
    'Roma': ('Claudio Ranieri', 'defensive', 1.2, 0.9),
    'Lyon': ('Pierre Sage', 'offensive', 1.9, 1.2),
    'Lille': ('Bruno Genesio', 'offensive', 1.7, 0.9),
    'Lens': ('Will Still', 'offensive', 1.6, 0.9),
    'Rennes': ('Jorge Sampaoli', 'attacking_vulnerable', 1.8, 1.4),
    'VfB Stuttgart': ('Sebastian Hoeness', 'attacking_vulnerable', 2.0, 1.4),
    'RB Leipzig': ('Marco Rose', 'offensive', 1.9, 1.1),
    'Eintracht Frankfurt': ('Dino Toppmoller', 'attacking_vulnerable', 2.0, 1.6),
    'Hoffenheim': ('Christian Ilzer', 'attacking_vulnerable', 2.0, 1.5),
    'Villarreal': ('Marcelino', 'offensive', 1.7, 1.1),
    'Athletic Club': ('Ernesto Valverde', 'defensive', 1.3, 0.9),
    'Real Sociedad': ('Imanol Alguacil', 'balanced', 1.4, 1.2),
    'Real Betis': ('Manuel Pellegrini', 'offensive', 1.6, 1.1),
    'Sevilla': ('Garcia Pimienta', 'balanced', 1.3, 1.3),
    
    # === DEFENSIVE (Solides derrière) ===
    'Atlético de Madrid': ('Diego Simeone', 'defensive', 1.5, 0.8),
    'Brighton': ('Fabian Hurzeler', 'offensive', 1.6, 1.1),
    'Fulham': ('Marco Silva', 'balanced', 1.3, 1.2),
    'Crystal Palace': ('Oliver Glasner', 'defensive', 1.2, 1.0),
    'Brentford': ('Thomas Frank', 'attacking_vulnerable', 1.8, 1.5),
    'West Ham': ('Julen Lopetegui', 'balanced', 1.2, 1.4),
    'Bournemouth': ('Andoni Iraola', 'attacking_vulnerable', 1.7, 1.5),
    'Everton': ('Sean Dyche', 'defensive', 0.9, 1.1),
    'Nottingham Forest': ('Nuno Espirito Santo', 'defensive', 1.2, 0.9),
    'Manchester United': ('Ruben Amorim', 'balanced', 1.4, 1.3),
    
    # === STRUGGLING (En difficulté) ===
    'Valencia': ('Ruben Baraja', 'struggling', 0.9, 1.6),
    'Wolverhampton': ('Gary ONeil', 'struggling', 0.8, 1.8),
    'Southampton': ('Russell Martin', 'struggling', 0.9, 2.0),
    'Ipswich': ('Kieran McKenna', 'struggling', 0.8, 1.7),
    'Leicester': ('Steve Cooper', 'struggling', 1.0, 1.8),
    'Girona': ('Michel', 'struggling', 1.0, 1.6),
    'Valladolid': ('Paulo Pezzolano', 'struggling', 0.8, 1.5),
    'Lecce': ('Marco Giampaolo', 'struggling', 0.9, 1.5),
    'Verona': ('Paolo Zanetti', 'struggling', 0.8, 1.7),
    'Monza': ('Alessandro Nesta', 'struggling', 0.7, 1.4),
    'Venezia': ('Eusebio Di Francesco', 'struggling', 0.9, 1.8),
    'Parma': ('Fabio Pecchia', 'defensive_weak', 0.9, 1.3),
    'Como': ('Cesc Fabregas', 'balanced', 1.2, 1.4),
    'Cagliari': ('Davide Nicola', 'balanced', 1.0, 1.3),
    'Empoli': ('Roberto DAversa', 'defensive_weak', 0.9, 1.0),
    'Torino': ('Paolo Vanoli', 'struggling', 1.0, 1.7),
    'Genoa': ('Patrick Vieira', 'balanced', 1.0, 1.3),
    'Udinese': ('Kosta Runjaic', 'balanced', 1.1, 1.4),
    'Le Havre': ('Didier Digard', 'struggling', 0.8, 1.5),
    'Nantes': ('Antoine Kombouare', 'struggling', 0.9, 1.5),
    'Angers': ('Alexandre Dujeux', 'defensive_weak', 0.9, 1.2),
    'Montpellier': ('Jean-Louis Gasset', 'struggling', 0.7, 1.8),
    'Auxerre': ('Christophe Pelissier', 'defensive_weak', 0.8, 1.2),
    'Saint-Etienne': ('Olivier Dall Oglio', 'struggling', 0.9, 1.6),
    'Reims': ('Luka Elsner', 'balanced', 1.1, 1.2),
    'Toulouse': ('Carles Martinez', 'balanced', 1.3, 1.3),
    'Strasbourg': ('Liam Rosenior', 'attacking_vulnerable', 1.7, 1.5),
    'Brest': ('Eric Roy', 'balanced', 1.3, 1.4),
    'Nice': ('Franck Haise', 'balanced', 1.2, 1.3),
    
    # === DEFENSIVE_WEAK (Marque peu mais tient) ===
    'Getafe': ('Pepe Bordalas', 'defensive_weak', 0.9, 1.0),
    'Rayo Vallecano': ('Inigo Perez', 'defensive_weak', 0.9, 1.1),
    'Osasuna': ('Vicente Moreno', 'defensive_weak', 1.0, 1.2),
    'Alaves': ('Eduardo Coudet', 'defensive_weak', 0.9, 1.2),
    'Espanyol': ('Manolo Gonzalez', 'defensive_weak', 1.0, 1.1),
    'Mallorca': ('Jagoba Arrasate', 'defensive', 1.1, 1.1),
    'Celta Vigo': ('Claudio Giraldez', 'attacking_vulnerable', 1.6, 1.8),
    'Las Palmas': ('Diego Martinez', 'balanced', 1.1, 1.3),
    
    # === BUNDESLIGA 2 / Autres ===
    'FC St. Pauli': ('Alexander Blessin', 'struggling', 0.8, 1.8),
    'Holstein Kiel': ('Marcel Rapp', 'struggling', 0.9, 2.0),
    'Heidenheim': ('Frank Schmidt', 'struggling', 1.0, 1.8),
    'Mainz': ('Bo Henriksen', 'balanced', 1.2, 1.5),
    'Werder Bremen': ('Ole Werner', 'balanced', 1.2, 1.4),
    'Union Berlin': ('Bo Svensson', 'defensive', 1.1, 1.2),
    'Augsburg': ('Jess Thorup', 'balanced', 1.2, 1.6),
    'Freiburg': ('Julian Schuster', 'offensive', 1.6, 1.3),
    'Wolfsburg': ('Ralph Hasenhuttl', 'balanced', 1.2, 1.4),
    'Monchengladbach': ('Gerardo Seoane', 'balanced', 1.3, 1.4),
}


def apply_expert_styles():
    """Applique les styles experts à la DB"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    updated = 0
    not_found = []
    
    for team, (coach, style, gf, ga) in EXPERT_STYLES.items():
        # Chercher le coach dans la DB
        cur.execute("""
            UPDATE coach_intelligence
            SET tactical_style = %s,
                avg_goals_per_match = %s,
                avg_goals_conceded_per_match = %s,
                is_reliable = FALSE
            WHERE current_team ILIKE %s
            RETURNING coach_name
        """, (style, gf, ga, f"%{team}%"))
        
        result = cur.fetchone()
        if result:
            updated += 1
            logger.info(f"✅ {team} ({result[0]}): {style} (GF={gf}, GA={ga})")
        else:
            not_found.append(team)
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"\n🎯 {updated} coaches mis à jour avec styles experts")
    if not_found:
        logger.info(f"⚠️ Non trouvés: {not_found[:10]}...")
    
    return updated


if __name__ == "__main__":
    logger.info("🎯 APPLICATION DES STYLES EXPERTS")
    logger.info("=" * 60)
    apply_expert_styles()

#!/usr/bin/env python3
"""Ajouter mapping de styles pour tactical_matrix"""

# Lire le fichier
with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Ancien code
old_code = '''    def _get_tactical_match(self, style_a: str, style_b: str) -> Optional[Dict]:
        """Récupère tactical_matrix"""
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT
                        style_a, style_b,
                        btts_probability, over_25_probability,
                        avg_goals_total, sample_size, confidence_level
                    FROM tactical_matrix
                    WHERE LOWER(style_a) = %s AND LOWER(style_b) = %s
                    LIMIT 1
                """, (style_a.lower(), style_b.lower()))'''

# Nouveau code avec style mapping
new_code = '''    def _get_tactical_match(self, style_a: str, style_b: str) -> Optional[Dict]:
        """Récupère tactical_matrix"""
        if not self.conn:
            return None
        
        # Mapping des styles vers ceux disponibles dans tactical_matrix
        STYLE_MAP = {
            'balanced_defensive': 'defensive',
            'balanced_offensive': 'attacking',
            'ultra_defensive': 'park_the_bus',
            'ultra_offensive': 'attacking',
            'offensive': 'attacking',
            'high_pressing': 'high_press',
        }
        
        style_a = STYLE_MAP.get(style_a.lower(), style_a.lower())
        style_b = STYLE_MAP.get(style_b.lower(), style_b.lower())
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT
                        style_a, style_b,
                        btts_probability, over_25_probability,
                        avg_goals_total, sample_size, confidence_level
                    FROM tactical_matrix
                    WHERE LOWER(style_a) = %s AND LOWER(style_b) = %s
                    LIMIT 1
                """, (style_a, style_b))'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.write(content)
    print("OK - Style mapping ajouté")
else:
    print("Code non trouvé - vérification manuelle")

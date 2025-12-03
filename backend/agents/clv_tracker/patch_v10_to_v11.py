#!/usr/bin/env python3
"""
Patch V10 -> V10.1 (préparation V11)
- Game State Dynamics dans Monte Carlo
- Spread/Liquidité dans Steam Detection
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# ============================================================
# 1. GAME STATE DYNAMICS - Améliorer Monte Carlo
# ============================================================

old_mc = '''    def _simulate_single_match(self, home_xg: float, away_xg: float,
                                home_var: float, away_var: float,
                                context: Dict = None) -> Tuple[int, int]:
        """
        Simule un seul match minute par minute

        Events possibles:
        - But (basé sur xG)
        - Carton rouge (réduit xG équipe)
        - Momentum shift (après but)
        """

        context = context or {}

        # xG par minute (90 minutes)
        home_xg_per_min = home_xg / 90
        away_xg_per_min = away_xg / 90

        home_goals = 0
        away_goals = 0
        home_red = False
        away_red = False

        # Facteur momentum (change après chaque but)
        home_momentum = 1.0
        away_momentum = 1.0

        for minute in range(1, 91):
            # Vérifier carton rouge (rare)
            if not home_red and random.random() < self.config['red_card_prob'] / 90:
                home_red = True
                home_xg_per_min *= 0.7  # -30% après rouge

            if not away_red and random.random() < self.config['red_card_prob'] / 90:
                away_red = True
                away_xg_per_min *= 0.7

            # Calculer probabilité de but cette minute
            # Utiliser distribution Poisson modifiée avec variance
            home_prob = home_xg_per_min * home_momentum * (1 + random.gauss(0, home_var))
            away_prob = away_xg_per_min * away_momentum * (1 + random.gauss(0, away_var))

            # But domicile ?
            if random.random() < max(0, home_prob):
                home_goals += 1
                # Momentum shift
                home_momentum *= (1 + self.config['momentum_shift_factor'])
                away_momentum *= (1 - self.config['momentum_shift_factor'] * 0.5)

            # But extérieur ?
            if random.random() < max(0, away_prob):
                away_goals += 1
                away_momentum *= (1 + self.config['momentum_shift_factor'])
                home_momentum *= (1 - self.config['momentum_shift_factor'] * 0.5)

            # Decay momentum vers 1.0
            home_momentum = 1.0 + (home_momentum - 1.0) * 0.98
            away_momentum = 1.0 + (away_momentum - 1.0) * 0.98

        return home_goals, away_goals'''

new_mc = '''    def _simulate_single_match(self, home_xg: float, away_xg: float,
                                home_var: float, away_var: float,
                                context: Dict = None) -> Tuple[int, int]:
        """
        Simule un seul match minute par minute avec Game State Dynamics

        Events possibles:
        - But (basé sur xG)
        - Carton rouge (réduit xG équipe)
        - Momentum shift (après but)
        - Game State adjustment (équipe qui mène se replie)
        """

        context = context or {}

        # xG de base par minute (90 minutes)
        base_home_xg_per_min = home_xg / 90
        base_away_xg_per_min = away_xg / 90

        home_goals = 0
        away_goals = 0
        home_red = False
        away_red = False

        # Facteur momentum (change après chaque but)
        home_momentum = 1.0
        away_momentum = 1.0

        for minute in range(1, 91):
            # ═══════════════════════════════════════════════════════
            # GAME STATE DYNAMICS - Ajuster selon le score et le temps
            # ═══════════════════════════════════════════════════════
            goal_diff = home_goals - away_goals
            time_factor = minute / 90  # 0.0 -> 1.0
            
            # Facteurs Game State
            home_gs_factor = 1.0
            away_gs_factor = 1.0
            
            if minute >= 60:  # Dernière demi-heure = tactiques changent
                if goal_diff >= 2:
                    # Home mène largement -> se replie, Away pousse
                    home_gs_factor = 0.7  # Home défend
                    away_gs_factor = 1.4  # Away attaque désespérément
                elif goal_diff == 1:
                    # Home mène d'1 but -> léger repli
                    home_gs_factor = 0.85
                    away_gs_factor = 1.2
                elif goal_diff == -1:
                    # Home est mené -> pousse
                    home_gs_factor = 1.2
                    away_gs_factor = 0.85
                elif goal_diff <= -2:
                    # Home est mené largement -> pousse fort
                    home_gs_factor = 1.4
                    away_gs_factor = 0.7
            
            elif minute >= 75:  # 15 dernières minutes = intensité max
                if goal_diff >= 1:
                    home_gs_factor = 0.6  # Park the bus
                    away_gs_factor = 1.5  # All out attack
                elif goal_diff <= -1:
                    home_gs_factor = 1.5
                    away_gs_factor = 0.6

            # xG ajusté pour cette minute
            home_xg_per_min = base_home_xg_per_min * home_gs_factor
            away_xg_per_min = base_away_xg_per_min * away_gs_factor

            # Vérifier carton rouge (rare)
            if not home_red and random.random() < self.config['red_card_prob'] / 90:
                home_red = True
                home_xg_per_min *= 0.7  # -30% après rouge

            if not away_red and random.random() < self.config['red_card_prob'] / 90:
                away_red = True
                away_xg_per_min *= 0.7

            # Calculer probabilité de but cette minute
            home_prob = home_xg_per_min * home_momentum * (1 + random.gauss(0, home_var))
            away_prob = away_xg_per_min * away_momentum * (1 + random.gauss(0, away_var))

            # But domicile ?
            if random.random() < max(0, home_prob):
                home_goals += 1
                home_momentum *= (1 + self.config['momentum_shift_factor'])
                away_momentum *= (1 - self.config['momentum_shift_factor'] * 0.5)

            # But extérieur ?
            if random.random() < max(0, away_prob):
                away_goals += 1
                away_momentum *= (1 + self.config['momentum_shift_factor'])
                home_momentum *= (1 - self.config['momentum_shift_factor'] * 0.5)

            # Decay momentum vers 1.0
            home_momentum = 1.0 + (home_momentum - 1.0) * 0.98
            away_momentum = 1.0 + (away_momentum - 1.0) * 0.98

        return home_goals, away_goals'''

if old_mc in content:
    content = content.replace(old_mc, new_mc)
    print("✅ 1. Game State Dynamics ajouté au Monte Carlo")
else:
    print("❌ 1. Monte Carlo pattern non trouvé")

# ============================================================
# 2. SPREAD/LIQUIDITÉ - Améliorer Steam Detection
# ============================================================

old_steam = '''    def _detect_steam(self, odds_list: List[Dict]) -> Tuple[bool, str, float]:
        """
        Détecte un mouvement steam (sharp money)
        Steam = mouvement > 3% en < 4h
        """
        if len(odds_list) < 2:
            return False, "", 0.0

        now = datetime.now()
        window = timedelta(hours=self.config['steam_time_window_hours'])

        # Filtrer les cotes récentes
        recent = [o for o in odds_list
                  if o['timestamp'] and now - o['timestamp'] < window]

        if len(recent) < 2:
            return False, "", 0.0

        first_recent = recent[0]['odds']
        last_recent = recent[-1]['odds']

        movement_pct = (last_recent - first_recent) / first_recent * 100

        if abs(movement_pct) >= self.config['steam_threshold_pct']:
            direction = 'shortening' if movement_pct < 0 else 'drifting'
            return True, direction, abs(movement_pct)

        return False, "", 0.0'''

new_steam = '''    def _detect_steam(self, odds_list: List[Dict]) -> Tuple[bool, str, float]:
        """
        Détecte un mouvement steam (sharp money) avec pondération par liquidité
        
        V10.1 Upgrade:
        - Calcule le spread (proxy de liquidité)
        - Spread < 3% = marché liquide = signal FORT
        - Spread > 7% = marché illiquide = ignorer le bruit
        """
        if len(odds_list) < 2:
            return False, "", 0.0

        now = datetime.now()
        window = timedelta(hours=self.config['steam_time_window_hours'])

        # Filtrer les cotes récentes
        recent = [o for o in odds_list
                  if o.get('timestamp') and now - o['timestamp'] < window]

        if len(recent) < 2:
            return False, "", 0.0

        first_recent = recent[0]['odds']
        last_recent = recent[-1]['odds']

        movement_pct = (last_recent - first_recent) / first_recent * 100

        # ═══════════════════════════════════════════════════════
        # SPREAD/LIQUIDITÉ - Calculer l'importance du signal
        # ═══════════════════════════════════════════════════════
        steam_importance = 1.0
        
        # Calculer spread si on a les 3 cotes (1X2)
        last_record = recent[-1]
        home_odds = last_record.get('home_odds')
        draw_odds = last_record.get('draw_odds') 
        away_odds = last_record.get('away_odds')
        
        if home_odds and draw_odds and away_odds:
            try:
                spread = (1/float(home_odds) + 1/float(draw_odds) + 1/float(away_odds)) - 1
                
                if spread < 0.03:
                    # Marché très liquide (Pinnacle, jour de match)
                    steam_importance = 1.5  # Signal FORT
                elif spread < 0.05:
                    # Marché moyennement liquide
                    steam_importance = 1.0  # Signal normal
                elif spread < 0.07:
                    # Marché peu liquide
                    steam_importance = 0.7  # Signal faible
                else:
                    # Marché très illiquide (petits bookies)
                    steam_importance = 0.3  # Quasi-ignoré
            except (ValueError, ZeroDivisionError):
                steam_importance = 1.0

        # Ajuster le seuil selon la liquidité
        adjusted_threshold = self.config['steam_threshold_pct'] / steam_importance
        
        if abs(movement_pct) >= adjusted_threshold:
            direction = 'shortening' if movement_pct < 0 else 'drifting'
            # Retourner le mouvement ajusté par l'importance
            adjusted_movement = abs(movement_pct) * steam_importance
            return True, direction, adjusted_movement

        return False, "", 0.0'''

if old_steam in content:
    content = content.replace(old_steam, new_steam)
    print("✅ 2. Spread/Liquidité ajouté au Steam Detection")
else:
    print("❌ 2. Steam Detection pattern non trouvé")

# Sauvegarder
with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n✅ Patch V10.1 appliqué!")

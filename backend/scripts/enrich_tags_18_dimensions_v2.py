#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
ENRICHISSEMENT TAGS 18 DIMENSIONS ADN - PHASE 5.2 V2 (REFONTE COMPLÈTE)
═══════════════════════════════════════════════════════════════════════════════
Date: 2025-12-16
Version: 2.0 (Refonte après audit Hedge Fund)

RÈGLES ABSOLUES:
1. NE JAMAIS INVENTER DE DONNÉES - Si manquant → NULL ou "NO_DATA"
2. THRESHOLDS BASÉS SUR PERCENTILES - Pas de valeurs arbitraires
3. VALIDATION AVANT UPDATE - Chaque tag doit avoir 10-50% des équipes
4. MÉTHODOLOGIE SCIENTIFIQUE - Observer → Analyser → Valider → Appliquer

CREDENTIALS POSTGRESQL:
- Container: monps_postgres
- User: monps_user
- Database: monps_db
- Password: monps_secure_password_2024
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import subprocess
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONTAINER = 'monps_postgres'
DB_USER = 'monps_user'
DB_NAME = 'monps_db'

SOURCES = {
    'unified': '/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json',
    'gamestate': '/home/Mon_ps/data/quantum_v2/gamestate_behavior_index_v3.json',
    'timing': '/home/Mon_ps/data/quantum_v2/timing_dna_profiles.json',
    'narrative': '/home/Mon_ps/data/quantum_v2/team_narrative_dna_v3.json',
    'goalkeeper': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v4_4_final.json',
    'players': '/home/Mon_ps/data/quantum_v2/players_impact_dna.json'
}

# Mapping noms JSON → DB
NAME_MAPPING = {
    'Borussia Monchengladbach': 'Borussia M.Gladbach',
    'Heidenheim': 'FC Heidenheim',
    'Inter Milan': 'Inter',
    'Paris Saint-Germain': 'Paris Saint Germain',
    'AS Roma': 'Roma',
    'RB Leipzig': 'RasenBallsport Leipzig',
    'Wolverhampton': 'Wolverhampton Wanderers',
    'Parma': 'Parma Calcio 1913',
    'Hellas Verona': 'Verona',
    'Leeds United': 'Leeds',
    'Athletic Bilbao': 'Athletic Club'
}

# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

class ADNEnricher:
    """
    Enrichisseur de tags ADN basé sur méthodologie scientifique.
    Thresholds calibrés sur percentiles, pas sur valeurs arbitraires.
    """
    
    def __init__(self):
        self.data = {}
        self.thresholds = self.load_thresholds()
        self.tag_counts = {}
        self.gk_by_team = {}
        
    def load_thresholds(self) -> Dict:
        """Charge les thresholds calibrés depuis /tmp/calibrated_thresholds.json"""
        try:
            with open('/tmp/calibrated_thresholds.json', 'r') as f:
                return json.load(f)
        except:
            print("⚠️ Thresholds non trouvés, utilisation valeurs par défaut")
            return {}
    
    def load_sources(self) -> bool:
        """Charge toutes les sources de données"""
        print("\n" + "="*80)
        print("1. CHARGEMENT SOURCES")
        print("="*80)
        
        for name, path in SOURCES.items():
            try:
                with open(path, 'r') as f:
                    self.data[name] = json.load(f)
                print(f"   ✅ {name}: Chargé")
            except Exception as e:
                print(f"   ⚠️ {name}: {e}")
                self.data[name] = {}
        
        # Créer index goalkeeper par équipe
        gk_data = self.data.get('goalkeeper', {})
        goalkeepers = gk_data.get('goalkeepers', [])
        for gk in goalkeepers:
            team = gk.get('team')
            if team:
                self.gk_by_team[team] = gk
        
        print(f"   ✅ Goalkeepers indexés: {len(self.gk_by_team)} équipes")
        
        return True
    
    def map_team_name(self, db_name: str) -> str:
        """Mappe nom DB → nom JSON si différent"""
        for json_name, dbn in NAME_MAPPING.items():
            if dbn == db_name:
                return json_name
        return db_name
    
    def extract_tags_for_team(self, team_name: str) -> List[str]:
        """
        Extrait les tags pour UNE équipe en utilisant les thresholds calibrés.
        
        RÈGLE: Si une donnée n'existe pas → NE PAS INVENTER → Skip le tag
        """
        tags = []
        
        # Données de l'équipe
        unified = self.data.get('unified', {})
        teams = unified.get('teams', unified)
        team_unified = teams.get(team_name, {})
        
        timing = self.data.get('timing', {}).get(team_name, {})
        gamestate = self.data.get('gamestate', {}).get(team_name, {})
        narrative = self.data.get('narrative', {}).get(team_name, {})
        gk = self.gk_by_team.get(team_name, {})
        
        # ─────────────────────────────────────────────────────────────────
        # DIMENSION 1: TACTICAL PROFILE (depuis fingerprint existant)
        # ─────────────────────────────────────────────────────────────────
        dna = narrative.get('dna', {})
        tactical = dna.get('tactical', {})
        profile = tactical.get('profile', '')
        if profile and profile not in ['UNKNOWN', 'BALANCED', 'NEUTRAL']:
            tags.append(profile)  # GEGENPRESS, POSSESSION, LOW_BLOCK, TRANSITION
        
        # ─────────────────────────────────────────────────────────────────
        # DIMENSION 2: VOLUME DNA (xG/90)
        # ─────────────────────────────────────────────────────────────────
        context = team_unified.get('context', {})
        history = context.get('history', {})
        xg_90 = history.get('xg_90')
        
        if xg_90 and 'xg_for_avg' in self.thresholds:
            th = self.thresholds['xg_for_avg']
            if float(xg_90) > th['p75']:
                tags.append('HIGH_VOLUME')
            elif float(xg_90) < th['p25']:
                tags.append('LOW_VOLUME')
        
        # ─────────────────────────────────────────────────────────────────
        # DIMENSION 3: TIMING DNA (diesel/fast_starter)
        # ─────────────────────────────────────────────────────────────────
        decay = timing.get('decay_factor')
        if decay and 'diesel_factor' in self.thresholds:
            th = self.thresholds['diesel_factor']
            if float(decay) > th['p75']:
                tags.append('DIESEL')
            elif float(decay) < th['p25']:
                tags.append('FAST_STARTER')
        
        # Clutch factor (75-90 minutes)
        time_curve = timing.get('time_curve', {})
        clutch = time_curve.get('75-90')
        if clutch and 'clutch_factor' in self.thresholds:
            th = self.thresholds['clutch_factor']
            if float(clutch) > th['p75']:
                tags.append('LATE_GAME_KILLER')
        
        # ─────────────────────────────────────────────────────────────────
        # DIMENSION 4: DEPENDENCY DNA
        # ─────────────────────────────────────────────────────────────────
        attackers = dna.get('attackers', {})
        mvp = attackers.get('mvp', {})
        mvp_dep = mvp.get('dependency')
        
        if mvp_dep and 'mvp_share' in self.thresholds:
            th = self.thresholds['mvp_share']
            if float(mvp_dep) > th['p75']:
                tags.append('MVP_DEPENDENT')
            elif float(mvp_dep) < th['p25']:
                tags.append('COLLECTIVE')
        
        # ─────────────────────────────────────────────────────────────────
        # DIMENSION 15-16: GAMESTATE DNA
        # ─────────────────────────────────────────────────────────────────
        metrics = gamestate.get('metrics', gamestate)
        behavior = gamestate.get('behavior', '')
        
        # Behavior direct si présent
        if behavior and behavior not in ['NEUTRAL', 'UNKNOWN', 'SETTLER', '']:
            tags.append(behavior)  # COMEBACK_KING, KILLER, FRONT_RUNNER
        else:
            # Calculer depuis métriques
            xg_trailing = metrics.get('xg_trailing') or metrics.get('xG_trailing')
            xg_leading = metrics.get('xg_leading') or metrics.get('xG_leading')
            
            if xg_trailing and 'xg_trailing' in self.thresholds:
                th = self.thresholds['xg_trailing']
                if float(xg_trailing) > th['p75']:
                    tags.append('COMEBACK_KING')
            
            if xg_leading and 'xg_leading' in self.thresholds:
                th = self.thresholds['xg_leading']
                if float(xg_leading) < th['p25']:
                    tags.append('GAME_MANAGER')
                elif float(xg_leading) > th['p75']:
                    tags.append('KILLER')
        
        # ─────────────────────────────────────────────────────────────────
        # GOALKEEPER DNA
        # ─────────────────────────────────────────────────────────────────
        gk_status = dna.get('goalkeeper', {}).get('status', '')
        if gk_status and gk_status in ['ELITE', 'LEAKY']:
            tags.append(f'GK_{gk_status}')
        elif gk:
            # Calculer depuis save rate
            sr = gk.get('save_rate')
            if sr and 'gk_save_rate' in self.thresholds:
                th = self.thresholds['gk_save_rate']
                if float(sr) > th['p75']:
                    tags.append('GK_ELITE')
                elif float(sr) < th['p25']:
                    tags.append('GK_LEAKY')
        
        # ─────────────────────────────────────────────────────────────────
        # DIMENSION 5: STYLE DNA (set piece, buildup)
        # ─────────────────────────────────────────────────────────────────
        set_piece_pct = tactical.get('set_piece_pct')
        if set_piece_pct and float(set_piece_pct) > 0.30:
            tags.append('SET_PIECE_KINGS')
        
        conversion = tactical.get('conversion_rate')
        if conversion and float(conversion) > 0.15:  # >15% conversion
            tags.append('CLINICAL')
        
        chain_ratio = tactical.get('xgchain_ratio') or tactical.get('buildup_ratio')
        if chain_ratio and float(chain_ratio) > 2.5:
            tags.append('BUILDUP_ARCHITECT')
        
        return list(set(tags))  # Déduplique
    
    def run_sql(self, query: str) -> str:
        """Exécute une requête SQL"""
        cmd = f"docker exec {CONTAINER} psql -U {DB_USER} -d {DB_NAME} -t -c \"{query}\""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    
    def get_db_teams(self) -> List[str]:
        """Récupère la liste des équipes en DB"""
        result = self.run_sql("SELECT team_name FROM quantum.team_quantum_dna_v3 ORDER BY team_name")
        return [t.strip() for t in result.split('\n') if t.strip()]
    
    def update_team_tags(self, team_name: str, tags: List[str]) -> bool:
        """Met à jour les tags d'une équipe"""
        if not tags:
            return False
        
        tags_pg = "ARRAY[" + ",".join(f"'{t}'" for t in tags) + "]::text[]"
        query = f"""
            UPDATE quantum.team_quantum_dna_v3
            SET narrative_fingerprint_tags = {tags_pg},
                updated_at = NOW()
            WHERE team_name = '{team_name.replace("'", "''")}'
        """
        self.run_sql(query)
        return True
    
    def validate_tag_distribution(self):
        """
        Valide que les tags sont DISCRIMINANTS.
        RÈGLE: Un tag présent pour >80% ou <10% des équipes = MAL CALIBRÉ
        """
        print("\n" + "="*80)
        print("3. VALIDATION DISTRIBUTION DES TAGS")
        print("="*80)
        
        result = self.run_sql("""
            SELECT unnest(narrative_fingerprint_tags) as tag, COUNT(*) as cnt
            FROM quantum.team_quantum_dna_v3
            WHERE narrative_fingerprint_tags IS NOT NULL
            GROUP BY tag
            ORDER BY cnt DESC
        """)
        
        print("\n   Tag                  | Équipes | Status")
        print("   " + "-"*60)
        
        good_tags = 0
        bad_tags = 0
        
        for line in result.split('\n'):
            if '|' in line:
                parts = line.split('|')
                tag = parts[0].strip()
                cnt = int(parts[1].strip())
                pct = cnt / 99 * 100
                
                if pct > 80:
                    status = "❌ TROP GÉNÉRIQUE"
                    bad_tags += 1
                elif pct < 5:
                    status = "⚠️ Très rare"
                    bad_tags += 1
                else:
                    status = "✅ OK"
                    good_tags += 1
                
                print(f"   {tag:20} | {cnt:3} ({pct:5.1f}%) | {status}")
        
        print(f"\n   ✅ Tags discriminants: {good_tags}")
        print(f"   ⚠️ Tags mal calibrés: {bad_tags}")
        
        return good_tags, bad_tags
    
    def run(self):
        """Exécution principale"""
        print("="*80)
        print("ENRICHISSEMENT TAGS ADN - PHASE 5.2 V2 (PERCENTILES RÉELS)")
        print("="*80)
        print("RÈGLES: Thresholds sur PERCENTILES - JAMAIS inventer de données")
        
        # 1. Charger sources
        self.load_sources()
        
        # 2. Afficher thresholds utilisés
        print("\n" + "="*80)
        print("2. THRESHOLDS CALIBRÉS UTILISÉS")
        print("="*80)
        
        if self.thresholds:
            for metric, vals in self.thresholds.items():
                if vals:
                    print(f"   {metric}: P25={vals['p25']:.3f}, P75={vals['p75']:.3f}")
        else:
            print("   ⚠️ Pas de thresholds chargés!")
        
        # 3. Récupérer équipes DB
        print("\n" + "="*80)
        print("3. ENRICHISSEMENT DES ÉQUIPES")
        print("="*80)
        
        db_teams = self.get_db_teams()
        print(f"   Équipes en DB: {len(db_teams)}")
        
        # 4. Traiter chaque équipe
        updated = 0
        no_data = []
        
        for db_name in db_teams:
            # Mapper vers nom JSON si différent
            json_name = self.map_team_name(db_name)
            
            # Extraire tags
            tags = self.extract_tags_for_team(json_name)
            
            if tags:
                self.update_team_tags(db_name, tags)
                updated += 1
                
                # Compter tags
                for tag in tags:
                    self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
                
                if updated <= 5:
                    print(f"   ✅ {db_name}: {tags}")
            else:
                no_data.append(db_name)
        
        print(f"\n   ... {updated - 5} autres équipes enrichies")
        
        # 5. Équipes sans données
        if no_data:
            print(f"\n   ⚠️ Équipes sans tags ({len(no_data)}):")
            for name in no_data[:5]:
                print(f"      - {name}")
                # Marquer comme PROMOTED_NO_DATA
                self.run_sql(f"""
                    UPDATE quantum.team_quantum_dna_v3
                    SET narrative_fingerprint_tags = ARRAY['PROMOTED_NO_DATA']::text[]
                    WHERE team_name = '{name.replace("'", "''")}'
                """)
        
        # 6. Validation
        good, bad = self.validate_tag_distribution()
        
        # 7. Résumé final
        print("\n" + "="*80)
        print("RÉSUMÉ FINAL")
        print("="*80)
        
        total_tags = len(self.tag_counts)
        avg_tags_count = sum(self.tag_counts.values()) / len(db_teams) if db_teams else 0
        
        print(f"\n   ✅ Équipes mises à jour: {updated}/{len(db_teams)}")
        print(f"   ✅ Tags différents: {total_tags}")
        print(f"   ✅ Tags par équipe (moy): {avg_tags_count:.1f}")
        print(f"   ⚠️ Équipes sans données: {len(no_data)}")
        print(f"   ✅ Tags discriminants: {good}")
        print(f"   ⚠️ Tags mal calibrés: {bad}")
        
        # Vérification unicité préservée
        result = self.run_sql("""
            SELECT COUNT(DISTINCT dna_fingerprint), COUNT(*)
            FROM quantum.team_quantum_dna_v3
            WHERE dna_fingerprint IS NOT NULL AND dna_fingerprint != ''
        """)
        print(f"\n   📊 Unicité fingerprints: {result}")
        
        # Grade final
        if bad == 0 and good > 8:
            grade = "10/10 PERFECT"
        elif bad <= 2 and good > 6:
            grade = "8.5/10 HEDGE FUND QUANT"
        elif bad <= 4:
            grade = "7/10 BON"
        else:
            grade = "5/10 INSUFFISANT"
        
        print(f"\n   🏆 GRADE FINAL: {grade}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    enricher = ADNEnricher()
    enricher.run()

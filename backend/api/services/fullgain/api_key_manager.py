"""
API Key Manager - Gestion intelligente des 4 clés API
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Gestionnaire intelligent des 4 API Keys
    - 2 clés API-Football (MAIN + BACKUP)
    - 2 clés The Odds API (MAIN + BACKUP)
    """
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'monps_postgres'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
        
        # Les 4 clés (depuis variables d'environnement)
        self.keys = {
            'APIF_MAIN': os.getenv('API_FOOTBALL_KEY_MAIN'),
            'APIF_BACKUP': os.getenv('API_FOOTBALL_KEY_BACKUP'),
            'ODDS_MAIN': os.getenv('ODDS_API_KEY_MAIN'),
            'ODDS_BACKUP': os.getenv('ODDS_API_KEY_BACKUP'),
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def get_key(self, service: str) -> Optional[Dict]:
        """
        Récupère la meilleure clé disponible pour un service
        
        Args:
            service: 'api_football' ou 'the_odds_api'
        
        Returns:
            {'key_id': 'APIF_MAIN', 'key_value': 'xxx', 'remaining': 95}
        """
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Reset quotas si nouveau jour (pour daily)
            self._reset_daily_quotas_if_needed(cur, conn)
            
            # Chercher clé principale puis backup
            cur.execute("""
                SELECT key_id, quota_limit, quota_used, is_backup
                FROM api_keys_manager
                WHERE api_service = %s
                AND is_active = true
                AND quota_used < quota_limit
                ORDER BY is_backup ASC, priority ASC
                LIMIT 1
            """, (service,))
            
            row = cur.fetchone()
            
            if not row:
                logger.error(f"Aucune clé disponible pour {service}")
                return None
            
            key_id = row['key_id']
            remaining = row['quota_limit'] - row['quota_used']
            
            if row['is_backup']:
                logger.warning(f"Utilisation clé BACKUP pour {service}")
            
            return {
                'key_id': key_id,
                'key_value': self.keys.get(key_id),
                'remaining': remaining
            }
            
        finally:
            cur.close()
            conn.close()
    
    def increment_usage(self, key_id: str, success: bool = True):
        """Incrémente le compteur après une requête"""
        conn = self._get_conn()
        cur = conn.cursor()
        
        try:
            if success:
                cur.execute("""
                    UPDATE api_keys_manager
                    SET quota_used = quota_used + 1,
                        total_requests = total_requests + 1,
                        last_used_at = NOW()
                    WHERE key_id = %s
                """, (key_id,))
            else:
                cur.execute("""
                    UPDATE api_keys_manager
                    SET total_errors = total_errors + 1,
                        last_used_at = NOW()
                    WHERE key_id = %s
                """, (key_id,))
            
            conn.commit()
        finally:
            cur.close()
            conn.close()
    
    def _reset_daily_quotas_if_needed(self, cur, conn):
        """Reset les quotas journaliers si nouveau jour"""
        cur.execute("""
            UPDATE api_keys_manager
            SET quota_used = 0, quota_reset_at = NOW()
            WHERE quota_type = 'daily'
            AND (quota_reset_at IS NULL OR quota_reset_at::date < CURRENT_DATE)
        """)
        conn.commit()
    
    def get_stats(self) -> Dict:
        """Statistiques d'usage des clés"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT key_id, api_service, quota_limit, quota_used,
                       (quota_limit - quota_used) as remaining,
                       total_requests, total_errors, is_backup
                FROM api_keys_manager
                ORDER BY api_service, is_backup
            """)
            return [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()

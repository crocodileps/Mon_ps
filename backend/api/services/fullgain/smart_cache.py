"""
Smart Cache - Cache intelligent avec TTL adaptatif
"""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime, timedelta
from typing import Optional, Any
import hashlib
import logging

logger = logging.getLogger(__name__)

class SmartCache:
    """
    Cache intelligent:
    - TTL adaptatif selon type de données
    - Économise les requêtes API
    """
    
    # TTL en heures par type
    TTL = {
        'team_stats': 24,      # Stats équipes = 24h
        'h2h': 168,            # H2H = 1 semaine
        'odds': 1,             # Cotes = 1h
        'fixtures': 6,         # Fixtures = 6h
        'standings': 24,       # Classements = 24h
        'injuries': 12,        # Blessures = 12h
    }
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'monps_postgres'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def _make_key(self, cache_type: str, params: dict) -> str:
        """Génère clé unique"""
        h = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
        return f"{cache_type}:{h}"
    
    def get(self, cache_type: str, params: dict) -> Optional[Any]:
        """Récupère du cache si existe et non expiré"""
        key = self._make_key(cache_type, params)
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT data FROM smart_cache
                WHERE cache_key = %s AND expires_at > NOW()
            """, (key,))
            
            row = cur.fetchone()
            if row:
                # Update hit count
                cur.execute("UPDATE smart_cache SET hit_count = hit_count + 1 WHERE cache_key = %s", (key,))
                conn.commit()
                logger.info(f"✅ Cache HIT: {key}")
                return row['data']
            
            logger.info(f"❌ Cache MISS: {key}")
            return None
        finally:
            cur.close()
            conn.close()
    
    def set(self, cache_type: str, params: dict, data: Any, api_service: str = None):
        """Stocke en cache avec TTL adaptatif"""
        key = self._make_key(cache_type, params)
        ttl = self.TTL.get(cache_type, 24)
        expires = datetime.now() + timedelta(hours=ttl)
        
        conn = self._get_conn()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO smart_cache (cache_key, cache_type, data, ttl_hours, expires_at, api_service)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
                    data = EXCLUDED.data,
                    cached_at = NOW(),
                    expires_at = EXCLUDED.expires_at,
                    hit_count = 0
            """, (key, cache_type, Json(data), ttl, expires, api_service))
            conn.commit()
            logger.info(f"💾 Cache SET: {key} (TTL: {ttl}h)")
        finally:
            cur.close()
            conn.close()
    
    def get_stats(self) -> dict:
        """Stats du cache"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT cache_type, COUNT(*) as entries, SUM(hit_count) as hits
                FROM smart_cache WHERE expires_at > NOW()
                GROUP BY cache_type
            """)
            return {r['cache_type']: dict(r) for r in cur.fetchall()}
        finally:
            cur.close()
            conn.close()

"""
Service de connexion à la base de données
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from api.config import settings

def get_db_connection():
    """Créer une connexion à la base de données"""
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )

@contextmanager
def get_db():
    """Context manager pour la connexion DB"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def get_cursor(cursor_factory=RealDictCursor):
    """Context manager pour cursor avec dict"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
        finally:
            cursor.close()

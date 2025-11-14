"""
Routes API pour la gestion des paramètres (Settings)
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import json

from ..services.database import get_cursor
from ..models.schemas import SettingResponse, SettingUpdate

router = APIRouter(tags=["settings"])


@router.get("/", response_model=List[SettingResponse])
def get_all_settings():
    """Récupérer tous les paramètres de configuration"""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT id, key, value, description, created_at, updated_at
            FROM settings
            ORDER BY key
        """)
        rows = cursor.fetchall()
    return rows


@router.get("/health", response_model=Dict[str, Any])
def settings_health_check():
    """Vérifier que la table settings est accessible"""
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM settings")
            result = cursor.fetchone()
            count = result['count']
        
        return {
            "status": "healthy",
            "settings_count": count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: str):
    """Récupérer un paramètre spécifique par sa clé"""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT id, key, value, description, created_at, updated_at
            FROM settings
            WHERE key = %s
        """, (key,))
        row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    
    return row


@router.put("/{key}", response_model=SettingResponse)
def update_setting(key: str, setting: SettingUpdate):
    """Mettre à jour un paramètre existant"""
    with get_cursor() as cursor:
        # Vérifier existence
        cursor.execute("SELECT id FROM settings WHERE key = %s", (key,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        # Update (trigger auto-update updated_at)
        cursor.execute("""
            UPDATE settings
            SET value = %s
            WHERE key = %s
            RETURNING id, key, value, description, created_at, updated_at
        """, (json.dumps(setting.value), key))
        
        row = cursor.fetchone()
    
    return row

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class VariationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    enabled_factors: List[str] = []
    enabled_adjustments: List[str] = []
    use_new_threshold: bool = False
    custom_threshold: Optional[float] = None
    traffic_percentage: int = 0
    is_control: bool = False

class VariationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled_factors: Optional[List[str]] = None
    enabled_adjustments: Optional[List[str]] = None
    use_new_threshold: Optional[bool] = None
    custom_threshold: Optional[float] = None
    traffic_percentage: Optional[int] = None
    is_active: Optional[bool] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/improvements/{improvement_id}/variations")
async def get_variations(improvement_id: int):
    """
    Liste toutes les variations d'une amélioration
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                v.*,
                si.agent_name,
                si.new_threshold as improvement_threshold
            FROM improvement_variations v
            JOIN strategy_improvements si ON v.improvement_id = si.id
            WHERE v.improvement_id = %s
            ORDER BY v.is_control DESC, v.id ASC
        """, (improvement_id,))
        
        variations = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(variations),
            "variations": variations
        }
        
    except Exception as e:
        logger.error(f"Erreur get variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/improvements/{improvement_id}/variations")
async def create_variation(improvement_id: int, variation: VariationCreate):
    """
    Crée une nouvelle variation pour une amélioration
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier que l'amélioration existe
        cursor.execute("SELECT id FROM strategy_improvements WHERE id = %s", (improvement_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Amélioration non trouvée")
        
        # Insérer la variation
        cursor.execute("""
            INSERT INTO improvement_variations (
                improvement_id, name, description,
                enabled_factors, enabled_adjustments,
                use_new_threshold, custom_threshold,
                traffic_percentage, is_control
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING *
        """, (
            improvement_id,
            variation.name,
            variation.description,
            variation.enabled_factors,
            variation.enabled_adjustments,
            variation.use_new_threshold,
            variation.custom_threshold,
            variation.traffic_percentage,
            variation.is_control
        ))
        
        new_variation = cursor.fetchone()
        conn.commit()
        conn.close()
        
        logger.info(f"Variation créée: {variation.name} pour amélioration {improvement_id}")
        
        return {
            "success": True,
            "variation": new_variation
        }
        
    except Exception as e:
        logger.error(f"Erreur create variation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/variations/{variation_id}")
async def update_variation(variation_id: int, updates: VariationUpdate):
    """
    Met à jour une variation
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Construire la requête UPDATE dynamique
        update_fields = []
        update_values = []
        
        if updates.name is not None:
            update_fields.append("name = %s")
            update_values.append(updates.name)
        
        if updates.description is not None:
            update_fields.append("description = %s")
            update_values.append(updates.description)
        
        if updates.enabled_factors is not None:
            update_fields.append("enabled_factors = %s")
            update_values.append(updates.enabled_factors)
        
        if updates.enabled_adjustments is not None:
            update_fields.append("enabled_adjustments = %s")
            update_values.append(updates.enabled_adjustments)
        
        if updates.use_new_threshold is not None:
            update_fields.append("use_new_threshold = %s")
            update_values.append(updates.use_new_threshold)
        
        if updates.custom_threshold is not None:
            update_fields.append("custom_threshold = %s")
            update_values.append(updates.custom_threshold)
        
        if updates.traffic_percentage is not None:
            update_fields.append("traffic_percentage = %s")
            update_values.append(updates.traffic_percentage)
        
        if updates.is_active is not None:
            update_fields.append("is_active = %s")
            update_values.append(updates.is_active)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="Aucune modification fournie")
        
        update_fields.append("updated_at = NOW()")
        update_values.append(variation_id)
        
        query = f"""
            UPDATE improvement_variations
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """
        
        cursor.execute(query, update_values)
        updated_variation = cursor.fetchone()
        
        if not updated_variation:
            conn.close()
            raise HTTPException(status_code=404, detail="Variation non trouvée")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Variation {variation_id} mise à jour")
        
        return {
            "success": True,
            "variation": updated_variation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur update variation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/variations/{variation_id}")
async def delete_variation(variation_id: int):
    """
    Supprime une variation
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            DELETE FROM improvement_variations
            WHERE id = %s
            RETURNING id, name
        """, (variation_id,))
        
        deleted = cursor.fetchone()
        
        if not deleted:
            conn.close()
            raise HTTPException(status_code=404, detail="Variation non trouvée")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Variation {variation_id} supprimée: {deleted['name']}")
        
        return {
            "success": True,
            "deleted_id": deleted['id'],
            "deleted_name": deleted['name']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete variation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variations/{variation_id}/stats")
async def get_variation_stats(variation_id: int):
    """
    Récupère les stats de performance d'une variation
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                v.*,
                CASE 
                    WHEN v.matches_tested > 0 
                    THEN ROUND(100.0 * v.wins / v.matches_tested, 2)
                    ELSE 0
                END as calculated_win_rate
            FROM improvement_variations v
            WHERE v.id = %s
        """, (variation_id,))
        
        variation = cursor.fetchone()
        conn.close()
        
        if not variation:
            raise HTTPException(status_code=404, detail="Variation non trouvée")
        
        return {
            "success": True,
            "variation": variation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get variation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


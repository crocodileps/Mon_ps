from fastapi import APIRouter, HTTPException
import subprocess
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/settlement", tags=["settlement"])

@router.post("/run-clv")
async def run_clv_calculation():
    """Déclenche le calcul CLV manuellement"""
    try:
        result = subprocess.run(
            ['python3', 'scripts/auto_clv.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
    except Exception as e:
        logger.error("clv_calculation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run-settlement")
async def run_settlement():
    """Déclenche le settlement automatique manuellement"""
    try:
        result = subprocess.run(
            ['python3', 'scripts/auto_settlement.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
    except Exception as e:
        logger.error("settlement_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_settlement_stats():
    """Stats sur les paris réglés vs en attente"""
    from api.services.database import get_db
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status IN ('won', 'lost')) as settled,
                    COUNT(*) FILTER (WHERE settled_by = 'auto') as auto_settled,
                    COUNT(*) FILTER (WHERE clv_percent IS NOT NULL) as with_clv,
                    AVG(clv_percent) FILTER (WHERE clv_percent IS NOT NULL) as avg_clv
                FROM bets
            """)
            row = cursor.fetchone()
            
            return {
                "pending": row[0] or 0,
                "settled": row[1] or 0,
                "auto_settled": row[2] or 0,
                "with_clv": row[3] or 0,
                "avg_clv": float(row[4] or 0)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

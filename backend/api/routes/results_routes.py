from fastapi import APIRouter, HTTPException
import subprocess
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/fetch")
async def fetch_match_results():
    """
    Déclenche récupération résultats matchs terminés
    Exécute script fetch_results_football_data_v2.py
    """
    try:
        logger.info("Démarrage récupération résultats...")
        
        result = subprocess.run(
            ["python3", "/app/scripts/fetch_results_football_data_v2.py"],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes max
        )
        
        if result.returncode == 0:
            # Parser output pour extraire stats
            lines = result.stdout.split('\n')
            matches_processed = 0
            
            for line in lines:
                if "matchs traités" in line:
                    try:
                        matches_processed = int(line.split()[0])
                    except:
                        pass
                    break
            
            logger.info(f"✅ {matches_processed} matchs traités")
            
            return {
                "success": True,
                "message": "Résultats récupérés",
                "matches_processed": matches_processed,
                "output": result.stdout[-1000:]  # Derniers 1000 chars
            }
        else:
            raise Exception(f"Script error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout: Récupération trop longue")
    except Exception as e:
        logger.error(f"Erreur fetch results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

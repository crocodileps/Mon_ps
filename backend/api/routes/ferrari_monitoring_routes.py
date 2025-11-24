"""
Routes Ferrari Monitoring - Métriques et Dashboard
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
import logging

from api.services.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/monitoring/overview")
async def get_ferrari_overview(db: Session = Depends(get_db)):
    """
    Vue d'ensemble Ferrari - Métriques principales
    """
    try:
        # Variations actives
        query_variations = """
            SELECT 
                COUNT(*) as total_variations,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_variations
            FROM agent_b_variations
        """
        variations_stats = db.execute(query_variations).fetchone()
        
        # Stats globales depuis variation_stats
        query_stats = """
            SELECT 
                COUNT(DISTINCT variation_id) as variations_tested,
                SUM(total_bets) as total_signals,
                SUM(wins) as total_wins,
                AVG(win_rate) as avg_win_rate,
                AVG(roi) as avg_roi
            FROM variation_stats
            WHERE total_bets > 0
        """
        global_stats = db.execute(query_stats).fetchone()
        
        # Performance par variation (top 5)
        query_top = """
            SELECT 
                v.id,
                v.variation_name,
                vs.total_bets,
                vs.wins,
                vs.win_rate,
                vs.roi
            FROM agent_b_variations v
            JOIN variation_stats vs ON v.id = vs.variation_id
            WHERE vs.total_bets > 0
            ORDER BY vs.roi DESC
            LIMIT 5
        """
        top_variations = [dict(row) for row in db.execute(query_top).fetchall()]
        
        return {
            "success": True,
            "overview": {
                "total_variations": variations_stats[0] if variations_stats else 0,
                "active_variations": variations_stats[1] if variations_stats else 0,
                "variations_tested": global_stats[0] if global_stats and global_stats[0] else 0,
                "total_signals": global_stats[1] if global_stats and global_stats[1] else 0,
                "total_wins": global_stats[2] if global_stats and global_stats[2] else 0,
                "avg_win_rate": float(global_stats[3]) if global_stats and global_stats[3] else 0.0,
                "avg_roi": float(global_stats[4]) if global_stats and global_stats[4] else 0.0
            },
            "top_variations": top_variations
        }
        
    except Exception as e:
        logger.error(f"Erreur monitoring overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/daily-runs")
async def get_daily_runs(limit: int = 30):
    """
    Historique des runs quotidiens Ferrari
    """
    try:
        import os
        import glob
        from datetime import datetime
        
        log_dir = "/var/log/ferrari"
        log_files = glob.glob(f"{log_dir}/ferrari_ab_test_*.log")
        log_files.sort(reverse=True)
        
        runs = []
        for log_file in log_files[:limit]:
            try:
                # Parser le nom du fichier pour la date
                filename = os.path.basename(log_file)
                timestamp_str = filename.replace("ferrari_ab_test_", "").replace(".log", "")
                
                # Lire les métriques du log
                with open(log_file, 'r') as f:
                    content = f.read()
                    
                baseline_count = 0
                ferrari_count = 0
                success = "✅ SUCCÈS" in content
                
                # Extraire métriques
                for line in content.split('\n'):
                    if "📊 Baseline:" in line:
                        try:
                            baseline_count = int(line.split(":")[1].strip().split()[0])
                        except:
                            pass
                    if "🏎️  Ferrari Total:" in line:
                        try:
                            ferrari_count = int(line.split(":")[1].strip().split()[0])
                        except:
                            pass
                
                runs.append({
                    "timestamp": timestamp_str,
                    "success": success,
                    "baseline_signals": baseline_count,
                    "ferrari_signals": ferrari_count,
                    "log_file": log_file
                })
            except Exception as e:
                logger.warning(f"Erreur parsing log {log_file}: {e}")
                continue
        
        return {
            "success": True,
            "total_runs": len(runs),
            "runs": runs
        }
        
    except Exception as e:
        logger.error(f"Erreur daily runs: {e}")
        return {
            "success": False,
            "error": str(e),
            "runs": []
        }


@router.get("/monitoring/variations-performance")
async def get_variations_performance(db: Session = Depends(get_db)):
    """
    Performance détaillée de toutes les variations
    """
    try:
        query = """
            SELECT 
                v.id,
                v.variation_name,
                v.config,
                v.status,
                COALESCE(vs.total_bets, 0) as total_bets,
                COALESCE(vs.wins, 0) as wins,
                COALESCE(vs.losses, 0) as losses,
                COALESCE(vs.win_rate, 0) as win_rate,
                COALESCE(vs.total_profit, 0) as total_profit,
                COALESCE(vs.roi, 0) as roi
            FROM agent_b_variations v
            LEFT JOIN variation_stats vs ON v.id = vs.variation_id
            ORDER BY v.id
        """
        
        variations = [dict(row) for row in db.execute(query).fetchall()]
        
        return {
            "success": True,
            "total": len(variations),
            "variations": variations
        }
        
    except Exception as e:
        logger.error(f"Erreur variations performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

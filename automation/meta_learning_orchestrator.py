#!/usr/bin/env python3
"""
Meta-Learning Orchestrator - Ferrari 2.0
Automatisation robuste analyse GPT-4o quotidienne
"""

import requests
import time
import logging
import sys
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Optional
import json

# Configuration
API_BASE = "http://localhost:8001"
LOG_FILE = "/var/log/meta_learning_orchestrator.log"
MAX_RETRIES = 3
RETRY_DELAY = 60  # secondes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MetaLearningOrchestrator:
    """Orchestrateur principal analyse meta-learning"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 300  # 5 minutes timeout
        self.results = {
            "start_time": datetime.now().isoformat(),
            "steps_completed": [],
            "errors": [],
            "improvements_created": 0
        }
    
    def retry_request(self, method: str, url: str, max_retries: int = MAX_RETRIES) -> Optional[Dict]:
        """Exécute requête avec retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Tentative {attempt + 1}/{max_retries}: {method} {url}")
                
                if method == "POST":
                    response = self.session.post(url)
                else:
                    response = self.session.get(url)
                
                response.raise_for_status()
                
                logger.info(f"✅ Succès: {url}")
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ Tentative {attempt + 1} échouée: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Attente {RETRY_DELAY}s avant retry...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"🚨 Échec définitif après {max_retries} tentatives")
                    self.results["errors"].append(f"{method} {url}: {str(e)}")
                    return None
        
        return None
    
    def step_1_fetch_results(self) -> bool:
        """Étape 1: Récupérer résultats matchs"""
        logger.info("=" * 60)
        logger.info("ÉTAPE 1: Récupération résultats matchs")
        logger.info("=" * 60)
        
        url = f"{API_BASE}/results/fetch"
        result = self.retry_request("POST", url)
        
        if result:
            matches = result.get("matches_processed", 0)
            logger.info(f"✅ {matches} matchs traités")
            self.results["steps_completed"].append("fetch_results")
            self.results["matches_processed"] = matches
            return True
        
        logger.error("❌ Échec récupération résultats")
        return False
    
    def step_2_run_gpt4o(self) -> bool:
        """Étape 2: Lancer analyse GPT-4o"""
        logger.info("=" * 60)
        logger.info("ÉTAPE 2: Analyse GPT-4o")
        logger.info("=" * 60)
        
        # Attendre 5 minutes pour laisser DB se mettre à jour
        logger.info("⏳ Attente 5 minutes (update DB)...")
        time.sleep(300)
        
        url = f"{API_BASE}/strategies/meta-learning/analyze"
        result = self.retry_request("POST", url)
        
        if result:
            improvements = result.get("improvements_created", 0)
            logger.info(f"✅ {improvements} améliorations créées")
            self.results["steps_completed"].append("gpt4o_analysis")
            self.results["improvements_created"] = improvements
            return True
        
        logger.error("❌ Échec analyse GPT-4o")
        return False
    
    def step_3_get_improvements(self) -> Optional[list]:
        """Étape 3: Récupérer améliorations créées"""
        logger.info("=" * 60)
        logger.info("ÉTAPE 3: Récupération améliorations")
        logger.info("=" * 60)
        
        url = f"{API_BASE}/strategies/improvements"
        result = self.retry_request("GET", url)
        
        if result:
            improvements = result.get("improvements", [])
            logger.info(f"✅ {len(improvements)} améliorations au total")
            self.results["steps_completed"].append("get_improvements")
            return improvements
        
        logger.error("❌ Échec récupération améliorations")
        return None
    
    def send_notification(self, improvements: list):
        """Envoie notification si nouvelles améliorations"""
        if not improvements:
            logger.info("ℹ️  Aucune nouvelle amélioration")
            return
        
        # Filtrer améliorations d'aujourd'hui
        today = datetime.now().date()
        new_improvements = [
            imp for imp in improvements 
            if imp.get("created_at", "").startswith(str(today))
        ]
        
        if not new_improvements:
            logger.info("ℹ️  Aucune nouvelle amélioration aujourd'hui")
            return
        
        logger.info(f"🔔 {len(new_improvements)} nouvelles améliorations!")
        
        # Log détails
        for imp in new_improvements:
            logger.info(f"""
    Agent: {imp['agent_name']}
    Baseline: {imp['baseline_win_rate']}%
    Nouveau seuil: {imp['new_threshold']}%
    Gain attendu: +{imp['new_threshold'] - imp['baseline_win_rate']}%
            """)
        
        self.results["new_improvements"] = len(new_improvements)
    
    def generate_report(self) -> str:
        """Génère rapport final"""
        self.results["end_time"] = datetime.now().isoformat()
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║         RAPPORT META-LEARNING QUOTIDIEN                  ║
╚══════════════════════════════════════════════════════════╝

⏰ Début:  {self.results['start_time']}
⏰ Fin:    {self.results['end_time']}

✅ ÉTAPES COMPLÉTÉES:
{chr(10).join(f"   • {step}" for step in self.results['steps_completed'])}

📊 RÉSULTATS:
   • Matchs traités: {self.results.get('matches_processed', 0)}
   • Améliorations créées: {self.results.get('improvements_created', 0)}
   • Nouvelles améliorations: {self.results.get('new_improvements', 0)}

"""
        
        if self.results["errors"]:
            report += f"""
❌ ERREURS:
{chr(10).join(f"   • {err}" for err in self.results['errors'])}
"""
        else:
            report += "✅ Aucune erreur\n"
        
        report += """
╚══════════════════════════════════════════════════════════╝
"""
        return report
    
    def run(self):
        """Exécution complète workflow"""
        logger.info("🚀 Démarrage orchestrateur Meta-Learning")
        
        try:
            # Étape 1: Récupérer résultats
            if not self.step_1_fetch_results():
                logger.warning("⚠️  Étape 1 échouée, on continue quand même")
            
            # Étape 2: Analyse GPT-4o
            if not self.step_2_run_gpt4o():
                logger.error("🚨 Échec critique: Analyse GPT-4o")
                raise Exception("GPT-4o analysis failed")
            
            # Étape 3: Récupérer améliorations
            improvements = self.step_3_get_improvements()
            
            # Étape 4: Notifications
            if improvements:
                self.send_notification(improvements)
            
            # Rapport final
            report = self.generate_report()
            logger.info(report)
            
            # Sauvegarder rapport JSON
            with open("/var/log/meta_learning_last_run.json", "w") as f:
                json.dump(self.results, f, indent=2)
            
            logger.info("✅ Workflow terminé avec succès")
            return 0
            
        except Exception as e:
            logger.error(f"🚨 ERREUR CRITIQUE: {e}", exc_info=True)
            self.results["errors"].append(str(e))
            
            # Rapport d'erreur
            report = self.generate_report()
            logger.error(report)
            
            return 1


def main():
    """Point d'entrée principal"""
    orchestrator = MetaLearningOrchestrator()
    exit_code = orchestrator.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

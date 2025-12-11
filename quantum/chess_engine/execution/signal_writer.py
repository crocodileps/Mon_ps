"""SIGNAL WRITER - Output Generation"""

import json
import sys
from pathlib import Path
from typing import List, Any, Dict
from datetime import datetime
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PATHS


class SignalWriter:
    def __init__(self):
        self.output_dir = Path(PATHS.get("signals_output", "/home/Mon_ps/outputs/chess_engine_signals"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write(self, signals: List[Any], match_id: str) -> str:
        if not signals:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signals_{match_id}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        data = {
            "match_id": match_id,
            "generated_at": datetime.now().isoformat(),
            "signals_count": len(signals),
            "signals": [
                asdict(s) if hasattr(s, '__dataclass_fields__') else s
                for s in signals
            ],
            "summary": self._generate_summary(signals),
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"   📄 Signaux sauvegardes: {filepath}")
        return str(filepath)
    
    def _generate_summary(self, signals: List[Any]) -> Dict[str, Any]:
        if not signals:
            return {}
        
        total_stake = sum(
            s.stake_pct if hasattr(s, 'stake_pct') else 0
            for s in signals
        )
        
        avg_edge = sum(
            s.edge_net if hasattr(s, 'edge_net') else 0
            for s in signals
        ) / len(signals)
        
        markets = list(set(
            s.market if hasattr(s, 'market') else "unknown"
            for s in signals
        ))
        
        return {
            "total_stake_pct": total_stake,
            "average_edge": avg_edge,
            "markets": markets,
        }
